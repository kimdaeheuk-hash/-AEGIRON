"""백업 복원 훈련 (2026-10-19, 캡틴 승인 ②) — 복원해 본 적 없는 백업은 절반만 백업이다.

고정하는 것: ① 아티팩트 해시 불일치를 잡는다 ② DB 가 열리고 무결성·핵심 표를 본다
③ 백업에 있던 예측이 운영에서 사라지면 실패 ④ 봉인된 예측의 해시가 바뀌면 실패
⑤ 운영이 더 많은 것(새 예측)은 정상 ⑥ 워크플로가 백업을 받아 이 스크립트와 리허설을 부른다.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("restore_drill", ROOT / "scripts" / "restore_drill.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


def _backup(tmp_path, isolated_db, preds):
    for country, h in preds:
        p = isolated_db.create_prediction(country, "에볼라", 70.0, ["시험"])
        if h:
            with isolated_db.get_connection() as c:
                c.execute("UPDATE predictions SET content_hash=? WHERE id=?", (h, p["id"]))
                c.commit()
    d = tmp_path / "backup"
    d.mkdir()
    src, dst = sqlite3.connect(isolated_db.DB_PATH), sqlite3.connect(d / "epiweather.db")
    src.backup(dst)
    src.close()
    dst.close()
    (d / "predictions.json").write_text(json.dumps({"predictions": isolated_db.list_predictions()}))
    manifest = {f.name: {"sha256": hashlib.sha256(f.read_bytes()).hexdigest()} for f in d.iterdir()}
    manifest["_ledger"] = {"predictions": len(preds)}
    (d / "MANIFEST.json").write_text(json.dumps(manifest))
    return d


def _live(isolated_db, extra=()):
    rows = [{"id": p["id"], "content_hash": p.get("content_hash")} for p in isolated_db.list_predictions()]
    return rows + list(extra)


def test_good_backup_passes_and_new_live_predictions_are_fine(tmp_path, isolated_db):
    d = _backup(tmp_path, isolated_db, [("COD", "a" * 64), ("UGA", None)])
    problems, summary = rd.verify(d, _live(isolated_db, [{"id": 999, "content_hash": None}]))
    assert problems == []
    assert summary["integrity"] == "ok" and summary["rows"]["predictions"] == 2
    assert summary["sealed_compared"] == 1 and summary["live_predictions"] == 3


def test_tampered_artifact_is_caught(tmp_path, isolated_db):
    d = _backup(tmp_path, isolated_db, [("COD", None)])
    (d / "predictions.json").write_text("{}")
    problems, _ = rd.verify(d, _live(isolated_db))
    assert problems == ["predictions.json: SHA-256 불일치"]


def test_prediction_missing_from_live_ledger_fails(tmp_path, isolated_db):
    d = _backup(tmp_path, isolated_db, [("COD", None), ("UGA", None)])
    live = _live(isolated_db)[1:]
    problems, _ = rd.verify(d, live)
    assert any("운영 원장에서 사라짐" in p for p in problems)


def test_sealed_hash_changed_in_live_fails(tmp_path, isolated_db):
    d = _backup(tmp_path, isolated_db, [("COD", "a" * 64)])
    live = [{"id": r["id"], "content_hash": "b" * 64} for r in _live(isolated_db)]
    problems, _ = rd.verify(d, live)
    assert any("내용 해시가 운영에서 바뀜" in p for p in problems)


def test_missing_db_copy_is_a_failure(tmp_path, isolated_db):
    d = _backup(tmp_path, isolated_db, [("COD", None)])
    (d / "epiweather.db").unlink()
    manifest = json.loads((d / "MANIFEST.json").read_text())
    manifest.pop("epiweather.db")
    (d / "MANIFEST.json").write_text(json.dumps(manifest))
    problems, _ = rd.verify(d, _live(isolated_db))
    assert problems == ["DB 전체 사본 없음 — 원장 JSON 만으로는 복원할 수 없다"]


def test_workflow_restores_backup_then_rehearses_on_it():
    wf = (ROOT.parent / ".github" / "workflows" / "restore-drill.yml").read_text(encoding="utf-8")
    assert "ledger-backup.yml" in wf and "gh run download" in wf
    assert wf.index("scripts/restore_drill.py") < wf.index("scripts/rehearse_resolution.py"), \
        "복원한 사본으로 리허설한다"
    assert "cron:" in wf

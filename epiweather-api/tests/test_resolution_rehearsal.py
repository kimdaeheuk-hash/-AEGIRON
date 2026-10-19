"""90일 예측 첫 채점일 리허설 스크립트 (2026-10-19, 캡틴 승인 ⑤).

운영 DB 사본으로 채점 경로를 앞당겨 돌린다. 이 시험이 고정하는 것:
① 원본 DB 를 건드리지 않는다 ② 정답 경로가 그 기간을 못 봤으면 오답이 아니라 판정 보류로 센다
③ 공개 판정 기한(resolves_by)과 채점기 기한이 다르면 실패로 드러낸다 ④ 끝나면 DB 경로를 되돌린다.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rehearse_resolution", ROOT / "scripts" / "rehearse_resolution.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def _pred(db, made: str, resolves_by: str | None, disease="에볼라", country="COD"):
    p = db.create_prediction(country, disease, 80.0, ["시험"], confidence=0.6,
                             resolution_criteria="기준", resolves_by=resolves_by)
    with db.get_connection() as c:
        c.execute("UPDATE predictions SET predicted_at=? WHERE id=?", (made, p["id"]))
        c.commit()
    return p["id"]


def _counts(path) -> tuple:
    with sqlite3.connect(path) as c:
        return c.execute("SELECT COUNT(*), COUNT(verified_at) FROM predictions").fetchone()


def test_rehearsal_runs_on_a_copy_and_reports_blind_not_incorrect(isolated_db):
    _pred(isolated_db, "2026-08-17T23:00:00+00:00", "2026-11-15")
    _pred(isolated_db, "2026-09-01T10:00:00+00:00", "2026-11-30")
    src = isolated_db.DB_PATH
    before = _counts(src)
    rep = rr.rehearse(src, max_days=5)
    assert _counts(src) == before, "원본 DB 를 건드리면 안 된다"
    assert isolated_db.DB_PATH == src, "끝나면 DB 경로를 되돌린다"
    assert rep["first_deadline"] == "2026-11-15" and rep["open_before"] == 2
    assert [d["run_day"] for d in rep["days"]] == ["2026-11-16", "2026-12-01"]
    # 정답 경로가 한 건도 적재하지 않았다 → 오답으로 닫지 않고 판정 보류
    assert rep["days"][0]["blind"] == 1 and rep["days"][0]["resolved"] == {}
    assert "정답 경로가 한 건도 적재한 적이 없다" in rep["days"][0]["blind_reasons"]
    assert rep["deadline_mismatches"] == []
    assert rep["scorecard_after"]["resolved"] == 0
    md = rr.to_markdown(rep)
    assert "판정 보류 사유" in md and "성적이 아님" in md


def test_deadline_mismatch_fails_the_rehearsal(isolated_db, capsys):
    _pred(isolated_db, "2026-10-17T23:00:00+00:00", "2026-11-15")    # 채점기 기한은 2027-01-15
    assert rr.main([str(isolated_db.DB_PATH)]) == 1
    out = capsys.readouterr().out
    assert "공개 기한 2026-11-15 · 채점기 기한 2027-01-15" in out


def test_no_open_predictions_is_reported_not_crashed(isolated_db):
    rep = rr.rehearse(isolated_db.DB_PATH)
    assert rep["days"] == [] and rep["first_deadline"] is None
    assert "첫 판정 기한 없음" in rr.to_markdown(rep)

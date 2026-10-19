# -*- coding: utf-8 -*-
"""백업 복원 훈련 (2026-10-19, 캡틴 승인 ②).

## 왜

매일 백업(.github/workflows/ledger-backup.yml)은 성공하고 있지만 그 백업으로 **복원해 본 적이
없다.** 복원이 되는지 모르는 백업은 절반만 백업이다. 매주 가장 최근 백업 아티팩트를 받아
실제로 열어 보고, 운영 원장과 대조한다(.github/workflows/restore-drill.yml).

    python scripts/restore_drill.py BACKUP_DIR --live-predictions live.json

## 무엇을 확인하는가 (하나라도 어긋나면 실패)

1. MANIFEST 의 SHA-256 이 파일과 같다 — 아티팩트가 온전히 왔다.
2. DB 전체 사본이 열리고 PRAGMA integrity_check 가 ok, 핵심 표가 있다.
3. 백업의 예측이 운영 원장에서 **사라지지 않았다** — 원장은 추가만 되는 기록이다.
4. 봉인된 예측(content_hash)이 운영에서 **바뀌지 않았다** — 봉인 뒤 수정은 있을 수 없다.

운영이 백업보다 많은 것(그 사이 새 예측)은 정상이다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import sys

CORE_TABLES = ("predictions", "alerts", "outbreak_timeline", "baikal_transitions", "weekly_forecasts")


def verify(backup_dir: pathlib.Path, live_predictions: list[dict]) -> tuple[list[str], dict]:
    problems: list[str] = []
    summary: dict = {}
    manifest_path = backup_dir / "MANIFEST.json"
    if not manifest_path.exists():
        return ["MANIFEST.json 없음 — 백업 아티팩트 형식이 다름"], summary
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, meta in manifest.items():
        if name.startswith("_"):
            continue
        f = backup_dir / name
        if not f.exists():
            problems.append(f"{name}: 아티팩트에 없음")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != meta.get("sha256"):
            problems.append(f"{name}: SHA-256 불일치")
    summary["files_checked"] = sum(1 for n in manifest if not n.startswith("_"))

    db_file = backup_dir / "epiweather.db"
    backup_preds: list[dict] = []
    if not db_file.exists():
        problems.append("DB 전체 사본 없음 — 원장 JSON 만으로는 복원할 수 없다")
        ledger = backup_dir / "predictions.json"
        if ledger.exists():
            backup_preds = json.loads(ledger.read_text(encoding="utf-8")).get("predictions") or []
    else:
        try:
            conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            summary["integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = [t for t in CORE_TABLES if t not in tables]
            summary["tables"] = len(tables)
            summary["rows"] = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                               for t in CORE_TABLES if t in tables}
            backup_preds = [dict(r) for r in conn.execute("SELECT id, content_hash FROM predictions")]
            conn.close()
        except sqlite3.Error as e:
            problems.append(f"DB 를 열지 못함: {type(e).__name__}")
        else:
            if summary["integrity"] != "ok":
                problems.append(f"DB 무결성 검사 실패: {summary['integrity']}")
            if missing:
                problems.append(f"핵심 표 없음: {', '.join(missing)}")

    live = {p["id"]: p for p in live_predictions}
    gone = [p["id"] for p in backup_preds if p["id"] not in live]
    changed = [p["id"] for p in backup_preds
               if p.get("content_hash") and p["id"] in live
               and live[p["id"]].get("content_hash") != p["content_hash"]]
    summary.update({"backup_predictions": len(backup_preds), "live_predictions": len(live),
                    "sealed_compared": sum(1 for p in backup_preds if p.get("content_hash") and p["id"] in live)})
    if gone:
        problems.append(f"백업에 있던 예측 {len(gone)}건이 운영 원장에서 사라짐: {gone[:10]}")
    if changed:
        problems.append(f"봉인된 예측 {len(changed)}건의 내용 해시가 운영에서 바뀜: {changed[:10]}")
    return problems, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("backup_dir", type=pathlib.Path)
    ap.add_argument("--live-predictions", type=pathlib.Path, required=True)
    args = ap.parse_args(argv)
    live = json.loads(args.live_predictions.read_text(encoding="utf-8")).get("predictions") or []
    problems, summary = verify(args.backup_dir, live)
    print("## 백업 복원 훈련\n")
    print(f"- 확인한 파일 {summary.get('files_checked', 0)}개 · DB 무결성 {summary.get('integrity', '—')}"
          f" · 표 {summary.get('tables', '—')}개")
    if summary.get("rows"):
        print("- 행 수: " + " · ".join(f"{k} {v}" for k, v in summary["rows"].items()))
    print(f"- 예측: 백업 {summary.get('backup_predictions', 0)}건 · 운영 {summary.get('live_predictions', 0)}건"
          f" · 봉인 해시 대조 {summary.get('sealed_compared', 0)}건")
    if problems:
        print("\n복원 훈련 실패:")
        print("\n".join(f"- {p}" for p in problems))
        return 1
    print("\n복원 훈련 통과 — 백업을 열어 운영 원장과 대조했다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

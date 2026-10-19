# -*- coding: utf-8 -*-
"""90일 예측 첫 채점일 리허설 — 운영 DB **사본**으로 채점 경로를 미리 끝까지 돌려 본다.

## 왜 (2026-10-19, 캡틴 승인 ⑤)

예측 자동 채점(`prediction_resolver.resolve_due_predictions`)은 지금까지 실데이터로
기한이 지난 예측을 한 번도 닫아 본 적이 없다. 첫 판정 기한이 오는 날 처음으로 그
경로가 돈다 — 그날 고장 나거나, 예상과 다르게 닫히면(전부 '판정 보류' 등) 트랙레코드의
첫 장이 그렇게 기록된다. 그 전에 사본으로 날짜를 앞당겨 돌려 본다.

    python scripts/rehearse_resolution.py /path/to/epiweather.db [--days 5]

## 무엇을 보는가

- 미결 예측을 판정 기한(예측일 + 판정 기간)별로 묶고, 앞쪽 기한 N개마다 **그 다음 날**로
  시계를 옮겨 채점을 누적 실행한다(사본에만 쓴다).
- 날마다 해소(적중·오답·질병 불일치) · 판정 보류(정답 경로가 그 기간을 못 봄)와 사유 ·
  여전히 미결을 센다.
- 채점표(`prediction_scoring.score`)가 그 상태로 계산되는지 확인한다.
- ★ 기한 불일치 ★ 예측에 적힌 `resolves_by`(공개 판정 기준 문구에 들어간 날짜)와 채점기가
  쓰는 기한이 다르면 센다 — 공개한 약속과 실제 채점일이 어긋나면 안 된다.

## 정직성 경계선

- 운영 DB 를 건드리지 않는다. 받은 파일을 임시 폴더에 복사해 그 사본만 쓴다.
- 이 결과는 '그날 무엇이 일어날지'의 모의이지 성적이 아니다. 그 사이에 새 공식 선언이
  적재되면 실제 결과는 달라진다.
- 실패(빨간불) 조건: 채점 경로 예외 · 채점표 계산 예외 · 기한 불일치. 판정 보류가 많은 것은
  실패가 아니라 **보고할 사실**이다.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _date(value) -> dt.date | None:
    from algorithms.prediction_resolver import _parse_date
    return _parse_date(value)


def rehearse(db_file: pathlib.Path, max_days: int = 5) -> dict:
    import db

    original = db.DB_PATH
    try:
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "rehearsal.db"
            # 파일 복사가 아니라 sqlite backup API 로 뜬다 — WAL 에만 있는 쓰기가 빠지지 않게.
            src, dst = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True), sqlite3.connect(copy)
            try:
                src.backup(dst)
            finally:
                src.close()
                dst.close()
            db.DB_PATH = copy                   # 이 프로세스의 모든 읽기·쓰기가 사본으로 간다
            return _rehearse_on_copy(db, max_days)
    finally:
        db.DB_PATH = original


def _rehearse_on_copy(db, max_days: int) -> dict:
    from algorithms.prediction_resolver import _horizon_days, resolve_due_predictions
    from algorithms.prediction_scoring import score

    horizon = _horizon_days()
    preds = db.list_predictions() or []
    open_preds = [p for p in preds if not p.get("verified_at")]
    mismatches, due = [], collections.Counter()
    for p in open_preds:
        made = _date(p.get("predicted_at"))
        if made is None:
            continue
        deadline = made + dt.timedelta(days=horizon)
        due[deadline] += 1
        promised = _date(p.get("resolves_by"))
        if promised is not None and promised != deadline:
            mismatches.append({"id": p.get("id"), "predicted_at": p.get("predicted_at"),
                               "resolves_by": promised.isoformat(),
                               "resolver_deadline": deadline.isoformat()})

    days = []
    for deadline in sorted(due)[:max_days]:
        run_day = deadline + dt.timedelta(days=1)   # 기한 '다음 날'부터 닫힌다(today > deadline)
        out = resolve_due_predictions(today=run_day)
        kinds = collections.Counter(
            "적중" if r["correct"] == 1 else "오답" if r["correct"] == 0 else "질병 불일치"
            for r in out["resolved"])
        days.append({
            "run_day": run_day.isoformat(), "deadline": deadline.isoformat(),
            "due_on_deadline": due[deadline],
            "resolved": dict(kinds), "blind": out["blind"],
            "blind_reasons": out["blind_reasons"], "still_open": out["still_open"],
        })

    final_day = (dt.date.fromisoformat(days[-1]["run_day"]) if days else dt.date.today())
    card = score(db.list_predictions() or [], today=final_day)

    return {
        "horizon_days": horizon,
        "predictions": len(preds),
        "open_before": len(open_preds),
        "first_deadline": min(due).isoformat() if due else None,
        "deadline_mismatches": mismatches,
        "days": days,
        "scorecard_after": {k: card.get(k) for k in
                            ("total", "resolved", "correct", "incorrect", "unresolved", "brier")},
    }


def to_markdown(rep: dict) -> str:
    lines = [
        "## 90일 예측 채점 리허설 (운영 DB 사본)",
        "",
        f"- 예측 {rep['predictions']}건 · 미결 {rep['open_before']}건 · 판정 기간 {rep['horizon_days']}일"
        f" · 첫 판정 기한 {rep['first_deadline'] or '없음'}",
        f"- 기한 불일치(공개 문구 resolves_by ≠ 채점기 기한): {len(rep['deadline_mismatches'])}건",
        "",
        "| 실행일 | 기한 도래 | 적중 | 오답 | 질병 불일치 | 판정 보류 | 미결 |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in rep["days"]:
        r = d["resolved"]
        lines.append(f"| {d['run_day']} | {d['due_on_deadline']} | {r.get('적중', 0)} | {r.get('오답', 0)} | "
                     f"{r.get('질병 불일치', 0)} | {d['blind']} | {d['still_open']} |")
    reasons = collections.Counter()
    for d in rep["days"]:
        reasons.update(d["blind_reasons"])
    if reasons:
        lines += ["", "판정 보류 사유(정답 경로가 그 기간을 못 봄 — 오답으로 닫지 않음):"]
        lines += [f"- {k}: {v}건" for k, v in reasons.most_common()]
    if rep["deadline_mismatches"]:
        lines += ["", "기한 불일치 예(최대 10건):"]
        lines += [f"- #{m['id']} 예측 {m['predicted_at'][:10]} · 공개 기한 {m['resolves_by']}"
                  f" · 채점기 기한 {m['resolver_deadline']}" for m in rep["deadline_mismatches"][:10]]
    s = rep["scorecard_after"]
    lines += ["", f"리허설 후 채점표: 전체 {s['total']} · 판정 {s['resolved']} · 적중 {s['correct']} · "
                  f"오답 {s['incorrect']} · 미결 {s['unresolved']} · Brier {s['brier']}",
              "", "_모의 결과이며 성적이 아님 — 그 사이 새 공식 선언이 적재되면 실제 결과는 달라진다._"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("db_file", type=pathlib.Path)
    ap.add_argument("--days", type=int, default=5, help="앞쪽 판정 기한 몇 개를 돌릴지")
    ap.add_argument("--json", type=pathlib.Path, help="결과 JSON 저장 경로")
    args = ap.parse_args(argv)
    try:
        rep = rehearse(args.db_file, args.days)
    except Exception as e:                       # 채점 경로가 실데이터에서 깨졌다 — 이게 찾으려던 것
        print(f"리허설 실패: {type(e).__name__}: {e}")
        return 1
    print(to_markdown(rep))
    if args.json:
        args.json.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    if rep["deadline_mismatches"]:
        print(f"::error::공개 판정 기한과 채점기 기한이 다른 예측 {len(rep['deadline_mismatches'])}건")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

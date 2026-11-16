"""실적표 — 판매의 신뢰 근거를 한 응답으로 (2026-11-16).

고객이 데이터를 사기 전에 묻는 것은 "맞았나"다. 이미 따로 있는 채점표들을 **합치지 않고** 나란히 모은다:

- 질병 지목 예측(90일) 채점 — prediction_scoring.score
- 선행성 원장 — lead_time_ledger.ledger_record (문턱 통과 → 공식 선언, 오경보 포함)
- 선행일수 실측 — prediction_resolver.lead_time_record
- 이웃 나라 주간 방향 예측 — weekly_forecast.scorecard (판정 8건 미만이면 성적 판정 안 함)
- 경보 월별 건수 — 등급별·실제 전송 건수(전송 기록 notified_rank 가 있는 것)

★ 정직성 ★ 각 채점표의 '아직 표본 부족' 표시를 그대로 둔다. 하나라도 못 읽으면 그 칸은 error(판정 안 함).
서로 다른 과제의 적중률을 한 숫자로 합치지 않는다(쉬운 예측이 어려운 예측의 성적을 부풀린다).
"""
from __future__ import annotations


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:200]}


def alerts_by_month() -> list[dict]:
    import db

    with db.get_connection() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(alerts)").fetchall()}
        sent = "SUM(CASE WHEN notified_rank IS NOT NULL THEN 1 ELSE 0 END)" if "notified_rank" in cols else "NULL"
        rows = conn.execute(
            f"SELECT substr(alert_date, 1, 7) AS month, tier, COUNT(*) AS n, {sent} AS sent, "
            "SUM(CASE WHEN suppressed = 1 THEN 1 ELSE 0 END) AS suppressed "
            "FROM alerts GROUP BY month, tier ORDER BY month, tier"
        ).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        m = out.setdefault(r["month"], {"month": r["month"], "by_tier": {}, "total": 0, "sent": 0, "suppressed": 0})
        m["by_tier"][r["tier"]] = int(r["n"])
        m["total"] += int(r["n"])
        m["sent"] += int(r["sent"] or 0)
        m["suppressed"] += int(r["suppressed"] or 0)
    return list(out.values())


def track_record() -> dict:
    import db
    from algorithms.lead_time_ledger import ledger_record
    from algorithms.prediction_resolver import lead_time_record
    from algorithms.prediction_scoring import score
    from algorithms.weekly_forecast import all_forecasts, scorecard

    return {
        "predictions_90d": _safe(lambda: score(db.list_predictions())),
        "lead_time_ledger": _safe(ledger_record),
        "lead_time_measured": _safe(lead_time_record),
        "weekly_direction": _safe(lambda: scorecard(all_forecasts())),
        "alerts_by_month": _safe(alerts_by_month),
        "notes": [
            "과제가 다른 채점표를 하나의 적중률로 합치지 않음",
            "표본 부족 표시(enough·measured_events 등)는 각 채점표가 낸 그대로",
            "경보 sent = 실제 전송이 성공해 기록된 건수. 경보는 확인이 필요한 신호이며 발병 확정이 아님",
        ],
    }

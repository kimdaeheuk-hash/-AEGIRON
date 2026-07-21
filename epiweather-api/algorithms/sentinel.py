"""Sentinel Layer — Phase 2 ⑭ 빠른 이상 탐지.

5분 이내 반응. 신호가 과거 기준선의 2배 이상이면 sentinel_queue에 등록.
오탐 허용 — 진짜인지 판별은 verification.py가 담당.

설계 원칙:
  임계값(SPIKE_RATIO_MIN)은 낮게 잡는다. 놓치는 것보다 오탐이 낫다.
  같은 날 같은 metric은 DB에서 갱신(upsert) — 매시간 재실행해도 중복 없음.
"""
from __future__ import annotations
import datetime as dt
import statistics

import db
from .signal_metrics import iter_metric_series, load_records, MIN_HISTORY

SPIKE_RATIO_MIN = 2.0   # 기준선 대비 배수 임계값
BASELINE_WINDOW = 14    # 기준선 계산에 쓸 과거 관측치 수


def _compute_baseline(series: list[float | None]) -> float | None:
    clean = [v for v in series if v is not None and v > 0]
    if len(clean) < MIN_HISTORY:
        return None
    return statistics.mean(clean[-BASELINE_WINDOW:])


def scan_spikes() -> list[dict]:
    """
    모든 신호원의 최신값을 기준선(14일 평균)과 비교해 2배 이상 급등한 것을 반환.
    DB에도 upsert해서 verification.py가 처리 대기열로 쓸 수 있게 한다.
    """
    records = load_records()
    today = dt.date.today().isoformat()
    spikes: list[dict] = []

    for layer_key, metric_id, _trust, series in iter_metric_series(records):
        clean = [v for v in series if v is not None]
        if len(clean) < MIN_HISTORY + 1:
            continue

        latest = clean[-1]
        baseline_series = clean[-(BASELINE_WINDOW + 1):-1]
        baseline = _compute_baseline(baseline_series)
        if baseline is None or baseline == 0:
            continue

        ratio = latest / baseline
        if ratio < SPIKE_RATIO_MIN:
            continue

        sid = db.upsert_sentinel(
            detected_at=today,
            layer=layer_key,
            metric=metric_id,
            spike_ratio=round(ratio, 2),
            latest_val=round(latest, 4),
            baseline_avg=round(baseline, 4),
        )
        spikes.append({
            "id": sid,
            "layer": layer_key,
            "metric": metric_id,
            "spike_ratio": round(ratio, 2),
            "latest_val": round(latest, 4),
            "baseline_avg": round(baseline, 4),
            "status": "pending",
        })

    return spikes


def get_sentinel_status() -> dict:
    """대기열 전체 현황 요약."""
    pending   = db.list_sentinel_queue(status="pending")
    confirmed = db.list_sentinel_queue(status="confirmed")
    dismissed = db.list_sentinel_queue(status="dismissed")
    return {
        "pending_count":   len(pending),
        "confirmed_count": len(confirmed),
        "dismissed_count": len(dismissed),
        "pending":   pending[:10],
        "confirmed": confirmed[:10],
        # AI 자동검증(verification.py)이 사람의 수동 재검증과 얼마나 일치하는지 —
        # "AI 판정을 얼마나 믿을 수 있나"를 뒷받침할 실측 근거. 표본이 쌓여야 의미 생김.
        "ai_verification_accuracy": db.sentinel_verification_accuracy(),
        # 오탐율 상위 3개만 요약 — 전체 리포트는 GET /api/sentinel/reliability
        "least_reliable_metrics": db.metric_reliability_report()[:3],
    }

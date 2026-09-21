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
from .signal_metrics import (has_enough_distinct_history, iter_metric_series,
                             load_records, meets_alert_minimum, MIN_HISTORY)

SPIKE_RATIO_MIN = 2.0   # 기준선 대비 배수 임계값
BASELINE_WINDOW = 14    # 기준선 계산에 쓸 과거 관측치 수


def _compute_baseline(series: list[float | None]) -> float | None:
    """기준선(과거 평균). 표본이 모자라거나 **변해온 적이 없으면** None.

    ★ 두 문턱을 한 곳에서 본다 (2026-09-21) ★ 예전엔 표본 수(MIN_HISTORY)만
    봤다. 그런데 기준선에 실제로 들어가는 값은 `v > 0` 로 거른 뒤의 것이라,
    바깥에서 원본 series 로 '서로 다른 값'을 세면 **평균을 만든 값과 다른 걸
    세게 된다** — 0 이 여럿 섞인 축에서 둘이 어긋난다.
    그래서 같은 리스트로 둘 다 여기서 판정한다. #37 이 gai·anomaly_engine 을
    같은 문턱으로 묶은 것과 같은 이유다: 같은 지표를 두고 두 셈법이 다른 말을
    하면 그 자체가 고장이다.
    """
    clean = [v for v in series if v is not None and v > 0]
    if len(clean) < MIN_HISTORY:
        return None
    window = clean[-BASELINE_WINDOW:]
    if not has_enough_distinct_history(window):
        # 전부 같은 값이면 '2배'는 변동이 아니라 첫 변화일 뿐이다.
        return None
    return statistics.mean(window)


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

        # ★ 세 번째 엔진이 같은 문턱을 안 쓰고 있었다 (2026-09-21) ★
        # #37 이 `MIN_DISTINCT_HISTORY` 를 넣으면서 이렇게 적었다 — "gai 와
        # anomaly_engine **양쪽에** 같은 문턱. 두 엔진이 같은 지표를 두고 다른
        # 말을 하면 그 자체가 고장이다". Sentinel 은 같은 iter_metric_series 를
        # 읽는 **세 번째** 엔진인데 그때 빠졌다.
        #
        # 실측 (2026-09-20 22:01):
        #     🚨 Sentinel: 기준선 대비 2배 이상 급등 1건 감지 → 검증 대기열 등록
        #        - behavioral/social_cholera: x2.0 (최근값 2 vs 기준선 1)
        #
        # 마스토돈 콜레라 언급이 1명에서 2명이 된 것이다. 산술은 맞지만 서로 다른
        # 값 2개로 낸 '2배'는 숫자이지 근거가 아니다 — #37 이 네이버 축에서
        # 겪은 것과 같은 모양이고, 그때는 그게 캡틴 폰으로 critical 을 보냈다.
        #
        # 여기서 막는 건 **대기열 등록**이지 측정이 아니다(#36 의 원칙 그대로 —
        # 지수는 안 건드리고 승격 자리에만 문턱을 둔다). 오탐 허용은 이 층의
        # 설계 원칙이지만, 그건 '진짜일 수도 있는 걸 올린다'는 뜻이지 '표본이
        # 없어도 올린다'는 뜻이 아니다.
        # (판정 자체는 _compute_baseline 이 한다 — 평균을 만든 값과 같은
        #  리스트로 세야 해서 그 안에 뒀다. 위에서 baseline is None 으로 걸린다.)

        # 0 근처 카운트 지표의 최소 절대값(#36 의 표). 문턱이 없는 지표는 언제나
        # 통과한다 — 이 표는 '막는 목록'이지 '허용 목록'이 아니다.
        if not meets_alert_minimum(metric_id, latest):
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

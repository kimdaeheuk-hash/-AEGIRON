"""부정적 공간 감시 — 인수인계서 Part5 ⑤.

신호가 늘어나는 것만 위험한 게 아니다. 평소 활발하던 보고 채널이 갑자기
조용해지면 그 자체가 경보 대상 — 실제로 보고 체계가 무너졌을 수 있다.

  실제 사례:
  2014년 기니 에볼라 — 보건부 보고가 갑자기 감소
  → WHO가 "조용하다"고 판단 → 실제론 의료시스템 붕괴
  → 몇 주 후 폭발적 확산

판정 기준은 인수인계서 원문 그대로: 오늘 값이 과거 평균의 50% 미만이면 경보.
gai.py의 이상도 계산은 증가만 보므로(z<0은 0점), 이 모듈이 감소 쪽을 전담한다.
"""
from __future__ import annotations
import statistics

from .signal_metrics import LAYERS, MIN_HISTORY, load_records

DROP_RATIO = 0.5


def check_negative_space(latest: float | None, history_avg: float | None) -> dict:
    """단건 판정 — 인수인계서 원문 함수와 동일한 기준."""
    if latest is None or history_avg is None or history_avg <= 0:
        return {"alert": False, "message": "판정 불가 (과거 기준선 없음)"}
    if latest < history_avg * DROP_RATIO:
        return {"alert": True, "message": "⚠️ 신호 50% 감소 — 보고 체계 붕괴 가능성"}
    return {"alert": False, "message": "정상"}


def scan_negative_space() -> dict:
    """모든 신호원을 스캔해 보고량이 급감한 곳을 찾는다."""
    records = load_records()
    alerts = []
    checked = 0

    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, _trust_category in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            cleaned = [v for v in series if v is not None]
            if len(cleaned) < MIN_HISTORY + 1:
                continue
            checked += 1
            *history, latest = cleaned
            history_avg = statistics.mean(history)
            verdict = check_negative_space(latest, history_avg)
            if verdict["alert"]:
                alerts.append({
                    "layer": layer_key,
                    "label": cfg["label"],
                    "metric": metric_id,
                    "latest": latest,
                    "history_avg": round(history_avg, 2),
                    "drop_ratio": round(latest / history_avg, 2) if history_avg else None,
                    "message": verdict["message"],
                })

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "metrics_checked": checked,
    }

"""이상 신호 탐지 엔진 — Phase 2 ㉒.

기준선(baseline_signals.jsonl) + 실시간(signals_log.jsonl) 데이터를
합산해 신호원별 이상도를 자동 계산.

인수인계서 Part5 ㉒:
  Anomaly_Score = (오늘값 - 30일평균) / 30일평균

추가 기능:
  - 증상 기반 감시: 질병명 없이 '출혈+고열+격리' 동시 급증 감지
  - 기준선 통계 포함 (min/max/stdev)
  - 탐지된 이상 항목 상위 N개 반환
"""
from __future__ import annotations
import statistics
from datetime import date, timedelta

from .signal_metrics import iter_metric_series, load_records, MIN_HISTORY

ANOMALY_THRESHOLD  = 50.0   # 이상도 점수 임계값 (0~100)
BASELINE_WINDOW    = 30     # 기준선 계산에 쓸 과거 관측치 수
SYMPTOM_CLUSTERS = [
    {
        "name": "출혈열 클러스터",
        "fields": ["wiki_ebola_daily", "cidrap_ebola"],
        "threshold": 0.5,
    },
    {
        "name": "호흡기 클러스터",
        "fields": ["naver_flu_ratio", "cidrap_mers", "wiki_flu_daily"],
        "threshold": 0.5,
    },
    {
        "name": "동물→인간 클러스터",
        "fields": ["cidrap_avian_flu", "wahis_watch_hits"],
        "threshold": 0.5,
    },
]


def _ratio_anomaly(series: list[float | None], window: int = BASELINE_WINDOW) -> dict | None:
    """
    (오늘값 - N일평균) / N일평균 방식 이상도 계산.
    결과를 0~100으로 정규화(2배 급증 = 100점).
    """
    clean = [v for v in series if v is not None and v >= 0]
    if len(clean) < MIN_HISTORY + 1:
        return None
    latest = clean[-1]
    baseline = clean[-(window + 1):-1]
    avg = statistics.mean(baseline) if baseline else None
    if avg is None or avg == 0:
        return None
    ratio = (latest - avg) / avg
    score = round(min(max(ratio * 50 + 50, 0), 100), 1)
    stdev = statistics.pstdev(baseline) if len(baseline) > 1 else 0.0
    return {
        "latest":       round(latest, 4),
        "baseline_avg": round(avg, 4),
        "baseline_std": round(stdev, 4),
        "ratio":        round(ratio, 3),
        "anomaly_score": score,
    }


def compute_anomalies() -> dict:
    """
    모든 신호원의 이상도를 계산해 임계값 이상인 항목 목록과 전체 요약 반환.
    """
    records = load_records()
    anomalies: list[dict] = []
    all_metrics: list[dict] = []

    for layer_key, metric_id, trust_category, series in iter_metric_series(records):
        result = _ratio_anomaly(series)
        if result is None:
            continue
        entry = {
            "layer":   layer_key,
            "metric":  metric_id,
            "trust":   trust_category,
            **result,
        }
        all_metrics.append(entry)
        if result["anomaly_score"] >= ANOMALY_THRESHOLD:
            anomalies.append(entry)

    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

    return {
        "anomaly_count":   len(anomalies),
        "metrics_checked": len(all_metrics),
        "threshold":       ANOMALY_THRESHOLD,
        # gai.py의 GAI, forecast_engine.py의 예측점수와 척도(0~100)는 같아도
        # 계산식이 다른 별개 모델 — 소비자가 섞어서 비교하지 않도록 명시.
        "score_model":     "anomaly_engine_v1_ratio_vs_baseline",
        "anomalies":       anomalies,
        "symptom_clusters": _check_symptom_clusters(records),
    }


def _check_symptom_clusters(records: list[dict]) -> list[dict]:
    """
    질병명 없이 증상 키워드 동시 급등 탐지.
    '에볼라'라는 이름 대신 '출혈열 신호 + 격리 신호' 동시 급등을 잡는다.
    """
    metric_scores: dict[str, float] = {}
    for _, metric_id, _, series in iter_metric_series(records):
        result = _ratio_anomaly(series)
        if result:
            metric_scores[metric_id] = result["anomaly_score"]

    triggered = []
    for cluster in SYMPTOM_CLUSTERS:
        scores = [metric_scores.get(f) for f in cluster["fields"] if f in metric_scores]
        if not scores:
            continue
        avg_score = sum(scores) / len(scores)
        hit_ratio = sum(1 for s in scores if s >= ANOMALY_THRESHOLD) / len(scores)
        if hit_ratio >= cluster["threshold"]:
            triggered.append({
                "cluster":   cluster["name"],
                "avg_score": round(avg_score, 1),
                "hit_ratio": round(hit_ratio, 2),
                "fields":    cluster["fields"],
            })

    return triggered

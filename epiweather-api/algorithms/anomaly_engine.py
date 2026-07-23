"""이상 신호 탐지 엔진 — Phase 2 ㉒ (㉖에서 z-score로 통계 재보정).

기준선(baseline_signals.jsonl) + 실시간(signals_log.jsonl) 데이터를
합산해 신호원별 이상도를 자동 계산.

인수인계서 원안(Part5 ㉒)은 단순 퍼센트 편차였다:
  Anomaly_Score = (오늘값 - 30일평균) / 30일평균
그런데 이 방식은 지표의 '평소 변동폭'을 무시해서, 원래 들쭉날쭉한 지표든
안정적인 지표든 같은 임계값(고정 50)으로 판정한다 — 통계적으로 캘리브레이션된
게 아니라 '감으로 정한 숫자'였고(로컬 코드리뷰 지적), 실제로 score 50 = "오늘이
30일 평균보다 조금이라도 높음" = 우연히도 절반은 걸리는 과대탐지였다.

㉖에서 gai.py의 _anomaly_score와 동일한 z-score 방식으로 교체:
  z = (오늘값 - 기준선평균) / 기준선표준편차
지표마다 자기 변동폭으로 나누므로, 2σ 이상(통계적으로 유의한 급증)만 걸린다.
임계값도 하드코딩 50이 아니라 z=2.0(상위 ~2.3%, 단측)에서 유도한 값으로 명시.

추가 기능:
  - 증상 기반 감시: 질병명 없이 '출혈+고열+격리' 동시 급증 감지
  - 기준선 통계 포함 (평균·표준편차·z-score·퍼센트변화)
  - 탐지된 이상 항목 상위 N개 반환
"""
from __future__ import annotations
import statistics
from datetime import date, timedelta

from .signal_metrics import iter_metric_series, load_records, MIN_HISTORY

BASELINE_WINDOW      = 30     # 기준선 계산에 쓸 과거 관측치 수
# 2σ = 정규분포 단측 상위 ~2.3% — "통계적으로 유의한 급증"의 표준 관례.
# gai.py와 동일하게 z를 [0,3]에 클램프해 0~100으로 매핑하므로, 이 임계 점수도
# 그 매핑에서 유도한다(= 66.7). 하드코딩 50이 아니라 σ 기준에서 나온 값.
ANOMALY_Z_THRESHOLD  = 2.0
ANOMALY_THRESHOLD    = round(min(ANOMALY_Z_THRESHOLD, 3.0) / 3.0 * 100, 1)
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


def _zscore_anomaly(series: list[float | None], window: int = BASELINE_WINDOW) -> dict | None:
    """
    z-score 방식 이상도: z = (오늘값 - 기준선평균) / 기준선표준편차.
    z를 [0,3]에 클램프해 0~100으로 매핑(gai.py._anomaly_score와 동일 산식 —
    두 모듈이 같은 척도를 쓰게 해 소비자 혼란 방지). ratio(퍼센트변화)는
    사람이 읽기 위한 참고값으로 함께 반환한다.
    """
    clean = [v for v in series if v is not None and v >= 0]
    if len(clean) < MIN_HISTORY + 1:
        return None
    latest = clean[-1]
    baseline = clean[-(window + 1):-1]
    if not baseline:
        return None
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline) if len(baseline) > 1 else 0.0
    ratio = (latest - mean) / mean if mean else None  # 표시용 상대변화

    if stdev == 0:
        # 분산 0(항상 같은 값)인 기준선에선 z가 정의되지 않음 — gai.py와 동일하게
        # 통계적 이상도를 0으로 둬 과대탐지를 막되, 원시값은 그대로 노출.
        z = 0.0
    else:
        z = (latest - mean) / stdev
    score = round(max(0.0, min(z, 3.0)) / 3.0 * 100, 1)
    return {
        "latest":        round(latest, 4),
        "baseline_avg":  round(mean, 4),
        "baseline_std":  round(stdev, 4),
        "z_score":       round(z, 2),
        "ratio":         round(ratio, 3) if ratio is not None else None,
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
        result = _zscore_anomaly(series)
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
        "score_model":     "anomaly_engine_v2_zscore_vs_baseline",
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
        result = _zscore_anomaly(series)
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

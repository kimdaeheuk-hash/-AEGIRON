"""7·14일 예측 엔진 — Phase 3.

인수인계서:
  Wikipedia 조회수 7일 추세 → 선형회귀
  Perplexity 확진자 증가율 → 지수평활
  → "태국 7일 후 예측: 위험도 89점"

구현:
  1. 선형회귀 (Linear Regression):
     최근 N일 시계열에서 기울기(slope) 추출 → 7일/14일 후 값 외삽
  2. 지수평활 (Exponential Smoothing / EWMA):
     최신 데이터에 더 높은 가중치 → 최근 트렌드 반영 예측
  3. 앙상블: 두 방법 평균

외부 라이브러리 없이 순수 Python으로 구현 (numpy 없어도 동작).
"""
from __future__ import annotations
import statistics
from typing import NamedTuple

from .signal_metrics import iter_metric_series, load_records, MIN_HISTORY

FORECAST_DAYS = [7, 14]
EWMA_ALPHA    = 0.3   # 지수평활 계수 (0~1, 높을수록 최근 데이터 가중)
MIN_SERIES    = 7     # 예측에 필요한 최소 관측치


class ForecastResult(NamedTuple):
    metric:        str
    layer:         str
    current:       float
    forecast_7d:   float
    forecast_14d:  float
    method:        str
    confidence:    str   # high / medium / low


def _linear_regression(y: list[float]) -> tuple[float, float]:
    """단순 선형회귀 — (기울기, 절편) 반환."""
    n = len(y)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    num   = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denom = sum((xi - x_mean) ** 2 for xi in x)
    slope = num / denom if denom != 0 else 0.0
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _ewma_forecast(y: list[float], steps: int, alpha: float = EWMA_ALPHA) -> float:
    """지수가중이동평균으로 steps 후 값 예측."""
    smoothed = y[0]
    for val in y[1:]:
        smoothed = alpha * val + (1 - alpha) * smoothed
    trend = (y[-1] - y[max(0, len(y) - 4)]) / max(len(y) - 4, 1) if len(y) > 1 else 0
    return smoothed + trend * steps


def _score_from_value(value: float, baseline_avg: float, baseline_std: float) -> float:
    """값을 0~100 위험도 점수로 변환 (z-score 기반)."""
    if baseline_std == 0:
        return 50.0
    z = (value - baseline_avg) / baseline_std
    return round(max(0.0, min(z / 3.0 * 100 + 50, 100)), 1)


def forecast_all_metrics() -> dict:
    """
    모든 신호원에 대해 7일·14일 예측 점수 계산.
    예측 불가(데이터 부족)한 신호원은 제외.
    """
    records = load_records()
    forecasts: list[dict] = []

    for layer_key, metric_id, _trust, series in iter_metric_series(records):
        clean = [v for v in series if v is not None and v >= 0]
        if len(clean) < MIN_SERIES:
            continue

        baseline_avg = statistics.mean(clean[:-1]) if len(clean) > 1 else clean[0]
        baseline_std = statistics.pstdev(clean[:-1]) if len(clean) > 1 else 0.0
        current      = clean[-1]

        # 선형회귀 예측
        slope, intercept = _linear_regression(clean[-14:] if len(clean) >= 14 else clean)
        n = len(clean[-14:] if len(clean) >= 14 else clean)
        lr_7d  = intercept + slope * (n + 7)
        lr_14d = intercept + slope * (n + 14)

        # 지수평활 예측
        ew_7d  = _ewma_forecast(clean, 7)
        ew_14d = _ewma_forecast(clean, 14)

        # 앙상블 평균
        pred_7d  = max(0.0, (lr_7d  + ew_7d)  / 2)
        pred_14d = max(0.0, (lr_14d + ew_14d) / 2)

        score_now  = _score_from_value(current,  baseline_avg, baseline_std)
        score_7d   = _score_from_value(pred_7d,  baseline_avg, baseline_std)
        score_14d  = _score_from_value(pred_14d, baseline_avg, baseline_std)

        confidence = "high" if len(clean) >= 30 else ("medium" if len(clean) >= 14 else "low")

        forecasts.append({
            "layer":         layer_key,
            "metric":        metric_id,
            "current_val":   round(current, 4),
            "current_score": score_now,
            "forecast_7d": {
                "val":   round(pred_7d, 4),
                "score": score_7d,
                "delta": round(score_7d - score_now, 1),
            },
            "forecast_14d": {
                "val":   round(pred_14d, 4),
                "score": score_14d,
                "delta": round(score_14d - score_now, 1),
            },
            "confidence":   confidence,
            "data_points":  len(clean),
        })

    forecasts.sort(key=lambda f: f["forecast_7d"]["score"], reverse=True)

    top_alerts = [f for f in forecasts if f["forecast_7d"]["score"] >= 70]
    return {
        "forecast_count": len(forecasts),
        "top_alerts_7d":  len(top_alerts),
        "forecasts":      forecasts,
        "top_alerts":     top_alerts[:10],
    }


def forecast_summary(country: str | None = None) -> dict:
    """
    전체 예측을 가중평균해 단일 위험도 점수로 요약.
    GET /api/forecast 의 최상위 응답.
    """
    result = forecast_all_metrics()
    if not result["forecasts"]:
        return {"score_7d": None, "score_14d": None, "confidence": "insufficient_data"}

    forecasts = result["forecasts"]
    w7  = sum(f["forecast_7d"]["score"]  for f in forecasts) / len(forecasts)
    w14 = sum(f["forecast_14d"]["score"] for f in forecasts) / len(forecasts)

    def tier(s: float) -> str:
        if s >= 90: return "위험"
        if s >= 80: return "경보"
        if s >= 70: return "주의"
        return "정상"

    return {
        "score_7d":   round(w7,  1),
        "score_14d":  round(w14, 1),
        "tier_7d":    tier(w7),
        "tier_14d":   tier(w14),
        "confidence": "medium",
        "top_alerts": result["top_alerts"],
        "metrics_used": len(forecasts),
    }

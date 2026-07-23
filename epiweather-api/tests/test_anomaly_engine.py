"""이상탐지 엔진 z-score 재보정(㉖) — 퍼센트편차가 아니라 표준편차 기반으로
계산되는지, 임계값이 하드코딩이 아니라 σ 기준에서 유도되는지 확인. 로컬
코드리뷰가 지적한 '감으로 정한 50점 고정 임계값' 회귀 방지."""
from __future__ import annotations

from algorithms import anomaly_engine as ae
from algorithms.anomaly_engine import _zscore_anomaly, ANOMALY_THRESHOLD, ANOMALY_Z_THRESHOLD


def test_threshold_is_derived_from_sigma_not_hardcoded_50():
    """임계값이 z=2.0에서 유도된 값(≈66.7)이지 옛 하드코딩 50이 아니어야 함."""
    assert ANOMALY_Z_THRESHOLD == 2.0
    assert ANOMALY_THRESHOLD == round(2.0 / 3.0 * 100, 1)
    assert ANOMALY_THRESHOLD != 50.0


def test_zscore_accounts_for_metric_variability():
    """같은 절대 상승폭이라도 '평소 변동폭'이 크면 이상도가 낮아야 함 —
    퍼센트편차 방식은 이걸 구분 못 했지만 z-score는 구분한다."""
    # 안정적 기준선(변동 작음)에서 20 상승 → 강한 이상
    stable = [100.0] * 5 + [102, 98, 101, 99, 100] * 3 + [120.0]
    # 들쭉날쭉한 기준선(변동 큼)에서 같은 20 상승 → 약한 이상
    noisy = [100.0, 60, 140, 70, 130, 80, 120, 90, 110, 100] * 3 + [120.0]

    r_stable = _zscore_anomaly(stable)
    r_noisy = _zscore_anomaly(noisy)
    assert r_stable is not None and r_noisy is not None
    assert r_stable["anomaly_score"] > r_noisy["anomaly_score"]


def test_zscore_score_scale_matches_gai_mapping():
    """z를 [0,3]에 클램프해 0~100으로 매핑 — 3σ 이상이면 100점.
    (신호 카운트는 음수 불가라 기준선은 양수로 구성 — mean 10, pstdev 2)."""
    baseline = [8.0, 12.0, 8.0, 12.0, 8.0, 12.0, 8.0, 12.0, 8.0, 12.0]  # mean=10, pstdev=2
    series = baseline + [16.0]  # z = (16-10)/2 = 3
    r = _zscore_anomaly(series)
    assert r["z_score"] >= 2.9
    assert r["anomaly_score"] == 100.0


def test_flat_baseline_returns_zero_anomaly_not_crash():
    """분산 0 기준선(항상 같은 값)에서 값이 튀어도 z 정의 불가 → 0점(과대탐지 방지),
    크래시하지 않아야 함."""
    series = [50.0] * 10 + [80.0]
    r = _zscore_anomaly(series)
    assert r is not None
    assert r["z_score"] == 0.0
    assert r["anomaly_score"] == 0.0
    assert r["baseline_std"] == 0.0


def test_ratio_still_returned_for_human_display():
    """z-score로 바꿔도 사람이 읽는 퍼센트변화(ratio)는 참고용으로 남겨둠."""
    series = [100.0] * 10 + [150.0]
    r = _zscore_anomaly(series)
    assert r["ratio"] == 0.5  # +50%


def test_insufficient_history_returns_none():
    assert _zscore_anomaly([100.0]) is None


def test_compute_anomalies_reports_v2_score_model():
    result = ae.compute_anomalies()
    assert result["score_model"] == "anomaly_engine_v2_zscore_vs_baseline"
    assert result["threshold"] == ANOMALY_THRESHOLD

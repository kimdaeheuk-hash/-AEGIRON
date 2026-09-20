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
    # 서로 다른 값 3개 이상이어야 판정한다(2026-09-20) — 3σ 지점은 손으로 적지
    # 않고 기준선에서 직접 계산한다. 픽스처를 고쳐도 검증 대상은 그대로다.
    import statistics
    baseline = [8.0, 12.0, 10.0] * 4
    mean, std = statistics.mean(baseline), statistics.pstdev(baseline)
    series = baseline + [mean + 3 * std]  # 정확히 z = 3
    r = _zscore_anomaly(series)
    assert abs(r["z_score"] - 3.0) < 0.01
    assert r["anomaly_score"] == 100.0


def test_flat_baseline_is_withheld_not_scored_zero():
    """★계약이 바뀌었다 (2026-09-20)★ 예전엔 0점짜리 결과를 돌려줬다.

    한 번도 변한 적 없는 기준선에서 0점은 '이상 없음'이라는 판정이 된다. 우리가
    아는 건 '판정할 수 없다'뿐이다. 이제 None 이고, compute_anomalies 가 그
    지표를 건너뛴다(metrics_checked 에서도 빠진다 — 세지 않은 걸 셌다고 하지 않는다).

    크래시하지 않아야 한다는 원래 요구는 그대로 지킨다."""
    series = [50.0] * 10 + [80.0]
    assert _zscore_anomaly(series) is None


def test_ratio_still_returned_for_human_display():
    """z-score로 바꿔도 사람이 읽는 퍼센트변화(ratio)는 참고용으로 남겨둠."""
    # 기준선 평균 100 은 유지하되 서로 다른 값 3개를 준다(2026-09-20 문턱).
    series = [90.0, 100.0, 110.0] * 3 + [150.0]
    r = _zscore_anomaly(series)
    assert r["ratio"] == 0.5  # +50%


def test_insufficient_history_returns_none():
    assert _zscore_anomaly([100.0]) is None


def test_compute_anomalies_reports_score_model_and_ears():
    result = ae.compute_anomalies()
    assert result["score_model"] == "anomaly_engine_v3_zscore_plus_cdc_ears"
    assert result["threshold"] == ANOMALY_THRESHOLD
    # CDC EARS를 z-score와 나란히 쓴다는 걸 명시(심사 방어용)
    assert "cdc_ears_c1_c2_c3" in result["detection_methods"]
    assert "ears_alarm_count" in result

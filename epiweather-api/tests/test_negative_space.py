"""부정적 공간 감시 — 인수인계서 Part5 ⑤.
'오늘 값이 과거평균의 50% 미만이면 경보' 판정 기준과, 실측 오탐으로 밝혀져
스캔에서 제외된 지표 목록(UNRELIABLE_METRICS/SEASONAL_METRICS)이 계속
지켜지는지 확인."""
from __future__ import annotations

from algorithms.negative_space import (
    check_negative_space, UNRELIABLE_METRICS, SEASONAL_METRICS, MIN_MEANINGFUL_AVG,
)


def test_alert_when_dropped_below_50_percent():
    result = check_negative_space(latest=4, history_avg=10)
    assert result["alert"] is True


def test_no_alert_exactly_at_50_percent_boundary():
    """코드 기준은 '미만'(<)이라 정확히 50%는 정상 취급."""
    result = check_negative_space(latest=5, history_avg=10)
    assert result["alert"] is False


def test_no_alert_when_signal_is_normal_or_rising():
    assert check_negative_space(latest=9, history_avg=10)["alert"] is False
    assert check_negative_space(latest=15, history_avg=10)["alert"] is False


def test_no_verdict_without_baseline():
    result = check_negative_space(latest=5, history_avg=None)
    assert result["alert"] is False
    assert "판정 불가" in result["message"]


def test_no_verdict_when_baseline_is_zero_or_negative():
    assert check_negative_space(latest=5, history_avg=0)["alert"] is False
    assert check_negative_space(latest=5, history_avg=-1)["alert"] is False


def test_no_verdict_when_average_too_small_to_be_meaningful():
    """평균이 MIN_MEANINGFUL_AVG 미만이면 0건→비율 급변이 정상이라 판정 자체를 건너뜀
    (2026-07-19 SNS 언급수·AI 긴급도 점수 만성 오탐 수정에서 도입)."""
    result = check_negative_space(latest=0, history_avg=MIN_MEANINGFUL_AVG - 0.1)
    assert result["alert"] is False
    assert "판정 불가" in result["message"]


def test_known_noisy_metrics_stay_excluded_from_scan():
    """실측 오탐으로 확인되어 스캔에서 뺀 지표들 — 회귀 방지용 잠금 테스트."""
    assert "mobility_total_flights" in UNRELIABLE_METRICS
    assert "infodengue_casos_total" in SEASONAL_METRICS

"""기후·환경 선행지표(㉛) — 매개체 적합도 곡선, 단기 온난화 추세, 정직성
플래그(측정치가 아니라 선행지표 추정)가 맞는지 확인. 실제 Open-Meteo 호출은
mock(샌드박스 외부 API 차단)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.climate_signals import (
    vector_suitability, compute_country_climate, climate_signals_all,
    COUNTRY_COORDS, VECTOR_T_OPT,
)


def test_vector_suitability_peaks_at_optimum_and_zero_outside_window():
    assert vector_suitability(VECTOR_T_OPT) == 1.0       # 29°C 최적
    assert vector_suitability(10.0) == 0.0               # 너무 추움
    assert vector_suitability(40.0) == 0.0               # 너무 더움
    # 최적 양옆으로 단조 증가/감소
    assert 0.0 < vector_suitability(23.0) < 1.0
    assert 0.0 < vector_suitability(32.0) < 1.0


def _fake_openmeteo(temps, precip):
    payload = {"daily": {"temperature_2m_max": temps, "precipitation_sum": precip}}
    resp = MagicMock(status_code=200)
    resp.json = lambda: payload
    return resp


def test_compute_country_climate_computes_heat_trend_and_pressure():
    # 이전 85일 평균 25°C, 최근 7일 평균 29°C → +4°C 단기 온난화, 최적 매개온도
    temps = [25.0] * 85 + [29.0] * 7
    precip = [0.0] * 78 + [10.0] * 14  # 최근 14일 누적 140mm
    with patch("algorithms.climate_signals.requests.get", return_value=_fake_openmeteo(temps, precip)):
        result = compute_country_climate("THA")

    assert result["data_available"] is True
    assert result["mean_recent_temp_c"] == 29.0
    assert result["heat_trend_c"] == 4.0
    assert result["vector_suitability"] == 1.0        # 29°C = 최적
    assert result["precip_recent_14d_mm"] == 140.0
    assert 0 <= result["spillover_pressure"] <= 100
    # 정직성 플래그
    assert result["is_leading_indicator"] is True
    assert result["measured"] is False
    assert result["weights_calibrated"] is False


def test_compute_country_climate_flags_unavailable_on_fetch_failure():
    with patch("algorithms.climate_signals.requests.get", side_effect=Exception("blocked")):
        result = compute_country_climate("KOR")
    assert result["data_available"] is False
    assert result["measured"] is False


def test_compute_country_climate_unknown_country_raises_keyerror():
    import pytest
    with pytest.raises(KeyError):
        compute_country_climate("ZZZ")


def test_all_tier1_countries_have_coords():
    """country_risk.COUNTRIES(Tier-1) 14개국이 전부 기후 좌표를 갖는지 회귀 방지."""
    from algorithms.country_risk import COUNTRIES
    for iso3 in COUNTRIES:
        assert iso3 in COUNTRY_COORDS, f"{iso3} 좌표 누락"


def test_climate_signals_all_sorts_available_by_pressure_and_flags_source():
    temps_hot = [28.0] * 85 + [29.0] * 7   # 높은 압력
    temps_cold = [5.0] * 85 + [5.0] * 7    # 매개온도 밖 → 낮은 압력
    precip = [0.0] * 92

    def _side_effect(*args, **kwargs):
        lat = kwargs["params"]["latitude"]
        # 태국(위도 13.75)만 더운 데이터, 나머지는 추운 데이터로
        temps = temps_hot if abs(lat - 13.7563) < 0.01 else temps_cold
        return _fake_openmeteo(temps, precip)

    with patch("algorithms.climate_signals.requests.get", side_effect=_side_effect):
        result = climate_signals_all()

    assert result["data_source"].startswith("Open-Meteo")
    assert "삼림파괴" in result["disclaimer"]  # 미구현 동인 정직하게 명시
    available = [c for c in result["countries"] if c.get("data_available")]
    # 내림차순 정렬
    scores = [c["spillover_pressure"] for c in available]
    assert scores == sorted(scores, reverse=True)

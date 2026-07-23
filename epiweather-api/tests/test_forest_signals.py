"""토지이용·벌목 선행지표(㉜) — FIRMS 화재 수 파싱·정규화, 그리고 정직성
플래그(화재는 실측이나 삼림파괴는 프록시)가 맞는지 확인. 실제 FIRMS 호출은
mock(샌드박스 외부 API 차단)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

import pytest

from algorithms.forest_signals import (
    fetch_fire_count, _pressure_from_count, compute_country_land, land_signals_all,
    FIRMS_COUNTRY_CODES,
)

SAMPLE_CSV = (
    "country_id,latitude,longitude,bright_ti4,acq_date,confidence,frp,daynight\n"
    "BRA,-3.1,-60.0,320.1,2026-07-20,n,5.2,D\n"
    "BRA,-3.2,-60.1,330.5,2026-07-20,h,8.1,D\n"
    "BRA,-3.3,-60.2,310.0,2026-07-21,l,3.0,N\n"
)


def _fake_csv_resp(text, status=200):
    return MagicMock(status_code=status, text=text)


def test_fetch_fire_count_counts_data_rows_excluding_header():
    with patch("algorithms.forest_signals.requests.get", return_value=_fake_csv_resp(SAMPLE_CSV)):
        count = fetch_fire_count("BRA", "fakekey")
    assert count == 3


def test_fetch_fire_count_empty_body_returns_zero():
    with patch("algorithms.forest_signals.requests.get", return_value=_fake_csv_resp("")):
        assert fetch_fire_count("BRA", "fakekey") == 0


def test_fetch_fire_count_rejects_non_csv_error_body():
    """잘못된 키 등으로 에러 텍스트가 오면(헤더 아님) None으로 방어."""
    with patch("algorithms.forest_signals.requests.get",
               return_value=_fake_csv_resp("Invalid MAP_KEY provided")):
        assert fetch_fire_count("BRA", "badkey") is None


def test_fetch_fire_count_network_error_returns_none():
    with patch("algorithms.forest_signals.requests.get", side_effect=Exception("blocked")):
        assert fetch_fire_count("BRA", "fakekey") is None


def test_pressure_from_count_monotonic_and_bounded():
    assert _pressure_from_count(0) == 0.0
    p_low = _pressure_from_count(10)
    p_high = _pressure_from_count(3000)
    assert 0 < p_low < p_high <= 100


def test_compute_country_land_flags_fire_measured_but_deforestation_proxy():
    with patch("algorithms.forest_signals.requests.get", return_value=_fake_csv_resp(SAMPLE_CSV)):
        result = compute_country_land("BRA", map_key="fakekey")
    assert result["data_available"] is True
    assert result["fire_count_recent"] == 3
    assert result["fire_detections_measured"] is True     # 화재는 실측
    assert result["is_proxy_for_deforestation"] is True   # 삼림파괴는 프록시(정직성 핵심)
    assert result["is_leading_indicator"] is True
    assert 0 <= result["land_clearing_pressure"] <= 100


def test_compute_country_land_no_key_flags_unavailable(monkeypatch):
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    result = compute_country_land("BRA")
    assert result["data_available"] is False
    assert "FIRMS_MAP_KEY" in result["reason"]


def test_compute_country_land_unknown_country_raises_keyerror():
    with pytest.raises(KeyError):
        compute_country_land("ZZZ", map_key="fakekey")


def test_hong_kong_intentionally_excluded_from_firms():
    """FIRMS 국가목록에 없는 홍콩(HKG)은 의도적으로 제외 — 억지로 넣지 않음."""
    assert "HKG" not in FIRMS_COUNTRY_CODES
    # 나머지 Tier-1은 전부 포함
    from algorithms.country_risk import COUNTRIES
    for iso3 in COUNTRIES:
        if iso3 == "HKG":
            continue
        assert iso3 in FIRMS_COUNTRY_CODES, f"{iso3} 누락"


def test_land_signals_all_sorts_and_flags_source(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "fakekey")

    def _side_effect(url, *a, **k):
        # 브라질만 많은 화재, 나머지는 빈 CSV
        text = SAMPLE_CSV if "/BRA/" in url else "country_id,latitude,longitude\n"
        return _fake_csv_resp(text)

    with patch("algorithms.forest_signals.requests.get", side_effect=_side_effect):
        result = land_signals_all()

    assert result["configured"] is True
    assert result["data_source"].startswith("NASA FIRMS")
    assert "GFW" in result["disclaimer"]  # 직접 산림손실은 다음 단계임을 명시
    available = [c for c in result["countries"] if c.get("data_available")]
    scores = [c["land_clearing_pressure"] for c in available]
    assert scores == sorted(scores, reverse=True)

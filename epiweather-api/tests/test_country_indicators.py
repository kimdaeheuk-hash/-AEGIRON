"""국가 취약성 지수 실데이터 연동 — World Bank/OpenFlights 응답 파싱과 정규화가
맞는지 확인. 실제 네트워크 호출은 하지 않고(이 개발 환경은 외부 API 접근이
막혀 있음) 알려진 응답 스펙을 mock으로 재현해 검증한다."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.country_indicators import (
    fetch_worldbank_indicator, _normalize_linear, _normalize_log,
)

WB_SAMPLE_RESPONSE = [
    {"page": 1, "pages": 1, "per_page": 1, "total": 1},
    [{
        "indicator": {"id": "SH.MED.BEDS.ZS", "value": "Hospital beds"},
        "country": {"id": "KR", "value": "Korea, Rep."},
        "countryiso3code": "KOR", "date": "2021", "value": 12.4,
        "unit": "", "obs_status": "", "decimal": 1,
    }],
]


def test_fetch_worldbank_indicator_parses_most_recent_value():
    with patch("algorithms.country_indicators.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: WB_SAMPLE_RESPONSE)
        result = fetch_worldbank_indicator("KOR", "SH.MED.BEDS.ZS")
    assert result == (12.4, "2021")


def test_fetch_worldbank_indicator_returns_none_on_http_error():
    with patch("algorithms.country_indicators.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)
        assert fetch_worldbank_indicator("XXX", "SH.MED.BEDS.ZS") is None


def test_fetch_worldbank_indicator_returns_none_when_no_data():
    empty_response = [{"page": 1}, []]
    with patch("algorithms.country_indicators.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: empty_response)
        assert fetch_worldbank_indicator("XXX", "SH.MED.BEDS.ZS") is None


def test_normalize_linear_clamps_to_0_1():
    assert _normalize_linear(100, 13) == 1.0
    assert _normalize_linear(0, 13) == 0.0
    assert _normalize_linear(6.5, 13) == 0.5


def test_normalize_log_handles_zero_and_negative():
    assert _normalize_log(0, 8000) == 0.0
    assert _normalize_log(-5, 8000) == 0.0


def test_normalize_log_orders_values_correctly():
    """인구밀도처럼 편차 큰 값도 상대적 순서는 유지돼야 함."""
    low = _normalize_log(40, 8000)     # DRC 수준
    high = _normalize_log(7000, 8000)  # 홍콩 수준
    assert 0.0 < low < high < 1.0

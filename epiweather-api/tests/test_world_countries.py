"""전세계 국가 참조데이터(World Bank 국가목록) — 지역집계 항목 제외, 좌표 파싱이
맞는지 확인. 실제 네트워크 호출은 하지 않음(이 개발 환경은 api.worldbank.org
접근이 막혀 있음 — country_indicators.py와 동일한 제약)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.world_countries import fetch_world_countries

SAMPLE_RESPONSE = [
    {"page": 1, "pages": 1, "per_page": 400, "total": 3},
    [
        {
            "id": "KOR", "iso2Code": "KR", "name": "Korea, Rep.",
            "region": {"id": "EAS", "value": "East Asia & Pacific"},
            "capitalCity": "Seoul", "longitude": "126.978", "latitude": "37.5665",
        },
        {
            "id": "COD", "iso2Code": "CD", "name": "Congo, Dem. Rep.",
            "region": {"id": "SSF", "value": "Sub-Saharan Africa"},
            "capitalCity": "Kinshasa", "longitude": "15.2663", "latitude": "-4.4419",
        },
        {
            "id": "ARB", "iso2Code": "1A", "name": "Arab World",
            "region": {"id": "NA", "value": "Aggregates"},
            "capitalCity": "", "longitude": "", "latitude": "",
        },
    ],
]


def test_fetch_world_countries_excludes_aggregate_regions():
    with patch("algorithms.world_countries.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE)
        result = fetch_world_countries()
    assert "ARB" not in result
    assert set(result) == {"KOR", "COD"}


def test_fetch_world_countries_parses_name_and_coords():
    with patch("algorithms.world_countries.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE)
        result = fetch_world_countries()
    assert result["KOR"]["name"] == "Korea, Rep."
    assert result["KOR"]["lat"] == 37.5665
    assert result["KOR"]["lng"] == 126.978


def test_fetch_world_countries_returns_empty_on_http_error():
    with patch("algorithms.world_countries.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=503)
        assert fetch_world_countries() == {}

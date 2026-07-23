"""직접 산림손실 선행지표(㉝) — GFW 응답의 방어적 파싱(컬럼명 달라도 견딤),
정직성 플래그, 예상밖 응답 시 가짜 숫자 대신 실패로 떨어지는지 확인.
실제 GFW 호출은 mock(샌드박스 외부 API 차단)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

import pytest

from algorithms.deforestation_signals import (
    _extract_count, fetch_deforestation_alerts, compute_country_deforestation,
    deforestation_signals_all, GFW_COUNTRIES,
)


def _resp(payload, status=200):
    r = MagicMock(status_code=status)
    r.json = lambda: payload
    return r


def test_extract_count_handles_various_column_names():
    """컬럼명이 count/alert__count/value 무엇이든 첫 숫자값을 집어야 함(방어적)."""
    assert _extract_count({"data": [{"count": 1234}]}) == 1234
    assert _extract_count({"data": [{"alert__count": 55}]}) == 55
    assert _extract_count({"data": [{"iso": "BRA", "value": 900}]}) == 900


def test_extract_count_returns_none_on_unexpected_shapes():
    """예상밖 응답이면 가짜 숫자 대신 None(→ data_available=False)."""
    assert _extract_count({}) is None
    assert _extract_count({"data": []}) is None
    assert _extract_count({"data": [{"iso": "BRA"}]}) is None   # 숫자 없음
    assert _extract_count({"status": "error"}) is None
    assert _extract_count("not a dict") is None


def test_extract_count_ignores_boolean_values():
    """bool은 int의 subclass라 실수로 집지 않도록 — True/False는 건너뛰고 실수만."""
    assert _extract_count({"data": [{"ok": True, "count": 7}]}) == 7


def test_fetch_deforestation_alerts_parses_count():
    with patch("algorithms.deforestation_signals.requests.get",
               return_value=_resp({"data": [{"count": 4200}]})):
        assert fetch_deforestation_alerts("BRA", "fakekey") == 4200


def test_fetch_deforestation_alerts_network_error_returns_none():
    with patch("algorithms.deforestation_signals.requests.get", side_effect=Exception("blocked")):
        assert fetch_deforestation_alerts("BRA", "fakekey") is None


def test_fetch_deforestation_alerts_non_200_returns_none():
    with patch("algorithms.deforestation_signals.requests.get", return_value=_resp({}, status=403)):
        assert fetch_deforestation_alerts("BRA", "badkey") is None


def test_compute_country_flags_direct_forest_loss():
    with patch("algorithms.deforestation_signals.requests.get",
               return_value=_resp({"data": [{"count": 4200}]})):
        result = compute_country_deforestation("BRA", api_key="fakekey")
    assert result["data_available"] is True
    assert result["deforestation_alerts_recent"] == 4200
    assert result["direct_forest_loss"] is True       # 화재 프록시 아닌 직접 탐지
    assert result["is_leading_indicator"] is True
    assert 0 <= result["deforestation_pressure"] <= 100


def test_compute_country_no_key_flags_unavailable(monkeypatch):
    monkeypatch.delenv("GFW_API_KEY", raising=False)
    result = compute_country_deforestation("BRA")
    assert result["data_available"] is False
    assert "GFW_API_KEY" in result["reason"]


def test_compute_country_unexpected_response_falls_back_not_fake(monkeypatch):
    """★ 실수 방지 핵심 — GFW 응답 형태가 예상과 다르면 가짜 숫자를 만들지 않고
    data_available=False로 정직하게 떨어져야 함."""
    monkeypatch.setenv("GFW_API_KEY", "fakekey")
    with patch("algorithms.deforestation_signals.requests.get",
               return_value=_resp({"unexpected": "shape"})):
        result = compute_country_deforestation("BRA")
    assert result["data_available"] is False


def test_compute_country_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        compute_country_deforestation("ZZZ", api_key="fakekey")


def test_hong_kong_excluded_rest_of_tier1_present():
    assert "HKG" not in GFW_COUNTRIES
    from algorithms.country_risk import COUNTRIES
    for iso3 in COUNTRIES:
        if iso3 == "HKG":
            continue
        assert iso3 in GFW_COUNTRIES, f"{iso3} 누락"


def test_deforestation_signals_all_sorts_and_flags(monkeypatch):
    monkeypatch.setenv("GFW_API_KEY", "fakekey")

    def _side_effect(url, *a, **k):
        # 브라질만 큰 산림손실, 나머지는 0
        iso = k["params"]["sql"].split("iso = '")[1][:3]
        count = 4200 if iso == "BRA" else 0
        return _resp({"data": [{"count": count}]})

    with patch("algorithms.deforestation_signals.requests.get", side_effect=_side_effect):
        result = deforestation_signals_all()

    assert result["configured"] is True
    assert result["data_source"].startswith("Global Forest Watch")
    assert "배포 환경에서 확인" in result["disclaimer"]  # 라이브 미검증 정직하게 명시
    available = [c for c in result["countries"] if c.get("data_available")]
    scores = [c["deforestation_pressure"] for c in available]
    assert scores == sorted(scores, reverse=True)

"""국제무역 선행지표(Phase 42) — Comtrade 응답 파싱·급증배율 계산·정직성 플래그가
맞는지 확인. 실제 Comtrade 호출은 mock(외부 API·유료키 필요라 라이브 검증 불가)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

import pytest

from algorithms.comtrade_signals import (
    fetch_import_series, _surge_ratio, _recent_periods,
    compute_country_trade_signal, trade_signals_all,
    UN_M49_CODES, HS_CODES,
)


def _fake_json_resp(data, status=200):
    m = MagicMock(status_code=status)
    m.json.return_value = {"data": data}
    return m


def test_recent_periods_returns_n_months_descending():
    periods = _recent_periods(3, lag_months=2)
    assert len(periods) == 3
    assert all(len(p) == 6 for p in periods)  # YYYYMM
    assert periods[0] > periods[1] > periods[2]


def test_fetch_import_series_aggregates_by_period():
    rows = [
        {"period": "202601", "primaryValue": 100.0},
        {"period": "202601", "primaryValue": 50.0},  # 같은 달 여러 행 합산
        {"period": "202602", "primaryValue": 300.0},
    ]
    with patch("algorithms.comtrade_signals.requests.get", return_value=_fake_json_resp(rows)):
        series = fetch_import_series("KOR", "902000", "fakekey")
    assert series == [150.0, 300.0]  # 과거→최신 순


def test_fetch_import_series_empty_data_returns_empty_list():
    with patch("algorithms.comtrade_signals.requests.get", return_value=_fake_json_resp([])):
        assert fetch_import_series("KOR", "902000", "fakekey") == []


def test_fetch_import_series_http_error_returns_none():
    with patch("algorithms.comtrade_signals.requests.get", return_value=_fake_json_resp([], status=401)):
        assert fetch_import_series("KOR", "902000", "badkey") is None


def test_fetch_import_series_network_error_returns_none():
    with patch("algorithms.comtrade_signals.requests.get", side_effect=Exception("blocked")):
        assert fetch_import_series("KOR", "902000", "fakekey") is None


def test_fetch_import_series_unknown_country_returns_none():
    assert fetch_import_series("ZZZ", "902000", "fakekey") is None


def test_surge_ratio_basic_math():
    assert _surge_ratio([100.0, 100.0, 100.0, 300.0]) == 3.0
    assert _surge_ratio([50.0, 150.0, 100.0]) == 1.0  # 최신 100 / 평균(50,150)=100


def test_surge_ratio_insufficient_data_returns_none():
    assert _surge_ratio([]) is None
    assert _surge_ratio([100.0]) is None


def test_surge_ratio_zero_baseline_returns_none():
    assert _surge_ratio([0.0, 0.0, 500.0]) is None


def test_compute_country_trade_signal_no_key_flags_unavailable(monkeypatch):
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    result = compute_country_trade_signal("KOR")
    assert result["data_available"] is False
    assert "COMTRADE_API_KEY" in result["reason"]


def test_compute_country_trade_signal_unknown_country_raises_keyerror():
    with pytest.raises(KeyError):
        compute_country_trade_signal("ZZZ", api_key="fakekey")


def test_compute_country_trade_signal_flags_honesty(monkeypatch):
    rows = [
        {"period": "202601", "primaryValue": 100.0},
        {"period": "202602", "primaryValue": 100.0},
        {"period": "202603", "primaryValue": 500.0},
    ]
    with patch("algorithms.comtrade_signals.requests.get", return_value=_fake_json_resp(rows)):
        result = compute_country_trade_signal("KOR", api_key="fakekey")

    assert result["data_available"] is True
    assert result["import_values_measured"] is True          # 수입액은 실측
    assert result["is_proxy_for_preparedness"] is True         # '대비 행동'은 추론
    assert result["is_leading_indicator"] is True
    assert result["reporting_lag_months"] >= 1                 # 실시간 아님을 명시
    assert result["max_surge_ratio"] == 5.0                    # 500 / mean(100,100)


def test_compute_country_trade_signal_all_products_fail_marks_unavailable(monkeypatch):
    with patch("algorithms.comtrade_signals.requests.get", side_effect=Exception("blocked")):
        result = compute_country_trade_signal("KOR", api_key="fakekey")
    assert result["data_available"] is False
    assert "Comtrade 조회 실패" in result["reason"]


def test_all_tier1_countries_covered_except_hkg():
    from algorithms.country_risk import COUNTRIES
    for iso3 in COUNTRIES:
        if iso3 == "HKG":
            continue
        assert iso3 in UN_M49_CODES, f"{iso3} 누락"


def test_hs_codes_cover_masks_gloves_diagnostics():
    assert set(HS_CODES) == {"masks_breathing", "surgical_gloves", "diagnostic_reagents"}


def test_trade_signals_all_sorts_and_flags_configured(monkeypatch):
    monkeypatch.setenv("COMTRADE_API_KEY", "fakekey")

    def _side_effect(url, params=None, **kwargs):
        # KOR만 급증, 나머지는 평이한 데이터
        if params.get("reporterCode") == UN_M49_CODES["KOR"]:
            rows = [{"period": "202601", "primaryValue": 100.0},
                    {"period": "202602", "primaryValue": 900.0}]
        else:
            rows = [{"period": "202601", "primaryValue": 100.0},
                    {"period": "202602", "primaryValue": 100.0}]
        return _fake_json_resp(rows)

    with patch("algorithms.comtrade_signals.requests.get", side_effect=_side_effect):
        result = trade_signals_all()

    assert result["configured"] is True
    assert result["data_source"].startswith("UN Comtrade")
    assert "지연" in result["disclaimer"]  # 실시간 아님을 명시
    available = [c for c in result["countries"] if c.get("data_available")]
    assert available[0]["country"] == "KOR"  # 급증 국가가 1등

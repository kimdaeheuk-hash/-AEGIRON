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


# ── 키 없는 공개 스캔 (2026-08-23) ────────────────────────────────────────
# 배경: COMTRADE_API_KEY 발급이 번거로워 7/27에 보류했더니, 이 모듈이 완성돼
# 있는데도 프로덕션에서 13개국 전부 data_available=False로 한 달 넘게 죽어 있었다.
# 말라크가 쓰는 인증 불필요 preview 경로를 폴백으로 붙였다.
# 이 경로는 국가 지정이 안 되므로 '전세계를 받아 튀는 곳을 발견'하는 방식이다 —
# 손으로 정한 목록 밖이 안 보이는 게 8/13 KDCA 사고의 원인이었으므로 방향이 맞다.

def _public_resp(rows):
    m = MagicMock(status_code=200)
    m.json.return_value = {"data": rows}
    m.raise_for_status.return_value = None
    return m


def test_fetch_public_month_aggregates_by_iso3():
    """같은 국가의 World 집계행이 여러 개 와도 합산해야 한다."""
    from algorithms.comtrade_signals import fetch_public_month
    rows = [
        {"reporterISO": "KOR", "primaryValue": 100.0},
        {"reporterISO": "KOR", "primaryValue": 50.0},     # 같은 국가 두 번째 조각
        {"reporterISO": "JPN", "primaryValue": 200.0},
    ]
    with patch("algorithms.comtrade_signals.requests.get", return_value=_public_resp(rows)):
        out = fetch_public_month("9020", "202601")
    assert out == {"KOR": 150.0, "JPN": 200.0}


def test_fetch_public_month_survives_one_broken_row():
    """★KDCA 교훈★ 값이 이상한 행 하나가 그 달 전체를 죽이면 안 된다."""
    from algorithms.comtrade_signals import fetch_public_month
    rows = [
        {"reporterISO": "KOR", "primaryValue": "1,296"},   # 쉼표
        {"reporterISO": "JPN", "primaryValue": "-"},       # 못 읽는 값
        {"reporterISO": "BRA", "primaryValue": 300.0},
        {"primaryValue": 999.0},                            # ISO 없음
    ]
    with patch("algorithms.comtrade_signals.requests.get", return_value=_public_resp(rows)):
        out = fetch_public_month("9020", "202601")
    assert out["KOR"] == 1296.0      # 쉼표도 읽는다
    assert "JPN" not in out          # 못 읽은 건 0이 아니라 제외
    assert out["BRA"] == 300.0       # 뒤 항목이 유실되지 않음


def test_fetch_public_month_returns_none_on_error():
    from algorithms.comtrade_signals import fetch_public_month
    m = MagicMock(status_code=200)
    m.json.return_value = {"error": "quota exceeded"}
    m.raise_for_status.return_value = None
    with patch("algorithms.comtrade_signals.requests.get", return_value=m):
        assert fetch_public_month("9020", "202601") is None


def test_fetch_public_series_skips_missing_months_without_zero_filling():
    """★핵심★ 결측 달을 0으로 메우면 가짜 급증이 만들어진다."""
    from algorithms.comtrade_signals import fetch_public_series
    months = [
        {"KOR": 100.0, "JPN": 100.0},
        {"KOR": 100.0, "JPN": 100.0},
        {"KOR": 100.0},                 # JPN 한 달 결측
        {"KOR": 120.0, "JPN": 900.0},   # 최신
    ]
    with patch("algorithms.comtrade_signals.fetch_public_month", side_effect=months):
        out = fetch_public_series("9020", months=4)
    assert out["KOR"] == [100.0, 100.0, 100.0, 120.0]
    # JPN은 결측 달을 건너뛰고 3개만 — 0을 끼워넣었다면 [100,100,0,900]이 되고
    # 기준선 평균이 66.7로 내려가 급증 배율이 13.5배로 부풀려진다(가짜 급증).
    assert out["JPN"] == [100.0, 100.0, 900.0]
    assert 0.0 not in out["JPN"]


def test_fetch_public_series_drops_country_without_enough_history():
    """비교할 과거가 부족하면 급증 배율을 낼 수 없다 — 지어내지 않는다."""
    from algorithms.comtrade_signals import fetch_public_series
    months = [{"KOR": 100.0}, {"KOR": 100.0}, {"KOR": 120.0, "NEW": 500.0}]
    with patch("algorithms.comtrade_signals.fetch_public_month", side_effect=months):
        out = fetch_public_series("9020", months=3)
    assert "KOR" in out
    assert "NEW" not in out          # 최신 달에만 등장 → 제외


def test_global_scan_surfaces_countries_outside_tier1():
    """★이 기능의 존재 이유★ 손으로 정한 목록 밖의 급증을 잡아야 한다."""
    from algorithms.comtrade_signals import global_trade_scan
    series = {
        "MKD": [100.0, 100.0, 410.0],    # Tier-1 밖 — 4.1배
        "KOR": [100.0, 100.0, 105.0],    # Tier-1 안 — 평온
    }
    with patch("algorithms.comtrade_signals.fetch_public_series", return_value=series):
        out = global_trade_scan()

    outside = [s["country_iso3"] for s in out["outside_tier1_surges"]]
    assert "MKD" in outside
    assert "KOR" not in outside          # Tier-1은 이 목록에 안 들어간다
    assert out["top_surges"][0]["country_iso3"] == "MKD"


def test_global_scan_always_declares_incomplete_coverage():
    """'안 잡힘 = 급증 없음'으로 읽히면 없는 안전을 지어내는 것이다."""
    from algorithms.comtrade_signals import global_trade_scan
    with patch("algorithms.comtrade_signals.fetch_public_series",
               return_value={"KOR": [100.0, 100.0, 120.0]}):
        out = global_trade_scan()
    assert out["coverage"]["complete"] is False
    assert "500" in out["coverage"]["note"]
    assert out["is_proxy_for_preparedness"] is True


def test_trade_signals_all_falls_back_to_public_scan_without_key(monkeypatch):
    """★핵심★ 키가 없어도 더 이상 '데이터 없음'으로 죽지 않는다."""
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    with patch("algorithms.comtrade_signals.fetch_public_series",
               return_value={"MKD": [100.0, 100.0, 410.0]}):
        out = trade_signals_all()
    assert out["mode"] == "public_global_scan"
    assert out["data_available"] is True
    assert "COMTRADE_API_KEY" in out["note"]      # 왜 이 모드인지 밝힌다


def test_trade_signals_all_uses_precise_path_when_key_exists(monkeypatch):
    """키가 생기면 국가별 정밀 추적으로 자동 전환된다."""
    monkeypatch.setenv("COMTRADE_API_KEY", "k")
    with patch("algorithms.comtrade_signals.fetch_import_series", return_value=[]):
        out = trade_signals_all()
    assert out.get("mode") != "public_global_scan"
    assert "countries" in out

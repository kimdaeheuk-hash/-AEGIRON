"""무역 스캔이 무엇을 했는지 로그로 말한다 — 09-30 BLZ·AZE 경보가 6시간 사라진 뒤의 빈칸.

## 배경 (2026-09-30 ~ 10-01)

BLZ(79.0점)·AZE(78.0점) 무역 경보가 14:40~21:02 사라졌다가 돌아왔다. 그때 스캔은 로그를
한 줄도 안 남겨서 **데이터가 실제로 변한 것인지, 일부 품목 조회가 실패한 부분 결과가
6시간 캐시된 것인지** 가를 수 없었다. 코드상 후자가 가능하다 — 품목 하나만 성공해도
최상위 `data_available` 이 True 이고 그 결과가 캐시된다.

이 시험은 (1) 실패 사유와 달 단위 진단이 남는지, (2) 그 진단이 줄로 찍히는지, (3) 줄이
**부분 스캔과 캐시 상태를 사실대로** 말하는지, (4) 그 줄이 스케줄러 경로에서 실제로 불리는지를
고정한다. 스캔의 동작은 바뀌지 않았다 — 기존 시험이 그 증거다.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from algorithms import comtrade_signals as cs

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"
MONTH = {"KOR": 100.0, "BLZ": 50.0}


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    cs._SCAN_CACHE.clear()
    monkeypatch.setattr(cs, "_LAST_CALL", {})
    yield
    cs._SCAN_CACHE.clear()


def _fake_month(failing: dict[str, str] | None = None, empty_latest: set[str] | None = None):
    """품목(HS)별로 실패/빈 최신 달을 흉내 낸다. failing={hs: 사유}."""
    failing = failing or {}
    empty_latest = empty_latest or set()
    periods = list(reversed(cs._recent_periods(cs.TRAILING_MONTHS)))
    latest = periods[-1]

    def fake(hs, period, notes=None):
        if hs in failing:
            cs._note_reason(notes, failing[hs])
            return None
        if hs in empty_latest and period == latest:
            return {}
        return dict(MONTH)
    return fake


# ── (1) 실패 사유 ──────────────────────────────────────────────────────

def _http_error(status: int) -> requests.HTTPError:
    resp = MagicMock()
    resp.status_code = status
    return requests.HTTPError(response=resp)


def test_month_records_http_status_and_still_returns_none():
    notes: dict = {}
    r = MagicMock()
    r.raise_for_status.side_effect = _http_error(429)
    with patch.object(cs.requests, "get", return_value=r):
        out = cs.fetch_public_month("9020", "202609", notes=notes)
    assert out is None                              # 반환 계약은 그대로
    assert notes["reasons"] == {"HTTP 429": 1}


def test_month_records_exception_class_when_there_is_no_response():
    notes: dict = {}
    with patch.object(cs.requests, "get", side_effect=requests.ConnectionError("x")):
        assert cs.fetch_public_month("9020", "202609", notes=notes) is None
    assert notes["reasons"] == {"ConnectionError": 1}


def test_month_records_payload_error_and_bad_json():
    notes: dict = {}
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"error": "x"}
    with patch.object(cs.requests, "get", return_value=r):
        assert cs.fetch_public_month("9020", "202609", notes=notes) is None
    r2 = MagicMock()
    r2.raise_for_status.return_value = None
    r2.json.side_effect = ValueError("bad")
    with patch.object(cs.requests, "get", return_value=r2):
        assert cs.fetch_public_month("9020", "202609", notes=notes) is None
    assert notes["reasons"] == {"응답 error": 1, "JSON 파싱": 1}


def test_month_without_notes_behaves_exactly_as_before():
    """notes 는 선택이다 — 안 주면 아무 흔적도 안 남기고 전과 같이 동작한다."""
    with patch.object(cs.requests, "get", side_effect=requests.ConnectionError("x")):
        assert cs.fetch_public_month("9020", "202609") is None


# ── (2) 달 단위 진단 ──────────────────────────────────────────────────

def test_series_notes_count_months_ok_and_empty_without_changing_the_result():
    months = [{"KOR": 100.0}, None, {"KOR": 100.0}, {"KOR": 110.0}, {}, {"KOR": 120.0}]
    notes: dict = {}
    with patch.object(cs, "fetch_public_month", side_effect=months):
        out = cs.fetch_public_series("9020", months=6, notes=notes)
    assert out == {"KOR": [100.0, 100.0, 110.0, 120.0]}     # 결과는 전과 같다
    assert notes["months_total"] == 6
    assert notes["months_ok"] == 5            # None 한 달 제외
    assert notes["months_empty"] == 1         # 응답은 왔는데 국가 0개인 달


def test_empty_latest_month_makes_the_product_unusable_and_notes_say_why():
    """신고가 아직 안 들어온 최신 달이 {} 로 오면 그 품목은 통째로 빈다 — 그 모양을 드러낸다."""
    months = [{"KOR": 100.0}] * 5 + [{}]
    notes: dict = {}
    with patch.object(cs, "fetch_public_month", side_effect=months):
        assert cs.fetch_public_series("9020", months=6, notes=notes) == {}
    assert (notes["months_ok"], notes["months_empty"]) == (6, 1)


def test_series_notes_report_too_few_months():
    notes: dict = {}
    with patch.object(cs, "fetch_public_month", side_effect=[None, None, None, None, {"KOR": 1.0}, {"KOR": 1.0}]):
        assert cs.fetch_public_series("9020", months=6, notes=notes) == {}
    assert (notes["months_total"], notes["months_ok"]) == (6, 2)   # MIN_SERIES_MONTHS=3 미만


# ── (3) 줄이 사실대로 말한다 ───────────────────────────────────────────

def test_clean_scan_line_says_fresh_full_months_and_cached():
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month()):
        cs.global_trade_scan()
    line = cs.trade_scan_line()
    assert line.startswith("🌐 무역 스캔: 새로 조회")
    for label in cs.PUBLIC_HS_CODES:
        assert f"{label} 6/6달 → 2개국" in line
    assert "부분 스캔" not in line
    assert line.endswith("캐시 저장")


def test_09_30_hypothesis_one_failed_product_is_a_partial_scan_that_gets_cached():
    """★09-30 의 모양 그대로★ 한 품목이 통째로 실패해도 스캔은 data_available=True 로 캐시된다.

    이 시험은 **현재 동작을 고정**한다 — 바꾸자는 게 아니라 줄이 그것을 사실대로 말하는지
    본다. 부분 결과를 캐시하지 않기로 하는 날(별개의 결정) 이 시험의 마지막 단언이 바뀐다.
    """
    failing = {cs.PUBLIC_HS_CODES["surgical_gloves"]: "HTTP 503"}
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month(failing=failing)):
        scan = cs.global_trade_scan()
    assert scan["data_available"] is True                       # 한 품목만 실패 → 여전히 True
    assert scan["products"]["surgical_gloves"]["data_available"] is False
    assert cs._SCAN_CACHE                                       # 그리고 캐시됐다

    line = cs.trade_scan_line()
    assert "surgical_gloves 0/6달 → 사용 불가(HTTP 503×6)" in line
    assert "masks_breathing 6/6달 → 2개국" in line
    assert "부분 스캔 1/3" in line
    assert line.endswith("캐시 저장")


def test_empty_latest_month_shows_as_a_partial_scan_with_the_empty_month_named():
    hs = cs.PUBLIC_HS_CODES["masks_breathing"]
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month(empty_latest={hs})):
        cs.global_trade_scan()
    line = cs.trade_scan_line()
    assert "masks_breathing 6/6달(빈 달 1) → 사용 불가" in line
    assert "부분 스캔 1/3" in line


def test_all_failed_scan_is_marked_not_cached():
    failing = {hs: "ConnectionError" for hs in cs.PUBLIC_HS_CODES.values()}
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month(failing=failing)):
        scan = cs.global_trade_scan()
    assert scan["data_available"] is False and not cs._SCAN_CACHE
    line = cs.trade_scan_line()
    assert "부분 스캔 3/3" in line and line.endswith("캐시 안 함")


def test_cache_hit_line_shows_the_age_of_the_cached_scan():
    import time
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month()):
        cs.global_trade_scan()
    cs._SCAN_CACHE["scan:6"] = (time.time() - 217 * 60, cs._SCAN_CACHE["scan:6"][1])
    cs.global_trade_scan()                      # 캐시 적중 — 네트워크 안 탄다
    line = cs.trade_scan_line()
    assert "캐시 217분 전 조회분" in line
    assert "캐시 저장" not in line              # 적중한 호출은 저장하지 않았다


def test_cache_hit_keeps_reporting_the_partial_state_it_is_serving():
    """부분 스캔이 캐시에서 6시간 서빙되는 동안 **매 주기 그 사실이 보인다** — 이게 이 줄의 목적."""
    failing = {cs.PUBLIC_HS_CODES["surgical_gloves"]: "HTTP 503"}
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month(failing=failing)):
        cs.global_trade_scan()
    cs.global_trade_scan()
    line = cs.trade_scan_line()
    assert line.startswith("🌐 무역 스캔: 캐시 ") and "부분 스캔 1/3" in line


def test_stale_call_record_is_not_read_as_this_cycle():
    import time
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month()):
        cs.global_trade_scan()
    line = cs.trade_scan_line(now=time.time() + 3 * 3600)
    assert "이번 주기에는 호출 안 됨" in line


def test_no_call_record_is_said_plainly():
    assert cs.trade_scan_line() == "🌐 무역 스캔: 호출 기록 없음"


def test_missing_diagnostics_are_reported_as_unknown_not_invented():
    """진단이 안 채워진 경로(예: 패치된 fetch)에서 '6/6달'을 지어내지 않는다."""
    with patch.object(cs, "fetch_public_series", return_value={"KOR": [1.0, 1.0, 2.0]}):
        cs.global_trade_scan()
    line = cs.trade_scan_line()
    assert "조회기록 없음" in line and "6/6달" not in line


# ── 스캔의 동작은 안 바뀌었다 ──────────────────────────────────────────

def test_scan_result_keeps_its_old_keys_and_only_adds_fetch():
    with patch.object(cs, "fetch_public_month", side_effect=_fake_month()):
        scan = cs.global_trade_scan()
    for key in ("scan_type", "data_available", "countries_observed", "products", "top_surges",
                "outside_tier1_surges", "multi_product_surges", "coverage", "method"):
        assert key in scan
    for p in scan["products"].values():
        assert set(p) == {"data_available", "countries_observed", "top_surges", "fetch"}


# ── (4) 배선 ──────────────────────────────────────────────────────────

def test_scheduler_path_actually_logs_the_trade_scan_line():
    """★ 만들어만 두고 아무도 안 부르는 층 ★ `_run_alert_cycle` 이 이 줄을 부르고 로그로 보내는지."""
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "_run_alert_cycle")
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "trade_scan_line" for n in ast.walk(fn)), \
        "_run_alert_cycle 이 trade_scan_line 을 부르지 않는다"
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "log"
               and any(isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                       and a.func.id == "trade_scan_line" for a in n.args)
               for n in ast.walk(fn)), "trade_scan_line 의 결과를 collector.log 로 내보내지 않는다"

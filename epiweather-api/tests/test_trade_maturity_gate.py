"""무역 스캔: 덜 찬 최신 달을 빼고 한 달 앞선 달을 최신으로 쓴다 (수리 목록 19번, 2026-10-04).

## 관측 (프로덕션 15:43 UTC, #55 의 달별 행 수 줄)

    🌐 masks_breathing 6/6달[행 78/71/64/57/42/8] → 8개국      (오래된 달 → 최신 달)

최신 달에 신고한 나라가 8곳뿐이라 '최신 달에 있어야 시계열에 남는' 규칙 때문에 후보가 8개국이 됐다.
한 달 앞선 달은 42곳이다. 신고가 늦게 들어오는 만큼 최신 달일수록 덜 차고, 그 정도가 달마다 달라서
무역 경보가 월 경계마다 있다 없다 한다(10-01 BLZ·AZE 도 같은 모양이었을 가능성).

수리: 최신 달의 신고국 수가 앞 달들 중앙값의 절반 미만이면 그 달을 **통째로** 뺀다.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from algorithms import comtrade_signals as cs

PROD_COUNTS = [78, 71, 64, 57, 42, 8]            # 오래된 달 → 최신 달 (프로덕션 관측 그대로)


def _fake_get(counts_by_index, *, surge_iso=None, surge_period_index=None):
    """periods(과거→최신)의 i 번째 달에 counts[i] 개 국가가 신고한 응답을 돌려주는 requests.get 대역."""
    periods = list(reversed(cs._recent_periods(len(counts_by_index))))
    by_period = {p: counts_by_index[i] for i, p in enumerate(periods)}

    def get(url, params=None, **kw):
        n = by_period[params["period"]]
        idx = periods.index(params["period"])
        rows = []
        for i in range(n):
            iso = f"C{i:03d}"
            value = 100.0
            if surge_iso and iso == surge_iso and idx == surge_period_index:
                value = 400.0                           # 평소의 4배
            rows.append({"reporterISO": iso, "primaryValue": value})
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = {"data": rows}
        return r

    return get, periods


def _series(counts, **kw):
    get, periods = _fake_get(counts, **kw)
    notes: dict = {}
    with patch.object(cs.requests, "get", get):
        out = cs.fetch_public_series("9020", months=len(counts), notes=notes)
    return out, notes, periods


# ── 프로덕션 모양 그대로 ─────────────────────────────────────

def test_production_counts_drop_the_thin_latest_month_and_widen_coverage():
    out, notes, periods = _series(PROD_COUNTS)
    assert len(out) == 42                                      # 8개국이 아니라 42개국
    assert notes["latest_period"] == periods[-2]               # 한 달 앞선 달이 최신
    assert notes["immature"] == [{"period": periods[-1], "reporters": 8, "reference": 64}]
    assert all(len(v) == 5 for v in out.values())              # 뺀 달은 시계열에도 안 섞인다


def test_months_ok_still_counts_every_month_that_answered():
    """응답을 받은 달 수는 그대로다 — 덜 찬 달을 뺀 것은 '조회 실패'가 아니다(scan_incomplete 불변)."""
    _, notes, _ = _series(PROD_COUNTS)
    assert (notes["months_total"], notes["months_ok"]) == (6, 6)
    assert cs.scan_incomplete({"products": {"a": {"data_available": True, "fetch": notes}}}) is False


def test_dropped_month_is_not_blended_into_the_surviving_series():
    """뺀 달에만 있던 국가는 결과에 없고, 남은 국가의 마지막 값은 뺀 달 값이 아니다."""
    out, _, _ = _series(PROD_COUNTS)
    assert "C050" not in out and "C041" in out
    assert all(v == [100.0] * 5 for v in out.values())


# ── 경계 ────────────────────────────────────────────────────

def test_exactly_half_of_the_reference_is_kept():
    out, notes, periods = _series([60, 60, 60, 60, 60, 30])    # 30 == 0.5 × 60 → 유지
    assert "immature" not in notes and notes["latest_period"] == periods[-1]
    assert len(out) == 30


def test_just_below_half_is_dropped():
    out, notes, periods = _series([60, 60, 60, 60, 60, 29])
    assert notes["immature"][0]["period"] == periods[-1] and notes["latest_period"] == periods[-2]
    assert len(out) == 60


def test_normal_complete_months_are_untouched():
    out, notes, periods = _series([60, 61, 62, 63, 62, 61])
    assert "immature" not in notes and notes["latest_period"] == periods[-1]


def test_small_reference_is_not_judged():
    """앞 달들의 중앙값이 20곳 미만이면 '덜 찼다'를 말할 근거가 없다 — 그대로 둔다."""
    out, notes, periods = _series([10, 10, 10, 10, 10, 1])
    assert "immature" not in notes and notes["latest_period"] == periods[-1]


def test_empty_latest_month_is_dropped_instead_of_killing_the_product():
    """예전엔 최신 달이 비면 품목 전체가 '사용 불가'였다. 이제 그 달만 빠진다."""
    out, notes, periods = _series([60, 60, 60, 60, 60, 0])
    assert len(out) == 60 and notes["latest_period"] == periods[-2]
    assert notes["immature"][0]["reporters"] == 0


def test_two_thin_months_are_both_dropped():
    out, notes, periods = _series([60, 60, 60, 60, 5, 3])
    assert [d["period"] for d in notes["immature"]] == [periods[-1], periods[-2]]
    assert notes["latest_period"] == periods[-3]


def test_never_drops_below_the_minimum_series_length():
    out, notes, periods = _series([60, 60, 5, 3])              # 4개월 — 3개월은 남긴다
    assert len(notes["immature"]) == 1
    assert notes["latest_period"] == periods[-2]
    assert all(len(v) >= cs.MIN_SERIES_MONTHS for v in out.values())


# ── 전체 경로: 8곳에 못 든 나라의 급증이 경보 후보가 된다 ─────

def _scan(counts, **kw):
    get, periods = _fake_get(counts, **kw)
    cs._SCAN_CACHE.clear()
    with patch.object(cs.requests, "get", get):
        scan = cs.global_trade_scan(use_cache=False)
    cs._SCAN_CACHE.clear()
    return scan, periods


def test_country_outside_the_latest_eight_is_now_visible_to_the_alert():
    """BLZ·AZE 같은 나라 — 8곳에 못 들어서 안 보이던 급증이 후보가 된다(세 품목 모두 4배)."""
    scan, periods = _scan(PROD_COUNTS, surge_iso="C030", surge_period_index=4)
    assert scan["countries_observed"] == 42
    cands = cs.trade_alert_candidates(scan)
    assert [c["source"] for c in cands] == ["trade_surge:C030"]


def test_without_the_gate_that_country_is_invisible(monkeypatch):
    """대조군 — 게이트를 끄면(비율 0) 같은 입력에서 8개국만 남고 경보가 사라진다(수리 전 모양)."""
    monkeypatch.setattr(cs, "MATURITY_MIN_RATIO", 0.0)
    scan, _ = _scan(PROD_COUNTS, surge_iso="C030", surge_period_index=4)
    assert scan["countries_observed"] == 8
    assert cs.trade_alert_candidates(scan) == []


def test_scan_reports_the_effective_period_and_what_it_excluded():
    scan, periods = _scan(PROD_COUNTS)
    assert scan["latest_period"] == periods[-2]
    assert scan["excluded_periods"] == [periods[-1]]
    assert scan["mixed"] is False
    assert scan["effective_lag_months"] == cs._lag_months_of(periods[-2])
    assert scan["effective_lag_months"] > cs.REPORTING_LAG_MONTHS      # 명목 2개월이 아니라 실효 지연
    assert "excluded_periods" in scan["coverage"]["note"]


def test_alert_evidence_states_the_effective_lag_and_the_exclusion():
    scan, periods = _scan(PROD_COUNTS, surge_iso="C030", surge_period_index=4)
    text = " ".join(cs.trade_alert_candidates(scan)[0]["evidence"])
    assert f"지연이 약 {scan['effective_lag_months']}개월" in text
    assert f"최신 달({periods[-1]})은 신고국이 적어 제외" in text
    assert "더 최근 값은 이 경보에 없다" in text


def test_evidence_keeps_the_nominal_lag_when_nothing_was_excluded():
    scan, _ = _scan([60, 61, 62, 63, 62, 61], surge_iso="C030", surge_period_index=5)
    cands = cs.trade_alert_candidates(scan)
    text = " ".join(cands[0]["evidence"])
    assert "제외" not in text
    assert f"지연이 약 {scan['effective_lag_months']}개월" in text


def test_products_with_different_latest_months_are_flagged_not_hidden():
    summary = cs.scan_period_summary({"products": {
        "a": {"data_available": True, "fetch": {"latest_period": "202607"}},
        "b": {"data_available": True, "fetch": {"latest_period": "202606"}},
    }})
    assert summary["mixed"] is True and summary["latest_period"] is None
    assert summary["effective_lag_months"] is None


def test_mixed_scan_adds_a_note_to_the_alert_evidence():
    scan = {"data_available": True, "mixed": True, "excluded_periods": [],
            "multi_product_surges": [{"country_iso3": "XXX", "products": ["a", "b"],
                                       "product_count": 2, "max_surge_ratio": 3.0}]}
    text = " ".join(cs.trade_alert_candidates(scan)[0]["evidence"])
    assert "품목마다 반영한 최신 달이 달라" in text


# ── 로그 줄 ─────────────────────────────────────────────────

def test_scan_line_names_the_excluded_month_and_why():
    scan, periods = _scan(PROD_COUNTS)
    import time
    cs._record_call(scan, scanned_at=time.time(), cache_hit=False, cached=True)
    line = cs.trade_scan_line()
    assert f"최신 {periods[-2]} · {periods[-1]} 제외(8곳<기준 64의 50%)" in line
    assert "→ 42개국" in line


def test_scan_line_has_no_exclusion_note_for_a_full_scan():
    scan, _ = _scan([60, 61, 62, 63, 62, 61])
    import time
    cs._record_call(scan, scanned_at=time.time(), cache_hit=False, cached=True)
    assert "제외(" not in cs.trade_scan_line()


# ── 배선 ────────────────────────────────────────────────────

def test_fetch_public_series_actually_calls_the_gate():
    """만들어만 두고 아무도 안 부르는 층 방지."""
    import ast
    import inspect
    calls = {n.func.id for n in ast.walk(ast.parse(inspect.getsource(cs.fetch_public_series)))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_drop_immature_months" in calls


@pytest.mark.parametrize("ratio", [0.0, 1.0])
def test_extreme_ratios_behave_predictably(monkeypatch, ratio):
    monkeypatch.setattr(cs, "MATURITY_MIN_RATIO", ratio)
    out, notes, periods = _series([60, 60, 60, 60, 60, 59])
    if ratio == 0.0:
        assert "immature" not in notes                         # 절대 안 뺀다
    else:
        assert notes["immature"][0]["period"] == periods[-1]   # 앞 달 중앙값에 못 미치면 뺀다

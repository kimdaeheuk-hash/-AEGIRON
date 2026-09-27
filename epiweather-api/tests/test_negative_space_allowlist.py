"""부정적 공간 감시 — 판정 대상을 '선언한 보고 채널'로 좁혔다.

## 배경 (2026-09-27, 소킹 판정)

소킹 1주일에서 이 층이 거짓 critical 을 **네 번** 냈고 네 번 다 캡틴 폰까지 갔다.
네 번 다 같은 모양이다 — 보고량이 아닌 지표를 '보고 급감'으로 읽었다.

    kdca_weekly_total   새 역학주간 집계가 아직 안 올라온 0
    naver_*_ratio x3    날짜 창이 밀려 기계적으로 재척도
    supply_alert_count  위 재척도의 파생
    social_mpox         평소가 시간당 2.6건이라 0이 정상

★ 결정적인 증거 ★ `MIN_MEANINGFUL_AVG = 2.0` 이 정확히 `social_*` 을 막으려고
있는데(주석에 이름이 적혀 있다) `social_mpox` 의 평균 2.59 가 그걸 넘었다.
**문턱으로는 못 막는다.** 그래서 자격을 선언한 지표만 판정한다.
"""
from __future__ import annotations

import pytest

from algorithms import negative_space as ns
from algorithms.negative_space import (
    MIN_MEANINGFUL_AVG, REPORTING_CHANNELS, RESCALED_METRICS, SEASONAL_METRICS,
    SKIP_RESCALED, SKIP_SEASONAL, SKIP_UNDECLARED, SKIP_UNRELIABLE, UNRELIABLE_METRICS,
    check_negative_space, eligibility, scan_negative_space, summary_line,
)


# ── 소킹에서 폰까지 간 네 건이 이제 판정되지 않는다 ──────────────────

@pytest.mark.parametrize("metric_id", [
    "social_mpox", "social_birdflu", "social_cholera",   # 평소가 작아 0이 정상
    "supply_alert_count",                                # 우리 파이프라인의 파생
    "naver_covid_ratio", "naver_ebola_ratio",            # 재척도되는 관심도
])
def test_the_metrics_that_reached_the_phone_are_no_longer_judged(metric_id):
    ok, _reason = eligibility(metric_id)
    assert ok is False


def test_social_mpox_is_the_proof_that_thresholds_cannot_do_this():
    """평균 2.59 는 MIN_MEANINGFUL_AVG(2.0) 를 넘는다 — 옛 규칙으로는 통과하고
    경보가 났다. 자격 규칙으로는 막힌다. 이 두 줄이 이번 변경의 이유 전체다."""
    assert 2.59 > MIN_MEANINGFUL_AVG
    assert check_negative_space(latest=0, history_avg=2.59)["alert"] is True
    assert eligibility("social_mpox")[0] is False


# ── 남긴 것: 진짜 보고 채널 ─────────────────────────────────────────

@pytest.mark.parametrize("metric_id", [
    "kdca_weekly_total",    # 법정감염병 주간 신고
    "who_afro_items",       # WHO 발병 공고
    "local_news_kw_hits",   # 2014 기니 사례의 현대판
    "japan_idwr_total", "hk_chp_total", "wahis_outbreaks_30d",
])
def test_real_reporting_channels_are_still_judged(metric_id):
    ok, reason = eligibility(metric_id)
    assert ok is True
    assert reason == "판정"


def test_founding_case_still_fires():
    """2014 기니 에볼라의 모양 — 평소 1,600건대에서 0 이 오면 경보다.
    좁힌 것이 이 층을 죽인 게 아님을 고정한다."""
    assert check_negative_space(latest=0, history_avg=1660.0)["alert"] is True
    assert eligibility("local_news_kw_hits")[0] is True


# ── 사유를 지우지 않는다 ────────────────────────────────────────────

def test_specific_reasons_win_over_generic_undeclared():
    """허용목록만 있으면 전부 '미선언'이 된다. 그러면 2026-07-19·09-22 에 왜
    뺐는지가 사라진다 — 더 구체적인 사유를 먼저 돌려준다."""
    assert eligibility("mobility_total_flights") == (False, SKIP_UNRELIABLE)
    assert eligibility("infodengue_casos_total") == (False, SKIP_SEASONAL)
    assert eligibility("naver_flu_ratio") == (False, SKIP_RESCALED)
    assert eligibility("cdc_eid_items") == (False, SKIP_UNDECLARED)


def test_seasonal_channel_stays_declared_but_still_excluded():
    """InfoDengue 는 진짜 보고 채널이라 선언은 유지하고, 계절성 때문에 판정만 막는다.
    선언에서 지워버리면 '계절성을 반영하면 되살릴 수 있다'는 사실이 사라진다."""
    assert "infodengue_casos_total" in REPORTING_CHANNELS
    assert "infodengue_casos_total" in SEASONAL_METRICS
    assert eligibility("infodengue_casos_total")[0] is False


def test_every_declared_channel_says_what_it_is():
    for metric_id, what in REPORTING_CHANNELS.items():
        assert what.strip(), metric_id


def test_declared_channels_are_real_metrics():
    """선언했는데 그런 지표가 없으면 조용히 아무것도 안 한다 — 오타가 곧 감시 구멍이다."""
    from algorithms.signal_metrics import LAYERS
    registered = {m[0] for cfg in LAYERS.values() for m in cfg["metrics"]}
    for metric_id in REPORTING_CHANNELS:
        assert metric_id in registered, metric_id


# ── 거른 것을 조용히 버리지 않는다 ──────────────────────────────────

def test_scan_counts_what_it_skipped_and_why():
    result = scan_negative_space()
    skipped = result.get("skipped")
    assert isinstance(skipped, dict) and skipped
    assert SKIP_UNDECLARED in skipped


def test_summary_line_shows_both_sides():
    line = summary_line({"metrics_checked": 9, "alert_count": 1,
                         "skipped": {SKIP_UNDECLARED: 28, SKIP_SEASONAL: 1}})
    assert "판정 9개" in line and "급감 1건" in line
    assert "미선언 28" in line and "계절성 1" in line


def test_summary_line_without_skips_has_no_empty_tail():
    assert summary_line({"metrics_checked": 3, "alert_count": 0}) == "판정 3개 · 급감 0건"


def test_scan_reads_the_eligibility_function():
    """집합만 만들어두고 스캔이 안 보면 이 리포의 단골 실패다."""
    import ast
    import inspect
    src = inspect.getsource(ns.scan_negative_space)
    names = {n.id for n in ast.walk(ast.parse(src.strip())) if isinstance(n, ast.Name)}
    assert "eligibility" in names


def test_index_is_untouched():
    """★ 지수는 안 건드린다 ★ 막는 건 '감소를 붕괴로 읽는 판정'뿐이고,
    제외된 지표도 GAI 지수에는 그대로 들어간다(#36 과 같은 원칙)."""
    from algorithms.signal_metrics import LAYERS
    registered = {m[0] for cfg in LAYERS.values() for m in cfg["metrics"]}
    for metric_id in list(RESCALED_METRICS) + list(UNRELIABLE_METRICS) + ["social_mpox"]:
        assert metric_id in registered

"""주간·일간 지표의 기준선 오염 (2026-10-19, ④).

운영 관측: 10-19 하수 농도 경보의 '평소 값'이 10:01 137,336 → 12:03 141,075 로 매시간 올랐다.
주간 값이 매시간 다시 기록돼 기준선이 그 값 쪽으로 끌려갔다. 같은 이유로 새 주 값의 이상도가
그 주 안에서 시간마다 저절로 낮아졌다. 고정하는 것:
① 반복을 한 관측으로 접는다 ② 접은 뒤에는 같은 주 안에서 점수·기준선이 변하지 않는다
③ 매시 바뀌는 지표는 접지 않는다 ④ 세 경로(지수·이상 엔진·국가 직접 지표)가 같은 규칙을 쓴다.
"""
from __future__ import annotations

from algorithms import country_risk, gai
from algorithms import signal_metrics as sm


def test_collapse_repeats():
    assert sm.collapse_repeats([1, 1, None, 1, 2, 2, 1]) == [1, 2, 1]
    assert sm.collapse_repeats([None, None]) == []


WEEKS = [100.0, 120.0, 90.0, 110.0, 105.0]


def _hourly(weeks, new_value, hours_into_week):
    """매주 168번 다시 기록된 과거 + 새 주 값이 hours_into_week 번 기록된 상태."""
    series = []
    for w in weeks:
        series += [w] * 168
    return series + [new_value] * hours_into_week


def test_raw_series_score_decays_within_the_week_which_is_the_bug():
    first = gai._anomaly_score(_hourly(WEEKS, 300.0, 1))
    later = gai._anomaly_score(_hourly(WEEKS, 300.0, 100))
    assert later < first, "접지 않으면 값은 그대로인데 점수가 주 안에서 줄어든다(이게 결함)"


def test_collapsed_series_is_stable_within_the_week():
    scores = {h: gai._anomaly_score(sm.collapse_repeats(_hourly(WEEKS, 300.0, h))) for h in (1, 24, 100, 167)}
    assert len(set(scores.values())) == 1, scores
    means = {h: gai._baseline_mean(sm.collapse_repeats(_hourly(WEEKS, 300.0, h))) for h in (1, 100)}
    assert means[1] == means[100] == round(sum(WEEKS) / len(WEEKS), 4), "평소 값이 시간마다 끌려가지 않는다"


def test_slow_metric_list_contains_the_observed_weekly_sources_but_not_hourly_counts():
    for m in ("cdc_nwss_concentration", "kdca_weekly_total", "japan_idwr_total", "wiki_ebola_daily"):
        assert m in sm.SLOW_CADENCE_METRICS
    for m in ("social_ebola", "local_news_kw_hits", "hk_chp_total", "who_afro_items"):
        assert m not in sm.SLOW_CADENCE_METRICS, f"{m} 은 매시 바뀔 수 있다 — 같은 값 반복도 독립 관측"


def test_compute_gai_and_metric_iterator_use_the_collapsed_series(monkeypatch):
    weekly = []
    for w in WEEKS:
        weekly += [w] * 168
    hourly_new = weekly + [300.0] * 50
    seen = {}
    real = gai._anomaly_score

    def spy(series):
        seen.setdefault("calls", []).append(list(series))
        return real(series)

    nwss_layer = {"environmental": {**sm.LAYERS["environmental"]}}
    extractor = next(m[2] for m in sm.LAYERS["environmental"]["metrics"] if m[0] == "cdc_nwss_concentration")
    records = [{"type": "free_sources", "_v": v} for v in hourly_new]
    monkeypatch.setattr(gai, "load_records", lambda: records)
    monkeypatch.setattr(gai, "LAYERS", {"environmental": {
        **nwss_layer["environmental"],
        "metrics": [("cdc_nwss_concentration", "free_sources", lambda r: r["_v"], "cdc")]}})
    monkeypatch.setattr(gai, "_anomaly_score", spy)
    gai.compute_gai()
    assert seen["calls"][0] == WEEKS + [300.0]
    assert extractor is not None

    monkeypatch.setattr(sm, "LAYERS", {"environmental": {
        **nwss_layer["environmental"],
        "metrics": [("cdc_nwss_concentration", "free_sources", lambda r: r["_v"], "cdc")]}})
    (_, _, _, series), = list(sm.iter_metric_series(records))
    assert series == WEEKS + [300.0]


def test_country_direct_weekly_metric_is_collapsed(monkeypatch):
    calls = []
    monkeypatch.setattr(country_risk, "_anomaly_score", lambda s: calls.append(list(s)) or None)
    monkeypatch.setattr(country_risk, "load_records",
                        lambda: [{"type": "free_sources", "_v": v} for v in [5.0] * 10 + [7.0] * 10])
    monkeypatch.setitem(country_risk.DIRECT_METRICS, "JPN", lambda r: r["_v"])
    monkeypatch.setitem(country_risk.DIRECT_METRICS, "HKG", lambda r: r["_v"])
    try:
        country_risk.compute_country_risk("JPN")
    except Exception:
        pass
    try:
        country_risk.compute_country_risk("HKG")
    except Exception:
        pass
    assert calls[0] == [5.0, 7.0], "주간 원천(일본)은 접는다"
    assert calls[1] == [5.0] * 10 + [7.0] * 10, "홍콩 CHP(RSS 항목 수)는 접지 않는다"

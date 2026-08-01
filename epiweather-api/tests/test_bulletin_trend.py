"""적재된 보고서 신호 → 추이 판정. 비교의 정직성 규칙을 고정한다."""
from __future__ import annotations

from algorithms import bulletin_trend as bt


def _row(location: str, date: str, confirmed: float, deaths: float = 0,
         disease: str = "Bundibugyo", iso3: str = "COD") -> dict:
    return {
        "location": location, "signal_date": date, "disease": disease,
        "country_iso3": iso3,
        "raw_text": f"{location} row [confirmed={confirmed:g} deaths={deaths:g}]",
    }


# ── raw_text에서 수치 복원 ────────────────────────────────────────
def test_metrics_parsed_back_from_raw_text():
    got = bt.metrics_from_raw("DRC | 3 262 | 1 437 [confirmed=3262 deaths=1437 cfr=0.441]")
    assert got == {"confirmed": 3262.0, "deaths": 1437.0, "cfr": 0.441}


def test_metrics_absent_when_no_block():
    assert bt.metrics_from_raw("DRC | 3 262 | 1 437") == {}
    assert bt.metrics_from_raw(None) == {}


# ── 시계열 구성 ───────────────────────────────────────────────────
def test_series_sorted_by_date_per_location():
    rows = [_row("DRC", "2026-07-26", 3262), _row("DRC", "2026-05-18", 12),
            _row("Uganda", "2026-07-26", 20, iso3="UGA")]
    series = bt.build_series(rows)
    assert [p["date"] for p in series["DRC"]] == ["2026-05-18", "2026-07-26"]
    assert set(series) == {"DRC", "Uganda"}


def test_series_filters_by_disease():
    rows = [_row("DRC", "2026-07-26", 3262), _row("DRC", "2026-07-26", 40, disease="Cholera")]
    assert len(bt.build_series(rows, disease="Cholera")["DRC"]) == 1


# ── 추이 판정 ─────────────────────────────────────────────────────
def test_single_observation_is_not_assessed():
    """회차 하나로 추이를 말하면 안 된다."""
    out = bt.assess([_row("DRC", "2026-07-26", 3262)])
    result = out["results"][0]
    assert result["assessed"] is False and "2회 이상" in result["reason"]


def test_surge_detected_on_large_weekly_increase():
    rows = [_row("DRC", "2026-07-19", 2000), _row("DRC", "2026-07-26", 3262)]
    result = bt.assess(rows)["results"][0]
    assert result["direction"] == "급증"
    assert result["delta"] == 1262
    assert result["rate"] == round(1262 / 2000, 4)


def test_small_increase_is_not_a_surge():
    """소규모 표본의 흔들림을 급증으로 부르면 경보가 무뎌진다."""
    rows = [_row("Uganda", "2026-07-19", 18, iso3="UGA"),
            _row("Uganda", "2026-07-26", 20, iso3="UGA")]
    result = bt.assess(rows)["results"][0]
    assert result["direction"] == "증가"        # 2명 증가는 급증이 아니다


def test_flat_series_is_stagnant():
    rows = [_row("France", "2026-07-19", 1, iso3="FRA"),
            _row("France", "2026-07-26", 1, iso3="FRA")]
    assert bt.assess(rows)["results"][0]["direction"] == "정체"


def test_decrease_is_called_revision_not_improvement():
    """★핵심★ 누적이 줄어든 건 사례 재분류지 환자가 사라진 게 아니다.
    '감소'로 읽으면 실제로 진행 중인 발병을 호전으로 오독한다."""
    rows = [_row("DRC", "2026-07-19", 3300), _row("DRC", "2026-07-26", 3262)]
    result = bt.assess(rows)["results"][0]
    assert result["direction"] == "재조정"
    assert result["delta"] == -38


def test_span_delta_uses_first_and_latest():
    rows = [_row("DRC", "2026-05-18", 12), _row("DRC", "2026-06-21", 800),
            _row("DRC", "2026-07-26", 3262)]
    result = bt.assess(rows)["results"][0]
    assert result["first"]["value"] == 12 and result["latest"]["value"] == 3262
    assert result["span_delta"] == 3250
    assert result["observations"] == 3
    assert [p["value"] for p in result["series"]] == [12, 800, 3262]


def test_metric_selection_does_not_mix_cumulative_with_weekly():
    """new_ 접두어(주간 신규)는 누적과 다른 지표다 — 섞이면 안 된다."""
    rows = [
        {"location": "DRC", "signal_date": "2026-07-19", "disease": "Bundibugyo",
         "country_iso3": "COD", "raw_text": "r [confirmed=2000 new_confirmed=300]"},
        {"location": "DRC", "signal_date": "2026-07-26", "disease": "Bundibugyo",
         "country_iso3": "COD", "raw_text": "r [confirmed=3262 new_confirmed=567]"},
    ]
    cumulative = bt.assess(rows, metric="confirmed")["results"][0]
    weekly = bt.assess(rows, metric="new_confirmed")["results"][0]
    assert cumulative["latest"]["value"] == 3262
    assert weekly["latest"]["value"] == 567


def test_surging_list_collects_locations():
    rows = [_row("DRC", "2026-07-19", 2000), _row("DRC", "2026-07-26", 3262),
            _row("France", "2026-07-19", 1, iso3="FRA"),
            _row("France", "2026-07-26", 1, iso3="FRA")]
    out = bt.assess(rows)
    assert out["surging"] == ["DRC"] and out["locations_assessed"] == 2

"""관측값 시계열 저장 — 측정/해석 분리 · 같은 값은 확인만 · 못 읽음은 판정 안 함 · 배선 (2026-11-15)."""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms import observation_store as obs

MAIN = Path(__file__).resolve().parents[1] / "main.py"

POLAR = {"regions": [
    {"region": "siberia_yamal",
     "baseline": {"mean_max_c_current": -3.5, "current_days_counted": 10, "reference_period": "2026-11",
                  "anomaly_c": 6.2, "mean_max_c_baseline": -9.7, "baseline_years": 10},
     "thaw": {"data_available": True, "thaw_days_30d": 16, "permafrost_thaw_pressure": 72.0},
     "news": {"status": "ok", "keyword_hits": 5, "item_count": 0},
     "polar_watch_score": 72.0, "watch_grade": True, "yamal_index": {"score": 50.0}},
    {"region": "greenland", "thaw": {"data_available": False, "reason": "Open-Meteo 실패"}},
]}


def test_polar_splits_measured_from_derived_and_marks_unreadable():
    rows = {r["target"]: r for r in obs.rows_polar(POLAR)}
    y = rows["siberia_yamal"]
    assert y["measured"] == {"mean_max_c_current": -3.5, "current_days_counted": 10,
                             "reference_period": "2026-11", "thaw_days_30d": 16, "keyword_hits": 5, "item_count": 0}
    # 이상도·압력·점수는 우리가 계산한 것 → 해석값
    assert y["derived"]["anomaly_c"] == 6.2 and y["derived"]["permafrost_thaw_pressure"] == 72.0
    assert y["derived"]["yamal_index_score"] == 50.0
    assert "anomaly_c" not in y["measured"]
    g = rows["greenland"]
    assert g["status"] == "undetermined" and g["reason"] == "Open-Meteo 실패" and g["measured"] is None


def test_store_same_value_confirms_change_inserts_failure_is_undetermined(isolated_db):
    db = isolated_db
    state = {"temp": -3.5}

    def polar():
        d = {"regions": [{**POLAR["regions"][0],
                          "baseline": {**POLAR["regions"][0]["baseline"], "mean_max_c_current": state["temp"]}}]}
        d["response_cache"] = {"computed_at": "2026-11-15T05:00:00+00:00"}
        return d

    def broken():
        raise RuntimeError("CDC RSS 503")

    s1 = obs.store({"polar": polar, "travel": broken})
    assert s1["polar"] == {"new": 1, "same": 0, "undetermined": 0}
    assert s1["travel"] == {"new": 1, "same": 0, "undetermined": 1}  # 한 층 실패가 다른 층을 막지 않음
    trav = db.observation_history("travel")
    assert trav[0]["target"] == "*" and trav[0]["status"] == "undetermined"
    assert "RuntimeError: CDC RSS 503" in trav[0]["reason"]

    s2 = obs.store({"polar": polar})
    assert s2["polar"]["same"] == 1
    h = db.observation_history("polar", target="siberia_yamal")
    assert len(h) == 1 and h[0]["checks"] == 2
    assert h[0]["observed_at"] == "2026-11-15T05:00:00+00:00"  # 저장본의 계산 시각(지금이 아님)

    state["temp"] = -2.0
    obs.store({"polar": polar})
    h = db.observation_history("polar", target="siberia_yamal")
    assert [r["measured"]["mean_max_c_current"] for r in h] == [-3.5, -2.0]


def test_kill_switch(monkeypatch, isolated_db):
    import main

    monkeypatch.setenv("EPIWEATHER_OBSERVATION_STORE", "off")
    assert main._store_observations() is None


@pytest.mark.parametrize("layer", obs.LAYERS)
def test_every_layer_fetcher_exists(layer):
    import main

    assert layer in main._observation_fetchers()

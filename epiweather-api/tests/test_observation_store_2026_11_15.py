"""관측값 시계열 저장 — 측정/해석 분리 · 같은 값은 확인만 · 못 읽음은 판정 안 함 · 배선 (2026-11-15)."""
from __future__ import annotations

import ast
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


def test_country_layers_never_fill_missing_with_zero():
    land = obs.rows_land({"countries": [
        {"country": "COD", "data_available": False, "reason": "FIRMS 조회 실패 — 값 없음"},
        {"country": "BRA", "data_available": True, "fire_count_recent": 0, "day_range": 7,
         "land_clearing_pressure": 0.0},
    ]})
    by = {r["target"]: r for r in land}
    assert by["COD"]["status"] == "undetermined" and by["COD"]["measured"] is None
    assert by["BRA"]["measured"] == {"fire_count_recent": 0, "day_range": 7}  # 진짜 0 은 0
    clim = obs.rows_climate({"countries": [{"country": "MDG", "data_available": True, "mean_recent_temp_c": 27.7,
                                            "spillover_pressure": 79.1}]})
    assert clim[0]["measured"] == {"mean_recent_temp_c": 27.7}  # 없는 강수량을 만들지 않음
    assert clim[0]["derived"] == {"spillover_pressure": 79.1}


def test_trade_rows_per_product_and_unavailable_product():
    rows = obs.rows_trade({"data_available": True, "products": {
        "masks_breathing": {"data_available": True, "fetch": {"latest_period": "202608"},
                            "top_surges": [{"country_iso3": "BLZ", "surge_ratio": 3.77,
                                            "monthly_import_usd": [1.0, 2.0]}]},
        "surgical_gloves": {"data_available": False, "reason": "429 반복"},
    }})
    by = {(r["target"], r["metric"]): r for r in rows}
    blz = by[("BLZ", "masks_breathing")]
    assert blz["measured"] == {"monthly_import_usd": [1.0, 2.0], "latest_period": "202608"}
    assert blz["derived"] == {"surge_ratio": 3.77}
    assert by[("*", "surgical_gloves")]["status"] == "undetermined"
    assert obs.rows_trade({"data_available": False, "reason": "키 없음"})[0]["target"] == "*"


def test_travel_notice_id_and_country_read():
    rows = obs.rows_travel({"all_notices": [{
        "level": 4, "headline": "Ebola in the Democratic Republic of the Congo",
        "link": "https://wwwnc.cdc.gov/travel/notices/level4/ebola-drc-provinces", "pub_date": "x"}]})
    assert rows[0]["target"] == "ebola-drc-provinces"
    assert rows[0]["measured"]["level"] == 4
    assert rows[0]["derived"]["countries_read"] == ["COD"]


def test_disaster_dedupes_events():
    w = {"disaster_type": "TC", "alert_level": "red", "disaster_date": "2026-11-01", "title": "Red TC", "disease": "콜레라"}
    rows = obs.rows_disaster({"countries": [{"country_iso3": "IND", "window_count": 2,
                                             "open_windows": [w, {**w, "disease": "뎅기"}]}]})
    assert len(rows[0]["measured"]["events"]) == 1
    assert rows[0]["derived"] == {"open_windows": 2, "window_diseases": ["뎅기", "콜레라"]}


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


def test_summary_line_names_undetermined():
    line = obs.summary_line({"land": {"new": 0, "same": 14, "undetermined": 14}})
    assert line == "🗄 관측 저장: 토지 14(새 0·같음 14·판정 안 함 14)"


def test_history_and_coverage_endpoints(isolated_db):
    from fastapi.testclient import TestClient

    import main

    obs.store({"polar": lambda: POLAR})
    c = TestClient(main.app)
    body = c.get("/api/observations/history?layer=polar&target=siberia_yamal").json()
    assert body["row_count"] == 1 and body["rows"][0]["measured"]["thaw_days_30d"] == 16
    assert "처음 계산된" in body["fields"]["observed_at"]
    assert c.get("/api/observations/history?layer=nope").status_code == 400
    cov = {row["layer"]: row for row in c.get("/api/observations/coverage").json()["layers"]}
    assert cov["polar"]["rows"] == 2 and cov["polar"]["undetermined_rows"] == 1
    assert cov["trade"]["rows"] == 0  # 아직 없으면 0행이라고 말함


def test_kill_switch(monkeypatch, isolated_db):
    import main

    monkeypatch.setenv("EPIWEATHER_OBSERVATION_STORE", "off")
    assert main._store_observations() is None
    assert isolated_db.observation_coverage() == []


def test_wiring_hourly_and_same_cache_keys_as_endpoints():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    fns = {n.name: ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "_after_cycle_bg" in fns["_prewarm_after_cycle"]
    assert "_prewarm_heavy()" in fns["_after_cycle_bg"] and "_store_observations()" in fns["_after_cycle_bg"]
    fetchers = fns["_observation_fetchers"]
    for endpoint, key in (("land_signals", "land-signals"), ("deforestation_signals", "deforestation-signals")):
        assert f"'{key}'" in fetchers
        assert f"response_cache.swr('{key}'" in fns[endpoint]  # 같은 키 → 외부 API 재호출 없음
    # 극지·기후는 2026-11-18 부터 키·ttl 을 모듈 상수로 둔다(Open-Meteo 한도 — 수집기가 같은 키로 넣는다).
    # 같은 상수를 양쪽이 쓰는지, 상수 값이 예전 키 그대로인지 본다.
    from algorithms.climate_signals import CLIMATE_CACHE_KEY
    from algorithms.polar_signals import POLAR_CACHE_KEY
    assert (POLAR_CACHE_KEY, CLIMATE_CACHE_KEY) == ("polar-watch", "climate-signals")
    for endpoint, const in (("polar_watch", "POLAR_CACHE_KEY"), ("climate_signals", "CLIMATE_CACHE_KEY")):
        assert f"response_cache.swr({const}," in fetchers
        assert f"response_cache.swr({const}," in fns[endpoint]
    assert set(obs.EXTRACTORS) == set(obs.LAYERS) == set(obs.SOURCES)


@pytest.mark.parametrize("layer", obs.LAYERS)
def test_every_layer_fetcher_exists(layer):
    import main

    assert layer in main._observation_fetchers()

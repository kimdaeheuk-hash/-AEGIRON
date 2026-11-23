"""발할라 대응제 공백 지도 (2026-11-23).

칸 판정(승인/임상/없음/판정 안 함/검색 불가) · '못 읽음'을 '없음'으로 접지 않기 · 공백 규칙 ·
임상 조회 배선 · API · 등록부 정합성을 네트워크 없이 고정한다.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from algorithms import approved_products as ap
from algorithms import gap_map

PQ = {"records": [{"vaccine_type": "Ebola Zaire (rVSV∆G-ZEBOV-GP, live attenuated)", "manufacturer": "M"},
                  {"vaccine_type": "Yellow Fever", "manufacturer": "M"}]}
FDA = {"by_threat": {"Ebola": {"product_count": 3, "examples": ["ERVEBO"]},
                     "Nipah": {"product_count": 0}, "Marburg": {"product_count": 0}}}


def _t(count, rank=None, phase=None, ok=True):
    if not ok:
        return {"available": False, "reason": "조회 실패: Timeout"}
    return {"available": True, "study_count": count, "furthest_phase": rank, "furthest_phase_ko": phase}


TRIALS = {"by_pathogen": {
    "ebola": {"vaccine": _t(40, 6, "4상(시판 후)"), "therapeutic": _t(10, 5, "3상")},
    "nipah": {"vaccine": _t(3, 2, "1상"), "therapeutic": _t(0)},
    "marburg": {"vaccine": _t(0), "therapeutic": _t(0, ok=False)},
}}


def _row(m, key):
    return next(r for r in m["rows"] if r["key"] == key)


def test_registry_is_consistent():
    keys = [r["key"] for r in gap_map.REGISTRY]
    assert len(keys) == len(set(keys))
    for r in gap_map.REGISTRY:
        assert r["basis"] in gap_map.BASIS_KO
        assert r["fda"] in ap.THREAT_SEARCH_TERMS            # 주간 스냅숏이 실제로 조회한다
    assert set(ap.DOMESTIC_THREAT_TERMS) == set(ap.THREAT_SEARCH_TERMS)


def test_ebola_row_approved_everywhere_it_should_be():
    m = gap_map.build(PQ, FDA, TRIALS)
    c = _row(m, "ebola")["cells"]
    assert c["vaccine"]["status"] == "approved" and c["vaccine"]["label"] == "WHO 사전적격"
    assert c["therapeutic"]["status"] == "clinical" and c["therapeutic"]["label"] == "3상"
    assert c["fda"]["status"] == "approved" and "3종" in c["fda"]["label"]
    assert c["diagnostic"]["status"] == "approved" and c["diagnostic"]["source"].startswith("https://")
    assert c["domestic"]["status"] == "undetermined"
    assert _row(m, "ebola")["countermeasure_gap"] is False


def test_nipah_is_a_countermeasure_gap():
    m = gap_map.build(PQ, FDA, TRIALS)
    r = _row(m, "nipah")
    assert r["cells"]["vaccine"]["status"] == "clinical"          # 1상
    assert r["cells"]["therapeutic"]["status"] == "none"          # 등록 연구 없음
    assert r["cells"]["fda"]["status"] == "none"
    assert r["cells"]["diagnostic"]["status"] == "clinical"       # 'limited' → 제한적
    assert r["countermeasure_gap"] is True
    assert "니파" in m["gap_pathogens"]


def test_failed_lookup_is_undetermined_and_not_counted_as_gap():
    m = gap_map.build(PQ, FDA, TRIALS)
    r = _row(m, "marburg")
    assert r["cells"]["therapeutic"]["status"] == "undetermined"
    assert r["countermeasure_gap"] is False                       # 못 본 칸이 있으면 공백으로 안 센다


def test_missing_snapshots_do_not_become_none():
    m = gap_map.build(None, None, None)
    c = _row(m, "nipah")["cells"]
    assert c["vaccine"]["status"] == "undetermined"
    assert c["therapeutic"]["status"] == "undetermined"
    assert c["fda"]["status"] == "undetermined"
    assert m["gap_count"] == 0


def test_phase4_counts_as_approved_somewhere():
    cell = gap_map._trial_cell(_t(5, 6, "4상(시판 후)"))
    assert cell["status"] == "approved" and "시판 후" in cell["label"]


def test_pathogen_x_is_unsearchable():
    m = gap_map.build(PQ, FDA, TRIALS)
    c = _row(m, "pathogen_x")["cells"]
    assert all(c[k]["status"] == "unsearchable" for k in ("vaccine", "therapeutic", "fda", "diagnostic"))
    assert _row(m, "pathogen_x")["countermeasure_gap"] is False


def test_fetch_trials_asks_vaccine_and_therapeutic_separately_and_survives_failures():
    calls = []

    def fake(query, intr):
        calls.append((query, intr))
        if query == "Nipah Virus":
            raise RuntimeError("boom")
        return _t(1, 3, "2상")
    out = gap_map.fetch_trials(fetch=fake)
    searchable = [r for r in gap_map.REGISTRY if r["ct"]]
    assert out["fetched"] == 2 * len(searchable)
    assert {i for _, i in calls} == {gap_map.VACCINE_INTR, gap_map.THERAPEUTIC_INTR}
    assert out["by_pathogen"]["nipah"]["vaccine"]["available"] is False
    assert out["by_pathogen"]["ebola"]["vaccine"]["furthest_phase"] == 3


def test_api_serves_map(isolated_db, monkeypatch):
    import main
    from algorithms import response_cache, valhalla_watch
    response_cache.clear()
    monkeypatch.setattr(valhalla_watch, "_load_state", lambda: {"gap_trials": {
        "fetched_at": "2026-11-23T00:00:00+00:00", "value": TRIALS}})
    body = TestClient(main.app).get("/api/valhalla/gap-map").json()
    assert body["pathogen_count"] == len(gap_map.REGISTRY)
    assert {"vaccine", "therapeutic", "fda", "diagnostic", "domestic"} <= set(body["rows"][0]["cells"])
    assert "원문" in body["sources"]["registry"]


def test_summary_line_counts_gaps_and_undetermined():
    m = gap_map.build(PQ, FDA, TRIALS, 3.0)
    line = gap_map.summary_line(m)
    assert line.startswith(f"🗺 공백 지도: {len(gap_map.REGISTRY)}개 중 공백 1개(니파)")
    assert "판정 안 함 칸" in line and "임상 3.0시간 전 값" in line

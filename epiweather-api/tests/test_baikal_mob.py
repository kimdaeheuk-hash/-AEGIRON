"""BAIKAL MOB — 상태변화 엔진 시험 (2026-11-22 재구현).

판정(엔진별 상태) · 전이(바뀐 순간만) · 영향(온톨로지 간선) · 저장 · API · 수집 주기 배선을
네트워크 없이 고정한다. 서열 스크리너 응답 확인은 스텁으로 대신한다.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib

import pytest
from fastapi.testclient import TestClient

from algorithms import baikal, ontology

T0 = dt.datetime(2026, 11, 22, 12, 0, tzinfo=dt.timezone.utc)
OK_PROBE = lambda seq: {"ok": True}  # noqa: E731

GOOD = {
    "polar_regions_total": 8, "polar_regions_with_weather": 8, "polar_failure_reasons": {},
    "genomic_variants": {"/ncov": {"available": True, "label": "SARS-CoV-2",
                                   "dominant_clade": "25C", "dominant_share": 0.57}},
    "variant_ledger_ok": True,
    "valhalla": {"pipeline": {"refreshed": True, "reason": None}},
}


def _with(**kw):
    r = {k: (dict(v) if isinstance(v, dict) else v) for k, v in GOOD.items()}
    r.update(kw)
    return r


# ── 온톨로지: 간선은 실제 노드만 잇는다 ────────────────────────────
def test_ontology_edges_connect_known_nodes_and_order_is_complete():
    assert set(ontology.NODE_ORDER) == set(ontology.NODES)
    for e in ontology.EDGES:
        assert e["from"] in ontology.NODES and e["to"] in ontology.NODES
        assert e["wired_at"]  # 연결이 일어나는 코드 자리를 반드시 적는다


def test_variant_to_valhalla_edge_is_really_wired_in_match_ledger():
    """온톨로지가 주장하는 헤임달→발할라 연결이 코드에 실제로 있는지(지어낸 간선 방지)."""
    src = (pathlib.Path(__file__).resolve().parents[1] / "algorithms" / "match_ledger.py").read_text(
        encoding="utf-8")
    assert "variant_flag" in src and "variant_ledger" in src


# ── 엔진별 판정 ───────────────────────────────────────────────────
def test_all_good_is_ok_everywhere():
    snap = baikal.observe(GOOD, None, now=T0, screener_probe=OK_PROBE)
    assert {k: n["status"] for k, n in snap["nodes"].items()} == {k: "ok" for k in ontology.NODES}
    assert snap["impacts"] == []


def test_polar_quota_exhausted_is_down_with_plain_reason():
    r = _with(polar_regions_with_weather=0,
              polar_failure_reasons={"HTTP 429 · Daily API request limit exceeded": 8})
    n = baikal.judge_polar(r)
    assert n["status"] == "down"
    assert "0/8" in n["reason"] and "한도 초과" in n["reason"]


def test_polar_partial_weather_is_degraded_and_missing_result_is_undetermined():
    assert baikal.judge_polar(_with(polar_regions_with_weather=5))["status"] == "degraded"
    r = {k: v for k, v in GOOD.items() if not k.startswith("polar")}
    assert baikal.judge_polar(r)["status"] == "undetermined"   # 못 본 것은 정상이 아니다
    assert baikal.judge_polar(_with(polar_error="TypeError: x"))["status"] == "down"


def test_variants_states():
    assert baikal.judge_heimdall_variants(_with(genomic_variants_error="Timeout"))["status"] == "down"
    assert baikal.judge_heimdall_variants(_with(variant_ledger_ok=False))["status"] == "degraded"
    no_data = {"/ncov": {"available": True, "label": "x", "dominant_share": None}}
    assert baikal.judge_heimdall_variants(_with(genomic_variants=no_data))["status"] == "undetermined"
    gone = {"/ncov": {"available": False, "label": "x", "reason": "HTTP 503"}}
    n = baikal.judge_heimdall_variants(_with(genomic_variants=gone))
    assert n["status"] == "down" and "HTTP 503" in n["reason"]
    assert baikal.judge_heimdall_variants({})["status"] == "undetermined"


def test_screener_probe_is_response_check_not_accuracy():
    ok = baikal.judge_heimdall_screener(OK_PROBE)
    assert ok["status"] == "ok" and "정확도" in ok["scope_ko"] and "개발 중" in ok["note"]

    def boom(seq):
        raise RuntimeError("x")
    assert baikal.judge_heimdall_screener(boom)["status"] == "down"
    assert baikal.judge_heimdall_screener(lambda s: {"ok": False})["status"] == "down"


def test_screener_probe_runs_against_the_real_engine():
    assert baikal.judge_heimdall_screener()["status"] == "ok"


def test_valhalla_states():
    assert baikal.judge_valhalla(_with(valhalla_error="KeyError"))["status"] == "down"
    assert baikal.judge_valhalla({})["status"] == "undetermined"
    stale = {"pipeline": {"refreshed": False, "reason": "갱신 실패", "age_hours": 30}}
    assert baikal.judge_valhalla(_with(valhalla=stale))["status"] == "degraded"


def test_collector_notes_a_gap_without_inventing_a_bad_state():
    n = baikal.judge_collector((T0 - dt.timedelta(hours=5)).isoformat(), T0)
    assert n["status"] == "ok" and "공백" in n["note"]
    assert "note" not in baikal.judge_collector((T0 - dt.timedelta(hours=1)).isoformat(), T0)


# ── 전이 · 언제부터 · 영향 ─────────────────────────────────────────
def test_first_observation_is_observation_start_not_a_change():
    snap = baikal.observe(GOOD, None, now=T0, screener_probe=OK_PROBE)
    assert all(t["from_status"] is None for t in snap["transitions"])
    assert len(snap["transitions"]) == len(ontology.NODES)


def test_only_changes_are_recorded_and_since_carries_over():
    s1 = baikal.observe(GOOD, None, now=T0, screener_probe=OK_PROBE)
    s2 = baikal.observe(GOOD, s1, now=T0 + dt.timedelta(hours=1), screener_probe=OK_PROBE)
    assert s2["transitions"] == []
    assert s2["nodes"]["POLAR"]["since"] == s1["observed_at"]

    down = _with(polar_regions_with_weather=0)
    s3 = baikal.observe(down, s2, now=T0 + dt.timedelta(hours=2), screener_probe=OK_PROBE)
    assert [(t["node"], t["from_status"], t["to_status"]) for t in s3["transitions"]] == [
        ("POLAR", "ok", "down")]
    assert s3["nodes"]["POLAR"]["since"] == s3["observed_at"]
    assert s3["nodes"]["VALHALLA"]["since"] == s1["observed_at"]


def test_impact_follows_ontology_edges_and_does_not_change_downstream_status():
    r = _with(genomic_variants_error="Timeout")
    snap = baikal.observe(r, None, now=T0, screener_probe=OK_PROBE)
    assert snap["nodes"]["VALHALLA"]["status"] == "ok"           # 하류 상태는 그대로
    imp = [(i["from"], i["to"]) for i in snap["impacts"]]
    assert imp == [("HEIMDALL_VARIANTS", "VALHALLA")]
    assert "최신이 아닐 수 있음" in snap["impacts"][0]["note_ko"]


def test_degraded_does_not_propagate():
    snap = baikal.observe(_with(variant_ledger_ok=False), None, now=T0, screener_probe=OK_PROBE)
    assert snap["impacts"] == []


def test_summary_and_transition_lines():
    s1 = baikal.observe(GOOD, None, now=T0, screener_probe=OK_PROBE)
    s2 = baikal.observe(_with(polar_regions_with_weather=0), s1,
                        now=T0 + dt.timedelta(hours=1), screener_probe=OK_PROBE)
    line = baikal.summary_line(s2)
    assert line.startswith("🌊 BAIKAL: 정상 4/5") and "극지 감시 중단" in line
    assert baikal.transition_lines(s2) == [
        "🌊 BAIKAL 전이: 극지 감시 정상 → 중단 — 기상 자료 0/8곳"]
    assert all("관측 시작" in x for x in baikal.transition_lines(s1))


# ── 저장 · API ─────────────────────────────────────────────────────
def test_run_cycle_persists_snapshot_and_transitions(isolated_db):
    baikal.run_cycle(GOOD, now=T0, screener_probe=OK_PROBE)
    baikal.run_cycle(_with(polar_regions_with_weather=0), now=T0 + dt.timedelta(hours=1),
                     screener_probe=OK_PROBE)
    latest = isolated_db.latest_baikal_snapshot()
    assert latest["nodes"]["POLAR"]["status"] == "down"
    rows = isolated_db.list_baikal_transitions(limit=50)
    assert rows[0]["node"] == "POLAR" and rows[0]["to_status"] == "down"
    assert len(rows) == len(ontology.NODES) + 1
    assert [r["node"] for r in isolated_db.list_baikal_transitions(node="POLAR")] == ["POLAR", "POLAR"]


@pytest.fixture()
def client(isolated_db):
    import main
    return TestClient(main.app)


def test_api_without_snapshot_says_so(client):
    body = client.get("/api/baikal").json()
    assert body["observed_at"] is None and body["fresh"] is False and body["nodes"] == []
    assert body["ontology"]["edges"]


def test_api_reports_state_and_staleness(client, isolated_db):
    now = dt.datetime.now(dt.timezone.utc)
    baikal.run_cycle(GOOD, now=now - dt.timedelta(hours=5), screener_probe=OK_PROBE)
    body = client.get("/api/baikal").json()
    assert body["fresh"] is False and "멎었을 수 있음" in body["freshness_note"]
    assert [n["key"] for n in body["nodes"]] == list(ontology.NODE_ORDER)
    assert body["nodes"][0]["status"] == "ok"

    baikal.run_cycle(GOOD, now=now, screener_probe=OK_PROBE)
    body = client.get("/api/baikal").json()
    assert body["fresh"] is True and body["freshness_note"] is None


def test_transitions_api_validates_node(client, isolated_db):
    baikal.run_cycle(GOOD, now=T0, screener_probe=OK_PROBE)
    assert client.get("/api/baikal/transitions?node=POLAR").json()["count"] == 1
    assert client.get("/api/baikal/transitions?node=NOPE").status_code == 400


# ── 배선: 수집 주기가 BAIKAL 을 실제로 부른다 (만들어만 두고 안 부르는 결함 방지) ──
def test_collector_calls_baikal_run_cycle():
    src = (pathlib.Path(__file__).resolve().parents[1] / "collector.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == "collect_free_sources")
    calls = {ast.unparse(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)}
    assert "baikal.run_cycle" in calls

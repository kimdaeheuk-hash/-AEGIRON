"""BAIKAL MOB · YGGDRASIL 시험 (2026-10-19).

캡틴: "온톨로지로 연결하고 피드백 루프로 결과 받고 그 위에 상태변화 시스템(바이칼 몹)을
구축해서 아이기론 생태계의 흐름 상태변화를 저장하고 보여주는 대표 시스템."

이 층이 지켜야 하는 것:
  ① 상태를 지어내지 않는다 — 읽을 값이 없으면 '판정 안 함'이지 '정상'이 아니다.
  ② 온톨로지의 간선은 코드에 있는 흐름만 — VALHALLA 는 경보에 입력되지 않는 독립 축이다.
  ③ 피드백 루프는 판정 0건이면 '측정 대기'(적중률 0% 가 아니다)이고, 기록만 한다.
  ④ 전이는 상태가 바뀐 순간만 남는다. 첫 관측은 '관측 시작'(이전 상태를 지어내지 않는다).
  ⑤ 소킹 중에 들어온 층이라 경보를 절대 막지 않는다 — 예외는 스케줄러에서 삼키고, 끌 수 있다.
  ⑥ 만들어만 두고 아무도 안 부르는 층이 되지 않게 스케줄러 배선을 AST 로 고정한다.
"""
from __future__ import annotations

import ast
import asyncio
import datetime as dt
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("EPIWEATHER_SCHEDULER", "off")

from algorithms import baikal, yggdrasil  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = ROOT / "main.py"
NOW = dt.datetime(2026, 10, 19, 1, 0, tzinfo=dt.timezone.utc)


def _inputs(**over) -> dict:
    """2026-10-18~19 운영 관측과 같은 모양의 입력(소킹 일지 10-18)."""
    base = {
        "health": {
            "total_tracked": 23, "healthy_count": 22, "collector_silent_hours": 0.1,
            "sources": [{"source": "Wikipedia_Ebola", "status": "failing"},
                        {"source": "LocalNews", "status": "ok"}],
            "long_no_data_sources": [],
        },
        "quality": {"invariants": [
            {"key": "llm_reclassify", "label": "LLM 재분류", "last_result": "ok",
             "alarming": False, "consecutive_violations": 0, "alarm_after": 3},
            {"key": "extraction", "label": "구조화 추출", "last_result": "ok",
             "alarming": False, "consecutive_violations": 0, "alarm_after": 3},
        ]},
        "extracted_24h": 4,
        "alerts_today": [
            {"tier": "medium", "score": 79.0, "label": "cdc_nwss_concentration",
             "suppressed": 0, "updated_at": "2026-10-19T00:02:09+00:00", "notified_rank": None},
            {"tier": "low", "score": 63.3, "label": "GTM", "suppressed": 0,
             "updated_at": "2026-10-19T00:02:09+00:00", "notified_rank": None},
        ],
        "predictions": [
            {"predicted_at": "2026-10-17T23:01:23+00:00", "disease": "종합 위험도(GAI 기반)",
             "correct": None, "resolves_by": "2026-11-15"},
            {"predicted_at": "2026-10-02T20:01:19+00:00", "disease": "에볼라",
             "correct": None, "resolves_by": "2026-12-31"},
        ],
        "cycle_record": {
            "type": "free_sources", "timestamp": "2026-10-19T00:01:00",
            "genomic_variants": {"covid": {"available": True, "dominant_share": 0.6,
                                           "label": "코로나", "dominant_clade": "XEC"}},
            "valhalla": {"procurement": {"reason": None}, "pipeline": {"reason": None}},
        },
        "unsealed": 0,
        "scorecard": {"total": 2, "resolved": 0, "correct": 0, "incorrect": 0,
                      "unresolved": 2, "overdue": []},
        "ledger": {"measured_events": 0, "open_crossings": 4, "false_alarms": 0},
        "ground_truth": {"live": 7, "other": 31, "total": 38,
                         "latest_live_event_date": "2026-10-07"},
        "seal_batch": 10,
        "errors": {},
    }
    base.update(over)
    return base


# ── ② YGGDRASIL: 간선은 코드에 있는 흐름만 ──────────────────────

def test_every_relation_connects_known_systems():
    keys = set(yggdrasil.SYSTEM_KEYS)
    assert len(keys) == 7
    for r in yggdrasil.RELATIONS:
        assert r["from"] in keys and r["to"] in keys, r["id"]
        assert r["kind"] in ("data", "feedback")
        assert r["code_path"], f"{r['id']} 에 코드 자리가 없다 — 그럴듯한 간선을 그려 넣지 않는다"


def test_valhalla_sends_no_flow_because_alert_path_never_reads_it():
    """VALHALLA 는 경보 계산에 입력되지 않는 독립 축이다(2026-10-19 확인).

    누가 경보 경로에 발할라를 연결하면 이 시험이 깨져서, 온톨로지에 간선을 추가하라고
    알려 준다 — 그림과 코드가 말없이 갈라지지 않게."""
    assert not [r for r in yggdrasil.RELATIONS if r["from"] == "VALHALLA"]
    assert yggdrasil.isolated_systems() == ["VALHALLA"]
    for name in ("alerts.py", "gai.py", "alert_intervention.py", "country_risk.py"):
        src = (ROOT / "algorithms" / name).read_text(encoding="utf-8").lower()
        assert "valhalla" not in src, (
            f"{name} 이 발할라를 읽기 시작했다 — yggdrasil.RELATIONS 에 VALHALLA 간선을 추가하라")


def test_feedback_edge_is_record_only():
    fb = [r for r in yggdrasil.RELATIONS if r["kind"] == "feedback"]
    assert [r["id"] for r in fb] == ["var-skuld"]
    assert fb[0]["automatic"] is False
    rel = {r["id"]: r for r in yggdrasil.ontology()["relations"]}
    assert rel["var-skuld"]["automatic"] is False
    assert rel["huginn-forseti"]["automatic"] is True


def test_on_request_engines_are_declared_not_claimed_hourly():
    """요청 시에만 도는 엔진을 매시간 가동 중인 것처럼 보이게 하지 않는다."""
    assert "digital_twin" in yggdrasil.system("SKULD")["on_request"]
    assert "evo2_naturalness" in yggdrasil.system("HEIMDALL")["on_request"]
    r = baikal.observe(NOW, _inputs())
    by = {s["key"]: s for s in r["systems"]}
    assert "digital_twin" in by["SKULD"]["on_request"]
    assert "요청 시" in by["SKULD"]["scope_ko"] and "요청 시" in by["HEIMDALL"]["scope_ko"]


def test_jsonld_uses_w3c_vocab_and_does_not_claim_a_domain():
    j = yggdrasil.to_jsonld()
    ctx = j["@context"]
    assert ctx["rdfs"] == "http://www.w3.org/2000/01/rdf-schema#"
    assert ctx["owl"] == "http://www.w3.org/2002/07/owl#"
    assert ctx["ygg"].startswith("urn:"), "실제 도메인을 주장하지 않는다"
    systems = [n for n in j["@graph"] if n.get("@type") == "ygg:System"]
    flows = [n for n in j["@graph"] if n.get("@type") == "ygg:Flow"]
    assert len(systems) == 7 and len(flows) == len(yggdrasil.RELATIONS)
    json.dumps(j, ensure_ascii=False)


# ── ① 상태 판정: 지어내지 않는다 ─────────────────────────────

def test_every_system_carries_status_scope_and_evidence_class():
    r = baikal.observe(NOW, _inputs())
    assert [s["key"] for s in r["systems"]] == list(yggdrasil.SYSTEM_KEYS)
    for s in r["systems"]:
        assert s["status"] in baikal.STATUSES
        assert s["status_ko"] == baikal.STATUS_KO[s["status"]]
        assert s["evidence_class"] in baikal.EVIDENCE_CLASSES
        assert s["scope_ko"], f"{s['key']} 이 무엇을 보고 판정했는지 말하지 않는다"
        assert s["reason"]


def test_missing_inputs_are_undetermined_never_ok():
    """읽을 값이 하나도 없으면 일곱 시스템 전부 '판정 안 함'이다 — 정상이 아니다."""
    empty = {k: None for k in _inputs()}
    empty["errors"] = {}
    r = baikal.observe(NOW, empty)
    assert {s["status"] for s in r["systems"]} == {"undetermined"}
    assert r["summary"]["counts"]["ok"] == 0


def test_huginn_failing_source_degrades_but_no_data_alone_does_not():
    """no_data 는 위키처럼 정상 지연이 잦아 매 주기 저하로 올리면 경보 피로가 된다
    (source_health._status_for 의 같은 판단). 중단(failing)은 저하다."""
    assert baikal.judge_huginn(_inputs()["health"], None)["status"] == "degraded"
    nodata = {"total_tracked": 23, "healthy_count": 22, "collector_silent_hours": 0.1,
              "sources": [{"source": "Wikipedia_Ebola", "status": "no_data"}]}
    res = baikal.judge_huginn(nodata, None)
    assert res["status"] == "ok"
    assert "값없음 Wikipedia_Ebola" in res["reason"], "값없음을 숨기지 않는다"


def test_huginn_long_no_data_and_silent_collector():
    h = {"total_tracked": 23, "healthy_count": 23, "collector_silent_hours": 0.1,
         "sources": [], "long_no_data_sources": [{"source": "LocalNews"}]}
    assert baikal.judge_huginn(h, None)["status"] == "degraded"
    h2 = {**h, "long_no_data_sources": [], "collector_silent_hours": 2.5}
    res = baikal.judge_huginn(h2, None)
    assert res["status"] == "down" and "침묵" in res["reason"]
    assert baikal.judge_huginn({"total_tracked": 0}, None)["status"] == "undetermined"


def test_huginn_follows_quality_layer_alarm_threshold():
    """문턱을 새로 지어내지 않는다 — 품질 층의 alarm_after 를 따른다."""
    h = {"total_tracked": 23, "healthy_count": 23, "collector_silent_hours": 0.1, "sources": []}
    q_under = {"invariants": [{"key": "llm_reclassify", "label": "LLM 재분류",
                               "last_result": "violated", "alarming": False,
                               "consecutive_violations": 1, "alarm_after": 3}]}
    res = baikal.judge_huginn(h, q_under)
    assert res["status"] == "ok" and "위반 1주기째" in res["reason"], "문턱 전 위반도 숨기지 않는다"
    q_over = {"invariants": [{**q_under["invariants"][0], "alarming": True,
                              "consecutive_violations": 3}]}
    assert baikal.judge_huginn(h, q_over)["status"] == "degraded"
    # 추출 불변식은 MIMIR 몫이다 — HUGINN 상태를 바꾸지 않는다.
    q_extr = {"invariants": [{"key": "extraction", "label": "구조화 추출",
                              "last_result": "violated", "alarming": True,
                              "consecutive_violations": 5, "alarm_after": 3}]}
    assert baikal.judge_huginn(h, q_extr)["status"] == "ok"


def test_mimir_states():
    def q(last, alarming=False, streak=0):
        return {"invariants": [{"key": "extraction", "label": "구조화 추출", "last_result": last,
                                "alarming": alarming, "consecutive_violations": streak,
                                "alarm_after": 3}]}
    assert baikal.judge_mimir(q("ok"), 4)["status"] == "ok"
    # 위반 자체가 '48시간 넘게 저장 0건'이라 문턱 전이어도 저하다.
    assert baikal.judge_mimir(q("violated", streak=1), 0)["status"] == "degraded"
    assert baikal.judge_mimir(q("unknown"), None)["status"] == "undetermined"
    assert baikal.judge_mimir(None, None)["status"] == "undetermined"


def test_forseti_empty_table_is_undetermined_not_calm():
    res = baikal.judge_forseti([], NOW)
    assert res["status"] == "undetermined"
    assert "가리지 않는다" in res["reason"]


def test_forseti_retired_rows_on_a_quiet_day_are_not_a_stopped_cycle():
    """★ 작성 중 발견한 거짓 '중단' ★ 내려간 행(suppressed)은 내려간 뒤 updated_at 이 멈춘다.
    오전에 low 하나가 내려간 조용한 날, 표 전체의 최신 시각으로 신선도를 재면 몇 시간 뒤
    '경보 주기 멎음'을 거짓으로 낸다. 활성 행으로만 재야 한다 — 옛 방식이 '중단'이었다는
    사실까지 여기 고정한다."""
    rows = [{"tier": "low", "score": 61.0, "label": "x", "suppressed": 1,
             "updated_at": "2026-10-18T05:00:00+00:00", "notified_rank": None}]
    res = baikal.judge_forseti(rows, NOW)
    assert res["status"] == "undetermined", res
    assert res["status"] != "down"
    assert "활성 경보 없음(내려간 행 1건)" in res["reason"], "의도한 판정 경로를 지나야 한다"
    # 옛 판정(표 전체 최신 시각)이었다면: 20시간 → 중단이었다.
    stale_hours = (NOW - dt.datetime.fromisoformat(rows[0]["updated_at"])).total_seconds() / 3600
    assert stale_hours >= baikal.ALERT_TABLE_STALE_HOURS


def test_forseti_fresh_active_ok_and_stale_active_down():
    fresh = baikal.judge_forseti(_inputs()["alerts_today"], NOW)
    assert fresh["status"] == "ok"
    assert fresh["readings"]["tiers"] == {"medium": 1, "low": 1}
    assert "폰 전송 없음" in fresh["reason"]
    later = NOW + dt.timedelta(hours=3)
    stale = baikal.judge_forseti(_inputs()["alerts_today"], later)
    assert stale["status"] == "down" and "멎음 의심" in stale["reason"]


def test_forseti_reports_highest_tier_actually_sent_to_phone():
    rows = [{"tier": "critical", "score": 95, "label": "a", "suppressed": 0,
             "updated_at": "2026-10-19T00:30:00+00:00", "notified_rank": 3}]
    res = baikal.judge_forseti(rows, NOW)
    assert res["readings"]["phone_sent_highest_tier"] == "critical"
    assert "폰 전송 최고 critical" in res["reason"]


def test_skuld_counts_named_disease_against_unnamed_label():
    from algorithms.country_risk import UNNAMED_DISEASE
    res = baikal.judge_skuld(_inputs()["predictions"], NOW)
    assert res["status"] == "ok"
    assert res["readings"]["named_disease"] == 1
    assert res["readings"]["unnamed_disease"] == 1
    assert _inputs()["predictions"][0]["disease"] == UNNAMED_DISEASE
    assert baikal.judge_skuld([], NOW)["status"] == "undetermined"


def test_heimdall_old_cycle_record_is_not_read_as_now():
    rec = {**_inputs()["cycle_record"], "timestamp": "2026-10-18T18:00:00"}
    res = baikal.judge_heimdall(rec, NOW)
    assert res["status"] == "undetermined" and "지금 상태로 읽지 않음" in res["reason"]
    assert baikal.judge_heimdall(None, NOW)["status"] == "undetermined"


def test_heimdall_partial_and_failed_tracking():
    rec = _inputs()["cycle_record"]
    assert baikal.judge_heimdall(rec, NOW)["status"] == "ok"
    mixed = {**rec, "genomic_variants": {
        "covid": rec["genomic_variants"]["covid"],
        "mpox": {"available": False, "reason": "빌드 갱신 정지", "label": "엠폭스"}}}
    res = baikal.judge_heimdall(mixed, NOW)
    assert res["status"] == "degraded" and "빌드 갱신 정지" in res["reason"]
    none_ok = {**rec, "genomic_variants": {"mpox": mixed["genomic_variants"]["mpox"]}}
    assert baikal.judge_heimdall(none_ok, NOW)["status"] == "down"
    failed = {**rec, "genomic_variants": None}
    assert baikal.judge_heimdall(failed, NOW)["status"] == "down"


def test_valhalla_uses_the_real_stale_parts_rule():
    from algorithms.valhalla_watch import FAILURE_PREFIX
    rec = _inputs()["cycle_record"]
    assert baikal.judge_valhalla(rec, NOW)["status"] == "ok"
    bad = {**rec, "valhalla": {"procurement": {"reason": f"{FAILURE_PREFIX}: 503",
                                               "age_hours": 30},
                               "pipeline": {"reason": None}}}
    res = baikal.judge_valhalla(bad, NOW)
    assert res["status"] == "degraded" and "조달 갱신 실패" in res["reason"]
    assert baikal.judge_valhalla({**rec, "valhalla": None}, NOW)["status"] == "down"


def test_var_seal_backlog():
    i = _inputs()
    ok = baikal.judge_var(0, i["scorecard"], i["ledger"])
    assert ok["status"] == "ok" and "미봉인 없음" in ok["reason"]
    assert baikal.judge_var(10, i["scorecard"], i["ledger"])["status"] == "ok"
    assert baikal.judge_var(11, i["scorecard"], i["ledger"])["status"] == "degraded"
    assert baikal.judge_var(None, i["scorecard"], i["ledger"])["status"] == "undetermined"


def test_var_with_nothing_to_verify_is_not_ok():
    """예측 0건이면 봉인·채점할 대상이 없다 — '정상'이라고 하면 관측보다 많이 주장한다."""
    res = baikal.judge_var(0, {"total": 0, "resolved": 0, "unresolved": 0}, None)
    assert res["status"] == "undetermined" and "검증할 예측 없음" in res["reason"]


# ── ③ 피드백 루프 ─────────────────────────────────────────────

def test_loop_with_zero_resolved_is_awaiting_not_zero_percent():
    i = _inputs()
    loop = baikal.loop_state(i["scorecard"], i["predictions"], i["ground_truth"], NOW.date())
    assert loop["state"] == "awaiting"
    assert "측정 불가" in loop["text"] and "0%가 아니라" in loop["text"]
    assert loop["automatic_feedback"] is False
    assert loop["earliest_due"] == "2026-11-15"
    links = {link["key"]: link for link in loop["links"]}
    assert links["ground_truth"]["live"] == 7 and links["ground_truth"]["other"] == 31
    assert links["predictions"]["named_disease"] == 1


def test_loop_measuring_and_empty():
    sc = {"total": 2, "resolved": 1, "correct": 1, "incorrect": 0, "unresolved": 1, "overdue": []}
    loop = baikal.loop_state(sc, _inputs()["predictions"], None, NOW.date())
    assert loop["state"] == "measuring" and "적중 1" in loop["text"]
    assert baikal.loop_state({"total": 0}, [], None, NOW.date())["state"] == "empty"


def test_loop_earliest_due_skips_resolved_and_past_dates():
    preds = [
        {"correct": 1, "resolves_by": "2026-10-20"},          # 이미 판정됨
        {"correct": None, "resolves_by": "2026-10-01"},       # 지난 기한(overdue 쪽 몫)
        {"correct": None, "resolves_by": "2026-12-01T00:00"},
    ]
    loop = baikal.loop_state({"total": 3, "resolved": 1}, preds, None, NOW.date())
    assert loop["earliest_due"] == "2026-12-01"


# ── ④ 전이: 바뀐 순간만 ───────────────────────────────────────

def test_first_cycle_records_observation_start_without_inventing_prior_state(isolated_db):
    r = baikal.run_cycle(NOW, _inputs())
    subjects = [t["subject"] for t in r["transitions"]]
    assert subjects == list(yggdrasil.SYSTEM_KEYS) + ["LOOP"]
    assert all(t["from_status"] is None for t in r["transitions"])
    assert "관측 시작" in baikal.summary_line(r)
    assert len(isolated_db.list_baikal_transitions(100)) == 8


def test_same_state_adds_snapshot_but_no_transition(isolated_db):
    baikal.run_cycle(NOW, _inputs())
    r2 = baikal.run_cycle(NOW + dt.timedelta(minutes=30), _inputs())
    assert r2["transitions"] == []
    assert "전이 없음" in baikal.summary_line(r2)
    assert len(isolated_db.list_baikal_transitions(100)) == 8
    assert len(isolated_db.list_baikal_snapshots("2026-01-01")) == 2


def test_one_change_is_exactly_one_transition(isolated_db):
    baikal.run_cycle(NOW, _inputs())
    healed = _inputs()
    healed["health"] = {**healed["health"], "healthy_count": 23,
                        "sources": [{"source": "Wikipedia_Ebola", "status": "ok"}]}
    r = baikal.run_cycle(NOW + dt.timedelta(minutes=30), healed)
    assert [(t["subject"], t["from_status"], t["to_status"]) for t in r["transitions"]] == [
        ("HUGINN", "degraded", "ok")]
    assert "HUGINN 저하→정상" in baikal.summary_line(r)


def test_first_scored_prediction_is_a_loop_transition(isolated_db):
    """첫 판정이 나오는 순간 — 이 제품의 논지가 처음 증명되는 자리 — 가 전이로 남는다."""
    baikal.run_cycle(NOW, _inputs())
    scored = _inputs(scorecard={"total": 2, "resolved": 1, "correct": 1, "incorrect": 0,
                                "unresolved": 1, "overdue": []})
    r = baikal.run_cycle(NOW + dt.timedelta(hours=1), scored)
    loop_t = [t for t in r["transitions"] if t["subject"] == "LOOP"]
    assert loop_t and loop_t[0]["from_status"] == "awaiting"
    assert loop_t[0]["to_status"] == "measuring"


def test_old_snapshots_pruned_transitions_kept(isolated_db):
    old = NOW - dt.timedelta(days=40)
    baikal.run_cycle(old, _inputs())
    baikal.run_cycle(NOW, _inputs())
    snaps = isolated_db.list_baikal_snapshots("2000-01-01")
    assert [s["observed_at"] for s in snaps] == [NOW.isoformat()]
    assert len(isolated_db.list_baikal_transitions(100)) == 8, "전이는 감사 기록이라 지우지 않는다"


# ── ⑤ 읽기 전용 · 격리 ───────────────────────────────────────

def test_one_broken_reader_leaves_other_systems_judged(isolated_db, monkeypatch, tmp_path):
    from algorithms import baikal as b

    def boom():
        raise RuntimeError("db locked")
    monkeypatch.setattr(isolated_db, "count_unsealed_predictions", boom)
    monkeypatch.setattr(b, "_latest_cycle_record", lambda: None)
    r = b.observe(NOW)
    by = {s["key"]: s for s in r["systems"]}
    assert by["VAR"]["status"] == "undetermined"
    assert r["read_errors"]["unsealed"] == "RuntimeError"
    assert "db locked" not in json.dumps(r, ensure_ascii=False), "예외 원문은 공개 API 로 안 나간다"
    assert "읽기 실패 unsealed" in b.summary_line({**r, "transitions": []})


def test_cycle_does_not_write_alerts_or_predictions(isolated_db, monkeypatch):
    from algorithms import baikal as b
    monkeypatch.setattr(b, "_latest_cycle_record", lambda: None)
    isolated_db.upsert_alert(dt.date.today().isoformat(), "gai:x", "low", "x", 61.0)

    def counts():
        with isolated_db.get_connection() as c:
            return (tuple(c.execute("SELECT COUNT(*), MAX(updated_at) FROM alerts").fetchone()),
                    c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    before = counts()
    b.run_cycle()
    assert counts() == before


def test_cycle_record_reader_finds_last_free_sources_across_chunk_boundaries(tmp_path):
    p = tmp_path / "signals_log.jsonl"
    lines = [{"type": "free_sources", "timestamp": "2026-10-18T22:00:00", "n": 1},
             {"type": "free_sources", "timestamp": "2026-10-18T23:00:00", "n": 2,
              "pad": "가" * 300},
             {"type": "ai_sources", "timestamp": "2026-10-18T23:30:00", "pad": "x" * 500}]
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n",
                 encoding="utf-8")
    for chunk in (7, 64, 1024 * 1024):
        rec = baikal._latest_cycle_record(p, chunk=chunk)
        assert rec and rec["n"] == 2, chunk
    assert baikal._latest_cycle_record(tmp_path / "none.jsonl") is None


# ── ⑥ 스케줄러 배선 (AST) ────────────────────────────────────

def _fn(name):
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree)
                if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == name)


def _awaited_calls(node) -> list[str]:
    return [n.value.func.id for n in ast.walk(node)
            if isinstance(n, ast.Await) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Name)]


def test_scheduler_runs_baikal_right_after_alert_cycle_every_hour():
    """만들어만 두고 아무도 안 부르는 층이 되지 않게 — 매시간 루프 안에서, 경보 주기
    **뒤에** 부르는지 고정한다(앞에 두면 방금 갱신된 경보 표를 못 본다)."""
    loop_fn = _fn("_scheduler_loop")
    whiles = [n for n in ast.walk(loop_fn) if isinstance(n, ast.While)]
    assert whiles, "매시간 루프가 없다"
    seq = _awaited_calls(whiles[0])
    assert "_run_baikal_cycle" in seq, "매시간 루프가 BAIKAL 을 부르지 않는다"
    assert seq.index("_run_alert_cycle") < seq.index("_run_baikal_cycle")
    # 기동 직후 첫 주기에도.
    assert "_run_baikal_cycle" in _awaited_calls(loop_fn)


def test_baikal_cycle_logs_the_line_and_swallows_errors():
    fn = _fn("_run_baikal_cycle")
    names = {n.func.id for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "summary_line" in names
    logs = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "log"]
    assert logs, "🌊 BAIKAL 줄을 collector.log 로 내보내지 않는다"
    handlers = [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]
    assert handlers, "예외를 삼키지 않으면 BAIKAL 고장이 스케줄러를 죽인다"


def test_baikal_failure_never_breaks_the_scheduler(monkeypatch):
    import collector
    import main
    from algorithms import baikal as b

    def boom(*a, **k):
        raise RuntimeError("baikal exploded")
    errors = []
    monkeypatch.setenv("EPIWEATHER_BAIKAL", "on")
    monkeypatch.setattr(b, "run_cycle", boom)
    monkeypatch.setattr(collector, "log_error", lambda ctx, e: errors.append(ctx))
    asyncio.run(main._run_baikal_cycle())     # 예외가 새어 나오면 여기서 시험이 깨진다
    assert errors == ["scheduler_baikal"]


def test_kill_switch_skips_the_cycle(monkeypatch):
    import main
    from algorithms import baikal as b
    called = []
    monkeypatch.setenv("EPIWEATHER_BAIKAL", "off")
    monkeypatch.setattr(b, "run_cycle", lambda *a, **k: called.append(1))
    asyncio.run(main._run_baikal_cycle())
    assert called == []


# ── API ──────────────────────────────────────────────────────

@pytest.fixture()
def client(isolated_db, monkeypatch):
    from fastapi.testclient import TestClient
    import main
    monkeypatch.setenv("EPIWEATHER_SCHEDULER", "off")
    return TestClient(main.app)


def test_api_before_first_cycle_says_so(client):
    body = client.get("/api/baikal").json()
    assert body["available"] is False and "첫 매시 관측 전" in body["reason"]


def test_api_returns_stored_snapshot_and_transitions(client):
    baikal.run_cycle(NOW, _inputs())
    body = client.get("/api/baikal").json()
    assert body["available"] is True
    assert [s["key"] for s in body["systems"]] == list(yggdrasil.SYSTEM_KEYS)
    assert body["loop"]["state"] == "awaiting"
    assert len(body["transitions"]) == 8
    hist = client.get("/api/baikal/history?hours=24").json()
    assert hist["hours"] == 24


def test_api_ontology_plain_and_jsonld(client):
    plain = client.get("/api/yggdrasil").json()
    assert plain["name"] == "YGGDRASIL" and len(plain["systems"]) == 7
    assert plain["isolated_systems"] == ["VALHALLA"]
    ld = client.get("/api/yggdrasil?format=jsonld").json()
    assert "@context" in ld and "@graph" in ld


# ── 2026-10-19 재검토(캡틴 "다시 검토해봐 — 오류가 있는지")에서 찾은 것 ──────────

def test_forseti_held_rows_only_are_not_a_stopped_cycle():
    """★ 붙들린 행만 남은 날 ★ 무역 스캔·보도 조회가 실패한 주기에 그 계열 행은 내리지 않고
    지난 값 그대로 화면에 남는다(alerts._held, suppressed=0) — upsert 되지 않아 updated_at 이
    멈춘다. 활성 행이 전부 이런 행이고 실패가 두 시간을 넘으면, 경보 주기는 돌았는데
    '멎음 의심'(중단)을 거짓으로 냈다. 옛 판정이 중단이었다는 사실까지 고정한다."""
    from algorithms.alerts import stale_marker
    held = [{"tier": "medium", "score": 78.0, "label": "BLZ (2 품목)", "suppressed": 0,
             "updated_at": "2026-10-18T20:00:00+00:00", "notified_rank": None,
             "evidence": [stale_marker("2026-10-18T20:00:00+00:00"), "근거"]}]
    res = baikal.judge_forseti(held, NOW)
    assert res["status"] == "undetermined", res
    assert "전부 판정 보류" in res["reason"]
    assert res["readings"]["held"] == 1
    # 옛 판정(활성 행 전체의 최신 시각): 5시간 → 중단이었다.
    assert (NOW - dt.datetime.fromisoformat(held[0]["updated_at"])).total_seconds() / 3600 \
        >= baikal.ALERT_TABLE_STALE_HOURS


def test_forseti_one_freshly_saved_row_is_enough_evidence():
    from algorithms.alerts import stale_marker
    rows = [
        {"tier": "medium", "score": 78.0, "label": "BLZ", "suppressed": 0,
         "updated_at": "2026-10-18T20:00:00+00:00", "notified_rank": None,
         "evidence": [stale_marker("2026-10-18T20:00:00+00:00")]},
        {"tier": "medium", "score": 79.0, "label": "NWSS", "suppressed": 0,
         "updated_at": "2026-10-19T00:02:09+00:00", "notified_rank": None, "evidence": ["근거"]},
    ]
    res = baikal.judge_forseti(rows, NOW)
    assert res["status"] == "ok" and res["readings"]["held"] == 1
    assert res["readings"]["tiers"] == {"medium": 2}, "붙들린 행도 화면에 있으니 건수에는 든다"


def test_read_failure_is_never_reported_as_empty():
    """'못 읽음'과 '비어 있음'은 다른 사실이다(honesty-review 3번). 옛 문구는 예측 원장을
    못 읽었을 때 '기록된 예측 없음'이라고 말했다 — 운영에는 36건이 있다."""
    cases = {
        "HUGINN": baikal.judge_huginn(None, None),
        "MIMIR": baikal.judge_mimir(None, None),
        "FORSETI": baikal.judge_forseti(None, NOW),
        "SKULD": baikal.judge_skuld(None, NOW),
    }
    for key, res in cases.items():
        assert res["status"] == "undetermined", key
        assert "못 읽음" in res["reason"], (key, res["reason"])
        assert "비어 있음" not in res["reason"] and "기록 없음" not in res["reason"], key
    # 비어 있는 것은 여전히 비어 있다고 말한다.
    assert "비어 있음" in baikal.judge_forseti([], NOW)["reason"]
    assert "비어 있음" in baikal.judge_skuld([], NOW)["reason"]

    loop = baikal.loop_state(None, None, None, NOW.date())
    assert loop["state"] == "undetermined"
    assert "기록된 예측 없음" not in loop["text"] and "못 읽음" in loop["text"]
    assert baikal.loop_state({"total": 0}, [], None, NOW.date())["state"] == "empty"


def test_unreadable_predictions_end_to_end(isolated_db, monkeypatch):
    from algorithms import baikal as b

    def boom():
        raise RuntimeError("locked")
    monkeypatch.setattr(isolated_db, "list_predictions", boom)
    monkeypatch.setattr(b, "_latest_cycle_record", lambda: None)
    r = b.observe(NOW)
    by = {s["key"]: s for s in r["systems"]}
    assert by["SKULD"]["reason"] == "예측 원장을 못 읽음"
    assert r["loop"]["state"] == "undetermined"
    assert r["read_errors"]["predictions"] == "RuntimeError"


def test_var_unreadable_ledger_never_prints_none():
    i = _inputs()
    res = baikal.judge_var(0, i["scorecard"], None)
    assert res["status"] == "undetermined"
    assert "None" not in res["reason"] and "선행성 원장을 못 읽음" in res["reason"]
    # 관측된 봉인 밀림은 원장 읽기 실패에 가려지지 않는다.
    backlog = baikal.judge_var(25, i["scorecard"], None)
    assert backlog["status"] == "degraded" and "None" not in backlog["reason"]


def test_missing_stage_key_is_undetermined_but_explicit_none_is_down():
    """수집기는 단계가 예외로 실패하면 키를 남기고 값을 None 으로 둔다 — 그건 중단이다.
    키가 아예 없는 기록은 실패가 아니라 모르는 것이다."""
    rec = {"type": "free_sources", "timestamp": "2026-10-19T00:01:00"}
    assert baikal.judge_heimdall(rec, NOW)["status"] == "undetermined"
    assert baikal.judge_valhalla(rec, NOW)["status"] == "undetermined"
    assert baikal.judge_heimdall({**rec, "genomic_variants": None}, NOW)["status"] == "down"
    assert baikal.judge_valhalla({**rec, "valhalla": None}, NOW)["status"] == "down"


def test_api_flags_a_stale_snapshot_instead_of_serving_it_as_now(client):
    """스케줄러가 멈추면 BAIKAL 도 멈추는데 API 는 마지막 스냅숏을 계속 준다. 몇 시간 전의
    '정상'이 지금처럼 읽히지 않게 요청 시점에 나이를 잰다."""
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=10)
    baikal.run_cycle(old, _inputs())
    body = client.get("/api/baikal").json()
    assert body["stale"] is True
    assert body["snapshot_age_minutes"] >= 590
    assert "지금 상태로 읽지 않는다" in body["stale_note"]


def test_api_fresh_snapshot_is_not_stale(client):
    baikal.run_cycle(dt.datetime.now(dt.timezone.utc), _inputs())
    body = client.get("/api/baikal").json()
    assert body["stale"] is False and body["stale_note"] is None
    assert body["snapshot_age_minutes"] <= 1


def test_ontology_names_only_engines_that_exist():
    """없는 엔진을 이름만 걸어 두면 그것도 지어낸 것이다 — 모듈이 사라지거나 이름이 바뀌면 깨진다."""
    for s in yggdrasil.SYSTEMS:
        for name in s["engines"] + s["on_request"]:
            mod = name.split(".")[0]
            assert (ROOT / "algorithms" / f"{mod}.py").exists(), f"{s['key']}: {name} 모듈이 없다"


def test_heimdall_missing_recent_sequences_is_not_a_degradation():
    """★ 프로덕션 첫 관측(2026-10-19 04:00) ★ 수집 로그
    `⏭ Nextstrain 엠폭스: 최근 구간 시퀀스 없음(제출 지연 가능)` 한 줄로 HEIMDALL 이 '저하'로
    나갔다. 조회는 성공했고 아직 판정할 시퀀스가 안 온 것이다 — 고장이 아니다."""
    rec = {"type": "free_sources", "timestamp": "2026-10-19T00:01:00", "genomic_variants": {
        "covid": {"available": True, "dominant_share": 0.54, "label": "SARS-CoV-2(공개시퀀스)",
                  "dominant_clade": "25C (XFG)", "n_recent_sequences": 1510},
        "mpox": {"available": True, "dominant_share": None, "label": "엠폭스",
                 "note": "최근 구간 시퀀스 없음(제출 지연 가능)"},
        "rsv_a": {"available": True, "dominant_share": 1.0, "label": "RSV-A",
                  "dominant_clade": "A.D.3.2", "n_recent_sequences": 1, "new_clade_count": 1},
    }}
    res = baikal.judge_heimdall(rec, NOW)
    assert res["status"] == "ok", res
    assert "엠폭스 판정 불가(최근 구간 시퀀스 없음" in res["reason"], "판정 불가를 숨기지 않는다"
    assert res["readings"]["no_data"] == 1 and res["readings"]["failed"] == 0
    # 전부 데이터 부재면 정상도 저하도 아니다.
    only_gap = {**rec, "genomic_variants": {"mpox": rec["genomic_variants"]["mpox"]}}
    assert baikal.judge_heimdall(only_gap, NOW)["status"] == "undetermined"
    # 진짜 실패가 섞이면 여전히 저하다.
    with_fail = {**rec, "genomic_variants": {**rec["genomic_variants"],
                 "rsv_b": {"available": False, "reason": "Nextstrain API 응답 실패", "label": "RSV-B"}}}
    res2 = baikal.judge_heimdall(with_fail, NOW)
    assert res2["status"] == "degraded" and "RSV-B 실패(Nextstrain API 응답 실패)" in res2["reason"]

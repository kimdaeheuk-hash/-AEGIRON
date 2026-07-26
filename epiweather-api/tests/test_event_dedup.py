"""이벤트 중복제거 — 인수인계서 Part5 ⑩ + 교차언어 의미 클러스터링(㉚).
같은 질병을 보고한 여러 출처는 하나로 병합되고, 다른 질병은 안 섞이는지,
그리고 LLM 클러스터링이 질병명이 문자로 안 겹쳐도 뜻으로 묶는지 확인."""
from __future__ import annotations
import json
from unittest.mock import patch

import anthropic

from algorithms.event_dedup import normalize_disease, dedupe_events, semantic_cluster


def test_normalize_disease_matches_known_aliases():
    assert normalize_disease("에볼라 바이러스(Bundibugyo)") == "에볼라"
    assert normalize_disease("Ebola outbreak in DRC") == "에볼라"
    assert normalize_disease("h5n1 case confirmed") == "조류인플루엔자"
    assert normalize_disease("COVID-19 variant") == "코로나19"


def test_normalize_disease_none_input_returns_none():
    assert normalize_disease(None) is None


def test_normalize_disease_unknown_disease_kept_verbatim():
    """사전에 없는 질병명은 병합하지 않고 원문 유지 — 잘못 합치는 것보다 안전."""
    assert normalize_disease("정체불명 신종질병 X") == "정체불명 신종질병 X"


def _make_signal(dbmod, source, disease, location, signal_type, trust, date, country_iso3=None):
    return dbmod.create_extracted_signal(
        source=source, disease=disease, location=location, signal_type=signal_type,
        severity=["unusual"], symptom=None, transmission=None,
        source_trust=trust, signal_date=date, raw_text=f"{source}: {disease}",
        country_iso3=country_iso3,
    )


def test_multiple_sources_reporting_same_disease_merge_into_one_event(isolated_db):
    _make_signal(isolated_db, "WHO", "에볼라", "DRC", "신규발생", 1.00, "2026-05-16")
    _make_signal(isolated_db, "Wikipedia", "ebola", "DRC", "급증", 0.90, "2026-05-17")
    _make_signal(isolated_db, "Perplexity", "MERS", "Saudi Arabia", "진행중", 0.65, "2026-06-01")

    events = dedupe_events()

    ebola = [e for e in events if e["disease"] == "에볼라"]
    assert len(ebola) == 1
    assert ebola[0]["source_count"] == 2
    assert set(ebola[0]["sources"]) == {"WHO", "Wikipedia"}

    mers = [e for e in events if e["disease"] == "MERS"]
    assert len(mers) == 1
    assert mers[0]["source_count"] == 1


def test_country_iso3_matches_even_with_unaliased_location_text(isolated_db):
    """country_iso3(⑯)가 있으면 location 문구가 별칭 사전에 없어도 국가가 정확히
    태깅돼야 함 — 별칭사전 없이도 전세계 매칭이 되는지 이벤트 병합 단위에서 확인."""
    _make_signal(
        isolated_db, "WHO", "에볼라", "이 문구는 어떤 별칭에도 안 걸림",
        "신규발생", 1.00, "2026-05-16", country_iso3="COD",
    )

    events = dedupe_events()
    ebola = next(e for e in events if e["disease"] == "에볼라")
    assert ebola["countries"] == ["COD"]


def test_merged_score_is_trust_weighted_not_plain_average(isolated_db):
    """출처신뢰도가 다른 두 보고를 병합할 때 단순평균이 아니라 신뢰도가중 평균인지 확인."""
    _make_signal(isolated_db, "WHO", "콜레라", "Yemen", "신규발생", 1.00, "2026-01-01")   # severity 85
    _make_signal(isolated_db, "SNS", "콜레라", "Yemen", "감소", 0.20, "2026-01-02")        # severity 15

    events = dedupe_events()
    cholera = next(e for e in events if e["disease"] == "콜레라")
    # 신뢰도가중 평균이므로 단순평균((85+15)/2=50)보다 신뢰도 높은 WHO(85) 쪽에 훨씬 가까워야 함
    assert cholera["merged_score"] > 50


def test_deterministic_path_flags_clustering_method(isolated_db):
    """api_key 없이 부르면 결정론적(질병명) 방식임이 응답에 명시돼야 함."""
    _make_signal(isolated_db, "WHO", "에볼라", "DRC", "신규발생", 1.0, "2026-05-16")
    events = dedupe_events()
    assert events[0]["clustering_method"] == "disease_name_fallback"


# ── ㉚ 교차언어 의미 클러스터링 ───────────────────────────────


class _FakeBlock:
    def __init__(self, text):
        self.type = "text"; self.text = text


class _FakeResp:
    def __init__(self, payload):
        self.content = [_FakeBlock(json.dumps(payload, ensure_ascii=False))]


def _stub_claude(monkeypatch, payload):
    class _Msgs:
        def create(self, **kw): return _FakeResp(payload)
    class _Client:
        def __init__(self, api_key): self.messages = _Msgs()
    monkeypatch.setattr(anthropic, "Anthropic", _Client)


def test_semantic_cluster_merges_cross_language_same_event(isolated_db, monkeypatch):
    """질병명이 문자로 안 겹치는 두 신호(태국어 정체불명 폐렴 vs 영어 unknown
    pneumonia)를 LLM이 같은 사건으로 묶으면 하나의 이벤트가 돼야 함."""
    s1 = _make_signal(isolated_db, "thai_news", "ปอดอักเสบไม่ทราบสาเหตุ", "ลำปาง",
                      "신규발생", 0.65, "2026-07-01")
    s2 = _make_signal(isolated_db, "reuters", "unknown pneumonia", "northern Thailand",
                      "급증", 0.9, "2026-07-02")
    # Claude가 두 id를 한 클러스터로 반환하도록 스텁
    _stub_claude(monkeypatch, {"clusters": [[s1["id"], s2["id"]]]})

    events = dedupe_events(api_key="fake")
    assert len(events) == 1
    assert events[0]["source_count"] == 2
    assert events[0]["clustering_method"] == "semantic_llm"


def test_semantic_cluster_keeps_distinct_events_separate(isolated_db, monkeypatch):
    s1 = _make_signal(isolated_db, "who", "에볼라", "DRC", "신규발생", 1.0, "2026-05-01")
    s2 = _make_signal(isolated_db, "paho", "뎅기열", "Brazil", "급증", 0.9, "2026-05-02")
    _stub_claude(monkeypatch, {"clusters": [[s1["id"]], [s2["id"]]]})

    events = dedupe_events(api_key="fake")
    assert len(events) == 2


def test_semantic_cluster_llm_failure_falls_back_to_deterministic(isolated_db, monkeypatch):
    """LLM 호출이 실패하면 결정론적 방식으로 폴백하고, 그 사실이 표시돼야 함(회귀 방지)."""
    _make_signal(isolated_db, "who", "에볼라", "DRC", "신규발생", 1.0, "2026-05-01")

    def _boom(api_key):
        raise RuntimeError("api down")
    monkeypatch.setattr(anthropic, "Anthropic", _boom)

    events = dedupe_events(api_key="fake")
    assert events[0]["clustering_method"] == "disease_name_fallback"


def test_semantic_cluster_assigns_omitted_ids_as_solo(isolated_db, monkeypatch):
    """모델이 일부 id를 빠뜨려도 유실 없이 각각 단독 사건으로 배정돼야 함."""
    s1 = _make_signal(isolated_db, "a", "에볼라", "DRC", "신규발생", 1.0, "2026-05-01")
    s2 = _make_signal(isolated_db, "b", "콜레라", "Yemen", "급증", 0.9, "2026-05-02")
    import db as dbmod
    records = dbmod.list_extracted_signals(limit=500)
    # 모델이 s1만 언급, s2 누락
    _stub_claude(monkeypatch, {"clusters": [[s1["id"]]]})
    assignment = semantic_cluster(records, api_key="fake")
    assert s2["id"] in assignment  # 누락된 id도 배정됨
    assert assignment[s1["id"]] != assignment[s2["id"]]  # 서로 다른 클러스터


# ── JRC/EMM 방법론 준용(medoid 대표선정 + 10% 중첩 연속성) ──────────
from algorithms.event_dedup import (
    _medoid, _jaccard, link_clusters, CLUSTER_CONTINUITY_MIN_OVERLAP,
)


def test_medoid_picks_central_signal():
    """medoid = 다른 멤버들과 가장 비슷한(중심에 가까운) 신호."""
    members = [
        {"disease": "dengue", "location": "Brazil Sao Paulo", "raw_text": "dengue surge sao paulo"},
        {"disease": "dengue", "location": "Brazil", "raw_text": "dengue outbreak brazil"},
        {"disease": "measles", "location": "Canada", "raw_text": "measles unrelated far away"},
    ]
    rep = _medoid(members)
    assert rep["disease"] == "dengue"  # 외따로 떨어진 measles는 대표가 아님


def test_medoid_single_member():
    m = [{"disease": "x", "location": "y", "raw_text": "z"}]
    assert _medoid(m) == m[0]
    assert _medoid([]) is None


def test_jaccard_basic():
    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0
    assert _jaccard({"a", "b", "c", "d"}, {"a", "z"}) == 0.2  # 1/5


def test_link_clusters_10pct_continuity_rule():
    """이전 라운드 클러스터와 10% 이상 겹치는 새 클러스터를 연결(JRC 규칙)."""
    prev = [{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, {20, 21, 22}]
    new = [{1, 2, 3, 4, 5, 6, 7, 8, 9, 99}, {50, 51}]  # 첫 클러스터는 prev[0]과 큰 중첩
    mapping = link_clusters(prev, new)
    assert mapping[0] == 0        # 새 클러스터0 → 이전 클러스터0
    assert 1 not in mapping       # 새 클러스터1(50,51)은 아무데도 연결 안 됨


def test_link_clusters_below_threshold_not_linked():
    prev = [{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}]
    new = [{10, 100, 101, 102, 103, 104, 105, 106, 107, 108}]  # 겹침 1/19 < 10%
    assert link_clusters(prev, new) == {}
    assert CLUSTER_CONTINUITY_MIN_OVERLAP == 0.10

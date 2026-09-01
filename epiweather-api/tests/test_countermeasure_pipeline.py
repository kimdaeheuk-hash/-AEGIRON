"""대응제 파이프라인이 **임상시험 수를 준비도로 팔지 않는지** 지킨다 (2026-09-01).

## 왜 만들었나

캡틴: *"발할라를 대규모 업데이트로 가야겠군! 정보가 너무 없어! 국가 바이오
안보 분야로 진입을 해야 국가사업을 할 수 있어!"*

앞서 만든 비축 격차는 **있다/없다 두 칸**뿐이었다. 그런데 "없다" 안에 전혀
다른 상태가 섞여 있었다. 실측(2026-09-01):

    뎅기열    140건 · 4상 시판 중  ← 약은 있는데 비축 체계가 없다
    마버그      9건 · 2상          ← 약 자체가 아직 없다

이 둘의 대응은 완전히 다르다. 앞은 **조달 협상**의 문제이고, 뒤는 **개발
투자**의 문제다. 같은 "비축 없음" 으로 묶으면 예산을 어디에 쓸지 정할 수 없다.

## ★ 이 파일이 막는 것 ★

**연구 수를 준비도로 읽는 것.** 수막구균 372건은 관심의 양이지 물량이 아니다.
그리고 **조회 실패를 "개발 없음" 으로 바꾸는 것.** 등록부가 안 되면 모르는
것이지 없는 것이 아니다 — 군사·기밀 프로그램은 애초에 등재되지 않는다.
"""
from __future__ import annotations

import pytest

from algorithms import countermeasure_pipeline as cp
from algorithms.countermeasure_pipeline import (
    PATHOGEN_QUERIES, fetch_pipeline, readiness_stage,
)
from algorithms.countermeasure_stockpile import ICG_STOCKPILES, KNOWN_GAP_ALIASES


def _study(phases, status="COMPLETED", title="시험"):
    return {"protocolSection": {
        "designModule": {"phases": phases},
        "statusModule": {"overallStatus": status},
        "identificationModule": {"briefTitle": title},
    }}


class _Resp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def _patched(monkeypatch, body):
    monkeypatch.setattr(cp.requests, "get", lambda *a, **k: _Resp(body))


# ── 파이프라인 조회 ────────────────────────────────────────────────────────

def test_furthest_phase_is_the_max_not_the_first(monkeypatch):
    """가장 앞선 단계를 잡는다 — 목록 순서에 끌려가지 않는다."""
    _patched(monkeypatch, {"totalCount": 3, "studies": [
        _study(["PHASE1"]), _study(["PHASE3"]), _study(["PHASE2"]),
    ]})

    out = fetch_pipeline("Marburg")

    assert out["available"] is True
    assert out["furthest_phase_ko"] == "3상"
    assert out["study_count"] == 3


def test_fetch_failure_is_not_no_development(monkeypatch):
    """★★핵심★★ 조회 실패를 '개발 없음' 으로 바꾸지 않는다.

    등록부가 안 되면 **모르는** 것이다. 그걸 0건으로 접으면 네트워크 오류
    하나가 "이 병엔 아무 대응제도 없다" 는 국가 보고로 둔갑한다.
    """
    def boom(*a, **k):
        raise ConnectionError("nope")
    monkeypatch.setattr(cp.requests, "get", boom)

    out = fetch_pipeline("Nipah Virus")

    assert out["available"] is False
    assert "ConnectionError" in out["reason"]
    assert "study_count" not in out, "실패를 건수로 바꿨다"
    assert "furthest_phase" not in out


def test_missing_total_count_is_a_failure_not_a_zero(monkeypatch):
    """응답 형식이 바뀌면 모른다고 한다 — 조용히 0건으로 세지 않는다."""
    _patched(monkeypatch, {"studies": []})

    out = fetch_pipeline("Lassa Fever")

    assert out["available"] is False
    assert "totalCount" in out["reason"]


def test_zero_studies_says_it_is_a_registry_gap(monkeypatch):
    """★핵심★ 0건은 '개발이 없다' 가 아니라 '이 등록부에 없다' 이다."""
    _patched(monkeypatch, {"totalCount": 0, "studies": []})

    out = fetch_pipeline("Nipah Virus")

    assert out["available"] is True
    assert out["study_count"] == 0
    assert out["furthest_phase"] is None
    assert "개발이 없다는 뜻이 아니라" in out["note"]
    assert "군사·기밀" in out["note"], "왜 없을 수 있는지 근거가 빠졌다"


def test_unlabelled_phase_is_not_ranked_as_early(monkeypatch):
    """단계 표기가 없는 연구를 1상으로 승격하지 않는다."""
    _patched(monkeypatch, {"totalCount": 5, "studies": [
        _study([]), _study(["NA"]),
    ]})

    out = fetch_pipeline("Nipah Virus")

    assert out["furthest_phase"] is None
    assert out["furthest_phase_ko"] == "임상 단계 미표기"


# ── 대비 단계 판정 ────────────────────────────────────────────────────────

def test_stockpile_beats_everything():
    """비축이 있으면 임상 현황을 못 봐도 판정은 선다."""
    out = readiness_stage({"available": False, "reason": "조회 실패"}, True)

    assert out["stage"] == "stockpiled"
    assert "충분하다는 뜻은 아니다" in out["meaning"]


def test_no_stockpile_but_approved_is_a_procurement_problem():
    """★핵심★ 뎅기·말라리아 — 약은 있는데 비축이 없다.

    이건 개발 문제가 아니라 **조달 문제**다. 그렇게 말해야 예산이 제 자리로 간다.
    """
    out = readiness_stage(
        {"available": True, "study_count": 140, "furthest_phase": 6,
         "completed_late_phase": 12}, False)

    assert out["stage"] == "approved_path"
    assert "조달" in out["meaning"]


def test_early_trial_is_kept_apart_from_late():
    """★핵심★ 마버그(2상)와 니파(3상)를 같은 칸에 넣지 않는다."""
    early = readiness_stage(
        {"available": True, "study_count": 9, "furthest_phase": 3,
         "completed_late_phase": 0}, False)
    late = readiness_stage(
        {"available": True, "study_count": 6, "furthest_phase": 5,
         "completed_late_phase": 0}, False)

    assert early["stage"] == "early_trial"
    assert late["stage"] == "late_trial"
    assert early["stage"] != late["stage"]


def test_unknown_pipeline_is_not_the_worst_stage():
    """★★핵심★★ 판정 불가를 '등록 연구 없음' 으로 접지 않는다.

    둘을 섞으면 조회가 하루 실패한 병이 최하위 대비 등급으로 보고된다.
    """
    unknown = readiness_stage({"available": False, "reason": "조회 실패: Timeout"}, False)
    none = readiness_stage(
        {"available": True, "study_count": 0, "furthest_phase": None}, False)

    assert unknown["stage"] == "unknown"
    assert none["stage"] == "no_registered_trial"
    assert "Timeout" in unknown["meaning"], "실패 사유를 버렸다"


def test_stage_carries_no_score():
    """★★핵심★★ 점수를 내지 않는다 — '니파 32점' 을 만들지 않는다.

    숫자를 매기면 그 숫자가 문서에 실리고, 우리에겐 그 32 를 설명할 근거가 없다.
    """
    for pipeline, has in [
        ({"available": True, "study_count": 140, "furthest_phase": 6,
          "completed_late_phase": 9}, False),
        ({"available": True, "study_count": 9, "furthest_phase": 3,
          "completed_late_phase": 0}, False),
        ({"available": False, "reason": "x"}, True),
    ]:
        out = readiness_stage(pipeline, has)
        assert set(out) == {"stage", "stage_ko", "meaning"}
        for value in out.values():
            assert not isinstance(value, (int, float)), "단계에 점수가 섞였다"


def test_study_count_does_not_move_the_stage():
    """★★핵심★★ 연구가 372건이어도 단계를 올리지 않는다.

    연구 수는 **관심의 양**이지 물량이 아니다. 수막구균 372건과 니파 6건의
    차이는 세계가 무엇에 돈을 썼는지이지, 우리가 얼마나 준비됐는지가 아니다.
    """
    few = readiness_stage(
        {"available": True, "study_count": 4, "furthest_phase": 3,
         "completed_late_phase": 0}, False)
    many = readiness_stage(
        {"available": True, "study_count": 372, "furthest_phase": 3,
         "completed_late_phase": 0}, False)

    assert few["stage"] == many["stage"] == "early_trial"


# ── 표 정합성 ─────────────────────────────────────────────────────────────

def test_every_watched_pathogen_has_a_query():
    """★핵심★ 비축 표에 있는 병은 전부 임상 현황을 물을 수 있어야 한다.

    하나라도 빠지면 그 병만 조용히 보고에서 사라진다.
    """
    watched = {v["name_ko"] for v in ICG_STOCKPILES.values()} | set(KNOWN_GAP_ALIASES)

    assert watched <= set(PATHOGEN_QUERIES), \
        f"검색어가 없는 병: {sorted(watched - set(PATHOGEN_QUERIES))}"


@pytest.mark.parametrize("ko,query", sorted(PATHOGEN_QUERIES.items()))
def test_queries_are_in_the_registry_language(ko, query):
    """ClinicalTrials.gov 는 영어로만 답한다 — 한글로 물으면 0건이 나온다."""
    assert query.isascii() and query.strip() == query and query

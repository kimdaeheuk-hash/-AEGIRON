"""보고서 신호 → 경보 엔진 연결 통합 검증.

넣어놓고 아무도 안 읽으면 파이프라인이 무의미하다. 이 배선은 조용히 깨지기
쉬운 종류라(스키마 필드명·signal_type 값·country_iso3 유무 중 하나만 어긋나도
집계에서 조용히 빠진다) 실제 DB에 적재해 경보 점수가 오르는지까지 확인한다.

실측(2026-08-01): 적재 전 COD 19.3 → 적재 후 29.8, 케냐는 랭킹에 아예 없다가
27.0으로 자동 편입(tier=auto).
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import country_risk as cr
from algorithms.bulletin_ingest import ingest


def _signal(location: str, disease: str = "Bundibugyo", grade: str = "Grade 3") -> dict:
    return {
        "source": "who_afro_bulletin", "disease": disease, "location": location,
        "grade": grade, "layout": "who_afro_events",
        "metrics": {"total_cases": 1963, "deaths": 719},
        "signal_date": dt.date.today().isoformat(),
        "raw_text": f"{location} | {disease} | 1963 | 719",
        "cross_check": {"checked": True, "numbers_unverified": 0},
    }


@pytest.fixture()
def db_with_bulletin_signals(isolated_db):
    ingest([_signal("DRC"), _signal("Kenya", disease="Cholera", grade="Protracted 3")],
           source="who_afro_bulletin", dbmod=isolated_db)
    return isolated_db


def test_signal_type_ongoing_is_recognized_by_alert_engine():
    """적재 시 쓰는 '진행중'이 경보 엔진의 심각도 표에 실제로 있어야 한다 —
    없으면 기본값 40으로 조용히 떨어진다."""
    assert cr.SIGNAL_TYPE_SEVERITY["진행중"] == 60


def test_ingested_signal_produces_nlp_score(db_with_bulletin_signals):
    """국가별 신호 점수 = 심각도(60) × 신뢰도(0.90) = 54.0."""
    score, count = cr._nlp_raw_score("COD")
    assert count == 1 and score == pytest.approx(54.0, abs=0.1)


def test_iso3_match_works_without_alias_dictionary(db_with_bulletin_signals):
    """케냐는 Tier-1 별칭사전에 없다 — country_iso3만으로 매칭돼야 한다."""
    score, count = cr._nlp_raw_score("KEN")
    assert count == 1 and score is not None


def test_country_without_signal_is_not_matched(db_with_bulletin_signals):
    """신호 없는 나라가 덩달아 점수를 받으면 안 된다."""
    score, count = cr._nlp_raw_score("UGA")
    assert count == 0 and score is None


def test_new_country_is_auto_discovered_into_tier2(db_with_bulletin_signals):
    """★핵심★ 감시 목록에 없던 나라도 신호가 들어오면 랭킹에 편입돼야 한다."""
    assert "KEN" in cr.discovered_tier2_countries()


def test_ingested_signal_raises_country_risk_ranking(db_with_bulletin_signals):
    """실제 랭킹에서 신호 있는 나라가 위로 올라오고 has_signal이 켜져야 한다."""
    ranked = {r["country"]: r for r in cr.rank_countries()["countries"]}
    assert ranked["COD"]["has_signal"] is True
    assert ranked["COD"]["raw_score_components"]["nlp_signal"] == pytest.approx(54.0, abs=0.1)
    assert ranked["KEN"]["coverage_tier"] == "auto"        # 자동 편입 경로로 들어옴
    # 신호 있는 나라가 신호 없는 Tier-1 나라보다 위험도가 높아야 한다
    assert ranked["COD"]["risk_score"] > ranked["UGA"]["risk_score"]


def test_non_disease_events_never_reach_the_alert_engine(isolated_db):
    """사이클론 등은 적재 자체가 안 되므로 경보 점수에도 영향이 없어야 한다."""
    ingest([_signal("DRC", disease="Cyclone Gezani")],
           source="who_afro_bulletin", dbmod=isolated_db)
    score, count = cr._nlp_raw_score("COD")
    assert count == 0 and score is None

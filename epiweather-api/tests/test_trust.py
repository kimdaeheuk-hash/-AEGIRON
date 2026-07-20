"""신뢰도 엔진 — 인수인계서 Part5 ③. 최종점수 = 원시점수 × 출처신뢰도가
실제로 SOURCE_TRUST 테이블 값을 그대로 곱하는지 확인."""
from __future__ import annotations

from algorithms.trust import trust_for, SOURCE_TRUST


def test_trust_for_every_known_category_matches_table():
    for category, expected in SOURCE_TRUST.items():
        assert trust_for(category) == expected


def test_trust_for_unknown_category_falls_back_to_unknown_value():
    assert trust_for("존재하지않는카테고리") == SOURCE_TRUST["unknown"]


def test_who_is_most_trusted_unknown_is_least_trusted():
    assert SOURCE_TRUST["who"] == max(SOURCE_TRUST.values())
    assert SOURCE_TRUST["unknown"] == min(SOURCE_TRUST.values())


def test_official_sources_trusted_more_than_ai_extracted():
    """루머·AI 추출 수치가 1차 공식 데이터와 같은 비중이면 안 됨(설계 원칙)."""
    assert SOURCE_TRUST["who"] > SOURCE_TRUST["ai_extracted"]
    assert SOURCE_TRUST["government"] > SOURCE_TRUST["ai_extracted"]
    assert SOURCE_TRUST["ai_extracted"] > SOURCE_TRUST["prediction_market"]

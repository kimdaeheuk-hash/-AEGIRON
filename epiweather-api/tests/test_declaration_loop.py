"""피드백 루프가 닫힐 수 있게 되었는가 (2026-09-21).

## 왜 이 파일이 있나

캡틴: *"각 엔진들의 온톨로지가 있어야 하고 피드백 루프가 돌아야 아이기론이
동적인 살아있는 게 돼!"*

확인해보니 **루프가 닫힐 수 없는 상태**였다. 끊긴 곳이 셋이다.

    ① 정답 테이블을 채우는 게 손으로 적은 16건뿐 — 최근 선언이 2024-09-27
    ② 예측의 disease 가 "종합 위험도(GAI 기반)" 라 사건 이름과 영원히 불일치
    ③ 예측이 스스로 적어둔 판정기준의 ambiguous 를 채점기가 안 내놓음

채점 조건이 `선언일 > 예측일` 이라 ①만으로도 적중이 불가능했고, 빗나간 예측은
90일 뒤 자동으로 incorrect 가 된다. 그대로 두면 아이기론은 **"측정된 것처럼
보이는 적중률 0%"** 를 스스로 만들어낸다 — 이 제품이 파는 게 그 숫자다.
"""
from __future__ import annotations

import datetime as dt

from algorithms.declaration_ingest import (MIN_TRUST, MILESTONE, SOURCE_TYPE,
                                           eligible, event_name_for, summary)
from algorithms.prediction_resolver import (DECLARATION_MILESTONES, MATCH_COUNTRY,
                                            MATCH_FULL, MATCH_NONE, match_kind)


def _sig(**kw) -> dict:
    base = {"source_trust": MIN_TRUST, "signal_type": "신규발생", "disease": "라싸열",
            "country_iso3": "NGA", "location": "나이지리아", "signal_date": "2026-09-15"}
    return {**base, **kw}


# ── ★핵심★ 정답이 채점기가 받는 모양으로 들어간다 ──────────────
def test_the_milestone_is_one_the_resolver_accepts():
    """★이 테스트가 이 파일의 이유다★ 적재해도 채점기가 안 보는 milestone 이면
    '만들어만 두고 아무도 안 부르는 층'이 하나 더 생길 뿐이다."""
    assert MILESTONE in DECLARATION_MILESTONES


def test_the_event_name_is_the_join_key():
    """event_name 이 곧 대조 키다 — 질병명·지역명이 그대로 들어가야 예측과 만난다."""
    name = event_name_for("라싸열", "나이지리아", dt.date(2026, 9, 15))
    pred = {"country": "나이지리아", "disease": "라싸열"}
    assert match_kind(pred, {"event_id": "x", "event_name": name}) == MATCH_FULL


def test_live_ground_truth_is_labelled_apart_from_the_curated_set():
    """백필분(source_type="official")과 섞으면 나중에 어느 정답이 어디서 왔는지
    아무도 못 가른다. 문서 추출분은 다른 이름을 단다."""
    assert SOURCE_TYPE != "official"


# ── 정답은 채점받는 것보다 믿을 만해야 한다 ────────────────────
def test_news_grade_ai_extraction_is_not_ground_truth():
    """★핵심★ 우리가 낸 신호로 우리 예측을 채점하면 자기 숙제를 자기가 매기는
    꼴이다. 뉴스 자유문장 추출(0.65)·교차검증 실패분(0.70)은 정답이 아니다."""
    assert eligible(_sig(source_trust=0.65))[0] is False
    assert eligible(_sig(source_trust=0.70))[0] is False
    assert eligible(_sig())[0] is True


def test_only_new_outbreaks_count_as_a_declaration():
    """'진행중'은 이미 알려진 사건의 경과 보고지 선언이 아니다."""
    assert eligible(_sig(signal_type="진행중"))[0] is False
    assert eligible(_sig(signal_type="급증"))[0] is False


def test_a_declaration_without_a_date_is_useless_as_ground_truth():
    """날짜가 없으면 선행일수를 못 잰다 — 이 제품의 논지가 선행성이다."""
    assert eligible(_sig(signal_date=None)) == (False, "날짜없음")


def test_skip_reasons_are_reported_not_swallowed():
    """★핵심★ 거른 것을 조용히 버리면 '정답이 왜 안 늘어나는지'를 아무도 모른다
    — 이번에 2년을 그렇게 보냈다."""
    line = summary({"등재": 1, "검토": 9, "건너뜀": {"신뢰도미달": 5, "선언아님": 3}})
    assert "정답 적재 1건 / 검토 9건" in line
    assert "신뢰도미달 5" in line and "선언아님 3" in line


# ── ★핵심★ 세 번째 칸(ambiguous)이 생겼다 ─────────────────────
def test_country_only_match_is_neither_correct_nor_wrong():
    """예측이 기록될 때 같이 적히는 계약이 이렇게 말한다 — *"발병은 확인됐으나
    이 신호와 다른 질병이면 ambiguous"*. db 도 prediction_scoring 도 받는데
    채점기만 안 내놨다. 계약이 먼저 쓰였으니 안 지킨 쪽이 버그다."""
    event = {"event_id": "lassa_nga_2026", "event_name": "라싸열 나이지리아 2026"}
    assert match_kind({"country": "나이지리아", "disease": "라싸열"}, event) == MATCH_FULL
    assert match_kind({"country": "나이지리아", "disease": "종합 위험도(GAI 기반)"},
                      event) == MATCH_COUNTRY
    assert match_kind({"country": "케냐", "disease": "라싸열"}, event) == MATCH_NONE


def test_the_composite_prediction_can_never_match_a_disease():
    """★이게 거짓 0% 를 만들던 자리다★ 종합 예측의 disease 는 글자 그대로
    "종합 위험도(GAI 기반)" 라, 어떤 발병 사건 이름과도 안 겹친다."""
    for name in ("라싸열 나이지리아 2026", "엠폭스 콩고 2024", "마르부르크 르완다 2024"):
        assert match_kind({"country": name.split()[1], "disease": "종합 위험도(GAI 기반)"},
                          {"event_id": "e", "event_name": name}) == MATCH_COUNTRY

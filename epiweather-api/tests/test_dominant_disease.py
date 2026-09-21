"""국가 예측이 '어떤 질병'을 말하는지 — 그리고 말할 수 없을 때 지어내지 않는지.

## 배경 (2026-09-21, 캡틴 지시 B)

예측은 전부 `disease="종합 위험도(GAI 기반)"` 로 기록되고 있었다. 채점기는 예측의
질병 문자열이 발병 사건 이름 안에 있는지를 보는데, 그 글자는 어떤 사건 이름에도
안 나온다 — **적중이 구조적으로 불가능**했다. 루프가 열려 있던 게 아니라, 닫히는
쪽 문이 벽이었다.

여기서 지키려는 계약은 셋이다.

1. 지목할 수 있으면 지목한다 — 그래야 correct 가 나올 수 있다.
2. 흩어져 있으면 지목하지 **않는다** — 없는 정밀도를 지어내면 틀린 근거로 틀린
   성적표가 나온다. 그 경우는 ambiguous 로 떨어지는 게 맞다.
3. 이름은 점수를 만든 것과 **같은 저울**로 고른다. 가중치 식이 두 벌이면
   '점수를 만든 질병'과 '이름 붙인 질병'이 갈라진다.
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import country_risk as cr
from algorithms.country_risk import (
    DOMINANT_DISEASE_MIN_SHARE, _nlp_raw_score, _signal_weight, dominant_disease,
)


@pytest.fixture(autouse=True)
def no_real_country_data(monkeypatch):
    monkeypatch.setattr(cr, "load_country_indicators", lambda: {})


def _signal(disease: str, *, signal_type: str = "신규발생", trust: float = 1.0,
            days_ago: int = 0, iso3: str = "COD", location: str = "Kinshasa"):
    import db as dbmod
    dbmod.create_extracted_signal(
        source="test", disease=disease, location=location, signal_type=signal_type,
        severity=["spike"], symptom=None, transmission=None, source_trust=trust,
        signal_date=(dt.date.today() - dt.timedelta(days=days_ago)).isoformat(),
        raw_text="t", country_iso3=iso3,
    )


# ── 지목할 수 있을 때 ────────────────────────────────────────────────

def test_single_disease_is_named_with_full_share(isolated_db):
    _signal("에볼라")
    name, share = dominant_disease("COD")
    assert name == "에볼라"
    assert share == 1.0


def test_majority_disease_wins_over_minority(isolated_db):
    for _ in range(3):
        _signal("에볼라")
    _signal("콜레라")
    name, share = dominant_disease("COD")
    assert name == "에볼라"
    assert share == pytest.approx(0.75, abs=0.01)


# ── 지목할 수 없을 때 — 이름을 지어내지 않는다 ──────────────────────

def test_evenly_split_signals_refuse_to_name_a_disease(isolated_db):
    """반반이면 어느 쪽도 '이 위험도를 만든 질병'이 아니다. 산술적으로는 50%가
    문턱을 넘지만, 그 1등은 들어온 순서가 정한 것이지 신호가 정한 게 아니다."""
    _signal("에볼라")
    _signal("콜레라")
    name, share = dominant_disease("COD")
    assert name is None
    assert share == pytest.approx(0.5, abs=0.01)


def test_tie_does_not_depend_on_insertion_order(isolated_db):
    """같은 동점을 반대 순서로 넣어도 같은 판정(지목 안 함)이어야 한다 —
    순서가 예측의 질병을 바꾸면 그건 측정이 아니라 우연이다."""
    _signal("콜레라")
    _signal("에볼라")
    assert dominant_disease("COD")[0] is None


def test_bare_majority_above_the_floor_is_named(isolated_db):
    """60:40 은 동점이 아니다. 문턱을 넘었으면 지목한다 — 지목을 과하게 아끼면
    루프가 다시 닫히지 않는다."""
    for _ in range(3):
        _signal("콜레라")
    for _ in range(2):
        _signal("에볼라")
    name, share = dominant_disease("COD")
    assert name == "콜레라"
    assert share == pytest.approx(0.6, abs=0.01)


def test_refusal_still_reports_the_measured_share(isolated_db):
    """못 골랐다고 0.0 을 돌려주지 않는다 — '재보니 33%였다'와 '아예 못 쟀다'는
    다른 사실이고, 예측 근거문에 그 숫자가 그대로 들어간다."""
    _signal("에볼라")
    _signal("콜레라")
    _signal("홍역")
    name, share = dominant_disease("COD")
    assert name is None
    assert share == pytest.approx(0.333, abs=0.01)
    assert share < DOMINANT_DISEASE_MIN_SHARE


def test_no_signals_returns_none_and_zero(isolated_db):
    assert dominant_disease("COD") == (None, 0.0)


def test_unnamed_signals_count_against_the_share(isolated_db):
    """질병명이 비어있는 신호도 위험도는 올린다. 그 몫까지 '에볼라가 만든 위험'으로
    치면 지목 근거가 부풀려진다 — 분모에 남겨 비중을 정직하게 깎는다."""
    _signal("에볼라")
    _signal("")
    _signal("")
    name, share = dominant_disease("COD")
    assert name is None
    assert share == pytest.approx(0.333, abs=0.01)


def test_zero_trust_signal_does_not_vote(isolated_db):
    """신뢰도 0 은 위험도에 기여하지 않는다. 지목에서도 같아야 한다 —
    아니면 점수에 아무 영향도 못 준 신호가 이름을 정하게 된다."""
    _signal("에볼라")
    for _ in range(5):
        _signal("콜레라", trust=0.0)
    name, share = dominant_disease("COD")
    assert name == "에볼라"
    assert share == 1.0


# ── ★ 점수와 지목이 같은 저울을 쓰는가 ★ ────────────────────────────

def test_recent_signal_outweighs_old_one_in_naming(isolated_db):
    """오래된 신호는 위험도 기여가 줄어든다(반감기 14일). 지목도 같은 감쇠를
    받아야 한다 — 안 그러면 2년 전 사건 이름이 오늘 예측에 붙는다."""
    _signal("에볼라", days_ago=90)
    _signal("콜레라", days_ago=0)
    name, _ = dominant_disease("COD")
    assert name == "콜레라"


def test_naming_uses_the_same_weight_function_as_the_score(isolated_db):
    """구조 시험: _nlp_raw_score 의 분자 항이 _signal_weight 와 **같은 값**인지.
    식이 두 벌이 되는 순간 이 시험이 깨진다."""
    _signal("에볼라", signal_type="신규발생", trust=0.9, days_ago=10)
    _signal("콜레라", signal_type="진행중", trust=0.7, days_ago=3)

    matched = cr._matched_signals("COD")
    score, count = _nlp_raw_score("COD", matched)
    den = sum(cr._recency_weight(cr._signal_age_days(r)) for r in matched)
    expected = round(sum(_signal_weight(r) for r in matched) / den, 1)
    assert count == 2
    assert score == expected


def test_compute_country_risk_exposes_the_name_and_the_share(isolated_db):
    _signal("에볼라")
    result = cr.compute_country_risk("COD")
    assert result["dominant_disease"] == "에볼라"
    assert result["dominant_disease_share"] == 1.0


# ── ★ 온톨로지: 예측의 질병명이 정답 이름과 실제로 만나는가 ★ ───────

def test_named_prediction_matches_the_ground_truth_event_name(isolated_db):
    """제일 싼 온톨로지는 사전이 아니라 하나의 어휘다.

    지목한 질병명은 extracted_signals.disease 이고, 정답 테이블에 올라가는 이름도
    같은 필드에서 온다(declaration_ingest.event_name_for). 둘이 같은 출처를 쓰므로
    표기가 어긋날 자리가 없다 — 그걸 실제 채점기로 확인한다."""
    from algorithms.declaration_ingest import event_name_for
    from algorithms.prediction_resolver import MATCH_FULL, match_kind

    _signal("에볼라", location="콩고민주공화국 킨샤사")
    name, _ = dominant_disease("COD")
    assert name is not None

    event = {
        "event_id": "ebola_cod_2026",
        "event_name": event_name_for(name, "콩고민주공화국 킨샤사", dt.date.today()),
    }
    prediction = {"country": "콩고민주공화국", "disease": name}
    assert match_kind(prediction, event) == MATCH_FULL


def test_unnamed_prediction_falls_to_ambiguous_not_incorrect(isolated_db):
    """지목 못 한 예측은 발병이 확인돼도 correct 가 아니다. 그렇다고 incorrect 도
    아니다 — 발병은 실제로 있었으니 '틀렸다'는 사실이 아니다."""
    from algorithms.prediction_resolver import MATCH_COUNTRY, match_kind

    event = {"event_id": "ebola_cod_2026", "event_name": "에볼라 콩고민주공화국 2026"}
    prediction = {"country": "콩고민주공화국", "disease": "종합 위험도(GAI 기반)"}
    assert match_kind(prediction, event) == MATCH_COUNTRY

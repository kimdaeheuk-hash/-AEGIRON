"""이미 선언된 발병을 다시 지목한 예측은 선행이 아니다 — 모호 (2026-10-25, 캡틴 결정 "모호로 하고 진행").

10-23 21:07 첫 '선행일수 실측' 4건이 전부 같은 WHO 발표 하나(`Ebola disease caused by Bundibugyo virus`,
event `eboladiseasecausedbybund_ken_2026`)로 닫혔다. DRC 에볼라는 그 전에 이미 PHEIC 상태였다 — 채점기는
'예측 뒤의 첫 일치 발표'만 보고 '예측 전에 이미 선언됐는가'를 안 봤다. 고정하는 것:
① 예측 전 같은 나라·질병 선언이 있으면 결과를 기다리지 않고 모호, 선행일수 없음
② 질병 표기가 달라도 같은 병(분디부교 = 에볼라)이면 같다고 본다
③ 이미 correct 로 닫힌 자동 판정을 다시 매기고 원판정을 남긴다 · 손 판정은 안 건드린다
④ 예측 전 선언이 없으면 예전 그대로 적중·선행 ⑤ 다른 나라의 선언은 막지 않는다
⑥ 선행성 원장도 같은 규칙(나라를 아는 통과는 같은 나라만).
"""
from __future__ import annotations

import datetime as dt
import json

import db
from algorithms import lead_time_ledger as ledger
from algorithms.prediction_resolver import resolve_due_predictions


def _days(n: int) -> str:
    return (dt.date.today() - dt.timedelta(days=n)).isoformat()


def _predict(days_ago: int, country: str, disease: str) -> int:
    row = db.create_prediction(country, disease, 80.0, ["시험"], confidence=0.6,
                               resolution_criteria="공식 선언으로 판정(시험)", resolves_by=_days(-60))
    with db.get_connection() as conn:
        conn.execute("UPDATE predictions SET predicted_at=? WHERE id=?", (_days(days_ago), row["id"]))
        conn.commit()
    return row["id"]


def _declare(event_id: str, name: str, days_ago: int, milestone: str = "who_statement") -> None:
    db.upsert_timeline_event(event_id, name, _days(days_ago), milestone, "시험", "WHO DON", "who_don")


def _get(pid: int) -> dict:
    return next(p for p in db.list_predictions() if p["id"] == pid)


def test_drc_ebola_case_from_2026_10_23_is_ambiguous_without_lead(isolated_db):
    _declare("ebolavirusdisease_cod_2026", "Ebola virus disease 에볼라 Democratic Republic of the Congo 2026", 120)
    _declare("eboladiseasecausedbybund_cod_2026",
             "Ebola disease caused by Bundibugyo virus 에볼라 Democratic Republic of the Congo, Kenya 2026", 2)
    pid = _predict(27, "콩고민주공화국", "에볼라")
    out = resolve_due_predictions()
    p = _get(pid)
    assert p["outcome"] == "ambiguous" and p["lead_days"] is None and p["correct"] is None
    assert "이미 같은 나라·질병의 공식 선언" in p["actual_result"]
    assert out["resolved"][0]["already_declared"] is True


def test_bundibugyo_prediction_sees_an_earlier_ebola_declaration(isolated_db):
    _declare("ebolavirusdisease_ken_2026", "Ebola virus disease 에볼라 Kenya 2026", 30)
    pid = _predict(10, "Kenya", "Bundibugyo")
    resolve_due_predictions()
    assert _get(pid)["outcome"] == "ambiguous"


def test_without_a_prior_declaration_a_hit_still_counts(isolated_db):
    _declare("eboladiseasecausedbybund_ken_2026", "Ebola disease caused by Bundibugyo virus 에볼라 Kenya 2026", 2)
    pid = _predict(15, "Kenya", "Bundibugyo")
    resolve_due_predictions()
    p = _get(pid)
    assert p["outcome"] == "correct" and p["lead_days"] == 13


def test_a_declaration_in_another_country_does_not_block(isolated_db):
    _declare("ebolavirusdisease_cod_2026", "Ebola virus disease 에볼라 Democratic Republic of the Congo 2026", 120)
    _declare("eboladiseasecausedbybund_nga_2026", "Ebola disease caused by Bundibugyo virus 에볼라 Nigeria 2026", 1)
    pid = _predict(2, "나이지리아", "Bundibugyo")
    resolve_due_predictions()
    assert _get(pid)["outcome"] == "correct"


def test_already_closed_auto_hits_are_regraded_and_keep_the_original(isolated_db):
    _declare("ebolavirusdisease_cod_2026", "Ebola virus disease 에볼라 Democratic Republic of the Congo 2026", 120)
    auto = _predict(27, "콩고민주공화국", "에볼라")
    db.verify_prediction(auto, actual_result="공식 선언 확인: X", correct=True, lead_days=25, outcome="correct",
                         resolution_sources=["auto:outbreak_timeline:eboladiseasecausedbybund_ken_2026:who_statement@x"])
    manual = _predict(27, "콩고민주공화국", "에볼라")
    db.verify_prediction(manual, actual_result="사람 판정", correct=True, lead_days=25, outcome="correct",
                         resolution_sources=["manual:캡틴"])
    out = resolve_due_predictions()
    p = _get(auto)
    assert p["outcome"] == "ambiguous" and p["lead_days"] is None
    assert "원판정 correct(선행 25일)" in p["actual_result"]
    sources = p["resolution_sources"] if isinstance(p["resolution_sources"], list) else json.loads(p["resolution_sources"])
    assert sources[0].startswith("auto:outbreak_timeline:") and "regrade:already_declared" in sources
    assert [r["prediction_id"] for r in out["regraded"]] == [auto]
    assert _get(manual)["outcome"] == "correct", "손으로 넣은 판정은 건드리지 않는다"
    # 두 번째 채점에서 다시 매기지 않는다.
    assert resolve_due_predictions()["regraded"] == []


def test_the_seal_does_not_cover_the_regraded_fields():
    from algorithms.prediction_timestamp import canonical_hash
    base = {"id": 1, "predicted_at": "2026-09-26", "country": "COD", "disease": "에볼라", "risk_score": 80,
            "basis": ["x"]}
    assert canonical_hash({**base, "outcome": "correct", "lead_days": 25}) == \
        canonical_hash({**base, "outcome": "ambiguous", "lead_days": None})


def test_ledger_crossing_after_a_same_country_declaration_is_not_a_lead(isolated_db):
    _declare("ebolavirusdisease_cod_2026", "Ebola virus disease 에볼라 Democratic Republic of the Congo 2026", 60, "who_pheic")
    _declare("eboladiseasecausedbybund_cod_2026", "Ebola disease caused by Bundibugyo virus 에볼라 DRC 2026", 2, "who_pheic")
    ledger.open_crossing("에볼라", "COD", 85.0, 80.0, [1])
    with db.get_connection() as conn:
        conn.execute("UPDATE lead_time_ledger SET crossed_at=?", (_days(20) + "T00:00:00+00:00",))
        conn.commit()
    out = ledger.resolve_ledger()
    assert out["closed_declared"] == [] and out["closed_already_declared"] == 1
    assert ledger.ledger_record()["already_declared"] == 1 and ledger.ledger_record()["measured_events"] == 0


def test_ledger_other_country_declaration_does_not_block(isolated_db):
    _declare("ebolavirusdisease_cod_2026", "Ebola virus disease 에볼라 Democratic Republic of the Congo 2026", 60, "who_pheic")
    _declare("ebolavirusdisease_uga_2026", "Ebola virus disease 에볼라 Uganda 2026", 2, "who_pheic")
    ledger.open_crossing("에볼라", "UGA", 85.0, 80.0, [1])
    with db.get_connection() as conn:
        conn.execute("UPDATE lead_time_ledger SET crossed_at=?", (_days(20) + "T00:00:00+00:00",))
        conn.commit()
    out = ledger.resolve_ledger()
    assert out["closed_already_declared"] == 0 and len(out["closed_declared"]) == 1

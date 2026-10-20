"""받았지만 못 읽은 공식 발표 (2026-10-20, 10-19 첫 아카이브 채점 다음 날).

10-19 21:00 슬롯에서 WHO DON 100건 중 16건이 나라·형식을 못 읽어 정답에서 빠졌다. 아카이브 포괄은
'받았다'이지 '읽었다'가 아니다 — 못 읽은 발표가 예측의 나라였으면 결과가 달라진다. 고정하는 것:
① 공백 없이 붙은 구분자를 읽는다(실제 제목 두 개) — 단 `Crimean-Congo` 를 콩고로 읽지 않는다
② 못 읽은 발표가 판정 구간 (예측일, 기한] 에 있으면 오답·질병 불일치로 닫지 않는다
③ 예측일 이전 발표는 보류 사유가 아니다 ④ 나중에 읽히면 목록에서 빠지고 다음 채점에서 닫힌다
⑤ 적중은 막지 않는다 ⑥ 선행성 원장도 같은 규칙 ⑦ 못 읽은 항목의 필드 이름을 로그에 싣는다.
"""
from __future__ import annotations

import datetime as dt

import db
from algorithms import who_don_declarations as don
from algorithms.ground_truth_channel import unread_reason
from algorithms.prediction_resolver import resolve_due_predictions


def test_tight_separators_from_production_titles_are_read():
    assert don.title_options("Marburg Virus Disease–United Republic of Tanzania")[0] == \
        ("Marburg Virus Disease", "United Republic of Tanzania")
    assert don.title_options("Human infection caused by avian Influenza A(H5N2)-Mexico")[0] == \
        ("Human infection caused by avian Influenza A(H5N2)", "Mexico")


def test_hyphens_inside_disease_names_are_not_read_as_a_country():
    assert don.title_options("Crimean-Congo haemorrhagic fever") == []
    assert don.title_options("MERS-CoV") == []
    out = don.parse_items({"value": [
        {"Title": "Cholera – Angola", "PublicationDate": "2026-10-02", "DonId": "B"},
        {"Title": "Crimean-Congo haemorrhagic fever", "PublicationDate": "2026-10-01", "DonId": "A"}]},
        dt.date(2026, 10, 19))
    assert [d["iso3"] for d in out["declarations"]] == ["AGO"] and out["skipped"] == {"제목 형식 모름": 1}


def _payload(today: dt.date):
    return {"value": [
        {"Title": "Cholera – Angola", "PublicationDate": (today - dt.timedelta(days=5)).isoformat(), "DonId": "R1"},
        {"Title": "Avian Influenza A(H9N2)", "PublicationDate": (today - dt.timedelta(days=40)).isoformat(),
         "DonId": "U1", "Overview": "…"},
        {"Title": "Yellow fever - Global", "PublicationDate": (today - dt.timedelta(days=60)).isoformat(),
         "DonId": "U2"},
    ]}


def test_ingest_records_unread_items_and_their_field_names(isolated_db):
    today = dt.date.today()
    out = don.ingest_don(_payload(today), today)
    rows = db.list_ground_truth_unread(("who_don",))
    assert {r["item_key"]: r["reason"] for r in rows} == {"U1": "제목 형식 모름", "U2": "국가 못 읽음"}
    line = don.samples_line(out)
    assert "못 읽은 항목의 필드: DonId, Overview, PublicationDate, Title" in line


def _predict(days_ago: int, country="Angola", disease="콜레라"):
    row = db.create_prediction(country, disease, 80.0, ["테스트"], confidence=0.7,
                               resolution_criteria="공식 선언으로 판정(테스트)",
                               resolves_by=(dt.date.today() + dt.timedelta(days=60)).isoformat())
    when = (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()
    with db.get_connection() as conn:
        conn.execute("UPDATE predictions SET predicted_at=? WHERE id=?", (when, row["id"]))
        conn.commit()
    return row["id"]


def _watching(today: dt.date):
    """정답 경로가 그 기간을 보고 있었다 — 포괄 시작이 예측보다 이르고, 구간 안에 읽힌 선언이 하나 있다."""
    db.extend_ground_truth_coverage("who_don", (today - dt.timedelta(days=400)).isoformat(), "시험")
    db.upsert_timeline_event("seed_atlantis", "Seed Atlantis", (today - dt.timedelta(days=150)).isoformat(),
                             "who_statement", "시험용", "WHO DON seed", "who_don")


def test_unread_announcement_in_window_holds_an_incorrect_closure(isolated_db):
    today = dt.date.today()
    _watching(today)
    _predict(days_ago=200)                     # 구간: (200일 전, 110일 전]
    published = (today - dt.timedelta(days=150)).isoformat()
    db.record_ground_truth_unread("who_don", [{"key": "U9", "published": published, "title": "Yellow fever - Global",
                                               "reason": "국가 못 읽음"}], [])
    out = resolve_due_predictions()
    assert out["resolved"] == [] and out["blind"] == 1
    assert any("못 읽은 공식 발표 1건" in k for k in out["blind_reasons"])

    # 파서가 그 발표를 읽게 되면 목록에서 빠지고, 다음 채점에서 닫힌다.
    db.record_ground_truth_unread("who_don", [], ["U9"])
    out = resolve_due_predictions()
    assert [r["correct"] for r in out["resolved"]] == [0] and out["blind"] == 0


def test_unread_announcement_before_the_prediction_is_not_a_reason(isolated_db):
    today = dt.date.today()
    _watching(today)
    db.record_ground_truth_unread("who_don", [{"key": "U8", "published": (today - dt.timedelta(days=250)).isoformat(),
                                               "title": "x", "reason": "제목 형식 모름"}], [])
    assert unread_reason(today - dt.timedelta(days=200), today - dt.timedelta(days=110)) is None
    _predict(days_ago=200)
    assert [r["correct"] for r in resolve_due_predictions()["resolved"]] == [0]


def test_a_hit_is_not_held_back_by_an_unread_announcement(isolated_db):
    today = dt.date.today()
    _watching(today)
    _predict(days_ago=200)
    db.upsert_timeline_event("cholera_ago", "콜레라 Angola", (today - dt.timedelta(days=170)).isoformat(),
                             "who_statement", "적중", "WHO DON", "who_don")
    db.record_ground_truth_unread("who_don", [{"key": "U7", "published": (today - dt.timedelta(days=150)).isoformat(),
                                               "title": "x", "reason": "국가 못 읽음"}], [])
    out = resolve_due_predictions()
    assert [r["correct"] for r in out["resolved"]] == [1]


def test_the_lead_time_ledger_uses_the_same_rule():
    import inspect
    from algorithms import lead_time_ledger
    assert "unread_reason(crossed, window_end)" in inspect.getsource(lead_time_ledger)

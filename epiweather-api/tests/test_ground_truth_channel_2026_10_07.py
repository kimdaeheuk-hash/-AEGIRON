"""정답 적재 0건 진단(2026-10-07)과 그 수리 두 가지.

## 진단
`declaration_ingest.eligible()` 은 신뢰도 ≥0.90 **그리고** 신호유형 `신규발생` 을 요구하는데, 그런 신호를
만드는 생산자가 없다 — 뉴스 NLP 추출은 신뢰도 0.65(`신규발생` 가능), WHO 표 추출은 0.90(`진행중/불명` 만).
로그의 `신뢰도미달 178 · 선언아님 22` 가 정확히 그 모양이다.

## 수리
1. 정답 경로가 눈이 먼 채 기한이 지난 침묵은 오답이 아니다 → **판정 보류**(`ground_truth_channel`).
2. WHO DON(사람이 쓴 공식 발표)을 정답 경로의 생산자로 연결한다(`who_don_declarations`).
"""
from __future__ import annotations

import datetime as dt

import pytest
import requests

import db
from algorithms import ground_truth_channel as gtc
from algorithms import who_don_declarations as don
from algorithms.declaration_ingest import eligible
from algorithms.lead_time_ledger import (RESOLUTION_HORIZON_DAYS, list_entries, open_crossing, resolve_ledger)
from algorithms.prediction_resolver import lead_time_record, resolve_due_predictions
from tests._live_channel import seed_live_channel

TODAY = dt.date.today()


def _predict(country="Angola", disease="콜레라", days_ago=200):
    row = db.create_prediction(
        country=country, disease=disease, risk_score=80.0, basis=["테스트"], confidence=0.7,
        resolution_criteria="공식 선언이 나오는지로 판정한다(테스트)",
        resolves_by=(TODAY + dt.timedelta(days=60)).isoformat())
    pid = row["id"] if isinstance(row, dict) else row
    when = (TODAY - dt.timedelta(days=days_ago)).isoformat()
    with db.get_connection() as conn:
        conn.execute("UPDATE predictions SET predicted_at = ? WHERE id = ?", (when, pid))
        conn.commit()
    return pid


def _row(pid):
    return next(p for p in db.list_predictions() if p["id"] == pid)


# ── 진단: 지금 생산자로는 정답이 구조적으로 0건이다 ──────────────

def test_no_current_producer_can_satisfy_the_eligibility_rule():
    """뉴스 추출(0.65·신규발생)과 WHO 표 추출(0.90·진행중)은 각각 한쪽만 만족한다 — 둘 다는 없다."""
    news = {"source_trust": 0.65, "signal_type": "신규발생", "disease": "콜레라",
            "country_iso3": "AGO", "signal_date": "2026-09-01"}
    table = {"source_trust": 0.90, "signal_type": "진행중", "disease": "콜레라",
             "country_iso3": "AGO", "signal_date": "2026-09-01"}
    assert eligible(news) == (False, "신뢰도미달")
    assert eligible(table) == (False, "선언아님")


def test_production_producers_still_have_the_trust_and_type_the_diagnosis_relies_on():
    """진단의 두 전제가 바뀌면 이 시험이 알린다(생산자가 바뀌었으면 진단을 다시 해야 한다)."""
    from algorithms.bulletin_ingest import signal_type_for
    from algorithms.trust import trust_for
    assert trust_for("ai_extracted") < trust_for("document_extracted")
    assert signal_type_for({"layout": "who_afro_events"}) == "진행중"
    assert signal_type_for({"metrics": {"new_cases": 10}}) == "진행중"
    assert signal_type_for({"metrics": {"new_cases": 0}}) == "불명"


# ── 1. 눈이 먼 채 지난 침묵은 오답이 아니다 ──────────────────────

def test_silence_is_not_incorrect_when_the_channel_never_ingested_anything(isolated_db):
    pid = _predict()
    out = resolve_due_predictions()
    assert out["blind"] == 1 and out["resolved"] == []
    assert "한 건도 적재한 적이 없다" in next(iter(out["blind_reasons"]))
    assert _row(pid).get("verified_at") is None
    assert lead_time_record()["resolved_incorrect"] == 0


def test_silence_is_not_incorrect_when_the_channel_started_after_the_prediction(isolated_db):
    pid = _predict(days_ago=200)
    start = TODAY - dt.timedelta(days=200)
    seed_live_channel(first_seen=start + dt.timedelta(days=5), event_date=start + dt.timedelta(days=20))
    out = resolve_due_predictions()
    assert out["blind"] == 1 and "첫 적재" in next(iter(out["blind_reasons"]))
    assert _row(pid).get("verified_at") is None


def test_silence_is_not_incorrect_when_nothing_was_seen_inside_the_window(isolated_db):
    pid = _predict(days_ago=200)
    start = TODAY - dt.timedelta(days=200)
    seed_live_channel(first_seen=start - dt.timedelta(days=1), event_date=start + dt.timedelta(days=150))
    out = resolve_due_predictions()
    assert out["blind"] == 1 and "구간 안" in next(iter(out["blind_reasons"]))
    assert _row(pid).get("verified_at") is None


def test_hand_written_backfill_does_not_count_as_the_channel_watching(isolated_db):
    """옛 16건 백필(`official`)은 오늘의 경로가 보고 있었다는 증거가 아니다."""
    pid = _predict(days_ago=200)
    start = TODAY - dt.timedelta(days=200)
    db.upsert_timeline_event("old_x_2026", "Atlantis 1999", (start + dt.timedelta(days=10)).isoformat(),
                             "who_statement", "백필", "수기", "official")
    with db.get_connection() as conn:                  # 시각 조건은 통과하게 — source_type 만으로 갈린다
        conn.execute("UPDATE outbreak_timeline SET created_at = ? WHERE event_id = 'old_x_2026'",
                     ((start - dt.timedelta(days=1)).isoformat() + "T00:00:00+00:00",))
        conn.commit()
    assert resolve_due_predictions()["blind"] == 1
    assert _row(pid).get("verified_at") is None


def test_silence_is_incorrect_when_the_channel_was_watching(isolated_db):
    """대조군 — 보고 있었으면 예전처럼 오답으로 닫는다(조용했다는 것도 채점 대상)."""
    pid = _predict(days_ago=200)
    start = TODAY - dt.timedelta(days=200)
    seed_live_channel(first_seen=start - dt.timedelta(days=1), event_date=start + dt.timedelta(days=10))
    out = resolve_due_predictions()
    assert out["blind"] == 0 and [r["correct"] for r in out["resolved"]] == [0]
    assert _row(pid).get("verified_at")


def test_blind_prediction_can_still_be_scored_correct_later(isolated_db):
    """닫지 않았으니 정답이 나중에 적재되면 적중으로 채점될 수 있다(오답으로 닫았으면 불가능했다)."""
    pid = _predict(days_ago=60)                       # 기한 안
    res = don.ingest_don({"value": [{"Title": "콜레라 – Angola", "PublicationDate": (TODAY - dt.timedelta(days=5)).isoformat(),
                                     "DonId": "2026-DON999"}]})
    assert res["등재"] == 1
    out = resolve_due_predictions()
    assert [(r["correct"], r["lead_days"]) for r in out["resolved"]] == [(1, 55)]
    assert _row(pid).get("verified_at")


def test_ledger_leaves_blind_silence_open_instead_of_closing_as_false_alarm(isolated_db):
    now = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    open_crossing("니파", "IND", 85.0, 80.0, [1], now=now - dt.timedelta(days=RESOLUTION_HORIZON_DAYS + 5))
    out = resolve_ledger(now=now)
    assert out["closed_no_declaration"] == 0 and out["blind"] == 1
    assert list_entries(outcome="open")


def test_ledger_still_closes_silence_when_the_channel_was_watching(isolated_db):
    now = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    crossed = now - dt.timedelta(days=RESOLUTION_HORIZON_DAYS + 5)
    open_crossing("니파", "IND", 85.0, 80.0, [1], now=crossed)
    seed_live_channel(crossed.date() - dt.timedelta(days=1), crossed.date() + dt.timedelta(days=10))
    out = resolve_ledger(now=now)
    assert out["closed_no_declaration"] == 1 and out["blind"] == 0


def test_blind_reason_is_none_only_when_both_conditions_hold(isolated_db):
    s, e = TODAY - dt.timedelta(days=100), TODAY - dt.timedelta(days=10)
    assert gtc.blind_reason(s, e) is not None
    seed_live_channel(first_seen=s - dt.timedelta(days=1), event_date=s + dt.timedelta(days=3))
    assert gtc.blind_reason(s, e) is None


def test_resolvers_actually_call_the_guard():
    """배선 — 만들어만 두고 아무도 안 부르는 층 방지."""
    import ast
    import inspect
    from algorithms import lead_time_ledger as ledger, prediction_resolver as resolver
    for fn in (resolver.resolve_due_predictions, ledger.resolve_ledger):
        calls = {n.func.id for n in ast.walk(ast.parse(inspect.getsource(fn)))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "blind_reason" in calls, fn.__name__


# ── 2. WHO DON 생산자 ────────────────────────────────────────

def _item(title, date=None, don_id="2026-DON1"):
    return {"Title": title, "PublicationDate": (date or TODAY - dt.timedelta(days=3)).isoformat(), "DonId": don_id}


def test_title_is_split_into_disease_and_country_phrase():
    assert don.split_title("Cholera – Angola") == ("Cholera", "Angola")
    assert don.split_title("Avian Influenza A(H5N1) - Cambodia") == ("Avian Influenza A(H5N1)", "Cambodia")
    assert don.split_title("Marburg virus disease — Ethiopia") == ("Marburg virus disease", "Ethiopia")
    assert don.split_title("제목에 구분자 없음") is None


def test_parse_reads_declarations_and_counts_what_it_skips():
    out = don.parse_items({"value": [
        _item("Cholera – Angola"),
        _item("Mpox – African Region"),                      # 지역 — 추측하지 않는다
        _item("구분자 없는 제목"),
        _item("Cholera – Angola", date=TODAY - dt.timedelta(days=900)),
        {"Title": "Ebola – Uganda", "PublicationDate": "날짜아님"},
    ]})
    assert [(d["disease"], d["iso3"]) for d in out["declarations"]] == [("Cholera", "AGO")]
    assert out["skipped"] == {"국가 못 읽음": 1, "제목 형식 모름": 1, "기간 밖": 1, "날짜 못 읽음": 1}
    assert out["read"] == 5


def test_multi_country_title_yields_one_declaration_per_country():
    out = don.parse_items({"value": [_item("Cholera – Angola, Zambia")]})
    assert sorted(d["iso3"] for d in out["declarations"]) == ["AGO", "ZMB"]


def test_unexpected_shape_raises_instead_of_inventing():
    with pytest.raises(don.DonError, match="목록"):
        don.parse_items({"error": "x"})
    with pytest.raises(don.DonError, match="하나도 못 읽었다"):
        don.parse_items({"value": [{"foo": "bar"}, {"baz": 1}]})


def test_future_dated_items_are_not_taken_as_declarations():
    out = don.parse_items({"value": [_item("Cholera – Angola", date=TODAY + dt.timedelta(days=30))]})
    assert out["declarations"] == [] and out["skipped"] == {"기간 밖": 1}


def test_fetch_failure_is_raised_with_its_kind(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("프록시 403")
    monkeypatch.setattr(don.requests, "get", boom)
    with pytest.raises(don.DonError, match="ConnectionError"):
        don.ingest_don()


def test_ingest_writes_who_statement_rows_tagged_as_who_don(isolated_db):
    res = don.ingest_don({"value": [_item("Cholera – Angola")]})
    assert res["등재"] == 1
    rows = db.list_live_timeline_rows(gtc.LIVE_SOURCE_TYPES)
    assert [(r["source_type"]) for r in rows] == ["who_don"]
    (ev,) = db.list_timeline_events()
    (m,) = db.get_timeline(ev["event_id"])["milestones"]
    assert m["milestone"] == "who_statement" and m["source"] == "WHO DON 2026-DON1"


def test_ingest_is_idempotent_and_keeps_the_first_date(isolated_db):
    first = TODAY - dt.timedelta(days=20)
    don.ingest_don({"value": [_item("Cholera – Angola", date=first)]})
    res = don.ingest_don({"value": [_item("Cholera – Angola", date=TODAY - dt.timedelta(days=2), don_id="2026-DON2")]})
    assert res["등재"] == 0 and res["이미있음"] == 1
    (ev,) = db.list_timeline_events()
    assert db.get_timeline(ev["event_id"])["milestones"][0]["event_date"] == first.isoformat()


def test_korean_prediction_matches_an_english_don_title(isolated_db):
    """어휘 불일치 방지 — 영어 제목에 한글 표준명을 덧붙여 '콜레라' 예측이 완전일치로 잡힌다."""
    don.ingest_don({"value": [_item("Cholera – Angola")]})
    (ev,) = db.list_timeline_events()
    assert "콜레라" in ev["event_name"] and "Angola" in ev["event_name"]


def test_wrong_country_or_disease_is_not_a_hit(isolated_db):
    _predict(country="Zambia", disease="콜레라", days_ago=60)
    _predict(country="Angola", disease="에볼라", days_ago=60)
    don.ingest_don({"value": [_item("Cholera – Angola")]})
    out = resolve_due_predictions()
    assert [r for r in out["resolved"] if r["correct"] == 1] == []


def test_summary_line_is_informative():
    line = don.summary({"등재": 2, "이미있음": 1, "건너뜀": {"국가 못 읽음": 3}, "검토": 9})
    assert "WHO DON 정답 적재 2건 / 검토 9건" in line and "이미 있음 1" in line and "국가 못 읽음 3" in line


def test_main_runs_the_don_step_before_the_resolver_and_logs_blind():
    import ast
    import inspect
    import main
    src = inspect.getsource(main._run_prediction_resolution) if hasattr(main, "_run_prediction_resolution") else None
    if src is None:                                       # 이름이 다르면 해당 함수를 찾는다
        src = next(inspect.getsource(f) for n, f in vars(main).items()
                   if callable(f) and getattr(f, "__module__", "") == "main" and "ingest_don" in _safe_src(f))
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)}
    assert "ingest_don" in names
    assert src.index("ingest_don") < src.index("resolve_due_predictions")
    assert "예측 판정 보류" in src


def _safe_src(f):
    import inspect
    try:
        return inspect.getsource(f)
    except (OSError, TypeError):
        return ""

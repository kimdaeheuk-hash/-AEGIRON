"""정답 경로의 공식 아카이브 전수 포괄 (2026-10-19, 캡틴 결정 "10월 7일 이전 정답 채우기 — 진행해").

WHO DON 경로는 첫 적재가 10-07 이라, 그 전에 만든 예측은 기한이 와도 '판정 보류'였다(리허설: 9건).
그런데 이 경로는 공식 발표 목록을 발행일 내림차순으로 통째로 받는다 — 고른 백필이 아니다. 그 목록이
빠짐없이 덮는 가장 이른 날부터는 보고 있던 것과 같다. 고정하는 것:
① 내림차순·발행일 전부 읽힘일 때만 포괄을 말한다 ② LOOKBACK_DAYS 경계보다 이르게 말하지 않는다
③ 포괄 시작일은 당기기만 한다 ④ 포괄이 있으면 첫 적재가 늦어도 닫는다(오답도 채점)
⑤ 손으로 적은 백필은 여전히 세지 않는다 ⑥ 선행 인정은 선언일 > 예측일 그대로.
"""
from __future__ import annotations

import datetime as dt

import db
from algorithms import who_don_declarations as don
from algorithms.prediction_resolver import resolve_due_predictions
from tests._live_channel import seed_live_channel

TODAY = dt.date(2026, 10, 19)


def _items(*dates, titles=None):
    titles = titles or ["Cholera – Angola"] * len(dates)
    return {"value": [{"Title": t, "PublicationDate": f"{d}T00:00:00Z", "DonId": f"D{i}"}
                      for i, (t, d) in enumerate(zip(titles, dates))]}


def test_coverage_is_the_oldest_item_when_sorted_descending():
    covered, basis = don.archive_coverage(_items("2026-10-10", "2026-09-01", "2026-03-02"), TODAY)
    assert covered == "2026-03-02" and "빠짐없이" in basis


def test_coverage_is_clamped_to_the_lookback_boundary():
    covered, _ = don.archive_coverage(_items("2026-10-10", "2024-01-01"), TODAY)
    assert covered == (TODAY - dt.timedelta(days=don.LOOKBACK_DAYS)).isoformat()


def test_no_coverage_claim_when_order_or_dates_are_unreliable():
    assert don.archive_coverage(_items("2026-09-01", "2026-10-10"), TODAY)[0] is None
    bad = {"value": [{"Title": "Cholera – Angola", "PublicationDate": "2026-10-10"}, {"Title": "x"}]}
    covered, why = don.archive_coverage(bad, TODAY)
    assert covered is None and "발행일 못 읽은" in why
    assert don.archive_coverage({"value": []}, TODAY)[0] is None


def test_ingest_records_coverage_and_only_pulls_it_earlier(isolated_db):
    out = don.ingest_don(_items("2026-10-10", "2026-05-01"), TODAY)
    assert out["포괄"] == "2026-05-01" and "아카이브 포괄 2026-05-01~" in don.summary(out)
    out2 = don.ingest_don(_items("2026-10-12", "2026-08-01"), TODAY)
    assert out2["포괄"] == "2026-05-01", "더 늦은 시작일로 미루지 않는다"
    assert db.ground_truth_coverage(("who_don",))[0]["covered_from"] == "2026-05-01"


def _predict(days_ago: int, country="Angola", disease="콜레라"):
    row = db.create_prediction(country, disease, 80.0, ["테스트"], confidence=0.7,
                               resolution_criteria="공식 선언으로 판정(테스트)",
                               resolves_by=(dt.date.today() + dt.timedelta(days=60)).isoformat())
    when = (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()
    with db.get_connection() as conn:
        conn.execute("UPDATE predictions SET predicted_at=? WHERE id=?", (when, row["id"]))
        conn.commit()
    return row["id"]


def test_archive_coverage_lets_a_pre_channel_prediction_be_scored(isolated_db):
    today = dt.date.today()
    start = today - dt.timedelta(days=200)
    _predict(days_ago=200)
    # 실시간 경로는 예측 뒤에야 처음 적재됐다 — 예전 규칙이면 판정 보류.
    seed_live_channel(first_seen=start + dt.timedelta(days=150), event_date=start + dt.timedelta(days=20))
    assert resolve_due_predictions()["blind"] == 1

    db.extend_ground_truth_coverage("who_don", (start - dt.timedelta(days=30)).isoformat(), "시험")
    out = resolve_due_predictions()
    assert out["blind"] == 0 and [r["correct"] for r in out["resolved"]] == [0], "보고 있었으니 조용했으면 오답"


def test_archive_coverage_does_not_credit_declarations_before_the_prediction(isolated_db):
    today = dt.date.today()
    start = today - dt.timedelta(days=200)
    pid = _predict(days_ago=200)
    db.extend_ground_truth_coverage("who_don", (start - dt.timedelta(days=30)).isoformat(), "시험")
    # 예측 열흘 전에 이미 나온 발표 — 같은 질병·나라여도 '먼저 안 것'이 아니다.
    seed_live_channel(first_seen=today, event_date=start + dt.timedelta(days=20))
    db.upsert_timeline_event("cholera_ago_early", "Cholera Angola", (start - dt.timedelta(days=10)).isoformat(),
                             "who_statement", "예측 전 발표", "WHO DON", "who_don")
    out = resolve_due_predictions()
    assert [r["correct"] for r in out["resolved"]] == [0]
    assert next(p for p in db.list_predictions() if p["id"] == pid)["lead_days"] is None


def test_hand_written_backfill_still_does_not_count(isolated_db):
    """포괄은 who_don 경로의 것이다 — 손으로 적은 백필(official)에는 포괄이 없다."""
    today = dt.date.today()
    start = today - dt.timedelta(days=200)
    _predict(days_ago=200)
    db.extend_ground_truth_coverage("official", (start - dt.timedelta(days=30)).isoformat(), "시험")
    seed_live_channel(first_seen=start + dt.timedelta(days=150), event_date=start + dt.timedelta(days=20))
    assert resolve_due_predictions()["blind"] == 1

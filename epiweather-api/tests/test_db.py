"""DB 계층 — upsert 멱등성과 예측 검증(create → verify → accuracy_stats) 흐름.
'적중률' 수치가 실제로 신뢰 가능한 계산식에서 나오는지 확인."""
from __future__ import annotations


def test_upsert_alert_same_date_and_source_updates_not_duplicates(isolated_db):
    db = isolated_db
    db.upsert_alert("2026-07-20", "gai", "🟠 경보", "GAI 상승", 82.0)
    db.upsert_alert("2026-07-20", "gai", "🔴 위험", "GAI 추가상승", 91.0)

    rows = db.list_alerts("2026-07-20")
    assert len(rows) == 1
    assert rows[0]["score"] == 91.0
    assert rows[0]["tier"] == "🔴 위험"


def test_upsert_alert_different_source_creates_separate_rows(isolated_db):
    db = isolated_db
    db.upsert_alert("2026-07-20", "gai", "🟡 주의", "a", 70.0)
    db.upsert_alert("2026-07-20", "negative_space", "🟡 주의", "b", 71.0)

    assert len(db.list_alerts("2026-07-20")) == 2


def test_prediction_lifecycle_create_verify_accuracy(isolated_db):
    db = isolated_db
    pred = db.create_prediction("Thailand", "뎅기열", 82.0, ["근거1", "근거2"])
    assert pred["verified_at"] is None
    assert pred["basis"] == ["근거1", "근거2"]

    verified = db.verify_prediction(pred["id"], "실제 발생", True, lead_days=5)
    assert verified["correct"] is True
    assert verified["lead_days"] == 5

    stats = db.accuracy_stats(country="Thailand")
    assert stats["total_verified"] == 1
    assert stats["correct"] == 1
    assert stats["accuracy"] == 1.0
    assert stats["mean_lead_days"] == 5.0


def test_accuracy_stats_empty_when_nothing_verified(isolated_db):
    db = isolated_db
    db.create_prediction("Thailand", "뎅기열", 82.0, ["근거"])  # 검증 안 함

    stats = db.accuracy_stats(country="Thailand")
    assert stats["total_verified"] == 0
    assert stats["accuracy"] is None


def test_verify_nonexistent_prediction_returns_none(isolated_db):
    db = isolated_db
    assert db.verify_prediction(999999, "x", True) is None

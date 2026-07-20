"""DB 계층 — upsert 멱등성과 예측 검증(create → verify → accuracy_stats) 흐름.
'적중률' 수치가 실제로 신뢰 가능한 계산식에서 나오는지 확인."""
from __future__ import annotations
import sqlite3


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


def test_api_key_usage_summary_groups_by_label(isolated_db):
    db = isolated_db
    db.log_api_key_usage("default", "/api/civic-fusion")
    db.log_api_key_usage("default", "/api/predictions")
    db.log_api_key_usage("partnerA", "/api/civic-fusion")

    summary = db.api_key_usage_summary(days=30)
    by_label = {row["key_label"]: row["call_count"] for row in summary}
    assert by_label == {"default": 2, "partnerA": 1}


def test_api_key_usage_summary_excludes_old_calls_outside_window(isolated_db):
    db = isolated_db
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO api_key_usage (key_label, endpoint, called_at) VALUES (?, ?, ?)",
            ("stale", "/api/civic-fusion", "2020-01-01T00:00:00+00:00"),
        )
        conn.commit()
    db.log_api_key_usage("fresh", "/api/civic-fusion")

    summary = db.api_key_usage_summary(days=30)
    labels = {row["key_label"] for row in summary}
    assert "fresh" in labels
    assert "stale" not in labels


def _make_sentinel_item(db, layer="behavioral", metric="naver_flu_ratio"):
    sid = db.upsert_sentinel(
        detected_at="2026-07-20", layer=layer, metric=metric,
        spike_ratio=2.5, latest_val=100.0, baseline_avg=40.0,
    )
    return sid


def test_ai_verification_records_ai_status_and_label(isolated_db):
    db = isolated_db
    sid = _make_sentinel_item(db)
    db.update_sentinel_verification(sid, "confirmed", "근거 텍스트", 0.8, verified_by="ai")

    row = next(r for r in db.list_sentinel_queue() if r["id"] == sid)
    assert row["status"] == "confirmed"
    assert row["verified_by"] == "ai"
    assert row["ai_status"] == "confirmed"
    assert row["ai_confidence"] == 0.8


def test_human_override_preserves_original_ai_verdict(isolated_db):
    """사람이 AI 판정을 뒤집어도 ai_status는 그대로 남아야 비교가 가능함."""
    db = isolated_db
    sid = _make_sentinel_item(db)
    db.update_sentinel_verification(sid, "confirmed", "AI 근거", 0.7, verified_by="ai")
    db.update_sentinel_verification(sid, "dismissed", "사람이 오탐으로 판단", None, verified_by="human")

    row = next(r for r in db.list_sentinel_queue() if r["id"] == sid)
    assert row["status"] == "dismissed"        # 최종 판정은 사람 것
    assert row["verified_by"] == "human"
    assert row["ai_status"] == "confirmed"      # AI의 원래 판정은 보존됨


def test_verification_accuracy_empty_when_no_human_review(isolated_db):
    db = isolated_db
    sid = _make_sentinel_item(db)
    db.update_sentinel_verification(sid, "confirmed", "근거", 0.9, verified_by="ai")

    result = db.sentinel_verification_accuracy()
    assert result["total_compared"] == 0
    assert result["agreement_rate"] is None


def test_verification_accuracy_computes_agreement_rate(isolated_db):
    db = isolated_db
    sid1 = _make_sentinel_item(db, metric="metric_a")
    sid2 = _make_sentinel_item(db, metric="metric_b")

    # 1건은 AI·사람 판정 일치, 1건은 불일치
    db.update_sentinel_verification(sid1, "confirmed", "e1", 0.8, verified_by="ai")
    db.update_sentinel_verification(sid1, "confirmed", "e1-human", None, verified_by="human")
    db.update_sentinel_verification(sid2, "confirmed", "e2", 0.6, verified_by="ai")
    db.update_sentinel_verification(sid2, "dismissed", "e2-human", None, verified_by="human")

    result = db.sentinel_verification_accuracy()
    assert result["total_compared"] == 2
    assert result["agreed"] == 1
    assert result["agreement_rate"] == 0.5


def test_schema_migration_adds_columns_to_pre_existing_table(tmp_path, monkeypatch):
    """새 컬럼 도입 전에 이미 만들어진(운영 중이던) DB에도 init_db()가
    안전하게 컬럼을 추가해주는지 — 배포 시 실제로 벌어질 상황을 재현."""
    import db as dbmod

    old_schema = """
    CREATE TABLE sentinel_queue (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        detected_at  TEXT NOT NULL,
        layer        TEXT NOT NULL,
        metric       TEXT NOT NULL,
        spike_ratio  REAL NOT NULL,
        latest_val   REAL NOT NULL,
        baseline_avg REAL NOT NULL,
        status       TEXT NOT NULL DEFAULT 'pending',
        evidence     TEXT,
        confidence   REAL,
        verified_at  TEXT,
        UNIQUE(detected_at, layer, metric)
    );
    """
    old_db_path = tmp_path / "old.db"
    conn = sqlite3.connect(old_db_path)
    conn.executescript(old_schema)
    conn.commit()
    conn.close()

    monkeypatch.setattr(dbmod, "DB_PATH", old_db_path)
    dbmod.init_db()  # 마이그레이션 트리거
    dbmod.init_db()  # 두 번째 호출도 에러 없이 통과해야 함(멱등성)

    columns = {row[1] for row in sqlite3.connect(old_db_path).execute("PRAGMA table_info(sentinel_queue)")}
    assert {"verified_by", "ai_status", "ai_confidence"} <= columns


def test_table_counts_reflects_inserted_rows(isolated_db):
    db = isolated_db
    counts_before = db.table_counts()
    assert counts_before["predictions"] == 0
    assert counts_before["alerts"] == 0

    db.create_prediction("Thailand", "뎅기열", 82.0, ["근거"])
    db.upsert_alert("2026-07-20", "gai", "🟡 주의", "a", 70.0)

    counts_after = db.table_counts()
    assert counts_after["predictions"] == 1
    assert counts_after["alerts"] == 1
    # /api/status가 참조하는 모든 테이블이 빠짐없이 포함되는지
    assert set(counts_after) == {
        "predictions", "alerts", "extracted_signals", "sentinel_queue", "outbreak_timeline",
    }

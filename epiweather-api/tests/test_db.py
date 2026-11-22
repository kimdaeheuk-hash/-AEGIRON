"""DB 계층 — API 키 사용량·표 행 수."""
from __future__ import annotations


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



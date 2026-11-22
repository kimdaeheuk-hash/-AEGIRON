"""DB 스키마 버전·인덱스·FK 기본값. isolated_db 격리."""
from __future__ import annotations


def _indexes(db):
    with db.get_connection() as conn:
        return {r[0] for r in
                conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}


def test_init_stamps_schema_version(isolated_db):
    db = isolated_db
    with db.get_connection() as conn:
        row = conn.execute("SELECT version FROM _schema_version WHERE id = 1").fetchone()
    assert row[0] == db.SCHEMA_VERSION


def test_second_init_skips_ddl(isolated_db, monkeypatch):
    db = isolated_db
    calls = []
    orig = db._migrate

    def spy(conn):
        calls.append(1)
        return orig(conn)

    monkeypatch.setattr(db, "_migrate", spy)
    db.init_db()
    assert calls == []  # 버전 일치 → 마이그레이션 미실행


def test_legacy_db_is_repaired(isolated_db):
    db = isolated_db
    with db.get_connection() as conn:
        conn.execute("DROP INDEX idx_match_ledger_date")
        conn.execute("DELETE FROM _schema_version WHERE id = 1")
        conn.commit()
    db.init_db()  # 구 DB 취급 → 전문 + 버전 재기록
    assert "idx_match_ledger_date" in _indexes(db)
    with db.get_connection() as conn:
        row = conn.execute("SELECT version FROM _schema_version WHERE id = 1").fetchone()
    assert row[0] == db.SCHEMA_VERSION


def test_expected_indexes_exist(isolated_db):
    db = isolated_db
    have = _indexes(db)
    for name in [
        "idx_variant_ledger_build_observed",
        "idx_match_ledger_date",
        "idx_observations_key",
        "idx_observations_layer_time",
        "idx_api_usage_label_called",
    ]:
        assert name in have, name


def test_foreign_keys_enforced_by_default(isolated_db):
    db = isolated_db
    with db.get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

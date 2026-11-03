"""변이 상태원장 — 병원체 상태 전이를 놓치지 않고, 지어내지도 않는다 (2026-11-03).

## 이 파일이 지키는 것

- 첫 기록은 first_seen — 이전 상태를 지어내지 않는다.
- 같은 우세 + 신규 없음이면 전이 아님(none).
- 우세가 바뀌면 dominant_changed, 신규만 나면 new_clade.
- available=False 주기는 적지 않는다 — 없는 관측을 "변화 없음"으로
  적으면 거짓말이 된다.

isolated_db 픽스처라 운영 DB를 건드리지 않는다. 외부 HTTP 없음.
"""
from __future__ import annotations

import datetime as dt

from algorithms.variant_ledger import (
    list_entries,
    list_transitions,
    record_cycle,
)

UTC = dt.timezone.utc


def _sig(label="SARS-CoV-2", dominant="JN.1", share=0.4, n=100,
         new=None, updated="2026-11-01"):
    return {
        "label": label, "available": True, "build_updated": updated,
        "n_recent_sequences": n, "n_prior_sequences": n,
        "dominant_clade": dominant, "dominant_share": share,
        "new_clades": list(new or []), "new_clade_count": len(new or []),
        "note": None,
    }


def _dead(label="SARS-CoV-2"):
    return {"label": label, "available": False, "reason": "Nextstrain API 응답 실패"}


def _at(h):
    return dt.datetime(2026, 11, 3, h, tzinfo=UTC)


def test_first_cycle_is_first_seen(isolated_db):
    """첫 기록은 first_seen — 이전 우세를 지어내지 않는다."""
    rows = record_cycle({"ncov": _sig()}, now=_at(1))
    assert len(rows) == 1
    assert rows[0]["transition"] == "first_seen"
    assert rows[0]["prev_dominant"] is None
    assert rows[0]["dominant_clade"] == "JN.1"


def test_unchanged_cycle_is_none(isolated_db):
    """같은 우세 + 신규 없음이면 전이 아님."""
    record_cycle({"ncov": _sig()}, now=_at(1))
    rows = record_cycle({"ncov": _sig()}, now=_at(2))
    assert rows[0]["transition"] == "none"
    assert rows[0]["prev_dominant"] == "JN.1"


def test_dominant_change_opens_transition(isolated_db):
    """우세가 바뀌면 dominant_changed."""
    record_cycle({"ncov": _sig(dominant="JN.1")}, now=_at(1))
    rows = record_cycle({"ncov": _sig(dominant="KP.3")}, now=_at(2))
    assert rows[0]["transition"] == "dominant_changed"
    assert rows[0]["prev_dominant"] == "JN.1"
    assert rows[0]["dominant_clade"] == "KP.3"


def test_new_clade_only_opens_new_clade(isolated_db):
    """우세는 같은데 신규가 나면 new_clade."""
    record_cycle({"ncov": _sig()}, now=_at(1))
    rows = record_cycle({"ncov": _sig(new=["XEC"])}, now=_at(2))
    assert rows[0]["transition"] == "new_clade"
    assert rows[0]["new_clades"] == ["XEC"]


def test_failed_cycle_records_nothing(isolated_db):
    """available=False 주기는 적지 않는다."""
    record_cycle({"ncov": _sig()}, now=_at(1))
    rows = record_cycle({"ncov": _dead()}, now=_at(2))
    assert rows == []
    assert len(list_entries()) == 1


def test_builds_are_independent(isolated_db):
    """빌드별로 직전 상태를 따로 본다."""
    record_cycle({"ncov": _sig(dominant="JN.1"),
                  "mpox": _sig(label="엠폭스", dominant="IIb")}, now=_at(1))
    rows = record_cycle({"ncov": _sig(dominant="KP.3"),
                         "mpox": _sig(label="엠폭스", dominant="IIb")}, now=_at(2))
    by_build = {r["build"]: r["transition"] for r in rows}
    assert by_build == {"ncov": "dominant_changed", "mpox": "none"}


def test_list_transitions_skips_none(isolated_db):
    """transitions 조회는 none을 제외한다."""
    record_cycle({"ncov": _sig()}, now=_at(1))
    record_cycle({"ncov": _sig()}, now=_at(2))
    record_cycle({"ncov": _sig(dominant="KP.3")}, now=_at(3))
    got = list_transitions()
    assert [r["transition"] for r in got] == ["dominant_changed", "first_seen"]
    assert len(list_entries()) == 3


def test_endpoint_lists_entries(isolated_db):
    """핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다."""
    import main as main_mod

    record_cycle({"ncov": _sig()}, now=_at(1))
    record_cycle({"ncov": _sig()}, now=_at(2))
    full = main_mod.variant_ledger()
    assert full["count"] == 2
    trans = main_mod.variant_ledger(transitions_only=True)
    assert trans["count"] == 1
    assert trans["entries"][0]["transition"] == "first_seen"
    scoped = main_mod.variant_ledger(build="mpox")
    assert scoped["count"] == 0


def test_migration_creates_table_on_old_db(isolated_db):
    """★★배포 실측★★ 구 버전 DB에도 테이블이 생긴다.

    IF NOT EXISTS라도 _migrate 자체가 버전 게이트 뒤에 있어서,
    SCHEMA_VERSION을 안 올리면 운영 DB에 테이블이 안 생기고 엔드포인트가
    500이 된다. 구 버전 스탬프(v2, 테이블 없음)에서 init_db가 따라잡는지 본다.
    """
    import db as dbmod

    assert dbmod.SCHEMA_VERSION >= 3
    with dbmod.get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version ("
            "id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL)"
        )
        conn.execute("INSERT OR REPLACE INTO _schema_version (id, version) VALUES (1, 2)")
        conn.commit()
    dbmod.init_db()
    with dbmod.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'variant_ledger'"
        ).fetchone()
        assert row is not None
    rows = record_cycle({"ncov": _sig()}, now=_at(1))
    assert rows[0]["transition"] == "first_seen"

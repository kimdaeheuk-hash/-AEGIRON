"""전송 기록 — 보낸 것만 '보낸 것'으로 센다 (캡틴 지시 9번, 2026-10-04).

## 배경

#53 의 이월 규칙은 전송 기록이 없어서 '어제 화면에 떠 있던 것'을 '보낸 것'으로 간주했다. 그래서
**전송이 실패한 critical 이 다음 날 '이미 본 것'이 되어 재시도되지 않았다** — 있는 경보를 없는
것으로 만드는 방향이다. 이제 `alerts.notified_rank` 에 *전송 성공한 최고 등급* 만 기록하고, 채널이
설정돼 있으면 그 기록을 기준선으로 쓴다.

- 성공 → 기록. 같은 등급은 다시 안 나간다(오늘도, 날이 바뀌어도).
- 실패 → 기록 안 함. 다음 주기에 다시 시도한다.
- 채널 미설정 → 기록 안 함, 재시도 안 함(보낼 곳이 없다). 예전처럼 '잡힌 행 = 본 것'.
- 마이그레이션 시점의 옛 critical/high 행은 '보낸 것으로 간주'한다(안 그러면 배포 직후 재전송).
"""
from __future__ import annotations

import sqlite3

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import (NOTIFY_FAILED, NOTIFY_NONE, NOTIFY_SENT, TIER_RANK, baseline_rank,
                               notified_rank_of, refresh_alerts, summary_line)


def _candidate(source, score, label="테스트 경보"):
    return {"source": source, "label": label, "score": score, "evidence": ["근거"]}


def _setup(monkeypatch, candidates, *, configured=True, outcome=NOTIFY_SENT):
    """채널 설정 여부와 전송 결과를 정해서 refresh_alerts 를 돌릴 준비. 시도 목록을 돌려준다."""
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: list(candidates))
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: configured)
    attempts: list[list[str]] = []

    def notify(new):
        attempts.append([r["source"] for r in new])
        if not new:
            return {"status": NOTIFY_NONE, "new_critical_high": 0}
        return {"status": outcome, "new_critical_high": len(new)}

    monkeypatch.setattr(alerts_mod, "_notify", notify)
    return attempts


# ── 성공은 기록되고 다시 안 나간다 ───────────────────────────

def test_successful_send_is_recorded_with_its_tier(isolated_db, monkeypatch):
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-04")
    assert attempts == [["a"]]
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] == TIER_RANK["critical"]


def test_sent_alert_is_not_resent_the_same_day(isolated_db, monkeypatch):
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-04")
    refresh_alerts("2026-10-04")
    assert attempts == [["a"], []]


def test_sent_alert_is_not_resent_after_midnight(isolated_db, monkeypatch):
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-03")
    refresh_alerts("2026-10-04")
    assert attempts == [["a"], []]


def test_escalation_after_a_successful_send_notifies_again(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 85.0)])                      # high
    refresh_alerts("2026-10-04")
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])           # critical
    refresh_alerts("2026-10-04")
    assert attempts == [["a"]]
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] == TIER_RANK["critical"]


def test_easing_does_not_lower_the_recorded_rank(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-04")
    attempts = _setup(monkeypatch, [_candidate("a", 85.0)])           # critical → high
    refresh_alerts("2026-10-04")
    assert attempts == [[]]                                           # 완화는 새 소식이 아니다
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] == TIER_RANK["critical"]


# ── 실패는 기록되지 않고 재시도된다 ──────────────────────────

def test_failed_send_is_not_recorded_and_is_retried_next_cycle(isolated_db, monkeypatch):
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_FAILED)
    first = refresh_alerts("2026-10-04")
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] is None
    assert first["notification"]["retry_pending"] == 1
    refresh_alerts("2026-10-04")
    assert attempts == [["a"], ["a"]]                                 # 다음 주기에 다시 시도


def test_failed_send_is_retried_the_next_day_too(isolated_db, monkeypatch):
    """#53 의 구멍 — 어제 전송이 실패했는데 오늘 '이미 본 것'이 되어 조용해지던 것."""
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_FAILED)
    refresh_alerts("2026-10-03")
    refresh_alerts("2026-10-04")
    assert attempts == [["a"], ["a"]]


def test_retry_succeeds_and_then_stops(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_FAILED)
    refresh_alerts("2026-10-04")
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_SENT)
    refresh_alerts("2026-10-04")
    refresh_alerts("2026-10-04")
    assert attempts == [["a"], []]
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] == TIER_RANK["critical"]


def test_summary_line_names_the_retry_pending_count(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_FAILED)
    line = summary_line(refresh_alerts("2026-10-04"))
    assert "알림: 전송 실패" in line and "미전송 1건, 다음 주기에 재시도" in line


def test_summary_line_has_no_retry_note_when_sent(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0)], outcome=NOTIFY_SENT)
    assert "재시도" not in summary_line(refresh_alerts("2026-10-04"))


# ── 채널 미설정이면 예전 동작 ────────────────────────────────

def test_unconfigured_channel_records_nothing_and_does_not_retry(isolated_db, monkeypatch):
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)], configured=False, outcome="채널 미설정")
    refresh_alerts("2026-10-04")
    refresh_alerts("2026-10-04")
    assert db.list_alerts("2026-10-04")[0]["notified_rank"] is None   # 거짓으로 '보냄'을 적지 않는다
    assert attempts == [["a"], []]                                    # 매 주기 만들지 않는다


# ── 기준선 함수 ─────────────────────────────────────────────

def test_notified_rank_of_ignores_unsent_rows_and_keeps_the_max():
    rows = [
        {"source": "a", "tier": "critical", "notified_rank": None},
        {"source": "b", "tier": "critical", "notified_rank": 3},
        {"source": "b", "tier": "high", "notified_rank": 2},
    ]
    assert notified_rank_of(rows) == {"b": 3}


def test_baseline_uses_sent_records_when_configured_and_seen_rows_otherwise():
    today = [{"source": "a", "tier": "critical", "notified_rank": None, "suppressed": 0}]
    assert baseline_rank(today, [], True) == {}                       # 안 보냈다 → 기준선 없음
    assert baseline_rank(today, [], False) == {"a": TIER_RANK["critical"]}


def test_yesterdays_sent_record_counts_even_if_the_row_was_retired(isolated_db, monkeypatch):
    """보낸 사실은 행이 내려갔어도 남는다 — 어제 알렸는데 오늘 같은 등급을 또 알리지 않는다."""
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-03")
    _setup(monkeypatch, [])
    refresh_alerts("2026-10-03")                                      # 내려감(suppressed)
    attempts = _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-04")
    assert attempts == [[]]


# ── 마이그레이션 ────────────────────────────────────────────

def test_migration_backfills_old_critical_and_high_rows_once(tmp_path, monkeypatch):
    """옛 DB(전송 기록 열이 없던) 를 열면 critical/high 행은 '보낸 것으로 간주'되고, 이후엔 안 건드린다."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, alert_date TEXT NOT NULL, source TEXT NOT NULL,
            tier TEXT NOT NULL, label TEXT NOT NULL, score REAL NOT NULL, evidence TEXT,
            suppressed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(alert_date, source));
    """)
    for src, tier in (("c", "critical"), ("h", "high"), ("m", "medium"), ("l", "low")):
        conn.execute("INSERT INTO alerts (alert_date, source, tier, label, score, created_at, updated_at) "
                     "VALUES ('2026-10-04', ?, ?, 'x', 90, 't', 't')", (src, tier))
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", path, raising=False)
    db.init_db()
    rows = {r["source"]: r["notified_rank"] for r in db.list_alerts("2026-10-04")}
    assert rows == {"c": 3, "h": 2, "m": None, "l": None}

    # 두 번째 init_db — 컬럼이 이미 있으니 채우기를 다시 하지 않는다(새 행의 NULL 을 덮지 않는다).
    conn = sqlite3.connect(path)
    conn.execute("UPDATE alerts SET notified_rank = NULL WHERE source = 'c'")
    conn.commit()
    conn.close()
    db.init_db()
    assert {r["source"]: r["notified_rank"] for r in db.list_alerts("2026-10-04")}["c"] is None


def test_refresh_alerts_wires_the_record_on_success_only():
    """배선 — 만들어만 두고 아무도 안 부르는 층 방지."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(refresh_alerts).strip())
    called = {n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "mark_alerts_notified" in called
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "NOTIFY_SENT" in names                                      # 성공일 때만 기록한다

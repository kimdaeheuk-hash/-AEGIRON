"""관측 대기 항목(수리 목록 1~4번)을 값으로 판정할 수 있게 하는 로그 줄 (2026-10-04).

1. 00:01 이월 — `알림: 보낼 신규 경보 없음` 만으로는 '울릴 게 없어서'인지 '있는데 이미 알려서'인지
   '어제 알려서(이월)'인지 못 가른다 → `🔕 재통보 안 함` 줄.
2. 무역 `8개국` 이 정상인지 — 달별 행 수가 줄에 없었다 → `[행 a/b/…]`.
3. 기준 스냅샷 파일이 재배포로 사라진 뒤 주간작업이 왜 안 채웠나 — 추정뿐이었다 → 시작 시
   `주간 작업: 마지막 실행 …` 줄.
4. `⏸ 판정 안 함` — 줄은 이미 있다(test_day_carryover_and_scan_hold). 프로덕션에서 아직 못 봤을 뿐이다.
"""
from __future__ import annotations

import datetime as dt
import time

import main
from algorithms import alerts as alerts_mod
from algorithms import comtrade_signals as cs
from algorithms.alerts import (NOTIFY_SENT, already_notified_line, refresh_alerts)


def _candidate(source, score, label="테스트 경보"):
    return {"source": source, "label": label, "score": score, "evidence": ["근거"]}


def _setup(monkeypatch, candidates, *, configured=True, outcome=NOTIFY_SENT):
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: list(candidates))
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: configured)
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (
        {"status": outcome, "new_critical_high": len(new)} if new
        else {"status": "보낼 신규 경보 없음", "new_critical_high": 0}))


# ── 1. 재통보 안 함 ─────────────────────────────────────────

def test_nothing_is_listed_when_the_alert_was_just_sent(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0)])
    result = refresh_alerts("2026-10-04")
    assert result["already_notified"] == []                 # 방금 보냈다 — 안 보낸 게 아니다
    assert already_notified_line(result) is None


def test_same_day_repeat_is_attributed_to_today(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("a", 95.0, "콜레라")])
    refresh_alerts("2026-10-04")
    result = refresh_alerts("2026-10-04")
    assert [(r["source"], r["origin"]) for r in result["already_notified"]] == [("a", "오늘")]
    line = already_notified_line(result)
    assert line.startswith("🔕 재통보 안 함:") and "콜레라" in line and "(오늘)" in line


def test_midnight_repeat_is_attributed_to_yesterday(isolated_db, monkeypatch):
    """00:01 의 모양 — 어제 알린 같은 critical 이 새 날 표에 처음 나타났다. 이월 덕에 안 나갔다."""
    _setup(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-10-03")
    result = refresh_alerts("2026-10-04")
    assert [(r["source"], r["origin"]) for r in result["already_notified"]] == [("a", "어제 이월")]
    assert "(어제 이월)" in already_notified_line(result)


def test_lower_tiers_are_never_listed(isolated_db, monkeypatch):
    _setup(monkeypatch, [_candidate("m", 75.0)])            # medium
    refresh_alerts("2026-10-04")
    assert refresh_alerts("2026-10-04")["already_notified"] == []


def test_failed_send_is_not_called_already_notified(isolated_db, monkeypatch):
    """전송이 실패한 것은 '이미 알림'이 아니다 — 다음 주기에 재시도되므로 이 줄에 안 나온다."""
    _setup(monkeypatch, [_candidate("a", 95.0)], outcome="전송 실패")
    refresh_alerts("2026-10-04")
    assert refresh_alerts("2026-10-04")["already_notified"] == []


def test_main_cycle_logs_the_line():
    import ast
    import inspect
    names = {n.id for n in ast.walk(ast.parse(inspect.getsource(main._run_alert_cycle)))
             if isinstance(n, ast.Name)}
    assert "already_notified_line" in names


# ── 2. 무역 달별 행 수 ──────────────────────────────────────

def _scan_with(fetch):
    return {"products": {"masks": {"data_available": True, "countries_observed": 8, "fetch": fetch}}}


def test_scan_line_shows_rows_oldest_to_newest():
    fetch = {"months_total": 6, "months_ok": 6,
             "rows_by_period": {"202608": 9, "202603": 120, "202604": 118, "202605": 95,
                                "202606": 60, "202607": 31}}
    cs._record_call(_scan_with(fetch), scanned_at=time.time(), cache_hit=False, cached=True)
    line = cs.trade_scan_line()
    assert "[행 120/118/95/60/31/9]" in line           # 키 정렬 — 오래된 달 → 최신 달
    assert "→ 8개국" in line


def test_scan_line_without_row_data_has_no_row_note():
    cs._record_call(_scan_with({"months_total": 6, "months_ok": 6}),
                    scanned_at=time.time(), cache_hit=False, cached=True)
    assert "[행" not in cs.trade_scan_line()


def test_real_fetch_fills_rows_by_period_in_the_line(monkeypatch):
    """실제 수집 경로로 — fetch_public_month 가 달별 행 수를 notes 에 남기고 줄이 읽는다."""
    from unittest.mock import MagicMock, patch

    def resp(n):
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = {"data": [{"reporterISO": f"C{i}", "primaryValue": 1.0} for i in range(n)]}
        return r

    sizes = [50, 40, 30, 20, 10, 5]
    notes: dict = {}
    with patch.object(cs.requests, "get", side_effect=[resp(n) for n in sizes]):
        cs.fetch_public_series("630790", months=6, notes=notes)
    assert [notes["rows_by_period"][k] for k in sorted(notes["rows_by_period"])] == sizes


# ── 3. 주간작업 상태 줄 ─────────────────────────────────────

def _now():
    return dt.datetime(2026, 10, 4, 12, 0, tzinfo=dt.timezone.utc)


def test_weekly_line_says_no_record_when_state_file_is_gone(monkeypatch):
    monkeypatch.setattr(main, "_load_last_weekly_run", lambda: None)
    line = main._weekly_state_line(_now())
    assert "기록 없음" in line and "이번 시작에서 실행" in line


def test_weekly_line_says_how_long_to_wait_when_recent(monkeypatch):
    last = _now() - dt.timedelta(days=2)
    monkeypatch.setattr(main, "_load_last_weekly_run", lambda: last)
    line = main._weekly_state_line(_now())
    assert "2일 전" in line and "다음 실행까지 약 5.0일" in line


def test_weekly_line_says_due_when_a_week_has_passed(monkeypatch):
    last = _now() - dt.timedelta(days=8)
    monkeypatch.setattr(main, "_load_last_weekly_run", lambda: last)
    line = main._weekly_state_line(_now())
    assert "8일 전" in line and "이번 시작에서 실행" in line


def test_scheduler_logs_the_weekly_line_at_start():
    import ast
    import inspect
    calls = {n.func.id for n in ast.walk(ast.parse(inspect.getsource(main._scheduler_loop)))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_weekly_state_line" in calls

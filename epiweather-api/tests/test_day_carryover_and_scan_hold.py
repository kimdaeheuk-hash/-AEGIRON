"""날짜가 바뀌어도 '진행 중' 경보는 새 소식이 아니다 + 스캔이 못 낸 것은 내림이 아니다.

## 배경 (2026-10-04)

C. social_cholera critical 이 10-03 에 폰으로 나가고 10-04 00:01 에 **같은 경보가 다시**
   나갔다. `alerts` 는 날짜별 행이라 날이 바뀌면 오늘 표가 비고, 어제부터 이어지던 critical 이
   '오늘 처음 보는 것'이 됐다. 같은 등급으로 이어지는 경보는 새 소식이 아니다 — 날짜 경계에서만
   그 원칙이 깨져 있었다.

3. `내림` 은 '값이 내려갔다'와 '스캔이 못 냈다'를 가르지 못했다. 무역 스캔이 일부 실패한 주기에
   후보가 없는 것은 급증이 없다는 뜻이 아니라 **모른다**는 뜻이다.

2. 일부 실패한 스캔이 6시간 캐시되면 일시 장애가 '없는 경보'로 굳는다.

행 수 기록: 500행 상한에 닿은 달은 뒤쪽 국가가 잘렸을 수 있다 — 가설을 가를 근거를 남긴다.
"""
from __future__ import annotations

from unittest.mock import patch

import db
from algorithms import alerts as alerts_mod
from algorithms import comtrade_signals as cs
from algorithms.alerts import (carried_rank_from_yesterday, escalated, merge_seen_rank,
                               refresh_alerts, undetermined_alerts_line)


def _candidate(source, score, label="테스트 경보"):
    return {"source": source, "label": label, "score": score, "evidence": ["근거"]}


def _stub(monkeypatch, candidates, *, undetermined=()):
    def collect(today, negative_space=None):
        for p in undetermined:
            alerts_mod._mark_undetermined(p)
        return list(candidates)

    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts", collect)
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    sent: list[list[str]] = []

    def notify(new):
        sent.append([r["source"] for r in new])
        return {"status": "전송됨" if new else "보낼 신규 경보 없음", "new_critical_high": len(new)}

    monkeypatch.setattr(alerts_mod, "_notify", notify)
    return sent


# ── C. 날짜 경계 ─────────────────────────────────────────────

def test_ongoing_critical_is_not_resent_at_midnight(isolated_db, monkeypatch):
    """10-03 → 10-04 00:01 의 모양 그대로 — 어제 화면에 떠 있던 critical 은 다시 안 나간다."""
    sent = _stub(monkeypatch, [_candidate("gai:behavioral.social_cholera", 90.0)])
    refresh_alerts("2026-10-03")
    assert sent == [["gai:behavioral.social_cholera"]]       # 어제는 나갔다

    refresh_alerts("2026-10-04")                              # 날이 바뀐 첫 주기
    assert sent[-1] == []                                     # 새 소식이 아니다


def test_escalation_across_midnight_still_notifies(isolated_db, monkeypatch):
    """어제 high 였다가 오늘 critical 로 올라가면 날짜와 상관없이 새 소식이다."""
    sent = _stub(monkeypatch, [_candidate("x", 85.0)])         # high
    refresh_alerts("2026-10-03")
    _stub_sent = _stub(monkeypatch, [_candidate("x", 95.0)])   # critical
    refresh_alerts("2026-10-04")
    assert _stub_sent == [["x"]]


def test_alert_that_was_not_visible_yesterday_is_new_today(isolated_db, monkeypatch):
    """어제 내려갔던(suppressed) 행은 어제 화면에 없었다 — 오늘 되살아나면 새 소식이다."""
    sent = _stub(monkeypatch, [_candidate("x", 95.0)])
    refresh_alerts("2026-10-03")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-03")                               # 후보에서 빠져 내려감
    assert all(r["suppressed"] for r in db.list_alerts("2026-10-03"))

    sent3 = _stub(monkeypatch, [_candidate("x", 95.0)])
    refresh_alerts("2026-10-04")
    assert sent3 == [["x"]]


def test_never_seen_source_notifies_as_before(isolated_db, monkeypatch):
    sent = _stub(monkeypatch, [_candidate("fresh", 95.0)])
    refresh_alerts("2026-10-04")
    assert sent == [["fresh"]]


def test_carried_rank_ignores_suppressed_rows_and_keeps_max():
    rows = [
        {"source": "a", "tier": "critical", "suppressed": 0},
        {"source": "a", "tier": "low", "suppressed": 0},
        {"source": "b", "tier": "critical", "suppressed": 1},
    ]
    out = carried_rank_from_yesterday(rows)
    assert out == {"a": alerts_mod.TIER_RANK["critical"]}


def test_merge_takes_the_higher_rank_of_today_and_carried():
    merged = merge_seen_rank({"a": 1, "b": 3}, {"a": 2, "c": 0})
    assert merged == {"a": 2, "b": 3, "c": 0}
    assert escalated("a", "high", merged) is False   # high(2) 는 이미 본 등급
    assert escalated("a", "critical", merged) is True


def test_year_boundary_looks_at_dec_31(isolated_db, monkeypatch):
    sent = _stub(monkeypatch, [_candidate("y", 95.0)])
    refresh_alerts("2026-12-31")
    sent2 = _stub(monkeypatch, [_candidate("y", 95.0)])
    refresh_alerts("2027-01-01")
    assert sent2 == [[]]


# ── 3. 판정 안 함 ───────────────────────────────────────────

def test_trade_row_is_held_not_retired_when_scan_was_incomplete(isolated_db, monkeypatch):
    _stub(monkeypatch, [_candidate("trade_surge:BLZ", 72.0, "의료물자 수입 동시 급증 · BLZ (2 품목)")])
    first = refresh_alerts("2026-10-04")
    assert first["tier_summary"]["high"]["total"] + first["tier_summary"]["medium"]["total"] == 1

    _stub(monkeypatch, [], undetermined=["trade_surge:"])      # 스캔이 못 냈다
    second = refresh_alerts("2026-10-04")
    assert second["retired"] == []
    assert [r["source"] for r in second["undetermined"]] == ["trade_surge:BLZ"]
    row = db.list_alerts("2026-10-04")[0]
    assert row["suppressed"] == 0                              # 지우지도, 내리지도 않았다


def test_trade_row_is_retired_when_scan_was_complete(isolated_db, monkeypatch):
    """스캔이 온전했는데 후보가 없으면 그건 진짜로 내려간 것이다 — 기존 동작 그대로."""
    _stub(monkeypatch, [_candidate("trade_surge:BLZ", 72.0)])
    refresh_alerts("2026-10-04")
    _stub(monkeypatch, [])
    result = refresh_alerts("2026-10-04")
    assert [r["source"] for r in result["retired"]] == ["trade_surge:BLZ"]
    assert result["undetermined"] == []


def test_undetermined_only_covers_the_failed_family(isolated_db, monkeypatch):
    """무역 스캔이 실패해도 다른 계열이 후보에서 빠지면 그건 그대로 내려간다."""
    _stub(monkeypatch, [_candidate("trade_surge:BLZ", 72.0), _candidate("gai:x.y", 72.0)])
    refresh_alerts("2026-10-04")
    _stub(monkeypatch, [], undetermined=["trade_surge:"])
    result = refresh_alerts("2026-10-04")
    assert [r["source"] for r in result["retired"]] == ["gai:x.y"]
    assert [r["source"] for r in result["undetermined"]] == ["trade_surge:BLZ"]


def test_undetermined_line_is_separate_from_retired_line():
    assert undetermined_alerts_line({"undetermined": []}) is None
    line = undetermined_alerts_line({"undetermined": [
        {"tier": "medium", "label": "무역 BLZ", "score": 72.0, "source": "trade_surge:BLZ"}]})
    assert line.startswith("⏸ 판정 안 함:") and "trade_surge:BLZ" in line and "내림" not in line


def test_collect_marks_undetermined_when_trade_scan_raises(monkeypatch):
    """스캔이 예외로 죽은 주기 — '후보 없음'이 아니라 '모름'으로 알린다."""
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: {"gai": None, "layers": {}})
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    bucket: list[str] = []
    token = alerts_mod._UNDETERMINED.set(bucket)
    try:
        with patch("algorithms.comtrade_signals.trade_alert_candidates",
                   side_effect=RuntimeError("boom")):
            alerts_mod.collect_candidate_alerts(
                "2026-10-04", {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}})
    finally:
        alerts_mod._UNDETERMINED.reset(token)
    assert bucket == ["trade_surge:"]


def test_collect_does_not_claim_incomplete_from_a_stale_call(monkeypatch):
    """낡은 호출 기록으로 이번 주기를 '판정 안 함'으로 돌리지 않는다."""
    import time
    old = {"called_at": time.time() - 3600, "scanned_at": 0, "cache_hit": False, "cached": True,
           "scan": {"products": {"masks": {"data_available": False}}}}
    monkeypatch.setattr(cs, "_LAST_CALL", old)
    assert cs.last_scan_incomplete() is False


def test_collect_wiring_marks_undetermined_after_candidates():
    """배선 — collect_candidate_alerts 가 last_scan_incomplete 를 실제로 부른다(만들어만 두고 안 부르는 층 방지)."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(alerts_mod.collect_candidate_alerts).lstrip())
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "last_scan_incomplete" in called and "_mark_undetermined" in called


def test_main_cycle_logs_the_undetermined_line():
    import ast
    import inspect
    import main
    tree = ast.parse(inspect.getsource(main._run_alert_cycle).lstrip())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "undetermined_alerts_line" in names


# ── 2. 부분 스캔 캐시 ───────────────────────────────────────

def _product(ok, total=6, available=True, empty=0):
    return {"data_available": available, "countries_observed": 90,
            "fetch": {"months_total": total, "months_ok": ok, "months_empty": empty}}


def test_scan_incomplete_definition():
    full = {"products": {"a": _product(6), "b": _product(6)}}
    assert cs.scan_incomplete(full) is False
    assert cs.scan_incomplete({"products": {"a": _product(6), "b": _product(5)}}) is True
    assert cs.scan_incomplete({"products": {"a": _product(6), "b": {"data_available": False}}}) is True


def test_empty_months_alone_are_not_a_failure():
    """신고가 안 들어온 최신 달이 비는 건 정상이다 — 실패로 치면 캐시가 영영 안 된다."""
    assert cs.scan_incomplete({"products": {"a": _product(6, empty=1)}}) is False


def test_unknown_diagnostics_are_not_called_a_failure():
    assert cs.scan_incomplete({"products": {"a": {"data_available": True, "fetch": {}}}}) is False


def test_partial_scan_gets_the_short_ttl():
    full = {"products": {"a": _product(6)}}
    part = {"products": {"a": _product(5)}}
    assert cs._cache_ttl(full) == cs.SCAN_CACHE_TTL_SEC
    assert cs._cache_ttl(part) == cs.PARTIAL_SCAN_CACHE_TTL_SEC
    assert cs.PARTIAL_SCAN_CACHE_TTL_SEC < 3600      # 다음 경보 주기(1시간)에는 다시 묻는다


def test_partial_cache_entry_expires_before_the_next_hourly_cycle():
    import time
    part = {"products": {"a": _product(5)}, "data_available": True}
    cs._SCAN_CACHE.clear()
    cs._SCAN_CACHE["scan:6"] = (time.time() - 20 * 60, part)     # 20분 전 부분 결과
    calls = []

    def fake_series(hs, months=6, notes=None):
        calls.append(hs)
        notes.update({"months_total": 6, "months_ok": 6, "months_empty": 0})
        return {"AAA": [1.0] * 6}

    with patch.object(cs, "fetch_public_series", fake_series):
        cs.global_trade_scan()
    cs._SCAN_CACHE.clear()
    assert calls          # 캐시를 쓰지 않고 다시 물었다


def test_full_cache_entry_still_serves_within_six_hours():
    import time
    full = {"products": {"a": _product(6)}, "data_available": True}
    cs._SCAN_CACHE.clear()
    cs._SCAN_CACHE["scan:6"] = (time.time() - 3 * 3600, full)
    with patch.object(cs, "fetch_public_series", side_effect=AssertionError("다시 묻지 않아야 함")):
        assert cs.global_trade_scan() is full
    cs._SCAN_CACHE.clear()


# ── 행 수 기록 ──────────────────────────────────────────────

class _Resp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return {"data": self._rows}


def _rows(n):
    return [{"reporterISO": f"C{i:03d}", "primaryValue": 1.0} for i in range(n)]


def test_row_count_is_noted_and_cap_is_flagged():
    notes: dict = {}
    with patch.object(cs.requests, "get", return_value=_Resp(_rows(cs.PUBLIC_MAX_RECORDS))):
        cs.fetch_public_month("630790", "202608", notes=notes)
    assert notes["rows_by_period"]["202608"] == cs.PUBLIC_MAX_RECORDS
    assert notes["capped_months"] == 1


def test_under_cap_is_not_flagged():
    notes: dict = {}
    with patch.object(cs.requests, "get", return_value=_Resp(_rows(120))):
        cs.fetch_public_month("630790", "202608", notes=notes)
    assert notes["rows_by_period"]["202608"] == 120
    assert "capped_months" not in notes


def test_scan_line_names_capped_months():
    scan = {"products": {"masks": {
        "data_available": True, "countries_observed": 100,
        "fetch": {"months_total": 6, "months_ok": 6, "capped_months": 2}}}}
    import time
    cs._record_call(scan, scanned_at=time.time(), cache_hit=False, cached=True)
    line = cs.trade_scan_line()
    assert f"{cs.PUBLIC_MAX_RECORDS}행 상한 2달" in line

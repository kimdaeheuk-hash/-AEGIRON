"""판정 못 한 행의 '낡음' 표시와 자정 넘김 (2026-10-09, 소킹 일지 10-08).

## 관측
Google News 503 이 종일 이어지던 10-08 15:03~23:03, `headline:plague` 행은 `⏸ 판정 안 함`으로 내려가지 않고
유지됐는데 근거 문구가 14:01 의 값("24시간 안에 25곳이 보도")을 **현재형으로 그대로** 보였다. 그리고 자정을 넘긴
10-09 00:05 에는 붙들 행이 새 날 표에 없어 경보가 조용히 사라졌고, 화면에서 '보도 없음'과 구별이 안 됐다.

## 고친 것
1. 판정 못 한 행의 근거 맨 앞에 "마지막으로 확인한 시각 + 지금 확인된 것이 아니다" 줄을 붙인다. updated_at 은 안 건드린다.
2. 날이 바뀐 첫 주기에 판정 못 한 계열은 어제 행을 같은 표시와 함께 새 날 표에 만든다(48시간 이내).
"""
from __future__ import annotations

import datetime as dt

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import (CARRY_MAX_HOURS, STALE_PREFIX, last_verified_text, refresh_alerts,
                               undetermined_alerts_line)

SRC = "headline:plague"


def _cand(score=72.0, evidence=None):
    return {"source": SRC, "label": "고위험 병원체 보도 · 페스트(흑사병) (25개 매체)", "score": score,
            "evidence": evidence or ["24시간 안에 서로 다른 매체 25곳이 보도: X / Y", "측정값이 아니라 키워드 일치"]}


def _stub(monkeypatch, candidates, *, undetermined=()):
    def collect(today, negative_space=None):
        for p in undetermined:
            alerts_mod._mark_undetermined(p)
        return list(candidates)
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts", collect)
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    sent = []
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "보낼 신규 경보 없음", "new_critical_high": 0}))
    return sent


def _row(date, source=SRC):
    return next((r for r in db.list_alerts(date) if r["source"] == source), None)


def _backdate(date, source, hours_ago):
    at = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours_ago)).isoformat()
    with db.get_connection() as conn:
        conn.execute("UPDATE alerts SET updated_at = ? WHERE alert_date = ? AND source = ?", (at, date, source))
        conn.commit()
    return at


# ── 1. 같은 날 붙든 행에 낡음 표시 ───────────────────────────

def test_held_row_gets_a_stale_marker_with_the_last_verified_time(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    at = _backdate("2026-10-08", SRC, hours_ago=9)
    _stub(monkeypatch, [], undetermined=["headline:"])
    result = refresh_alerts("2026-10-08")

    row = _row("2026-10-08")
    assert row["evidence"][0].startswith(STALE_PREFIX) and "지금 확인된 것이 아니다" in row["evidence"][0]
    assert row["evidence"][1].startswith("24시간 안에 서로 다른 매체 25곳")      # 원래 근거는 그대로 뒤따른다
    assert row["updated_at"] == at                                              # 마지막 실제 확인 시각을 새것처럼 만들지 않는다
    assert result["undetermined"][0]["last_verified"] == last_verified_text({"updated_at": at})


def test_marker_is_not_stacked_on_later_cycles(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [], undetermined=["headline:"])
    for _ in range(3):
        refresh_alerts("2026-10-08")
    ev = _row("2026-10-08")["evidence"]
    assert sum(1 for e in ev if e.startswith(STALE_PREFIX)) == 1 and len(ev) == 3


def test_marker_disappears_when_the_row_is_judged_again(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [], undetermined=["headline:"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [_cand(evidence=["새 근거 1", "새 근거 2"])])
    refresh_alerts("2026-10-08")
    assert _row("2026-10-08")["evidence"] == ["새 근거 1", "새 근거 2"]


def test_undetermined_line_names_when_each_row_was_last_verified():
    line = undetermined_alerts_line({"undetermined": [
        {"tier": "medium", "label": "페스트", "score": 72.0, "source": SRC, "last_verified": "10-08 14:01"}]})
    assert "(마지막 확인 10-08 14:01 UTC)" in line


def test_rows_of_other_families_are_not_marked(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand(), {"source": "gai:x", "label": "다른 경보", "score": 75.0, "evidence": ["근거"]}])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [{"source": "gai:x", "label": "다른 경보", "score": 75.0, "evidence": ["근거"]}],
          undetermined=["headline:"])
    refresh_alerts("2026-10-08")
    assert _row("2026-10-08", "gai:x")["evidence"] == ["근거"]


# ── 2. 자정을 넘길 때 ────────────────────────────────────────

def test_undetermined_row_is_carried_into_the_new_day_with_the_marker(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    at = _backdate("2026-10-08", SRC, hours_ago=3)
    _stub(monkeypatch, [], undetermined=["headline:"])
    result = refresh_alerts("2026-10-09")

    row = _row("2026-10-09")
    assert row is not None and row["tier"] == "medium" and row["score"] == 72.0
    assert row["evidence"][0].startswith(STALE_PREFIX)
    assert last_verified_text({"updated_at": at}) in row["evidence"][0]          # 어제 확인 시각이 적힌다
    assert [r["source"] for r in result["undetermined"]] == [SRC]


def test_carried_row_keeps_the_original_verification_time_on_the_next_day(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    at = _backdate("2026-10-08", SRC, hours_ago=3)
    _stub(monkeypatch, [], undetermined=["headline:"])
    refresh_alerts("2026-10-09")
    _backdate("2026-10-09", SRC, hours_ago=1)
    refresh_alerts("2026-10-10")
    assert last_verified_text({"updated_at": at}) in _row("2026-10-10")["evidence"][0]
    assert sum(1 for e in _row("2026-10-10")["evidence"] if e.startswith(STALE_PREFIX)) == 1


def test_a_successful_scan_with_no_candidate_does_not_carry(isolated_db, monkeypatch):
    """대조군 — 조회가 성공했는데 후보가 없으면 정말 '없다'. 어제 행을 넘기지 않는다."""
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")
    assert _row("2026-10-09") is None


def test_row_older_than_the_carry_limit_is_not_carried(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _backdate("2026-10-08", SRC, hours_ago=CARRY_MAX_HOURS + 1)
    _stub(monkeypatch, [], undetermined=["headline:"])
    refresh_alerts("2026-10-09")
    assert _row("2026-10-09") is None


def test_carry_does_not_overwrite_a_live_row_of_the_new_day(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [_cand(evidence=["오늘 새 근거", "x"])], undetermined=["headline:"])
    refresh_alerts("2026-10-09")
    assert _row("2026-10-09")["evidence"] == ["오늘 새 근거", "x"]


def test_carrying_a_medium_row_does_not_page_the_phone(isolated_db, monkeypatch):
    sent = _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [], undetermined=["headline:"])
    refresh_alerts("2026-10-09")
    assert all(not batch for batch in sent)


def test_refresh_actually_calls_the_carry_and_the_marker():
    """배선 — 만들어만 두고 아무도 안 부르는 층 방지."""
    import ast
    import inspect
    names = {n.func.id for n in ast.walk(ast.parse(inspect.getsource(refresh_alerts)))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert {"_carry_forward_undetermined", "stale_marker", "is_stale_marked"} <= names



# ── 3. 이미 내려간 행은 붙들지도 잇지도 않는다 (2026-10-30 운영) ─────────────────────
# 10-29 13:01 에 내려간 페스트 오탐이 10-30 11:05(Google 차단 → 판정 안 함)에 '마지막 상태'로 되살아나
# 두 시간 화면에 다시 떴다. 마지막으로 안 상태는 '내려감'이었다.

def test_a_retired_row_is_not_revived_by_an_undetermined_cycle(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-30")
    _stub(monkeypatch, [])                                   # 스캔 온전 · 후보 없음 → 내림
    refresh_alerts("2026-10-30")
    assert _row("2026-10-30")["suppressed"] == 1
    _stub(monkeypatch, [], undetermined=["headline:"])       # 스캔 불완전
    result = refresh_alerts("2026-10-30")
    assert _row("2026-10-30")["suppressed"] == 1             # 되살아나지 않는다
    assert result["undetermined"] == []


def test_a_visible_row_is_still_held_by_an_undetermined_cycle(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-30")
    _stub(monkeypatch, [], undetermined=["headline:"])
    result = refresh_alerts("2026-10-30")
    assert _row("2026-10-30")["suppressed"] == 0 and len(result["undetermined"]) == 1


def test_a_row_retired_yesterday_is_not_carried_into_today(isolated_db, monkeypatch):
    _stub(monkeypatch, [_cand()])
    refresh_alerts("2026-10-29")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-29")                             # 어제 안에 내려감
    _stub(monkeypatch, [], undetermined=["headline:"])
    refresh_alerts("2026-10-30")                             # 오늘 첫 주기가 판정 못 함
    row = _row("2026-10-30")
    assert row is None or row["suppressed"] == 1

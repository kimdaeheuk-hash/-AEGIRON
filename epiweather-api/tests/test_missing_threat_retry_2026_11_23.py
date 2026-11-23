"""승인 제품 스냅숏에 빠진 위협이 있으면 주간 작업을 6시간 간격으로 앞당긴다 (2026-11-23).

#146 은 refresh_due 가 빠진 위협을 다시 받게 했지만, refresh_due 는 7일 간격 주간 작업에서만 불렸다 —
배포 첫 주기 로그에 '발할라 승인제품: 승인 5종 · 없음 2종'(옛 8개 위협)만 나오고 재조회가 없었다.
"""
from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path

import main
from algorithms import reference_snapshots as rs

NOW = dt.datetime(2026, 11, 23, 9, 0, tzinfo=dt.timezone.utc)


def _ago(hours):
    return NOW - dt.timedelta(hours=hours)


def test_first_run_and_week_old_are_due(monkeypatch):
    monkeypatch.setattr(rs, "any_missing_threats", lambda: False)
    assert main._weekly_job_due(None, NOW) is True
    assert main._weekly_job_due(_ago(7 * 24), NOW) is True
    assert main._weekly_job_due(_ago(3 * 24), NOW) is False


def test_missing_threats_pull_the_job_forward_after_six_hours(monkeypatch):
    monkeypatch.setattr(rs, "any_missing_threats", lambda: True)
    assert main._weekly_job_due(_ago(6), NOW) is True
    assert main._weekly_job_due(_ago(5.9), NOW) is False      # 실패가 이어져도 매시 두드리지 않는다


def test_any_missing_threats_reads_the_snapshot(monkeypatch):
    from algorithms import approved_products as ap
    full = {k: {"product_count": 0} for k, v in ap.THREAT_SEARCH_TERMS.items() if v}
    monkeypatch.setattr(rs, "_load", lambda name: {"by_threat": full} if name == "approved_products" else {})
    assert rs.any_missing_threats() is False
    partial = dict(list(full.items())[:8])
    monkeypatch.setattr(rs, "_load", lambda name: {"by_threat": partial} if name == "approved_products" else {})
    assert rs.any_missing_threats() is True


def test_scheduler_loop_uses_the_due_check():
    tree = ast.parse(Path(main.__file__).read_text(encoding="utf-8"))
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_scheduler_loop")
    called = {c.func.id for c in ast.walk(loop) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert "_weekly_job_due" in called

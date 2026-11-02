"""현지어 위키 신호의 수집 편입 — 매시간 부르고 일키로 캐시한다 (2026-11-02).

부를 때만 계산하면 추세가 안 쌓인다(극지 09-01·발할라 09-03과 같은 이유).
8도시 × 2문서 = 16요청이지만 위키 집계가 일 단위라 같은 날 안에서는 캐시를 쓴다.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib

import collector
from algorithms import local_signal as ls

COLLECTOR_PY = pathlib.Path(collector.__file__)


def _items(views=100):
    today = dt.date(2026, 11, 2)
    return [{"timestamp": (today - dt.timedelta(days=back)).strftime("%Y%m%d") + "00",
             "views": views} for back in range(1, 29)]


def test_second_call_within_the_day_does_not_hit_the_network(monkeypatch):
    ls._SIGNAL_CACHE.update(at=None, data=None)
    calls = []
    monkeypatch.setattr(ls, "_daily_views",
                        lambda *a, **k: (calls.append(1), _items())[1])
    first = ls.fetch_all_signals(today=dt.date(2026, 11, 2))
    second = ls.fetch_all_signals(today=dt.date(2026, 11, 2))
    assert set(first) == set(ls.CITY_WIKI) and first == second
    assert len(calls) == len(ls.CITY_WIKI) * 2      # 도시당 2문서, 한 번만
    ls._SIGNAL_CACHE.update(at=None, data=None)


def test_next_day_refetches(monkeypatch):
    ls._SIGNAL_CACHE.update(at=None, data=None)
    calls = []
    monkeypatch.setattr(ls, "_daily_views",
                        lambda *a, **k: (calls.append(1), _items())[1])
    ls.fetch_all_signals(today=dt.date(2026, 11, 2))
    ls.fetch_all_signals(today=dt.date(2026, 11, 3))
    assert len(calls) == len(ls.CITY_WIKI) * 2 * 2
    ls._SIGNAL_CACHE.update(at=None, data=None)


def test_collector_registers_the_source_health_key():
    assert collector.FREE_SOURCE_HEALTH_KEYS["LocalSignal"] == "local_signal"


def test_collector_block_fetches_and_marks_total_failure():
    """수집 블록이 `fetch_all_signals` 를 부르고, 전멸이면 None+실패 기록."""
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    src = ast.get_source_segment(COLLECTOR_PY.read_text(encoding="utf-8"), fn)
    assert "fetch_all_signals()" in src
    assert 'result["local_signal"] = None' in src
    assert 'log_error("LocalSignal"' in src

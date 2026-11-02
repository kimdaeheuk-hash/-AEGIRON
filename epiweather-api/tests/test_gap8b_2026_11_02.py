"""갭 #8b — 행동 신호(HIRA·서울) 수집 주기 편입.

/api/behavioral을 부를 때만 계산되던 것을 매시간 주기에 넣는다.
"""
from __future__ import annotations

import inspect

import collector


def test_behavioral_wired_into_free_cycle():
    src = inspect.getsource(collector.collect_free_sources)
    assert "get_behavioral_signal" in src
    assert 'result["behavioral"]' in src


def test_behavioral_in_health_keys():
    assert collector.FREE_SOURCE_HEALTH_KEYS["Behavioral"] == "behavioral"


def test_behavioral_failure_is_none_not_silent():
    """예외는 None+로그 — 조용히 빠지지 않는다."""
    src = inspect.getsource(collector.collect_free_sources)
    assert 'result["behavioral"] = None' in src
    assert 'log_error("Behavioral"' in src

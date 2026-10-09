"""병원체 감시: 공급자 둘이 다 실패하면 쿨다운 동안 다시 안 부른다 (2026-10-09, 소킹 일지 10-08).

10-08 22시대에 5분 사이 네 번(22:03·22:03·22:05·22:07) 같은 실패를 다시 불렀다(갱신·수동 호출이 겹침).
막힌 쪽을 두드릴수록 풀리는 데 오래 걸릴 수 있다.
"""
from __future__ import annotations

import pytest

from algorithms import pathogen_sentinel as ps


class Calls:
    def __init__(self):
        self.n = 0


@pytest.fixture
def both_down(monkeypatch):
    c = Calls()
    monkeypatch.delenv(ps.FALLBACK_KEY_ENV, raising=False)

    def feed(*a, **k):
        c.n += 1
        return {"status": "error", "error": "503 Server Error"}
    monkeypatch.setattr(ps, "fetch_local_feed", feed)
    return c


def test_second_call_inside_the_cooldown_does_not_hit_the_network(both_down):
    with pytest.raises(ps.SentinelError):
        ps.fetch_titles(now=1000.0)
    with pytest.raises(ps.SentinelError, match="쿨다운"):
        ps.fetch_titles(now=1000.0 + 60)
    assert both_down.n == 1


def test_the_same_reason_is_raised_so_the_log_stays_truthful(both_down):
    with pytest.raises(ps.SentinelError) as first:
        ps.fetch_titles(now=1000.0)
    with pytest.raises(ps.SentinelError) as second:
        ps.fetch_titles(now=1100.0)
    assert str(first.value) in str(second.value)


def test_after_the_cooldown_it_tries_again(both_down):
    with pytest.raises(ps.SentinelError):
        ps.fetch_titles(now=1000.0)
    with pytest.raises(ps.SentinelError):
        ps.fetch_titles(now=1000.0 + ps.FAIL_COOLDOWN_SEC + 1)
    assert both_down.n == 2


def test_a_success_clears_the_cooldown(both_down, monkeypatch):
    with pytest.raises(ps.SentinelError):
        ps.fetch_titles(now=1000.0)
    monkeypatch.setattr(ps, "fetch_local_feed", lambda *a, **k: {"status": "ok", "_all_titles": ["x - y"]})
    assert ps.fetch_titles(now=1000.0 + ps.FAIL_COOLDOWN_SEC + 1) == ["x - y"]
    assert ps._FAIL["err"] is None


def test_a_fallback_answer_is_not_a_failure(monkeypatch):
    """Google 만 막히고 대체가 답하면 실패가 아니다 — 쿨다운이 걸리지 않는다."""
    monkeypatch.setenv(ps.FALLBACK_KEY_ENV, "tvly-key")
    monkeypatch.setattr(ps, "fetch_local_feed", lambda *a, **k: {"status": "error", "error": "503"})
    monkeypatch.setattr(ps, "tavily_headlines", lambda q, k: ["Plague death - Reuters"])
    assert ps.fetch_titles(now=1000.0) == ["Plague death - Reuters"]
    assert ps._FAIL["err"] is None


def test_the_cache_still_wins_over_the_cooldown(both_down, monkeypatch):
    ps._CACHE.update(at=1000.0, titles=["cached - x"], provider=ps.GOOGLE)
    ps._FAIL.update(at=1000.0, err="이전 실패")
    assert ps.fetch_titles(now=1000.0 + 60) == ["cached - x"]
    assert both_down.n == 0

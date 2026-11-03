"""라이브 fetch 캐시 — 느린 것 두 가지 추가(2026-11-03).

③ /api/genomic-variants: 요청마다 Nextstrain 3빌드 라이브 fetch(최대 45초).
   1시간 스냅샷으로 낸다.
④ /api/social-signal: Mastodon 8태그 직렬 호출(최악 120초).
   15분 스냅샷으로 낸다.

핸들러·헬퍼를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다.
외부 HTTP 실호출 없음(conftest 가드 준수).
"""
from __future__ import annotations

import pytest

import main as main_mod
from algorithms import genomic_variants as gv_mod
from algorithms import social_signal as ss_mod


@pytest.fixture(autouse=True)
def _clean_live_cache():
    main_mod._LIVE_CACHE.clear()
    yield
    main_mod._LIVE_CACHE.clear()


def _ok_payload():
    return {
        "a": {"label": "A", "available": True},
        "b": {"label": "B", "available": False, "reason": "x"},
    }


def _dead_payload():
    return {
        "a": {"label": "A", "available": False, "reason": "down"},
        "b": {"label": "B", "available": False, "reason": "down"},
    }


def test_second_call_uses_cache():
    """두 번째 호출은 builder를 다시 안 돈다."""
    calls: list = []

    def build():
        calls.append(1)
        return _ok_payload()

    r1 = main_mod._live_cached("genomic-variants", build)
    r2 = main_mod._live_cached("genomic-variants", build)
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True
    assert r2["a"] == r1["a"]


def test_cache_keys_are_independent():
    """키가 다르면 캐시를 공유하지 않는다."""
    calls: list = []

    def build():
        calls.append(1)
        return _ok_payload()

    main_mod._live_cached("genomic-variants", build)
    main_mod._live_cached("social-signal", build)
    assert len(calls) == 2


def test_cache_expires(monkeypatch):
    """TTL이 지나면 다시 돈다."""
    monkeypatch.setitem(main_mod._LIVE_CACHE_TTL_SEC, "social-signal", 0)
    calls: list = []

    def build():
        calls.append(1)
        return _ok_payload()

    main_mod._live_cached("social-signal", build)
    main_mod._live_cached("social-signal", build)
    assert len(calls) == 2


def test_total_failure_is_never_cached():
    """전멸(전부 available=False)은 안 남긴다 — 장애가 스냅샷이 되면 안 된다."""
    calls: list = []

    def build():
        calls.append(1)
        return _dead_payload()

    r1 = main_mod._live_cached("genomic-variants", build)
    r2 = main_mod._live_cached("genomic-variants", build)
    assert len(calls) == 2
    assert r1["cached"] is False and r2["cached"] is False


def test_partial_success_is_cached():
    """하나라도 살아있으면 성공으로 남긴다(수집기와 같은 관대함)."""
    calls: list = []

    def build():
        calls.append(1)
        return _ok_payload()

    main_mod._live_cached("social-signal", build)
    main_mod._live_cached("social-signal", build)
    assert len(calls) == 1


def test_genomic_handler_serves_cached(monkeypatch):
    """핸들러 두 번이면 Nextstrain fetch는 한 번."""
    calls: list = []

    def fake():
        calls.append(1)
        return _ok_payload()

    monkeypatch.setattr(gv_mod, "get_genomic_variant_signals", fake)
    r1 = main_mod.genomic_variants()
    r2 = main_mod.genomic_variants()
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True


def test_social_handler_serves_cached(monkeypatch):
    """핸들러 두 번이면 Mastodon fetch는 한 번."""
    calls: list = []

    def fake():
        calls.append(1)
        return _ok_payload()

    monkeypatch.setattr(ss_mod, "get_social_signal", fake)
    r1 = main_mod.social_signal()
    r2 = main_mod.social_signal()
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True

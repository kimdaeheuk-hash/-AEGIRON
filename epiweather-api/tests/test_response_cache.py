"""응답 캐시 — 느린 것 두 가지(2026-11-03).

① /api/ai/infer: Meta 추론 60~120초라 캐시 없인 Vercel 무료 한도(60초)를
   넘겨 브라우저가 504로 죽는다. 같은 상황 해시면 저장된 답을 즉시 낸다.
② /api/dashboard: 요청마다 7엔진 전체 재계산이라 무한 로딩처럼 보인다.
   수 분짜리 스냅샷으로 낸다. 수집 완료 브로드캐스트는 강제 갱신.

핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다.
외부 HTTP 실호출 없음(conftest 가드 준수).
"""
from __future__ import annotations

import pytest

import main as main_mod
from algorithms import ai_inference as ai_mod


@pytest.fixture(autouse=True)
def _clean_caches():
    main_mod._INFER_CACHE.clear()
    main_mod._DASHBOARD_CACHE.update({"at": 0.0, "payload": None})
    yield
    main_mod._INFER_CACHE.clear()
    main_mod._DASHBOARD_CACHE.update({"at": 0.0, "payload": None})


def _no_keys(monkeypatch):
    for env in ("META_MODEL_API_KEY", "MODEL_API_KEY",
                "META_MODEL_BASE_URL", "META_MODEL_API_MODEL",
                "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(env, raising=False)


def _fake_run(calls):
    def run(situation, api_key=None):
        calls.append(dict(situation))
        return {
            "alert_level": "주의", "decision_tree": {},
            "rag_documents_used": [], "llm_analysis": "1) 평가",
            "llm_provider": "meta_model_api", "llm_model": "muse-spark-1.3",
            "meta_error": None, "cache_hit": False, "usage": {},
        }
    return run


def _req(**kw):
    args = {"rt": 1.5, "arrival_day": 20}
    args.update(kw)
    return main_mod.AIInferRequest(**args)


def test_infer_identical_situation_served_from_cache(monkeypatch):
    """같은 상황 두 번이면 추론은 한 번만 돈다."""
    _no_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(ai_mod, "run_ai_inference", _fake_run(calls))
    r1 = main_mod.ai_infer(_req())
    r2 = main_mod.ai_infer(_req())
    assert len(calls) == 1
    assert r1["mode"] == "full_rag_llm" and r1["cached"] is False
    assert r2["cached"] is True
    assert r2["llm_analysis"] == r1["llm_analysis"]
    assert r2["situation_hash"] == r1["situation_hash"]
    assert r2["cached_at"] == r1["cached_at"]


def test_infer_different_situation_recomputes(monkeypatch):
    """상황이 다르면 해시가 달라 새로 돈다."""
    _no_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(ai_mod, "run_ai_inference", _fake_run(calls))
    r1 = main_mod.ai_infer(_req(rt=1.5))
    r2 = main_mod.ai_infer(_req(rt=2.0))
    assert len(calls) == 2
    assert r1["cached"] is False and r2["cached"] is False
    assert r1["situation_hash"] != r2["situation_hash"]


def test_infer_cache_expires(monkeypatch):
    """TTL이 지나면 다시 돈다."""
    _no_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(main_mod, "_INFER_CACHE_TTL_SEC", 0)
    calls: list = []
    monkeypatch.setattr(ai_mod, "run_ai_inference", _fake_run(calls))
    main_mod.ai_infer(_req())
    main_mod.ai_infer(_req())
    assert len(calls) == 2


def test_infer_failure_is_never_cached(monkeypatch):
    """실패·폴백은 안 남긴다 — 일시 장애가 30분짜리 답이 되면 안 된다."""
    _no_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    calls: list = []

    def flaky(situation, api_key=None):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("meta down")
        return _fake_run([])(situation, api_key)

    monkeypatch.setattr(ai_mod, "run_ai_inference", flaky)
    r1 = main_mod.ai_infer(_req())
    assert r1["mode"] == "decision_tree_fallback"
    assert "cached" not in r1
    r2 = main_mod.ai_infer(_req())
    assert r2["mode"] == "full_rag_llm" and r2["cached"] is False
    assert len(calls) == 2


def test_situation_hash_is_order_insensitive():
    """키 순서가 달라도 같은 입력은 같은 해시."""
    assert (main_mod._situation_hash({"b": 1, "a": 2})
            == main_mod._situation_hash({"a": 2, "b": 1}))
    assert len(main_mod._situation_hash({})) == 16


def _fake_builder(calls):
    def build():
        calls.append(1)
        return {"generated_at": "T", "x": 1}
    return build


def test_dashboard_second_call_uses_cache(monkeypatch):
    """두 번째 대시보드 호출은 재계산 없이 스냅샷."""
    calls: list = []
    monkeypatch.setattr(main_mod, "_build_dashboard", _fake_builder(calls))
    r1 = main_mod._dashboard_cached()
    r2 = main_mod._dashboard_cached()
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True
    assert r2["generated_at"] == r1["generated_at"]


def test_dashboard_force_refresh_recomputes(monkeypatch):
    """수집 완료 브로드캐스트는 강제 갱신."""
    calls: list = []
    monkeypatch.setattr(main_mod, "_build_dashboard", _fake_builder(calls))
    main_mod._dashboard_cached(force_refresh=True)
    main_mod._dashboard_cached(force_refresh=True)
    assert len(calls) == 2


def test_dashboard_cache_expires(monkeypatch):
    """TTL이 지나면 다시 계산한다."""
    calls: list = []
    monkeypatch.setattr(main_mod, "_build_dashboard", _fake_builder(calls))
    monkeypatch.setattr(main_mod, "_DASHBOARD_CACHE_TTL_SEC", 0)
    main_mod._dashboard_cached()
    main_mod._dashboard_cached()
    assert len(calls) == 2

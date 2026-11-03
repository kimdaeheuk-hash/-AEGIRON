"""0단계 AI 분석 — Meta 우선·Claude 폴백 (2026-11-03).

외부 호출 전부 mock. 직접 호출이라 소켓 불필요.
"""
from __future__ import annotations

import sys
import types

import pytest
import requests

from algorithms import synthetic_threat as st


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    for env in ("META_MODEL_API_KEY", "MODEL_API_KEY", "META_MODEL_API_BASE_URL",
                "META_MODEL_API_MODEL", "ANTHROPIC_API_KEY", "AEGIRON_REQUIRE_LOCAL"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(st._meta, "record_layer_call", lambda *a, **k: None)


class _MetaResp:
    def __init__(self, message, status=200):
        self._message = message
        self.status_code = status
        self.text = "err-body"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"choices": [{"message": self._message}], "usage": {}}


def _fake_anthropic(text="", stop="end_turn"):
    mod = types.ModuleType("anthropic")

    class _Messages:
        def create(self, **kw):
            ns = types.SimpleNamespace
            return ns(content=[ns(type="text", text=text)], stop_reason=stop)

    class _Client:
        def __init__(self, api_key=None, timeout=None):
            self.messages = _Messages()

    mod.Anthropic = _Client
    return mod


def _summary():
    return {"종합": 0.5, "CI": {"lo": 0.1, "hi": 0.9}}


def _boom_anthropic():
    mod = types.ModuleType("anthropic")

    class _Boom:
        def __init__(self, api_key=None, timeout=None):
            raise RuntimeError("claude down")

    mod.Anthropic = _Boom
    return mod


def test_claude_first_on_success(monkeypatch):
    """Claude 우선 — 성공하면 Meta를 호출하지 않는다."""
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    called = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: called.append(1))
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic("1) 자연스러움"))
    r = st.analyze_synthetic_threat(_summary())
    assert r["llm_provider"] == "anthropic"
    assert r["analysis"] == "1) 자연스러움"
    assert r["refused"] is False
    assert called == []
    assert r["timings_ms"]["claude_ms"] >= 0


def test_claude_error_falls_back_to_meta(monkeypatch):
    """Claude 오류 때만 Meta 폴백."""
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _MetaResp({"content": "1) 메타 분석"}))
    monkeypatch.setitem(sys.modules, "anthropic", _boom_anthropic())
    r = st.analyze_synthetic_threat(_summary())
    assert r["llm_provider"] == "meta_model_api"
    assert r["analysis"] == "1) 메타 분석"
    assert "claude down" in (r["claude_error"] or "")


def test_no_keys_raises_value_error():
    with pytest.raises(ValueError, match="모두 없다"):
        st.analyze_synthetic_threat(_summary())


def test_claude_refusal_returns_immediately(monkeypatch):
    """Claude 거부는 그대로 반환 — Meta 재시도 안 함(Meta도 거부할 프롬프트)."""
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    called = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: called.append(1))
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic(stop="refusal"))
    r = st.analyze_synthetic_threat(_summary())
    assert r["llm_provider"] == "anthropic"
    assert r["refused"] is True
    assert "거부" in r["analysis"]
    assert called == []


def test_both_fail_raises(monkeypatch):
    """Claude 오류 + Meta 빈 본문이면 둘 다 실패로 말한다."""
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setattr(requests, "post", lambda *a, **k: _MetaResp({}))
    monkeypatch.setitem(sys.modules, "anthropic", _boom_anthropic())
    with pytest.raises(RuntimeError, match="모두 실패"):
        st.analyze_synthetic_threat(_summary())


def test_require_local_blocks_hosted_meta_fallback(monkeypatch):
    """Claude 오류 + 주권 모드면 호스팅 Meta 폴백이 HTTP 전에 막힌다."""
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setenv("AEGIRON_REQUIRE_LOCAL", "on")
    called = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: called.append(1))
    monkeypatch.setitem(sys.modules, "anthropic", _boom_anthropic())
    with pytest.raises(RuntimeError, match="주권"):
        st.analyze_synthetic_threat(_summary())
    assert called == []


def test_sequence_gets_computed_signals(monkeypatch):
    from algorithms import genome_signals as gs
    monkeypatch.setenv("META_MODEL_API_KEY", "meta-key")
    seen = []
    monkeypatch.setattr(gs, "screen_sequence",
                        lambda seq, **k: seen.append(seq) or {"ok": True})
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _MetaResp({"content": "1) ok"}))
    s = _summary()
    s["sequence"] = "ATGGCC"
    r = st.analyze_synthetic_threat(s)
    assert seen == ["ATGGCC"]
    assert r["llm_provider"] == "meta_model_api"


def test_analyze_identical_summary_served_from_cache(monkeypatch):
    """같은 스캔 요약 두 번이면 LLM은 한 번만 돈다(Vercel 60초 회피)."""
    import main as main_mod

    main_mod._ANALYZE_CACHE.clear()
    calls = []

    def fake(summary, api_key=None):
        calls.append(1)
        return {"analysis": "1) ok", "llm_provider": "meta_model_api",
                "llm_model": "m", "meta_error": None}

    monkeypatch.setattr(st, "analyze_synthetic_threat", fake)
    req = main_mod.SyntheticThreatAnalyzeRequest(summary={"종합": 55})
    r1 = main_mod.synthetic_threat_analyze(req)
    r2 = main_mod.synthetic_threat_analyze(req)
    assert len(calls) == 1
    assert r1["cached"] is False and r2["cached"] is True
    assert r2["analysis"] == "1) ok"
    main_mod._ANALYZE_CACHE.clear()


def test_analyze_timeouts_fit_vercel_budget():
    """Meta 20초 + Claude 25초 + 여유 < Vercel 60초."""
    assert st._META_TIMEOUT_SEC <= 20

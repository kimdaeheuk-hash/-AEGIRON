"""Stage 7 추론 LLM 제공자 — Claude 우선·Meta 폴백(2026-11-03 밤 순서 뒤집음).

infer는 max_tokens 8000 + 추론 생각 토큰이라 Meta 실측 60~120초.
Vercel 60초 안에 Meta는 절대 못 끝나서 Meta 우선이면 매 호출 20초를
태우고 Claude로 간다. 그래서 Claude를 먼저, Claude 오류 때만 Meta 폴백.

외부 호출은 전부 mock 한다(conftest 가드가 실제 HTTP를 막는다).
"""
from __future__ import annotations
from unittest.mock import patch

import pytest

from algorithms import ai_inference as ai
from algorithms import meta_api


def _reset(monkeypatch):
    for env in (meta_api.KEY_ENV, meta_api.DOC_KEY_ENV,
                meta_api.BASE_URL_ENV, meta_api.MODEL_ENV,
                "ANTHROPIC_API_KEY", "AEGIRON_REQUIRE_LOCAL"):
        monkeypatch.delenv(env, raising=False)


def _situation():
    return {"rt": 1.5, "threat": "novel", "arrival_day": 20,
            "civic_lead": 3, "saved_lives": 100, "deaths": 50,
            "peak_infected": 1000, "hosp_overflow_days": 0}


def _meta_resp(text="1) 평가 2) 개입 3) 취약계층 4) 결정", usage=None):
    body = {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
    if usage is not None:
        body["usage"] = usage

    class _R:
        def raise_for_status(self):
            return None

        def json(self):
            return body
    return _R()


class _ClaudeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _ClaudeUsage:
    input_tokens = 100
    output_tokens = 50
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _ClaudeResp:
    content = [_ClaudeBlock("1) 평가 2) 개입 3) 취약계층 4) 결정")]
    usage = _ClaudeUsage()


class _ClaudeClient:
    def __init__(self, *a, **kw):
        pass

    class messages:
        @staticmethod
        def create(**kw):
            return _ClaudeResp()


class _BoomClient:
    def __init__(self, *a, **kw):
        raise RuntimeError("claude down")


def test_claude_first_when_keys_present(monkeypatch):
    """둘 다 있으면 Claude가 먼저 쓴다 — Meta를 호출하지 않는다."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    with patch("requests.post") as m, \
         patch("anthropic.Anthropic", _ClaudeClient):
        out = ai.run_ai_inference(_situation())
    m.assert_not_called()
    assert out["llm_provider"] == "anthropic"
    assert out["llm_model"] == "claude-sonnet-4-6"
    assert out["meta_error"] is None
    assert out["provider_path"] == "claude_first"
    assert "1) 평가" in out["llm_analysis"]


def test_claude_error_falls_back_to_meta(monkeypatch):
    """Claude 오류 때만 Meta 폴백 — 사용량 정규화도 여기서 본다."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    with patch("requests.post", return_value=_meta_resp(
            usage={"prompt_tokens": 10, "completion_tokens": 372,
                   "completion_tokens_details": {"reasoning_tokens": 354}})) as m, \
         patch("anthropic.Anthropic", _BoomClient):
        out = ai.run_ai_inference(_situation())
    assert out["llm_provider"] == "meta_model_api"
    assert out["llm_model"] == "muse-spark-1.3"
    assert "claude down" in (out["claude_error"] or "")
    assert out["usage"]["input_tokens"] == 10
    assert out["usage"]["output_tokens"] == 372
    assert out["usage"]["reasoning_tokens"] == 354
    assert "1) 평가" in out["llm_analysis"]
    url = m.call_args.args[0]
    assert url == "https://api.meta.ai/v1/chat/completions"
    assert m.call_args.kwargs["json"]["model"] == "muse-spark-1.3"
    # ★ 추론 모델은 생각+답이 상한을 나눈다 — 1200으론 답이 null로 온다.
    assert m.call_args.kwargs["json"]["max_tokens"] == 8000


def test_claude_only_when_no_meta_key(monkeypatch):
    """Meta 키가 없으면 Meta를 부르지 않고 Claude로 간다."""
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    with patch("requests.post") as m, \
         patch("anthropic.Anthropic", _ClaudeClient):
        out = ai.run_ai_inference(_situation())
    m.assert_not_called()
    assert out["llm_provider"] == "anthropic"
    assert out["meta_error"] is None


def test_no_keys_raises(monkeypatch):
    """키가 둘 다 없으면 터진다 — main.py가 트리 전용으로 받는다."""
    _reset(monkeypatch)
    with pytest.raises(ValueError, match="모두 없다"):
        ai.run_ai_inference(_situation())


def test_require_local_blocks_meta_fallback(monkeypatch):
    """Claude 오류 + 주권 모드면 호스팅 Meta 폴백이 HTTP 전에 막힌다."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setenv("AEGIRON_REQUIRE_LOCAL", "on")
    with patch("requests.post") as m, \
         patch("anthropic.Anthropic", _BoomClient):
        with pytest.raises(RuntimeError, match="REQUIRE_LOCAL"):
            ai.run_ai_inference(_situation())
    m.assert_not_called()


class _HttpFail:
    """상태코드+본문을 들고 실패하는 가짜 응답. 2026-11-03 실측: Meta가
    400 본문에 거부 이유(모델명·파라미터)를 싣는다."""

    status_code = 400
    text = '{"error": {"message": "model not found: muse-spark-1.3", "code": "bad_model"}}'

    def raise_for_status(self):
        import requests
        raise requests.exceptions.HTTPError("400 Client Error")


def test_meta_payload_starts_with_benign_use_preamble(monkeypatch):
    """Meta 호출 본문은 합법 사용 고지로 시작한다(필터 오탐 대응)."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_meta_resp()) as m:
        ai.run_ai_inference(_situation())
    msgs = m.call_args.kwargs["json"]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"].startswith("【작업 성격】")
    assert "civilian public-health" in msgs[0]["content"]


def test_meta_payload_avoids_filter_trigger_phrasing(monkeypatch):
    """Meta 호출 본문에 필터 방아쇠 표현이 없다(2026-11-03 이분 탐색)."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_meta_resp()) as m:
        ai.run_ai_inference(_situation())
    body = m.call_args.kwargs["json"]
    full = body["messages"][0]["content"] + body["messages"][1]["content"]
    for banned in ("가장 많은 생명을 살릴", "casualty reasoning",
                   "통합 위협 평가", "결정적 개입 지점", "취약계층"):
        assert banned not in full, f"방아쇠 표현이 돌아왔다 — {banned}"
    for kept in ("의료 대응 효과", "통합 위험 평가", "고위험군",
                 "수치 근거", "불확실성"):
        assert kept in full, f"과업 문구가 빠졌다 — {kept}"


def test_meta_system_omits_full_kb_dump_but_keeps_rag(monkeypatch):
    """Meta 시스템엔 지식베이스 덤프가 없고 RAG 맥락은 사용자 메시지에 있다."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_meta_resp()) as m:
        ai.run_ai_inference(_situation())
    msgs = m.call_args.kwargs["json"]["messages"]
    assert "한국 방역 지식베이스" not in msgs[0]["content"]
    assert msgs[0]["content"].startswith("【작업 성격】")
    assert "관련 가이드라인" in msgs[1]["content"]


def test_claude_system_keeps_full_kb_dump(monkeypatch):
    """Claude 경로는 전체 지식베이스+캐싱 그대로(동작 변경 없음)."""
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    sent = {}

    class _CapClient:
        def __init__(self, *a, **kw):
            pass

        class messages:
            @staticmethod
            def create(**kw):
                sent.update(kw)
                return _ClaudeResp()

    with patch("anthropic.Anthropic", _CapClient):
        ai.run_ai_inference(_situation())
    assert "한국 방역 지식베이스" in sent["system"][0]["text"]
    assert sent["system"][0].get("cache_control") == {"type": "ephemeral"}


def test_both_fail_reports_both(monkeypatch):
    """Claude 오류 + Meta HTTP 실패면 둘 다 실패로 말한다(상태코드+본문)."""
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    with patch("requests.post", return_value=_HttpFail()), \
         patch("anthropic.Anthropic", _BoomClient):
        with pytest.raises(RuntimeError, match="모두 실패"):
            ai.run_ai_inference(_situation())

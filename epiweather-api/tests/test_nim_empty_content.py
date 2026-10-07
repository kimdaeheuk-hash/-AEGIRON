"""NIM 이 본문 없는 200 을 줄 때 사유가 붙고 장부가 거짓말하지 않는가 (2026-10-07).

## 배경 (프로덕션 실측)

    10-01~10-06 매 AI 슬롯 (21:02 UTC)
    NLP 구조화 추출: N건 저장 · … · 경로별: nvidia_nim_hosted: 실패×5 · …

`nvidia_nim_hosted: 실패` 에 **사유가 없었다.** 09-18 엔 `HTTPError 410: …end of
life` 처럼 NVIDIA 가 보낸 문장이 찍혔는데 그 뒤로 맨 `실패` 만 남았다.

예외는 `nim_raw_detailed` 의 except 에서 반드시 종류를 달고 나간다
(`brief_reason` 은 최소한 클래스명을 돌려준다). 그러니 사유 없는 실패는 "HTTP 200
인데 choices[0].message.content 가 null" 한 길뿐이다. 그 길은 `ok=True` 로 능력
장부에 적혀 장부가 NIM 이 멀쩡하다고 말했다 — **전멸을 성공으로 기록**했다.

이 파일이 지키는 것: 본문 없는 200 은 (1) 실패이고 (2) 사유를 달고 나오며
(3) 장부에는 실패로 남고 (4) 응답 본문은 어디에도 실리지 않는다.
content 가 *왜* null 인지는 이 수리가 판정하지 않는다 — 사유 줄이 다음 AI 슬롯에서
말한다(finish_reason 과 응답 키 이름).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import algorithms.aegiron_model as am


def _nim_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_REQUIRE_LOCAL", raising=False)
    monkeypatch.delenv("AEGIRON_NVIDIA_ONPREM_BASE", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_BASE_URL", raising=False)


def _resp(message: dict, finish_reason="stop"):
    class _R:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": message, "finish_reason": finish_reason}]}
    return _R()


@pytest.fixture
def ledger(monkeypatch):
    calls = []
    monkeypatch.setattr(am._nvidia, "record_layer_call",
                        lambda layer, url, ok, error=None: calls.append((layer, ok, error)))
    return calls


def test_null_content_is_a_failure_with_a_reason_not_a_bare_none(monkeypatch, ledger):
    """★핵심★ 10-01~06 의 맨 `실패` 를 재현한다: 200 + content=null."""
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"role": "assistant", "content": None})):
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content is None
    assert reason and reason != "실패"
    assert "content=null" in reason


def test_null_content_is_recorded_as_failure_in_the_ledger(monkeypatch, ledger):
    """옛 동작은 ok=True 였다 — 전멸을 성공으로 적는 장부. 그 사실까지 고정한다."""
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"content": None})):
        am.nim_raw_detailed("원문", am._nim_config())
    assert [(l, ok) for l, ok, _ in ledger] == [("text", False)]
    assert "빈응답" in (ledger[0][2] or "")


def test_a_real_answer_is_still_a_success(monkeypatch, ledger):
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"content": '{"disease": "x"}'})):
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content == '{"disease": "x"}' and reason is None
    assert [(l, ok) for l, ok, _ in ledger] == [("text", True)]


def test_reasoning_model_shape_is_named_in_the_reason(monkeypatch, ledger):
    """추론형 모델이 본문을 reasoning_content 에 두고 content 를 비운 모양, 그리고
    max_tokens 에 걸려 잘린 모양이 사유에서 갈린다 — 처방이 다르다(한도 / 모델)."""
    _nim_env(monkeypatch)
    msg = {"role": "assistant", "content": None, "reasoning_content": "비밀 추론 본문"}
    with patch("requests.post", return_value=_resp(msg, finish_reason="length")):
        _, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert "finish_reason=length" in reason
    assert "reasoning_content" in reason
    assert "비밀 추론 본문" not in reason       # 키 이름만, 값은 안 싣는다


def test_empty_or_blank_string_counts_as_empty(monkeypatch, ledger):
    _nim_env(monkeypatch)
    for blank in ("", "  \n"):
        with patch("requests.post", return_value=_resp({"content": blank})):
            content, reason = am.nim_raw_detailed("원문", am._nim_config())
        assert content is None
        assert "content=빈문자열" in reason


def test_reason_carries_shape_only_never_odd_strings(monkeypatch, ledger):
    """★유출 방지★ finish_reason·키 이름은 서버가 정한 값이라 이상한 문자열이
    올 수 있다 — 식별자 모양이 아니면 버린다(URL·헤더·본문이 로그로 새지 않게)."""
    _nim_env(monkeypatch)
    msg = {"content": None, "https://evil/?key=SECRET": "x"}
    with patch("requests.post",
               return_value=_resp(msg, finish_reason="see https://x/?key=SECRET")):
        _, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert "SECRET" not in reason and "://" not in reason
    assert "finish_reason=없음" in reason


def test_missing_message_or_odd_shape_does_not_crash():
    assert "빈응답" in am._empty_content_reason({}, None)
    assert "빈응답" in am._empty_content_reason(None, None)
    assert "응답키=없음" in am._empty_content_reason({"message": None}, None)


def test_summary_line_now_shows_the_reason_end_to_end(monkeypatch, ledger):
    """추출 경로를 끝까지 태워 `경로별:` 줄에 사유가 실리는지 본다 — 운영에서 맨
    `실패` 였던 바로 그 자리."""
    from algorithms import nlp_extract as nx
    _nim_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    with patch("requests.post", return_value=_resp({"content": None}, "length")), \
         patch.object(nx, "llm_raw", return_value=(None, "Timeout")):
        _, prov = am.extract_record("원문", source="who_emro")
    first = prov["attempts"][0]
    assert first.startswith("nvidia_nim_hosted: 빈응답(")
    assert not first.endswith(": 실패")

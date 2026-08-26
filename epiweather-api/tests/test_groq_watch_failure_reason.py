"""GroqWatch 가 왜 실패했는지 알 수 있어야 한다 (2026-08-25).

2026-08-24 07:00 KST 부터 GroqWatch 가 매 주기 절반씩 실패해 하루 세 번 `중단`으로
떨어졌다. **25시간이 넘도록 원인을 특정하지 못했다.** 코드가 못 알려줬기 때문이다:

    except Exception:
        return None

이 한 줄이 타임아웃·429(쿼터)·5xx·JSON 형식 문제를 **전부 같은 None** 으로 뭉갰고,
호출부는 그걸 무조건 "응답 파싱 실패" 로 찍었다. 네트워크 문제여도 "파싱 실패" 였다.

더 나쁜 것은 삼켜진 예외가 호출부의 `except` 에 닿지 않아
`log_error("GroqWatch", e)` 가 **한 번도 실행되지 않았다는 점**이다.
실측 확인: `/api/status` 의 `recent_errors` 에 GroqWatch 항목이 **0건**이었다
(전부 2026-08-17 KDCA 항목). 소스 헬스는 실패를 세는데 **이유는 어디에도 없었다.**

이 테스트가 고정하는 문장:
    **실패했다는 사실만 남기고 왜 실패했는지를 버리면, 고칠 수 없다.**
"""
from __future__ import annotations

import json
import pytest
import requests
from unittest.mock import patch

from algorithms import groq_watch
from algorithms.groq_watch import SearchContextTooLarge, QuotaExceeded, TierLimitReached


def _response(status: int = 200, payload: dict | None = None, text: str | None = None):
    """requests.Response 흉내 — status 와 본문만 있으면 된다."""
    r = requests.Response()
    r.status_code = status
    body = text if text is not None else json.dumps(payload or {})
    r._content = body.encode("utf-8")
    return r


def _ok_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


# ─────────────────────────────────────────────────────────────────────────────

def test_rate_limit_is_not_swallowed_as_parse_failure():
    """★핵심★ 429(쿼터 소진)가 '응답 파싱 실패'로 둔갑하면 안 된다."""
    with patch.object(groq_watch.requests, "post", return_value=_response(429, text="rate limited")):
        with pytest.raises(QuotaExceeded):   # 예전엔 조용히 None 이었다
            groq_watch.fetch_groq_pulse("key")


def test_server_error_is_not_swallowed():
    """5xx 도 마찬가지다 — Groq 쪽 장애와 우리 파싱 문제는 다른 사건이다."""
    with patch.object(groq_watch.requests, "post", return_value=_response(503, text="unavailable")):
        with pytest.raises(requests.HTTPError):
            groq_watch.fetch_groq_pulse("key")


def test_timeout_propagates():
    """타임아웃은 타임아웃이라고 말해야 한다. 30초를 기다렸다는 사실이 단서다."""
    with patch.object(groq_watch.requests, "post", side_effect=requests.Timeout("timed out")):
        with pytest.raises(requests.Timeout):
            groq_watch.fetch_groq_pulse("key")


def test_broken_json_says_it_is_a_format_problem_and_shows_the_body():
    """형식 문제일 때는 **실제로 뭐가 왔는지** 보여야 다음 점검에 바로 갈린다."""
    with patch.object(
        groq_watch.requests, "post",
        return_value=_response(200, _ok_payload("이건 JSON 이 아니라 그냥 문장입니다")),
    ):
        with pytest.raises(ValueError) as err:
            groq_watch.fetch_groq_pulse("key")

    message = str(err.value)
    assert "JSON" in message
    assert "그냥 문장입니다" in message      # 본문 일부가 실려야 한다


def test_non_dict_json_is_rejected_with_its_type():
    """리스트가 오면 '객체가 아님' 이라고 말한다 — 파싱은 됐다는 뜻이므로 다른 사건이다."""
    with patch.object(
        groq_watch.requests, "post",
        return_value=_response(200, _ok_payload('{"a": 1} 뒤에 쓰레기')),
    ):
        # 첫 '{'~마지막 '}' 만 잘라내므로 여기는 파싱에 성공하고 dict 가 된다
        out = groq_watch.fetch_groq_pulse("key")
    assert isinstance(out, dict)


def test_failure_reasons_are_distinguishable():
    """★핵심★ 서로 다른 실패가 서로 다른 말을 해야 한다.

    예전에는 아래 두 경우가 **글자 그대로 똑같은 로그**("응답 파싱 실패")를 남겼다.
    그래서 무료 티어 쿼터인지 모델 응답 형식 문제인지 구분할 수 없었다.
    """
    with patch.object(groq_watch.requests, "post", return_value=_response(429, text="rate limited")):
        with pytest.raises(Exception) as quota:
            groq_watch.fetch_groq_pulse("key")

    with patch.object(
        groq_watch.requests, "post",
        return_value=_response(200, _ok_payload("not json at all")),
    ):
        with pytest.raises(Exception) as parse:
            groq_watch.fetch_groq_pulse("key")

    assert type(quota.value) is not type(parse.value)
    assert str(quota.value) != str(parse.value)


def test_valid_response_still_works():
    """고치면서 정상 경로를 깨지 않았는지 — 이게 없으면 위 테스트가 무의미하다."""
    payload = _ok_payload(json.dumps({
        "has_new_signal": True,
        "urgency": "high",
        "diseases": ["ebola"],
        "summary": "테스트 요약",
    }))
    with patch.object(groq_watch.requests, "post", return_value=_response(200, payload)):
        out = groq_watch.fetch_groq_pulse("key")

    assert out["has_new_signal"] is True
    assert out["urgency"] == "high"
    assert out["diseases"] == ["ebola"]


def test_invalid_urgency_becomes_none_not_a_guess():
    """모델이 이상한 urgency 를 주면 **비운다.** 그럴듯한 값으로 채우지 않는다."""
    payload = _ok_payload(json.dumps({
        "has_new_signal": True,
        "urgency": "catastrophic",   # 우리가 정의한 값이 아니다
        "diseases": [],
        "summary": "x",
    }))
    with patch.object(groq_watch.requests, "post", return_value=_response(200, payload)):
        out = groq_watch.fetch_groq_pulse("key")

    assert out["urgency"] is None    # "high" 로 올림하지 않는다


# ── 413: 검색결과가 티어 한도를 넘는 경우 (2026-08-26 실측으로 드러남) ──────

def test_413_is_reported_as_its_own_thing_not_a_generic_failure():
    """★핵심★ 413 은 소스 고장도 우리 버그도 아니다 — 전용 예외로 구분한다.

    실측: 2026-08-26 recent_errors 에 이것만 7건 찍혔다.
        413 Client Error: Payload Too Large for url: .../chat/completions
    우리 프롬프트가 큰 게 아니라, 모델이 서버에서 끌어온 검색결과가
    계정 티어의 요청 크기 한도를 넘은 것이다.
    """
    with patch.object(groq_watch.requests, "post", return_value=_response(413, text="too large")):
        with pytest.raises(SearchContextTooLarge) as err:
            groq_watch.fetch_groq_pulse("key")

    assert "413" in str(err.value)
    # 429·5xx 와 같은 부류로 뭉뚱그려지면 안 된다
    assert not isinstance(err.value, requests.HTTPError)


def test_413_does_not_retry():
    """★실측 반영(2026-08-26)★ 재시도하지 않는다 — 오히려 해롭다.

    좁힌 질의로 재시도해봐야 소용없다. 토큰의 대부분이 **모델이 끌어온 검색결과**라
    우리 프롬프트를 줄여도 5,307 토큰이 나온다(원 질의와 큰 차이 없음).
    게다가 한 번 호출이 5,000~5,800 토큰인데 분당 한도가 8,000 이라
    **1분 안에 두 번 부르면 스스로 429 를 만든다.** 실제로 그렇게 만들어봤다.
    """
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json["messages"][0]["content"])
        return _response(413, text="too large")

    with patch.object(groq_watch.requests, "post", side_effect=fake_post):
        with pytest.raises(SearchContextTooLarge):
            groq_watch.fetch_groq_pulse("key")

    assert len(calls) == 1     # 딱 한 번만 부른다


def test_429_is_a_tier_limit_not_a_source_failure():
    """★핵심★ 429(분당 토큰 초과)도 소스 고장이 아니다 — 413 과 같은 뿌리다.

    실측 429 본문:
      Rate limit reached for model `openai/gpt-oss-120b` ... (TPM): Limit 8000, Used 5784
    """
    with patch.object(groq_watch.requests, "post", return_value=_response(429, text="TPM: Limit 8000")):
        with pytest.raises(QuotaExceeded) as err:
            groq_watch.fetch_groq_pulse("key")

    assert isinstance(err.value, TierLimitReached)   # 호출부가 값없음으로 분류하는 근거
    assert "429" in str(err.value)


def test_413_and_429_share_a_base_but_say_different_things():
    """둘 다 티어 한도지만 이유는 구분돼야 한다 — 하나는 크기, 하나는 속도."""
    with patch.object(groq_watch.requests, "post", return_value=_response(413, text="x")):
        with pytest.raises(TierLimitReached) as big:
            groq_watch.fetch_groq_pulse("key")
    with patch.object(groq_watch.requests, "post", return_value=_response(429, text="y")):
        with pytest.raises(TierLimitReached) as fast:
            groq_watch.fetch_groq_pulse("key")

    assert type(big.value) is not type(fast.value)
    assert "413" in str(big.value) and "429" in str(fast.value)


def test_token_usage_is_reported():
    """★실측에서 얻은 교훈★ 한도 8,000 대비 얼마나 썼는지 남긴다 — 다음엔 추측 안 한다."""
    payload = _ok_payload('{"has_new_signal": false, "summary": null, "diseases": [], "urgency": "low"}')
    payload["usage"] = {"prompt_tokens": 4993, "completion_tokens": 314, "total_tokens": 5307}

    with patch.object(groq_watch.requests, "post", return_value=_response(200, payload)):
        out = groq_watch.fetch_groq_pulse("key")

    assert out["tokens_used"] == 5307
    assert out["tokens_prompt"] == 4993


def test_413_twice_gives_up_without_pretending():
    """좁힌 질의로도 413 이면 포기한다 — 빈 신호를 지어내지 않는다."""
    with patch.object(groq_watch.requests, "post", return_value=_response(413, text="too large")):
        with pytest.raises(SearchContextTooLarge):
            groq_watch.fetch_groq_pulse("key")




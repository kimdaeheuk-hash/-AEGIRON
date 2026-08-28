"""NewsWatch 가 Cerebras 402 로 매 주기 통째로 죽고 있었다 (2026-08-28 오후).

## 사고
NewsWatch(2026-08-28 오전 작업)는 요약을 Cerebras 하나에만 맡겼다. 그런데 같은
날 Cerebras 계정이 402(무료 한도 소진)가 됐고, 프로덕션 로그가 매 주기 이렇게
찍혔다:

    ❌ NewsWatch 실패: HTTPError: 402 Client Error: Payment Required
                       for url: https://api.cerebras.ai/v1/chat/completions

현지어 뉴스 재분류에는 같은 날 Groq 폴백을 붙였는데(PR #11·#12) **이 층에는
안 붙였다.** 고친 것과 안 고친 것이 같은 원인을 공유하고 있었다.

## ★ 여기 함정이 하나 있다 ★
로그 실측: 현지어 뉴스 재분류 `11:57:44`, NewsWatch `11:57:52` — **8초 차이**다.
즉 둘이 **같은 분당 한도(TPM 8,000) 창을 나눠 쓴다.** 재분류 쪽이 본진이므로
이 층은 `GROQ_TOKEN_SLICE` 만큼만 가져가고, 제목을 그만큼 깎아서 보낸다.
그 상한이 실제로 걸리는지가 이 파일의 핵심이다.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import requests

from algorithms import news_watch as nw
from algorithms.cerebras_classify import WORST_CHARS_PER_TOKEN


def _response(status: int, payload=None, text: str | None = None):
    r = requests.Response()
    r.status_code = status
    r._content = (text if text is not None else json.dumps(payload or {})).encode("utf-8")
    return r


def _ok(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}],
            "usage": {"total_tokens": 812, "prompt_tokens": 760}}


ANSWER = json.dumps({"has_new_signal": True, "summary": "요약",
                     "diseases": ["콜레라"], "urgency": "high"})


def _feed(titles):
    return {"slug": "global_watch", "status": "ok", "_all_titles": titles}


# ── 폴백이 실제로 작동하는가 ─────────────────────────────────────────

def test_cerebras_402_falls_back_to_groq():
    """★핵심★ 이게 프로덕션에서 실제로 일어나던 일이다."""
    responses = [_response(402, text="payment required"), _response(200, _ok(ANSWER))]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Cholera surge in Yemen"])):
        with patch.object(nw.requests, "post", side_effect=responses) as post:
            out = nw.fetch_news_pulse("cere-key", groq_key="groq-key")

    assert out["has_new_signal"] is True
    assert post.call_count == 2
    assert "groq" in out["source"], "어느 모델이 답했는지 남아야 한다"


def test_no_groq_key_keeps_the_original_exception_type():
    """폴백이 없을 때는 예전 계약 그대로 — 종류가 뭉개지면 안 된다.

    collector 가 `type(e).__name__` 을 로그에 찍는다. 통째로 감싸면
    429(기다리면 됨)와 402(돈 문제)가 로그에서 같아 보인다.
    """
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", return_value=_response(429, text="x")):
            with pytest.raises(nw.CerebrasRateLimited):
                nw.fetch_news_pulse("cere-key")


def test_groq_404_advances_to_next_model_but_402_stops():
    """404 는 '그 계정에 그 모델이 없다' — 다음 후보로. 402 는 계정 문제라 중단.

    모델을 계속 갈아봐야 같은 벽이면 한도만 태운다(cerebras_classify 와 같은 규칙).
    """
    # Cerebras 402 → groq 모델1 404 → groq 모델2 성공
    seq = [_response(402, text="p"), _response(404, text="model not found"),
           _response(200, _ok(ANSWER))]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", side_effect=seq) as post:
            out = nw.fetch_news_pulse("c", groq_key="g")
    assert out["has_new_signal"] is True
    assert post.call_count == 3

    # Cerebras 402 → groq 모델1 402 → 여기서 멈춘다(나머지 모델 안 부름)
    seq = [_response(402, text="p")] + [_response(402, text="q")] * 5
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", side_effect=seq) as post:
            with pytest.raises(nw.NewsWatchError) as exc:
                nw.fetch_news_pulse("c", groq_key="g")
    assert post.call_count == 2, "402 를 보고도 다음 Groq 모델을 계속 부르면 안 된다"
    assert "402" in str(exc.value)


def test_all_failures_are_listed_not_just_the_last():
    """왜 실패했는지가 **전부** 남아야 한다 — 오늘 하루 내내 나온 그 교훈."""
    seq = [_response(503, text="cere down")] + [_response(404, text="no model")] * 5
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", side_effect=seq):
            with pytest.raises(nw.NewsWatchError) as exc:
                nw.fetch_news_pulse("c", groq_key="g")
    msg = str(exc.value)
    assert "cerebras" in msg and "groq(" in msg
    assert "503" in msg and "404" in msg


def test_groq_only_works_without_cerebras_key():
    """Cerebras 키를 아예 빼도 이 층이 돌아야 한다."""
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", return_value=_response(200, _ok(ANSWER))) as post:
            out = nw.fetch_news_pulse(None, groq_key="g")
    assert out["has_new_signal"] is True
    assert post.call_count == 1
    assert post.call_args.args[0] == nw.GROQ_URL


def test_no_keys_at_all_is_its_own_reason():
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with pytest.raises(nw.NewsWatchError) as exc:
            nw.fetch_news_pulse(None, None)
    assert "둘 다 없음" in str(exc.value)


# ── ★ 예산 상한이 실제로 걸리는가 ★ ─────────────────────────────────

def test_groq_prompt_stays_inside_its_token_slice():
    """★가장 중요★ 현지어 뉴스 재분류와 같은 분(minute)을 나눠 쓴다.

    상한을 넘으면 429 가 나고, **본진인 재분류까지 같이 죽는다.**
    """
    fat = ["가" * nw.MAX_TITLE_CHARS] * nw.MAX_HEADLINES   # 최악: 전부 한국어 꽉 채움
    short = nw.groq_headlines(fat)

    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(short))
    prompt = nw.PROMPT.format(today="2026-08-28", headlines=numbered)
    est = len(prompt) / WORST_CHARS_PER_TOKEN

    assert est <= nw.GROQ_TOKEN_SLICE, (
        f"Groq 프롬프트 추정 {est:.0f} 토큰 > 예산 {nw.GROQ_TOKEN_SLICE}. "
        "상한을 낮추거나 GROQ_TOKEN_SLICE 를 재협상해라 — 넘기면 재분류까지 죽는다"
    )


def test_groq_slice_leaves_room_for_the_main_reclassifier():
    """이 층의 몫이 전체 TPM 예산을 다 먹으면 폴백을 붙인 의미가 없다."""
    from algorithms.cerebras_classify import GROQ_TPM_BUDGET
    assert nw.GROQ_TOKEN_SLICE < GROQ_TPM_BUDGET / 2, (
        "NewsWatch 몫이 절반을 넘으면 본진(현지어 뉴스 재분류)이 밀린다"
    )


def test_groq_path_reports_what_the_model_actually_saw():
    """제목을 깎아 보냈으면 headline_count 도 깎인 수여야 한다.

    검색된 개수를 적으면 '얼마나 얕은가' 대조가 거짓말이 된다 — 이 층을
    만든 이유가 바로 그 대조다.
    """
    many = [f"Outbreak headline number {i}" for i in range(nw.MAX_HEADLINES)]
    seq = [_response(402, text="p"), _response(200, _ok(ANSWER))]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(many)):
        with patch.object(nw.requests, "post", side_effect=seq):
            out = nw.fetch_news_pulse("c", groq_key="g")

    assert out["headlines_found"] == nw.MAX_HEADLINES
    assert out["headline_count"] <= nw.GROQ_MAX_HEADLINES
    assert out["headline_count"] < out["headlines_found"]


def test_cerebras_path_is_untrimmed():
    """Cerebras 가 살아나면 예전대로 40개를 다 본다 — 폴백 상한에 끌려가면 안 된다."""
    many = [f"Outbreak headline number {i}" for i in range(nw.MAX_HEADLINES)]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(many)):
        with patch.object(nw.requests, "post", return_value=_response(200, _ok(ANSWER))):
            out = nw.fetch_news_pulse("c", groq_key="g")

    assert out["headline_count"] == nw.MAX_HEADLINES
    assert out["source"] == "google_news+cerebras"


# ── collector 가 키 조건을 넓혔는가 ──────────────────────────────────

def test_collector_runs_newswatch_with_groq_key_alone():
    """예전엔 `if cerebras_key_watch:` 라 Cerebras 가 없으면 통째로 건너뛰었다."""
    import inspect
    import collector

    src = inspect.getsource(collector.collect_free_sources)
    assert "cerebras_key_watch or groq_key_watch" in src, (
        "NewsWatch 를 Cerebras 키에만 걸어두면 폴백이 있어도 안 돈다"
    )
    assert "fetch_news_pulse(cerebras_key_watch, groq_key_watch)" in src

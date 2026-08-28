"""NewsWatch — GroqWatch 무료 대체 후보 (2026-08-28).

GroqWatch 가 주기의 57% 를 티어 한도로 실패하는데 유료 전환은 선택지가 아니다.
뿌리는 **주입되는 검색량을 우리가 통제할 수 없다**는 것이었다:

    프롬프트 3,831~4,993 토큰 중 우리 지시문은 150 토큰 남짓
    나머지 96% 는 compound-mini 가 서버 쪽에서 끌어와 붙인 검색결과
    분당 한도 8,000 → 한 번 호출이 예산의 60~71%

그래서 검색(Google News RSS·무료)과 요약(Cerebras·하루 100만 토큰)을 분리했다.
이 테스트가 고정하는 것은 **통제권을 되찾았는가** 다 — 상한이 실제로 걸리는지,
실패 사유가 남는지, 검색어가 기사 제목 자리에 새지 않는지.
"""
from __future__ import annotations

import json
import pytest
import requests
from unittest.mock import patch

from algorithms import news_watch as nw


def _response(status: int, payload=None, text: str | None = None):
    r = requests.Response()
    r.status_code = status
    body = text if text is not None else json.dumps(payload or {})
    r._content = body.encode("utf-8")
    return r


def _cerebras_payload(content: str, total: int = 812, prompt: int = 760) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": total, "prompt_tokens": prompt},
    }


def _feed(titles: list[str]) -> dict:
    return {"slug": "global_watch", "status": "ok", "_all_titles": titles}


# ── ★핵심★ 토큰을 우리가 통제하는가 ──────────────────────────────────

def test_headline_count_is_capped():
    """GroqWatch 에 없던 손잡이 — 검색 결과가 아무리 많아도 상한이 걸린다."""
    many = [f"Outbreak news number {i}" for i in range(500)]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(many)):
        headlines = nw.fetch_headlines()

    assert len(headlines) == nw.MAX_HEADLINES == 40


def test_each_title_is_truncated():
    """제목 하나가 길어도 프롬프트가 폭발하지 않는다."""
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["X" * 5000])):
        headlines = nw.fetch_headlines()

    assert len(headlines[0]) == nw.MAX_TITLE_CHARS == 200


def test_prompt_stays_small_enough_to_never_hit_the_limit():
    """★가장 중요★ 최악의 입력에서도 프롬프트가 작아야 이 층의 존재 이유가 산다.

    GroqWatch 는 여기서 4,000~5,000 토큰이 됐고 분당 한도 8,000 을 위협했다.
    상한(40 × 200자)이면 대략 8,000자 = 2,000~3,000 토큰이고, Cerebras 한도는
    분당이 아니라 **하루 100만 토큰**이라 애초에 다른 자릿수의 싸움이 된다.
    """
    worst = ["Y" * 500 for _ in range(500)]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(worst)):
        headlines = nw.fetch_headlines()

    prompt = nw.PROMPT.format(today="2026-08-28", headlines="\n".join(headlines))
    assert len(prompt) < 10_000, f"프롬프트 {len(prompt)}자 — 상한이 새고 있다"


# ── 검색어가 기사 제목 자리에 새지 않는가 ────────────────────────────

def test_channel_title_is_not_mistaken_for_a_headline():
    """★실제로 겪은 함정★ Google News 는 첫 제목 자리에 **우리 검색어**를 돌려준다.

    2026-08-26 에 이걸 그대로 실었으면 브리핑 헤드라인이
    `"сибирская язва OR падёж оленей OR…"` 가 될 뻔했다.
    """
    titles = [
        '"(outbreak OR epidemic OR ebola) when:1d" - Google News',
        "Ebola cases surge in Ituri, DR Congo",
    ]
    with patch.object(nw, "fetch_local_feed", return_value=_feed(titles)):
        headlines = nw.fetch_headlines()

    assert headlines == ["Ebola cases surge in Ituri, DR Congo"]
    assert not any("Google News" in h for h in headlines)
    assert not any(" OR " in h for h in headlines)


# ── 실패 사유가 남는가 (2026-08-25·08-28 에 두 번 배운 것) ────────────

def test_rss_failure_carries_its_reason():
    """RSS 가 죽으면 '왜' 가 남아야 한다 — 조용한 None 이면 안 된다."""
    broken = {"slug": "global_watch", "status": "error", "error": "HTTPError: 503"}
    with patch.object(nw, "fetch_local_feed", return_value=broken):
        with pytest.raises(nw.NewsWatchError) as exc:
            nw.fetch_headlines()

    assert "503" in str(exc.value)


def test_cerebras_rate_limit_is_its_own_kind():
    """429 는 우리 버그가 아니다 — 파싱 실패와 섞이면 안 된다."""
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak somewhere"])):
        with patch.object(nw.requests, "post", return_value=_response(429, text="rate limited")):
            with pytest.raises(nw.CerebrasRateLimited):
                nw.fetch_news_pulse("key")


def test_bad_json_says_what_it_actually_got():
    """모델이 JSON 이 아닌 걸 돌려주면 **그 내용**이 보여야 한다."""
    payload = _cerebras_payload("어제는 조용했습니다")
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak somewhere"])):
        with patch.object(nw.requests, "post", return_value=_response(200, payload)):
            with pytest.raises(nw.NewsWatchError) as exc:
                nw.fetch_news_pulse("key")

    assert "어제는 조용했습니다" in str(exc.value)


def test_server_error_propagates():
    """5xx 는 그대로 올린다 — 파싱 문제와 다른 사건이다."""
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak somewhere"])):
        with patch.object(nw.requests, "post", return_value=_response(503, text="down")):
            with pytest.raises(requests.HTTPError):
                nw.fetch_news_pulse("key")


# ── GroqWatch 와 형태가 같은가 (갈아끼울 수 있어야 한다) ──────────────

def test_output_shape_matches_groq_pulse():
    """★대체 가능성의 조건★ 소비하는 쪽(signal_metrics 등)을 안 건드려도 되게."""
    payload = _cerebras_payload(json.dumps({
        "has_new_signal": True,
        "summary": "DR콩고 이투리에서 에볼라 사망자가 급증했다.",
        "diseases": ["에볼라"],
        "urgency": "high",
    }))
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Ebola surge in Ituri"])):
        with patch.object(nw.requests, "post", return_value=_response(200, payload)):
            out = nw.fetch_news_pulse("key")

    for key in ("has_new_signal", "summary", "diseases", "urgency",
                "tokens_used", "tokens_prompt"):
        assert key in out, key
    assert out["has_new_signal"] is True
    assert out["urgency"] == "high"
    assert out["diseases"] == ["에볼라"]
    assert out["headline_count"] == 1      # GroqWatch 엔 없던 대조 근거
    assert out["source"] == "google_news+cerebras"


def test_signal_metrics_can_score_it_unchanged():
    """소비하는 쪽이 실제로 이 형태를 읽을 수 있는지 — 흉내가 아니라 진짜로 호출한다."""
    from algorithms.signal_metrics import _groq_pulse_score

    payload = _cerebras_payload(json.dumps({
        "has_new_signal": True, "summary": "x", "diseases": [], "urgency": "high",
    }))
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", return_value=_response(200, payload)):
            out = nw.fetch_news_pulse("key")

    assert _groq_pulse_score({"groq_pulse": out}) is not None


def test_invalid_urgency_becomes_none_not_a_guess():
    """모델이 이상한 등급을 주면 지어내지 말고 None — 없는 걸 있다고 하면 안 된다."""
    payload = _cerebras_payload(json.dumps({
        "has_new_signal": True, "summary": "x", "diseases": [], "urgency": "매우높음",
    }))
    with patch.object(nw, "fetch_local_feed", return_value=_feed(["Outbreak"])):
        with patch.object(nw.requests, "post", return_value=_response(200, payload)):
            out = nw.fetch_news_pulse("key")

    assert out["urgency"] is None


def test_no_headlines_is_not_an_error_but_is_visible():
    """제목이 0개인 건 '고장' 이 아니라 '이번엔 없음' 일 수 있다 — 구분되게 드러낸다."""
    with patch.object(nw, "fetch_local_feed", return_value=_feed([])):
        with patch.object(nw.requests, "post") as post:
            out = nw.fetch_news_pulse("key")

    post.assert_not_called()          # 빈 목록으로 LLM 을 부르지 않는다
    assert out["has_new_signal"] is False
    assert out["headline_count"] == 0


# ── 질의가 의도대로 만들어지는가 ─────────────────────────────────────

def test_query_is_global_and_recent():
    url = nw._global_gnews_url()
    assert url.startswith("https://news.google.com/rss/search?q=")
    assert "hl=en-US" in url and "gl=US" in url
    assert "when%3A1d" in url, "최근 1일 필터가 빠졌다"
    assert "outbreak" in url

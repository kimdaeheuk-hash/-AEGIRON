"""Cerebras 가 죽으면 Groq 로 넘어간다 — 그리고 프롬프트가 예산 안에 든다 (2026-08-28).

## 왜
Cerebras 무료 쿼터가 끝났다(프로덕션 402 `payment_required_error`). 유료 전환은
선택지가 아니므로, 같은 계정에 이미 있고 **오늘 로그로 살아있음이 확인된** Groq
(`⚙ Groq 토큰 3990/8000`)로 넘어간다.

## 그런데 그냥 바꾸면 안 된다
Groq 무료 티어는 **분당 8,000 토큰**이다(2026-08-26 429 응답 원문). 예전 코드는
179개 피드의 `_all_titles` 를 **무제한**으로 밀어 넣었다 — 그래서 "하루 100만
토큰" 짜리 계정이 필요했고, 그게 끝나자 통째로 멈춘 것이다.

**통제할 수 없는 프롬프트가 문제였다.** NewsWatch(#8)에서 배운 것과 같다.

## 그래서 넣을 것만 넣는다
고경보 판정은 `hit_ratio >= 0.15` 이고 LLM 의 값어치는 키워드 오탐을 걷어내는
것이다. 임계에서 한참 아래인 피드는 LLM 이 무슨 말을 해도 고경보가 안 되므로
보지 않는다. 상한에 걸리면 **비율이 높은 피드부터** 들어간다.

이 파일이 고정하는 것: **상한이 실제로 걸리는가**, **넘어가는가**, 그리고
**두 제공자의 실패 사유를 모두 들고 가는가**.
"""
from __future__ import annotations

import json
import requests
from unittest.mock import patch

from algorithms import cerebras_classify as cc


def _response(status: int, payload=None, text: str | None = None):
    r = requests.Response()
    r.status_code = status
    r._content = (text if text is not None else json.dumps(payload or {})).encode("utf-8")
    return r


def _ok(n: int):
    return _response(200, {"choices": [{"message": {"content": json.dumps(
        [{"i": i, "relevant": i % 2 == 0} for i in range(n)]
    )}}]})


def _feed(ratio: float, n_titles: int = 30, lang: str = "ko"):
    return {"lang": lang, "status": "ok", "hit_ratio": ratio,
            "_all_titles": [f"제목 {i} " + "가" * 300 for i in range(n_titles)]}


# ── ★핵심★ 프롬프트가 무료 예산 안에 드는가 ─────────────────────────

def test_prompt_fits_the_free_tier_budget():
    """★이 층이 존재하는 이유★ 예전엔 상한이 없어서 하루 100만 토큰이 필요했다.

    Groq 무료 티어는 분당 8,000 토큰이다. 최악 입력(179개 피드 × 긴 제목 30개)
    에서도 프롬프트가 그 안에 들어야 이 대체가 성립한다.

    ⚠️ 토큰 환산을 영어 기준(4자=1토큰)으로 하면 안 된다 — 이 시스템의 제목은
    대부분 한국어·네팔어·아랍어이고 **1~1.5자당 1토큰**이다. 처음에 영어 기준으로
    잡았다가 상한이 예산의 3배(≈17,000 토큰)가 됐고, 이 테스트가 그걸 잡았다.
    """
    feeds = [_feed(0.9) for _ in range(179)]
    entries = cc.select_entries(feeds)

    numbered = "\n".join(f"{i}: [ko] {t}" for i, (_, t) in enumerate(entries))
    prompt = cc.MULTI_PROMPT_TEMPLATE.format(titles=numbered)
    worst_tokens = len(prompt) / cc.WORST_CHARS_PER_TOKEN     # 비영어 기준

    budget = cc.GROQ_TPM_BUDGET - cc.PROMPT_TOKEN_MARGIN
    assert len(entries) == cc.MAX_TOTAL_TITLES
    assert worst_tokens < budget, (
        f"비영어 최악 기준 ≈{worst_tokens:.0f} 토큰 — 예산 {budget} 을 넘는다"
    )


def test_budget_math_is_not_english_biased():
    """환산 가정 자체를 고정한다 — 여기가 느슨해지면 상한이 조용히 무의미해진다."""
    assert cc.WORST_CHARS_PER_TOKEN <= 1.5, (
        "한국어·데바나가리는 1~1.5자당 1토큰이다. 영어 기준(4)으로 되돌리면 "
        "상한이 실제 예산의 몇 배가 된다"
    )


def test_titles_are_capped_per_feed_and_truncated():
    feeds = [_feed(0.9, n_titles=100)]
    entries = cc.select_entries(feeds)

    assert len(entries) == cc.MAX_TITLES_PER_FEED
    assert all(len(t) <= cc.TITLE_MAX_CHARS for _, t in entries)


# ── 넣을 것만 넣는가 ─────────────────────────────────────────────────

def test_feeds_far_below_threshold_are_skipped():
    """임계에서 한참 아래면 LLM 이 봐도 고경보가 안 된다 — 토큰을 쓸 이유가 없다."""
    feeds = [_feed(0.9), _feed(0.01), _feed(0.02)]
    entries = cc.select_entries(feeds)

    assert {fi for fi, _ in entries} == {0}, "후보는 0번 피드뿐이어야 한다"


def test_candidate_band_reaches_below_the_alert_threshold():
    """임계(0.15) 바로 아래도 본다 — LLM 이 올릴 수도 있으니 경계를 넉넉히."""
    assert cc.CANDIDATE_RATIO < 0.15
    feeds = [_feed(0.12)]
    assert cc.select_entries(feeds), "임계 바로 아래 피드가 빠지면 안 된다"


def test_highest_ratio_feeds_win_when_capped():
    """★상한에 걸릴 때 무엇이 들어가는가★ 가장 의심스러운 것부터 들어가야 한다."""
    feeds = [_feed(0.2, n_titles=cc.MAX_TITLES_PER_FEED) for _ in range(50)]
    feeds.append(_feed(0.99, n_titles=cc.MAX_TITLES_PER_FEED))   # 마지막이 가장 높다
    entries = cc.select_entries(feeds)

    assert len(entries) == cc.MAX_TOTAL_TITLES
    assert 50 in {fi for fi, _ in entries}, "비율 최고 피드가 잘려나갔다"


def test_dead_feeds_are_not_sent():
    feeds = [{"lang": "ko", "status": "error", "error": "timeout"}]
    assert cc.select_entries(feeds) == []


# ── 제공자 전환이 실제로 되는가 ──────────────────────────────────────

def test_falls_over_to_groq_when_cerebras_is_out_of_quota():
    """★핵심★ 402 를 만나면 Groq 로 넘어가서 성공해야 한다."""
    feeds = [_feed(0.9, n_titles=4)]
    calls: list[str] = []

    def fake_post(url, model, api_key, prompt):
        calls.append(url)
        if url == cc.CEREBRAS_URL:
            return _response(402, text='{"code":"payment_required"}')
        return _ok(4)

    with patch.object(cc, "_post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere-key", groq_key="groq-key")

    assert reason is None, f"Groq 로 넘어가서 성공해야 한다: {reason}"
    assert calls == [cc.CEREBRAS_URL, cc.GROQ_URL]
    assert "llm_hit_ratio" in feeds[0]


def test_cerebras_success_does_not_call_groq():
    """Cerebras 가 살아나면 자동으로 돌아온다 — 사람이 손댈 필요가 없다."""
    feeds = [_feed(0.9, n_titles=4)]
    calls: list[str] = []

    def fake_post(url, model, api_key, prompt):
        calls.append(url)
        return _ok(4)

    with patch.object(cc, "_post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere-key", groq_key="groq-key")

    assert reason is None
    assert calls == [cc.CEREBRAS_URL]


def test_both_failures_are_reported_not_just_the_last():
    """★어느 쪽이 왜 안 됐는지★ 하나만 남기면 또 추측하게 된다."""
    feeds = [_feed(0.9, n_titles=4)]

    def fake_post(url, model, api_key, prompt):
        if url == cc.CEREBRAS_URL:
            return _response(402, text="quota gone")
        return _response(429, text="tpm exceeded")

    with patch.object(cc, "_post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere-key", groq_key="groq-key")

    assert reason is not None
    assert "Cerebras" in reason and "402" in reason
    assert "Groq" in reason and "429" in reason


def test_missing_groq_key_is_stated():
    feeds = [_feed(0.9, n_titles=4)]
    with patch.object(cc, "_post", return_value=_response(402, text="x")):
        reason = cc.classify_multi_feed(feeds, "cere-key", groq_key=None)
    assert "Cerebras" in reason and "402" in reason
    assert "Groq" not in reason      # 아예 시도하지 않았다


def test_groq_uses_plain_models_not_the_web_search_one():
    """★GroqWatch 를 터뜨린 그 모델을 쓰면 안 된다★

    413/429 의 원인은 compound-mini 가 **서버 쪽에서 끌어온 검색결과**였다.
    분류는 우리가 준 제목만 있으면 되므로 순수 추론 모델을 쓴다.
    """
    assert all("compound" not in m for m in cc.GROQ_MODELS)
    assert cc.GROQ_URL.startswith("https://api.groq.com/")


def test_first_groq_candidate_is_the_evidenced_one():
    """★찍지 말고 근거를 쓴다★

    `groq_watch.py` 에 기록된 이 계정의 실제 429 응답이 모델 ID 를 알려준다:
        Rate limit reached for model `openai/gpt-oss-120b`
    2026-08-28 에 근거 없이 `llama-3.3-70b-versatile` 로 찍었다가 404 가 났다.
    """
    assert cc.GROQ_MODELS[0] == "openai/gpt-oss-120b"
    assert cc.GROQ_MODELS[-1] == "llama-3.3-70b-versatile", "404 났던 건 맨 뒤로"


def test_404_advances_to_the_next_model():
    """모델이 없으면 다음 후보로 — 프로덕션이 답을 알려주게 한다."""
    feeds = [_feed(0.9, n_titles=4)]
    tried: list[str] = []

    def fake_post(url, model, api_key, prompt):
        tried.append(model)
        if url == cc.CEREBRAS_URL:
            return _response(402, text="quota")
        if model != cc.GROQ_MODELS[1]:
            return _response(404, text="model not found")
        return _ok(4)

    with patch.object(cc, "_post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere", groq_key="groq")

    assert reason is None
    assert tried[1:3] == cc.GROQ_MODELS[:2], f"404 뒤 다음 후보로 넘어가야 한다: {tried}"


def test_non_404_does_not_burn_the_remaining_candidates():
    """402·429 는 모델 문제가 아니다 — 남은 후보를 더 태우면 한도만 낭비한다."""
    feeds = [_feed(0.9, n_titles=4)]
    tried: list[str] = []

    def fake_post(url, model, api_key, prompt):
        tried.append(model)
        if url == cc.CEREBRAS_URL:
            return _response(402, text="quota")
        return _response(429, text="tpm exceeded")

    with patch.object(cc, "_post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere", groq_key="groq")

    assert reason is not None
    groq_tried = [m for m in tried if m in cc.GROQ_MODELS]
    assert len(groq_tried) == 1, f"429 인데 후보를 더 태웠다: {groq_tried}"


def test_successful_provider_is_recorded():
    """어느 제공자·모델이 먹었는지 남는다 — 다음엔 추측할 필요가 없다."""
    feeds = [_feed(0.9, n_titles=4)]

    def fake_post(url, model, api_key, prompt):
        if url == cc.CEREBRAS_URL:
            return _response(402, text="quota")
        return _ok(4)

    with patch.object(cc, "_post", side_effect=fake_post):
        cc.classify_multi_feed(feeds, "cere", groq_key="groq")

    assert feeds[0].get("llm_provider", "").startswith("Groq(")


def test_unclassified_feeds_keep_keyword_ratio():
    """후보에 안 든 피드는 llm_hit_ratio 가 안 채워져 키워드 값이 그대로 쓰인다."""
    feeds = [_feed(0.9, n_titles=4), _feed(0.01, n_titles=4)]
    with patch.object(cc, "_post", return_value=_ok(4)):
        cc.classify_multi_feed(feeds, "cere-key")

    assert "llm_hit_ratio" in feeds[0]
    assert "llm_hit_ratio" not in feeds[1]

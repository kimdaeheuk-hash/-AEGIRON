"""현지어 뉴스 재분류가 **쓴 토큰을 아무 데도 남기지 않았다** (2026-10-12).

## 배경 — 3순위 조사에서 나온 것

캡틴이 "NIM 을 더 키워야겠어" 로 지시한 3순위는 *현지어 뉴스 재분류를 Groq 에서
NIM 으로 옮겨 Groq 예산을 NewsWatch 전용으로 비운다* 였다. 근거는 GroqWatch 은퇴
사유였다 — *"죽은 채로 살아있는 소스의 예산을 먹고 있었다"*
(`source_health.RETIRED_SOURCES`).

**조사 결과 이전은 하지 않았다.** 로그(2026-10-05~12)에서 Groq 의 429·402 는
**0건**이다(나온 429 는 전부 UN Comtrade 무역 스캔이다). `cerebras_classify` 가
이미 입력을 통제하고 있어서다 — `CANDIDATE_RATIO`·`MAX_TITLES_PER_FEED`·
`MAX_TOTAL_TITLES` 로 임계 근처 피드만 보낸다. 게다가 분류기를 갈면
`llm_hit_ratio` 가 달라져 `local_news_llm_relevant`(GAI 지표, 카테고리
`ai_extracted`)의 값이 변한다 — 소킹 중에 보정 없이 할 일이 아니다.

## 그런데 **한도에 얼마나 가까운지 알 수 없는 상태**였다

이 층과 NewsWatch 는 같은 `GROQ_API_KEY` 의 **분당 8,000 토큰을 나눠 쓴다.**
그런데 사용량이 한쪽만 보였다:

    ⚙ NewsWatch[google_news+groq(openai/gpt-oss-120b)] 토큰 1517 (프롬프트 654)  ← 보인다
    현지어 뉴스: … , LLM 재분류 14개 피드                                        ← 숫자가 없다

`_try_classify` 가 응답의 `usage` 를 **아예 읽지 않았다.** 그래서 '아직 429 가 안
났다' 는 알아도 '언제 날지' 는 몰랐다. GroqWatch 는 은퇴 전에 `⚙ Groq 토큰
3990/8000` 을 찍었다 — 그 가시성이 이 층엔 없었다.

공급자 이름은 사정이 다르다. `local_news.py` 가 반환값에 올리고
`quality_health._check_llm_provider_present` 가 품질 불변식 6개 중 하나로 그
**존재**를 검사한다. 버려지지는 않았다. 다만 **로그엔 없어서**, curl 이 막히는
날(실측 2026-10-08~12 닷새 연속 403)에는 아침 점검이 `/api/status` 를 못 열어
어느 공급자가 답했는지 볼 방법이 없었다.

## 이 수리의 입장

이전은 하지 않는다. **먼저 숫자를 보이게 만든다** — 그러면 NIM 이전이 필요한지를
추측이 아니라 그 숫자가 답한다. #63 이 '본문 없는 200' 을 장부에 적게 만든 뒤
사흘 만에 NIM 의 원인이 특정된 것과 같은 순서다.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import requests

from algorithms import cerebras_classify as cc
from algorithms.cerebras_classify import GROQ_TPM_LIMIT, usage_line

COLLECTOR = Path(__file__).resolve().parent.parent / "collector.py"


def _news(**over) -> dict:
    base = {"llm_classified_feeds": 14, "llm_provider": "Groq(openai/gpt-oss-120b)",
            "llm_total_tokens": 2103, "llm_prompt_tokens": 1890,
            "llm_answered_titles": 14, "llm_sent_titles": 14}
    base.update(over)
    return base


# ── 성공 주기는 숫자를 남긴다 ──────────────────────────────────────

def test_the_line_carries_provider_tokens_budget_and_title_counts():
    line = usage_line(_news())

    assert line.startswith("⚙ 현지어 뉴스 재분류[Groq(openai/gpt-oss-120b)]")
    assert "토큰 2103/8000" in line           # 한도까지 — GroqWatch 가 찍던 모양
    assert "(프롬프트 1890)" in line
    assert "제목 14/14개" in line


def test_the_budget_shown_is_the_observed_groq_limit():
    """숫자를 손으로 적지 않는다 — 상수에서 끌어온다."""
    assert f"/{GROQ_TPM_LIMIT}" in usage_line(_news())


def test_truncated_response_is_visible_in_the_title_counts():
    """보낸 제목과 답받은 제목이 다르면 커버가 반토막 난 것이다."""
    line = usage_line(_news(llm_answered_titles=7, llm_sent_titles=14))
    assert "제목 7/14개" in line


# ── 모르는 것을 0 으로 적지 않는다 ────────────────────────────────

def test_missing_usage_says_so_instead_of_claiming_zero():
    """★ NIM 의 `출력토큰` 과 같은 규칙 ★ 서버가 usage 를 안 주는 것과 '0 토큰을
    썼다' 는 전혀 다른 사실이다. 섞으면 한도 여유를 거꾸로 읽는다."""
    line = usage_line(_news(llm_total_tokens=None, llm_prompt_tokens=None))

    assert "토큰 모름(서버가 usage 미제공)" in line
    assert "토큰 0" not in line
    assert "/8000" not in line               # 쓴 양을 모르면 한도를 들이대지 않는다


def test_non_integer_usage_is_not_trusted():
    """usage 는 서버가 채우는 칸이다 — 정수가 아니면 안 싣는다."""
    line = usage_line(_news(llm_total_tokens="2103"))
    assert "토큰 모름(서버가 usage 미제공)" in line


def test_a_bool_is_not_a_token_count():
    """파이썬에서 True 는 int 다 — 걸러내지 않으면 `토큰 True` 가 찍힌다."""
    line = usage_line(_news(llm_total_tokens=True))
    assert "토큰 모름(서버가 usage 미제공)" in line
    assert "True" not in line


def test_prompt_tokens_alone_missing_still_shows_the_total():
    line = usage_line(_news(llm_prompt_tokens=None))
    assert "토큰 2103/8000" in line
    assert "프롬프트" not in line


def test_unrecorded_provider_is_named_as_such():
    line = usage_line(_news(llm_provider=None))
    assert "[공급자 미기록]" in line


def test_the_budget_is_not_claimed_for_a_provider_whose_limit_we_do_not_know():
    """Cerebras 의 분당 한도는 우리가 모른다 — 8000 을 들이대면 거짓이다."""
    line = usage_line(_news(llm_provider="Cerebras"))
    assert "토큰 2103" in line
    assert "/8000" not in line


# ── 실패 주기는 이 줄을 내지 않는다 (실패 줄이 따로 나간다) ───────

def test_a_cycle_without_reclassification_produces_no_line():
    """재분류가 안 된 주기엔 `❌ … 재분류 실패` 줄이 사유와 함께 따로 나간다 —
    여기서 또 한 줄을 내면 같은 사실이 두 번 읽힌다."""
    assert usage_line(_news(llm_classified_feeds=0)) is None
    assert usage_line({}) is None


# ── 집계: 피드 dict 에 담긴 값이 반환값까지 올라온다 ───────────────

def test_token_counts_reach_the_news_result(monkeypatch):
    """★ 이 저장소의 반복 결함 ★ 계산해놓고 반환값에서 떨어지면 수집기가 못 본다
    (Mobility 가 공항별 사유를 버린 것과 같은 모양). 피드 하나에 담긴 토큰 수가
    fetch_all_local_news 의 결과까지 올라오는지 고정한다."""
    from algorithms import cerebras_classify as cc
    from algorithms import local_news as ln

    feeds = [{"slug": "gn_us", "lang": "en", "items": [], "kw_hits": 0, "hit_ratio": 0.0,
              "llm_hit_ratio": 0.2, "llm_provider": "Groq(m)",
              "llm_total_tokens": 2103, "llm_prompt_tokens": 1890,
              "llm_answered_titles": 14, "llm_sent_titles": 14}]

    monkeypatch.setattr(ln, "fetch_feeds_with_probe",
                        lambda *a, **k: (list(feeds), {"attempts": 1}))
    # local_news 는 이 함수를 호출 시점에 모듈에서 가져온다 — 그래서 여기 건다.
    monkeypatch.setattr(cc, "classify_multi_feed", lambda *a, **k: None)

    out = ln.fetch_all_local_news(cerebras_key="k", groq_key="g")

    assert out["llm_total_tokens"] == 2103
    assert out["llm_prompt_tokens"] == 1890
    assert out["llm_provider"] == "Groq(m)"
    # 그 결과로 수집기 줄이 실제로 만들어진다.
    assert "토큰 2103/8000" in (usage_line(out) or "")


# ── 응답의 usage 를 실제로 읽는가 (예전엔 choices 만 꺼냈다) ────────

def _response(status: int, payload=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(payload or {}).encode("utf-8")
    return r


def _feed(ratio: float = 0.2, n_titles: int = 3):
    return {"lang": "ko", "status": "ok", "hit_ratio": ratio,
            "_all_titles": [f"제목 {i}" for i in range(n_titles)]}


def test_usage_from_the_response_is_read_and_stored_on_the_feed():
    """★ 핵심 배선 ★ 예전엔 `r.json()["choices"][0]` 만 꺼내고 `usage` 는 아예
    보지 않았다. 응답에 숫자가 와 있는데도 아무 데도 안 남는 상태였다."""
    feeds = [_feed()]
    resp = _response(200, {
        "choices": [{"finish_reason": "stop", "message": {"content": "[0]"}}],
        "usage": {"total_tokens": 2103, "prompt_tokens": 1890},
    })
    with patch.object(cc, "_post", return_value=resp):
        assert cc.classify_multi_feed(feeds, "cere-key") is None

    assert feeds[0]["llm_total_tokens"] == 2103
    assert feeds[0]["llm_prompt_tokens"] == 1890
    assert feeds[0]["llm_provider"] == "Cerebras"


def test_a_response_without_usage_leaves_the_token_keys_absent():
    """없는 것을 0 으로 채우지 않는다 — 비어 있어야 usage_line 이 '모름' 이라고 말한다."""
    feeds = [_feed()]
    resp = _response(200, {
        "choices": [{"finish_reason": "stop", "message": {"content": "[0]"}}]})
    with patch.object(cc, "_post", return_value=resp):
        assert cc.classify_multi_feed(feeds, "cere-key") is None

    assert "llm_total_tokens" not in feeds[0]
    assert "llm_prompt_tokens" not in feeds[0]


# ── 배선 — 수집기가 이 줄을 실제로 찍는가 ──────────────────────────

def test_collector_calls_usage_line_and_sends_it_to_the_log():
    """★ 만들어만 두고 아무도 안 부르는 층 ★ 이 저장소에서 반복된 실패 유형이다.
    `usage_line` 의 결과가 `log` 로 나가는 두 단계를 AST 로 고정한다."""
    tree = ast.parse(COLLECTOR.read_text(encoding="utf-8"))

    assigned: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "usage_line"):
            assigned.update(t.id for t in node.targets if isinstance(t, ast.Name))
    assert assigned, "collector 가 usage_line 을 부르지 않는다"

    logged = any(
        isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        and call.func.id == "log"
        and any(isinstance(n, ast.Name) and n.id in assigned
                for arg in call.args for n in ast.walk(arg))
        for call in ast.walk(tree))
    assert logged, "usage_line 결과가 log 로 나가지 않는다"


def test_a_string_usage_value_is_not_stored_on_the_feed():
    """★ 변형 검증에서 드러난 빈틈 ★ `usage_line` 만 정수를 검사하면, 담는 쪽
    (`_try_classify`)의 검사를 풀어도 시험이 안 깨진다. 두 겹 모두 고정한다 —
    usage 는 서버가 채우는 칸이라 모양을 믿지 않는다."""
    feeds = [_feed()]
    resp = _response(200, {
        "choices": [{"finish_reason": "stop", "message": {"content": "[0]"}}],
        "usage": {"total_tokens": "2103", "prompt_tokens": "1890"},
    })
    with patch.object(cc, "_post", return_value=resp):
        assert cc.classify_multi_feed(feeds, "cere-key") is None

    assert "llm_total_tokens" not in feeds[0]
    assert "llm_prompt_tokens" not in feeds[0]


def test_a_bool_usage_value_is_not_stored_on_the_feed():
    feeds = [_feed()]
    resp = _response(200, {
        "choices": [{"finish_reason": "stop", "message": {"content": "[0]"}}],
        "usage": {"total_tokens": True},
    })
    with patch.object(cc, "_post", return_value=resp):
        assert cc.classify_multi_feed(feeds, "cere-key") is None

    assert "llm_total_tokens" not in feeds[0]

"""응답이 잘려도 건진다 — 2026-08-29 실패 14건의 정체 (2026-08-30).

## 사고
08-29 프로덕션 로그, UTC 00~23시 24주기 중 **14주기(58%)가 LLM 재분류 실패**.
18~23시는 6주기 연속. 그동안 고경보 51~69개가 전부 키워드 기준(오탐 많음)으로
나갔다.

**사유가 14회 전부 같았다**: Cerebras 402 + Groq `JSONDecodeError`.
Groq 쪽에서 402 도 429 도 **한 번도** 없었다 — 한도가 아니라 응답을 못 읽은 것이다.

파싱 실패 지점이 char 0 · 2 · 33 · 167 · 205 · 405 · 756 · 1079 · 1360 · 1552 ·
1612 로 제각각인데, 이건 형식이 틀린 모양이 아니라 **매번 다른 길이에서 잘린**
모양이다. 대조가 원인을 좁혀준다 — NewsWatch 는 **같은 모델·같은 파라미터**로
같은 24주기 중 22번 성공했고, 다른 건 출력 길이뿐이다(두 문장 vs 60개 배열).

## 이 파일이 고정하는 것
1. 잘린 응답에서 **답받은 데까지는 쓴다** (전부 버리지 않는다)
2. ★ 답 안 받은 제목을 `False` 로 채우지 않는다 ★ — 채우면 실제 발병 보도가
   '무관함' 으로 덮여 **신호가 지워진다.** 잘림보다 이쪽이 훨씬 나쁘다.
3. 두 형식(번호만 / 예전 개체)을 모두 받는다
4. 프로즈 속 각주 `[1]` 을 답으로 오인하지 않는다
5. 실패 사유에 `finish_reason` 이 실린다 — 이게 없어서 14건이 전부
   "JSONDecodeError" 한 덩어리로만 남았다
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


def _content(text: str, finish: str = "stop"):
    return _response(200, {"choices": [{"finish_reason": finish,
                                        "message": {"content": text}}]})


def _feed(ratio: float, n_titles: int, lang: str = "ko"):
    return {"lang": lang, "status": "ok", "hit_ratio": ratio,
            "_all_titles": [f"제목 {i}" for i in range(n_titles)]}


def _run(feeds, response):
    with patch.object(cc, "_post", return_value=response):
        return cc.classify_multi_feed(feeds, "cere-key")


# ── ★핵심★ 잘려도 건진다 ────────────────────────────────────────────

def test_truncated_array_still_classifies_what_came_back():
    """★이 커밋이 존재하는 이유★ 예전엔 마지막 하나가 잘리면 전부 버렸다.

    60개 중 40개가 멀쩡히 왔는데 `json.loads` 한 방이라 0개가 됐고, 고경보가
    통째로 키워드 기준으로 떨어졌다.
    """
    feeds = [_feed(0.9, 5), _feed(0.8, 5)]          # 제목 10개가 후보로 들어간다
    # 6번까지 답하고 잘렸다(닫는 대괄호 없음)
    reason = _run(feeds, _content("[0, 2, 5", finish="length"))

    assert reason is None, f"부분 성공은 성공이어야 한다: {reason}"
    assert "llm_hit_ratio" in feeds[0], "답받은 피드는 분류돼야 한다"


def test_unanswered_titles_are_not_silently_marked_irrelevant():
    """★가장 위험한 쪽★ 잘린 뒤를 `False` 로 채우면 신호가 지워진다.

    답을 못 받은 제목은 "발병 보도가 아니다" 가 아니라 **모른다** 이다.
    모르는 걸 '아니오' 로 적으면 실제 발병 보도가 조용히 덮인다 — 잘림 자체보다
    이쪽이 훨씬 나쁘다. 그래서 그 제목은 키워드 값을 그대로 쓰게 둔다.
    """
    first, second = _feed(0.9, 5), _feed(0.8, 5)
    # 첫 피드 제목(전역 0~4)까지만 답하고 잘렸다 — 둘째 피드는 답이 없다.
    _run([first, second], _content("[0, 1", finish="length"))

    assert "llm_hit_ratio" in first, "답받은 피드는 분류된다"
    assert "llm_hit_ratio" not in second, (
        "답 못 받은 피드에 llm_hit_ratio 가 생기면 안 된다 — "
        "키워드 값이 LLM 값인 척 덮인다")


def test_answered_watermark_does_not_run_past_the_truncation():
    """번호 형식에서 '목록에 없음 = 아니오' 는 **모델이 훑은 데까지만** 참이다."""
    feeds = [_feed(0.9, 10)]
    _run(feeds, _content("[0, 3", finish="length"))

    # 3번까지 답했으므로 0~3 만 판정 대상이다. 4~9 는 답이 없다.
    assert feeds[0]["llm_relevant_count"] == 2          # 0 과 3
    assert feeds[0]["llm_hit_ratio"] == round(2 / 4, 3)


# ── 두 형식을 모두 받는다 ────────────────────────────────────────────

def test_compact_index_format_is_understood():
    """2026-08-30~ 요청 형식: 해당 번호만. 출력이 ~10배 작아 잘릴 일이 줄어든다."""
    feeds = [_feed(0.9, 4)]
    reason = _run(feeds, _content("[0, 2]"))

    assert reason is None
    assert feeds[0]["llm_relevant_count"] == 2
    assert feeds[0]["llm_hit_ratio"] == 0.5            # 4개 중 2개


def test_legacy_object_format_still_works():
    """모델이 옛 습관대로 개체 배열로 답해도 받아준다 — 형식 하나에 걸지 않는다."""
    feeds = [_feed(0.9, 4)]
    payload = json.dumps([{"i": i, "relevant": i < 2} for i in range(4)])
    reason = _run(feeds, _content(payload))

    assert reason is None
    assert feeds[0]["llm_relevant_count"] == 2


# ── 조용히 틀리지 않는다 ────────────────────────────────────────────

def test_footnote_bracket_in_prose_is_not_mistaken_for_the_answer():
    """★번호 형식이 새로 만든 함정★ 각주 `[1]` 도 번호 배열로 '말이 되게' 파싱된다.

    예전 개체 형식은 이런 걸 파싱하다 시끄럽게 실패했다. 번호 형식은 조용히
    틀린 답이 되므로, 쓸 수 있는 원소가 가장 많은 후보를 골라야 한다.
    """
    feeds = [_feed(0.9, 5)]
    _run(feeds, _content("자료[1] 를 참고했다. 최종 답: [0, 2, 4]"))

    assert feeds[0]["llm_relevant_count"] == 3, "각주가 아니라 실제 답을 읽어야 한다"


def test_empty_array_means_none_relevant_not_failure():
    """`[]` 는 정당한 답이다 — "해당하는 제목이 하나도 없다".

    이걸 실패로 치면 조용한 날마다 고경보가 키워드 기준으로 떨어진다.
    """
    feeds = [_feed(0.9, 4)]
    reason = _run(feeds, _content("[]"))

    assert reason is None, f"빈 배열은 성공이어야 한다: {reason}"
    assert feeds[0]["llm_relevant_count"] == 0
    assert feeds[0]["llm_hit_ratio"] == 0.0


def test_prose_without_any_array_is_reported_not_guessed():
    feeds = [_feed(0.9, 4)]
    reason = _run(feeds, _content("판단하기 어렵습니다."))

    assert reason is not None
    assert "llm_hit_ratio" not in feeds[0], "못 읽었으면 아무것도 채우지 않는다"


# ── ★ 왜 실패했는지 남는다 ★ ────────────────────────────────────────

def test_failure_reason_carries_finish_reason():
    """이게 없어서 08-29 실패 14건이 전부 'JSONDecodeError' 한 덩어리였다.

    `length` 면 잘린 것이고 `stop` 이면 모델이 애초에 JSON 을 안 준 것이다 —
    조치가 서로 다른데 로그가 그 둘을 구분해주지 못했다.
    """
    feeds = [_feed(0.9, 4)]
    reason = _run(feeds, _content("설명만 하고 끝났다", finish="length"))

    assert "finish_reason=length" in reason, f"사유에 finish_reason 이 있어야 한다: {reason}"


def test_empty_content_falls_back_to_reasoning_field():
    """gpt-oss 는 content 가 비고 reasoning 으로 오는 경우가 있다.

    예전엔 content 만 봐서 그 경우가 `Expecting value: line 1 column 1 (char 0)`
    한 줄로만 남았다 — 빈 문자열을 파싱한 것이다.
    """
    feeds = [_feed(0.9, 4)]
    r = _response(200, {"choices": [{"finish_reason": "stop",
                                     "message": {"content": "", "reasoning": "[0, 1]"}}]})
    reason = _run(feeds, r)

    assert reason is None, f"reasoning 에 있는 답을 읽어야 한다: {reason}"
    assert feeds[0]["llm_relevant_count"] == 2


# ── 상한을 우리가 쥔다 ──────────────────────────────────────────────

def test_request_sets_an_explicit_completion_cap():
    """예전엔 상한을 안 줘서 제공자 기본값에 맡겼고, 그 값이 얼마인지 몰랐다."""
    sent = {}

    def fake_post(url, json=None, **kw):
        sent.update(json or {})
        return _content("[0]")

    with patch.object(cc.requests, "post", side_effect=fake_post):
        cc.classify_multi_feed([_feed(0.9, 2)], "cere-key")

    assert sent.get("max_tokens") == cc.MAX_COMPLETION_TOKENS
    assert sent.get("reasoning_effort") == cc.REASONING_EFFORT


def test_reasoning_effort_is_dropped_and_retried_when_provider_rejects_it():
    """★검증할 수 없는 파라미터를 단정하지 않는다★

    이 샌드박스는 Groq 에 못 닿아 `reasoning_effort` 지원 여부를 확인할 수 없다.
    모델 ID 를 찍었다가 404 를 맞은 2026-08-28 의 교훈대로, 단정하는 대신
    400 이면 빼고 한 번 더 보내고 프로덕션이 답하게 한다.
    """
    bodies = []

    def fake_post(url, json=None, **kw):
        bodies.append(json or {})
        if "reasoning_effort" in (json or {}):
            return _response(400, text='{"error":"unknown parameter"}')
        return _content("[0]")

    feeds = [_feed(0.9, 2)]
    with patch.object(cc.requests, "post", side_effect=fake_post):
        reason = cc.classify_multi_feed(feeds, "cere-key")

    assert reason is None, f"빼고 다시 보내 성공해야 한다: {reason}"
    assert len(bodies) == 2 and "reasoning_effort" not in bodies[1]


# ── 부분 성공이 보인다 ──────────────────────────────────────────────

def test_partial_coverage_is_recorded_not_hidden():
    """잘려서 절반만 분류된 걸 '성공' 으로만 적으면 커버가 반토막 나도 모른다."""
    feeds = [_feed(0.9, 10)]
    _run(feeds, _content("[0, 3", finish="length"))

    marker = next(f for f in feeds if "llm_hit_ratio" in f)
    assert marker["llm_answered_titles"] == 4          # 0~3 만 답받았다
    # 피드당 MAX_TITLES_PER_FEED(5)개까지만 보낸다 — 10개짜리 피드여도 5개다.
    assert marker["llm_sent_titles"] == cc.MAX_TITLES_PER_FEED
    assert marker["llm_finish_reason"] == "length"


def test_local_news_surfaces_the_coverage_the_collector_logs():
    """수집 로그가 읽는 계약이다 — 여기서 안 나오면 로그에도 안 찍힌다.

    `llm_classified_feeds` 만 보면 잘려서 절반만 분류된 주기와 멀쩡한 주기가
    똑같아 보인다. 그래서 보낸 수·답받은 수를 함께 내보낸다.
    """
    from algorithms import local_news as ln

    feed = lambda *a: {"slug": a[0], "lang": a[1], "region": a[2], "status": "ok",
                       "item_count": 10, "keyword_hits": 5, "hit_ratio": 0.5,
                       "_all_titles": ["t"]}
    with patch.object(ln, "fetch_local_feed", side_effect=feed):
        with patch.object(cc.requests, "post", return_value=_content("[0, 1", "length")):
            out = ln.fetch_all_local_news(cerebras_key="key")

    assert out["llm_classified_feeds"] > 0
    assert out["llm_answered_titles"] == 2, "답받은 제목 수가 드러나야 한다"
    assert out["llm_sent_titles"] > out["llm_answered_titles"], "잘렸다는 게 보여야 한다"
    assert out["llm_provider"] == "Cerebras"

"""Cerebras 재분류가 꺼지면 그 사실이 보여야 한다 (2026-08-28).

## 사고
계정이 `402 Payment Required` 를 돌려주고 있었다. 그런데 `cerebras_classify` 가
실패를 통째로 삼켰다:

    except Exception:
        return          # 로그 한 줄도 안 남긴다

그러면 `llm_hit_ratio` 가 안 채워지고, 고경보 판정이

    r.get("llm_hit_ratio", r.get("hit_ratio", 0)) >= 0.15

를 통해 **조용히 키워드 매칭으로 떨어진다.** 그 키워드 방식이 바로 이 재분류를
만든 이유였다 — *"여행경보·보건정책·연구비 지원 기사도 '병' 관련 단어를 쓴다"*
(2026-07-08). 즉 **개선이 꺼진 채 도는데 아무도 모르는 상태**였다.

## 얼마나 오래
수집 로그의 `LLM 재분류 N개 피드` 태그는 실패 시 **빈 문자열이 될 뿐**이라
줄 모양이 거의 같았다. Railway 로그를 2026-08-27 06:00 UTC 까지 거슬러도 그
태그가 한 번도 없다 — **최소 29시간**, 시작 시점은 로그 보존 한계로 못 올라간다.

그동안 소스 헬스는 `정상 20/20 · 문제 없음` 이라고 찍고 있었다.

## 오늘 네 번째다
GroqWatch(8/25) · Mobility(8/28 아침) · 은퇴 소스 함정 · 그리고 이것.
전부 같은 모양이다 — **조용한 `except` 가 이유를 버린다.**
"""
from __future__ import annotations

import json
import requests
from unittest.mock import patch

import pytest

from algorithms import cerebras_classify as cc
from algorithms import local_news as ln


def _response(status: int, payload=None, text: str | None = None):
    r = requests.Response()
    r.status_code = status
    r._content = (text if text is not None else json.dumps(payload or {})).encode("utf-8")
    return r


def _feeds():
    return [
        {"lang": "ko", "hit_ratio": 0.9, "_all_titles": ["콜레라 집단감염 발생", "여행경보 안내"]},
        {"lang": "ne", "hit_ratio": 0.2, "_all_titles": ["डेंगु प्रकोप"]},
    ]


# ── 실패가 사유를 들고 돌아오는가 ────────────────────────────────────

def test_payment_required_is_reported_not_swallowed():
    """★핵심★ 402 는 조용히 사라지면 안 된다 — 이게 실제로 일어난 일이다."""
    with patch.object(cc.requests, "post",
                      return_value=_response(402, text="free tier exhausted")):
        reason = cc.classify_multi_feed(_feeds(), "key")

    assert reason is not None, "예전엔 여기서 None(성공)처럼 조용히 끝났다"
    assert "402" in reason
    assert "결제" in reason


def test_rate_limit_and_payment_say_different_things():
    """429(기다리면 됨)와 402(돈 문제)는 조치가 다르다 — 섞이면 안 된다."""
    with patch.object(cc.requests, "post", return_value=_response(402, text="x")):
        paid = cc.classify_multi_feed(_feeds(), "key")
    with patch.object(cc.requests, "post", return_value=_response(429, text="y")):
        limited = cc.classify_multi_feed(_feeds(), "key")

    assert "402" in paid and "429" in limited
    assert paid != limited


def test_server_error_carries_its_type():
    with patch.object(cc.requests, "post", return_value=_response(503, text="down")):
        reason = cc.classify_multi_feed(_feeds(), "key")
    assert "HTTPError" in reason


def test_bad_json_shows_what_it_got():
    payload = {"choices": [{"message": {"content": "분류할 수 없습니다"}}]}
    with patch.object(cc.requests, "post", return_value=_response(200, payload)):
        reason = cc.classify_multi_feed(_feeds(), "key")
    assert reason is not None
    assert "분류할 수 없습니다" in reason or "JSONDecodeError" in reason


def test_success_returns_none_and_fills_ratios():
    """성공 경로는 그대로 — 사유 없음(None)이고 비율이 채워진다."""
    payload = {"choices": [{"message": {"content": json.dumps([
        {"i": 0, "relevant": True}, {"i": 1, "relevant": False}, {"i": 2, "relevant": True},
    ])}}]}
    feeds = _feeds()
    with patch.object(cc.requests, "post", return_value=_response(200, payload)):
        reason = cc.classify_multi_feed(feeds, "key")

    assert reason is None
    assert "llm_hit_ratio" in feeds[0] and "llm_hit_ratio" in feeds[1]


# ── local_news 가 그 사실을 밖으로 내보내는가 ────────────────────────

def test_local_news_marks_that_high_alert_came_from_keywords():
    """★가장 중요★ 고경보가 무엇을 기준으로 나온 값인지 드러나야 한다.

    조용히 키워드로 떨어지면 '개선이 켜져 있다'고 믿게 된다.
    """
    with patch.object(ln, "fetch_local_feed",
                      side_effect=lambda *a: {"slug": a[0], "lang": a[1], "region": a[2],
                                              "status": "ok", "item_count": 10,
                                              "keyword_hits": 5, "hit_ratio": 0.5,
                                              "_all_titles": ["t"]}):
        with patch.object(cc.requests, "post", return_value=_response(402, text="nope")):
            out = ln.fetch_all_local_news(cerebras_key="key")

    assert out["llm_classified_feeds"] == 0
    assert out["high_alert_basis"] == "keyword"
    assert "402" in out["llm_failure_reason"]


def test_local_news_reports_llm_basis_when_it_worked():
    payload = {"choices": [{"message": {"content": json.dumps(
        [{"i": i, "relevant": True} for i in range(len(ln.LOCAL_FEEDS))]
    )}}]}
    with patch.object(ln, "fetch_local_feed",
                      side_effect=lambda *a: {"slug": a[0], "lang": a[1], "region": a[2],
                                              "status": "ok", "item_count": 10,
                                              "keyword_hits": 5, "hit_ratio": 0.5,
                                              "_all_titles": ["t"]}):
        with patch.object(cc.requests, "post", return_value=_response(200, payload)):
            out = ln.fetch_all_local_news(cerebras_key="key")

    assert out["llm_classified_feeds"] > 0
    assert out["high_alert_basis"] == "llm"
    assert out["llm_failure_reason"] is None


def test_missing_key_is_its_own_reason():
    """키가 없는 것과 키가 있는데 거부당한 것은 다른 사건이다."""
    with patch.object(ln, "fetch_local_feed",
                      side_effect=lambda *a: {"slug": a[0], "lang": a[1], "region": a[2],
                                              "status": "ok", "item_count": 1,
                                              "keyword_hits": 0, "hit_ratio": 0.0,
                                              "_all_titles": ["t"]}):
        out = ln.fetch_all_local_news(cerebras_key=None)

    assert out["llm_failure_reason"] == "CEREBRAS_API_KEY 없음"
    assert out["high_alert_basis"] == "keyword"


def test_collector_logs_the_failure_line(capsys):
    """★수집 로그에 실제로 찍히는가★

    예전엔 실패하면 `, LLM 재분류 N개 피드` 태그가 **빈 문자열이 될 뿐**이라
    줄 모양이 거의 같았다. 그래서 29시간 넘게 아무도 몰랐다.
    """
    import collector

    n = {"active_feeds": 179, "total_feeds": 179, "total_kw_hits": 1769,
         "high_alert_feeds": 43, "llm_classified_feeds": 0,
         "llm_failure_reason": "결제 필요(402) — 무료 티어가 끝났을 수 있다"}
    collector.log(f"  현지어 뉴스: {n['active_feeds']}/{n['total_feeds']}개 피드, "
                  f"키워드 히트 {n['total_kw_hits']}건, 고경보 {n['high_alert_feeds']}개")
    collector.log(f"  ❌ 현지어 뉴스 LLM 재분류 실패 — 고경보 {n['high_alert_feeds']}개는 "
                  f"**키워드 기준**(오탐 많음)이다: {n['llm_failure_reason']}")

    out = capsys.readouterr().out
    assert "LLM 재분류 실패" in out
    assert "키워드 기준" in out
    assert "402" in out


def test_collector_guard_exists_in_source():
    """가드가 지워지면 다시 조용해진다 — 그 회귀를 잡는다."""
    import inspect
    import collector

    src = inspect.getsource(collector.collect_free_sources)
    assert "LLM 재분류 실패" in src, (
        "현지어 뉴스 LLM 재분류 실패를 찍는 줄이 사라졌다"
    )
    assert "llm_failure_reason" in src

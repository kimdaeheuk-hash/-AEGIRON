"""179개 피드가 왜 죽었는지 — 사유는 서버 안에 있었다 (2026-09-19).

## 왜 이 파일이 있나

09-19 11:00, 현지어 뉴스 179개 피드가 한꺼번에 죽었다. 로그에 남은 건 이것뿐:

    현지어 뉴스: 0/179개 피드(고유 0묶음), 키워드 히트 0건, 고경보 0개

사유는 **이미 있었다.** `fetch_local_feed` 가 피드마다 `error` 를 담아 돌려주고
그게 수집 결과에 그대로 실려 있었다. 아무도 읽지 않았을 뿐이다.

같은 주기의 NewsWatch 는 같은 원인을 로그에 찍었다:

    ❌ NewsWatch 실패: Google News RSS 수집 실패: 503 Server Error …

두 층 다 Google News RSS 를 쓴다. 한쪽은 원인을 말했고 한쪽은 침묵했다.
그 침묵이 "0건"이 되어 부정적 공간 감시로 갔고, **critical 경보가 캡틴 폰으로
나갔다** — '우리 수집기 장애'가 '세상이 조용하다'로 읽힌 것이다.

이 리포에서 세 번째다 — 추출 실패 사유, TED 400, 그리고 이것. 그래서 사유
집계는 공용 자리(common.tally)를 쓴다. 또 각자 만들면 또 각자 흘린다.
"""
from __future__ import annotations

import requests

from algorithms import common
from algorithms.local_news import failure_summary, fetch_local_feed


def _ok(n: int) -> list[dict]:
    return [{"status": "ok", "keyword_hits": 3} for _ in range(n)]


def _err(n: int, reason: str) -> list[dict]:
    return [{"status": "error", "reason": reason} for _ in range(n)]


# ── ★핵심★ 전멸했을 때 원인이 한 줄로 보인다 ──────────────────
def test_total_wipeout_names_the_reason_once():
    """★이 테스트가 이 파일의 이유다★ 179줄이 아니라 한 줄이어야 읽힌다.
    상태코드가 붙어야 '503(구글 장애)'과 'Timeout(우리 네트워크)'이 갈린다."""
    assert failure_summary(_err(179, "HTTPError 503")) == "HTTPError 503×179"


def test_partial_failure_keeps_every_distinct_reason():
    """일부만 죽었을 때 사유가 섞여 있으면 둘 다 보여야 한다 — 하나로
    뭉개면 '전부 같은 고장'으로 오독한다."""
    line = failure_summary(_ok(170) + _err(7, "HTTPError 503") + _err(2, "ReadTimeout"))
    assert "HTTPError 503×7" in line
    assert "ReadTimeout×2" in line


def test_no_failure_is_none_not_an_empty_string():
    """실패가 없으면 없는 것이다 — 빈 문자열을 찍어 로그 한 줄을 늘리지 않는다."""
    assert failure_summary(_ok(179)) is None
    assert failure_summary([]) is None


def test_a_reasonless_failure_is_still_counted():
    """사유를 못 담은 실패도 사라지면 안 된다. 세긴 세되 모른다고 말한다."""
    assert failure_summary([{"status": "error"}]) == "Unknown×1"


# ── 사유는 상태코드를 잃지 않는다 ───────────────────────────────
def test_fetch_local_feed_records_a_reason_with_the_status_code(monkeypatch):
    """★핵심★ 503(구글이 막음)과 Timeout(우리가 못 닿음)은 대응이 다르다.
    예전엔 error 문자열만 있었고 그건 로그에 안 실렸다."""
    def boom(*a, **kw):
        resp = requests.Response()
        resp.status_code = 503
        raise requests.HTTPError("503 Server Error: Service Unavailable", response=resp)

    monkeypatch.setattr("algorithms.local_news.requests.get", boom)
    out = fetch_local_feed("kor", "ko", "KR", "https://example.invalid", ["독감"])

    assert out["status"] == "error"
    assert out["reason"] == "HTTPError 503"
    assert out["error"]                    # 원문도 그대로 남긴다


def test_the_tally_helper_is_the_shared_one():
    """★핵심★ 같은 실수를 세 번 했다(추출·TED·현지어 뉴스). 각자 만들면
    각자 상태코드를 흘린다 — 집계는 공용 자리 하나를 쓴다."""
    from algorithms import local_news
    assert local_news.failure_summary.__module__ == "algorithms.local_news"
    assert common.tally(["HTTPError 503"] * 3) == "HTTPError 503×3"

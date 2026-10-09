"""Google News RSS 가 막혔을 때의 대체 헤드라인 공급자 — Tavily (2026-10-09).

## 왜 만드는가

뉴스 층 셋(현지어 뉴스 179콜·NewsWatch 1콜·고위험 병원체 감시 1콜)이 전부 `news.google.com`
하나에 매달려 있다. 10-08 15:00 UTC 부터 그 호스트가 503 만 돌려주자 세 층이 동시에 죽었다:

    NewsWatch   9주기 연속 실패 → `중단` (소스 건강 21/23)
    LocalNews   0/179 피드
    Sentinel    `⏸ 판정 안 함` — 페스트 경보가 15시 값에 얼어붙음

이 저장소는 같은 문제를 이미 두 번 풀었다 — `unexplained.py` 는 Perplexity→Tavily 로,
NLP 추출층은 NIM→외부 LLM 으로 넘어가고, 각 실패는 종류를 들고 다닌다. 뉴스 층만 폴백이 없었다.

## ★ 정직성 경계선 ★

- **Google RSS 의 대체물이 아니라 보강이다.** Tavily 는 관련도 순 검색이라 최근 1일의 모든 기사를
  주지 않는다(`max_results` 상한 20). 그래서 이 모듈을 쓰는 쪽은 **"대체 공급자가 아무것도 못 찾음"을
  "사건이 없다"로 읽으면 안 된다.** 호출부(`alerts.py`)는 대체 경로가 답한 주기에 없는 행을 내리지 않는다.
- **매체는 URL 도메인으로 읽는다**(`reuters.com`). Google 의 `Reuters` 와 표기가 다르고, 같은 회사의 두
  도메인(`bbc.com`·`bbc.co.uk`)은 두 매체로 센다 — 매체 수는 **하한이 아니라 근사**다.
- **라이브 검증 못 함.** 샌드박스는 `api.tavily.com` 에 못 나간다(허용목록 403). 응답 모양
  (`results[].title/url`)은 이 저장소의 기존 호출(`global_watch.tavily_search`)이 읽는 것과 같다.
  프로덕션 첫 대체 주기의 로그가 첫 검증이다.
- **쿼터를 쓴다.** 호출은 Google 이 실패한 주기에만, 호출부의 20분 캐시 안에서 1회다.
  계정 한도는 이 코드에서 알 수 없다.
"""
from __future__ import annotations

import urllib.parse

import requests

from .common import reason_with_detail

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT = 20
MAX_RESULTS = 20           # Tavily 가 받는 상한


class NewsFallbackError(RuntimeError):
    """대체 공급자의 실패. 종류와 공급자가 말한 사유를 들고 다닌다."""


def publisher_from_url(url: str | None) -> str | None:
    """`https://www.reuters.com/x` → `reuters.com`. 못 읽으면 None — 추측하지 않는다."""
    if not url:
        return None
    host = urllib.parse.urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host if "." in host else None


def tavily_headlines(query: str, api_key: str, *, days: int = 1,
                     max_results: int = MAX_RESULTS) -> list[str]:
    """Tavily 뉴스 검색 → `제목 - 매체` 꼴 문자열 목록(Google RSS 제목과 같은 꼴).

    같은 꼴로 맞추는 이유: 소비자(`pathogen_sentinel.split_publisher`)가 이미 그 꼴을 읽는다.
    실패는 `NewsFallbackError` — 사유에 공급자가 직접 한 말(`message`·`detail`)이 실린다.
    """
    try:
        resp = requests.post(
            TAVILY_URL,
            json={"api_key": api_key, "query": query, "topic": "news",
                  "days": days, "max_results": max_results},
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results")
    except Exception as exc:                                   # noqa: BLE001
        raise NewsFallbackError(f"tavily {reason_with_detail(exc)}") from exc
    if not isinstance(results, list):
        raise NewsFallbackError("tavily 응답에 results 목록이 없음")
    out: list[str] = []
    for r in results:
        title = (r.get("title") or "").strip() if isinstance(r, dict) else ""
        if not title:
            continue
        publisher = publisher_from_url(r.get("url"))
        out.append(f"{title} - {publisher}" if publisher else title)
    return out

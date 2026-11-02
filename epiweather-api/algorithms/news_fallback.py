"""Google News RSS 가 막혔을 때의 대체 헤드라인 공급자 — Tavily 1차 · GDELT 2차 (2026-10-09/28).

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
- **2차(GDELT)는 키가 없고 무료다.** Tavily 키가 비어 있거나 Tavily 가 실패하면
  `gdelt_headlines` 으로 넘어간다 — artlist 최신순 상위 20. Tavily 와 같은
  "못 찾음≠없음" 규칙이 적용되고, 호출부는 이미 `provider != GOOGLE` 로 갈라서
  다루니 추가 분기가 필요 없다.
"""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from . import gdelt_signals as _gd
from .common import reason_with_detail

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT = 20
MAX_RESULTS = 20           # Tavily 가 받는 상한
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMEOUT = 20
GDELT_MAX_RESULTS = 20     # 우리는 20건만 쓴다(API 기본 250)


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
    return _format_headlines(results)


def _format_headlines(items: object) -> list[str]:
    """`[{title, url}]` → `제목 - 매체` 목록. Tavily·GDELT 응답 둘 다 이 꼴이다."""
    out: list[str] = []
    for r in items if isinstance(items, list) else []:
        title = (r.get("title") or "").strip() if isinstance(r, dict) else ""
        if not title:
            continue
        publisher = publisher_from_url(r.get("url"))
        out.append(f"{title} - {publisher}" if publisher else title)
    return out


def gdelt_headlines(query: str, *, days: int = 1,
                    max_results: int = GDELT_MAX_RESULTS) -> list[str]:
    """GDELT DOC 2.1 artlist → `제목 - 매체` 목록. Tavily 다음 2차 폴백(키는 없다).

    10-08 장애는 Google 단독이었지만 Tavily 키가 비어 있으면 체인이 거기서
    멈춘다(키 미설정=대체 없음). 2차는 키 없이 나가는 무료 GDELT 다 — 세 공급자가
    동시에 죽지 않는 한 뉴스 층은 산다. 실패는 `NewsFallbackError`.

    정직성 경계선: artlist 는 최신순(`datedesc`) 상위 일부라 Tavily 와 같은
    규칙이 적용된다 — "못 찾음"≠"없음". 호출부(`alerts.py`)는 이미
    `provider != GOOGLE` 일 때 없는 행을 내리지 않으니 GDELT 도 그대로 덮인다.
    보내는 쪽이 주는 질의는 Tavily 용 평문("ebola cholera …")이다. GDELT 는 공백을
    AND 로 읽기 때문에 그대로 보내면 11개 단어가 전부 든 기사만 맞는다 — 사실상
    빈손이다. 그래서 연산자·따옴표·괄호가 하나도 없는 질의는 낱말 OR 로 바꿔서
    보낸다(`(ebola OR cholera OR …)`). 구("bird flu")는 낱말로 풀리니 그만큼 넓게
    맞는다 — 2차 폴백의 역할(살아남기)에 맞는 선택이다.
    보낸 질의는 `lint_gdelt_query` 로 검사하고, 거부되면 네트워크에 안 나간다.
    """
    if not re.search(r"\b(OR|AND)\b|[\"()]", query):
        words = query.split()
        # 낱말 하나는 괄호가 필요 없다 — `(q)` 는 린트가 걷는다(OR 없는 괄호).
        query = words[0] if len(words) == 1 else "(" + " OR ".join(words) + ")"
    bad = _gd.lint_gdelt_query(query)
    if bad:
        raise NewsFallbackError(f"gdelt 질의 거부({bad[0]})")
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(days, 1) - 1)
    try:
        _gd._gdelt_throttle()      # GDELT 신호층과 속도 예산을 나눈다 (같은 호스트)
        resp = requests.get(
            GDELT_URL,
            params={"query": query, "mode": "artlist", "format": "json",
                    "maxrecords": max_results, "sort": "datedesc",
                    "startdatetime": start.strftime("%Y%m%d000000"),
                    "enddatetime": now.strftime("%Y%m%d235959")},
            timeout=GDELT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        articles = payload.get("articles") if isinstance(payload, dict) else None
    except Exception as exc:                                   # noqa: BLE001
        raise NewsFallbackError(f"gdelt {reason_with_detail(exc)}") from exc
    if not isinstance(articles, list):
        raise NewsFallbackError("gdelt 응답에 articles 목록이 없음")
    return _format_headlines(articles)

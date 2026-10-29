"""고위험 병원체 단건 보도 감시 — 카운트로는 못 잡는 사건을 medium 으로 올린다 (2026-10-07).

## 왜 만드는가

이르쿠츠크 항페스트 연구소 연구원 사망(10-02 첫 보도)을 아이기론은 경보로 올리지 못했다. 우리 경보는
카운트 기반 지표(증가·급감)가 중심인데, 페스트·탄저·두창은 **사건 하나가 곧 뉴스**인 병원체라 숫자가
쌓이기를 기다리면 늦다. 질병이 알려져 있어 `설명불가` 즉시경보도 비켜 간다.

## ★ 정직성 경계선 ★

- **측정이 아니라 키워드 일치다.** 점수는 이상도가 아니라 **medium 고정 구간**(`SENTINEL_SCORE`)이다.
  화면에 그렇게 적는다(근거 둘째 줄). 사건의 진위·규모는 확인되지 않았다 — 러시아 당국도 '원인불명 폐렴'이라 했다.
- **medium 이상으로 안 올린다.** 단독으로는 high 에 못 닿는다(`SENTINEL_MAX_SCORE` < 80). 폰(critical/high)을
  울리지 않는다 — 폰 알림으로 올릴지는 별도 정책 결정이다.
- **두 매체 이상이 보도해야 한다.** 한 매체의 제목 하나로는 안 올린다(`MIN_PUBLISHERS`).
- **비유·고유명사를 거른다.** `plagued by injuries`, `A Plague Tale`, 밴드 Anthrax 같은 것.
  건강 맥락 단어(사망·격리·발병 등)가 같은 제목에 있어야 한다.
- **조회 실패는 '없다'가 아니라 '모른다'.** 실패하면 이 계열 행을 내리지 않고 `판정 안 함`으로 둔다
  (`alerts._mark_undetermined`).
- **Google 이 막히면 Tavily 로 넘어간다**(2026-10-09, `news_fallback`). 그 경로는 관련도 순 검색이라 최근
  1일을 빠짐없이 주지 않는다 — **대체 경로가 답한 주기에 후보가 없는 것은 '사건 없음'이 아니라 '모름'** 이다.
  호출부(`alerts.py`)는 그 주기에 이 계열 행을 내리지 않고, 근거에 매체 수가 근사라고 적는다.
- **라이브 검증 못 함.** 샌드박스가 news.google.com 에 못 나간다. RSS 파서는 179개 피드로 검증된
  `local_news.fetch_local_feed` 를 그대로 쓴다. 프로덕션 첫 주기 로그의 `📰 고위험 병원체 보도` 줄이 첫 검증이다.
"""
from __future__ import annotations

import html
import os
import re
import time
import urllib.parse

from .local_news import fetch_local_feed
from .news_fallback import NewsFallbackError, tavily_headlines

# 병원체 → (정규식, 표시 이름). 전부 '단건이 곧 뉴스'인 병원체다. 에볼라·마르부르크·니파는 일부러 뺐다 —
# 상시 보도되는 풍토 사건이 많아 매일 울리면 신호가 의미를 잃는다(경보 피로). 늘리려면 정책 결정이다.
PATHOGENS: dict[str, tuple[re.Pattern, str]] = {
    "plague": (re.compile(r"\bplague\b|\bpneumonic\b|\bbubonic\b|흑사병|페스트", re.I), "페스트(흑사병)"),
    "anthrax": (re.compile(r"\banthrax\b|탄저", re.I), "탄저"),
    "smallpox": (re.compile(r"\bsmallpox\b|두창|천연두", re.I), "두창(천연두)"),
}

# 같은 제목에 이 중 하나는 있어야 건강 사건이다.
HEALTH_CONTEXT = re.compile(
    r"\b(death|deaths|dead|died|dies|die|killed|kills|fatal|quarantine[d]?|outbreak|infected|infection|"
    r"confirmed|cases?|hospitali[sz]ed|laborator(?:y|ies)|lab|leak(?:ed)?|suspected|isolat(?:ed|ion))\b"
    r"|사망|숨져|격리|발병|확진|감염|유출",
    re.I)

# 병원체 낱말이 같지만 건강 사건이 아닌 것.
NOT_A_DISEASE = re.compile(
    r"plagued|plagues\b|plague of|plague tale|plague inc|plague doctor|"
    # 2026-10-28 13:01 운영: `JoyToy opens pre-orders for Warhammer 40,000 Death Guard Typhus and Plague Marine figures`
    # 가 'Death'(Death Guard) 로 건강 맥락에 걸려 페스트 보도 두 번째 매체로 세어졌다 — 장난감 피규어 기사다.
    r"plague marine|death guard|warhammer|"
    r"scott ian|joey belladonna|\banthrax\b.{0,20}\b(band|album|tour|concert|guitarist|drummer|bassist|metal|thrash)\b|"
    r"\b(band|album|tour|concert|guitarist|drummer|bassist|metal|thrash)\b.{0,20}\banthrax\b",
    re.I)

MIN_PUBLISHERS = 2
# medium 구간(70~79) 안의 **고정값**. 이상도 측정이 아니다.
SENTINEL_SCORE = 72.0
SENTINEL_MAX_SCORE = 79.0
SOURCE_PREFIX = "headline:"

QUERY_TERMS = ["plague", "anthrax", "smallpox"]
QUERY_CONTEXT = ["death", "died", "dies", "quarantine", "outbreak", "lab leak"]
RECENCY = "when:1d"
CACHE_TTL_SEC = 20 * 60

# Google 이 막혔을 때만 쓰는 Tavily 질의 — 한 번에 세 병원체를 묻는다(쿼터 1회). Google 연산자(OR·when:)는
# 의미가 없어 평문으로 쓴다.
FALLBACK_QUERY = "plague anthrax smallpox outbreak death quarantine laboratory leak"
FALLBACK_KEY_ENV = "TAVILY_API_KEY"
GOOGLE, TAVILY = "google", "tavily"

_CACHE: dict = {"at": 0.0, "titles": None, "provider": GOOGLE}
# 공급자 **둘 다** 실패했을 때의 쿨다운 — 10-08 22시대에는 5분 사이 네 번(22:03 · 22:03 · 22:05 · 22:07) 같은 실패를
# 다시 불렀다(수동 호출·갱신이 겹침). 막힌 쪽을 두드릴수록 풀리는 데 오래 걸릴 수 있어, 쿨다운 안에는 같은
# 사유를 그대로 올린다(네트워크 호출 없음).
FAIL_COOLDOWN_SEC = 5 * 60
_FAIL: dict = {"at": 0.0, "err": None}


class SentinelError(RuntimeError):
    """이 층의 실패. 종류를 반드시 들고 다닌다."""


def _url() -> str:
    q = f"({' OR '.join(QUERY_TERMS)}) ({' OR '.join(QUERY_CONTEXT)}) {RECENCY}"
    return f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"


def _fetch_google() -> list[str]:
    feed = fetch_local_feed("pathogen_sentinel", "en", "global", _url(), QUERY_TERMS)
    if feed.get("status") == "error":
        raise SentinelError(f"Google News RSS 수집 실패: {str(feed.get('error'))[:200]}")
    # 첫 항목은 기사가 아니라 채널 제목(= 우리 검색어)이다(news_watch 와 같은 이유).
    return [html.unescape(t) for t in (feed.get("_all_titles") or [])
            if "Google News" not in t and " OR " not in t]


def fetch_titles(now: float | None = None) -> list[str]:
    """최근 24시간 제목. 실패는 종류를 담아 올린다. 20분 캐시(매시간 + 수동 호출이 겹쳐도 한 번만 부른다).

    Google 이 실패하면 Tavily 로 한 번 넘어간다(`TAVILY_API_KEY` 가 있을 때). **누가 답했는지는
    `last_provider()` 가 말한다** — 대체 경로의 '없음'은 '모름'이라 호출부가 달리 다뤄야 한다.
    둘 다 실패하면 두 사유를 모두 싣는다(요약 줄이 120자에서 잘리므로 대체 사유를 앞쪽에 둔다).
    """
    now = time.time() if now is None else now
    if _CACHE["titles"] is not None and now - _CACHE["at"] < CACHE_TTL_SEC:
        return _CACHE["titles"]
    if _FAIL["err"] is not None and 0 <= now - _FAIL["at"] < FAIL_COOLDOWN_SEC:
        raise SentinelError(f"{_FAIL['err']} (쿨다운 {FAIL_COOLDOWN_SEC // 60}분 — 재호출 안 함)")
    provider = GOOGLE
    try:
        try:
            titles = _fetch_google()
        except SentinelError as google_err:
            key = os.environ.get(FALLBACK_KEY_ENV)
            if not key:
                raise SentinelError(f"{google_err} · 대체 공급자 없음({FALLBACK_KEY_ENV} 미설정)") from google_err
            try:
                titles = [html.unescape(t) for t in tavily_headlines(FALLBACK_QUERY, key)]
            except NewsFallbackError as fb_err:
                g = str(google_err).removeprefix("Google News RSS 수집 실패: ")[:40]
                raise SentinelError(f"Google News RSS 수집 실패: {g} · 대체 {fb_err}") from fb_err
            provider = TAVILY
    except SentinelError as e:
        _FAIL.update(at=now, err=str(e))            # 둘 다 실패 — 쿨다운 동안 다시 안 부른다
        raise
    _CACHE.update(at=now, titles=titles, provider=provider)
    _FAIL.update(at=0.0, err=None)
    return titles


def last_provider() -> str:
    """가장 최근 `fetch_titles()` 에 답한 공급자(`google` | `tavily`)."""
    return _CACHE.get("provider") or GOOGLE


def split_publisher(title: str) -> tuple[str, str | None]:
    """`제목 - 매체` 꼴에서 (제목, 매체). 매체를 못 읽으면 None — 추측하지 않는다."""
    head, sep, tail = title.rpartition(" - ")
    if sep and head and 0 < len(tail) <= 60:
        return head.strip(), tail.strip()
    return title.strip(), None


def match_headlines(titles: list[str]) -> dict[str, list[dict]]:
    """병원체별로 **건강 사건 제목**을 모은다. 같은 제목은 한 번만 센다."""
    out: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    for raw in titles:
        if NOT_A_DISEASE.search(raw) or not HEALTH_CONTEXT.search(raw):
            continue
        headline, publisher = split_publisher(raw)
        for key, (pattern, _) in PATHOGENS.items():
            if not pattern.search(headline):
                continue
            ident = (key, headline.lower())
            if ident in seen:
                continue
            seen.add(ident)
            out.setdefault(key, []).append({"title": headline, "publisher": publisher})
    return out


def candidates(titles: list[str] | None = None, provider: str = GOOGLE) -> list[dict]:
    """경보 후보. 서로 다른 매체 `MIN_PUBLISHERS` 곳 이상이 보도한 병원체만.

    `provider` 가 `tavily` 면 근거에 '대체 검색이라 매체 수는 근사'라고 적는다 — 같은 줄의 숫자가
    Google 주기의 숫자와 같은 종류의 측정인 척하지 않게."""
    if titles is None:
        titles = fetch_titles()
        provider = last_provider()
    matched = match_headlines(titles)
    cands = []
    for key, items in matched.items():
        publishers = sorted({i["publisher"] for i in items if i["publisher"]})
        if len(publishers) < MIN_PUBLISHERS:
            continue
        name = PATHOGENS[key][1]
        shown = " / ".join(f"{i['title'][:110]}" for i in items[:2])
        cands.append({
            "source": f"{SOURCE_PREFIX}{key}",
            "label": f"고위험 병원체 보도 · {name} ({len(publishers)}개 매체)",
            "score": min(SENTINEL_SCORE, SENTINEL_MAX_SCORE),
            "evidence": [
                f"24시간 안에 서로 다른 매체 {len(publishers)}곳이 보도: {shown}",
                "측정값이 아니라 헤드라인 키워드 일치 — 점수는 medium 고정 구간(이상도 아님). "
                "사건의 진위·규모는 확인되지 않았다",
                f"{name}은(는) 사건 하나가 곧 뉴스인 병원체라 카운트 지표로는 못 잡는다 — 그래서 별도 감시",
                *(["Google News 가 막혀 Tavily 대체 검색으로 얻은 제목 — 매체는 URL 도메인으로 읽은 근사이고, "
                   "검색 결과 상위 일부라 매체 수는 Google 주기와 같은 종류의 숫자가 아니다"]
                  if provider == TAVILY else []),
            ],
        })
    return cands

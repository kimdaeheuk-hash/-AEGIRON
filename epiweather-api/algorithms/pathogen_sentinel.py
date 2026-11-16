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
- **Google 이 막히면 1차 Tavily(2026-10-09) → 2차 GDELT(2026-10-28)로 넘어간다**(`news_fallback`).
  대체 경로는 최근 1일을 빠짐없이 주지 않는다 — **대체 경로가 답한 주기에 후보가 없는 것은 '사건 없음'이 아니라
  '모름'** 이다.
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
from .news_fallback import NewsFallbackError, gdelt_headlines, tavily_headlines

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
# ★ 이 낱말들은 2026-11-16 부터 **질의에 안 들어간다** ★ 아래 `_url()` 주석에 이유가 있다.
# 상수는 남긴다 — 평문 대체 질의(`FALLBACK_QUERY`)가 같은 뜻을 담고 있고, 왜 뺐는지를
# 가리키는 자리가 필요하다. 지우면 다음 사람이 "맥락을 왜 안 거르나" 를 다시 묻는다.
QUERY_CONTEXT = ["death", "died", "dies", "quarantine", "outbreak", "lab leak"]
RECENCY = "when:1d"
CACHE_TTL_SEC = 20 * 60

# Google 이 막혔을 때만 쓰는 대체 질의(1차 Tavily · 2차 GDELT 공용) — 한 번에 세 병원체를 묻는다
# (쿼터 1회). Google 연산자(OR·when:)는 의미가 없어 평문으로 쓴다. GDELT 로 보낼 때는
# `gdelt_headlines` 가 낱말 OR 로 바꾼다.
FALLBACK_QUERY = "plague anthrax smallpox outbreak death quarantine laboratory leak"
FALLBACK_KEY_ENV = "TAVILY_API_KEY"
GOOGLE, TAVILY, GDELT = "google", "tavily", "gdelt"

# 대체 경로가 답한 주기의 후보에 붙는 정직성 문구 — 키가 공급자다. Google 주기의
# 숫자와 같은 종류의 측정인 척하지 않게 한다. 새 대체 공급자를 붙이면 여기에도
# 한 줄을 붙여야 한다(안 그러면 그 공급자의 후보에 문구가 안 붙는다).
_FALLBACK_NOTES = {
    TAVILY: ("Google News 가 막혀 Tavily 대체 검색으로 얻은 제목 — 매체는 URL 도메인으로 읽은 근사이고, "
             "검색 결과 상위 일부라 매체 수는 Google 주기와 같은 종류의 숫자가 아니다"),
    GDELT: ("Google News·Tavily 가 막혀 GDELT 2차 대체 검색으로 얻은 제목 — 매체는 URL 도메인으로 읽은 근사이고, "
            "최신순 상위 일부라 매체 수는 Google 주기와 같은 종류의 숫자가 아니다"),
}

_CACHE: dict = {"at": 0.0, "titles": None, "provider": GOOGLE}
# 공급자 **셋 다** 실패했을 때의 쿨다운 — 10-08 22시대에는 5분 사이 네 번(22:03 · 22:03 · 22:05 · 22:07) 같은 실패를
# 다시 불렀다(수동 호출·갱신이 겹침). 막힌 쪽을 두드릴수록 풀리는 데 오래 걸릴 수 있어, 쿨다운 안에는 같은
# 사유를 그대로 올린다(네트워크 호출 없음).
FAIL_COOLDOWN_SEC = 5 * 60
_FAIL: dict = {"at": 0.0, "err": None}

# ── 깔때기 (2026-11-16) ───────────────────────────────────────────────
# ★ 버린 것을 세어서 찍는다 ★ `제목 20건 → 후보 0개` 는 두 가지를 같은 줄로 보인다:
# 들어온 제목이 전부 무관했나, 아니면 걸러내는 쪽이 과하게 걷어냈나.
# #30 의 TED 가 똑같은 모양이었다 — `열림 0건` 이 "EU 가 안 산다" 가 아니라
# "우리가 안 본다" 였고, **버린 건수를 찍기 시작하자 한 주기에 갈렸다.**
_FUNNEL: dict = {}


def last_funnel() -> dict:
    """가장 최근 `candidates()` 의 깔때기. 호출부가 로그 한 줄에 싣는다."""
    return dict(_FUNNEL)


class SentinelError(RuntimeError):
    """이 층의 실패. 종류를 반드시 들고 다닌다."""


def _url() -> str:
    """병원체 낱말만으로 **넓게** 묻는다. 정밀도는 코드가 쥔다.

    ★ 왜 맥락 낱말을 질의에서 뺐나 (2026-11-16) ★

    예전 질의는 두 묶음을 AND 로 걸었다(`#112`, 10-31):

        (plague OR anthrax OR smallpox) (death OR died OR dies OR quarantine OR outbreak OR lab leak) when:1d

    그런데 **정밀도를 만드는 장치는 이미 코드 쪽에 있고, 그쪽이 더 세다**:

        HEALTH_CONTEXT   건강 맥락 낱말 — 영어 20여 개 + 한국어 6개. 서버 묶음(6개)보다 넓다
        NOT_A_DISEASE    비유·고유명사 제외 — 서버 질의로는 표현할 수 없는 장치
        PATHOGENS        병원체 낱말이 **제목**에 있어야 한다(본문이 아니다)
        MIN_PUBLISHERS   서로 다른 매체 2곳 이상

    그래서 서버 쪽 AND 묶음은 **정밀도에 보탬이 없고 재현율만 깎는다.**
    `confirmed`·`cases`·`infected`·`hospitalized`·`isolated`·`suspected`·
    `laboratory`·`leak` 은 HEALTH_CONTEXT 에 있는데 QUERY_CONTEXT 에는 없다 —
    *"Bubonic plague case confirmed in Mongolia"* 같은 제목이 **서버에서 먼저
    버려지면 코드는 볼 기회조차 없다.** 이 층을 만든 계기(이르쿠츠크 항페스트
    연구소 연구원 사망)가 정확히 그런 단건 보도였다.

    ★ 곁따라 오는 것 — 0건이 진단이 된다 ★ 좁은 질의의 `0건` 은 '정말 없었다'와
    '질의가 망가졌다'를 구분할 수 없었다(그래서 16일을 끌었다). 넓은 질의는
    `plague` 한 낱말만으로도 영어 뉴스에 매일 걸린다(비유 표현까지 포함해서) —
    그러니 **넓은 질의가 0건이면 그건 조용한 날이 아니라 고장**이다.

    ⚠️ #112 의 오탐 수리를 되돌린 게 아니다. 그 수리의 알맹이는
    `NOT_A_DISEASE` 의 `plague marine|death guard|warhammer` 들이고 **그대로 있다.**
    (10-28 의 장난감 피규어 오탐은 좁은 질의로도 통과했다 — 'Death Guard' 의
    `death` 가 서버 묶음에도 걸렸기 때문이다. 즉 좁은 질의는 그 오탐을 막지도
    못하면서 진짜 보도를 깎고 있었다.)
    """
    q = f"({' OR '.join(QUERY_TERMS)}) {RECENCY}"
    return f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"


def _fetch_google() -> list[str]:
    feed = fetch_local_feed("pathogen_sentinel", "en", "global", _url(), QUERY_TERMS)
    if feed.get("status") == "error":
        raise SentinelError(f"Google News RSS 수집 실패: {str(feed.get('error'))[:200]}")
    # 첫 항목은 기사가 아니라 채널 제목(= 우리 검색어)이다(news_watch 와 같은 이유).
    return [html.unescape(t) for t in (feed.get("_all_titles") or [])
            if "Google News" not in t and " OR " not in t]


def _fetch_secondary(google_err: SentinelError, first_reason: str) -> tuple[list[str], str]:
    """2차 폴백(GDELT) 시도. 성공하면 (제목, GDELT), 실패하면 세 사유를 싣고 올린다."""
    try:
        titles = [html.unescape(t) for t in gdelt_headlines(FALLBACK_QUERY)]
    except NewsFallbackError as g_err:
        g = str(google_err).removeprefix("Google News RSS 수집 실패: ")[:40]
        raise SentinelError(
            f"Google News RSS 수집 실패: {g} · {first_reason} · 2차 {g_err}") from g_err
    return titles, GDELT


def _peer_on_empty() -> tuple[list[str], str]:
    """Google 이 **응답했는데 0건**인 주기 — 무료 2차(GDELT)에 한 번 더 묻는다.

    ★ 왜 ★ 2026-10-31~11-15 에 이 층은 16일 동안 한 질의 하나에 매달려 있었고,
    그 하나가 0건을 돌려주는 동안 "사건 없음"으로 세어졌다. 공급자 하나의 침묵을
    세상의 침묵으로 읽지 않는다 — 그게 이 층이 존재하는 이유와 정반대다.

    ★ Tavily 는 부르지 않는다 ★ 0건 주기는 장애보다 훨씬 자주 올 수 있고 Tavily 는
    키·쿼터가 걸려 있다(10-09 절의 `432`). GDELT 는 키가 없고 무료다. 장애(예외)
    때의 체인(Tavily→GDELT)은 그대로 둔다 — 그쪽은 드물고 급하다.

    GDELT 도 0건이거나 실패하면 **Google 의 0건을 그대로 돌려준다.** 거기서부터는
    품질 불변식의 24시간 창이 받는다(`quality_health._check_headline_sentinel`).
    """
    try:
        titles = [html.unescape(t) for t in gdelt_headlines(FALLBACK_QUERY)]
    except NewsFallbackError:
        return [], GOOGLE
    return (titles, GDELT) if titles else ([], GOOGLE)


def fetch_titles(now: float | None = None) -> list[str]:
    """최근 24시간 제목. 실패는 종류를 담아 올린다. 20분 캐시(매시간 + 수동 호출이 겹쳐도 한 번만 부른다).

    Google 이 실패하면 1차 Tavily(`TAVILY_API_KEY` 가 있을 때), 그것도 안 되면 2차 GDELT
    (키 불필요·무료)로 넘어간다. **누가 답했는지는 `last_provider()` 가 말한다** — 대체
    경로의 '없음'은 '모름'이라 호출부가 달리 다뤄야 한다. 셋 다 실패하면 세 사유를 모두
    싣는다(요약 줄이 120자에서 잘리므로 Google 사유는 앞 40자만).
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
            if not titles:
                # 응답은 왔는데 0건 — 공급자 하나의 침묵으로 끝내지 않는다(_peer_on_empty).
                titles, provider = _peer_on_empty()
        except SentinelError as google_err:
            key = os.environ.get(FALLBACK_KEY_ENV)
            if key:
                try:
                    titles = [html.unescape(t) for t in tavily_headlines(FALLBACK_QUERY, key)]
                    provider = TAVILY
                except NewsFallbackError as fb_err:
                    titles, provider = _fetch_secondary(google_err, f"대체 {fb_err}")
            else:
                titles, provider = _fetch_secondary(
                    google_err, f"대체 공급자 없음({FALLBACK_KEY_ENV} 미설정)")
    except SentinelError as e:
        _FAIL.update(at=now, err=str(e))            # 셋 다 실패 — 쿨다운 동안 다시 안 부른다
        raise
    _CACHE.update(at=now, titles=titles, provider=provider)
    _FAIL.update(at=0.0, err=None)
    return titles


def last_provider() -> str:
    """가장 최근 `fetch_titles()` 에 답한 공급자(`google` | `tavily` | `gdelt`)."""
    return _CACHE.get("provider") or GOOGLE


def split_publisher(title: str) -> tuple[str, str | None]:
    """`제목 - 매체` 꼴에서 (제목, 매체). 매체를 못 읽으면 None — 추측하지 않는다."""
    head, sep, tail = title.rpartition(" - ")
    if sep and head and 0 < len(tail) <= 60:
        return head.strip(), tail.strip()
    return title.strip(), None


def match_headlines(titles: list[str],
                    drops: dict | None = None) -> dict[str, list[dict]]:
    """병원체별로 **건강 사건 제목**을 모은다. 같은 제목은 한 번만 센다.

    `drops` 를 주면 버린 사유별 건수를 거기에 더한다(판정 결과는 바뀌지 않는다).
    순서는 '병원체 낱말 먼저' 다 — 그래야 `비질병`·`건강맥락없음` 이 **병원체를
    언급한 제목에 대한 수**가 된다. 넓은 질의에서 무관한 제목까지 섞어 세면
    숫자가 커지기만 하고 아무 말도 못 한다.
    """
    out: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    counts = drops if drops is not None else {}
    for raw in titles:
        headline, publisher = split_publisher(raw)
        hits = [k for k, (pattern, _) in PATHOGENS.items() if pattern.search(headline)]
        if not hits:
            counts["병원체낱말없음"] = counts.get("병원체낱말없음", 0) + 1
            continue
        # NOT_A_DISEASE·HEALTH_CONTEXT 는 예전처럼 **매체명이 붙은 원문**에 걸어야 한다
        # (매체명이 맥락 낱말을 담는 경우가 있다). 판정을 바꾸지 않으려고 그대로 둔다.
        if NOT_A_DISEASE.search(raw):
            counts["비질병"] = counts.get("비질병", 0) + 1
            continue
        if not HEALTH_CONTEXT.search(raw):
            counts["건강맥락없음"] = counts.get("건강맥락없음", 0) + 1
            continue
        for key in hits:
            ident = (key, headline.lower())
            if ident in seen:
                counts["중복"] = counts.get("중복", 0) + 1
                continue
            seen.add(ident)
            out.setdefault(key, []).append({"title": headline, "publisher": publisher})
    return out


def candidates(titles: list[str] | None = None, provider: str = GOOGLE) -> list[dict]:
    """경보 후보. 서로 다른 매체 `MIN_PUBLISHERS` 곳 이상이 보도한 병원체만.

    `provider` 가 대체 경로(`tavily`·`gdelt`)면 근거에 '대체 검색이라 매체 수는 근사'라고
    적는다 — 같은 줄의 숫자가 Google 주기의 숫자와 같은 종류의 측정인 척하지 않게."""
    if titles is None:
        titles = fetch_titles()
        provider = last_provider()
    drops: dict[str, int] = {}
    matched = match_headlines(titles, drops)
    _FUNNEL.clear()
    _FUNNEL.update(titles=len(titles), provider=provider,
                   pathogen_hits=sum(len(v) for v in matched.values()), drops=drops)
    cands = []
    for key, items in matched.items():
        publishers = sorted({i["publisher"] for i in items if i["publisher"]})
        if len(publishers) < MIN_PUBLISHERS:
            # ★ 여기가 가장 아까운 자리다 ★ 병원체 보도가 **왔는데** 매체가 한 곳이라
            # 못 올린 것이다. 한 곳이 보도한 단건이 이 층이 노리는 바로 그 모양일 수
            # 있어서, 버렸다는 사실과 무엇을 버렸는지를 남긴다.
            drops["매체부족"] = drops.get("매체부족", 0) + 1
            drops.setdefault("매체부족_예", []).append(
                f"{PATHOGENS[key][1]}:{items[0]['title'][:60]}")
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
                *([_FALLBACK_NOTES[provider]] if provider in _FALLBACK_NOTES else []),
            ],
        })
    return cands

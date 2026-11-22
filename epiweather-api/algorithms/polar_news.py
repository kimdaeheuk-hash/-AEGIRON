"""극지 현지어 보도 피드 — Google News RSS 한 지역 한 피드 (2026-11-22 개편 2차).

옛 `local_news`(179개국 피드 + Cerebras/Groq LLM 재분류)에서 극지가 실제로 쓰던 것만 옮겼다.
극지는 지역마다 피드 하나를 키워드 비율로만 본다 — LLM 재분류·국가 문턱은 쓰지 않았다.
옛 모듈은 복원 기준 커밋 83406e4 에 있다.
"""
from __future__ import annotations

import re
import urllib.parse
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import requests

from .common import brief_reason

USER_AGENT = {"User-Agent": "EpiWeather-LocalNews/1.0 (epiweather.kr)"}
TIMEOUT = 15

# 질의에 붙이는 공통어 — 현지 일반어와 OR 로 묶는다.
_UNIVERSAL_QUERY_TERMS = [
    "outbreak", "epidemic", "ebola", "cholera", "dengue", "mpox", "measles",
    "bird flu", "coronavirus",
]

# ★ 표본이 적으면 판정하지 않는다 ★ 기사 5건에 키워드 6종이 잡혀 ratio 1.2 가 나오기도 한다.
# 그건 신호가 아니라 표본 부족이다 — '모른다'와 '괜찮다'는 다르다.
MIN_ITEMS_FOR_ALERT = 20

# 같은 피드가 전역 뉴스로 되돌아오는 것을 막으려고 질의에 영토 이름을 덧붙인다(2026-08-31 실측).
POLAR_TERMS: dict[str, str] = {
    "siberia_yamal_news": "Ямал",
    "alaska_north_news": '"North Slope"',
    "canada_arctic_news": '"Northwest Territories"',
    "greenland_news": "Greenland",
    "svalbard_news": "Svalbard",
    "antarctic_peninsula_news": '"Antarctic Peninsula"',
    "arctic_archipelago_news": '"Arctic Archipelago"',
    "iceland_news": "Iceland",
}


def _gnews(local_terms: list[str], hl: str, gl: str) -> str:
    """Google News RSS 검색 URL. hl=인터페이스 언어, gl=국가."""
    query = " OR ".join(local_terms + _UNIVERSAL_QUERY_TERMS)
    ceid = f"{gl}:{hl.split('-')[0]}"
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"


def _scoped(url: str, slug: str) -> str:
    """극지 피드면 질의에 영토 이름을 덧붙인다. 아니면 그대로."""
    term = POLAR_TERMS.get(slug)
    if not term:
        return url
    p = urlparse(url)
    q = parse_qs(p.query)
    q["q"] = ["(%s) %s" % (q["q"][0], term)]
    return urlunparse(p._replace(query=urlencode({k: v[0] for k, v in q.items()}, quote_via=quote)))


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def fetch_local_feed(slug: str, lang: str, region: str, url: str, keywords: list[str]) -> dict:
    """RSS 피드 하나에서 항목 수 + 키워드 히트 수. 실패는 status='error' 와 짧은 사유."""
    try:
        resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        resp.raise_for_status()
        text = resp.text
        item_count = text.count("<item>")
        keyword_hits = _count_keyword_hits(text, keywords)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text)
        all_titles = [t[0] or t[1] for t in titles if t[0] or t[1]]
        return {
            "slug": slug, "lang": lang, "region": region,
            "item_count": item_count,
            "keyword_hits": keyword_hits,
            "hit_ratio": round(keyword_hits / max(item_count, 1), 3),
            "sample_titles": all_titles[:5],
            "status": "ok",
            "_all_titles": all_titles,
        }
    except Exception as e:  # noqa: BLE001 — 실패는 값으로 돌려준다
        return {
            "slug": slug, "lang": lang, "region": region,
            "status": "error",
            "error": str(e)[:100],
            "reason": brief_reason(e),
            "http_status": getattr(getattr(e, "response", None), "status_code", None),
        }

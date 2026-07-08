"""현지어 뉴스 RSS — Phase 2 ⑰.

영어 번역 전에 감지가 목표. 에볼라 진원 동아프리카, 에이즈·콜레라 서아프리카,
뎅기열·H5N1 동남아 커버.

스와힐리어 (동아프리카 — 에볼라, 콜레라 진원)
프랑스어   (서·중앙아프리카 — DRC, 카메룬)
태국어     (���남아 — 뎅기열, H5N1)
베트남어   (동남아 — 뎅기열, 조류독감)

감지 방식:
  각 RSS 피드에서 최근 항목 수 + 감염병 키워드 히트 수를 반환.
  키워드는 현지어로 작성 (번역 전에 잡아��� ����가 있음).
"""
from __future__ import annotations
import re
from typing import Any

import requests

USER_AGENT = {"User-Agent": "EpiWeather-LocalNews/1.0 (epiweather.kr)"}
TIMEOUT = 15

# (slug, 언어, 지역, RSS URL, 감염병 키워드 목록)
LOCAL_FEEDS: list[tuple[str, str, str, str, list[str]]] = [
    (
        "swahili_rbc",
        "스와힐리어", "동아프리카",
        "https://www.rbc.co.rw/spip.php?page=backend&lang=sw",
        ["ugonjwa", "mlipuko", "virusi", "homa", "kipindupindu", "ebola", "malaria"],
    ),
    (
        "swahili_bbc",
        "스와힐리어", "동아프리카",
        "https://feeds.bbci.co.uk/swahili/rss.xml",
        ["ugonjwa", "mlipuko", "virusi", "homa", "kipindupindu", "ebola", "malaria"],
    ),
    (
        "french_rfi_africa",
        "프랑스어", "서·중앙아프리카",
        "https://www.rfi.fr/fr/rss/afrique.xml",
        ["épidémie", "maladie", "virus", "fièvre", "choléra", "ebola", "grippe aviaire"],
    ),
    (
        "french_lemonde_afrique",
        "프랑스어", "서·중앙아프리카",
        "https://www.lemonde.fr/afrique/rss_full.xml",
        ["épidémie", "maladie", "virus", "fièvre", "choléra", "ebola"],
    ),
    (
        "thai_matichon",
        "태국어", "동남아",
        "https://www.matichon.co.th/feed",
        ["โรค", "ระบาด", "ไวร��ส", "ไข้", "ไข้��ลือดออก", "ไข้หวัดนก"],
    ),
    (
        "thai_bangkokpost_health",
        "영어(태국)", "동남아",
        "https://www.bangkokpost.com/rss/data/topstories.xml",
        ["dengue", "bird flu", "H5N1", "outbreak", "disease", "fever"],
    ),
    (
        "vietnam_vnexpress",
        "베트남어", "동남아",
        "https://vnexpress.net/rss/suc-khoe.rss",
        ["dịch bệnh", "virus", "sốt xuất huyết", "cúm gia cầm", "ebola", "bệnh"],
    ),
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def fetch_local_feed(slug: str, lang: str, region: str, url: str, keywords: list[str]) -> dict:
    """단일 RSS 피드에서 항목 수 + 키워드 히트 수 반환. _all_titles는 내부용
    (Cerebras 배치 분류에 씀 — fetch_all_local_news가 최종 응답에서 제거함)."""
    try:
        resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        resp.raise_for_status()
        text = resp.text
        item_count = text.count("<item>")
        keyword_hits = _count_keyword_hits(text, keywords)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text)
        all_titles = [t[0] or t[1] for t in titles if t[0] or t[1]]

        return {
            "slug":          slug,
            "lang":          lang,
            "region":        region,
            "item_count":    item_count,
            "keyword_hits":  keyword_hits,
            "hit_ratio":     round(keyword_hits / max(item_count, 1), 3),
            "sample_titles": all_titles[:5],
            "status":        "ok",
            "_all_titles":   all_titles,
        }
    except Exception as e:
        return {
            "slug":   slug,
            "lang":   lang,
            "region": region,
            "status": "error",
            "error":  str(e)[:100],
        }


def fetch_all_local_news(cerebras_key: str | None = None) -> dict:
    """
    모든 현지어 RSS를 수집해 언어/지역별 요약 반환.
    keyword_hits가 높을수록 현지에서 감염병 관련 보도가 많다는 신호.
    cerebras_key가 있으면 llm_hit_ratio(제목 배치 분류 기반)를 우선 써서
    고경보 판정 — 키워드 매칭보다 오탐이 적음(실측: "말라리아 연구비 지원"
    같은 무관 기사도 키워드만으로는 히트로 잡혔음).

    Cerebras 분류는 피드 7개를 한 번에 묶어 단일 호출로 처리한다 — 실측 확인
    (2026-07-08) 결과 이 계정 무료 티어는 분당 요청 5개로 제한돼 있어서,
    피드별로 따로 호출하면 뒤쪽 피드는 레이트리밋에 걸려 조용히 빠지고 있었음.
    """
    results = [fetch_local_feed(*feed) for feed in LOCAL_FEEDS]

    if cerebras_key:
        from .cerebras_classify import classify_multi_feed
        classify_multi_feed(results, cerebras_key)

    total_hits = 0
    for r in results:
        total_hits += r.get("keyword_hits", 0)
        r.pop("_all_titles", None)

    active_feeds = [r for r in results if r.get("status") == "ok"]
    high_alert = [
        r for r in active_feeds
        if r.get("llm_hit_ratio", r.get("hit_ratio", 0)) >= 0.15
    ]

    return {
        "total_feeds":     len(LOCAL_FEEDS),
        "active_feeds":    len(active_feeds),
        "total_kw_hits":   total_hits,
        "high_alert_feeds": len(high_alert),
        "high_alert":      high_alert,
        "feeds":           results,
    }


def get_local_news_score() -> dict[str, Any]:
    """
    GAI 비공���신호 층에 넣을 ���일 점수.
    hit_ratio 평���이 높을수록 현지에서 감염병 관련 보도가 활발하다는 의미.
    """
    result = fetch_all_local_news()
    active = [r for r in result["feeds"] if r.get("status") == "ok" and "hit_ratio" in r]
    avg_ratio = sum(r["hit_ratio"] for r in active) / max(len(active), 1) if active else 0.0
    return {
        "local_news_hit_ratio": round(avg_ratio, 4),
        "total_kw_hits":        result["total_kw_hits"],
        "high_alert_count":     result["high_alert_feeds"],
    }

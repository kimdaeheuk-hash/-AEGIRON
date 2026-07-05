"""추가 데이터 소스 — Phase 2 ⑳.

medRxiv:           의학 프리프린트 (생명과학 bioRxiv + 의학 medRxiv)
Our World in Data: 국가별 의료인프라·백신률·기저질환률
Google Trends:     전세계 검색 (pytrends 라이브러리)
"""
from __future__ import annotations
import datetime as dt
from typing import Any

import warnings
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENT = {"User-Agent": "EpiWeather-ExtraSources/1.0 (epiweather.kr)"}
TIMEOUT = 15

MEDRXIV_BASE = "https://api.medrxiv.org/details/medrxiv"

OWID_INDICATORS = {
    "hospital_beds_per_thousand":      "https://ourworldindata.org/grapher/hospital-beds-per-1000-people.csv",
    "medical_doctors_per_thousand":    "https://ourworldindata.org/grapher/physicians-per-1000-people.csv",
}

DISEASE_KEYWORDS = [
    "ebola", "mpox", "MERS", "influenza pandemic",
    "novel virus", "unknown pathogen", "emerging infectious",
]


def fetch_medrxiv_preprints(days_back: int = 7, max_results: int = 30) -> list[dict]:
    """medRxiv 최근 N일 감염병 관련 프리프린트 조회."""
    today = dt.date.today()
    start = (today - dt.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")

    papers: list[dict] = []
    try:
        resp = requests.get(
            f"{MEDRXIV_BASE}/{start}/{end}/0/json",
            headers=USER_AGENT,
            timeout=TIMEOUT,
            verify=False,
        )
        if resp.status_code != 200:
            return papers
        collection = resp.json().get("collection", [])
        for item in collection[:max_results]:
            title    = item.get("title", "").lower()
            abstract = item.get("abstract", "").lower()
            text     = title + " " + abstract
            kw_hits  = [kw for kw in DISEASE_KEYWORDS if kw.lower() in text]
            if kw_hits:
                papers.append({
                    "doi":      item.get("doi"),
                    "title":    item.get("title"),
                    "date":     item.get("date"),
                    "category": item.get("category"),
                    "kw_hits":  kw_hits,
                })
    except Exception:
        pass
    return papers


def fetch_medrxiv_count(days_back: int = 7) -> dict:
    """medRxiv 감염병 프리프린트 수 요약."""
    papers = fetch_medrxiv_preprints(days_back)
    return {
        "medrxiv_epi_papers": len(papers),
        "papers": papers[:10],
    }


def fetch_google_trends(keywords: list[str], geo: str = "") -> dict[str, float | None]:
    """
    Google Trends — pytrends 사용. 설치 없으면 skip.
    geo="" 이면 전세계. "KR"=한국, "TH"=태국 등.
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=540, timeout=(10, 15))
        pt.build_payload(keywords[:5], cat=0, timeframe="now 7-d", geo=geo)
        df = pt.interest_over_time()
        if df.empty:
            return {kw: None for kw in keywords}
        result = {}
        for kw in keywords:
            if kw in df.columns:
                result[kw] = round(float(df[kw].iloc[-1]), 1)
            else:
                result[kw] = None
        return result
    except ImportError:
        return {kw: None for kw in keywords}
    except Exception:
        return {kw: None for kw in keywords}


def get_extra_signals() -> dict:
    """
    추가 데이터 소스 신호 종합.
    """
    medrxiv = fetch_medrxiv_count(days_back=7)

    trends_kw = ["ebola", "mpox", "bird flu", "pandemic"]
    global_trends = fetch_google_trends(trends_kw, geo="")
    kr_trends     = fetch_google_trends(["에볼라", "조류독감", "신종 바이러스"], geo="KR")

    return {
        "medrxiv":       medrxiv,
        "google_trends_global": global_trends,
        "google_trends_kr":     kr_trends,
    }

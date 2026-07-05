"""WAHIS 동물질병 신호 — Phase 2 ⑯.

세계동물보건기구(WOAH) WAHIS 공개 API — 계정 등록 후 무료.
신종 감염병 75%가 동물에서 시작. 동물 신호 없으면 진짜 조기경보 ���가.

감시 대상:
  - 조류인플루엔자 (H5N1, H5N8)
  - 아프리카돼��열병 (ASF)
  - 구제역 (FMD)
  - 브루셀라증
  - 광견병

API 문서: https://wahis.woah.org/api/v1
계정 없이 쓸 수 있는 공개 엔드포인트를 우선 활용.
계정 등록 후 Bearer 토큰을 WAHIS_API_KEY 환경변수에 넣으면 전체 데이터 접근 가능.
"""
from __future__ import annotations
import os
import datetime as dt
from typing import Any

import requests

WAHIS_BASE    = "https://wahis.woah.org/api/v1"
USER_AGENT    = {"User-Agent": "EpiWeather-WAHIS/1.0 (epiweather.kr)"}
TIMEOUT       = 20

WATCH_DISEASES = [
    "Highly pathogenic avian influenza",
    "African swine fever",
    "Foot and mouth disease",
    "Brucellosis",
    "Rabies",
]

# WOAH 공개 RSS — 계정 없이 사용 가능 (공식 발병 보고 요약).
# "/en/home/feed/"는 항상 403(WordPress comments-closed 오류)이라 죽어있던
# URL — 실제 유효한 경로는 "/en/feed/"(실측 확인, 200·항목 10개).
WOAH_RSS_URL = "https://www.woah.org/en/feed/"


def _headers(api_key: str | None) -> dict:
    h = dict(USER_AGENT)
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def fetch_wahis_outbreaks(api_key: str | None = None) -> list[dict]:
    """
    최근 30일 발병 보고 목록.
    계정 없이도 /reports/immediate 엔드포인트는 일부 접근 가능.
    """
    api_key = api_key or os.environ.get("WAHIS_API_KEY")
    today = dt.date.today()
    start = (today - dt.timedelta(days=30)).isoformat()
    outbreaks: list[dict] = []

    try:
        resp = requests.get(
            f"{WAHIS_BASE}/reports/immediate",
            headers=_headers(api_key),
            params={"startDate": start, "endDate": today.isoformat(), "pageSize": 100},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data") or data.get("items") or []
            for item in items:
                disease = item.get("disease", {})
                disease_name = disease.get("name") if isinstance(disease, dict) else str(disease)
                outbreaks.append({
                    "disease":  disease_name,
                    "country":  (item.get("country") or {}).get("name") if isinstance(item.get("country"), dict) else item.get("country"),
                    "species":  item.get("species"),
                    "date":     item.get("reportDate") or item.get("date"),
                    "cases":    item.get("cases"),
                    "deaths":   item.get("deaths"),
                    "source":   "wahis_api",
                })
    except Exception:
        pass

    return outbreaks


def fetch_woah_rss_count() -> int | None:
    """WOAH 공식 RSS 최근 항목 수 (계정 불필��)."""
    try:
        resp = requests.get(WOAH_RSS_URL, headers=USER_AGENT, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text.count("<item>")
    except Exception:
        pass
    return None


def get_animal_signal() -> dict:
    """
    GAI 동물신호 층에 넣�� 요약값 반환.
    - outbreaks_30d: 30일 내 발병 건수
    - watch_hits: WATCH_DISEASES 중 현재 발병 중인 종 수
    - woah_rss_items: WOAH RSS 최신 항목 수
    """
    api_key = os.environ.get("WAHIS_API_KEY")
    outbreaks = fetch_wahis_outbreaks(api_key)
    rss_count = fetch_woah_rss_count()

    watch_hits = 0
    if outbreaks:
        active_diseases = {(o.get("disease") or "").lower() for o in outbreaks}
        for wd in WATCH_DISEASES:
            if any(wd.lower() in d for d in active_diseases):
                watch_hits += 1

    return {
        "outbreaks_30d":  len(outbreaks),
        "watch_hits":     watch_hits,
        "woah_rss_items": rss_count,
        "has_api_key":    bool(api_key),
        "outbreaks":      outbreaks[:20],
    }

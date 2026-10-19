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

from .common import brief_reason

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


def fetch_wahis_outbreaks(api_key: str | None = None) -> tuple[list[dict] | None, str | None]:
    """
    최근 30일 발병 보고 목록. 반환: (목록, 실패 사유).

    ★ 못 읽으면 목록은 None 이다 — 빈 목록([])이 아니다 (2026-10-19) ★
    예전엔 200 이 아니거나 예외가 나면 조용히 [] 를 돌려줬고, 그게 그대로
    '30일 발병 0건'으로 매시간 로그·지수·부정적 공간에 들어갔다. 전 세계 동물
    발병이 30일 동안 0건일 리 없는데도 측정값처럼 보였다(소킹 결함 #4 와 같은 모양:
    못 읽음 → 0건). 부정적 공간은 이 지표의 '급감'을 보고 붕괴로 읽으므로, 한 번
    값을 받다가 실패하면 거짓 '보고 중단'이 울릴 수 있었다.
    빈 목록은 응답이 '목록이 비었다'고 분명히 말했을 때만 돌려준다.
    """
    api_key = api_key or os.environ.get("WAHIS_API_KEY")
    today = dt.date.today()
    start = (today - dt.timedelta(days=30)).isoformat()

    try:
        resp = requests.get(
            f"{WAHIS_BASE}/reports/immediate",
            headers=_headers(api_key),
            params={"startDate": start, "endDate": today.isoformat(), "pageSize": 100},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        data = resp.json()
    except Exception as e:
        return None, brief_reason(e)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        items = data["data"]
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
    else:
        # 목록이 어디 있는지 모르는 응답을 '0건'으로 읽지 않는다.
        return None, "응답 형식 불일치"

    outbreaks: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
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
    return outbreaks, None


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
    - outbreaks_30d: 30일 내 발병 건수 — API 를 못 읽었으면 None(판정 안 함)
    - watch_hits: WATCH_DISEASES 중 현재 발병 중인 종 수 — 같은 조건에서 None
    - woah_rss_items: WOAH RSS 최신 항목 수
    - api_reason: API 를 못 읽은 사유(읽었으면 None)
    """
    api_key = os.environ.get("WAHIS_API_KEY")
    outbreaks, api_reason = fetch_wahis_outbreaks(api_key)
    rss_count = fetch_woah_rss_count()

    if outbreaks is None:
        outbreaks_30d = watch_hits = None
    else:
        outbreaks_30d = len(outbreaks)
        active_diseases = {(o.get("disease") or "").lower() for o in outbreaks}
        watch_hits = sum(1 for wd in WATCH_DISEASES
                         if any(wd.lower() in d for d in active_diseases))

    return {
        "outbreaks_30d":  outbreaks_30d,
        "watch_hits":     watch_hits,
        "woah_rss_items": rss_count,
        "has_api_key":    bool(api_key),
        "api_reason":     api_reason,
        "outbreaks":      (outbreaks or [])[:20],
    }

"""전세계 국가 참조 데이터 — Tier-2(자동발견) 국가의 표시명·좌표 조회용.

World Bank 국가목록 API(https://api.worldbank.org/v2/country, 무료·키 불필요)는
ISO3·국가명·수도 위경도를 포함한 전세계 국가 목록을 준다. country_risk.py의
COUNTRIES(Tier-1, 14개국 수작업 큐레이션)에 없는 국가라도 nlp_extract.py(⑯)가
country_iso3를 뽑아내면 이 캐시로 이름·좌표를 채워 지도에 표시할 수 있다 —
국가 추가마다 countryCoords.ts를 손으로 늘리던 방식의 근본적 대안.

주의: 이 캐시는 "이름·좌표"만 제공한다. 취약성 지수(의료인프라·인구밀도)는
country_indicators.py가 별도로 ISO3 기준 World Bank 지표를 조회해서 채운다 —
공항연결성(OpenFlights)만은 국가명 문자열 매칭이 필요해서(예: "Korea, Rep."
vs "South Korea") 오매칭 위험이 있어 Tier-2에는 자동 연동하지 않고 중립값
그대로 둔다(country_risk._vulnerability_components 참고).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import requests

USER_AGENT = {"User-Agent": "EpiWeather-WorldCountries/1.0 (epiweather.kr)"}
TIMEOUT = 20

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "world_countries_cache.json"

WORLDBANK_COUNTRY_LIST_URL = "https://api.worldbank.org/v2/country"


def fetch_world_countries() -> dict[str, dict]:
    """
    World Bank 국가목록 전체 조회 → {ISO3: {name, capital, lat, lng, region}}.
    "Arab World"·"OECD members"처럼 개별 국가가 아닌 지역집계 항목은
    region.value == "Aggregates"로 표시되므로 제외한다. 실패 시 빈 dict.
    """
    try:
        resp = requests.get(
            WORLDBANK_COUNTRY_LIST_URL,
            params={"format": "json", "per_page": 400},
            headers=USER_AGENT, timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return {}
    except (requests.RequestException, ValueError):
        return {}

    results: dict[str, dict] = {}
    for entry in data[1]:
        region = entry.get("region") or {}
        if region.get("value") == "Aggregates":
            continue
        iso3 = entry.get("id")
        name = entry.get("name")
        if not iso3 or not name:
            continue

        lat_raw, lng_raw = entry.get("latitude"), entry.get("longitude")
        item: dict[str, Any] = {"name": name, "region": region.get("value"), "capital": entry.get("capitalCity")}
        try:
            if lat_raw and lng_raw:
                item["lat"] = float(lat_raw)
                item["lng"] = float(lng_raw)
        except ValueError:
            pass
        results[iso3] = item
    return results


def refresh_world_countries() -> dict:
    """
    캐시 갱신 — country_indicators.py의 "실패해도 이전 캐시 유지" 패턴과 동일.
    자주 안 바뀌는 참조데이터라 주간 스케줄러(main.py _run_weekly_job)에서만 호출됨.
    """
    DATA_DIR.mkdir(exist_ok=True)
    countries = fetch_world_countries()

    import datetime as dt
    cache = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "countries": countries}

    if countries:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return {"countries_fetched": len(countries), "cache_written": bool(countries)}


def load_world_countries() -> dict[str, dict]:
    """캐시 파일에서 국가 참조데이터 로드. 없으면 빈 dict."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f).get("countries", {})
    except (json.JSONDecodeError, OSError):
        return {}

"""국가 취약성 지수 실데이터 연동 — country_risk.py의 COUNTRIES 시드값을
가능한 만큼 실측 데이터로 교체한다.

covers (무료·키 불필요):
  - World Bank Open Data API: 병상수(SH.MED.BEDS.ZS) → healthcare_infra 프록시
                               인구밀도(EN.POP.DNST)   → population_density 프록시
  - OpenFlights 공개 데이터셋(GitHub 호스팅): 국가별 출발 항공노선 수
                               → airport_connectivity 프록시

border_mobility(국경이동량)는 근거로 삼을 만한 무료 API가 없어서(UNWTO는 유료)
계속 COUNTRIES의 시드값을 씀 — country_risk.py가 정직하게 명시함.

주의: World Bank의 "병상수"·"인구밀도" 원자료는 원래 COUNTRIES 시드값이 담고
있던 "의료 접근성 전반"·"확산 취약성 전반"이라는 정성적 의미보다 좁은 프록시다.
실측이라고 해서 더 정교한 게 아니라 "다른 종류의 근사치"라는 점을 인지하고 씀.
"""
from __future__ import annotations
import csv
import io
import json
import math
from pathlib import Path
from typing import Any

import requests

USER_AGENT = {"User-Agent": "EpiWeather-CountryIndicators/1.0 (epiweather.kr)"}
TIMEOUT = 20

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "country_indicators_cache.json"

WORLDBANK_BASE = "https://api.worldbank.org/v2/country"
WORLDBANK_ISO3 = {
    "DRC": "COD", "Uganda": "UGA", "Saudi Arabia": "SAU", "Thailand": "THA",
    "South Korea": "KOR", "Japan": "JPN", "Hong Kong": "HKG", "Brazil": "BRA",
    "USA": "USA",
    "Nigeria": "NGA", "Ethiopia": "ETH", "Yemen": "YEM", "Madagascar": "MDG",
    "Papua New Guinea": "PNG",
}
# 인구1천명당 병상수 — 대략 0~13 범위(선진국 상한 근처)로 정규화
WB_HOSPITAL_BEDS_INDICATOR = "SH.MED.BEDS.ZS"
HOSPITAL_BEDS_NORM_MAX = 13.0

# EN.POP.DNST(㎢당 인구) — 국가 간 편차가 매우 커서 로그 스케일로 정규화
WB_POP_DENSITY_INDICATOR = "EN.POP.DNST"
POP_DENSITY_LOG_MAX = 8000.0  # 홍콩(~7000)보다 살짝 위 — 여유를 둔 상한

OPENFLIGHTS_AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
OPENFLIGHTS_ROUTES_URL   = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
# country_risk.py의 COUNTRIES 키 → OpenFlights 데이터셋이 쓰는 국가명 문자열
OPENFLIGHTS_COUNTRY_NAMES = {
    "DRC": "Congo (Kinshasa)", "Uganda": "Uganda", "Saudi Arabia": "Saudi Arabia",
    "Thailand": "Thailand", "South Korea": "South Korea", "Japan": "Japan",
    "Hong Kong": "Hong Kong", "Brazil": "Brazil", "USA": "United States",
    "Nigeria": "Nigeria", "Ethiopia": "Ethiopia", "Yemen": "Yemen",
    "Madagascar": "Madagascar", "Papua New Guinea": "Papua New Guinea",
}
# 2026-07 실측 기준 미국이 최다(약 13,100개 노선) — 여유를 둔 상한
ROUTE_COUNT_LOG_MAX = 15000.0


def fetch_worldbank_indicator(iso3: str, indicator: str) -> tuple[float, str] | None:
    """
    최신 비결측치 하나를 (값, 연도)로 반환. 실패/데이터없음이면 None.
    mrnev=1(most recent non-empty value)로 최신 실측 연도를 바로 받는다.
    """
    url = f"{WORLDBANK_BASE}/{iso3}/indicator/{indicator}"
    try:
        resp = requests.get(
            url, params={"format": "json", "per_page": 1, "mrnev": 1},
            headers=USER_AGENT, timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return None
        entry = data[1][0]
        value = entry.get("value")
        if value is None:
            return None
        return float(value), str(entry.get("date", ""))
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def _normalize_linear(value: float, max_val: float) -> float:
    return round(max(0.0, min(value / max_val, 1.0)), 3)


def _normalize_log(value: float, max_val: float) -> float:
    if value <= 0:
        return 0.0
    return round(max(0.0, min(math.log10(value + 1) / math.log10(max_val + 1), 1.0)), 3)


def refresh_worldbank_indicators() -> dict[str, dict]:
    """국가별 병상수·인구밀도 실데이터 조회 → 0~1 정규화 값으로 반환."""
    results: dict[str, dict] = {}
    for country_id, iso3 in WORLDBANK_ISO3.items():
        beds = fetch_worldbank_indicator(iso3, WB_HOSPITAL_BEDS_INDICATOR)
        density = fetch_worldbank_indicator(iso3, WB_POP_DENSITY_INDICATOR)
        entry: dict[str, Any] = {}
        if beds:
            entry["healthcare_infra"] = _normalize_linear(beds[0], HOSPITAL_BEDS_NORM_MAX)
            entry["healthcare_infra_raw"] = beds[0]
            entry["healthcare_infra_year"] = beds[1]
        if density:
            entry["population_density"] = _normalize_log(density[0], POP_DENSITY_LOG_MAX)
            entry["population_density_raw"] = density[0]
            entry["population_density_year"] = density[1]
        if entry:
            results[country_id] = entry
    return results


def fetch_openflights_connectivity() -> dict[str, dict]:
    """OpenFlights 공개 데이터로 국가별 출발노선 수 집계 → 0~1 정규화."""
    try:
        airports_resp = requests.get(OPENFLIGHTS_AIRPORTS_URL, headers=USER_AGENT, timeout=TIMEOUT)
        routes_resp = requests.get(OPENFLIGHTS_ROUTES_URL, headers=USER_AGENT, timeout=TIMEOUT)
        if airports_resp.status_code != 200 or routes_resp.status_code != 200:
            return {}
    except requests.RequestException:
        return {}

    airport_country: dict[str, str] = {}
    reader = csv.reader(io.StringIO(airports_resp.text))
    for row in reader:
        if len(row) < 4:
            continue
        airport_country[row[0]] = row[3]

    route_counts: dict[str, int] = {}
    reader = csv.reader(io.StringIO(routes_resp.text))
    for row in reader:
        if len(row) < 4:
            continue
        src_country = airport_country.get(row[3])
        if src_country:
            route_counts[src_country] = route_counts.get(src_country, 0) + 1

    results: dict[str, dict] = {}
    for country_id, of_name in OPENFLIGHTS_COUNTRY_NAMES.items():
        count = route_counts.get(of_name, 0)
        if count:
            results[country_id] = {
                "airport_connectivity": _normalize_log(count, ROUTE_COUNT_LOG_MAX),
                "airport_connectivity_route_count": count,
            }
    return results


def refresh_country_indicators() -> dict:
    """
    World Bank + OpenFlights를 전부 조회해 country_indicators_cache.json에 저장.
    baseline_collector.collect_baseline()과 같은 패턴: 실패해도 이전 캐시는
    덮어쓰지 않고(부분 실패분만 비워둠), 성공한 지표만 반영.
    """
    DATA_DIR.mkdir(exist_ok=True)
    wb = refresh_worldbank_indicators()
    of = fetch_openflights_connectivity()

    merged: dict[str, dict] = {}
    for country_id in set(wb) | set(of):
        merged[country_id] = {**wb.get(country_id, {}), **of.get(country_id, {})}

    import datetime as dt
    cache = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "countries": merged}

    if merged:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return {
        "worldbank_countries": len(wb),
        "openflights_countries": len(of),
        "cache_written": bool(merged),
        "countries": merged,
    }


def load_country_indicators() -> dict[str, dict]:
    """캐시 파일에서 국가별 실데이터 지표 로드. 없으면 빈 dict(전부 시드값 폴백)."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f).get("countries", {})
    except (json.JSONDecodeError, OSError):
        return {}

"""지역 단위 세분화 — Phase 3.

지금: 국가 단위 위험도 (country_risk.py)
Phase3: 도시 단위 세분화
장기: 공항·항만 클러스터 → 인천공항 → 서울 유입 경로 추적

도시별 위험도 = 국가 위험도 × 도시 가중치
도시 가중치 요소:
  - 공항 연결성 (직항 여부)
  - 인구 밀도
  - 의료 인프라 수준
  - 관광·비즈니스 왕래량 (한국 기준)
"""
from __future__ import annotations
from typing import Any

CITY_RISK_DATA: dict[str, dict] = {
    "Kinshasa": {
        "country": "COD",
        "region":  "아프리카",
        "population_m": 17.1,
        "airport": "FZAA",
        "direct_to_icn": False,
        "transit_hubs":  ["OMDB", "EGLL"],
        "infra_score":   0.15,
        "korea_traffic_annual": 200,
        "disease_focus": ["Ebola", "Mpox"],
    },
    "Kampala": {
        "country": "UGA",
        "region":  "아프리카",
        "population_m": 3.6,
        "airport": "HUEN",
        "direct_to_icn": False,
        "transit_hubs":  ["OMDB", "EGLL"],
        "infra_score":   0.25,
        "korea_traffic_annual": 150,
        "disease_focus": ["Ebola"],
    },
    "Riyadh": {
        "country": "SAU",
        "region":  "중동",
        "population_m": 7.7,
        "airport": "OERK",
        "direct_to_icn": True,
        "transit_hubs":  ["OERK"],
        "infra_score":   0.75,
        "korea_traffic_annual": 180000,
        "disease_focus": ["MERS"],
    },
    "Dubai": {
        "country": "UAE",
        "region":  "중동",
        "population_m": 3.6,
        "airport": "OMDB",
        "direct_to_icn": True,
        "transit_hubs":  ["OMDB"],
        "infra_score":   0.85,
        "korea_traffic_annual": 1200000,
        "disease_focus": ["MERS", "Novel"],
    },
    "Bangkok": {
        "country": "THA",
        "region":  "동남아",
        "population_m": 10.7,
        "airport": "VTBS",
        "direct_to_icn": True,
        "transit_hubs":  ["VTBS"],
        "infra_score":   0.60,
        "korea_traffic_annual": 2800000,
        "disease_focus": ["Dengue", "H5N1", "Novel"],
    },
    "Hanoi": {
        "country": "Vietnam",
        "region":  "동남아",
        "population_m": 8.1,
        "airport": "VVNB",
        "direct_to_icn": True,
        "transit_hubs":  ["VVNB"],
        "infra_score":   0.50,
        "korea_traffic_annual": 4200000,
        "disease_focus": ["Dengue", "H5N1"],
    },
    "Jakarta": {
        "country": "Indonesia",
        "region":  "동남아",
        "population_m": 34.5,
        "airport": "WIII",
        "direct_to_icn": True,
        "transit_hubs":  ["WIII"],
        "infra_score":   0.45,
        "korea_traffic_annual": 1100000,
        "disease_focus": ["Dengue", "H5N1"],
    },
    "Seoul": {
        "country": "KOR",
        "region":  "국내",
        "population_m": 9.7,
        "airport": "RKSI",
        "direct_to_icn": True,
        "transit_hubs":  ["RKSI"],
        "infra_score":   0.90,
        "korea_traffic_annual": 0,
        "disease_focus": ["Novel", "H5N1", "MERS"],
    },
}

INCHEON_ROUTES: dict[str, dict] = {
    "Bangkok":  {"weekly_flights": 140, "travel_time_h": 5.5,  "passenger_annual": 2800000},
    "Hanoi":    {"weekly_flights": 120, "travel_time_h": 5.0,  "passenger_annual": 4200000},
    "Jakarta":  {"weekly_flights": 42,  "travel_time_h": 7.5,  "passenger_annual": 1100000},
    "Riyadh":   {"weekly_flights": 14,  "travel_time_h": 9.5,  "passenger_annual": 180000},
    "Dubai":    {"weekly_flights": 28,  "travel_time_h": 9.0,  "passenger_annual": 1200000},
    "Kinshasa": {"weekly_flights": 0,   "travel_time_h": 18.0, "passenger_annual": 200},
    "Kampala":  {"weekly_flights": 0,   "travel_time_h": 16.0, "passenger_annual": 150},
}


def compute_city_risk(city: str, country_risk_score: float) -> dict:
    """도시별 위험도 = 국가 위험도 × 도시 가중치."""
    info = CITY_RISK_DATA.get(city)
    if not info:
        return {"error": f"도시 데이터 없음: {city}"}

    route = INCHEON_ROUTES.get(city, {})
    weekly_flights = route.get("weekly_flights", 0)
    passengers     = route.get("passenger_annual", 0)

    connectivity = min(weekly_flights / 200, 1.0)
    traffic_weight = min(passengers / 5_000_000, 1.0)
    infra_vulnerability = 1 - info["infra_score"]

    city_weight = (
        connectivity       * 0.35 +
        traffic_weight     * 0.35 +
        infra_vulnerability * 0.30
    )

    city_risk = round(country_risk_score * (0.5 + city_weight), 1)
    city_risk = min(city_risk, 100.0)

    return {
        "city":          city,
        "country":       info["country"],
        "region":        info["region"],
        "country_risk":  country_risk_score,
        "city_risk":     city_risk,
        "direct_flight": info["direct_to_icn"],
        "weekly_flights_to_icn": weekly_flights,
        "annual_passengers":     passengers,
        "disease_focus": info["disease_focus"],
        "infra_score":   info["infra_score"],
    }


def rank_cities(country_risks: dict[str, float] | None = None) -> list[dict]:
    """
    모든 도시의 위험도를 계산해 내림차순 정렬.
    country_risks: {국가명: 위험점수} — 없으면 기본값 50 사용.
    """
    if country_risks is None:
        country_risks = {}

    results = []
    for city, info in CITY_RISK_DATA.items():
        base = country_risks.get(info["country"], 50.0)
        results.append(compute_city_risk(city, base))
    results.sort(key=lambda r: r.get("city_risk", 0), reverse=True)
    return results


def get_korea_inflow_path(city: str, risk_score: float) -> dict:
    """인천공항 → 서울 유입 경로 분석."""
    route = INCHEON_ROUTES.get(city, {})
    weekly = route.get("weekly_flights", 0)
    if weekly == 0:
        transit = CITY_RISK_DATA.get(city, {}).get("transit_hubs", [])
        inflow_route = f"{city} → 환승({'/'.join(transit)}) → 인천(RKSI) → 수도권"
        inflow_risk  = "낮음 (직항 없음, 환승 경유)"
    else:
        inflow_route = f"{city} → 인천(RKSI, 주 {weekly}편) → 수도권"
        inflow_risk  = "높음" if risk_score >= 70 else "중간" if risk_score >= 50 else "낮음"

    return {
        "city":         city,
        "risk_score":   risk_score,
        "inflow_route": inflow_route,
        "inflow_risk":  inflow_risk,
        "weekly_flights": weekly,
        "note": "인천공항 → KTX/버스 2시간 내 수도권 전파 가능",
    }

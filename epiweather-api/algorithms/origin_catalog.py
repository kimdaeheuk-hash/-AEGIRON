"""Stage 2 발원지 카탈로그 — 큐레이션 8개 도시 + 전세계 실제 국가 병합.

배경: "해외 발원지" 선택창이 원래 8개 도시(우한·방콕 등)로 고정돼 있었음.
전세계로 넓히되, 190여 개국에 대해 발병위험도(er) 같은 점수를 새로
지어내면 이 프로젝트가 지켜온 "지어내지 않는다" 원칙에 어긋난다. 그래서
실제 발병 역사가 있는 기존 8개(curated, common.CITIES)는 er/pax/hrs를
그대로 두고, 나머지는 world_countries.py(World Bank 실측 데이터, 이미
국가위험도 계량화 Tier-2에서 쓰던 캐시)에서 이름·좌표만 가져와 위험도는
중립값으로 명시적으로 미보정 처리한다(tier="auto").
"""
from __future__ import annotations
import math

from .common import CITIES

from .world_countries import load_world_countries

ICN_LAT, ICN_LON = 37.4602, 126.4407
CRUISE_KMH = 850.0  # 상용기 평균 순항속도 — 실제 항로·시간표가 아닌 근사치

# auto 국가(위험도 미보정)의 중립 기본값. 0.5/0.3은 "측정값 0"이 아니라
# "판단 근거 없음"을 뜻하는 중립점 — 커버리지 우려 없이 계산은 되게 하되
# curated 국가와 비교해 실제로 위험하다/여객이 많다는 주장은 하지 않는다.
AUTO_ER_DEFAULT = 0.5
AUTO_PAX_DEFAULT = 0.3


def haversine_hours(lat: float, lon: float) -> float:
    """대권거리(km) → 상용기 순항속도 환산 비행시간(시간). 실제 공식,
    실제 항로/시간표는 아님(직선거리 기반 근사치)."""
    r = 6371.0
    p1, p2 = math.radians(ICN_LAT), math.radians(lat)
    dp = math.radians(lat - ICN_LAT)
    dl = math.radians(lon - ICN_LON)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    dist_km = 2 * r * math.asin(min(1.0, math.sqrt(a)))
    return round(dist_km / CRUISE_KMH, 1)


def _curated_ids() -> set[str]:
    return {c["id"] for c in CITIES}


def build_origin_catalog() -> list[dict]:
    """curated(8) + auto(전세계 국가, curated와 겹치는 건 제외) 병합 목록.

    각 항목: id, nm(curated만 한글, auto는 World Bank 영문명), iso2(auto만),
    region(auto만), lon, lat, er, pax, hrs, note, tier("curated"|"auto")."""
    catalog: list[dict] = []
    for c in CITIES:
        catalog.append({
            "id": c["id"], "nm": c["nm"], "iso2": None, "region": None,
            "lon": c["lon"], "lat": c["lat"],
            "er": c["er"], "pax": c["pax"], "hrs": c["hrs"],
            "note": c["note"], "tier": "curated",
        })

    curated_ids = _curated_ids()
    world = load_world_countries()
    for iso3, info in world.items():
        if iso3 in curated_ids:
            continue
        lat, lon = info.get("lat"), info.get("lng")
        if lat is None or lon is None:
            continue  # 좌표 없는 국가는 지도·유입일 계산에 못 씀 — 제외
        catalog.append({
            "id": iso3, "nm": info.get("name"), "iso2": info.get("iso2"),
            "region": info.get("region"),
            "lon": lon, "lat": lat,
            "er": AUTO_ER_DEFAULT, "pax": AUTO_PAX_DEFAULT,
            "hrs": haversine_hours(lat, lon),
            "note": "위험도 미보정(참고용) — 실측 근거 없음, 중립값 계산",
            "tier": "auto",
        })
    return catalog


def get_origin_map() -> dict[str, dict]:
    """id → 항목 조회용 인덱스. compute_import() 등 단건 조회에 사용."""
    return {c["id"]: c for c in build_origin_catalog()}

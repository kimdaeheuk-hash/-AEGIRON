"""발원지 카탈로그 — curated(8) + World Bank auto 병합이 정직하게 되는지 확인.
auto 국가에 지어낸 정밀도(위험도·여객량)가 안 붙고 중립값+미보정 명시가 있는지,
좌표 없는 국가는 빠지는지, 하버사인 비행시간 추정이 맞는지 검증."""
from __future__ import annotations
from unittest.mock import patch

from algorithms import origin_catalog as oc
from algorithms.common import CITIES


SAMPLE_WORLD = {
    "VNM": {"name": "Viet Nam", "region": "East Asia & Pacific", "capital": "Hanoi",
            "iso2": "VN", "lat": 21.0069, "lng": 105.8194},
    "COD": {"name": "Congo, Dem. Rep.", "region": "Sub-Saharan Africa", "capital": "Kinshasa",
            "iso2": "CD", "lat": -4.4419, "lng": 15.2663},
    # 좌표가 없는 항목(예: 데이터 누락) — 지도·유입일 계산에 못 쓰므로 제외돼야 함
    "XYZ": {"name": "무좌표국", "region": "Unknown", "capital": None, "iso2": "XY",
            "lat": None, "lng": None},
}


def test_haversine_hours_zero_distance_is_zero():
    assert oc.haversine_hours(oc.ICN_LAT, oc.ICN_LON) == 0.0


def test_haversine_hours_positive_for_far_country():
    assert oc.haversine_hours(-4.4419, 15.2663) > 10  # 킨샤사급 거리


def test_build_origin_catalog_includes_curated_unchanged():
    with patch("algorithms.origin_catalog.load_world_countries", return_value={}):
        catalog = oc.build_origin_catalog()
    curated = [c for c in catalog if c["tier"] == "curated"]
    assert len(curated) == len(CITIES)
    wuh = next(c for c in curated if c["id"] == "WUH")
    assert wuh["er"] == 0.85 and wuh["nm"] == "우한"


def test_build_origin_catalog_adds_auto_countries_with_neutral_values():
    with patch("algorithms.origin_catalog.load_world_countries", return_value=SAMPLE_WORLD):
        catalog = oc.build_origin_catalog()
    vnm = next(c for c in catalog if c["id"] == "VNM")
    assert vnm["tier"] == "auto"
    assert vnm["er"] == oc.AUTO_ER_DEFAULT
    assert vnm["pax"] == oc.AUTO_PAX_DEFAULT
    assert "미보정" in vnm["note"]
    assert vnm["hrs"] > 0


def test_build_origin_catalog_excludes_countries_without_coordinates():
    with patch("algorithms.origin_catalog.load_world_countries", return_value=SAMPLE_WORLD):
        catalog = oc.build_origin_catalog()
    assert "XYZ" not in {c["id"] for c in catalog}


def test_build_origin_catalog_no_duplicate_when_auto_overlaps_curated():
    """curated ID(WUH 등)와 겹치는 항목이 world_countries에 있어도 curated가 우선."""
    overlapping = {**SAMPLE_WORLD, "WUH": {"name": "Wuhan (auto)", "region": "x",
                                            "capital": "x", "iso2": "CN", "lat": 30.6, "lng": 114.3}}
    with patch("algorithms.origin_catalog.load_world_countries", return_value=overlapping):
        catalog = oc.build_origin_catalog()
    wuh_entries = [c for c in catalog if c["id"] == "WUH"]
    assert len(wuh_entries) == 1
    assert wuh_entries[0]["tier"] == "curated"


def test_get_origin_map_indexes_by_id():
    with patch("algorithms.origin_catalog.load_world_countries", return_value=SAMPLE_WORLD):
        m = oc.get_origin_map()
    assert m["VNM"]["tier"] == "auto"
    assert m["WUH"]["tier"] == "curated"

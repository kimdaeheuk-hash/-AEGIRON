"""Stage 2 해외 유입일 예측 — 큐레이션 도시뿐 아니라 발원지 카탈로그(auto
국가 포함)에서도 조회되는지, 정말 없는 ID는 여전히 에러 내는지 확인."""
from __future__ import annotations
from unittest.mock import patch

from algorithms.global_inflow import compute_import

SAMPLE_WORLD = {
    "VNM": {"name": "Viet Nam", "region": "East Asia & Pacific", "capital": "Hanoi",
            "iso2": "VN", "lat": 21.0069, "lng": 105.8194},
}


def test_compute_import_works_for_curated_city():
    result = compute_import("WUH", "novel")
    assert result["origin"]["id"] == "WUH"
    assert result["arrival_day"] >= 0


def test_compute_import_falls_back_to_auto_country():
    with patch("algorithms.origin_catalog.load_world_countries", return_value=SAMPLE_WORLD):
        result = compute_import("VNM", "novel")
    assert result["origin"]["id"] == "VNM"
    assert result["origin"]["nm"] == "Viet Nam"


def test_compute_import_raises_for_truly_unknown_id():
    with patch("algorithms.origin_catalog.load_world_countries", return_value={}):
        try:
            compute_import("NOPE", "novel")
            assert False, "ValueError가 발생했어야 함"
        except ValueError:
            pass

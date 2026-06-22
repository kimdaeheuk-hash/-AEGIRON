"""Stage 2: 해외 유입일 예측 — 항공 여객 × 출현위험 × 지수성장."""
from __future__ import annotations
import math
from .common import clamp, CITY_MAP, ENTRY_PORTS


def _import_day(pax: float, hrs: float, novel: bool) -> int:
    """발원지 여객·비행시간으로 한국 첫 유입까지 걸리는 일수 추정."""
    r = 0.20 if novel else 0.16
    p0, cap = 0.00006, 0.4
    dp = pax * 4200
    lh = 1.0 if hrs < 10 else 0.68
    cum = 0.0
    for d in range(150):
        cum += min(cap, p0 * math.exp(r * d)) * dp * lh
        if cum >= 1:
            return d
    return -1


def compute_import(origin_id: str, threat: str) -> dict:
    """
    BlueDot 방식 해외 유입 추론.
    항공 여객량 × 출현위험지수 × 지수성장으로 첫 유입일 추정.
    """
    city = CITY_MAP.get(origin_id)
    if city is None:
        raise ValueError(f"알 수 없는 발원지: {origin_id}")

    novel = threat != "flu"
    arrival = _import_day(city["pax"], city["hrs"], novel)
    risk = round(clamp(city["er"] * 38 + city["pax"] * 52 + (8 if novel else 0), 5, 99))
    detect_lead = round(6 + city["er"] * 8 + (4 if novel else 0))

    sea_asia = origin_id in ("BKK", "HAN", "JKT", "DAC")
    dist = []
    for port in ENTRY_PORTS:
        w = port["base"]
        if port["id"] == "PUS" and sea_asia:
            w += 0.05
        if port["id"] == "CJU" and sea_asia:
            w += 0.03
        if port["id"] == "ICN" and not sea_asia:
            w += 0.06
        dist.append({"port": port, "weight": w})

    sw = sum(x["weight"] for x in dist)
    for x in dist:
        x["weight"] /= sw

    dist_sorted = sorted(dist, key=lambda x: -x["weight"])

    return {
        "origin": {
            "id": city["id"],
            "nm": city["nm"],
            "er": city["er"],
            "pax": city["pax"],
            "note": city["note"],
        },
        "threat": threat,
        "arrival_day": arrival,
        "risk_index": risk,
        "detect_lead_days": detect_lead,
        "entry_distribution": [
            {
                "port_id": x["port"]["id"],
                "port_nm": x["port"]["nm"],
                "pct": round(x["weight"] * 100),
                "arrival_day": arrival + round(i * 1.5),
            }
            for i, x in enumerate(dist_sorted)
        ],
    }

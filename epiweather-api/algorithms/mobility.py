"""이동성 신호 — Phase 2 ⑲.

사람이 움직이면 질병도 움직인다.
항공편 취소/감소 패턴이 발병 지역의 공항에서 먼저 나타남.

OpenSky Network API (무료, 인증 불필요):
  - 특정 공항 도착/출발 항공편 수
  - 특정 노선 항공편 수
  - 항공편 급감 = 해당 지역 유행 간접 신호

감시 공항 (발병 진원 + 한국 주요 연결 공항):
  킨샤사(FIH), 엔테베(EBB), 라고스(LOS), 다카르(DKR) — 아프리카
  방콕(BKK/DMK), 하노이(HAN), 자카르타(CGK)          — 동남아
  리야드(RUH), 두바이(DXB)                            — 중동
  인천(ICN)                                           — 한국 유입 감시
"""
from __future__ import annotations
import datetime as dt
from typing import Any

import requests

OPENSKY_BASE = "https://opensky-network.org/api"
USER_AGENT   = {"User-Agent": "EpiWeather-Mobility/1.0 (epiweather.kr)"}
TIMEOUT      = 20

WATCH_AIRPORTS = {
    "FZAA": ("킨샤사", "아프리카"),
    "HUEN": ("엔테베(우간다)", "아프리카"),
    "DNMM": ("라고스", "아프리카"),
    "GOBD": ("다카르", "아프리카"),
    "VTBS": ("방콕(수완나품)", "동남아"),
    "VTBD": ("방콕(돈므앙)", "동남아"),
    "VVNB": ("하노이", "동남아"),
    "WIII": ("자카르타", "동남아"),
    "OERK": ("리야드", "중동"),
    "OMDB": ("두바이", "중동"),
    "RKSI": ("인천", "한국"),
}


def _fetch_airport_flights(icao: str, begin: int, end: int) -> int | None:
    """특정 공항의 도착+출발 항공편 수. 실패하면 None."""
    try:
        resp = requests.get(
            f"{OPENSKY_BASE}/flights/airport",
            params={"airport": icao, "begin": begin, "end": end},
            headers=USER_AGENT,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return len(resp.json())
        if resp.status_code == 404:
            return 0
    except Exception:
        pass
    return None


def fetch_mobility_signals(hours_back: int = 1) -> dict:
    """
    주요 공항의 최근 1시간 항공편 수 조회.
    비인증 OpenSky는 최대 1시간 구간만 조회 가능.
    감소율이 높은 공항은 해당 지역 유행 징조일 수 있음.
    """
    now_ts   = int(dt.datetime.utcnow().timestamp())
    begin_ts = now_ts - hours_back * 3600

    results: list[dict] = []
    for icao, (city, region) in WATCH_AIRPORTS.items():
        count = _fetch_airport_flights(icao, begin_ts, now_ts)
        results.append({
            "icao":   icao,
            "city":   city,
            "region": region,
            "flights_24h": count,
            "status": "ok" if count is not None else "error",
        })

    available = [r for r in results if r["flights_24h"] is not None]
    total_flights = sum(r["flights_24h"] for r in available)

    return {
        "airports_checked": len(WATCH_AIRPORTS),
        "airports_ok":      len(available),
        "total_flights_24h": total_flights,
        "airports":         results,
    }


def get_mobility_score() -> dict[str, Any]:
    """
    GAI 행동신호 층에 넣을 이동성 요약.
    total_flights_24h가 기준선 대비 급감하면 이상 신호.
    """
    data = fetch_mobility_signals()
    return {
        "mobility_total_flights": data["total_flights_24h"],
        "mobility_airports_ok":   data["airports_ok"],
    }

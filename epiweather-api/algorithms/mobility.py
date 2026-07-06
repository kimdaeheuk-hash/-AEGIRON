"""이동성 신호 — Phase 2 ⑲.

사람이 움직이면 질병도 움직인다.
항공편 취소/감소 패턴이 발병 지역의 공항에서 먼저 나타난다.

OpenSky Network API (무료, 인증 불필요 — 단 익명 사용자는 쿼터가 매우 작음):
  - 특정 공항 도착/출발 항공편 수
  - 항공편 급감 = 해당 지역 유행 간접 신호

실측 확인(2026-07-06): 익명 사용자로 /flights/airport를 몇 번만 호출해도
X-Rate-Limit-Retry-After-Seconds 응답 헤더가 13686초(약 3.8시간)로 찍히며
429가 남. 공항 11개를 매시간 순서대로 조회하는 이 모듈은 그래서 사실상
상시 레이트리밋에 걸려있었을 가능성이 높다. 대응:
  1. OPENSKY_CLIENT_ID/SECRET 환경변수가 있으면 OAuth2 client_credentials로
     인증해 더 높은 쿼터를 씀(OpenSky 공식 무료 가입 방식).
  2. 429를 만나면 그 즉시 나머지 공항 조회를 중단(어차피 다 실패할 게
     뻔한데 쿼터만 더 태움) — "rate_limited"로 명시.
  3. 전 공항이 실패했을 때 total_flights_24h를 0이 아니라 None으로 반환 —
     "항공편이 실제로 0건"과 "아예 못 가져옴"을 구분(전자로 잘못 읽히면
     이상탐지가 진짜 항공편 급감처럼 오인함).

감시 공항 (발병 진원 + 한국 주요 연결 공항):
  킨샤사(FZAA), 엔테베(HUEN), 라고스(DNMM), 다카르(GOBD) — 아프리카
  방콕(VTBS/VTBD), 하노이(VVNB), 자카르타(WIII)          — 동남아
  리야드(OERK), 두바이(OMDB)                              — 중동
  인천(RKSI)                                              — 한국 유입 감시
"""
from __future__ import annotations
import datetime as dt
import os
import time
from typing import Any

import requests

OPENSKY_BASE = "https://opensky-network.org/api"
OAUTH_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
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

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _auth_header() -> dict:
    """OPENSKY_CLIENT_ID/SECRET이 있으면 OAuth2 토큰을 발급받아 Authorization
    헤더를 반환. 없거나 발급 실패하면 빈 dict(=익명 요청)."""
    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {}

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return {"Authorization": f"Bearer {_token_cache['token']}"}

    try:
        r = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 1800) - 60
        return {"Authorization": f"Bearer {_token_cache['token']}"}
    except Exception:
        return {}


def _fetch_airport_flights(icao: str, begin: int, end: int) -> tuple[int | None, bool]:
    """특정 공항의 도착+출발 항공편 수. 반환: (건수 또는 None, rate_limited 여부)."""
    try:
        resp = requests.get(
            f"{OPENSKY_BASE}/flights/airport",
            params={"airport": icao, "begin": begin, "end": end},
            headers={**USER_AGENT, **_auth_header()},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return len(resp.json()), False
        if resp.status_code == 404:
            return 0, False
        if resp.status_code == 429:
            return None, True
    except Exception:
        pass
    return None, False


def fetch_mobility_signals(hours_back: int = 1) -> dict:
    """
    주요 공항의 최근 1시간 항공편 수 조회.
    비인증 OpenSky는 최대 1시간 구간만 조회 가능하고 쿼터도 매우 작음.
    감소율이 높은 공항은 해당 지역 유행 징조일 수 있음.
    """
    now_ts   = int(dt.datetime.utcnow().timestamp())
    begin_ts = now_ts - hours_back * 3600

    results: list[dict] = []
    rate_limited = False
    for icao, (city, region) in WATCH_AIRPORTS.items():
        if rate_limited:
            # 이미 429를 만났으면 나머지도 뻔히 실패함 — 쿼터만 더 태우지 않고 건너뜀
            results.append({
                "icao": icao, "city": city, "region": region,
                "flights_24h": None, "status": "skipped_rate_limit",
            })
            continue

        count, hit_limit = _fetch_airport_flights(icao, begin_ts, now_ts)
        if hit_limit:
            rate_limited = True
            results.append({
                "icao": icao, "city": city, "region": region,
                "flights_24h": None, "status": "rate_limited",
            })
            continue

        results.append({
            "icao":   icao,
            "city":   city,
            "region": region,
            "flights_24h": count,
            "status": "ok" if count is not None else "error",
        })

    available = [r for r in results if r["flights_24h"] is not None]
    # 전 공항이 실패했으면 0이 아니라 None — "항공편 0건 확인"과 "아예 못 가져옴"을 구분
    total_flights = sum(r["flights_24h"] for r in available) if available else None

    return {
        "airports_checked": len(WATCH_AIRPORTS),
        "airports_ok":      len(available),
        "rate_limited":     rate_limited,
        "total_flights_24h": total_flights,
        "airports":         results,
    }


def get_mobility_score() -> dict[str, Any]:
    """
    GAI 행동신호 층에 넣을 이동성 요약.
    total_flights_24h가 기준선 대비 급감하면 이상 신호(단, None이면 급감이
    아니라 수집 실패이므로 이상탐지에서 자동으로 제외됨).
    """
    data = fetch_mobility_signals()
    return {
        "mobility_total_flights": data["total_flights_24h"],
        "mobility_airports_ok":   data["airports_ok"],
        "mobility_rate_limited":  data["rate_limited"],
    }

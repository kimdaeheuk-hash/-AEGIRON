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

★ 2026-08-28 — 이 모듈이 열흘 넘게 죽어 있었는데 원인을 알 수 없었다 ★
2026-08-17 오후부터 245시간(10.2일) 동안 `airports_ok=0` 이었다. 그런데 로그에
남은 것은 이 한 줄뿐이었다:

    이동성(OpenSky): 0개 공항 확인, 1h 항공편 합계 None

레이트리밋 분기가 **아니라** 일반 분기가 찍혔으니 429는 아니었다. 남는 건
인증 거부(401)·IP 차단(403)·서버 장애(5xx)·연결 차단인데 **넷이 전부 같은
"http_error"/"network_error" 로 뭉개진 뒤 요약 단계에서 통째로 버려졌다.**
게다가 OPENSKY_CLIENT_ID/SECRET 은 실제로 설정돼 있었다 — 그런데도 전멸했다.
즉 "클라우드 IP가 막혀서" 라는 설명은 **한 번도 검증된 적이 없는 추측**이었고,
그 추측이 주석과 절차 문서에 굳어 열흘 동안 아무도 다시 보지 않았다.

그래서 이 모듈은 이제 **실패 사유를 끝까지 들고 간다**(아래 4·5번).
2026-08-25 groq_watch.py 와 정확히 같은 구조의 결함이었다.
  1. OPENSKY_CLIENT_ID/SECRET 환경변수가 있으면 OAuth2 client_credentials로
     인증해 더 높은 쿼터를 씀(OpenSky 공식 무료 가입 방식).
  2. 429를 만나면 그 즉시 나머지 공항 조회를 중단(어차피 다 실패할 게
     뻔한데 쿼터만 더 태움) — "rate_limited"로 명시.
  3. 전 공항이 실패했을 때 total_flights_24h를 0이 아니라 None으로 반환 —
     "항공편이 실제로 0건"과 "아예 못 가져옴"을 구분(전자로 잘못 읽히면
     이상탐지가 진짜 항공편 급감처럼 오인함).
  4. HTTP 오류를 상태코드까지 남김("http_401" vs "http_403" vs "http_503").
     401은 키 재발급, 403은 IP 차단, 503은 기다리기 — 조치가 전부 다르다.
  5. 인증 결과와 실패 사유 집계를 요약(get_mobility_score)까지 들고 감.
     계산해놓고 버리면 로그에 "0개 공항 확인" 만 남는다.

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
TIMEOUT      = (3, 8)  # (연결 타임아웃, 응답 타임아웃) — 일부 호스팅 IP대에서
                       # OpenSky가 연결 자체를 막아 20초씩 멈추던 문제 방지

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


def _auth_header() -> tuple[dict, str]:
    """OPENSKY_CLIENT_ID/SECRET이 있으면 OAuth2 토큰을 발급받는다.
    반환: (Authorization 헤더 또는 빈 dict, 인증 상태 문자열).

    인증 상태: "authenticated" | "no_credentials" | "auth_failed: <종류>: <메시지>"

    ★ 예전엔 `except Exception: return {}` 한 줄로 실패를 통째로 삼켰다 ★
    키 오타·만료·OAuth 서버 장애가 전부 같은 침묵이 되고 조용히 익명 요청으로
    떨어졌다. 익명은 쿼터가 거의 없어 곧바로 전멸하는데, 로그에는 "0개 공항
    확인" 한 줄만 남아 **인증이 깨진 것인지 IP가 막힌 것인지 알 수 없었다.**
    2026-08-17부터 열흘 넘게 죽어 있었고, 그동안 원인이 어디에도 없었다.

    인증 실패로 수집 전체를 죽이지는 않는다(익명으로라도 시도한다 — 그게
    예전 동작이고, 익명이 되는 날도 있다). 달라지는 건 **왜 실패했는지가
    남는다는 점**뿐이다. 2026-08-25 groq_watch.py 수정과 같은 원칙이다.
    """
    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {}, "no_credentials"

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return {"Authorization": f"Bearer {_token_cache['token']}"}, "authenticated"

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
        return {"Authorization": f"Bearer {_token_cache['token']}"}, "authenticated"
    except Exception as e:
        # 키 값은 절대 찍지 않는다 — 종류와 메시지만.
        return {}, f"auth_failed: {type(e).__name__}: {str(e)[:120]}"


def _fetch_airport_flights(
    icao: str, begin: int, end: int, auth: dict | None = None
) -> tuple[int | None, str]:
    """특정 공항의 도착+출발 항공편 수. 반환: (건수 또는 None, status).

    status: "ok" | "rate_limited" | "http_<코드>"
          | "network_error: <종류>" | "error: <종류>"

    rate_limited/network_error는 나머지 공항도 뻔히 같은 이유로 실패할
    가능성이 높아 상위 루프에서 조기 중단시키는 신호로 쓰인다.

    ★ 예전엔 200/404/429 가 아닌 응답을 전부 "http_error" 한 덩어리로 묶었다 ★
    401(인증 거부)·403(IP 차단)·503(서버 장애)이 같은 말이 됐는데, 셋은 조치가
    완전히 다르다 — 키 재발급 / 호출 경로 변경 / 기다리기. 상태코드를 그대로
    남기면 다음 주기 로그 한 줄로 갈린다.
    """
    try:
        resp = requests.get(
            f"{OPENSKY_BASE}/flights/airport",
            params={"airport": icao, "begin": begin, "end": end},
            headers={**USER_AGENT, **(auth or {})},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return len(resp.json()), "ok"
        if resp.status_code == 404:
            return 0, "ok"
        if resp.status_code == 429:
            return None, "rate_limited"
        return None, f"http_{resp.status_code}"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        # 타임아웃(블랙홀)과 연결 거부(차단·DNS)는 다른 사건이다.
        return None, f"network_error: {type(e).__name__}"
    except Exception as e:
        return None, f"error: {type(e).__name__}"


def fetch_mobility_signals(hours_back: int = 1) -> dict:
    """
    주요 공항의 최근 1시간 항공편 수 조회.
    비인증 OpenSky는 최대 1시간 구간만 조회 가능하고 쿼터도 매우 작음.
    감소율이 높은 공항은 해당 지역 유행 징조일 수 있음.
    """
    now_ts   = int(dt.datetime.utcnow().timestamp())
    begin_ts = now_ts - hours_back * 3600

    # 인증은 주기당 한 번만 판정한다(토큰은 캐시됨). 공항마다 다시 묻던 것을
    # 위로 끌어올려, 인증 결과가 요약까지 그대로 실려 나가게 한다.
    auth, auth_status = _auth_header()

    results: list[dict] = []
    abort_reason: str | None = None    # "rate_limited" | "network_error"
    abort_detail: str | None = None    # 종류까지 붙은 원문
    for icao, (city, region) in WATCH_AIRPORTS.items():
        if abort_reason:
            # 이미 429나 연결 차단을 만났으면 나머지도 뻔히 같은 이유로
            # 실패함 — 매 공항마다 타임아웃을 다 기다리지 않고 건너뜀
            results.append({
                "icao": icao, "city": city, "region": region,
                "flights_24h": None, "status": f"skipped_{abort_reason}",
            })
            continue

        count, status = _fetch_airport_flights(icao, begin_ts, now_ts, auth)
        if status == "rate_limited":
            abort_reason, abort_detail = "rate_limited", status
        elif status.startswith("network_error"):
            abort_reason, abort_detail = "network_error", status
        results.append({
            "icao":   icao,
            "city":   city,
            "region": region,
            "flights_24h": count,
            "status": status,
        })

    rate_limited = abort_reason == "rate_limited"

    available = [r for r in results if r["flights_24h"] is not None]
    # 전 공항이 실패했으면 0이 아니라 None — "항공편 0건 확인"과 "아예 못 가져옴"을 구분
    total_flights = sum(r["flights_24h"] for r in available) if available else None

    # ★ 실패 사유를 세어 요약에 싣는다 ★
    # 예전엔 공항별 status 를 계산해놓고 get_mobility_score 에서 통째로 버렸다.
    # 그래서 로그엔 "0개 공항 확인" 만 남고 **왜 0개인지가 어디에도 없었다.**
    failure_reasons: dict[str, int] = {}
    for r in results:
        if r["status"] != "ok":
            failure_reasons[r["status"]] = failure_reasons.get(r["status"], 0) + 1

    return {
        "airports_checked": len(WATCH_AIRPORTS),
        "airports_ok":      len(available),
        "rate_limited":     rate_limited,
        "total_flights_24h": total_flights,
        "auth_status":      auth_status,
        "failure_reasons":  failure_reasons,
        "abort_detail":     abort_detail,
        "airports":         results,
    }


def get_mobility_score() -> dict[str, Any]:
    """
    GAI 행동신호 층에 넣을 이동성 요약.
    total_flights_24h가 기준선 대비 급감하면 이상 신호(단, None이면 급감이
    아니라 수집 실패이므로 이상탐지에서 자동으로 제외됨).

    ★ 실패 사유를 여기서 버리지 않는다(2026-08-28) ★
    fetch_mobility_signals 가 공항마다 정확한 사유를 계산해두는데, 예전엔 이
    함수가 숫자 셋만 뽑아 나머지를 통째로 버렸다. 수집기가 보는 건 이 반환값이
    전부라, 버려진 사유는 로그에도 /api/status 에도 영영 남지 않았다.
    """
    data = fetch_mobility_signals()
    return {
        "mobility_total_flights": data["total_flights_24h"],
        "mobility_airports_ok":   data["airports_ok"],
        "mobility_rate_limited":  data["rate_limited"],
        "mobility_auth_status":     data["auth_status"],
        "mobility_failure_reasons": data["failure_reasons"],
    }

"""직접 산림손실 선행지표 — 인수인계서 확장(㉝).

FIRMS 화재(㉜)는 벌목의 '프록시'였다(모든 화재가 벌목은 아님). 이 층은 한
단계 더 나아가 Global Forest Watch(GFW) 통합 산림손실 알림 — GLAD-L/GLAD-S2/
RADD 위성이 실제 나무 손실을 탐지한 것 — 을 국가별로 조회한다. 스필오버
1순위 동인(삼림파괴)의 '직접 측정' 선행 신호.

★ 정직성 경계선 ★
- GFW 통합 알림은 화재가 아니라 실제 산림손실(수관 소실)을 위성이 탐지한
  것이라 화재 프록시보다 직접적이다. 다만 알림에는 confidence 등급·탐지
  지연이 있어 '완벽한 실측'은 아니다(is_leading_indicator=True로 유지).
- deforestation_pressure는 알림 수를 정규화한 추정으로 발병 위험 측정치가 아님.
- GFW_API_KEY(무료)가 없으면 data_available=False로 정직하게 표시.

★ 배포 시 확인 필요(정직하게 명시) ★
  이 샌드박스는 외부 API가 정책 차단이라 GFW 응답을 라이브로 검증하지 못했다.
  GFW Data API의 정확한 SQL 컬럼명/응답 봉투는 배포(Railway) 환경에서 실제
  응답으로 확인해야 한다. 그래서 _extract_count는 응답의 첫 행에서 '첫 숫자
  값'을 집는 방어적 파서로 짰다 — 컬럼명이 count/alert__count/value 무엇이든
  동작하고, 형태가 예상과 다르면 가짜 숫자를 만들지 않고 None(→ data_available
  =False)으로 떨어진다. 쿼리 템플릿은 파일 상단 상수라 조정이 쉽다.
"""
from __future__ import annotations
import math
import os
import datetime as dt

import requests

USER_AGENT = {"User-Agent": "EpiWeather-Deforestation/1.0 (epiweather.kr)"}
TIMEOUT = 25

# GFW Data API — 조정 쉽도록 상단 상수로. 배포 환경에서 실제 응답으로 확인할 것.
GFW_BASE = "https://data-api.globalforestwatch.org"
GFW_DATASET = "gfw_integrated_alerts"
GFW_VERSION = "latest"
# {iso3}·{since}를 채워 count 쿼리. 컬럼명이 다르면 여기만 고치면 됨.
GFW_SQL_TEMPLATE = (
    "SELECT count(*) FROM {dataset} "
    "WHERE iso = '{iso3}' AND gfw_integrated_alerts__date >= '{since}'"
)
DEFAULT_LOOKBACK_DAYS = 30

# 30일 알림 수 정규화 상한(로그). 대규모 산림손실국이 수만 건대라 여유를 둔 값.
ALERT_REF_MAX = 50000.0

# country_risk.COUNTRIES(Tier-1) ISO3 — GFW도 iso3를 씀. 홍콩(HKG)은 산림
# 손실 대상이 사실상 없어 제외(억지로 넣지 않음).
GFW_COUNTRIES = ["COD", "UGA", "SAU", "THA", "KOR", "JPN", "BRA", "USA",
                 "NGA", "ETH", "YEM", "MDG", "PNG"]


def _extract_count(payload: dict) -> int | None:
    """GFW 응답에서 알림 수를 방어적으로 추출. 첫 데이터 행의 첫 숫자값을 집어
    컬럼명 차이(count/alert__count/value 등)에 견디게 한다. 형태가 예상 밖이면
    가짜 숫자 대신 None."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    row = data[0]
    if not isinstance(row, dict):
        return None
    for v in row.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return int(v)
    return None


def fetch_deforestation_alerts(iso3: str, api_key: str,
                               days: int = DEFAULT_LOOKBACK_DAYS) -> int | None:
    """GFW 통합 산림손실 알림 수(최근 days일). 실패/예상밖 응답이면 None."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    sql = GFW_SQL_TEMPLATE.format(dataset=GFW_DATASET, iso3=iso3, since=since)
    url = f"{GFW_BASE}/dataset/{GFW_DATASET}/{GFW_VERSION}/query"
    try:
        resp = requests.get(
            url, params={"sql": sql},
            headers={**USER_AGENT, "x-api-key": api_key}, timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        return _extract_count(resp.json())
    except Exception:
        return None


def _pressure_from_alerts(count: int) -> float:
    if count <= 0:
        return 0.0
    return round(min(math.log10(count + 1) / math.log10(ALERT_REF_MAX + 1), 1.0) * 100, 1)


def compute_country_deforestation(country_id: str, api_key: str | None = None,
                                  days: int = DEFAULT_LOOKBACK_DAYS) -> dict:
    """단일 Tier-1 국가의 직접 산림손실 선행지표. 미지원국은 KeyError,
    키 없거나 조회 실패 시 data_available=False."""
    if country_id not in GFW_COUNTRIES:
        raise KeyError(country_id)
    api_key = api_key or os.environ.get("GFW_API_KEY")
    if not api_key:
        return {
            "country": country_id, "data_available": False,
            "reason": "GFW_API_KEY 미설정 — 무료 발급 필요(data-api.globalforestwatch.org)",
            "is_leading_indicator": True,
        }

    count = fetch_deforestation_alerts(country_id, api_key, days)
    if count is None:
        return {
            "country": country_id, "data_available": False,
            "reason": "GFW 조회 실패 또는 예상밖 응답(배포 환경에서 쿼리 확인 필요) — 값 없음",
            "is_leading_indicator": True,
        }

    return {
        "country": country_id,
        "data_available": True,
        "deforestation_alerts_recent": count,     # GFW 위성 통합 산림손실 알림 수(days일)
        "day_range": days,
        "deforestation_pressure": _pressure_from_alerts(count),  # 0~100 정규화 추정
        "direct_forest_loss": True,               # 화재 프록시가 아닌 직접 산림손실 탐지
        "is_leading_indicator": True,
        "method": "gfw_integrated_alerts_v1",
    }


def deforestation_signals_all(days: int = DEFAULT_LOOKBACK_DAYS) -> dict:
    """Tier-1 전 국가의 직접 산림손실 선행지표. FIRMS 화재 프록시(㉜)의 직접 측정판."""
    api_key = os.environ.get("GFW_API_KEY")
    countries = []
    for cid in GFW_COUNTRIES:
        try:
            countries.append(compute_country_deforestation(cid, api_key=api_key, days=days))
        except KeyError:
            continue
    available = [c for c in countries if c.get("data_available")]
    available.sort(key=lambda c: -c.get("deforestation_pressure", 0))
    unavailable = [c for c in countries if not c.get("data_available")]

    return {
        "countries": available + unavailable,
        "note": "deforestation_alerts_recent는 GFW 통합 위성 산림손실 알림 수(화재 프록시가 아닌 직접 "
                "탐지). deforestation_pressure는 이를 정규화한 선행 신호 추정으로 발병 위험 측정이 아님.",
        "disclaimer": "GFW 알림에는 confidence 등급·탐지 지연이 있음. 이 샌드박스는 외부 API 차단이라 "
                      "GFW 응답을 라이브 검증하지 못함 — 정확한 쿼리/파싱은 배포 환경에서 확인 필요(파서는 "
                      "예상밖 응답 시 가짜 숫자 대신 data_available=False로 떨어지게 방어적으로 짬).",
        "data_source": "Global Forest Watch integrated alerts (무료, GFW_API_KEY 필요)",
        "configured": bool(api_key),
    }

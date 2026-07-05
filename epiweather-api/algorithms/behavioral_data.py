"""행동 변화 데이터 — Phase 3.

건강보험심사평가원(HIRA) 약품 처방 데이터와
서울열린데이터광장 응급실 방문 통계를 수집.

HIRA 공공 API: https://www.hira.or.kr/openapi
서울 열린데이터: https://data.seoul.go.kr

API 키 없어도 작동하는 공개 엔드포인트를 우선 활용.
키가 있으면 더 세분화된 데이터 접근 가능.
"""
from __future__ import annotations
import os
import datetime as dt
import requests

USER_AGENT = {"User-Agent": "EpiWeather-Behavioral/1.0 (epiweather.kr)"}
TIMEOUT = 15

# 감시 대상 약품 코드 (항바이러스제 + 해열제 + 항생제)
HIRA_DRUG_WATCH = {
    "항바이러스제": ["J05AH02", "J05AB01"],   # 타미플루, 아시클로버
    "해열진통제":   ["N02BE01", "N02AA01"],   # 아세트아미노펜, 코데인
    "항생제":       ["J01CA04", "J01CR02"],   # 아목시실린, 아목시클라브
}

SEOUL_OPEN_DATA_BASE = "http://openapi.seoul.go.kr:8088"
SEOUL_ER_DATASET = "TbHospEmgHospInfo"  # 응급의료기관 목록 + 현황


def fetch_hira_drug_claims(api_key: str | None = None) -> dict:
    """
    HIRA 약품 청구 데이터.
    공개 API는 통계 집계 수준 — 개인정보 없는 의약품 처방 건수.
    키 없이는 HIRA 통합포털 공개 통계 RSS/CSV 사용.
    """
    api_key = api_key or os.environ.get("HIRA_API_KEY")
    result: dict = {"status": "ok", "drug_claims": {}}

    if not api_key:
        result["status"] = "no_key"
        result["note"] = "HIRA_API_KEY 없음 — hira.or.kr 에서 발급 후 환경변수 설정"
        result["fallback"] = _hira_public_stats()
        return result

    today = dt.date.today()
    ym = today.strftime("%Y%m")
    for category, codes in HIRA_DRUG_WATCH.items():
        claims = []
        for code in codes:
            try:
                resp = requests.get(
                    "https://www.hira.or.kr/openapi/drugInfoService/getDrugPrescr",
                    params={
                        "ServiceKey": api_key,
                        "ediCode":    code,
                        "startYm":    ym,
                        "endYm":      ym,
                        "pageNo":     1,
                        "numOfRows":  1,
                    },
                    headers=USER_AGENT,
                    timeout=TIMEOUT,
                )
                if resp.status_code == 200:
                    claims.append({"code": code, "response": resp.text[:200]})
            except Exception:
                pass
        result["drug_claims"][category] = claims

    return result


def _hira_public_stats() -> dict:
    """HIRA 공개 통계 페이지 RSS — 키 없이 쓸 수 있는 최신 동향."""
    try:
        resp = requests.get(
            "https://www.hira.or.kr/rss/statistics.do",
            headers=USER_AGENT,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return {"rss_items": resp.text.count("<item>"), "status": "ok"}
    except Exception:
        pass
    return {"status": "unavailable"}


def fetch_seoul_er_stats(api_key: str | None = None) -> dict:
    """
    서울 응급실 현황 — 서울열린데이터광장 공공 API.
    응급실 포화도, 입원 대기, 중증 환자 비율이 감염병 급증의 간접 지표.
    """
    api_key = api_key or os.environ.get("SEOUL_OPEN_DATA_KEY")

    if not api_key:
        return {
            "status": "no_key",
            "note": "SEOUL_OPEN_DATA_KEY 없음 — data.seoul.go.kr 에서 발급 (무료)",
        }

    try:
        url = f"{SEOUL_OPEN_DATA_BASE}/{api_key}/json/{SEOUL_ER_DATASET}/1/100"
        resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        if resp.status_code != 200:
            return {"status": "error", "http": resp.status_code}
        data = resp.json()
        rows = data.get(SEOUL_ER_DATASET, {}).get("row", [])
        total_er = len(rows)
        # 현재 병상 가용률 집계
        available = sum(int(r.get("hvec", 0) or 0) for r in rows)
        total_cap = sum(int(r.get("hvs01", 0) or 0) for r in rows)
        return {
            "status": "ok",
            "total_er_count": total_er,
            "available_beds": available,
            "total_capacity": total_cap,
            "occupancy_rate": round(1 - available / max(total_cap, 1), 3),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)[:100]}


def get_behavioral_signal() -> dict:
    """행동 변화 신호 종합."""
    hira   = fetch_hira_drug_claims()
    seoul  = fetch_seoul_er_stats()
    return {
        "hira_drug_claims": hira,
        "seoul_er":         seoul,
    }

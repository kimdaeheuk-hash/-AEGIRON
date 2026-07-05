"""공급망 신호 — Phase 2 ⑱.

질병은 의료 시스템 밖에서도 흔적을 남긴다.
해열제/마스크/산소발생기 수요 급증이 공식 발표 수일 전에 나타남.

역사적 선행성:
  2003년 SARS — 홍콩 약국 해열제 품절이 공식 발표 11일 전
  2020년 코로나 — 마스크·손소독제 품절 (대구 집단감염 1주 전)

감시 방법:
  1. 네이버 DataLab 쇼핑 트렌드 — 의약품·의료용품 키워드 검색량
  2. 네이버 검색 트렌드 — "품절", "재고없음" 동시 검색
  3. 키워드 조합 이상도 계산

네이버 DataLab 쇼핑은 카테고리 ID가 필요하고, 일반 검색 DataLab은
기존 collector.py에서 이미 사용 중이므로 공급망 특화 키워드만 추가.
"""
from __future__ import annotations
import os
import json
import datetime as dt

import requests

NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
TIMEOUT = 15

SUPPLY_KEYWORDS = [
    {"groupName": "해열제", "keywords": ["해열제", "타이레놀", "이부프로펜", "부루펜"]},
    {"groupName": "마스크", "keywords": ["마스크", "KF94", "N95", "방역마스크"]},
    {"groupName": "손소독제", "keywords": ["손소독제", "손세정제", "알코올", "소독제"]},
    {"groupName": "산소발생기", "keywords": ["산소발생기", "산소포화도", "산소측정기", "혈중산소"]},
    {"groupName": "검사키트", "keywords": ["신속항원검사", "코로나키트", "독감키트", "검사키트"]},
    {"groupName": "격리용품", "keywords": ["격리", "자가격리", "재택치료", "격리키트"]},
]


def fetch_supply_trends(client_id: str, client_secret: str) -> dict[str, float | None]:
    """네이버 DataLab에서 공급망 키워드 트렌드 비율 반환."""
    today = dt.date.today()
    start = (today - dt.timedelta(days=30)).isoformat()
    end = today.isoformat()

    out: dict[str, float | None] = {}
    for group in SUPPLY_KEYWORDS:
        try:
            resp = requests.post(
                NAVER_DATALAB_URL,
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "startDate": start,
                    "endDate": end,
                    "timeUnit": "week",
                    "keywordGroups": [group],
                }, ensure_ascii=False).encode("utf-8"),
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results and results[0].get("data"):
                    latest = results[0]["data"][-1]["ratio"]
                    out[group["groupName"]] = latest
                else:
                    out[group["groupName"]] = None
            else:
                out[group["groupName"]] = None
        except Exception:
            out[group["groupName"]] = None
    return out


def get_supply_signal() -> dict:
    """
    공급망 이상 신호 종합.
    트렌드 비율이 높을수록 해당 용품 수요가 급증한 상태.
    """
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {
            "status": "no_key",
            "note": "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음 — 공급망 트렌드 수집 불가",
            "supply_trends": {},
            "supply_alert_count": 0,
        }

    trends = fetch_supply_trends(client_id, client_secret)

    # 30 이상이면 이상 급증으로 판단 (네이버 트렌드 기준 100점 척도)
    alerts = [k for k, v in trends.items() if v is not None and v >= 30]
    total_ratio = sum(v for v in trends.values() if v is not None)

    return {
        "status": "ok",
        "supply_trends": trends,
        "supply_alert_count": len(alerts),
        "supply_alert_items": alerts,
        "total_supply_ratio": round(total_ratio, 2),
    }

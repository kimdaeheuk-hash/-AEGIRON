"""구호망 2차 확인층 — ReliefWeb 무료 API (2026-11-03).

## 왜 만들었나

오지 적극개입 루프의 "묻는다" 단계: ReliefWeb/OCHA 상황보고를 보도등급
2차 확인층으로 쓴다. 무료·키 불필요(appname만 요구)를 코드 전제로 둔다.

★ 민감도 규칙(협상 불가) ★
- 등급 표기: 보도자료 등급 vs 검증됨 구분 — 여기는 전부 "보도자료 등급,
  검증 아님"이다.
- 정밀 위치 비공개: 좌표·상세 위치는 들고 오지 않는다(현장 안전).
- ProMED 미편입: 공식 무료 API가 없어(메일링) 손대지 않는다. 아래에 선언.
- medRxiv는 이미 편입됨(extra_sources.fetch_medrxiv_count) — 중복 수집 안 함.

ReliefWeb API v1: POST https://api.reliefweb.int/v1/reports?appname=...
"""
from __future__ import annotations

import requests

API_URL = "https://api.reliefweb.int/v2/reports"
# v1은 폐기됨(전 요청 410). v2는 무료지만 사전 승인 appname 필요
# (2025-11-01~, apidoc.reliefweb.int에서 무료 등록). 미승인이면 403.
APP_NAME_ENV = "RELIEFWEB_APPNAME"
APP_NAME_DEFAULT = "epiweather"


def _appname() -> str:
    import os
    return (os.environ.get(APP_NAME_ENV) or APP_NAME_DEFAULT).strip()
USER_AGENT = {"User-Agent": "EpiWeather-Relief/1.0 (epiweather.kr)"}
TIMEOUT = 20

# 질병·인도주의 관련만 남긴다(전부 들고 오면 구호 일반 뉴스 Tripadvisor가 된다).
DISEASE_KEYWORDS = [
    "cholera", "ebola", "measles", "dengue", "malaria", "mpox",
    "outbreak", "epidemic", "famine", "malnutrition", "flood", "drought",
]

GRADE_NOTE = "보도자료 등급 — 검증된 사실이 아님. 현장 안전상 정밀 위치 미표시."


def fetch_reports(limit: int = 20) -> dict:
    """최신 상황보고 + 질병 키워드 선별. 실패하면 사유와 함께 모른다고 말한다."""
    try:
        r = requests.post(
            API_URL,
            params={"appname": _appname()},
            json={"limit": min(max(1, limit), 50), "sort": ["date:desc"],
                  "fields": {"include": ["title", "date", "country", "url",
                                          "disaster", "source"]}},
            headers={**USER_AGENT, "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        items = r.json().get("data", [])
    except Exception as exc:                         # noqa: BLE001
        msg = f"{type(exc).__name__}: {exc}"
        if "403" in msg:
            msg += " — appname 미승인. apidoc.reliefweb.int에서 무료 등록 후 " \
                   f"{APP_NAME_ENV} 환경변수에 설정."
        return {"available": False, "reason": msg[:300]}
    hits = []
    for it in items:
        fields = it.get("fields", {}) if isinstance(it, dict) else {}
        title = str(fields.get("title", ""))
        blob = (title + " " + " ".join(
            str(d.get("name", "")) for d in fields.get("disaster", [])
            if isinstance(d, dict))).lower()
        kw = [k for k in DISEASE_KEYWORDS if k in blob]
        if not kw:
            continue
        countries = [str(c.get("name", "")) for c in fields.get("country", [])
                     if isinstance(c, dict)]
        hits.append({"title": title[:200], "date": fields.get("date"),
                     "countries": countries, "url": fields.get("url"),
                     "kw_hits": kw})
    return {"available": True, "fetched": len(items), "disease_reports": hits,
            "disease_count": len(hits), "grade": GRADE_NOTE,
            "promed": {"integrated": False,
                       "reason": "공식 무료 API 없음(메일링 리스트) — 미편입"},
            "medrxiv_note": "medRxiv는 extra_sources에 편입済 — 중복 수집 안 함"}

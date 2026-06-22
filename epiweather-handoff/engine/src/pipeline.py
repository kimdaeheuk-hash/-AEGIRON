"""
데이터 수집·정렬 파이프라인 (Data Collection Pipeline)
======================================================
Phase 0 '이번 주 할 일'의 실제 구현:
  1) 질병관리청 ILI(인플루엔자 의사환자분율) 표본감시 데이터 수집
  2) 검색어 트렌드(독감 관련) 수집
  3) 둘을 주간 단위로 정렬하고, 교차상관으로 '검색어가 ILI보다 며칠 앞서는지' 분석

설계:
  - 실제 API 연결부는 fetch_*() 함수에 명시 (키 필요). 키가 없으면
    자동으로 현실적인 합성 데이터로 폴백하여 파이프라인 전체를 검증 가능.
  - 모든 출력은 표준 스키마(date, value)로 정규화 → 엔진에 바로 주입 가능.

실제 연결 시 교체 지점:
  - fetch_kdca_ili()      : 공공데이터포털/감염병포털 Open API
  - fetch_search_trend()  : 네이버 데이터랩 API (또는 구글 트렌드)
"""
from __future__ import annotations
import os, math, datetime as dt
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# 표준 스키마
# ----------------------------------------------------------------------
@dataclass
class Series:
    name: str
    df: pd.DataFrame   # columns: ['date','value'] (date=주 시작일, value=float)

    def weekly(self) -> pd.DataFrame:
        """주간 정렬 보장 (이미 주간이면 그대로)."""
        d = self.df.copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d.set_index("date").resample("W-MON").mean(numeric_only=True).reset_index()
        return d


# ----------------------------------------------------------------------
# 1. KDCA ILI 수집 (실제 API 자리 + 합성 폴백)
# ----------------------------------------------------------------------
def fetch_kdca_ili(api_key: Optional[str] = None,
                   start="2021-09-01", end="2025-05-01") -> Series:
    """
    질병관리청 인플루엔자 표본감시(ILI, 외래 1000명당 의사환자수).
    실제 연결: 공공데이터포털 KDCA 인플루엔자 의사환자분율 Open API.
    api_key 없으면 합성 데이터로 폴백.
    """
    if api_key:
        try:
            return _fetch_kdca_real(api_key, start, end)
        except Exception as exc:
            print(f"[경고] KDCA API 실패 ({exc}) — 합성 데이터로 폴백")
    return _synthetic_ili(start, end)


def _fetch_kdca_real(api_key: str, start: str, end: str) -> Series:
    """공공데이터포털 질병관리청 인플루엔자 표본감시 Open API 실제 호출."""
    import requests

    URL = "https://apis.data.go.kr/1790387/flu/flu"
    all_items: list = []
    page = 1

    while True:
        params = {
            "serviceKey": api_key,
            "pageNo": page,
            "numOfRows": 100,
            "_type": "json",
        }
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()

        body = resp.json().get("response", {}).get("body", {})
        items_wrap = body.get("items") or {}
        items = items_wrap.get("item", [])
        if isinstance(items, dict):
            items = [items]

        all_items.extend(items)
        total = int(body.get("totalCount", 0))
        if not items or page * 100 >= total:
            break
        page += 1

    if not all_items:
        raise ValueError("KDCA API: 빈 응답 — 엔드포인트·키 확인 필요")

    rows = []
    for item in all_items:
        # 유행주 형식: "202301" = 2023년 1주(ISO week)
        yw = str(item.get("yearweek") or item.get("sickSeason") or "").strip()
        try:
            if len(yw) == 6:
                year, week = int(yw[:4]), int(yw[4:])
                d = dt.date.fromisocalendar(year, week, 1)  # ISO 주 월요일
                date = pd.Timestamp(d)
            else:
                continue
        except (ValueError, AttributeError):
            continue

        raw = item.get("sickRatio") or item.get("iliRate") or 0
        try:
            value = float(str(raw).replace(",", ""))
        except ValueError:
            value = 0.0

        rows.append({"date": date, "value": value})

    df = pd.DataFrame(rows)
    df = df[(df["date"] >= pd.Timestamp(start)) &
            (df["date"] <= pd.Timestamp(end))]
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)

    if len(df) < 5:
        raise ValueError(f"KDCA API: 유효 데이터 부족 ({len(df)}개) — 기간·키 확인 필요")

    return Series("ILI", df[["date", "value"]])


def fetch_search_trend(keywords=None,
                       client_id: Optional[str] = None,
                       client_secret: Optional[str] = None,
                       api_key: Optional[str] = None,
                       start="2021-09-01", end="2025-05-01") -> Series:
    """
    독감 관련 검색어 트렌드 — 네이버 데이터랩 통합검색어 트렌드 API.
    client_id + client_secret 모두 있어야 실데이터 연결.
    api_key는 client_id의 하위호환 별칭.
    둘 중 하나라도 없으면 합성 데이터로 폴백.
    """
    if keywords is None:
        keywords = ["독감", "독감증상", "인플루엔자", "해열제", "타미플루", "기침"]

    cid = client_id or api_key
    if cid and client_secret:
        try:
            return _fetch_naver_real(cid, client_secret, keywords, start, end)
        except Exception as exc:
            print(f"[경고] 네이버 DataLab API 실패 ({exc}) — 합성 데이터로 폴백")
    elif cid:
        print("[경고] NAVER_CLIENT_SECRET 누락 — 합성 데이터로 폴백")

    return _synthetic_search(start, end, keywords)


def _fetch_naver_real(client_id: str, client_secret: str,
                      keywords: list, start: str, end: str) -> Series:
    """네이버 데이터랩 통합검색어 트렌드 API 실제 호출.
    API 제약: 한 요청당 날짜 범위 최대 2년 → 구간 분할 요청.
    """
    import requests

    URL = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    all_rows: list = []
    cur = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    while cur <= end_ts:
        seg_end = min(cur + pd.DateOffset(years=2) - pd.Timedelta(days=1), end_ts)
        body = {
            "startDate": cur.strftime("%Y-%m-%d"),
            "endDate": seg_end.strftime("%Y-%m-%d"),
            "timeUnit": "week",
            "keywordGroups": [{"groupName": "독감신호", "keywords": keywords}],
        }
        resp = requests.post(URL, headers=headers, json=body, timeout=20)
        resp.raise_for_status()

        results = resp.json().get("results", [])
        if results and results[0].get("data"):
            for pt in results[0]["data"]:
                all_rows.append({
                    "date": pd.Timestamp(pt["period"]),
                    "value": float(pt["ratio"]),
                })
        cur = seg_end + pd.Timedelta(days=1)

    if not all_rows:
        raise ValueError("네이버 API: 빈 응답 — Client ID/Secret 확인 필요")

    df = pd.DataFrame(all_rows).sort_values("date")
    df = df.drop_duplicates("date").reset_index(drop=True)
    return Series("SEARCH", df[["date", "value"]])


# ----------------------------------------------------------------------
# 합성 폴백 (실데이터 연결 전, 파이프라인 검증용)
# ----------------------------------------------------------------------
def _weeks(start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    return pd.date_range(s, e, freq="W-MON")


def _synthetic_ili(start, end, seed=7) -> Series:
    rng = np.random.default_rng(seed)
    weeks = _weeks(start, end)
    n = len(weeks)
    vals = np.zeros(n)
    # 매년 겨울(연말~2월) 유행 피크
    for i, w in enumerate(weeks):
        doy = w.dayofyear
        # 겨울 가까울수록 상승 (12월~1월 정점)
        winter = math.exp(-((min(abs(doy - 15), abs(doy - 380))) / 40) ** 2)
        vals[i] = 2.0 + 38 * winter + rng.normal(0, 1.5)
    vals = np.maximum(0.5, vals)
    df = pd.DataFrame({"date": weeks, "value": vals})
    return Series("ILI", df)


def _synthetic_search(start, end, keywords, lead_weeks=2, seed=13) -> Series:
    """검색어는 ILI보다 lead_weeks 앞서 상승하도록 생성."""
    rng = np.random.default_rng(seed)
    ili = _synthetic_ili(start, end, seed=7).df["value"].to_numpy()
    weeks = _weeks(start, end)
    # 선행: ILI를 lead_weeks만큼 시프트
    shifted = np.roll(ili, -lead_weeks)
    shifted[-lead_weeks:] = shifted[-lead_weeks - 1]
    search = 20 + shifted * 1.8 + rng.normal(0, 4, len(weeks))
    search = np.maximum(0, search)
    df = pd.DataFrame({"date": weeks, "value": search})
    return Series("SEARCH", df)


# ----------------------------------------------------------------------
# 2. 정렬·결합
# ----------------------------------------------------------------------
def align(*series: Series) -> pd.DataFrame:
    """여러 Series를 주간 기준으로 inner-join 정렬."""
    out = None
    for s in series:
        w = s.weekly().rename(columns={"value": s.name})
        out = w if out is None else out.merge(w, on="date", how="inner")
    return out.dropna().reset_index(drop=True)


# ----------------------------------------------------------------------
# 3. 교차상관 — 검색어가 ILI보다 며칠/몇 주 앞서는가
# ----------------------------------------------------------------------
def cross_correlation_lead(df: pd.DataFrame, lead_col: str, target_col: str,
                           max_lag_weeks: int = 6):
    """
    lead_col(검색어)을 target_col(ILI) 대비 여러 시차로 밀어보며 상관 최대 지점 탐색.
    반환: (best_lag_weeks, best_corr, 전체 lag별 corr dict)
      best_lag > 0  →  검색어가 ILI보다 best_lag주 선행
    """
    a = df[lead_col].to_numpy()
    b = df[target_col].to_numpy()
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    results = {}
    best_lag, best_corr = 0, -2
    for lag in range(-max_lag_weeks, max_lag_weeks + 1):
        if lag >= 0:
            x, y = a[:len(a) - lag], b[lag:] if lag > 0 else b
        else:
            x, y = a[-lag:], b[:len(b) + lag]
        if len(x) < 10:
            continue
        c = float(np.corrcoef(x, y)[0, 1])
        results[lag] = c
        if c > best_corr:
            best_corr, best_lag = c, lag
    return best_lag, best_corr, results

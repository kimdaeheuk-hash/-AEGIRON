"""국제무역 선행지표 — 의료물자 수입 급증 감지 (Phase 42).

블루닷의 "항공권 판매 데이터"에 대응하는 아이기론의 각도 후보로 논의됨
(역병예보_전략포지셔닝_로컬딥 참고): 감염병이 국제 뉴스가 되기 전에, 그 나라
정부·의료기관이 먼저 의료물자(마스크·방호장비·진단키트)를 대량 수입하기
시작하는 경우가 있다 — "준비 행동"이 공식 발표보다 먼저 관측될 수 있다는
가설. UN Comtrade(전세계 관세청 무역통계, 200개국 커버)로 이 가설을 검증한다.

★ 정직성 경계선 ★
- 수입량(import_value_usd)은 관세청이 신고한 실측 수치다(measured=True).
- 그러나 "수입 급증 = 발병 대비"는 추론이다 — 정기 재고보충·가격변동·계절수요
  등 다른 이유로도 급증할 수 있다. is_proxy_for_preparedness=True로 명시한다.
- **무역데이터는 실시간이 아니다** — 국가별로 관세 신고·집계에 1~3개월 시차가
  있다(reporting_lag_months로 명시). 오늘 신호가 아니라 "몇 주~몇 달 전에
  이미 준비하고 있었다"를 사후에 확인하는 중기 선행지표다.
- COMTRADE_API_KEY(무료, comtradeplus.un.org 가입 필요)가 없으면
  data_available=False로 정직하게 표시.
"""
from __future__ import annotations
import os
import statistics

import requests

TIMEOUT = 25
BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"  # 상품(C)/월별(M)/HS분류

# 의료물자 HS 코드 — 마스크/방호장비(902000), 수술용 고무장갑(401511),
# 진단시약/검사키트(382200, HS2022 개정에서 코로나 검사키트 추적용으로 신설).
HS_CODES = {
    "masks_breathing": "902000",
    "surgical_gloves": "401511",
    "diagnostic_reagents": "382200",
}

# UN M49 숫자 국가코드 — Comtrade API는 ISO3가 아니라 이 코드를 씀.
# country_risk.COUNTRIES(Tier-1)와 1:1 매핑.
UN_M49_CODES = {
    "COD": "180", "UGA": "800", "SAU": "682", "THA": "764", "KOR": "410",
    "JPN": "392", "BRA": "76", "USA": "842", "NGA": "566", "ETH": "231",
    "YEM": "887", "MDG": "450", "PNG": "598",
}

TRAILING_MONTHS = 6  # 최근 1개월을 비교할 과거 평균 구간(개월)
REPORTING_LAG_MONTHS = 2  # 대부분 국가의 관세 통계 집계·공개 지연 추정치


def _recent_periods(n: int, lag_months: int = REPORTING_LAG_MONTHS) -> list[str]:
    """오늘 기준 신고지연을 감안해 조회 가능할 법한 최근 n개월(YYYYMM) 목록.
    최신 달부터 과거순."""
    import datetime as dt

    today = dt.date.today()
    # 신고지연만큼 물러난 지점을 '최신 가용월'로 삼음
    year, month = today.year, today.month - lag_months
    while month <= 0:
        month += 12
        year -= 1
    periods = []
    for _ in range(n):
        periods.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return periods


def fetch_import_series(country_id: str, hs_code: str, api_key: str,
                         months: int = TRAILING_MONTHS) -> list[float] | None:
    """국가·HS코드별 최근 months개월 수입액(USD) 시계열(과거→최신 순). 실패 시 None.
    월별로 신고가 안 된 달은 건너뛴다(데이터가 아예 없으면 빈 리스트)."""
    m49 = UN_M49_CODES.get(country_id)
    if not m49:
        return None
    periods = ",".join(_recent_periods(months))
    params = {
        "reporterCode": m49,
        "period": periods,
        "partnerCode": "0",       # 0 = 전세계(파트너국 구분 없음, 총수입)
        "cmdCode": hs_code,
        "flowCode": "M",          # M = Import
        "includeDesc": "false",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        rows = resp.json().get("data", [])
    except Exception:
        return None

    by_period: dict[str, float] = {}
    for r in rows:
        period = str(r.get("period") or r.get("refPeriodId") or "")
        val = r.get("primaryValue")
        if period and isinstance(val, (int, float)):
            by_period[period] = by_period.get(period, 0.0) + float(val)

    if not by_period:
        return []
    return [by_period[p] for p in sorted(by_period)]


def _surge_ratio(series: list[float]) -> float | None:
    """최신월 대비 그 이전 달들 평균의 배율. 과거 데이터가 2개 미만이면 계산 불가."""
    if len(series) < 2:
        return None
    latest = series[-1]
    baseline = series[:-1]
    mean_baseline = statistics.mean(baseline)
    if mean_baseline <= 0:
        return None
    return round(latest / mean_baseline, 2)


def compute_country_trade_signal(country_id: str, api_key: str | None = None,
                                  months: int = TRAILING_MONTHS) -> dict:
    """단일 Tier-1 국가의 의료물자 수입 선행지표. 국가 미지원이면 KeyError,
    키 없거나 조회 실패 시 data_available=False로 정직하게 표시."""
    if country_id not in UN_M49_CODES:
        raise KeyError(country_id)
    api_key = api_key or os.environ.get("COMTRADE_API_KEY")
    if not api_key:
        return {
            "country": country_id, "data_available": False,
            "reason": "COMTRADE_API_KEY 미설정 — 무료 발급 필요(comtradeplus.un.org 가입)",
            "is_leading_indicator": True,
        }

    products = {}
    any_data = False
    for label, hs in HS_CODES.items():
        series = fetch_import_series(country_id, hs, api_key, months=months)
        if series is None:
            products[label] = {"data_available": False}
            continue
        if series:
            any_data = True
        products[label] = {
            "data_available": bool(series),
            "monthly_import_usd": series,
            "surge_ratio": _surge_ratio(series),
        }

    if not any_data:
        return {
            "country": country_id, "data_available": False,
            "reason": "Comtrade 조회 실패(네트워크·잘못된 키·해당국 미보고 등) — 값 없음",
            "is_leading_indicator": True,
        }

    max_surge = max(
        (p["surge_ratio"] for p in products.values() if p.get("surge_ratio")),
        default=None,
    )

    return {
        "country": country_id,
        "data_available": True,
        "products": products,
        "max_surge_ratio": max_surge,   # 품목 중 가장 튄 배율(1.0=평소와 동일)
        "reporting_lag_months": REPORTING_LAG_MONTHS,
        "import_values_measured": True,          # 수입액 자체는 관세청 실측
        "is_proxy_for_preparedness": True,        # '발병 대비'는 추론(프록시)
        "is_leading_indicator": True,
        "method": "un_comtrade_import_surge_v1",
    }


def trade_signals_all(api_key: str | None = None) -> dict:
    """Tier-1 전 국가의 의료물자 수입 선행지표. GDELT·환경지표와 같은 계열의
    '발병 앞'을 보는 층 — 다만 무역통계 특성상 신호가 몇 주~몇 달 지연됨."""
    api_key = api_key or os.environ.get("COMTRADE_API_KEY")
    countries = []
    for cid in UN_M49_CODES:
        try:
            countries.append(compute_country_trade_signal(cid, api_key=api_key))
        except KeyError:
            continue
    available = [c for c in countries if c.get("data_available")]
    available.sort(key=lambda c: -(c.get("max_surge_ratio") or 0))
    unavailable = [c for c in countries if not c.get("data_available")]

    return {
        "countries": available + unavailable,
        "note": "monthly_import_usd는 관세청 실측 수입액. surge_ratio는 직전 평균 대비 배율로, "
                "발병 위험 측정치가 아니라 '의료물자 사전 대비 행동' 추정 프록시.",
        "disclaimer": "무역통계는 국가별 신고·집계 지연이 있어(추정 2개월) 실시간 신호가 아님 — "
                      "며칠 전이 아니라 몇 주~몇 달 전 준비 행동을 사후 확인하는 중기 지표.",
        "data_source": "UN Comtrade (무료 API키 필요, comtradeplus.un.org)",
        "configured": bool(api_key),
    }

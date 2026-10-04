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

from algorithms.common import safe_float

TIMEOUT = 25
BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"  # 상품(C)/월별(M)/HS분류

# ── 키 없이 쓰는 공개 preview 엔드포인트 (2026-08-23 추가) ──────────────
# 배경: 위 BASE_URL은 COMTRADE_API_KEY가 필요한데, 발급이 comtradedeveloper.un.org
# 가입 → Subscribe → 1영업일 대기라 번거로워 7/27에 보류했다. 그 결과 이 모듈은
# 완성돼 있는데도 프로덕션에서 13개국 전부 data_available=False로 한 달 넘게
# 죽어 있었다. 말라크(server/comtrade.ts)가 인증이 필요 없는 preview 경로를
# 쓰고 있는 걸 발견해 폴백으로 붙인다.
#
# ★ 실측으로 확인한 제약 (2026-08-23) ★
#  - reporterCode(국가 지정)가 안 먹는다. 콩고(180)를 지정하면 count=0이다.
#    → 특정국 추적은 불가능하고, 전세계를 받아서 걸러내야 한다.
#  - 한 번에 500행이 상한이다. partnerCode를 안 주면 파트너국별로 행이 쪼개져
#    A~B 국가에서 잘린다(11개국만 들어옴). partnerCode=0(World 집계행)을 주면
#    중복이 사라져 A~Z 약 100개국이 들어온다 — 이 차이가 결정적이다.
#  - 그래도 전수는 아니다. 아이기론 Tier-1 13개국 중 7개(SAU/THA/KOR/JPN/BRA/
#    USA/NGA)만 잡히고, 콩고·우간다·에티오피아·예멘·마다가스카르·파푸아뉴기니는
#    안 들어온다. 여러 달을 확인해도 동일했다 — 이 나라들이 애초에 UN에 관세
#    통계를 안 내는 것이지, 우리가 못 받는 게 아니다. 그래도 '안 잡힘 = 없음'으로
#    읽히면 안 되므로 coverage 필드로 항상 명시한다.
PUBLIC_URL = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"
PUBLIC_MAX_RECORDS = 500

# 공개 스캔 전용 HS 코드 — 위 HS_CODES(6자리)보다 한 단계 넓은 4자리를 쓴다.
# 이유(2026-08-23 실측): 같은 달(202601) 기준으로 신고국 수가 크게 다르다.
#   401511(수술용 고무장갑) →  3개국   /  4015(고무 위생용품) → 81개국
#   382200(진단시약)        →  4개국   /  3822(진단·실험용 시약) → 80개국
#   902000(호흡보호구)      → 76개국   /  9020(호흡용구)        → 76개국
# 대부분의 나라가 6자리까지 세분해 신고하지 않는다. 6자리를 고집하면 3~4개국만
# 보이고, 그 상태로 '전세계 스캔'이라 말하면 그게 거짓이 된다. 4자리는 품목이
# 조금 넓어지지만(의료용 외 고무·시약 포함) 급증 '탐지'가 목적이므로 감수한다.
PUBLIC_HS_CODES = {
    "masks_breathing": "9020",       # 호흡용구·방독면
    "surgical_gloves": "4015",       # 고무제 의류·위생용품(수술장갑 포함)
    "diagnostic_reagents": "3822",   # 진단용·실험실용 조제 시약
}

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
    "YEM": "887", "MDG": "450", "PNG": "598", "NPL": "524",
}

TRAILING_MONTHS = 6  # 최근 1개월을 비교할 과거 평균 구간(개월)
REPORTING_LAG_MONTHS = 2  # 대부분 국가의 관세 통계 집계·공개 지연 추정치
# 급증 배율을 내려면 최소 이만큼의 달이 있어야 한다. 2개월(직전 1개월 vs 최신)이면
# 산술적으로는 계산되지만 한 달 변동에 그대로 휘둘린다.
MIN_SERIES_MONTHS = 3

# ── 경보 연결용 임계값 (2026-08-23) ────────────────────────────────────
# 실측 분포(2026-08 스캔, 급증 15건): 최대 4.10 · 중앙값 2.20 · 최소 1.65.
# 무역 통계는 원래 변동이 크다 — 재고 보충 한 번에 2배가 나온다. 그래서 단일
# 품목 급증만으로는 경보를 올리지 않는다.
#
# ★ 다품목 동시 급증을 경보 대상으로 삼는 이유 ★
# 마스크만 오르면 미세먼지·산업수요·계절 요인일 수 있다. 그런데 마스크·장갑·
# 진단시약이 함께 오르면 그건 '의료 대응 준비' 쪽에 훨씬 가깝다. 실측에서도
# 몰도바(장갑 3.52 + 진단시약 2.24)처럼 두 품목이 같이 튄 국가가 따로 잡혔다.
MULTI_PRODUCT_MIN_RATIO = 1.5   # 이 배율 이상인 품목만 '동시 급증' 계산에 넣는다
ALERT_MIN_PRODUCTS = 2          # 최소 2개 품목이 동시에 튀어야 경보 후보


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


def _note_reason(notes: dict | None, reason: str) -> None:
    if notes is None:
        return
    reasons = notes.setdefault("reasons", {})
    reasons[reason] = reasons.get(reason, 0) + 1


# ★ 429(요청 과다)에만 기다렸다가 다시 묻는다 ★ (2026-10-04 프로덕션 관측)
#
#     🌐 무역 스캔: masks 2/6달 → 사용 불가(HTTP 429×4) · gloves 2/6달 → 사용 불가(HTTP 429×4)
#                  · reagents 1/6달 → 사용 불가(HTTP 429×5) · 부분 스캔 3/3 · 캐시 안 함
#
# 스캔은 18번을 간격 없이 연달아 부르고, 429 가 오면 그 달을 그냥 버렸다. 일시적 제한이 '급증
# 없음'으로 보이는 경로다(09-30 가설이 이 모양이었는지는 그날 로그가 없어 모른다). 기다림에는
# 상한을 둔다 — 스캔이 경보 주기를 몇 분씩 붙잡지 않게. 429 가 아닌 실패는 전과 같이 바로 버린다.
RATE_LIMIT_RETRIES = 2          # 429 에 대한 재시도 횟수(달 하나당)
RATE_LIMIT_BACKOFF_SEC = 5.0    # Retry-After 가 없을 때 첫 기다림(시도마다 배로)
RATE_LIMIT_MAX_WAIT_SEC = 20.0  # 한 번 기다리는 최대치
RATE_LIMIT_BUDGET_SEC = 40.0    # 품목 하나(달 6개) 전체에서 기다릴 수 있는 합계
REQUEST_GAP_SEC = 0.5           # 같은 품목의 달 사이 간격


def _sleep(sec: float) -> None:
    import time
    time.sleep(sec)


def _rate_limit_wait(e: Exception, attempt: int, notes: dict | None) -> float | None:
    """429 이고 아직 재시도할 수 있으면 기다릴 초, 아니면 None(바로 실패 처리)."""
    resp = getattr(e, "response", None)
    if getattr(resp, "status_code", None) != 429 or attempt >= RATE_LIMIT_RETRIES:
        return None
    wait = RATE_LIMIT_BACKOFF_SEC * (2 ** attempt)
    retry_after = (getattr(resp, "headers", None) or {}).get("Retry-After")
    try:
        if retry_after is not None:
            wait = float(retry_after)
    except (TypeError, ValueError):
        pass                                 # 날짜 형식 Retry-After 는 안 읽고 기본값을 쓴다
    wait = max(0.0, min(wait, RATE_LIMIT_MAX_WAIT_SEC))
    if notes is not None:
        spent = notes.get("wait_spent", 0.0)
        if spent + wait > RATE_LIMIT_BUDGET_SEC:
            return None                      # 예산을 넘기면 더 안 기다린다
        notes["wait_spent"] = spent + wait
        notes["retried_429"] = notes.get("retried_429", 0) + 1
    return wait


def _note_rows(notes: dict | None, period: str, n_rows: int) -> None:
    """그 달 응답이 몇 행이었나. 상한(PUBLIC_MAX_RECORDS)에 닿았으면 '잘렸을 수 있다'로 센다.

    상한에 닿은 달은 뒤쪽 국가가 잘렸을 수 있다 — 스캔마다 국가 구성이 흔들리는 원인 후보다
    (2026-10-04 가설, 아직 관측 안 됨). 행 수를 안 남기면 그 가설을 가를 근거가 없다.
    """
    if notes is None:
        return
    notes.setdefault("rows_by_period", {})[period] = n_rows
    if n_rows >= PUBLIC_MAX_RECORDS:
        notes["capped_months"] = notes.get("capped_months", 0) + 1


def _failure_reason(e: Exception) -> str:
    """실패 사유를 짧은 라벨로 — 로그에 '왜'가 남게 한다(HTTPError×N 처럼 센다)."""
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    if status is not None:
        return f"HTTP {status}"
    if isinstance(e, ValueError):
        return "JSON 파싱"
    return type(e).__name__


def fetch_public_month(hs_code: str, period: str,
                       notes: dict | None = None) -> dict[str, float] | None:
    """키 없이 한 달치를 받아 {ISO3: 수입액USD} 로 집계. 실패하면 None.

    `notes` 를 주면 실패 사유를 `notes["reasons"][사유] += 1` 로 남긴다. 반환 형식은
    그대로다 — 호출부와 시험이 None/dict 만 본다. 사유를 안 남기면 '왜 이 품목이 비었나'를
    아무도 모른다(2026-09-30 BLZ·AZE 경보가 6시간 사라졌을 때 로그에 아무것도 없었다).

    partnerCode=0(World 집계행)만 받는 게 핵심이다 — 안 주면 파트너국별로 행이
    쪼개져 500행 상한에 A~B 국가에서 잘린다(실측: 11개국 vs 100개국).

    합계가 아니라 국가별 최대값을 쓰지 않고 **더하는** 이유: World 집계행이
    국가당 여러 개 올 수 있다(HS 세부코드·관세제도별로 분리). 같은 국가의
    World 행들은 서로 다른 조각이므로 더하는 게 맞다.
    """
    params = {
        "cmdCode": hs_code, "flowCode": "M", "period": period,
        "partnerCode": 0, "maxRecords": PUBLIC_MAX_RECORDS,
        "includeDesc": "true",
    }
    payload = None
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            r = requests.get(PUBLIC_URL, params=params,
                             headers={"Accept": "application/json"}, timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            wait = _rate_limit_wait(e, attempt, notes)
            if wait is None:
                _note_reason(notes, _failure_reason(e))
                return None
            _sleep(wait)
    if payload is None:
        return None
    if payload.get("error"):
        _note_reason(notes, "응답 error")
        return None

    rows = payload.get("data") or []
    _note_rows(notes, period, len(rows))
    totals: dict[str, float] = {}
    for row in rows:
        iso = row.get("reporterISO")
        if not iso:
            continue
        # 값이 이상한 행 하나가 그 달 전체를 죽이면 안 된다(2026-08-13 KDCA 교훈).
        value = safe_float(row.get("primaryValue"))
        if value is None:
            continue
        totals[iso] = totals.get(iso, 0.0) + value
    return totals


def fetch_public_series(hs_code: str, months: int = TRAILING_MONTHS,
                        notes: dict | None = None) -> dict[str, list[float]]:
    """키 없이 최근 N개월을 받아 {ISO3: [과거…최신]} 시계열로 만든다.

    `notes` 를 주면 진단을 채운다(반환 형식은 그대로): `months_total`(요청한 달),
    `months_ok`(응답을 받은 달 — None 이 아닌 것), `months_empty`(응답은 왔는데 국가가
    0개인 달 — 신고가 아직 안 들어온 최신 달이 이 모양이다), `reasons`(실패 사유별 횟수).
    '빈 결과'가 '조회 실패'인지 '달이 모자람'인지 '최신 달이 비었음'인지 가르는 근거다.

    최신 달에 신고가 있고 비교할 과거가 충분한 국가만 남긴다. 결측인 달은
    건너뛰되 0으로 메우지 않는다 — 없는 값을 0으로 적으면 가짜 급증이 만들어진다.
    """
    periods = list(reversed(_recent_periods(months)))   # 과거 → 최신
    monthly: list[dict[str, float]] = []
    for i, period in enumerate(periods):
        if i:
            _sleep(REQUEST_GAP_SEC)
        totals = fetch_public_month(hs_code, period, notes=notes)
        if totals is None:
            continue
        monthly.append(totals)
    if notes is not None:
        notes["months_total"] = len(periods)
        notes["months_ok"] = len(monthly)
        notes["months_empty"] = sum(1 for m in monthly if not m)
    if len(monthly) < MIN_SERIES_MONTHS:
        return {}

    # '모든 달에 있는 국가'만 남기면 안 된다 — 관세 신고는 최신 달일수록 늦게
    # 들어와서(실측: 마스크 76개국 → 최신달 30개국), 교집합을 쓰면 커버리지가
    # 가장 늦은 달에 묶여버린다. 대신 '최신 달에 있고, 비교할 과거가
    # MIN_SERIES_MONTHS-1개 이상 있는' 국가를 쓴다. 결측인 달은 건너뛰되
    # 0으로 메우지 않는다 — 없는 값을 0으로 적으면 가짜 급증이 만들어진다.
    latest = monthly[-1]
    out: dict[str, list[float]] = {}
    for iso in latest:
        series = [m[iso] for m in monthly if iso in m]
        if len(series) >= MIN_SERIES_MONTHS:
            out[iso] = series
    return out


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


# 스캔 1회에 UN으로 18번(품목 3 × 개월 6) 호출한다 — 프로덕션 실측 약 49초.
# 경보 수집은 매시간 돌고 /api/trade-signals도 같은 함수를 부르므로 캐시가 없으면
# UN에 하루 400회 넘게 때리게 되고, 응답도 매번 1분 가까이 걸린다. 무역통계는
# 신고 지연이 2개월이라 하루 안에 값이 바뀌지 않으므로 캐시가 정확도를 해치지 않는다.
_SCAN_CACHE: dict[str, tuple[float, dict]] = {}
SCAN_CACHE_TTL_SEC = 6 * 3600
# 조회가 일부 실패한 스캔(품목 사용 불가 · 응답 못 받은 달)은 6시간 굳히지 않는다. 다음 경보
# 주기(1시간)에 다시 묻되, 실패 직후 연타하지 않을 만큼만 잡아둔다. 09-30 에 부분 결과가
# 6시간 캐시됐을 가능성이 있었다(가설) — 일시 장애가 '없는 경보'로 굳는 경로를 닫는다.
PARTIAL_SCAN_CACHE_TTL_SEC = 15 * 60


def _cache_ttl(scan: dict) -> int:
    return PARTIAL_SCAN_CACHE_TTL_SEC if scan_incomplete(scan) else SCAN_CACHE_TTL_SEC


def scan_incomplete(scan: dict) -> bool:
    """조회가 *실패*해서 일부만 들어온 스캔인가.

    빈 달(응답은 왔는데 국가 0개)은 아직 신고가 안 들어온 최신 달의 정상 모양이라 실패로 안
    친다. 실패는 두 가지다: 품목이 통째로 사용 불가이거나, 요청한 달 중 응답 못 받은 달이 있다.
    진단이 안 채워진 품목은 *모른다* — 실패로 단정하지 않는다.
    """
    products = scan.get("products") or {}
    for p in products.values():
        if not p.get("data_available"):
            return True
        f = p.get("fetch") or {}
        total, ok = f.get("months_total"), f.get("months_ok")
        if total is not None and ok is not None and ok < total:
            return True
    return False


def last_scan_incomplete(max_age_sec: float = 120.0, now: float | None = None) -> bool:
    """방금 경보 후보를 만든 스캔이 불완전했나. 호출 기록이 없거나 낡았으면 False(모른다).

    '불완전했다'를 주장하려면 이번 주기의 스캔을 봐야 한다 — 낡은 기록으로 이번 판정을
    '판정 안 함'으로 돌리지 않는다.
    """
    import time
    if not _LAST_CALL:
        return False
    now = now if now is not None else time.time()
    if now - _LAST_CALL["called_at"] > max_age_sec:
        return False
    return scan_incomplete(_LAST_CALL["scan"])


def global_trade_scan(months: int = TRAILING_MONTHS, use_cache: bool = True) -> dict:
    """★ 키 없이 전세계를 훑어 의료물자 수입 급증 국가를 '발견'한다 ★

    기존 compute_country_trade_signal은 손으로 정한 Tier-1 13개국만 본다.
    이 함수는 반대다 — 목록을 안 정하고 받아서, 튀는 나라를 찾아낸다.

    왜 이 방향이 필요한가: 2026-08-13 KDCA 사고의 원인이 정확히 '손으로 정한
    목록 밖은 통째로 안 보인다'였다(레지오넬라를 놓쳤던 이유). 감염병은 우리가
    주목하는 나라에서만 생기지 않는다. 공개 엔드포인트가 국가 지정을 안 받는
    제약이 오히려 여기선 장점이 된다.

    ★ 커버리지를 반드시 함께 반환한다 ★
    500행 상한 때문에 약 100개국만 들어온다(전세계 200여국 중). '안 잡혔다 =
    급증이 없다'로 읽히면 그게 없는 안전을 지어내는 것이다.
    """
    import time

    cache_key = f"scan:{months}"
    if use_cache:
        hit = _SCAN_CACHE.get(cache_key)
        if hit and (time.time() - hit[0]) < _cache_ttl(hit[1]):
            _record_call(hit[1], scanned_at=hit[0], cache_hit=True, cached=True)
            return hit[1]

    products: dict[str, dict] = {}
    seen_countries: set[str] = set()
    surges: list[dict] = []

    for label, hs in PUBLIC_HS_CODES.items():
        notes: dict = {}
        series_by_country = fetch_public_series(hs, months=months, notes=notes)
        if not series_by_country:
            products[label] = {"data_available": False,
                               "reason": "공개 엔드포인트 조회 실패 또는 비교 가능한 달이 2개 미만",
                               "fetch": notes}
            continue
        seen_countries |= set(series_by_country)
        hits = []
        for iso, series in series_by_country.items():
            ratio = _surge_ratio(series)
            if ratio is None:
                continue
            hits.append({"country_iso3": iso, "surge_ratio": ratio,
                         "monthly_import_usd": series})
            surges.append({"country_iso3": iso, "product": label, "surge_ratio": ratio})
        hits.sort(key=lambda h: -h["surge_ratio"])
        products[label] = {
            "data_available": True,
            "countries_observed": len(series_by_country),
            "top_surges": hits[:10],
            "fetch": notes,
        }

    surges.sort(key=lambda s: -s["surge_ratio"])
    tier1 = set(UN_M49_CODES)
    outside = [s for s in surges if s["country_iso3"] not in tier1]

    # 국가별로 묶어 '몇 품목이 동시에 튀었는지'를 센다. 이게 단일 품목 급증보다
    # 훨씬 강한 신호다 — 마스크만 오르면 미세먼지·산업수요일 수 있지만, 장갑과
    # 진단시약까지 같이 오르면 의료 대응 준비 패턴에 가깝다.
    by_country: dict[str, list[dict]] = {}
    for s in surges:
        if s["surge_ratio"] >= MULTI_PRODUCT_MIN_RATIO:
            by_country.setdefault(s["country_iso3"], []).append(s)
    multi = [
        {
            "country_iso3": iso,
            "products": sorted((h["product"] for h in hits)),
            "product_count": len(hits),
            "max_surge_ratio": max(h["surge_ratio"] for h in hits),
        }
        for iso, hits in by_country.items() if len(hits) >= 2
    ]
    multi.sort(key=lambda m: (-m["product_count"], -m["max_surge_ratio"]))

    result = {
        "scan_type": "global_public_preview",
        "data_available": bool(seen_countries),
        "countries_observed": len(seen_countries),
        "products": products,
        "top_surges": surges[:15],
        # ★ 이 목록이 이 기능의 존재 이유다 — Tier-1 밖에서 잡힌 급증 ★
        "outside_tier1_surges": outside[:10],
        # 여러 품목이 동시에 튄 국가 — 경보 후보로 올리는 건 이쪽이다.
        "multi_product_surges": multi[:10],
        "reporting_lag_months": REPORTING_LAG_MONTHS,
        "import_values_measured": True,
        "is_proxy_for_preparedness": True,
        "is_leading_indicator": True,
        "coverage": {
            "complete": False,
            "note": f"공개 preview는 요청당 {PUBLIC_MAX_RECORDS}행 상한이라 매달 약 "
                    "100개국만 들어온다(전세계 200여국 중). 여기 안 잡힌 국가는 "
                    "'급증이 없다'가 아니라 '이 스캔 범위 밖'이다. 저소득국 상당수는 "
                    "애초에 UN에 관세통계를 신고하지 않는다(콩고·우간다·에티오피아 등 "
                    "여러 달 확인).",
        },
        "method": "un_comtrade_public_global_scan_v1",
    }
    # 조회에 실패한 결과는 캐시하지 않는다 — 일시적 네트워크 장애를 6시간 동안
    # '데이터 없음'으로 굳혀버리면 그게 조용한 실패가 된다.
    cached = bool(use_cache and result["data_available"])
    if cached:
        _SCAN_CACHE[cache_key] = (time.time(), result)
    _record_call(result, scanned_at=time.time(), cache_hit=False, cached=cached)
    return result


# ── 스캔이 무엇을 했는지 로그로 말한다 (2026-10-01) ──────────────────────────
#
# 09-30 BLZ·AZE 무역 경보가 14:40~21:02 사라졌다가 돌아왔다. 그때 스캔은 로그를 한 줄도
# 안 남겨서 **데이터가 실제로 변한 것인지, 일부 품목 조회가 실패한 부분 결과가 6시간 캐시된
# 것인지** 가를 수 없었다. 코드상 후자가 가능했다 — 품목 하나만 성공해도 data_available 이
# True 이고 그 결과가 캐시된다.
#
# 여기서는 **관측만** 한다. 스캔의 동작은 바꾸지 않았다(부분 결과를 캐시할지는 별개의 결정).
_LAST_CALL: dict = {}


def _record_call(scan: dict, *, scanned_at: float, cache_hit: bool, cached: bool) -> None:
    import time
    global _LAST_CALL
    _LAST_CALL = {"called_at": time.time(), "scanned_at": scanned_at,
                  "cache_hit": cache_hit, "cached": cached, "scan": scan}


STALE_CALL_SEC = 600  # 이보다 오래된 기록이면 '이번 주기에 호출 안 됨'을 같이 적는다


def _product_part(label: str, p: dict) -> str:
    """품목 하나의 한 조각 — 몇 달 중 몇 달 응답했고 몇 개국이 남았나."""
    f = p.get("fetch") or {}
    total, ok = f.get("months_total"), f.get("months_ok")
    if total is None or ok is None:
        head = f"{label} 조회기록 없음"          # 진단이 안 채워졌다 — 모른다고 적는다
    else:
        head = f"{label} {ok}/{total}달"
        if f.get("months_empty"):
            head += f"(빈 달 {f['months_empty']})"
        if f.get("retried_429"):
            head += f"[429 재시도 {f['retried_429']}회]"
        if f.get("capped_months"):
            head += f"[{PUBLIC_MAX_RECORDS}행 상한 {f['capped_months']}달]"
    if p.get("data_available"):
        head += f" → {p.get('countries_observed', 0)}개국"
    else:
        head += " → 사용 불가"
    reasons = f.get("reasons") or {}
    if reasons:
        head += "(" + " · ".join(f"{r}×{n}" for r, n in sorted(reasons.items())) + ")"
    return head


def _is_partial(p: dict) -> bool:
    f = p.get("fetch") or {}
    total, ok = f.get("months_total"), f.get("months_ok")
    if not p.get("data_available"):
        return True
    return total is not None and ok is not None and (ok < total or bool(f.get("months_empty")))


def trade_scan_line(now: float | None = None) -> str:
    """무역 스캔이 마지막으로 한 일 한 줄. 경보 주기 로그 옆에 찍힌다.

    `🌐 무역 스캔: 새로 조회 · masks 6/6달 → 87개국 · gloves 5/6달(HTTP 429×1) → 91개국 · …
     · 부분 스캔 1/3 · 캐시 저장`

    - **새로 조회 / 캐시 N분 전** — 6시간 캐시가 얼마나 낡은 결과를 보여주는지.
    - **N/M달** — 응답을 받은 달. **빈 달** 은 응답은 왔는데 국가가 0개인 달.
    - **부분 스캔 a/3** — 불완전한 품목 수. 이 줄은 그걸 *말할 뿐* 고치지 않는다.
    - 호출 기록이 오래됐으면 '이번 주기에 호출 안 됨'을 같이 적는다 — 낡은 기록을 현재처럼
      읽게 두지 않는다.
    """
    import time
    now = now if now is not None else time.time()
    if not _LAST_CALL:
        return "🌐 무역 스캔: 호출 기록 없음"
    scan = _LAST_CALL["scan"]
    products = scan.get("products") or {}
    if _LAST_CALL["cache_hit"]:
        age_min = int((now - _LAST_CALL["scanned_at"]) // 60)
        head = f"캐시 {age_min}분 전 조회분"
    else:
        head = "새로 조회"
    parts = [_product_part(label, p) for label, p in products.items()]
    partial = sum(1 for p in products.values() if _is_partial(p))
    tail = []
    if partial:
        tail.append(f"부분 스캔 {partial}/{len(products)}")
    if not _LAST_CALL["cache_hit"]:
        tail.append("캐시 저장" if _LAST_CALL["cached"] else "캐시 안 함")
    line = " · ".join([head, *parts, *tail])
    since_call = now - _LAST_CALL["called_at"]
    if since_call > STALE_CALL_SEC:
        line += f" (마지막 호출 {int(since_call // 60)}분 전 — 이번 주기에는 호출 안 됨)"
    return f"🌐 무역 스캔: {line}"


def trade_alert_candidates(scan: dict | None = None) -> list[dict]:
    """무역 급증 → 경보 후보(alerts.collect_candidate_alerts가 쓰는 형식).

    ★ 왜 다품목만 올리는가 ★
    무역 통계는 원래 변동이 크다. 재고 보충 한 번에 2배가 나온다. 단일 품목
    급증을 그대로 경보로 올리면 매달 수십 건이 뜨고, 그러면 사람이 경보를
    무시하게 된다 — 그게 진짜 사고를 놓치는 경로다(경보 피로).
    마스크·장갑·진단시약 중 둘 이상이 동시에 튄 경우만 후보로 올린다.

    ★ 점수 산정 ★
    50점(CANDIDATE_FLOOR)에서 시작해 품목 수와 배율로 올린다. 상한을 79로 두어
    **혼자서는 절대 high(80) 이상이 안 되게** 한다. 무역 데이터는 신고 지연이
    2개월이라 '지금 벌어지는 일'이 아니라 '두 달 전 준비 행동'이다. 그것만으로
    긴급 경보를 울리는 건 정직하지 않다. 다른 층(뉴스·공식통계)과 겹칠 때
    비로소 등급이 올라가야 한다.
    """
    scan = scan if scan is not None else global_trade_scan()
    if not scan.get("data_available"):
        return []

    out = []
    for m in scan.get("multi_product_surges") or []:
        if m["product_count"] < ALERT_MIN_PRODUCTS:
            continue
        # 품목 1개당 8점, 최대배율 초과분(1.5 기준)당 10점. 상한 79.
        score = 50.0 + (m["product_count"] - 1) * 8 + min(
            (m["max_surge_ratio"] - MULTI_PRODUCT_MIN_RATIO) * 10, 20
        )
        score = round(min(score, 79.0), 1)
        products = ", ".join(m["products"])
        out.append({
            "source": f"trade_surge:{m['country_iso3']}",
            # 라벨은 name_i18n.alert_label이 조각 단위로 치환한다. 숫자를 문구
            # 안에 섞으면("2개 품목") 치환표로 못 옮기므로, 숫자는 괄호 밖으로
            # 빼고 번역 가능한 고정 조각만 남긴다.
            "label": f"의료물자 수입 동시 급증 · {m['country_iso3']} "
                     f"({m['product_count']} 품목)",
            "score": score,
            "country_iso3": m["country_iso3"],
            "evidence": [
                f"{products} 가 동시에 평소 대비 급증(최대 {m['max_surge_ratio']}배)",
                "수입액은 관세청 신고 실측치이나, '발병 대비'라는 해석은 추론(프록시)이다 — "
                "정기 재고보충·가격변동·계절수요로도 같은 패턴이 나온다",
                f"무역통계는 신고·집계 지연이 약 {REPORTING_LAG_MONTHS}개월이라 실시간 신호가 "
                "아니다. '지금 벌어지는 일'이 아니라 '몇 달 전 준비 행동'의 사후 확인이다",
                "단일 품목 급증은 후보로 올리지 않는다 — 둘 이상 동시 급증만 본다",
            ],
        })
    return out


def trade_signals_all(api_key: str | None = None) -> dict:
    """Tier-1 전 국가의 의료물자 수입 선행지표. GDELT·환경지표와 같은 계열의
    '발병 앞'을 보는 층 — 다만 무역통계 특성상 신호가 몇 주~몇 달 지연됨.

    COMTRADE_API_KEY가 없으면 키 없는 공개 스캔(global_trade_scan)으로 폴백한다.
    폴백은 국가 지정이 안 되므로 Tier-1 국가별 시계열 대신 '전세계에서 튄 곳'을
    돌려준다 — 성격이 다른 데이터이므로 mode 필드로 명시한다.
    """
    api_key = api_key or os.environ.get("COMTRADE_API_KEY")
    if not api_key:
        scan = global_trade_scan()
        scan["mode"] = "public_global_scan"
        scan["note"] = ("COMTRADE_API_KEY가 없어 키 없는 공개 스캔으로 동작 중. "
                        "국가 지정이 불가하여 Tier-1 국가별 추적 대신 전세계에서 "
                        "급증한 곳을 찾는 방식이다. 키를 등록하면 국가별 정밀 추적으로 "
                        "자동 전환된다.")
        # 기존 소비자(홈페이지·대시보드)가 기대하는 필드를 유지한다 — 응답 형태를
        # 바꾸면 그건 계약 파괴다. countries는 Tier-1 국가별 관점이라 폴백에서는
        # 채울 수 없으므로 빈 배열 + 사유를 준다(없는 데이터를 지어내지 않는다).
        scan["countries"] = []
        scan["configured"] = False
        scan["disclaimer"] = (
            "무역통계는 국가별 신고·집계 지연이 있어(추정 2개월) 실시간 신호가 아님 — "
            "며칠 전이 아니라 몇 주~몇 달 전 준비 행동을 사후 확인하는 중기 지표. "
            "현재 키 없는 공개 스캔 모드라 국가별 시계열(countries) 대신 전세계 "
            "급증 목록(top_surges·outside_tier1_surges)을 제공한다."
        )
        scan["data_source"] = ("UN Comtrade 공개 preview (인증 불필요, "
                               "요청당 500행 상한)")
        return scan

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

"""기후·환경 선행지표 — 인수인계서 확장(㉛).

가설(사업주 관점): 온난화·기후가 발병에 '선행'한다. 이 관점은 과학적으로
부분적으로 지지된다 — 특히 모기 매개 감염병(뎅기·지카·치쿤구니야)은 기온에
직접 연동돼, 지구가 더워지면 매개모기의 서식·전파 가능 범위가 넓어진다
(Mordecai et al. 2017, 매개체 열생물학). 신종 코로나류 스필오버의 1순위
동인은 토지이용 변화(삼림파괴)지만, 기후는 벡터매개 질병에서 가장 뚜렷한
'선행 신호'다. 이 모듈은 그 선행 신호를 정량화한다.

★ 정직성 경계선 ★
- 여기 값은 '측정된 발병 위험'이 아니라 '발병에 선행할 수 있는 환경 압력'의
  모델 추정치다(is_leading_indicator=True, measured=False로 명시).
- vector_suitability는 기온에서 유도한 '매개체 적합도' 프록시이지, 실제
  모기 개체수 측정이 아니다 — 이름과 플래그로 그 한계를 못박는다.
- 삼림파괴/토지이용(스필오버 1순위 동인)은 이 층에 아직 없다. Global Forest
  Watch 연동이 필요한데 지어내지 않고 '미구현'으로 정직하게 남긴다(다음 단계).
- 데이터: Open-Meteo(무료·키 불필요). 샌드박스는 외부 API 정책 차단이라
  라이브 검증 불가 — mock 단위테스트, Railway 운영환경에서 실제 수집.
"""
from __future__ import annotations
import statistics
import threading
from collections import Counter

import requests

USER_AGENT = {"User-Agent": "EpiWeather-Climate/1.0 (epiweather.kr)"}
TIMEOUT = 20
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ★ Open-Meteo 무료 하루 한도 (2026-11-18) ★
# 11-15~17 사흘 내리 극지·기후가 낮에 비고 UTC 자정 직후 풀렸다 — 하루 한도 소진의 모양.
# 원인은 같은 자료를 여러 번 받는 것: 수집기(극지) + 매시 관측값 저장(극지·기후, 30분 캐시라
# 매번 만료) + API 방문. 기후 값은 일 단위(일최고기온·일강수)라 6시간 캐시로도 낡지 않는다.
CLIMATE_CACHE_KEY = "climate-signals"
CLIMATE_CACHE_TTL_S = 6 * 3600

# ★ 전부 조회 실패한 결과는 6시간을 살지 못한다 (2026-11-19) ★
# 11-18 의 6시간 캐시가 **빈 결과까지** 저장해서, 하루 한도가 자정에 풀려도 기후 15개국이
# 계속 '판정 안 함' 이었다(11-19 00:09 UTC 실측 — `기후 15(새 0·같음 15·판정 안 함 15)`).
# Open-Meteo 를 다시 부르지 않으니 회복할 기회가 없었다.
# 수집 주기(1시간)보다 **짧게** 잡아 다음 주기가 반드시 다시 계산하게 한다. 아주 끄지 않는
# 이유는 한도 소진 구간에 방문자마다 재호출이 돌아오면 안 되기 때문이다(#132 가 막은 것).
CLIMATE_UNUSABLE_TTL_S = 55 * 60

# 실패 사유 — fetch_climate 는 계약상 실패를 None 하나로 돌려준다(호출부 셋이 그렇게 쓴다).
# 그래서 '왜'가 어디에도 안 남았다(한도 429 인지 장애인지 갈리지 않음). 계약은 그대로 두고
# 사유만 따로 센다. 수집기가 주기마다 비워 가며 로그에 찍는다.
_FAILURES: Counter[str] = Counter()
_FAILURES_LOCK = threading.Lock()


def _record_failure(reason: str) -> None:
    with _FAILURES_LOCK:
        _FAILURES[reason] += 1


def pop_failure_reasons() -> dict[str, int]:
    """직전 호출 이후 쌓인 실패 사유(예: {"HTTP 429": 8})를 돌려주고 비운다."""
    with _FAILURES_LOCK:
        out = dict(_FAILURES)
        _FAILURES.clear()
    return out


def failure_reasons_line(reasons: dict[str, int]) -> str | None:
    """로그 한 줄. 사유가 없으면 None."""
    if not reasons:
        return None
    parts = " · ".join(f"{k}×{v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]))
    return f"  ⚠ Open-Meteo 실패 사유(직전 기록 이후 · 극지·기후·오지 합산): {parts}"

# country_risk.COUNTRIES(Tier-1, ISO3)와 1:1 대응하는 수도 대표 좌표.
# 프론트 countryCoords.ts와 동일 값 — 백엔드가 world_countries 캐시(네트워크
# 의존)에 안 묶이도록 self-contained하게 둔다.
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "COD": (-4.4419, 15.2663), "UGA": (0.3476, 32.5825), "SAU": (24.7136, 46.6753),
    "THA": (13.7563, 100.5018), "KOR": (37.5665, 126.9780), "JPN": (35.6762, 139.6503),
    "HKG": (22.3193, 114.1694), "BRA": (-15.7939, -47.8828), "USA": (39.8283, -98.5795),
    "NGA": (9.0765, 7.3986), "ETH": (9.0192, 38.7525), "YEM": (15.3694, 44.1910),
    "MDG": (-18.8792, 47.5079), "PNG": (-9.4438, 147.1803),
    "NPL": (27.7172, 85.3240),  # 카트만두
}

# ★ 네팔을 넣으면서 드러난 한계 — 지어내지 말고 적어둔다(2026-08-28) ★
# PRECIP_FULL_MM=100 은 '최근 14일 누적강수 100mm 면 강수 성분 만점'이다.
# 남아시아 몬순(6~9월)에는 그 값을 몇 배로 넘긴다 — 즉 네팔의 강수 성분은
# 우기 내내 1.0 에 붙박여 **정보량이 0 이 된다.** 홍수 같은 '평년 대비 이례적
# 폭우'를 잡으려면 절대량이 아니라 평년 대비 편차(anomaly)를 봐야 하는데,
# 이 모듈은 아직 절대량만 본다. 좌표를 넣는 것으로 그 문제는 풀리지 않는다.

# Aedes/뎅기 전파의 기온 창 ~18–34°C, 최적 ~29°C (Mordecai et al. 2017).
VECTOR_T_MIN, VECTOR_T_OPT, VECTOR_T_MAX = 18.0, 29.0, 34.0

# spillover_pressure 정책 가중치(실증 보정 아님 — weights_calibrated=False로 명시).
W_VECTOR, W_HEAT, W_PRECIP = 0.5, 0.25, 0.25
HEAT_TREND_FULL_C = 3.0     # 최근 단기 +3°C 온난화면 열 성분 만점
PRECIP_FULL_MM = 100.0      # 최근 14일 누적강수 100mm면 강수 성분 만점(고인물=번식지 프록시)


def vector_suitability(temp_c: float) -> float:
    """기온 1점의 매개체(Aedes) 적합도 0~1. 삼각형 곡선: 18°C 미만·34°C 초과는 0,
    29°C에서 1. 실제 모기 개체수가 아니라 기온 기반 프록시임을 유의."""
    if temp_c <= VECTOR_T_MIN or temp_c >= VECTOR_T_MAX:
        return 0.0
    if temp_c <= VECTOR_T_OPT:
        return round((temp_c - VECTOR_T_MIN) / (VECTOR_T_OPT - VECTOR_T_MIN), 3)
    return round((VECTOR_T_MAX - temp_c) / (VECTOR_T_MAX - VECTOR_T_OPT), 3)


def fetch_climate(lat: float, lng: float) -> dict | None:
    """Open-Meteo에서 최근 일별 최고기온·강수 조회. 실패 시 None.
    past_days로 과거를 받아 '최근 7일 vs 그 이전' 단기 온난화 추세를 계산한다."""
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat, "longitude": lng,
                "daily": "temperature_2m_max,precipitation_sum",
                "past_days": 92, "forecast_days": 1, "timezone": "auto",
            },
            headers=USER_AGENT, timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            _record_failure(f"HTTP {resp.status_code}")
            return None
        daily = resp.json().get("daily") or {}
        temps = [t for t in (daily.get("temperature_2m_max") or []) if t is not None]
        precip = [p for p in (daily.get("precipitation_sum") or []) if p is not None]
        if len(temps) < 14:
            _record_failure("표본 부족(일 14개 미만)")
            return None
        return {"temps": temps, "precip": precip}
    except Exception as e:
        # 어떤 오류(네트워크·파싱·예상외)든 기후 층 전체를 멈추면 안 됨 — None으로
        # 흡수하면 호출부가 data_available=False로 정직하게 표시한다. 사유는 따로 센다.
        _record_failure(type(e).__name__)
        return None


def _spillover_pressure(vector: float, heat_trend: float, precip_14d: float) -> float:
    heat_c = max(0.0, min(heat_trend / HEAT_TREND_FULL_C, 1.0))
    precip_c = max(0.0, min(precip_14d / PRECIP_FULL_MM, 1.0))
    return round(100 * (W_VECTOR * vector + W_HEAT * heat_c + W_PRECIP * precip_c), 1)


def compute_country_climate(country_id: str) -> dict:
    """단일 Tier-1 국가의 기후 선행지표. 좌표 없으면 KeyError,
    데이터 조회 실패 시 data_available=False로 정직하게 표시."""
    if country_id not in COUNTRY_COORDS:
        raise KeyError(country_id)
    lat, lng = COUNTRY_COORDS[country_id]

    raw = fetch_climate(lat, lng)
    if raw is None:
        return {
            "country": country_id,
            "data_available": False,
            "reason": "Open-Meteo 조회 실패(네트워크·정책 차단 등) — 값 없음",
            "is_leading_indicator": True,
            "measured": False,
        }

    temps = raw["temps"]
    recent = temps[-7:]
    prior = temps[:-7]
    mean_recent_temp = round(statistics.mean(recent), 1)
    heat_trend = round(mean_recent_temp - statistics.mean(prior), 1) if prior else 0.0
    precip_14d = round(sum(raw["precip"][-14:]), 1) if raw["precip"] else 0.0
    vector = vector_suitability(mean_recent_temp)
    pressure = _spillover_pressure(vector, heat_trend, precip_14d)

    return {
        "country": country_id,
        "data_available": True,
        "mean_recent_temp_c": mean_recent_temp,
        "heat_trend_c": heat_trend,          # 최근7일 - 그 이전 평균(단기 온난화, 기후 정상값 대비 아님)
        "precip_recent_14d_mm": precip_14d,
        "vector_suitability": vector,        # 기온 기반 매개체 적합도 프록시(0~1)
        "spillover_pressure": pressure,      # 발병에 선행할 수 있는 환경 압력(0~100, 모델 추정)
        "is_leading_indicator": True,
        "measured": False,
        "weights_calibrated": False,
        "method": "temp_vector_precip_v1",
    }


def climate_result_usable(result: dict | None) -> bool:
    """이 결과를 6시간 동안 답으로 써도 되는가 (2026-11-19).

    **자료의 성질로만 판정한다** — 나라 하나라도 기상 자료가 들어왔으면 쓸 수 있다.
    전부 `data_available: False` 면 이 주기엔 아무것도 못 받은 것이고, 그걸 6시간 쥐고
    있으면 한도가 풀려도 회복하지 않는다(#124 의 `polar_weather_ok` 와 같은 원칙:
    판정이 서식이나 문자열을 만드는 일에 의존하면 안 된다).

    나라 목록이 비어 있으면 **쓸 수 없다고 본다** — 그건 자료가 아니라 배선 문제이고,
    짧은 ttl 로 다음 주기에 다시 보는 쪽이 조용히 빈 답을 6시간 주는 것보다 낫다.
    """
    if not isinstance(result, dict):
        return False
    countries = result.get("countries")
    if not isinstance(countries, list) or not countries:
        return False
    return any(isinstance(c, dict) and c.get("data_available") for c in countries)


def climate_signals_all() -> dict:
    """Tier-1 전 국가의 기후 선행지표. 발병 뒤가 아니라 '앞'을 보는 층."""
    countries = []
    for cid in COUNTRY_COORDS:
        try:
            countries.append(compute_country_climate(cid))
        except KeyError:
            continue
    available = [c for c in countries if c.get("data_available")]
    available.sort(key=lambda c: -c.get("spillover_pressure", 0))
    unavailable = [c for c in countries if not c.get("data_available")]

    return {
        "countries": available + unavailable,
        "note": "spillover_pressure는 발병 위험 측정치가 아니라 '발병에 선행할 수 있는 환경 압력'의 "
                "모델 추정(vector_suitability는 기온 프록시, 모기 개체수 아님).",
        "disclaimer": "기후는 벡터매개 감염병의 뚜렷한 선행 신호지만, 신종 코로나류 스필오버의 1순위 "
                      "동인은 토지이용 변화(삼림파괴)임. 삼림파괴 지표는 이 층에 아직 미구현(Global Forest "
                      "Watch 연동 필요) — 지어내지 않고 정직하게 남김.",
        "data_source": "Open-Meteo (무료·키 불필요)",
    }

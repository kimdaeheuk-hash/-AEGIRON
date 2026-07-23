"""토지이용·벌목 선행지표 — 인수인계서 확장(㉜).

앞서 정직하게 밝혔듯 신종 코로나류 스필오버의 1순위 동인은 기후가 아니라
토지이용 변화(삼림파괴)다 — 인간이 숲을 밀고 들어가면서 야생동물 안에만
있던 병원체와 접촉하게 된다. 이 층은 그 '삼림파괴 압력'을 선행 신호로 잡는다.

데이터: NASA FIRMS(활성 화재/열이상 탐지, 위성 관측). 열대지역의 화재는
벌목·화전(land-clearing)의 강력한 프록시다(Amazon·Congo·동남아 등 스필오버
핫스팟이 곧 화전 지역). FIRMS는 국가별 최근 화재 탐지 수를 단순 CSV로 준다.

★ 정직성 경계선 ★
- 화재 탐지 수(fire_count)는 위성이 실제로 관측한 값이다(measured=True).
- 그러나 '삼림파괴'는 화재로부터 추론한 프록시다 — 모든 화재가 벌목은 아님
  (자연산불·농경지 소각 포함). is_proxy_for_deforestation=True로 명시한다.
  직접 산림손실 측정(GFW GLAD 위성 알림)은 별도 연동이 필요 — 다음 단계.
- land_clearing_pressure는 화재 수를 정규화한 '토지이용 압력' 추정이며 발병
  위험 측정치가 아니다(is_leading_indicator=True).
- FIRMS_MAP_KEY(무료)가 없으면 data_available=False로 정직하게 표시(조용한
  실패 아님). 샌드박스는 외부 API 정책 차단이라 라이브 검증 불가 — mock
  단위테스트, Railway 운영환경에서 실제 수집.
"""
from __future__ import annotations
import math
import os

import requests

USER_AGENT = {"User-Agent": "EpiWeather-Forest/1.0 (epiweather.kr)"}
TIMEOUT = 25
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"
FIRMS_SOURCE = "VIIRS_SNPP_NRT"   # VIIRS 근실시간 열이상
DEFAULT_DAY_RANGE = 7

# 주 7일 기준 화재 탐지 수 정규화 상한(로그 스케일). 열대 화전 성수기 대국
# (브라질·인니 등)이 수천 건대라 여유를 둔 값 — land_clearing_pressure 산출용.
FIRE_REF_MAX = 5000.0

# country_risk.COUNTRIES(Tier-1) ISO3와 FIRMS 국가코드 매핑. FIRMS는 대체로
# ISO3와 동일한 3글자 코드를 쓴다 — 홍콩(HKG)은 FIRMS 국가목록에 없어 제외.
FIRMS_COUNTRY_CODES = {
    "COD": "COD", "UGA": "UGA", "SAU": "SAU", "THA": "THA", "KOR": "KOR",
    "JPN": "JPN", "BRA": "BRA", "USA": "USA", "NGA": "NGA", "ETH": "ETH",
    "YEM": "YEM", "MDG": "MDG", "PNG": "PNG",
}


def fetch_fire_count(country_code: str, map_key: str, day_range: int = DEFAULT_DAY_RANGE) -> int | None:
    """FIRMS에서 해당 국가의 최근 day_range일 화재 탐지 수 반환. 실패 시 None.
    응답은 CSV(첫 줄 헤더) — 데이터 행 수를 센다."""
    url = f"{FIRMS_BASE}/{map_key}/{FIRMS_SOURCE}/{country_code}/{day_range}"
    try:
        resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        text = resp.text.strip()
        if not text:
            return 0
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return 0
        header = lines[0].lower()
        # CSV 헤더 검증(잘못된 키·에러 메시지 응답 방어)
        if "latitude" not in header and "country_id" not in header:
            return None
        return max(0, len(lines) - 1)  # 헤더 제외한 데이터 행 수
    except Exception:
        return None


def _pressure_from_count(count: int) -> float:
    """화재 수 → 0~100 토지이용 압력(로그 정규화). 화재 수는 국가·계절 편차가
    커서 로그 스케일로 완만하게 매핑한다."""
    if count <= 0:
        return 0.0
    return round(min(math.log10(count + 1) / math.log10(FIRE_REF_MAX + 1), 1.0) * 100, 1)


def compute_country_land(country_id: str, map_key: str | None = None,
                         day_range: int = DEFAULT_DAY_RANGE) -> dict:
    """단일 Tier-1 국가의 토지이용(벌목) 선행지표. 좌표/코드 없으면 KeyError,
    키 없거나 조회 실패 시 data_available=False로 정직하게 표시."""
    if country_id not in FIRMS_COUNTRY_CODES:
        raise KeyError(country_id)
    map_key = map_key or os.environ.get("FIRMS_MAP_KEY")
    if not map_key:
        return {
            "country": country_id, "data_available": False,
            "reason": "FIRMS_MAP_KEY 미설정 — 무료 발급 필요(firms.modaps.eosdis.nasa.gov/api/map_key)",
            "is_leading_indicator": True,
        }

    count = fetch_fire_count(FIRMS_COUNTRY_CODES[country_id], map_key, day_range)
    if count is None:
        return {
            "country": country_id, "data_available": False,
            "reason": "FIRMS 조회 실패(네트워크·정책 차단·잘못된 키 등) — 값 없음",
            "is_leading_indicator": True,
        }

    return {
        "country": country_id,
        "data_available": True,
        "fire_count_recent": count,                 # 위성 실제 관측 화재 수(day_range일)
        "day_range": day_range,
        "land_clearing_pressure": _pressure_from_count(count),  # 0~100 추정 프록시
        "fire_detections_measured": True,           # 화재 자체는 실측
        "is_proxy_for_deforestation": True,         # 벌목 여부는 화재로부터 추론(프록시)
        "is_leading_indicator": True,
        "method": "firms_viirs_fire_count_v1",
    }


def land_signals_all(day_range: int = DEFAULT_DAY_RANGE) -> dict:
    """Tier-1 전 국가의 토지이용 선행지표. 발병 '앞'을 보는 층(㉛ 기후와 짝)."""
    map_key = os.environ.get("FIRMS_MAP_KEY")
    countries = []
    for cid in FIRMS_COUNTRY_CODES:
        try:
            countries.append(compute_country_land(cid, map_key=map_key, day_range=day_range))
        except KeyError:
            continue
    available = [c for c in countries if c.get("data_available")]
    available.sort(key=lambda c: -c.get("land_clearing_pressure", 0))
    unavailable = [c for c in countries if not c.get("data_available")]

    return {
        "countries": available + unavailable,
        "note": "fire_count_recent는 위성 실측 화재 수. land_clearing_pressure는 이를 정규화한 "
                "'토지이용 압력' 추정으로, 발병 위험 측정치가 아니라 스필오버 선행 신호 프록시.",
        "disclaimer": "화재는 벌목·화전의 강력한 프록시지만 모든 화재가 벌목은 아님(자연산불·농경지 "
                      "소각 포함). 직접 산림손실 측정(GFW GLAD 위성 알림)은 별도 연동 필요 — 다음 단계.",
        "data_source": "NASA FIRMS VIIRS (무료, FIRMS_MAP_KEY 필요)",
        "configured": bool(map_key),
    }

"""극지 기준선 — "지금 뜨겁다" 를 "평소보다 뜨겁다" 로 바꾼다 (2026-09-01).

## 왜 만들었나

캡틴 지적: *"기온이 점점 상승해~ 이런 일들이 점점 일어날 듯한데…"*

맞는 말인데, **우리는 그걸 보여줄 수 없었다.** 극지 관찰층은 지금 이 순간의
해빙일과 기온 추세만 낸다. 그래서 브리핑에 이렇게 나갔다:

    시베리아 야말 해빙 30일 · 기온추세 -9.1℃ · 압력 60.0

읽는 사람은 이게 많은 건지 적은 건지 알 수 없다. 30일이 원래 그런 건지
이례적인 건지가 빠져 있다. **절대값은 맥락 없이는 아무 말도 하지 않는다.**

그리고 "기온이 오르고 있다" 는 지금까지 **남의 연구를 인용**하는 말이었다.
우리가 잰 것이 아니었다.

## 무엇을 하나

Open-Meteo 과거 재분석(archive-api)에서 같은 지점 10년치를 받아, **같은 달**의
평년값과 올해를 비교한다. 무료이고 키가 필요 없다 — 실측 확인(2026-09-01).

    시베리아 야말 8월    2016년 17.3℃ → 2026년 18.5℃
    (2016년은 야말 탄저가 폭염에 드러난 해다)

## ★ 같은 달끼리만 비교한다 ★

극지는 계절 진폭이 크다. 8월과 12월을 섞으면 평균이 아무 뜻도 없어진다.
그래서 오늘이 9월이면 **과거 10년의 9월들**과만 견준다.

## ★ 이건 기후 연구가 아니다 ★

10년은 기후 추세를 말하기엔 짧다(세계기상기구 기준은 30년). 여기서 내는 것은
**"지금이 최근 10년의 같은 달에 비해 어디쯤인가"** 이지 온난화 속도가 아니다.
`is_climate_trend=False` 로 항상 명시한다.

편차가 크다고 발병 위험이 큰 것도 아니다. 이 층은 경보가 아니라 관찰이고,
기준선은 **읽는 사람이 숫자를 해석할 수 있게** 하는 재료다.
"""
from __future__ import annotations

import datetime as dt
import statistics

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
BASELINE_YEARS = 10
TIMEOUT = 45

# 재분석 자료는 며칠 지연된다. 끝 날짜를 오늘로 잡으면 마지막 며칠이 비는데,
# 그 자체는 정상이므로 실패로 보지 않는다.
ARCHIVE_LAG_DAYS = 5


def _fetch_daily_max(lat: float, lng: float, start: dt.date, end: dt.date) -> list[tuple[str, float]]:
    """(날짜, 일최고기온) 목록. 값이 빈 날은 버린다 — 0 으로 채우지 않는다."""
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat, "longitude": lng,
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "daily": "temperature_2m_max", "timezone": "UTC",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    daily = (resp.json() or {}).get("daily") or {}
    times, temps = daily.get("time") or [], daily.get("temperature_2m_max") or []
    return [(d, t) for d, t in zip(times, temps) if t is not None]


def month_baseline(lat: float, lng: float, today: dt.date | None = None) -> dict:
    """같은 달 기준선. 자료가 모자라면 **모른다고 말한다.**

    반환의 `available` 이 False 면 나머지 값을 쓰지 말 것. 예전 이 저장소의
    사고들이 전부 "값이 없는데 그럴듯한 기본값을 골라서" 생긴 것이다.
    """
    today = today or dt.date.today()
    end = today - dt.timedelta(days=ARCHIVE_LAG_DAYS)
    start = end.replace(year=end.year - BASELINE_YEARS)
    # ★ 기준 달은 '오늘' 이 아니라 '자료가 있는 마지막 달' 이다 ★
    # 재분석 자료는 며칠 지연된다. 매달 1~5일에 today.month 를 쓰면 그 달
    # 자료가 아직 하루도 없어서 늘 "표본 부족" 이 된다 — 실제로 9월 1일에
    # 그렇게 나왔다. 방금 끝난 달과 비교하는 편이 뜻도 더 분명하다.
    month = end.month
    ref_year = end.year

    try:
        rows = _fetch_daily_max(lat, lng, start, end)
    except Exception as exc:                      # noqa: BLE001 — 사유를 들고 간다
        return {
            "available": False,
            "reason": f"과거 자료 조회 실패: {type(exc).__name__}",
            "is_climate_trend": False,
        }

    by_year: dict[int, list[float]] = {}
    for day, temp in rows:
        year, mon = int(day[:4]), int(day[5:7])
        if mon == month:
            by_year.setdefault(year, []).append(temp)

    current = by_year.pop(ref_year, [])
    past_years = sorted(by_year)
    past = [v for y in past_years for v in by_year[y]]

    if len(current) < 3 or len(past) < 30 or len(past_years) < 3:
        # 3일치로 평년 대비를 말하면 그건 측정이 아니라 우연이다.
        return {
            "available": False,
            "reason": (f"표본 부족 — 올해 {len(current)}일 · "
                       f"과거 {len(past_years)}개년 {len(past)}일"),
            "is_climate_trend": False,
        }

    mean_past = statistics.fmean(past)
    mean_now = statistics.fmean(current)
    thaw_past = sum(1 for v in past if v > 0) / len(past_years)
    thaw_now = sum(1 for v in current if v > 0)

    return {
        "available": True,
        "month": month,
        "baseline_years": len(past_years),
        "mean_max_c_baseline": round(mean_past, 1),
        "mean_max_c_current": round(mean_now, 1),
        "anomaly_c": round(mean_now - mean_past, 1),
        # 해빙일은 '월 평균 며칠' 로 낸다. 이번 달이 아직 안 끝났으면 현재까지의
        # 일수이므로 과거 월 전체와 직접 비교하면 안 된다 — 그래서 partial 을 붙인다.
        "thaw_days_baseline": round(thaw_past, 1),
        "thaw_days_current": thaw_now,
        "current_days_counted": len(current),
        # 그 달이 끝났는가. 안 끝났으면 과거 '월 전체' 와 일수를 직접 견주면 안 된다.
        "month_incomplete": end.day < 28,
        "reference_period": f"{ref_year}-{month:02d}",
        # ★ 항상 붙인다 ★
        "is_climate_trend": False,
        "note": (
            f"최근 {len(past_years)}개년 같은 달({month}월) 평균 대비다. "
            "기후 추세가 아니다 — 세계기상기구의 평년 기준은 30년이고 여기는 "
            "10년이며, 편차가 크다고 발병 위험이 큰 것도 아니다. "
            "숫자를 해석할 맥락을 주기 위한 값이다."
        ),
    }


def describe(anomaly_c: float | None, lang: str = "ko") -> str | None:
    """편차를 사람 말로. 모르면 None — 없는 말을 만들지 않는다."""
    if anomaly_c is None:
        return None
    warmer = {"ko": "평년보다 {v:.1f}℃ 높습니다",
              "en": "{v:.1f}℃ above the {n}-year mean",
              "fr": "{v:.1f}℃ au-dessus de la moyenne"}
    cooler = {"ko": "평년보다 {v:.1f}℃ 낮습니다",
              "en": "{v:.1f}℃ below the {n}-year mean",
              "fr": "{v:.1f}℃ en dessous de la moyenne"}
    same = {"ko": "평년과 비슷합니다", "en": "close to the mean",
            "fr": "proche de la moyenne"}
    if abs(anomaly_c) < 0.5:
        return same.get(lang, same["ko"])
    table = warmer if anomaly_c > 0 else cooler
    return table.get(lang, table["ko"]).format(v=abs(anomaly_c), n=BASELINE_YEARS)

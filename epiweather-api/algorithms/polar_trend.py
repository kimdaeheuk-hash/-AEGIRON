"""극지 추세 — "올해가 더웠다" 와 "몇 년째 오르고 있다" 를 가른다 (2026-09-01).

## 왜 만들었나

기준선(`polar_baseline.py`)을 만들자 캡틴이 이렇게 읽었다:
*"10년 동안 온도가 거의 2%나 올랐어!"*

**그건 기준선이 말하는 것이 아니다.** 기준선은 "2026년 8월이 최근 10년 8월
평균보다 3.4℃ 높다" 이다. 한 달이 유난히 더웠다는 뜻이지, 10년에 걸쳐 그만큼
올랐다는 뜻이 아니다. 한 해가 튀는 것은 추세가 아니라 변동일 수 있다.

숫자 하나가 이렇게 읽히면 그건 숫자를 잘못 낸 것이다. 그래서 **추세를 따로
잰다.**

## 실측이 보여준 것 (2026-09-01, 16개년 8월)

    시베리아 야말        11 14 15 14 12 17 14 15 14 17 18 19 19 16 20 19
                        → 10년당 +4.6℃   ★ 방향이 분명하다
    스발바르             → 10년당 +2.3℃
    그린란드             → 10년당 +1.8℃
    남극 반도            → 10년당 +1.3℃
    캐나다 북극권         → 10년당 +0.5℃   거의 평평
    알래스카 노스슬로프    → 10년당 +0.3℃   거의 평평

**여섯 곳이 다 오르는 것이 아니다.** 알래스카·캐나다는 그해가 튄 것이지
추세가 아니었다. 기준선만 봤으면 여섯 곳 모두 덥다고 읽었을 것이다.

## ★ 이건 여전히 기후 연구가 아니다 ★

16년은 세계기상기구 평년 기준(30년)에 못 미친다. 그리고 단순 최소제곱 직선은
가속·감속을 보지 못하고, 여섯 지점은 지구가 아니다. 여기서 내는 것은
**"이 지점의 이 달이 최근 몇 년간 어느 방향으로 가고 있는가"** 뿐이다.

`is_climate_projection=False` 로 항상 명시하고, 미래를 외삽하지 않는다.
"이 추세면 2050년에 몇 도" 같은 말은 이 파일이 할 수 있는 말이 아니다.
"""
from __future__ import annotations

import datetime as dt
import statistics

from .polar_baseline import ARCHIVE_LAG_DAYS, _fetch_daily_max

TREND_YEARS = 16
MIN_YEARS = 8
MIN_DAYS_PER_MONTH = 25       # 그 달 자료가 이만큼은 있어야 그해를 센다
# 방향을 말해도 되는 최소 기울기. 이보다 작으면 "뚜렷하지 않다" 고 한다 —
# 0.01℃/년 을 상승이라고 부르면 잡음을 추세로 파는 것이다.
FLAT_SLOPE_C_PER_DECADE = 1.0


def _slope_per_decade(years: list[int], values: list[float]) -> float:
    """단순 최소제곱 기울기(℃/10년). 가속은 보지 못한다 — 방향만 본다."""
    mean_x, mean_y = statistics.fmean(years), statistics.fmean(values)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(years, values))
    den = sum((x - mean_x) ** 2 for x in years)
    return (num / den) * 10 if den else 0.0


def month_trend(lat: float, lng: float, today: dt.date | None = None) -> dict:
    """같은 달의 연도별 평균으로 추세. 자료가 모자라면 **모른다고 말한다.**"""
    today = today or dt.date.today()
    end = today - dt.timedelta(days=ARCHIVE_LAG_DAYS)
    start = end.replace(year=end.year - TREND_YEARS)
    month = end.month

    try:
        rows = _fetch_daily_max(lat, lng, start, end)
    except Exception as exc:                       # noqa: BLE001 — 사유를 들고 간다
        return {"available": False,
                "reason": f"과거 자료 조회 실패: {type(exc).__name__}",
                "is_climate_projection": False}

    by_year: dict[int, list[float]] = {}
    for day, temp in rows:
        if int(day[5:7]) == month:
            by_year.setdefault(int(day[:4]), []).append(temp)

    # 자료가 반쯤 있는 해는 뺀다 — 열흘치 평균을 한 해로 세면 추세가 흔들린다.
    years = sorted(y for y, v in by_year.items() if len(v) >= MIN_DAYS_PER_MONTH)
    if len(years) < MIN_YEARS:
        return {"available": False,
                "reason": f"연수 부족 — {len(years)}개년 (최소 {MIN_YEARS})",
                "is_climate_projection": False}

    means = [statistics.fmean(by_year[y]) for y in years]
    slope = _slope_per_decade(years, means)
    flat = abs(slope) < FLAT_SLOPE_C_PER_DECADE

    return {
        "available": True,
        "month": month,
        "years": len(years),
        "first_year": years[0],
        "last_year": years[-1],
        "slope_c_per_decade": round(slope, 1),
        # ★ 방향을 단정할 만큼 기울기가 큰가 ★ 아니면 "뚜렷하지 않다" 이다.
        "direction": "flat" if flat else ("rising" if slope > 0 else "falling"),
        "yearly_means_c": [round(m, 1) for m in means],
        "is_climate_projection": False,
        "note": (
            f"{years[0]}~{years[-1]}년 {month}월 평균의 단순 추세다. "
            "기후 전망이 아니다 — 세계기상기구 평년 기준은 30년이고, 직선 하나는 "
            "가속·감속을 보지 못하며, 여섯 지점은 지구가 아니다. "
            "미래 값을 외삽하지 않는다."
        ),
    }


def describe(trend: dict | None, lang: str = "ko") -> str | None:
    """추세를 사람 말로. 판정 못 했으면 None — 없는 말을 만들지 않는다."""
    if not trend or not trend.get("available"):
        return None
    n, slope = trend["years"], trend["slope_c_per_decade"]
    if trend["direction"] == "flat":
        table = {"ko": "{n}년간 뚜렷한 방향은 없습니다",
                 "en": "no clear direction over {n} years",
                 "fr": "pas de tendance nette sur {n} ans"}
        return table.get(lang, table["ko"]).format(n=n)
    rising = slope > 0
    table = ({"ko": "{n}년간 10년당 {v:+.1f}℃ 로 오르고 있습니다",
              "en": "rising {v:+.1f}℃ per decade over {n} years",
              "fr": "en hausse de {v:+.1f}℃ par décennie sur {n} ans"} if rising else
             {"ko": "{n}년간 10년당 {v:.1f}℃ 로 내려가고 있습니다",
              "en": "falling {v:.1f}℃ per decade over {n} years",
              "fr": "en baisse de {v:.1f}℃ par décennie sur {n} ans"})
    return table.get(lang, table["ko"]).format(n=n, v=slope)

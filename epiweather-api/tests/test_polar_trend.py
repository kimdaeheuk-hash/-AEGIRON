"""추세가 **잡음을 방향으로 팔지 않는지** 지킨다 (2026-09-01).

## 왜 만들었나

기준선을 만들자 캡틴이 이렇게 읽었다:
*"10년 동안 온도가 거의 2%나 올랐어!"*

그건 기준선이 말하는 것이 아니었다. 기준선은 "올해 8월이 최근 10년 8월
평균보다 3.4℃ 높다" 이고, **한 해가 튄 것일 수 있다.**

숫자 하나가 그렇게 읽힌다면 숫자를 잘못 낸 것이다. 그래서 추세를 따로 쟀고,
실측이 그 구분을 증명했다:

    알래스카   평년 대비 +1.9℃ 인데 추세는 10년당 +0.4℃  → 그해가 튄 것
    캐나다     평년 대비 +1.8℃ 인데 추세는 10년당 +0.7℃  → 그해가 튄 것
    스발바르   평년 대비 -2.8℃ 인데 추세는 10년당 +2.2℃  → 올핸 추웠지만 오르는 중
    야말       평년 대비 +3.4℃ · 추세 10년당 +4.9℃      → 둘 다

**기준선만 봤으면 여섯 곳 모두 덥다고 읽었을 것이다.**
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import polar_trend as pt


def _rows(means_by_year: dict[int, float], month: int = 8, days: int = 31):
    return [(f"{y}-{month:02d}-{d:02d}", m)
            for y, m in means_by_year.items() for d in range(1, days + 1)]


def _patched(monkeypatch, rows):
    monkeypatch.setattr(pt, "_fetch_daily_max", lambda *a, **k: rows)


def test_steady_rise_is_reported_as_rising(monkeypatch):
    """분명히 오르면 오른다고 한다."""
    _patched(monkeypatch, _rows({y: 10.0 + (y - 2011) * 0.5 for y in range(2011, 2027)}))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["available"] is True
    assert out["direction"] == "rising"
    assert out["slope_c_per_decade"] == 5.0
    assert out["years"] == 16


def test_noise_is_not_sold_as_a_direction(monkeypatch):
    """★★핵심★★ 0.1℃/10년을 '상승'이라고 부르지 않는다.

    잡음을 추세로 팔면, 아무 데서나 온난화를 발견했다고 말하게 된다.
    """
    _patched(monkeypatch, _rows({y: 10.0 + (y % 3) * 0.05 for y in range(2011, 2027)}))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["direction"] == "flat"
    assert abs(out["slope_c_per_decade"]) < pt.FLAT_SLOPE_C_PER_DECADE
    assert "뚜렷한 방향은 없습니다" in pt.describe(out, "ko")


def test_a_hot_year_alone_is_not_a_trend(monkeypatch):
    """★핵심★ 한 해만 튄 것을 추세로 만들지 않는다.

    실측에서 알래스카가 정확히 이랬다 — 평년 대비 +1.9℃ 인데 추세는 평평했다.
    """
    means = {y: 10.0 for y in range(2011, 2026)}
    means[2026] = 13.0                                    # 올해만 3℃ 높다
    _patched(monkeypatch, _rows(means))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["direction"] == "flat", "한 해 튄 것을 상승으로 읽었다"


def test_falling_is_reported_too(monkeypatch):
    """내려가는 것도 내려간다고 한다 — 상승만 찾지 않는다."""
    _patched(monkeypatch, _rows({y: 10.0 - (y - 2011) * 0.3 for y in range(2011, 2027)}))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["direction"] == "falling"
    assert "내려가고" in pt.describe(out, "ko")


def test_half_empty_years_are_dropped(monkeypatch):
    """열흘치 평균을 한 해로 세면 추세가 흔들린다 — 그런 해는 뺀다."""
    rows = _rows({y: 10.0 for y in range(2011, 2027)})
    rows += [(f"2026-08-{d:02d}", 40.0) for d in range(1, 6)]   # 5일치 극단값
    _patched(monkeypatch, rows)

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    # 2026 은 31일치가 이미 있으므로 정상으로 세어진다. 반대로 자료가
    # 5일뿐인 해는 빠지는지 따로 본다.
    sparse = _rows({y: 10.0 for y in range(2011, 2026)}) + \
        [(f"2026-08-{d:02d}", 40.0) for d in range(1, 6)]
    _patched(monkeypatch, sparse)
    out2 = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert 2026 != out2["last_year"], "5일치뿐인 해를 한 해로 셌다"


def test_too_few_years_says_so(monkeypatch):
    """8개년이 안 되면 추세를 말하지 않는다."""
    _patched(monkeypatch, _rows({y: 10.0 for y in range(2023, 2027)}))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["available"] is False
    assert "연수 부족" in out["reason"]
    assert pt.describe(out, "ko") is None


def test_fetch_failure_is_not_a_flat_trend(monkeypatch):
    """★핵심★ 조회 실패를 '변화 없음' 으로 바꾸지 않는다."""
    def boom(*a, **k):
        raise ConnectionError("nope")
    monkeypatch.setattr(pt, "_fetch_daily_max", boom)

    out = pt.month_trend(66.5, 68.0)

    assert out["available"] is False
    assert "ConnectionError" in out["reason"]
    assert "direction" not in out


def test_never_projects_the_future(monkeypatch):
    """★★핵심★★ 미래를 외삽하지 않는다.

    "이 추세면 2050년에 몇 도" 는 이 파일이 할 수 있는 말이 아니다.
    직선 하나는 가속·감속을 보지 못하고, 여섯 지점은 지구가 아니다.
    """
    _patched(monkeypatch, _rows({y: 10.0 + (y - 2011) * 0.5 for y in range(2011, 2027)}))

    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["is_climate_projection"] is False
    assert "기후 전망이 아니다" in out["note"]
    assert "외삽하지 않는다" in out["note"]
    assert "30년" in out["note"], "왜 짧은지 근거가 빠졌다"
    # 미래 연도를 담은 값이 있으면 안 된다.
    # (is_climate_projection 은 "전망이 아니다" 를 밝히는 키라 이름에 project 가
    #  들어간다 — 그것까지 잡으면 자기 자신을 걸러낸다. 값을 본다.)
    future = dt.date.today().year + 1
    for key, value in out.items():
        assert str(future) not in str(value), f"{key} 에 미래 연도가 들어 있다"
    assert out["last_year"] <= dt.date.today().year


@pytest.mark.parametrize("lang", ["ko", "en", "fr"])
def test_describe_supports_all_brief_languages(lang, monkeypatch):
    """브리핑이 3개 국어로 나간다 — 하나가 비면 그 언어만 문장이 끊긴다."""
    _patched(monkeypatch, _rows({y: 10.0 + (y - 2011) * 0.5 for y in range(2011, 2027)}))
    out = pt.month_trend(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert pt.describe(out, lang)


def test_brief_omits_trend_when_unavailable(monkeypatch):
    """판정 못 하면 브리핑에 아무 말도 안 붙인다."""
    import algorithms.brief_sections as bs

    fake = {
        "regions": [{
            "region": "siberia_yamal", "name": "야말",
            "thaw": {"thaw_days_30d": 30, "heat_trend_c": -9.0,
                     "permafrost_thaw_pressure": 60.0},
            "news": {"sample_titles": []},
            "baseline": {"available": False},
            "trend": {"available": False, "reason": "연수 부족"},
        }],
        "grade": "watch", "note": "", "disclaimer": "", "data_source": "x",
    }
    monkeypatch.setattr("algorithms.polar_signals.polar_watch_all", lambda: fake)

    section = bs.build_polar_section("ko")

    assert "오르고 있습니다" not in section["lead"]
    assert section["rows"][0]["trend_c_per_decade"] is None
    assert section["rows"][0]["trend_direction"] is None

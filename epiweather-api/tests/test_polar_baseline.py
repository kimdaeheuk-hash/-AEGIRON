"""극지 기준선이 **모르는 것을 아는 척하지 않는지** 지킨다 (2026-09-01).

## 왜 만들었나

캡틴 지적: *"기온이 점점 상승해~ 이런 일들이 점점 일어날 듯한데…"*

맞는 말인데 우리는 그걸 보여줄 수 없었다. 극지 층은 지금 이 순간의 값만 냈다:

    시베리아 야말 해빙 30일 · 압력 60.0

읽는 사람은 30일이 많은 건지 알 수 없다. 그리고 "기온이 오르고 있다" 는
**남의 연구를 인용하는 말**이었지 우리가 잰 것이 아니었다.

이제 잰다. 다만 재는 순간 새 위험이 생긴다 — **기후 연구인 척하는 것**이다.
10년은 추세를 말하기엔 짧고(세계기상기구 평년은 30년), 편차가 크다고 발병
위험이 큰 것도 아니다. 이 파일이 그 선을 지킨다.
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import polar_baseline as pb


def _rows(temps_by_year: dict[int, list[float]], month: int = 8) -> list:
    out = []
    for year, temps in temps_by_year.items():
        for i, t in enumerate(temps, start=1):
            out.append((f"{year}-{month:02d}-{i:02d}", t))
    return out


def _patched(monkeypatch, rows):
    monkeypatch.setattr(pb, "_fetch_daily_max", lambda *a, **k: rows)


def test_compares_only_the_same_month(monkeypatch):
    """★핵심★ 다른 달과 섞지 않는다.

    극지는 계절 진폭이 크다. 8월과 12월을 섞으면 평균이 아무 뜻도 없어진다.
    """
    rows = _rows({y: [10.0] * 31 for y in range(2016, 2026)}, month=8)
    rows += [(f"2026-12-{d:02d}", -30.0) for d in range(1, 32)]      # 겨울 — 섞이면 안 된다
    rows += [(f"2026-08-{d:02d}", 14.0) for d in range(1, 29)]
    _patched(monkeypatch, rows)

    out = pb.month_baseline(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["available"] is True
    assert out["month"] == 8
    assert out["mean_max_c_baseline"] == 10.0
    assert out["anomaly_c"] == 4.0                                    # 14 − 10


def test_reference_month_follows_the_data_not_today(monkeypatch):
    """★핵심★ 매달 1~5일에 "표본 부족" 이 되지 않는다.

    재분석 자료는 며칠 지연된다. 기준 달을 today.month 로 잡으면 그 달 자료가
    아직 하루도 없어 늘 판정 불가가 된다 — 실제로 9월 1일에 그렇게 나왔다.
    """
    rows = _rows({y: [10.0] * 31 for y in range(2016, 2026)}, month=8)
    rows += [(f"2026-08-{d:02d}", 12.0) for d in range(1, 27)]
    _patched(monkeypatch, rows)

    out = pb.month_baseline(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["available"] is True
    assert out["reference_period"] == "2026-08"


def test_too_few_samples_says_so_instead_of_guessing(monkeypatch):
    """3일치로 평년 대비를 말하면 측정이 아니라 우연이다."""
    rows = _rows({2026: [12.0, 13.0]}, month=8)
    _patched(monkeypatch, rows)

    out = pb.month_baseline(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["available"] is False
    assert "표본 부족" in out["reason"]
    assert "anomaly_c" not in out, "판정 못 했는데 값을 내놓고 있다"


def test_fetch_failure_is_reported_not_defaulted(monkeypatch):
    """★핵심★ 조회 실패를 '평년과 같음' 으로 바꾸지 않는다."""
    def boom(*a, **k):
        raise TimeoutError("slow")
    monkeypatch.setattr(pb, "_fetch_daily_max", boom)

    out = pb.month_baseline(66.5, 68.0)

    assert out["available"] is False
    assert "TimeoutError" in out["reason"]


def test_never_claims_to_be_a_climate_trend(monkeypatch):
    """★★핵심★★ 10년 비교를 기후 추세로 팔지 않는다.

    세계기상기구 평년 기준은 30년이다. 여기서 내는 것은 "최근 10년의 같은
    달에 비해 어디쯤인가" 이지 온난화 속도가 아니다.
    """
    rows = _rows({y: [10.0] * 31 for y in range(2016, 2027)}, month=8)
    _patched(monkeypatch, rows)

    out = pb.month_baseline(66.5, 68.0, today=dt.date(2026, 9, 1))

    assert out["is_climate_trend"] is False
    assert "기후 추세가 아니다" in out["note"]
    assert "30년" in out["note"], "왜 짧은지 근거가 빠졌다"
    assert "발병 위험이 큰 것도 아니다" in out["note"]


def test_incomplete_month_is_flagged(monkeypatch):
    """달이 안 끝났으면 과거 '월 전체' 일수와 직접 견주면 안 된다."""
    rows = _rows({y: [10.0] * 31 for y in range(2016, 2026)}, month=8)
    rows += [(f"2026-08-{d:02d}", 12.0) for d in range(1, 12)]
    _patched(monkeypatch, rows)

    out = pb.month_baseline(66.5, 68.0, today=dt.date(2026, 8, 16))

    assert out["month_incomplete"] is True
    assert out["current_days_counted"] == 11


@pytest.mark.parametrize("anomaly,expect", [
    (3.4, "높습니다"), (-2.8, "낮습니다"), (0.2, "비슷합니다"), (None, None),
])
def test_describe_is_honest_about_small_differences(anomaly, expect):
    """0.5℃ 미만은 '비슷하다' 고 한다 — 없는 차이를 만들지 않는다."""
    result = pb.describe(anomaly, "ko")

    if expect is None:
        assert result is None
    else:
        assert expect in result


def test_brief_omits_the_phrase_when_unavailable(monkeypatch):
    """자료가 없으면 브리핑에 아무 말도 붙이지 않는다 — 억지로 채우지 않는다."""
    import algorithms.brief_sections as bs

    fake = {
        "regions": [{
            "region": "siberia_yamal", "name": "야말",
            "thaw": {"thaw_days_30d": 30, "heat_trend_c": -9.0,
                     "permafrost_thaw_pressure": 60.0},
            "news": {"sample_titles": []},
            "baseline": {"available": False, "reason": "표본 부족"},
        }],
        "grade": "watch", "note": "", "disclaimer": "", "data_source": "x",
    }
    monkeypatch.setattr("algorithms.polar_signals.polar_watch_all", lambda: fake)

    section = bs.build_polar_section("ko")

    assert "평년" not in section["lead"]
    assert section["rows"][0]["anomaly_c"] is None

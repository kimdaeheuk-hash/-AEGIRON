"""극지 과거 자료 — 과거분은 달마다 한 번, 이번 달분만 날마다 (2026-11-22, 캡틴 "전부 수정해").

11-19~21 실측: Open-Meteo 하루 한도가 매일 11~12시 UTC 에 바닥나 극지 8곳이 하루 13시간
'기상 자료 없음' 이었다(실패 사유 전부 HTTP 429). 기준선(10년)·추세(16년) 요청 구간의 끝이
`오늘 - 지연일` 이라 캐시 키가 매일 바뀌어, 수천 일치 요청 16번이 매일 새로 나갔다.

고정하는 것:
- 같은 달 안에서는 날이 바뀌어도 과거분을 다시 받지 않는다.
- 기준선과 추세가 과거분 한 번을 나눠 쓴다.
- 달이 바뀌면 과거분을 새로 받는다(새 달의 과거가 생겼으니).
- 돌려주는 행은 예전과 같다 — [start, end] 안의 날짜만, 겹침 없이, 날짜순.
- 과거분 캐시는 이틀 정리에 지워지지 않는다(한 달 넘게 산다).
"""
from __future__ import annotations

import datetime as dt
import json

from algorithms import polar_baseline as pb
from algorithms import polar_trend as pt


class _Api:
    """요청한 구간의 모든 날을 돌려주는 가짜 Open-Meteo. 받은 구간을 기록한다."""

    def __init__(self):
        self.windows: list[tuple[str, str]] = []

    def get(self, url, params=None, timeout=None):
        s, e = params["start_date"], params["end_date"]
        self.windows.append((s, e))
        d, end = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
        times, temps = [], []
        while d <= end:
            times.append(d.isoformat())
            temps.append(float(d.day))
            d += dt.timedelta(days=1)
        payload = {"daily": {"time": times, "temperature_2m_max": temps}}

        class _R:
            def raise_for_status(self):
                pass

            def json(self):
                return payload
        return _R()


def _setup(tmp_path, monkeypatch):
    api = _Api()
    monkeypatch.setattr(pb, "_CACHE_FILE", tmp_path / "cache.json")
    monkeypatch.setattr(pb.requests, "get", api.get)
    return api



def test_same_month_next_day_does_not_refetch_the_past(tmp_path, monkeypatch):
    api = _setup(tmp_path, monkeypatch)
    for day in (10, 11, 12):
        end = dt.date(2026, 11, day)
        pb._fetch_daily_max(66.5, 68.0, end.replace(year=2016), end)
    long_windows = [w for w in api.windows if w[0][:4] != "2026"]
    assert len(long_windows) == 1                 # 과거분은 이 달에 한 번
    assert len(api.windows) == 4                  # + 이번 달분 날마다 3번


def test_baseline_and_trend_share_one_past_fetch(tmp_path, monkeypatch):
    api = _setup(tmp_path, monkeypatch)
    end = dt.date(2026, 11, 17)
    pb._fetch_daily_max(66.5, 68.0, end.replace(year=end.year - pb.BASELINE_YEARS), end)
    pb._fetch_daily_max(66.5, 68.0, end.replace(year=end.year - pt.TREND_YEARS), end)
    assert len([w for w in api.windows if w[0][:4] != "2026"]) == 1
    assert len(api.windows) == 2                  # 이번 달분도 같은 키라 한 번


def test_month_rollover_fetches_the_new_past(tmp_path, monkeypatch):
    api = _setup(tmp_path, monkeypatch)
    pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 11, 30), dt.date(2026, 11, 30))
    pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 12, 1), dt.date(2026, 12, 1))
    assert len([w for w in api.windows if w[0][:4] != "2026"]) == 2


def test_rows_are_exactly_the_requested_window_without_overlap(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    start, end = dt.date(2016, 11, 17), dt.date(2026, 11, 17)
    rows = pb._fetch_daily_max(66.5, 68.0, start, end)
    dates = [d for d, _ in rows]
    assert dates[0] == start.isoformat() and dates[-1] == end.isoformat()
    assert len(dates) == len(set(dates)) == (end - start).days + 1   # 빠짐도 겹침도 없다
    assert dates == sorted(dates)


def test_past_segment_survives_the_two_day_prune(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    cache = tmp_path / "cache.json"
    ten_days_ago = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    cache.write_text(json.dumps({
        "old-past": {"at": ten_days_ago, "keep_days": pb._PAST_KEEP_DAYS, "rows": []},
        "old-recent": {"at": ten_days_ago, "keep_days": pb._CACHE_KEEP_DAYS, "rows": []},
    }), encoding="utf-8")
    pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 11, 17), dt.date(2026, 11, 17))
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert "old-past" in payload and "old-recent" not in payload


def test_past_window_covers_the_longest_consumer():
    """추세가 더 긴 구간을 쓰게 바뀌면 나눠 쓰기가 깨진다 — 숫자를 같이 바꿔야 한다."""
    assert pt.TREND_YEARS <= pb.ARCHIVE_PAST_YEARS
    assert pb.BASELINE_YEARS <= pb.ARCHIVE_PAST_YEARS


def test_baseline_result_unchanged_by_the_split(tmp_path, monkeypatch):
    """기준선이 받는 행이 예전 한 번 조회와 같으면 계산값도 같다 — 날짜 범위로 확인."""
    api = _setup(tmp_path, monkeypatch)
    today = dt.date(2026, 11, 22)
    out = pb.month_baseline(66.5, 68.0, today=today)
    assert out["available"] is True
    assert out["baseline_years"] == pb.BASELINE_YEARS     # 16년치를 받아도 10년만 센다
    assert out["reference_period"] == "2026-11"
    assert any(w[0][:4] == "2010" for w in api.windows)

"""재분석 캐시 — 같은 날 같은 구간은 한 번만 받는다 (2026-11-02).

기준선·추세는 10~16년치를 매시간 다시 받았다. 같은 날 안에서는 요청 구간이
똑같으니 두 번째 호출부터는 디스크 캐시를 쓴다. 캐시는 절약용이라 깨지거나
없어도 실시간 조회로 떨어져야지 호출이 죽으면 안 된다.
"""
from __future__ import annotations

import datetime as dt
import json

from algorithms import polar_baseline as pb


class _Resp:
    def __init__(self, times, temps):
        self._payload = {"daily": {"time": times, "temperature_2m_max": temps}}

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _rows(times=("2020-01-01", "2020-01-02"), temps=(1.0, 2.0)):
    return _Resp(list(times), list(temps))


def test_second_call_with_same_window_does_not_hit_the_network(tmp_path, monkeypatch):
    monkeypatch.setattr(pb, "_CACHE_FILE", tmp_path / "cache.json")
    calls = []
    monkeypatch.setattr(pb.requests, "get",
                        lambda *a, **k: (calls.append(1), _rows())[1])
    args = (66.5, 68.0, dt.date(2016, 1, 1), dt.date(2026, 1, 1))
    first = pb._fetch_daily_max(*args)
    second = pb._fetch_daily_max(*args)
    assert first == second == [("2020-01-01", 1.0), ("2020-01-02", 2.0)]
    assert len(calls) == 1


def test_different_window_fetches_again(tmp_path, monkeypatch):
    monkeypatch.setattr(pb, "_CACHE_FILE", tmp_path / "cache.json")
    calls = []
    monkeypatch.setattr(pb.requests, "get",
                        lambda *a, **k: (calls.append(1), _rows())[1])
    pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 1, 1), dt.date(2026, 1, 1))
    pb._fetch_daily_max(70.2, -148.5, dt.date(2016, 1, 1), dt.date(2026, 1, 1))
    assert len(calls) == 2


def test_corrupt_cache_falls_back_to_live_fetch(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    cache.write_text("{깨진", encoding="utf-8")
    monkeypatch.setattr(pb, "_CACHE_FILE", cache)
    monkeypatch.setattr(pb.requests, "get", lambda *a, **k: _rows())
    assert pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 1, 1),
                               dt.date(2026, 1, 1)) != []


def test_entries_older_than_two_days_are_pruned(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    old = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    cache.write_text(json.dumps({"stale-key": {"at": old, "rows": []}}),
                     encoding="utf-8")
    monkeypatch.setattr(pb, "_CACHE_FILE", cache)
    monkeypatch.setattr(pb.requests, "get", lambda *a, **k: _rows())
    pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 1, 1), dt.date(2026, 1, 1))
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert "stale-key" not in payload and len(payload) == 1


def test_cache_store_failure_does_not_kill_the_call(tmp_path, monkeypatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(pb, "_CACHE_FILE", blocker / "cache.json")  # 부모가 파일이라 저장 불가
    monkeypatch.setattr(pb.requests, "get", lambda *a, **k: _rows())
    assert pb._fetch_daily_max(66.5, 68.0, dt.date(2016, 1, 1),
                               dt.date(2026, 1, 1)) != []

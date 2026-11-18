"""Open-Meteo 무료 하루 한도 소진 (2026-11-18, 캡틴 "고쳐").

11-15~17 사흘 내리 극지·기후가 낮에 비고 UTC 자정 직후 풀렸다. 같은 자료를 여러 번 받았다:
수집기(극지) + 매시 관측값 저장(극지·기후, 30분 캐시라 매번 만료) + API 방문.

- 수집기가 계산한 극지 결과를 응답 캐시에 넣는다 → 관측값 저장·API 는 그 값을 쓴다.
- 기후는 일 단위 값이라 6시간 캐시. 오지 전체 목록도 같은 6시간.
- fetch_climate 의 실패 사유를 센다(계약은 그대로 None) → 수집기가 한 줄로 찍는다.
"""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import collector
from algorithms import climate_signals, polar_signals, response_cache

MAIN = Path(__file__).resolve().parents[1] / "main.py"


class _Resp:
    def __init__(self, status: int, body: dict | None = None):
        self.status_code = status
        self._body = body or {}

    def json(self):
        return self._body


def test_put_makes_swr_serve_without_recomputing():
    response_cache.clear()
    response_cache.put("polar-watch", {"regions": [1]})

    def builder():
        raise AssertionError("저장본이 신선한데 다시 계산했다 — Open-Meteo 를 또 부른다")

    out = response_cache.swr("polar-watch", polar_signals.POLAR_CACHE_TTL_S, builder)
    assert out["regions"] == [1]
    assert out["response_cache"]["stale"] is False
    response_cache.clear()


def test_ttls_cover_the_hourly_cycle_and_daily_climate():
    assert polar_signals.POLAR_CACHE_TTL_S > 3600       # 수집 간격(1시간)보다 길어야 방문자가 안 두드린다
    assert climate_signals.CLIMATE_CACHE_TTL_S >= 6 * 3600


def test_fetch_failure_reasons_are_counted_without_changing_the_contract():
    climate_signals.pop_failure_reasons()
    with patch("algorithms.climate_signals.requests.get", return_value=_Resp(429)):
        assert climate_signals.fetch_climate(0, 0) is None          # 계약: 실패는 None
        assert climate_signals.fetch_climate(1, 1) is None
    with patch("algorithms.climate_signals.requests.get", side_effect=TimeoutError("slow")):
        assert climate_signals.fetch_climate(2, 2) is None
    with patch("algorithms.climate_signals.requests.get",
               return_value=_Resp(200, {"daily": {"temperature_2m_max": [1.0] * 3}})):
        assert climate_signals.fetch_climate(3, 3) is None

    reasons = climate_signals.pop_failure_reasons()
    assert reasons == {"HTTP 429": 2, "TimeoutError": 1, "표본 부족(일 14개 미만)": 1}
    assert climate_signals.pop_failure_reasons() == {}                 # 비우고 돌려준다

    line = climate_signals.failure_reasons_line(reasons)
    assert line.index("HTTP 429×2") < line.index("TimeoutError×1")   # 많은 것부터
    assert climate_signals.failure_reasons_line({}) is None


def test_success_records_no_failure():
    climate_signals.pop_failure_reasons()
    body = {"daily": {"temperature_2m_max": [10.0] * 30, "precipitation_sum": [0.0] * 30}}
    with patch("algorithms.climate_signals.requests.get", return_value=_Resp(200, body)):
        assert climate_signals.fetch_climate(0, 0) is not None
    assert climate_signals.pop_failure_reasons() == {}


def test_collector_shares_its_polar_result_and_logs_reasons():
    """배선 고정 — 만들어만 두고 안 부르는 일이 이 리포에서 반복됐다."""
    src = inspect.getsource(collector.collect_free_sources)
    block = src[src.index("극지 관찰층"):src.index("현지어 위키 신호")]
    code = "\n".join(line for line in block.splitlines() if not line.lstrip().startswith("#"))
    # 수집이 성공한 갈래(else)에서, 판정·서식보다 먼저 캐시에 넣는다
    assert code.index("response_cache.put(POLAR_CACHE_KEY, pw)") < code.index("polar_weather_ok")
    assert code.index("pw = polar_watch_all()") < code.index("response_cache.put(POLAR_CACHE_KEY, pw)")
    # 실패 사유를 주기마다 비워 가며 찍는다
    assert "pop_failure_reasons()" in code and "failure_reasons_line" in code


def test_main_uses_the_shared_keys_and_ttls():
    src = MAIN.read_text(encoding="utf-8")
    assert 'swr("polar-watch", 1800' not in src
    assert 'swr("climate-signals", 1800' not in src
    assert src.count("swr(POLAR_CACHE_KEY, POLAR_CACHE_TTL_S, polar_watch_all)") == 2      # 관측값 저장 + API
    assert src.count("swr(CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S, climate_signals_all)") == 2
    assert 'swr("remote-watch:all", CLIMATE_CACHE_TTL_S, assess_all)' in src

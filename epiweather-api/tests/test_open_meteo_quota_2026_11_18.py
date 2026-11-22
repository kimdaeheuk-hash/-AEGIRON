"""Open-Meteo 무료 하루 한도 소진 (2026-11-18, 캡틴 "고쳐").

11-15~17 사흘 내리 극지·기후가 낮에 비고 UTC 자정 직후 풀렸다. 같은 자료를 여러 번 받았다:
수집기(극지) + 매시 관측값 저장(극지·기후, 30분 캐시라 매번 만료) + API 방문.

- 수집기가 계산한 극지 결과를 응답 캐시에 넣는다 → 관측값 저장·API 는 그 값을 쓴다.
- 기후는 일 단위 값이라 6시간 캐시. 오지 전체 목록도 같은 6시간.
- fetch_climate 의 실패 사유를 센다(계약은 그대로 None) → 수집기가 한 줄로 찍는다.
"""
from __future__ import annotations

import ast
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


def test_polar_ttl_covers_the_hourly_cycle():
    assert polar_signals.POLAR_CACHE_TTL_S > 3600       # 수집 간격(1시간)보다 길어야 방문자가 안 두드린다


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
    block = src[src.index("극지 관찰층"):src.index("헤임달: 공개 시퀀스")]
    code = "\n".join(line for line in block.splitlines() if not line.lstrip().startswith("#"))
    # 수집이 성공한 갈래(else)에서, 판정·서식보다 먼저 캐시에 넣는다
    assert code.index("response_cache.put(POLAR_CACHE_KEY, pw)") < code.index("polar_weather_ok")
    assert code.index("pw = polar_watch_all()") < code.index("response_cache.put(POLAR_CACHE_KEY, pw)")
    # 실패 사유를 주기마다 비워 가며 찍는다
    assert "pop_failure_reasons()" in code and "failure_reasons_line" in code


def test_main_uses_the_shared_keys_and_ttls():
    """호출부가 공유 키·공유 ttl 을 쓰는가 — 옛 하드코딩 1800 으로 돌아가지 않았는가.

    ★ 2026-11-19: 문자열 비교에서 **AST 비교로 바꿨다.** 원래는 호출문 전체를 글자로
    맞췄는데, 11-19 수리가 같은 호출에 `usable=`·`unusable_ttl=` 을 붙이며 줄을 접자
    계약은 그대로인데 시험이 깨졌다. 단언을 약하게 만드는 대신 **더 강하게** 고쳤다 —
    이제 서식(줄바꿈·따옴표·키워드 인자)에 안 묶이고 `(키, ttl, 빌더)` 세 자리를 구조로 본다.
    (이 저장소 규칙: 문자열 grep 이 아니라 AST 상수/호출을 본다.)
    """
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "swr"
             and len(n.args) >= 3]

    def shape(call: ast.Call) -> tuple[str, str, str]:
        def one(node: ast.expr) -> str:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Constant):
                return repr(node.value)
            return ast.unparse(node)
        return one(call.args[0]), one(call.args[1]), one(call.args[2])

    shapes = [shape(c) for c in calls]

    # 옛 하드코딩(1800초)으로 돌아가지 않았다
    assert ("'polar-watch'", "1800", "polar_watch_all") not in shapes

    # 공유 키 + 공유 ttl + 같은 빌더
    assert shapes.count(("POLAR_CACHE_KEY", "POLAR_CACHE_TTL_S", "polar_watch_all")) == 2   # 관측값 저장 + API
    # (기후·원격감시 엔드포인트는 2026-11-22 개편에서 지웠다)

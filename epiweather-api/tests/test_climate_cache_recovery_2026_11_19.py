"""기후·오지의 '전부 실패한 결과' 가 6시간 캐시를 쥐고 앉던 결함 (2026-11-19).

## 배경 (사고 기록)

11-15~18 나흘 동안 Open-Meteo 하루 한도(HTTP 429)가 낮에 바닥나 극지·기후가 반나절씩
비었다. 11-18 의 수리(#132)가 호출 수를 줄이려고 기후·오지를 **6시간 캐시**에 넣었다.

그런데 `climate_signals_all()` 은 조회가 다 실패해도 **예외를 던지지 않고**
`data_available: False` 를 채운 dict 를 돌려준다. 그래서 응답 캐시의
"예외는 저장하지 않는다" 장치가 이 경우를 못 잡고, **빈 결과가 성공처럼 6시간 저장됐다.**

실측 — 하루 한도가 자정에 풀린 직후(11-19 00:09 UTC):

    🗄 관측 저장: 극지 8(새 8·같음 0) · 기후 15(새 0·같음 15·판정 안 함 15)
                     ↑ 수집기가 매시간 put 해서 살아났다  ↑ 6시간 캐시가 빈 결과를 쥐고 있다

극지는 수집기가 매 주기 `put()` 으로 덮어써서 한 시간 안에 회복했는데, 기후·오지는
**읽을 때만** 계산되므로 캐시가 만료될 때까지 빈 결과가 답이었다. 한도는 풀렸는데
Open-Meteo 를 부르지 않으니 회복할 기회 자체가 없었다.

## 이 시험이 지키는 것

1. 전부 실패한 결과는 **짧은 ttl** 만 살고 다음 주기가 다시 계산한다(회복).
2. 쓸 만한 결과는 **6시간을 그대로** 산다(한도를 다시 태우지 않는다).
3. 배선 — 세 호출부가 판정을 **실제로 넘긴다**(이 저장소의 반복 결함 ②
   '만들어만 두고 아무도 안 부른다' 를 AST 로 못박는다).
"""
from __future__ import annotations

import ast
import pathlib
import time

import pytest

from algorithms import response_cache as rc
from algorithms.climate_signals import (CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S,
                                        CLIMATE_UNUSABLE_TTL_S, climate_result_usable)
from algorithms.remote_area import remote_result_usable

MAIN_PY = pathlib.Path(__file__).resolve().parent.parent / "main.py"

# 11-18~19 에 실제로 돌아온 모양 — 15개국 전부 조회 실패.
ALL_FAILED = {"countries": [{"country": f"C{i}", "data_available": False} for i in range(15)]}
# 회복한 주기의 모양 — 한 곳이라도 자료가 있다.
PARTLY_OK = {"countries": [{"country": "C0", "data_available": True},
                           *({"country": f"C{i}", "data_available": False} for i in range(1, 15))]}


@pytest.fixture(autouse=True)
def _clean_cache():
    rc.clear()
    yield
    rc.clear()


# ───────────────────── 판정기 — 자료의 성질로만 본다 ─────────────────────

@pytest.mark.parametrize("result", [
    ALL_FAILED,                                   # ★ 사고의 입력
    {"countries": []},                            # 나라 목록이 빔 — 배선 문제, 6시간 쥐지 않는다
    {},                                           # countries 키 없음(옛 형태)
    None,                                         # 아예 없음
    {"countries": [{"country": "C0"}]},           # data_available 키 없음
])
def test_unusable_climate_results_are_not_worth_six_hours(result):
    assert climate_result_usable(result) is False


def test_one_country_with_data_is_usable():
    assert climate_result_usable(PARTLY_OK) is True


@pytest.mark.parametrize("result", [
    [{"key": "a", "assessed": False}, {"key": "b", "assessed": False}],   # 한도 소진 시 전 영토
    [], None, {}, [{"key": "a"}],
])
def test_unusable_remote_results_are_not_worth_six_hours(result):
    assert remote_result_usable(result) is False


def test_one_assessed_territory_is_usable():
    assert remote_result_usable([{"key": "a", "assessed": True},
                                 {"key": "b", "assessed": False}]) is True


# ───────────────────── 회복 — 이게 사고의 알맹이다 ─────────────────────

def test_all_failed_result_is_recomputed_next_cycle_and_recovers():
    """★ 11-19 00:09 의 재현 — 한도가 풀리면 다음 주기에 회복해야 한다."""
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return ALL_FAILED if calls["n"] == 1 else PARTLY_OK   # 2회차 = 한도 풀린 뒤

    def read():
        return rc.swr(CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S, builder,
                      usable=climate_result_usable, unusable_ttl=CLIMATE_UNUSABLE_TTL_S)

    first = read()
    assert calls["n"] == 1
    assert [c["data_available"] for c in first["countries"]] == [False] * 15

    # 짧은 ttl 이 달려 있다 — 6시간이 아니다.
    assert rc._STORE[CLIMATE_CACHE_KEY][2] == CLIMATE_UNUSABLE_TTL_S

    # 다음 수집 주기(1시간 뒤). 저장 시각을 뒤로 밀어 시간 경과를 흉내낸다.
    at, value, ttl = rc._STORE[CLIMATE_CACHE_KEY]
    rc._STORE[CLIMATE_CACHE_KEY] = (at - (CLIMATE_UNUSABLE_TTL_S + 1), value, ttl)

    read()                      # 만료 → 저장본을 주고 뒤에서 갱신
    for _ in range(200):        # 배경 갱신을 기다린다
        if calls["n"] >= 2 and rc._STORE[CLIMATE_CACHE_KEY][1] is PARTLY_OK:
            break
        time.sleep(0.01)

    assert calls["n"] >= 2, "한도가 풀렸는데 다시 계산하지 않았다 — 회복 못 한다"
    assert climate_result_usable(rc._STORE[CLIMATE_CACHE_KEY][1])
    # 회복한 값에는 짧은 ttl 이 안 달린다 → 이제 6시간을 산다.
    assert rc._STORE[CLIMATE_CACHE_KEY][2] is None


def test_the_old_behavior_would_have_held_the_empty_result_for_six_hours():
    """옛 동작이 결함이었다는 사실을 고정한다 — 판정을 안 넘기면 빈 결과가 6시간 답이 된다."""
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return ALL_FAILED

    rc.swr(CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S, builder)      # usable= 없이 (= #132 당시)
    assert rc._STORE[CLIMATE_CACHE_KEY][2] is None               # 제 몫의 ttl 이 없다

    at, value, ttl = rc._STORE[CLIMATE_CACHE_KEY]
    rc._STORE[CLIMATE_CACHE_KEY] = (at - (CLIMATE_UNUSABLE_TTL_S + 1), value, ttl)

    rc.swr(CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S, builder)
    time.sleep(0.05)
    assert calls["n"] == 1, "옛 동작은 한 시간이 지나도 다시 계산하지 않는다(= 이 사고)"


def test_usable_result_keeps_the_full_six_hours():
    """회복한 뒤엔 한도를 다시 태우지 않는다 — 쓸 만한 값은 6시간 그대로."""
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return PARTLY_OK

    def read():
        return rc.swr(CLIMATE_CACHE_KEY, CLIMATE_CACHE_TTL_S, builder,
                      usable=climate_result_usable, unusable_ttl=CLIMATE_UNUSABLE_TTL_S)

    read()
    at, value, ttl = rc._STORE[CLIMATE_CACHE_KEY]
    rc._STORE[CLIMATE_CACHE_KEY] = (at - (CLIMATE_UNUSABLE_TTL_S + 1), value, ttl)
    read()                                    # 55분+ 지났어도 6시간 안이라 신선하다
    time.sleep(0.05)
    assert calls["n"] == 1


def test_short_ttl_is_shorter_than_the_collection_interval():
    """다음 수집 주기가 **반드시** 만료를 보게 — 1시간보다 짧아야 한다."""
    assert 0 < CLIMATE_UNUSABLE_TTL_S < 3600
    assert CLIMATE_UNUSABLE_TTL_S < CLIMATE_CACHE_TTL_S


def test_a_broken_predicate_does_not_cause_a_recall_storm():
    """판정기가 터지면 평소 ttl 로 둔다 — 판정 버그가 재호출 폭주로 번지지 않게."""
    def boom(_):
        raise RuntimeError("판정기 버그")

    rc.swr("k", 600, lambda: ALL_FAILED, usable=boom, unusable_ttl=1)
    assert rc._STORE["k"][2] is None


def test_every_writer_stores_the_same_entry_shape():
    """`put`·`seed`·`prewarm` 도 3칸으로 쓴다 — 읽는 쪽이 한 모양만 알면 되게."""
    rc.put("a", {"v": 1})
    rc.seed("b", {"v": 2})
    rc.prewarm("c", lambda: {"v": 3})
    for key in ("a", "b", "c"):
        assert len(rc._STORE[key]) == 3, key
        assert rc._STORE[key][2] is None, key


# ───────────── 배선 — 만들어만 두고 아무도 안 부르는 일을 막는다 ─────────────

def _swr_calls_with_keyword(tree: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "swr"]


def _first_arg_is(call: ast.Call, want: str) -> bool:
    """첫 인자가 이름 `want` 이거나 문자열 리터럴 `want` 인가(따옴표 종류에 안 묶이게)."""
    if not call.args:
        return False
    arg = call.args[0]
    if isinstance(arg, ast.Name):
        return arg.id == want
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value == want
    return False


@pytest.mark.parametrize("cache_key", [
    "CLIMATE_CACHE_KEY",      # 관측값 저장 + /api/climate-signals
    "remote-watch:all",       # 오지 전체
])
def test_main_passes_the_usability_judgement_to_the_cache(cache_key):
    """main.py 의 기후·오지 `swr` 호출이 `usable=`·`unusable_ttl=` 을 **실제로** 넘기는가.

    판정 함수를 만들어 두고 호출부에서 빼먹으면 결함이 조용히 돌아온다 — 그 자리를 막는다.
    """
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    matching = [c for c in _swr_calls_with_keyword(tree) if _first_arg_is(c, cache_key)]

    assert matching, f"{cache_key} 를 쓰는 swr 호출이 main.py 에 없다"
    for call in matching:
        kwargs = {kw.arg for kw in call.keywords}
        assert "usable" in kwargs, f"{cache_key_src}: usable= 이 빠졌다 (줄 {call.lineno})"
        assert "unusable_ttl" in kwargs, f"{cache_key_src}: unusable_ttl= 이 빠졌다 (줄 {call.lineno})"


def test_polar_cache_is_left_alone_on_purpose():
    """극지는 수집기가 매 주기 `put` 으로 덮어써서 한 시간 안에 회복한다 — 안 건드렸다.

    (소킹 규칙: 고장 나지 않으면 코드를 안 건드린다. 11-19 00:07 UTC 에 극지는 스스로
    회복했다 — `극지 8(새 8·같음 0)`. 이 시험은 그 판단을 기록으로 남긴다.)
    """
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    polar = [c for c in _swr_calls_with_keyword(tree) if _first_arg_is(c, "POLAR_CACHE_KEY")]
    assert polar, "극지 swr 호출이 사라졌다"
    for call in polar:
        assert "usable" not in {kw.arg for kw in call.keywords}

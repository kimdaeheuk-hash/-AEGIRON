"""극지 관찰층이 **실제로 돌고 있는지** 지킨다 (2026-09-01).

## 사고

캡틴이 "극지 감시망 돌고 있지?" 라고 물어 확인해 보니 **돌고 있지 않았다.**

    수집기(collector.py)   극지 호출 없음
    소스 헬스              등록 없음

`/api/polar-watch` 를 **부를 때만** 그 자리에서 계산됐다. 즉 기능은 있는데
감시는 하지 않는 상태였다. 결과가 어디에도 쌓이지 않으니 어제 대비 오늘을
비교할 수 없었고 — 동토 해빙은 추세가 핵심인데 매번 그 순간만 봤다 —
Open-Meteo 나 러시아어 뉴스가 막혀도 21개 소스 어디에도 안 잡혔다.

## ★ 왜 하루 한 번이 아니라 매시간인가 ★

처음엔 "동토는 시간 단위로 안 변하니 하루 한 번" 이라고 판단했다가 바꿨다.
소스 헬스는 **매 주기 기록**을 전제로 돈다(record_cycle). 하루 한 번만 돌면
나머지 23주기가 값없음으로 쌓여 **거짓 경보**가 된다.

호출량은 6개 관측지 × (기후+뉴스) = 12건이고 실측 10.6초다. 이미 매시간
179개 현지어 피드를 받고 있으므로 부담이 아니다. 일관성이 미세 최적화보다
중요하다.
"""
from __future__ import annotations

import inspect

import collector


def test_polar_watch_is_a_tracked_source():
    """★핵심★ 수집 대상으로 등록돼 있어야 한다.

    등록이 없으면 죽어도 아무도 모른다 — 이 저장소가 Mobility 245시간·
    GroqWatch 열흘로 배운 것이다.
    """
    assert collector.FREE_SOURCE_HEALTH_KEYS["PolarWatch"] == "polar_watch"


def test_collector_actually_calls_the_polar_layer():
    """등록만 하고 안 부르면 매 주기 값없음으로 쌓여 거짓 경보가 된다."""
    source = inspect.getsource(collector.collect_free_sources)

    assert "polar_watch_all" in source, "수집기가 극지 층을 부르지 않는다"
    assert 'result["polar_watch"]' in source, "결과를 등록 키에 담지 않는다"


def test_polar_failure_is_recorded_not_swallowed():
    """실패를 조용히 넘기지 않는다 — 사유를 남긴다."""
    source = inspect.getsource(collector.collect_free_sources)
    after = source[source.index("polar_watch_all"):]

    assert 'log_error("PolarWatch"' in after, "실패 사유를 기록하지 않는다"
    assert "❌" in after, "실패가 ⏭(소프트 스킵)로 찍히면 점검에서 걸러진다"


def test_polar_stays_a_watch_layer_not_an_alarm():
    """★핵심★ 수집에 넣었다고 경보가 되면 안 된다.

    대부분의 동토 미생물은 사람을 감염시키지 못하고, 이 위험은 토지이용
    동인보다 과대평가되는 경향이 있다(모듈 docstring). 수집하는 이유는
    울리기 위해서가 아니라 **쌓기 위해서**다.
    """
    from algorithms import polar_signals

    doc = polar_signals.__doc__ or ""
    assert "watch_grade" in doc, "관찰 등급이라는 근거가 문서에서 사라졌다"

    # 경보 파이프라인과 섞이지 않아야 한다.
    # ★ 주석에 적힌 것과 실제로 쓰는 것을 구분한다 ★ 이 모듈 docstring 은
    # "classify_tier 와 절대 섞지 않는다" 고 적고 있어서, 단어 등장만 보면
    # 정반대로 읽힌다. import·호출이 있는지를 본다.
    src = inspect.getsource(polar_signals)
    code = chr(10).join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "import classify_tier" not in code
    assert "classify_tier(" not in code, "경보 파이프라인을 실제로 호출한다"

    # 관찰 등급 표시가 결과에 실제로 실려야 한다
    assert "watch_grade" in src


def test_every_region_is_still_watched():
    """관측지가 조용히 줄지 않는다 — 6곳은 설계다."""
    from algorithms.polar_signals import POLAR_REGIONS

    keys = {r[0] for r in POLAR_REGIONS}
    assert keys == {
        "siberia_yamal", "alaska_north", "canada_arctic",
        "greenland", "svalbard", "antarctic_peninsula",
    }

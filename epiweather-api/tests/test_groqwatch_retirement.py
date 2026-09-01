"""GroqWatch 를 NewsWatch 로 교대한 것을 지킨다 (2026-09-01).

## 왜 교대했나

    GroqWatch  최근 24주기 성공률 0.0% · 마지막 성공 2026-08-30 03:00
    NewsWatch  같은 기간 16주기 연속 성공 · 토큰 1,031~1,766

원인은 2026-08-28 에 규명됐고 우리 손 밖이다. GroqWatch 의 프롬프트
3,831~4,993 토큰 중 우리 지시문은 150 남짓이고, 나머지 96% 는 compound-mini 가
서버 쪽에서 붙이는 검색결과다. 질의 축소·재시도·주기 조정이 전부 실패한 이유가
그것이다 — **주입량이 통제 밖**이었다.

NewsWatch 는 검색(구글 뉴스 RSS)과 요약(Cerebras/Groq)을 분리해 **주입량을
우리가 통제한다.** 그게 성공률 차이의 뿌리다.

## ★ 이 파일이 막는 것 ★

죽은 소스가 산 소스의 예산을 먹는 것. 둘은 같은 GROQ_API_KEY 를 쓰는데
(Cerebras 쿼터 소진 상태), GroqWatch 가 매시간 4,000 토큰씩 분당 한도 8,000 에서
태우고 실패했다. 그래서 추적에서 빼는 데 그치지 않고 **호출 자체를 막는다.**
"""
from __future__ import annotations

import inspect

import collector
from algorithms.source_health import RETIRED_SOURCES, is_retired


def test_groqwatch_is_retired_with_a_reason():
    """★핵심★ 은퇴는 이유와 함께 남는다 — 조용히 사라지면 안 된다."""
    assert is_retired("GroqWatch")

    reason = RETIRED_SOURCES["GroqWatch"]
    assert "NewsWatch" in reason, "무엇으로 교대했는지 적혀 있어야 한다"
    assert "0.0%" in reason, "왜 뺐는지 측정값이 있어야 한다"
    assert "되살리려면" in reason, "복구 방법을 남겨야 한다"


def test_newswatch_is_now_a_tracked_source():
    """NewsWatch 가 실험층에서 정식 소스가 됐다.

    실험층일 때는 죽어도 소스 헬스에 안 나타났다. 이제 이 층이 죽으면 보인다.
    """
    assert collector.FREE_SOURCE_HEALTH_KEYS["NewsWatch"] == "news_pulse"
    assert not is_retired("NewsWatch")


def test_retired_source_is_not_even_called():
    """★★핵심★★ 은퇴한 소스는 부르지도 않는다.

    추적에서만 빼면 호출은 계속된다. GroqWatch 의 경우 그게 실제로 해로웠다 —
    NewsWatch 가 같은 GROQ_API_KEY 로 도는데 GroqWatch 가 분당 한도의 절반을
    태우고 실패했다. **죽은 소스가 산 소스의 예산을 먹는다.**
    """
    source = inspect.getsource(collector.collect_free_sources)

    assert 'if is_retired("GroqWatch")' in source, "은퇴 여부를 보지 않고 부르고 있다"
    # 은퇴 검사가 실제 호출보다 먼저 와야 한다 — 뒤에 있으면 이미 부른 뒤다
    assert source.index('is_retired("GroqWatch")') < source.index("fetch_groq_pulse"), (
        "은퇴 검사가 호출 뒤에 있다 — 토큰을 태운 뒤에 거르는 셈이다"
    )


def test_groqwatch_code_still_exists_for_revival():
    """되살릴 수 있어야 한다 — 지운 게 아니라 뺀 것이다.

    Mobility 때 정한 원칙이다. 코드와 엔드포인트는 살려두고 등록만 뺀다.
    RETIRED_SOURCES 에서 한 줄을 지우면 돌아온다.
    """
    from algorithms import groq_watch

    assert hasattr(groq_watch, "fetch_groq_pulse")


def test_retirement_registry_keeps_earlier_entries():
    """새 은퇴가 이전 것을 덮어쓰지 않는다."""
    assert set(RETIRED_SOURCES) >= {"GroqWatch", "Mobility"}
    assert "OpenSky" in RETIRED_SOURCES["Mobility"], "Mobility 사유가 훼손됐다"

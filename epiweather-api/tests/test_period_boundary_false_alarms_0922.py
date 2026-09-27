"""거짓 경보 2건 — 둘 다 '아직 안 나온 기간'을 '보고가 끊긴 것'으로 읽었다.

## 배경 (2026-09-22, 소킹 2일차)

24시간 안에 거짓 경보 두 건이 **캡틴 폰으로** 나갔다.

    ① kdca_weekly_total  최신값 0.0 vs 과거 평균 101.86 → 100점 critical
       09-21 은 월요일이고, 새 역학주간의 집계가 아직 안 올라온 0 이었다.
       수집기는 같은 시각 매시간 정상이었고, 20:01 에 수치가 들어오자
       경보가 스스로 사라졌다.

    ② naver_ebola_ratio 93점 critical · naver_covid_ratio 85점 high
       세 축이 00:00 에 동시에 같은 배율로 무너졌다. 각각 다른 요청인데
       한꺼번에 떨어진 것은 검색이 준 게 아니라 재척도된 것이다.

둘은 같은 고장 하나다 — **부정적 공간 감시가 기간 경계를 못 본다.** #37 이
'수집 주기 > 원천 갱신 주기' 를 증가 쪽(gai·anomaly_engine)에서 막았는데
감소 쪽에는 그 문턱이 없었다.

캡틴 지시(2안): 네이버 축은 부정적 공간에서 빼고, KDCA 는 주기를 인지시킨다.

★ 고치는 자리를 다르게 잡았다 ★ KDCA 는 negative_space 가 아니라 **지표를
만드는 자리**(kdca_anomaly)에서 고친다. 그래야 증가 쪽 엔진도 같은 사실을 본다 —
#37 이 남긴 교훈이 정확히 그것이다("두 엔진이 같은 지표를 두고 다른 말을 하면
그 자체가 고장이다").
"""
from __future__ import annotations

import pytest

from algorithms import kdca_anomaly as ka
from algorithms.negative_space import (
    EXCLUDED_METRICS, RESCALED_METRICS, SEASONAL_METRICS, UNRELIABLE_METRICS,
    check_negative_space,
)


# ── ① KDCA — 아직 발행되지 않은 주는 판정하지 않는다 ────────────────

def test_unpublished_latest_week_is_unknown_not_zero():
    """새 주 칸이 생겼지만 전 질병이 0 → None(판정 안 함). 0 을 돌려주면
    '보고 급감' 으로 읽히고, 그게 09-21 에 실제로 일어난 일이다."""
    kw = {
        "수두": {"2026-W38": 120, "2026-W39": 0},
        "홍역": {"2026-W38": 3, "2026-W39": 0},
    }
    assert ka.notable_latest_total(kw) is None


def test_published_week_with_zero_notable_is_still_an_observation():
    """주는 발행됐고(상재성 질병에 값이 있다) 위험군만 0 → 0.0 은 관측이다.
    이걸 None 으로 만들면 이번엔 반대로 진짜 보고 붕괴를 죽인다."""
    kw = {
        "수두": {"2026-W38": 120, "2026-W39": 110},   # 발행된 증거
        "홍역": {"2026-W38": 3, "2026-W39": 0},        # 위험군은 0
    }
    assert ka.notable_latest_total(kw, notable={"홍역"}) == 0.0


def test_published_week_sums_notable_only():
    """기존 계약 유지 — 상재성 질병은 총합에 안 들어간다."""
    kw = {
        "수두": {"2026-W39": 500},      # 발행 증거이자 상재성(위험군 밖)
        "홍역": {"2026-W39": 30},
        "콜레라": {"2026-W39": 10},
    }
    assert ka.notable_latest_total(kw, notable={"홍역", "콜레라"}) == 40.0


def test_week_is_reported_needs_a_nonzero_somewhere():
    kw = {"수두": {"W1": 0, "W2": 5}, "홍역": {"W1": 0}}
    assert ka.week_is_reported(kw, "W2") is True
    assert ka.week_is_reported(kw, "W1") is False


def test_week_is_reported_tolerates_missing_and_none():
    """질병마다 주 칸이 다 있지는 않다. 없는 칸·None 이 예외를 내면
    그 주 KDCA 판정이 통째로 사라진다(2026-08-13 사고의 모양)."""
    kw = {"수두": {"W2": None}, "홍역": {}, "콜레라": {"W2": 7}}
    assert ka.week_is_reported(kw, "W2") is True
    assert ka.week_is_reported(None, "W2") is False


def test_empty_input_still_unknown():
    assert ka.notable_latest_total(None) is None
    assert ka.notable_latest_total({}) is None
    assert ka.notable_latest_total({"수두": {}}) is None


def test_the_false_critical_cannot_be_reproduced_now():
    """09-21 00:03 을 그대로 재현한다 — 과거 평균 101.86, 새 주는 미발행.

    예전: 최신값 0.0 → 과거 평균의 0.0배 → 100점 critical → 전송됨.
    지금: 최신값이 None 이라 부정적 공간이 판정 자체를 안 한다.
    """
    kw = {
        "수두": {"2026-W37": 100, "2026-W38": 104, "2026-W39": 0},
        "홍역": {"2026-W37": 2, "2026-W38": 1, "2026-W39": 0},
    }
    latest = ka.notable_latest_total(kw)
    assert latest is None
    assert check_negative_space(latest, 101.86)["alert"] is False
    # 그리고 옛 동작(0.0)이 경보였다는 사실도 같이 고정한다 — 판정은 옳았고
    # 틀린 건 입력이었다는 것이 코드에 남아야 한다.
    assert check_negative_space(0.0, 101.86)["alert"] is True


# ── ② 네이버 — 부정적 공간의 대상이 아니다 ──────────────────────────

@pytest.mark.parametrize("metric_id", [
    "naver_flu_ratio", "naver_ebola_ratio", "naver_covid_ratio",
])
def test_naver_axes_are_out_of_negative_space(metric_id):
    assert metric_id in RESCALED_METRICS
    assert metric_id in EXCLUDED_METRICS


def test_excluded_set_is_the_union_of_its_reasons():
    """제외 사유를 하나로 뭉치지 않는다 — 왜 뺐는지가 사라지면 다음 사람이
    되돌릴 수 없다. 스캔은 합집합만 본다."""
    assert EXCLUDED_METRICS == UNRELIABLE_METRICS | SEASONAL_METRICS | RESCALED_METRICS
    assert UNRELIABLE_METRICS and SEASONAL_METRICS and RESCALED_METRICS


def test_naver_axes_are_still_scored_on_the_increase_side():
    """★ 지수는 안 건드린다 ★ 검색 급증은 신고보다 앞서는 실제 조기신호다.
    빼는 건 '감소를 보고 붕괴로 읽는 것' 하나뿐이다."""
    from algorithms.signal_metrics import LAYERS
    registered = {m[0] for cfg in LAYERS.values() for m in cfg["metrics"]}
    for metric_id in RESCALED_METRICS:
        assert metric_id in registered


def test_scan_skips_every_excluded_metric():
    """스캔이 제외 사유를 실제로 읽는지 — 집합만 만들어두고 아무도 안 보면
    이 리포의 단골 실패다('만들어만 두고 아무도 안 부르는 층').

    2026-09-27 에 경로가 한 단계 늘었다: 스캔이 `EXCLUDED_METRICS` 를 직접 보는
    대신 `eligibility()` 를 부르고, 그 함수가 세 집합을 본다(소킹 판정 뒤
    허용목록 도입). 그래서 **양쪽을 다 고정한다** — 원래 계약보다 강하다.
    """
    import ast
    import inspect

    from algorithms import negative_space

    def names_in(fn):
        src = inspect.getsource(fn)
        return {n.id for n in ast.walk(ast.parse(src.strip())) if isinstance(n, ast.Name)}

    assert "eligibility" in names_in(negative_space.scan_negative_space)
    gate = names_in(negative_space.eligibility)
    assert {"UNRELIABLE_METRICS", "SEASONAL_METRICS", "RESCALED_METRICS"} <= gate

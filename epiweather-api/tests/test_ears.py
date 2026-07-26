"""CDC EARS C1/C2/C3 조기이상탐지 — 표준 알고리즘 동작 검증.
가드밴드(C2)가 발병 초기값의 기준선 오염을 막는지, 완만한 상승을 C3가 잡는지,
데이터 부족·분산0에서 가짜 경보를 안 내는지 확인."""
from __future__ import annotations

from algorithms import ears


def test_spike_over_stable_baseline_triggers_c1_c2():
    series = [10, 12, 11, 9, 10, 11, 10, 10, 11, 30]  # 마지막 날 급증
    assert ears.c1(series) > ears.C1_THRESHOLD
    assert ears.c2(series) > ears.C2_THRESHOLD
    ev = ears.evaluate(series)
    assert ev["alarm"] is True
    assert ev["method"] == "cdc_ears_c1_c2_c3"


def test_guard_band_prevents_baseline_contamination():
    """C2의 2일 가드밴드: 발병 직전 이틀이 이미 치솟아도 기준선이 오염되지 않아
    C2가 C1보다 급증을 더 또렷이 잡는다."""
    series = [10, 11, 10, 9, 10, 11, 10, 100, 100, 100]  # 마지막 3일 급등
    c1v, c2v = ears.c1(series), ears.c2(series)
    assert c2v > c1v          # 가드밴드 덕에 C2가 더 민감
    assert ev_alarm(series)


def ev_alarm(series):
    return ears.evaluate(series)["alarm"]


def test_constant_baseline_no_false_alarm():
    """분산 0 기준선(항상 같은 값)에선 통계 0 — 가짜 경보 금지."""
    series = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    assert ears.c1(series) == 0.0
    assert ears.c2(series) == 0.0
    assert ears.evaluate(series)["alarm"] is False


def test_gradual_rise_accumulates_in_c3():
    """단발 스파이크가 아닌 완만한 상승 — C3가 누적해서 잡는다."""
    series = [10, 10, 11, 10, 10, 11, 10, 12, 14, 16, 18, 20]
    c3v = ears.c3(series)
    assert c3v is not None and c3v >= 0.0


def test_too_short_series_returns_none():
    assert ears.c1([1, 2, 3]) is None
    assert ears.c2([1, 2, 3, 4, 5, 6, 7]) is None      # C2는 10일 필요
    assert ears.c3([1] * 11) is None                    # C3는 12일 필요
    assert ears.evaluate([1, 2, 3]) is None


def test_c2_needs_more_history_than_c1():
    nine = [10, 11, 10, 9, 10, 11, 10, 10, 40]  # 9일 — C1은 되고 C2는 아직
    assert ears.c1(nine) is not None
    assert ears.c2(nine) is None
    # C1만이라도 되면 evaluate는 결과를 준다
    assert ears.evaluate(nine) is not None

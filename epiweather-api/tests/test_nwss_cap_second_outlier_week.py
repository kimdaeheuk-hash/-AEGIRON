"""이상치가 두 주 연달아 와도 하수 농도 상한이 안 풀린다 (2026-10-25, 소킹 10-23 16:01 NWSS critical 폰 재발).

#83 이 적어 둔 한계 ⓪ 그대로였다: 1,680,230 이 '서로 다른 한 주'로 평균에 들어가 평소가 152,470 으로 올랐고,
다음 창 1,404,069 는 직전 값과 비슷해 두 비교점 모두 10배 미만 → 상한이 풀려 95점 critical. 고정하는 것:
① 과거 중앙값을 세 번째 비교점으로 쓴다 ② 10-23 모양에서 상한이 걸린다 ③ 진짜 새 수준이 오래 이어지면
중앙값도 따라 올라 상한이 결국 풀린다(영원히 묶지 않는다) ④ GAI 가 중앙값을 내보낸다.
"""
from __future__ import annotations

from algorithms.gai import _baseline_median
from algorithms.signal_metrics import implausible_jump

WEEKS = [63488.7, 70112.0, 81234.5, 59876.1, 75321.9, 68840.2, 1680229.8]


def test_the_2026_10_23_shape_stays_capped():
    mean = sum(WEEKS) / len(WEEKS)                      # 약 314k — 이상치에 끌려 오른 평균
    assert implausible_jump("cdc_nwss_concentration", 1404068.6, mean, 1680229.8) is None, "예전 비교점 둘로는 풀렸다"
    median = _baseline_median([*WEEKS, 1404068.6])
    assert median < 100_000
    assert implausible_jump("cdc_nwss_concentration", 1404068.6, mean, 1680229.8, median) > 10


def test_a_lasting_new_level_eventually_releases_the_cap():
    level = [*WEEKS[:-1]] + [1_500_000.0] * 7
    median = _baseline_median([*level, 1_450_000.0])
    assert median > 1_000_000
    assert implausible_jump("cdc_nwss_concentration", 1_450_000.0, None, 1_500_000.0, median) is None


def test_gai_exports_the_median():
    import inspect
    from algorithms import gai
    assert '"baseline_median": _baseline_median(series)' in inspect.getsource(gai.compute_gai)


def test_alerts_pass_the_median():
    import inspect
    from algorithms import alerts
    assert 'm.get("baseline_median")' in inspect.getsource(alerts)

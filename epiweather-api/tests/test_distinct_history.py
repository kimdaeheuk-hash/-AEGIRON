"""표본을 세는 것과 관측을 세는 것 (2026-09-20).

## 왜 이 파일이 있나

09-20 01:02, critical 경보가 캡틴 폰으로 나갔다. 원인은 **전날 내가 붙인 축**이다.

    과거 = 44.89879 × 21개   (naver_covid_ratio, 09-19 03:26 도입 후 매시간 같은 값)
    최신 = 50.87138
    → pstdev 1.24 → z ≈ 4.6 → 상한 3 → raw 100 → trusted 90 = critical

도입 PR 에 이렇게 적었다 — *"신규 지표는 관측 4개 미만이면 판정을 보류하므로
초기 지수 왜곡은 없다"*. **그 보호가 작동하지 않았다.**

`MIN_HISTORY = 3` 은 '한 주기에 한 관측'을 전제로 쓴 값이다. 그런데 네이버는
주 단위로 바뀌는데 수집은 시간마다 한다 — 같은 값이 168번 복제된다. 그래서
"과거 관측 4개"가 실제로는 **"과거 관측 1개를 4번 본 것"** 이었다.

표준편차가 '값이 얼마나 변하는가'가 아니라 '값이 언제 바뀌었나'를 재게 되고,
첫 변화에서 z 가 상한까지 튄다.

## 대가

주 단위 지표는 서로 다른 값 3개가 모이는 데 3주가 걸린다. 조기경보에서 3주는
길다. 그래도 '모르는 것을 모른다고 하는 쪽'을 택했다(캡틴 결정 2026-09-20) —
2개 값으로 낸 "3σ"는 숫자이지 근거가 아니다.
"""
from __future__ import annotations

from algorithms.anomaly_engine import _zscore_anomaly
from algorithms.gai import _anomaly_score
from algorithms.signal_metrics import MIN_DISTINCT_HISTORY, has_enough_distinct_history

# 09-20 01:02 경보를 만든 실제 값 (Railway 로그에서 옮김)
COVID_AXIS = [44.89879] * 21 + [50.87138] * 2


# ── ★핵심★ 그 경보가 다시 나지 않는다 ─────────────────────────
def test_the_alert_that_actually_fired_is_now_withheld():
    """★이 테스트가 이 파일의 이유다★ 09-20 01:02 에 나간 바로 그 계열이다."""
    assert _anomaly_score(COVID_AXIS) is None


def test_both_engines_agree_on_that_series():
    """★핵심★ 두 엔진이 같은 지표를 두고 다른 말을 하면(한쪽 판정 안 함,
    한쪽 100점) 그 자체가 고장이다. 같은 문턱을 쓴다."""
    assert _anomaly_score(COVID_AXIS) is None
    assert _zscore_anomaly(COVID_AXIS) is None


def test_withheld_is_none_not_zero():
    """★핵심★ '판정 안 함'을 0 으로 쓰면 '이상 없음'이 된다 — 없는 것을
    0 으로도 100 으로도 만들지 않는다. gai 는 None 인 지표를 건너뛴다."""
    assert _anomaly_score(COVID_AXIS) is not 0
    assert _anomaly_score(COVID_AXIS) is None


# ── 진짜 변동이 있는 축은 그대로 판정한다 ──────────────────────
def test_a_metric_that_has_actually_varied_still_scores():
    """★핵심★ 조용해지는 게 목적이 아니다. 과거가 실제로 변해온 축은
    전과 똑같이 판정된다 — 이게 깨지면 진짜 신호를 죽인 것이다."""
    varied = [40, 60, 75, 92.55, 85] * 4 + [100.0]
    assert _anomaly_score(varied) == 52.4
    assert _zscore_anomaly(varied)["anomaly_score"] == 52.4


def test_exactly_the_minimum_distinct_values_passes():
    """문턱은 '이상'이다 — 경계에서 막히면 3주가 4주가 된다."""
    assert has_enough_distinct_history([1.0, 2.0, 3.0]) is True
    assert has_enough_distinct_history([1.0, 2.0]) is False
    assert has_enough_distinct_history([1.0] * 100) is False


def test_repeats_do_not_count_toward_the_minimum():
    """★핵심★ 같은 값을 아무리 많이 봐도 관측이 늘어난 게 아니다 —
    이 문장이 곧 09-20 사고의 한 줄 요약이다."""
    assert has_enough_distinct_history([5.0] * 168) is False
    assert has_enough_distinct_history([5.0] * 168 + [6.0]) is False
    assert has_enough_distinct_history([5.0] * 168 + [6.0, 7.0]) is True


# ── 두 문턱은 서로 다른 것을 막는다 ────────────────────────────
def test_sample_count_and_distinct_count_are_separate_guards():
    """표본이 적은 것(아직 안 쌓임)과 표본은 많은데 전부 같은 값인 것
    (수집이 원천보다 빠름)은 다른 상태다. 둘 다 판정을 막되 구분은 남긴다."""
    assert _anomaly_score([1.0, 2.0]) is None           # 표본 부족
    assert _anomaly_score([7.0] * 50 + [9.0]) is None   # 표본은 충분, 변동 없음
    assert MIN_DISTINCT_HISTORY == 3

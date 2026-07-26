"""감시역학 표준 성능지표 — 혼동행렬·민감도·특이도·PPV·FAR·F-measure·리드타임.
분모 0이면 값을 지어내지 않고 None. 알려진 발병만 있을 때 특이도·FAR은 negative
baseline 필요를 정직하게 명시하는지 확인."""
from __future__ import annotations

from algorithms import surveillance_metrics as sm


def test_confusion_matrix_counts():
    labeled = [
        {"outbreak": True, "detected": True},    # TP
        {"outbreak": True, "detected": False},   # FN
        {"outbreak": False, "detected": True},   # FP
        {"outbreak": False, "detected": False},  # TN
        {"outbreak": True, "detected": True},    # TP
    ]
    c = sm.confusion_matrix(labeled)
    assert c == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}


def test_standard_metrics_values():
    c = {"tp": 8, "fp": 2, "fn": 2, "tn": 88}
    m = sm.metrics_from_confusion(c)
    assert m["sensitivity"] == 0.8          # 8/(8+2)
    assert m["specificity"] == 0.978        # 88/(88+2)
    assert m["ppv"] == 0.8                   # 8/(8+2)
    assert m["false_alarm_rate"] == 0.2      # 2/(8+2) = 1 - PPV
    assert m["f_measure"] == 0.8


def test_zero_denominator_returns_none_not_fabricated():
    """표본이 없으면(분모 0) 지어내지 않고 None."""
    assert sm.sensitivity(0, 0) is None
    assert sm.specificity(0, 0) is None
    assert sm.false_alarm_rate(0, 0) is None
    m = sm.metrics_from_confusion({"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    assert m["sensitivity"] is None and m["f_measure"] is None


def test_timeliness_stats():
    assert sm.timeliness_stats([])["mean_lead_days"] is None
    t = sm.timeliness_stats([3, 5, 9, 1])
    assert t["n"] == 4
    assert t["mean_lead_days"] == 4.5
    assert t["median_lead_days"] == 4.0
    assert t["min_lead_days"] == 1 and t["max_lead_days"] == 9


def test_detection_summary_uses_only_verified_events():
    results = [
        {"verified": True, "would_have_alerted": True, "lead_days": 5},
        {"verified": True, "would_have_alerted": True, "lead_days": 3},
        {"verified": True, "would_have_alerted": False},          # 데이터는 있었으나 미탐지 → FN
        {"verified": False, "reason": "데이터 없음"},               # 분모에서 제외
    ]
    s = sm.detection_summary(results)
    assert s["evaluable_events"] == 3        # verified=False 제외
    assert s["detected_events"] == 2
    assert s["detection_proportion"] == 0.667
    assert s["timeliness"]["mean_lead_days"] == 4.0
    # 알려진 발병만 있으므로 특이도·FAR은 아직 계산 불가 — 정직하게 None + 안내
    assert s["specificity"] is None and s["false_alarm_rate"] is None
    assert "negative baseline" in s["negative_baseline_note"]
    # EIOS 벤치마크 참조가 붙어야 함(어디에 위치하는지 비교 근거)
    assert s["benchmark_reference"]["eios_africa_sensitivity"] == 0.474

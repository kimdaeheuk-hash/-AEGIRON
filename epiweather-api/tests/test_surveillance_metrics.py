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


# ── 벤치마크 비교에 사후 조립분을 섞지 않는다 (2026-09-03) ─────────────────

def test_benchmark_comparison_points_at_live_only():
    """★★핵심★★ EIOS 와 견줄 수 있는 건 실측뿐이라고 못 박는다.

    섞은 탐지율 0.833 을 EIOS 아프리카 0.810 옆에 놓으면 **우리가 이긴 것처럼
    보인다.** 그런데 그 탐지 대부분은 아이기론이 존재하지 않던 시절 사건을
    사후 GDELT 뉴스량으로 되짚은 것이었다.
    """
    from algorithms.surveillance_metrics import detection_summary

    out = detection_summary([
        {"verified": True, "would_have_alerted": True, "lead_days": 37,
         "evidence_class": "retrospective"},
        {"verified": True, "would_have_alerted": True, "lead_days": -5,
         "evidence_class": "live"},
    ])

    assert out["includes_retrospective"] is True
    assert out["benchmark_reference"]["comparable_field"] == "live_only"
    assert "존재하지 않던 시점" in out["benchmark_reference"]["note"]


def test_live_only_excludes_retrospective_detections():
    """★핵심★ live_only 는 사후 조립분을 한 건도 세지 않는다."""
    from algorithms.surveillance_metrics import detection_summary

    out = detection_summary([
        {"verified": True, "would_have_alerted": True, "lead_days": 56,
         "evidence_class": "retrospective"},
        {"verified": True, "would_have_alerted": True, "lead_days": 37,
         "evidence_class": "mixed"},
        {"verified": True, "would_have_alerted": True, "lead_days": -5,
         "evidence_class": "live"},
    ])

    live = out["live_only"]
    assert live["evaluable_events"] == 1
    assert live["timeliness"]["mean_lead_days"] == -5.0, "사후분이 실측에 섞였다"
    assert out["timeliness"]["mean_lead_days"] != live["timeliness"]["mean_lead_days"]


def test_live_only_is_empty_when_nothing_was_measured_live():
    """★핵심★ 실측이 없으면 0 이라고 말한다 — 상위 숫자로 대신하지 않는다."""
    from algorithms.surveillance_metrics import detection_summary

    out = detection_summary([
        {"verified": True, "would_have_alerted": True, "lead_days": 56,
         "evidence_class": "retrospective"},
    ])

    assert out["live_only"]["evaluable_events"] == 0
    assert out["live_only"]["detection_proportion"] is None
    assert out["live_only"]["timeliness"]["n"] == 0

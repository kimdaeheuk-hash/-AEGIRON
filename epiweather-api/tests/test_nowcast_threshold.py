"""임계값 운영점 선택 — 곡선 계산과 '조정으로 될 문제인지' 진단을 검증."""
from __future__ import annotations

from algorithms import nowcast_threshold as nt


def _scored(pairs):
    """(확률, 라벨) 목록을 그대로 쓴다."""
    return list(pairs)


# ── 운영점 계산 ───────────────────────────────────────────────────
def test_operating_point_computes_surveillance_metrics():
    scored = _scored([(0.9, 1), (0.8, 1), (0.7, 0), (0.2, 0), (0.1, 0)])
    p = nt.operating_point(scored, 0.5)
    assert (p["tp"], p["fp"], p["fn"], p["tn"]) == (2, 1, 0, 2)
    assert p["sensitivity"] == 1.0                 # 양성 2건 다 잡음
    assert p["ppv"] == round(2 / 3, 3)
    assert p["false_alarm_rate"] == round(1 / 3, 3)
    assert p["false_alarm_rate"] == round(1 - p["ppv"], 3)   # FAR = 1-PPV


def test_alerts_per_100_windows_shows_operational_load():
    """운영 부담을 감으로 잡을 수 있어야 한다 — 경보가 몇 건 오는가."""
    scored = _scored([(0.9, 1)] + [(0.1, 0)] * 9)
    assert nt.operating_point(scored, 0.5)["alerts_per_100_windows"] == 10.0


def test_no_alerts_yields_undefined_precision_not_zero():
    """경보가 0건이면 정밀도는 0이 아니라 '측정불가'다."""
    scored = _scored([(0.1, 1), (0.1, 0)])
    p = nt.operating_point(scored, 0.9)
    assert p["ppv"] is None and p["false_alarm_rate"] is None


# ── FAR 예산별 추천 ───────────────────────────────────────────────
def test_recommend_picks_max_sensitivity_within_budget():
    curve = [
        {"threshold": 0.3, "sensitivity": 0.9, "specificity": 0.7, "ppv": 0.1, "false_alarm_rate": 0.9},
        {"threshold": 0.5, "sensitivity": 0.8, "specificity": 0.8, "ppv": 0.5, "false_alarm_rate": 0.5},
        {"threshold": 0.7, "sensitivity": 0.6, "specificity": 0.9, "ppv": 0.7, "false_alarm_rate": 0.3},
    ]
    assert nt.recommend(curve, 0.5)["threshold"] == 0.5    # 예산 안에서 민감도 최대
    assert nt.recommend(curve, 0.35)["threshold"] == 0.7


def test_recommend_returns_none_when_budget_infeasible():
    """그 예산으로 안 되면 억지로 고르지 않는다."""
    curve = [{"threshold": 0.5, "sensitivity": 0.8, "specificity": 0.8,
              "ppv": 0.1, "false_alarm_rate": 0.9}]
    assert nt.recommend(curve, 0.5) is None


# ── 곡선 진단(핵심) ───────────────────────────────────────────────
def test_flat_curve_says_threshold_tuning_will_not_help():
    """★핵심★ 실측 곡선이 이랬다 — 임계값 0.2~0.7 내내 민감도 0.778 고정,
    FAR은 0.815~0.766만 움직였다. 이걸 안 짚으면 임계값만 만지며 시간을 버린다."""
    curve = [{"threshold": t, "sensitivity": 0.778, "ppv": 0.2, "specificity": 0.95,
              "false_alarm_rate": far}
             for t, far in ((0.2, 0.815), (0.5, 0.782), (0.7, 0.766))]
    d = nt.diagnose_curve(curve)
    assert d["threshold_tuning_helps"] is False
    assert d["far_span"] < 0.15
    assert "조정으로 될 문제가 아니다" in d["verdict"]
    assert "특징 추가" in d["verdict"]


def test_wide_curve_says_tuning_is_meaningful():
    curve = [{"threshold": t, "sensitivity": sv, "ppv": 0.3, "specificity": 0.9,
              "false_alarm_rate": far}
             for t, sv, far in ((0.2, 0.95, 0.90), (0.5, 0.70, 0.55), (0.8, 0.40, 0.20))]
    d = nt.diagnose_curve(curve)
    assert d["threshold_tuning_helps"] is True
    assert "고를 여지가 있다" in d["verdict"]


def test_diagnosis_refuses_on_too_few_points():
    assert nt.diagnose_curve([{"threshold": 0.5, "sensitivity": 0.5, "ppv": 0.5,
                               "specificity": 0.9, "false_alarm_rate": 0.5}])["assessed"] is False


# ── 전체 분석 ─────────────────────────────────────────────────────
def test_analyze_refuses_untrained_model():
    out = nt.analyze([], {"trained": False})
    assert out["ok"] is False and "학습되지 않은" in out["reason"]


def test_analyze_carries_caveat_about_retrospective_fit():
    """같은 데이터로 그린 곡선이라는 걸 결과가 계속 달고 다녀야 한다."""
    rows = [{"features": {}, "label": 1}, {"features": {}, "label": 0}] * 30
    model = {"trained": True, "weights": {}, "bias": 0.0,
             "feature_means": {}, "feature_stds": {}}
    out = nt.analyze(rows, model)
    assert out["ok"] is True
    assert "과거적합" in out["caveat"] and "그림자" in out["caveat"]
    assert "운영 정책" in out["note"]


# ── 퇴화 운영점 제외(진단이 속지 않게) ───────────────────────────
def test_degenerate_alert_everything_points_are_excluded():
    """★회귀★ 임계값을 아주 낮추면 '전부 경보'(특이도 0)가 되는데, 이걸 곡선 폭에
    넣으면 FAR 변동폭이 부풀려져 '조정 여지 있음'이라는 반대 결론이 나온다.
    실측에서 0.350으로 부풀었다가 퇴화점 제외 후 0.180이 됐다."""
    curve = [
        {"threshold": 0.05, "sensitivity": 1.0, "specificity": 0.0,
         "ppv": 0.015, "false_alarm_rate": 0.985},          # 전부 경보 — 퇴화
        {"threshold": 0.5, "sensitivity": 0.778, "specificity": 0.957,
         "ppv": 0.218, "false_alarm_rate": 0.782},
        {"threshold": 0.7, "sensitivity": 0.778, "specificity": 0.961,
         "ppv": 0.234, "false_alarm_rate": 0.766},
        {"threshold": 0.95, "sensitivity": 0.492, "specificity": 0.987,
         "ppv": 0.365, "false_alarm_rate": 0.635},
    ]
    usable = nt.usable_points(curve)
    assert len(usable) == 3 and all(p["threshold"] >= 0.5 for p in usable)
    d = nt.diagnose_curve(curve)
    assert d["excluded_degenerate"] == 1
    assert d["far_span"] == round(0.782 - 0.635, 3)     # 퇴화점 0.985가 안 섞임


def test_recommendation_never_picks_a_degenerate_point():
    """'전부 경보'는 FAR 예산을 못 지키지만, 혹시라도 추천에 끼면 안 된다."""
    curve = [
        {"threshold": 0.05, "sensitivity": 1.0, "specificity": 0.0,
         "ppv": 0.5, "false_alarm_rate": 0.5},            # 퇴화인데 FAR은 낮은 함정
        {"threshold": 0.6, "sensitivity": 0.7, "specificity": 0.9,
         "ppv": 0.5, "false_alarm_rate": 0.5},
    ]
    assert nt.recommend(curve, 0.5)["threshold"] == 0.6

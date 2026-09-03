"""감시역학 표준 성능지표 — 반증 가능한 성능 주장을 위한 지표 세트.

배경(경쟁 벤치마크 지적): "아이기론이 N일 먼저 잡았다"만 단독 제시하면 골드스탠다드·
오경보율이 없어 반증 불가능한 주장으로 간주된다. 감시역학 심사자는 timeliness(리드타임)
하나가 아니라 **민감도·특이도·PPV·오경보율(FAR)**의 트레이드오프를 묻는다.

이 모듈은 그 표준 지표를 순수 함수로 제공한다(외부 의존 없음). 분모가 0이면(표본 부족)
값을 지어내지 않고 None을 돌린다 — 정직성 원칙.

지표 정의(감시역학 관례):
  - 민감도(sensitivity/POD, 재현율) = TP/(TP+FN)  : 실제 발병 중 탐지 비율
  - 특이도(specificity)            = TN/(TN+FP)  : 비발병을 비발병으로 본 비율
  - 양성예측도(PPV, 정밀도)         = TP/(TP+FP)  : 경보 중 진짜 비율
  - 오경보율(FAR)                  = FP/(TP+FP)  : 경보 중 헛경보 비율(= 1-PPV)
  - F-measure                     = 2·민감도·PPV/(민감도+PPV)

참고: EIOS 아프리카 평가(BMC Public Health 2025)의 탐지율 81.0%·민감도 47.4%가
공개 벤치마크 — 아이기론 목표를 "그 분포 안에서 어디"로 잡는 근거로 쓴다.
AMOC(Activity Monitoring Operating Characteristic) 커브는 timeliness vs FAR
트레이드오프를 그리는 표준(arXiv 1406.3496).
"""
from __future__ import annotations
import statistics


def confusion_matrix(labeled: list[dict]) -> dict:
    """labeled: [{"outbreak": bool, "detected": bool}, ...] → TP/FP/FN/TN."""
    tp = sum(1 for x in labeled if x["outbreak"] and x["detected"])
    fn = sum(1 for x in labeled if x["outbreak"] and not x["detected"])
    fp = sum(1 for x in labeled if not x["outbreak"] and x["detected"])
    tn = sum(1 for x in labeled if not x["outbreak"] and not x["detected"])
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _safe_div(num: float, den: float) -> float | None:
    return round(num / den, 3) if den else None   # 분모 0이면 '측정불가'


def sensitivity(tp: int, fn: int) -> float | None:
    return _safe_div(tp, tp + fn)


def specificity(tn: int, fp: int) -> float | None:
    return _safe_div(tn, tn + fp)


def ppv(tp: int, fp: int) -> float | None:
    return _safe_div(tp, tp + fp)


def false_alarm_rate(tp: int, fp: int) -> float | None:
    """경보 중 헛경보 비율 = FP/(TP+FP) = 1 - PPV. CIDARS의 교훈(오경보 폭증)을 정량화."""
    return _safe_div(fp, tp + fp)


def f_measure(tp: int, fp: int, fn: int) -> float | None:
    sens = sensitivity(tp, fn)
    prec = ppv(tp, fp)
    if not sens or not prec or (sens + prec) == 0:
        return None
    return round(2 * sens * prec / (sens + prec), 3)


def metrics_from_confusion(c: dict) -> dict:
    """혼동행렬 → 표준 지표 전부. 계산 불가 항목은 None(지어내지 않음)."""
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    return {
        "confusion": c,
        "sensitivity": sensitivity(tp, fn),        # POD / recall
        "specificity": specificity(tn, fp),
        "ppv": ppv(tp, fp),                        # precision
        "false_alarm_rate": false_alarm_rate(tp, fp),
        "f_measure": f_measure(tp, fp, fn),
    }


def timeliness_stats(lead_days: list[int]) -> dict:
    """리드타임 분포 — 평균·중앙값·최소·최대. 표본 없으면 전부 None."""
    if not lead_days:
        return {"n": 0, "mean_lead_days": None, "median_lead_days": None,
                "min_lead_days": None, "max_lead_days": None}
    return {
        "n": len(lead_days),
        "mean_lead_days": round(statistics.mean(lead_days), 1),
        "median_lead_days": round(statistics.median(lead_days), 1),
        "min_lead_days": min(lead_days),
        "max_lead_days": max(lead_days),
    }


# 특이도·FAR는 '라벨링된 비발병 기간(negative baseline)'이 있어야 계산된다.
# 아직 그 라벨셋이 없으면 지어내지 않고 아래 안내를 붙인다(방법은 이미 정의됨).
NEGATIVE_BASELINE_NOTE = (
    "특이도·오경보율(FAR)은 '발병이 없었던 기간에 경보를 안 냈는가'를 라벨링한 "
    "negative baseline이 있어야 계산된다. 현재는 알려진 발병(positive)만 있어 "
    "민감도·리드타임만 실측 가능 — 특이도·FAR은 방법만 정의(metrics_from_confusion)해 두고 "
    "GDELT 회고 검증셋으로 negative 기간을 라벨링하면 즉시 산출된다."
)


def detection_summary(backtest_results: list[dict]) -> dict:
    """실이력 백테스트 결과 목록 → 방어 가능한 성능 요약.
    honestly 계산 가능한 것(탐지율·민감도·리드타임)만 실측하고, 특이도·FAR은
    negative baseline 필요를 명시한다(EIOS 아프리카 81%/47.4%와 비교할 형태)."""
    # verified=True(그 시점 데이터가 있었던 이벤트)만 분모로 — 데이터 없는 건 제외.
    evaluable = [r for r in backtest_results if r.get("verified")]
    detected = [r for r in evaluable if r.get("would_have_alerted")]
    lead_days = [r["lead_days"] for r in detected if isinstance(r.get("lead_days"), int)]

    # 알려진 발병만 있으므로 FN은 '데이터가 있었는데 임계값을 못 넘은 이벤트'.
    tp = len(detected)
    fn = len(evaluable) - len(detected)

    # ★★ 실측만 따로 낸다 ★★ (2026-09-03)
    # 여기 들어오는 사건 대부분은 아이기론이 존재하지 않던 시절 것이고, 그 신호는
    # nowcast_backfill 이 지금 GDELT 뉴스량으로 조립한 대리지표다. 그걸 섞은
    # 탐지율(0.833)을 EIOS 아프리카 0.810 과 나란히 놓으면 **우리가 이긴 것처럼
    # 보인다.** 실제로 아이기론이 돌던 시점 실측은 사건 한 건뿐이었다.
    live_eval = [r for r in evaluable if r.get("evidence_class") == "live"]
    live_detected = [r for r in live_eval if r.get("would_have_alerted")]
    live_leads = [r["lead_days"] for r in live_detected if isinstance(r.get("lead_days"), int)]
    live_tp = len(live_detected)
    live_fn = len(live_eval) - live_tp

    return {
        "evaluable_events": len(evaluable),
        "detected_events": tp,
        "detection_proportion": _safe_div(tp, len(evaluable)),   # EIOS의 '탐지율'과 동형
        "sensitivity": sensitivity(tp, fn),                       # = 탐지율(여기선 동일)
        "timeliness": timeliness_stats(lead_days),
        # ★ 이 숫자들에는 사후 조립분이 섞여 있다 ★ 벤치마크 비교에 쓰면 안 된다.
        "includes_retrospective": any(
            r.get("evidence_class") in ("retrospective", "mixed") for r in evaluable),
        "live_only": {
            "evaluable_events": len(live_eval),
            "detected_events": live_tp,
            "detection_proportion": _safe_div(live_tp, len(live_eval)),
            "sensitivity": sensitivity(live_tp, live_fn),
            "timeliness": timeliness_stats(live_leads),
        },
        "specificity": None,
        "false_alarm_rate": None,
        "negative_baseline_note": NEGATIVE_BASELINE_NOTE,
        "benchmark_reference": {
            "eios_africa_detection_proportion": 0.810,
            "eios_africa_sensitivity": 0.474,
            "source": "EIOS Africa evaluation, BMC Public Health 2025 (DOI 10.1186/s12889-025-21998-9)",
            "comparable_field": "live_only",
            "note": "EIOS 와 견줄 수 있는 건 live_only 뿐이다. 상위 수치에는 아이기론이 "
                    "존재하지 않던 시점 사건이 사후 조립 데이터로 섞여 있다.",
        },
        "metric_standard": ["sensitivity", "specificity", "ppv", "false_alarm_rate",
                            "f_measure", "timeliness", "AMOC_curve"],
    }

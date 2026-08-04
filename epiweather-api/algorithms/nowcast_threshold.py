"""임계값 운영점 선택 — 재현율과 오경보율의 균형을 '고를 수 있게' 만든다.

배경: train_baseline은 임계값 0.5 고정(z>=0)이라 조정 여지가 없었다. 실측에서
재현율 0.778 / 정밀도 0.218이 나왔는데, 이건 **경보 5번 중 4번이 헛경보**라는
뜻이다(FAR 0.782). 이 저장소엔 이미 경보 피로를 다루는 모듈이 있는데 그 상태로
실전에 넣으면 경보가 무시당한다.

★ 여기서 가장 중요한 판단 ★
**적정 FAR은 기술 문제가 아니라 운영 정책이다.** 하루에 몇 건의 경보를 사람이
검토할 수 있는지, 발병을 놓치는 비용이 헛경보 비용의 몇 배인지는 조직이 정한다.
그래서 이 모듈은 하나의 '정답 임계값'을 고르지 않는다 — 운영특성 곡선 전체를
보여주고, 조직이 FAR 예산을 정하면 그 안에서 민감도를 최대화하는 점을 찾아준다.
(감시역학 표준 AMOC 커브의 timeliness↔FAR 트레이드오프와 같은 틀.)

지표 정의는 surveillance_metrics를 그대로 따른다:
  민감도(POD/재현율) = TP/(TP+FN), 특이도 = TN/(TN+FP),
  PPV(정밀도) = TP/(TP+FP), FAR = FP/(TP+FP) = 1-PPV
"""
from __future__ import annotations

import math

from .nowcast_dataset import FEATURE_KEYS, _vec, dataset_readiness

# 곡선을 그릴 임계값들(확률). 양 끝은 의미가 없어 제외한다.
DEFAULT_THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]
# 조직이 고를 만한 FAR 예산 예시 — 정답이 아니라 '선택지'로 제시한다.
FAR_BUDGETS = (0.5, 0.6, 0.7, 0.8)


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def score_rows(rows: list[dict], model: dict) -> list[tuple[float, int]]:
    """(예측확률, 실제라벨) 목록. 학습 때와 **같은 특징 순서·같은 표준화**를 적용한다.

    특징 순서를 전역 상수로 고정하면 확장 특징을 학습해 놓고 채점에선 통째로 무시해,
    특징을 추가해도 성능이 안 변하는 것처럼 보인다. 그래서 모델이 학습 때 쓴
    feature_order를 따른다(없으면 구형 모델이므로 기본 6개)."""
    weights = model.get("weights") or {}
    means = model.get("feature_means") or {}
    stds = model.get("feature_stds") or {}
    bias = model.get("bias", 0.0)
    keys = tuple(model.get("feature_order") or FEATURE_KEYS)
    out = []
    for row in rows:
        vec = _vec(row["features"], keys)
        z = bias
        for j, key in enumerate(keys):
            std = stds.get(key) or 1.0
            z += weights.get(key, 0.0) * ((vec[j] - means.get(key, 0.0)) / std)
        out.append((_sigmoid(z), int(row["label"])))
    return out


def operating_point(scored: list[tuple[float, int]], threshold: float) -> dict:
    """한 임계값에서의 혼동행렬과 감시역학 지표."""
    tp = fp = fn = tn = 0
    for prob, label in scored:
        alert = prob >= threshold
        if label == 1 and alert:
            tp += 1
        elif label == 1:
            fn += 1
        elif alert:
            fp += 1
        else:
            tn += 1
    alerts = tp + fp
    total = tp + fp + fn + tn
    return {
        "threshold": threshold,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "sensitivity": round(tp / (tp + fn), 3) if (tp + fn) else None,
        "specificity": round(tn / (tn + fp), 3) if (tn + fp) else None,
        "ppv": round(tp / alerts, 3) if alerts else None,
        "false_alarm_rate": round(fp / alerts, 3) if alerts else None,
        # 운영 부담을 감으로 잡을 수 있게 — 100개 관측창당 경보 수.
        "alerts_per_100_windows": round(100 * alerts / total, 1) if total else None,
    }


def operating_curve(rows: list[dict], model: dict,
                    thresholds: list[float] | None = None) -> list[dict]:
    scored = score_rows(rows, model)
    return [operating_point(scored, t) for t in (thresholds or DEFAULT_THRESHOLDS)]


def recommend(curve: list[dict], max_far: float) -> dict | None:
    """FAR 예산 안에서 민감도가 가장 높은 운영점. 없으면 None(그 예산으론 불가).

    민감도 우선인 이유: 조기경보에서 발병을 놓치는 비용이 헛경보보다 크다는 게
    이 도구의 전제다. 다만 그 전제가 무한하지는 않아서 FAR 상한을 먼저 건다."""
    feasible = [p for p in usable_points(curve) if p["false_alarm_rate"] <= max_far]
    if not feasible:
        return None
    # 민감도 최대 → 동률이면 FAR이 낮은 쪽
    return max(feasible, key=lambda p: (p["sensitivity"], -p["false_alarm_rate"]))


# 임계값을 움직여도 FAR이 이만큼도 안 바뀌면 '조정으로 될 문제가 아니다'로 본다.
_FLAT_CURVE_FAR_SPAN = 0.15
# 음성의 절반도 못 거르는 점은 운영 선택지가 아니다 — 사실상 '전부 경보'라
# 경보가 아니라 소음이다. 이런 퇴화점을 곡선 폭에 넣으면 진단이 속는다:
# 실측에서 임계값 0.05~0.15(특이도 0.000, 100창당 100건 경보)가 FAR 변동폭을
# 0.35로 부풀려 '조정 여지 있음'이라는 반대 결론이 나왔다.
_MIN_USABLE_SPECIFICITY = 0.5


def usable_points(curve: list[dict]) -> list[dict]:
    """실제로 고를 만한 운영점만. 지표가 없거나 퇴화한 점은 뺀다."""
    return [
        p for p in curve
        if p.get("false_alarm_rate") is not None
        and p.get("sensitivity") is not None
        and p.get("ppv") is not None
        and (p.get("specificity") is None or p["specificity"] >= _MIN_USABLE_SPECIFICITY)
    ]


def diagnose_curve(curve: list[dict]) -> dict:
    """곡선이 평평하면 임계값 조정으로는 균형이 안 잡힌다 — 그걸 명시한다.

    실측에서 임계값 0.20~0.70 내내 민감도가 0.778로 고정이고 FAR은 0.815~0.766만
    움직였다. 이런 모양은 점수 분포가 양성·음성을 잘 못 가른다는 뜻이라, 임계값을
    만질 게 아니라 특징·데이터를 손봐야 한다. 이걸 안 짚으면 임계값만 만지며
    시간을 버리게 된다."""
    usable = usable_points(curve)
    if len(usable) < 3:
        return {"assessed": False, "reason": "유효 운영점이 3개 미만 — 진단 불가",
                "usable_points": len(usable),
                "excluded_degenerate": len(curve) - len(usable)}
    fars = [p["false_alarm_rate"] for p in usable]
    sens = [p["sensitivity"] for p in usable]
    far_span = round(max(fars) - min(fars), 3)
    best_far = min(fars)
    flat = far_span < _FLAT_CURVE_FAR_SPAN
    return {
        "assessed": True,
        "usable_points": len(usable),
        "excluded_degenerate": len(curve) - len(usable),
        "far_span": far_span,
        "sensitivity_span": round(max(sens) - min(sens), 3),
        "best_achievable_far": best_far,
        "threshold_tuning_helps": not flat,
        "verdict": (
            f"임계값을 끝에서 끝까지 움직여도 FAR이 {far_span:.3f}밖에 안 변한다 — "
            "조정으로 될 문제가 아니다. 점수 분포가 양성·음성을 잘 못 가르는 것이므로 "
            "특징 추가·라벨 커버리지 확대로 판별력 자체를 올려야 한다."
            if flat else
            f"임계값에 따라 FAR이 {far_span:.3f} 움직인다 — 운영 정책에 맞춰 고를 여지가 있다."
        ),
    }


def analyze(rows: list[dict], model: dict,
            far_budgets: tuple[float, ...] = FAR_BUDGETS) -> dict:
    """운영특성 곡선 + FAR 예산별 추천점. 하나의 정답을 고르지 않는다."""
    if not model.get("trained"):
        return {"ok": False, "reason": "학습되지 않은 모델 — 임계값 분석 불가"}
    curve = operating_curve(rows, model)
    baseline = operating_point(score_rows(rows, model), 0.5)
    recommendations = {}
    for budget in far_budgets:
        point = recommend(curve, budget)
        recommendations[f"far<={budget}"] = point or {
            "feasible": False,
            "reason": f"이 모델로는 FAR {budget:.0%} 이하에서 잡히는 발병이 없다.",
        }
    return {
        "ok": True,
        "readiness": dataset_readiness(rows),
        "current_default": baseline,          # 지금 코드가 쓰는 0.5 고정점
        "curve": curve,
        "diagnosis": diagnose_curve(curve),   # 임계값으로 될 문제인지 먼저 판정
        "recommendations": recommendations,
        "note": (
            "적정 FAR은 기술이 아니라 운영 정책이다 — 하루 몇 건을 사람이 검토할 수 "
            "있는지, 발병을 놓치는 비용이 헛경보의 몇 배인지는 조직이 정한다. 그래서 "
            "정답 임계값을 고르지 않고 곡선과 예산별 선택지를 제시한다. "
            "alerts_per_100_windows로 실제 운영 부담을 가늠할 것."
        ),
        "caveat": (
            "이 곡선은 학습에 쓴 같은 데이터에서 나온 과거적합 수치다. 전향적 "
            "그림자 검증에서 다시 그려야 실제 운영점이 된다."
        ),
    }

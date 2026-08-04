"""Tier 2 전향적(out-of-sample) 평가 — 특징을 손대기 전에 '좋아졌는지 알 수 있게' 만든다.

배경: nowcast_dataset.train_baseline이 내는 재현율·정밀도는 **학습에 쓴 그 데이터를
다시 채점한 값**이다(train_accuracy). 그 숫자로는 특징을 추가했을 때 판별력이 정말
올랐는지, 아니면 그냥 학습 데이터를 더 잘 외운 건지 구분할 수 없다. 특징을 늘릴수록
학습 성적은 거의 항상 올라가기 때문에, 평가 장치 없이 특징부터 추가하면 **좋아졌다는
착각만 얻는다.**

그래서 여기서는 시간 전진 검증(forward-chaining, rolling origin)을 한다:
  과거 구간으로만 학습 → 그 다음 구간을 채점 → 원점을 앞으로 밀며 반복
각 예측은 '그 시점에 실제로 알 수 없던 미래'에 대한 것이라, 운영에서 나올 성능에
가깝다. 폴드별 out-of-sample 예측을 모아 하나의 혼동행렬·곡선을 만든다.

★ 정직성 ★
- 미래를 학습에 절대 넣지 않는다(as_of 기준 엄격 분리). 표준화 파라미터(평균·표준편차)도
  학습 구간에서만 계산된다 — train_baseline이 학습 행으로만 계산하므로 자동 보장.
- 학습 구간에 양성/음성이 부족한 폴드는 건너뛰고, 몇 개를 건너뛰었는지 보고한다.
  억지로 채워 넣은 성능을 만들지 않는다.
- 폴드가 하나도 성립하지 않으면 evaluated=False로 거부한다.
"""
from __future__ import annotations
import datetime as dt

from .nowcast_dataset import assemble_dataset, train_baseline, dataset_readiness
from .nowcast_threshold import score_rows, operating_point, DEFAULT_THRESHOLDS, diagnose_curve

# 검정 구간에 양성이 이만큼도 없으면 그 폴드의 재현율은 의미가 없다 — 건너뛴다.
MIN_TEST_POSITIVES = 3


def _as_of(row: dict) -> dt.date:
    return dt.date.fromisoformat(row["as_of"])


def temporal_folds(rows: list[dict], n_folds: int = 4) -> list[tuple[list[dict], list[dict]]]:
    """확장창 시간분할 — [과거 전체]로 학습하고 [바로 다음 구간]을 검정한다.

    경계는 '행 개수'가 아니라 **양성이 고르게 나뉘도록 양성 시점 분위수**로 잡는다.
    행 기준으로 자르면 신호 없는 빈 행 3,893개가 경계를 지배해 검정 구간에 양성이
    한 건도 없는 폴드가 생긴다(실제로 그렇게 나온다)."""
    pos_dates = sorted(_as_of(r) for r in rows if r["label"] == 1)
    if len(pos_dates) < (n_folds + 1) * MIN_TEST_POSITIVES:
        return []
    # 양성을 n_folds+1 등분한 경계 — 첫 구간은 최초 학습용이라 검정하지 않는다.
    step = len(pos_dates) / (n_folds + 1)
    cuts = [pos_dates[min(len(pos_dates) - 1, int(step * (i + 1)))] for i in range(n_folds)]

    folds = []
    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else None
        train = [r for r in rows if _as_of(r) < cut]
        test = [r for r in rows if cut <= _as_of(r) and (nxt is None or _as_of(r) < nxt)]
        folds.append((train, test))
    return folds


def coverage_split(rows: list[dict]) -> dict:
    """'데이터가 없어서 못 잡은 것'과 '데이터가 있는데 못 잡은 것'을 나눈다.

    이 둘을 섞으면 진단이 정확히 반대로 나온다. 실측에서 놓친 양성 14건이 **전부**
    신호창이 완전히 빈 행이었다 — 특징을 아무리 더해도 0벡터에서 발병을 예측할 수는
    없다. 그런데 합산 재현율만 보면 '모델 판별력이 부족하다'로 읽혀 특징 공학에
    시간을 쓰게 된다. 실제로 필요한 건 수집 확대다.

    반대로 오경보는 전부 신호가 있는 행에서 났다 — 그쪽은 진짜 판별력 문제다."""
    pos = [r for r in rows if r["label"] == 1]
    blind = [r for r in pos if r["features"].get("signal_count", 0) == 0]
    return {
        "positives": len(pos),
        "positives_with_signal": len(pos) - len(blind),
        "positives_blind": len(blind),
        # 어떤 모델도 넘을 수 없는 재현율 상한 — 빈 벡터는 학습 대상이 아니다.
        "max_achievable_sensitivity": (round((len(pos) - len(blind)) / len(pos), 3)
                                       if pos else None),
        "blind_examples": [{"country": r["country"], "as_of": r["as_of"]}
                           for r in sorted(blind, key=lambda x: x["as_of"])[:20]],
        "note": ("blind = 선언 직전 lookback 창에 신호가 한 건도 없던 경우. "
                 "모델·특징 문제가 아니라 수집 커버리지 문제이며, 재현율 상한을 "
                 "그만큼 깎는다. 판별력 개선 효과는 신호가 있는 행에서 봐야 한다."),
    }


def evaluate_temporal(rows: list[dict] | None = None, n_folds: int = 4,
                      thresholds: list[float] | None = None) -> dict:
    """시간 전진 검증. 폴드별 out-of-sample 예측을 모아 정직한 운영특성 곡선을 낸다."""
    rows = assemble_dataset() if rows is None else rows
    folds = temporal_folds(rows, n_folds)
    if not folds:
        return {"evaluated": False,
                "reason": f"양성 표본이 시간분할에 부족 — 폴드당 최소 {MIN_TEST_POSITIVES}건 필요",
                "readiness": dataset_readiness(rows)}

    pooled: list[tuple[float, int]] = []
    details = []
    skipped = 0
    for i, (train, test) in enumerate(folds):
        test_pos = sum(r["label"] for r in test)
        model = train_baseline(train)
        if not model.get("trained") or test_pos < MIN_TEST_POSITIVES:
            skipped += 1
            details.append({
                "fold": i, "used": False,
                "reason": ("학습 구간 표본 부족" if not model.get("trained")
                           else f"검정 구간 양성 {test_pos}건 < {MIN_TEST_POSITIVES}"),
                "train_n": len(train), "test_n": len(test), "test_positives": test_pos,
            })
            continue
        scored = score_rows(test, model)
        pooled.extend(scored)
        point = operating_point(scored, 0.5)
        details.append({
            "fold": i, "used": True,
            "train_n": len(train), "train_positives": model["positives"],
            "test_n": len(test), "test_positives": test_pos,
            "test_sensitivity": point["sensitivity"],
            "test_ppv": point["ppv"],
            "train_sensitivity_insample": model["positive_recall"],
        })

    if not pooled:
        return {"evaluated": False, "reason": "성립한 폴드가 없음 — 전향적 평가 불가",
                "folds": details, "readiness": dataset_readiness(rows)}

    curve = [operating_point(pooled, t) for t in (thresholds or DEFAULT_THRESHOLDS)]
    default = operating_point(pooled, 0.5)
    cov = coverage_split([r for _, (_, te) in enumerate(folds) for r in te])
    # 커버리지 상한을 감안한 '조건부 재현율' — 잡을 수 있었던 것 중 얼마를 잡았나.
    ceiling = cov["max_achievable_sensitivity"]
    sens = default["sensitivity"]
    conditional = (round(min(1.0, sens / ceiling), 3)
                   if (sens is not None and ceiling) else None)
    return {
        "evaluated": True,
        "method": "forward_chaining_temporal_holdout",
        "coverage": cov,
        # 이 둘을 같이 봐야 '수집을 늘려야 하나, 특징을 늘려야 하나'가 갈린다.
        "sensitivity_ceiling_from_coverage": ceiling,
        "conditional_sensitivity": conditional,
        "folds_total": len(folds),
        "folds_used": len(folds) - skipped,
        "folds_skipped": skipped,
        "fold_details": details,
        "pooled_n": len(pooled),
        "pooled_positives": sum(1 for _, y in pooled if y == 1),
        "out_of_sample": default,
        "curve": curve,
        "diagnosis": diagnose_curve(curve),
        "note": ("이 숫자는 '그 시점에 알 수 없던 미래'를 채점한 것이라 학습 성적보다 "
                 "낮은 게 정상이다. 특징을 바꿀 때는 학습 성적이 아니라 **이 값**을 "
                 "비교해야 한다."),
    }


def compare_feature_sets(rows_a: list[dict], rows_b: list[dict],
                         label_a: str = "before", label_b: str = "after",
                         n_folds: int = 4) -> dict:
    """두 특징셋을 같은 시간분할로 비교 — 판별력이 실제로 올랐는지 판정.

    같은 as_of 격자에서 만든 두 데이터셋이어야 공정하다(행 수가 다르면 비교 무효)."""
    a = evaluate_temporal(rows_a, n_folds)
    b = evaluate_temporal(rows_b, n_folds)
    if not (a.get("evaluated") and b.get("evaluated")):
        return {"compared": False, "reason": "한쪽 이상이 평가 불가", label_a: a, label_b: b}
    if a["pooled_n"] != b["pooled_n"]:
        return {"compared": False,
                "reason": f"검정 표본 수가 다름({a['pooled_n']} vs {b['pooled_n']}) — 비교 무효",
                label_a: a, label_b: b}

    pa, pb = a["out_of_sample"], b["out_of_sample"]

    def _d(k):
        va, vb = pa.get(k), pb.get(k)
        return None if va is None or vb is None else round(vb - va, 3)

    return {
        "compared": True,
        "pooled_n": a["pooled_n"],
        "pooled_positives": a["pooled_positives"],
        label_a: {k: pa.get(k) for k in ("sensitivity", "ppv", "false_alarm_rate",
                                         "specificity", "alerts_per_100_windows")},
        label_b: {k: pb.get(k) for k in ("sensitivity", "ppv", "false_alarm_rate",
                                         "specificity", "alerts_per_100_windows")},
        "delta": {"sensitivity": _d("sensitivity"), "ppv": _d("ppv"),
                  "false_alarm_rate": _d("false_alarm_rate"),
                  "alerts_per_100_windows": _d("alerts_per_100_windows")},
        "verdict": _verdict(_d("sensitivity"), _d("ppv")),
    }


def _verdict(d_sens: float | None, d_ppv: float | None) -> str:
    if d_sens is None or d_ppv is None:
        return "판정 불가 — 지표가 비어 있음."
    if d_sens >= 0 and d_ppv > 0:
        return f"판별력 향상 — 민감도 {d_sens:+.3f}, 정밀도 {d_ppv:+.3f}(재현율 손실 없음)."
    if d_ppv > 0 > d_sens:
        return (f"정밀도 {d_ppv:+.3f} 개선 대신 민감도 {d_sens:+.3f} 손실 — "
                "트레이드오프이지 순수 향상이 아니다. 운영 정책으로 판단할 것.")
    if d_ppv <= 0 and d_sens <= 0:
        return f"향상 없음 — 민감도 {d_sens:+.3f}, 정밀도 {d_ppv:+.3f}. 특징 추가를 되돌릴 것."
    return f"민감도 {d_sens:+.3f} / 정밀도 {d_ppv:+.3f} — 혼재. 운영 목표에 따라 판단."

"""Stage 0 유전체 신호 — Evo2(유전체 파운데이션 모델)로 서열의 '자연스러움'을 실측.

배경: genome_signals.py는 CAI·CpG O/E 같은 **점통계**를 계산한다. 이 지표들은
조성(composition)만 보기 때문에, 조성은 자연스럽되 순서가 부자연스러운 서열
(예: 조각 이어붙이기·재조합 산물)을 놓친다. Evo2는 실제 자연 유전체 수십억
염기로 학습된 유전체 언어모델이라 '순서의 자연스러움'을 직접 평가할 수 있다.

방법(teacher-forced next-token agreement):
  서열 여러 지점에서 앞부분(context)만 모델에 주고 다음 염기 몇 개를 예측시킨 뒤,
  **실제 서열과 얼마나 일치하는지** 센다. 자연 서열이면 모델이 잘 맞히고, 자연
  유전체 통계에서 벗어난 구간이면 못 맞힌다.

실측 판별력(2026-07-30, evo2-40b NIM, 인간 mtDNA NC_012920.1 1-1200bp):
  - 실제 자연서열      : 일치율 90.0%, 평균 확신도 0.883
  - 조성 동일 셔플서열 : 일치율 38.3%, 평균 확신도 0.377
  조성이 완전히 같아도 순서가 깨지면 일치율이 51.7%p 떨어진다 — 점통계가 못 잡는
  각도를 실제로 잡는다는 뜻. 임계값은 이 실측에 근거해 잡았다.

★ 안전 경계선(genome_signals.py와 동일) ★
- **방어적 스크리닝 전용**: 주어진 서열이 자연 유전체 통계에서 벗어나는지 '탐지·
  플래그'만 한다. 서열을 설계·생성·최적화하거나 스크리닝 회피법은 제공하지 않는다.
  모델이 생성한 염기는 실제 서열과 **대조하는 용도로만** 쓰고 반환하지 않는다.
- 낮은 일치율 = '인공 설계' 판정이 **아니다**. 학습 데이터에 드문 자연 계통,
  저품질 시퀀싱, 비코딩 반복영역도 낮게 나온다. 어디까지나 추가검토 우선순위다.
"""
from __future__ import annotations

import os

import requests

NIM_URL = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate"
MODEL = "evo2-40b"
TIMEOUT = 120

# 실측 기반 참고범위(위 모듈 docstring의 검증값 기준).
_REF = {
    "match_rate_natural": 0.90,      # 실제 자연서열 실측
    "match_rate_shuffled": 0.38,     # 조성 동일 셔플 실측(= 순서정보 파괴 시 바닥)
    "match_rate_low": 0.55,          # 이보다 낮으면 '자연 유전체 통계에서 이탈' 플래그
    "window_confident_conf": 0.70,   # 모델이 이만큼 확신했는데
    "window_confident_wrong": 0.40,  # 일치율이 이보다 낮으면 = 확신하고 틀림 → 국소 이상
}


def _predict_next(prefix: str, n_tokens: int, api_key: str) -> tuple[str, list[float]]:
    """prefix 다음에 올 염기 n_tokens개를 그리디(top_k=1)로 예측시킨다.

    top_k=1로 고정하는 이유: 여기서 필요한 건 '모델이 가장 자연스럽다고 보는 다음
    염기'와 실제의 일치 여부이지 다양한 후보 생성이 아니다. 생성물은 대조에만 쓴다."""
    r = requests.post(
        NIM_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"sequence": prefix, "num_tokens": n_tokens, "top_k": 1,
              "enable_sampled_probs": True},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    return (data.get("sequence") or "").upper(), (data.get("sampled_probs") or [])


def score_naturalness(raw: str, api_key: str | None = None, n_windows: int = 6,
                      context: int = 512, predict: int = 12) -> dict:
    """서열의 자연스러움을 Evo2 next-token 일치율로 실측. 실패해도 예외를 던지지
    않고 {"ok": False, ...}를 돌려준다 — 외부 API 장애가 Stage 0 스크리닝 전체를
    막으면 안 되기 때문(genome_signals의 순수 통계는 그대로 유효하다).

    n_windows개 지점을 서열 전체에 균등 배치해 각각 API 1회씩 호출한다."""
    key = api_key or os.environ.get("NVIDIA_API_KEY")
    if not key:
        return {"ok": False, "reason": "NVIDIA_API_KEY 없음 — Evo2 자연스러움 평가 생략",
                "is_screening_only": True}

    # genome_signals와 같은 방식으로 정제(모호 염기 경계로 끊고 최장 구간만).
    from .genome_signals import clean_segments

    segments = clean_segments(raw)
    seq = max(segments, key=len) if segments else ""
    usable = len(seq) - context - predict
    if usable <= 0:
        return {"ok": False,
                "reason": f"연속 구간이 {context + predict}bp 미만 — Evo2 평가 불가"
                          f"(분석가능 최장구간 {len(seq)}bp)",
                "is_screening_only": True}

    step = max(1, usable // max(n_windows, 1))
    windows: list[dict] = []
    matches = total = 0
    confs: list[float] = []
    errors = 0

    for w in range(n_windows):
        anchor = context + w * step
        if anchor + predict > len(seq):
            break
        prefix, actual = seq[anchor - context:anchor], seq[anchor:anchor + predict]
        try:
            predicted, probs = _predict_next(prefix, predict, key)
        except Exception as e:
            errors += 1
            windows.append({"position": anchor, "ok": False, "error": type(e).__name__})
            continue

        w_match = sum(1 for a, b in zip(actual, predicted) if a == b)
        w_total = min(len(actual), len(predicted))
        if not w_total:
            errors += 1
            continue
        w_conf = round(sum(probs) / len(probs), 4) if probs else None
        matches += w_match
        total += w_total
        confs.extend(probs)
        windows.append({
            "position": anchor,
            "ok": True,
            "match_rate": round(w_match / w_total, 4),
            "bases_compared": w_total,
            "mean_confidence": w_conf,
            # 확신하고 틀린 구간 = 국소 이상 후보(삽입·재조합 경계 등)
            "confidently_wrong": bool(
                w_conf is not None
                and w_conf >= _REF["window_confident_conf"]
                and (w_match / w_total) < _REF["window_confident_wrong"]
            ),
        })

    if not total:
        return {"ok": False, "reason": f"Evo2 호출이 모두 실패({errors}건) — 네트워크·키·쿼터 확인",
                "is_screening_only": True}

    match_rate = round(matches / total, 4)
    mean_conf = round(sum(confs) / len(confs), 4) if confs else None
    anomalous = [w for w in windows if w.get("confidently_wrong")]

    flags: list[dict] = []
    if match_rate < _REF["match_rate_low"]:
        flags.append({
            "metric": "evo2_match_rate", "value": match_rate,
            "note": f"Evo2 예측 일치율 {match_rate:.1%} < 참고 {_REF['match_rate_low']:.0%} — "
                    f"자연 유전체 통계에서 이탈(참고: 자연서열 실측 "
                    f"{_REF['match_rate_natural']:.0%}, 셔플 {_REF['match_rate_shuffled']:.0%})",
        })
    if anomalous:
        flags.append({
            "metric": "evo2_local_anomaly",
            "value": [w["position"] for w in anomalous],
            "note": f"모델이 확신했는데 빗나간 구간 {len(anomalous)}개 — 삽입·재조합 경계 후보",
        })

    return {
        "ok": True,
        "model": MODEL,
        "match_rate": match_rate,
        "mean_confidence": mean_conf,
        "bases_compared": total,
        "windows_scored": len([w for w in windows if w.get("ok")]),
        "windows_failed": errors,
        "context_bp": context,
        "predicted_bp_per_window": predict,
        "windows": windows,
        "local_anomaly_positions": [w["position"] for w in anomalous],
        "flags": flags,
        "flag_count": len(flags),
        "is_screening_only": True,
        "reference_ranges": _REF,
        "method": (
            "teacher-forced next-token agreement — 서열 여러 지점에서 앞 "
            f"{context}bp만 주고 다음 {predict}bp를 그리디 예측시켜 실제와 대조. "
            "생성 서열은 대조용으로만 쓰고 반환하지 않음(방어적 탐지 전용)."
        ),
        "disclaimer": (
            "낮은 일치율은 '인공 설계' 판정이 아니라 '자연 유전체 통계에서 벗어남'이라는 "
            "추가검토 우선순위 신호다. 학습 데이터에 드문 자연 계통·저품질 시퀀싱·반복영역도 "
            "낮게 나올 수 있으며, 최종 판단은 전문가·계통발생·습식실험 확인이 필요하다."
        ),
    }

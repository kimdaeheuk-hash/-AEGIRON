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

★★ 적용범위 한계(반드시 읽을 것) ★★
Evo2는 **진핵숙주 감염 바이러스를 학습에서 제외**했다(Arc의 바이오안보 조치).
그래서 코로나·독감·에볼라 같은 자연 그대로의 바이러스 유전체도 '셔플 수준'
점수가 나온다 — 그대로 플래그하면 **감시 대상 병원체 전부가 오탐**이 된다.

분류군별 실측(2026-07-30, 각 NCBI 레퍼런스 4kb, 자연서열 그대로):
  박테리오파지 람다 NC_001416.1   일치율 100.0%  확신 0.998   ← 세균 감염 바이러스
  인간 mtDNA      NC_012920.1    일치율  91.7%  확신 0.898
  효모 16번염색체  NC_001148.4    일치율  90.3%  확신 0.944
  대장균          NC_000913.3    일치율  87.5%  확신 0.882
  SARS-CoV-2      NC_045512.2    일치율  33.3%  확신 0.443   ← 진핵 감염 바이러스
  인플루엔자A HA   NC_026433.1    일치율  31.9%  확신 0.392   ← 진핵 감염 바이러스
  에볼라 자이르    NC_002549.1    일치율  25.0%  확신 0.450   ← 진핵 감염 바이러스
  진핵감염 바이러스 30.1% vs 그 외 92.4% (차이 62.3%p). 파지가 100%인데 진핵감염
  바이러스만 바닥인 게 '학습 제외' 가설의 직접 증거다.

그럼 '바이러스끼리 상대비교'로는 되지 않나? — 안 된다. 실측으로 확인함
(2026-07-31, 성공기준을 미리 정해두고 실험. scripts/validate_evo2_applicability.py로 재현 가능):
  자연 vs 조성동일 셔플 일치율 차이 —
    인플루엔자A +11.7% · SARS-CoV-2 +10.0% · 에볼라 +5.8% · MERS -0.1% · 뎅기1형 -11.7%
    평균 +3.2%(기준 15%p 미달), 자연 바이러스 표준편차 7.3%(기준 5%p 미달)
  키메라(SARS-CoV-2 + 에볼라 이어붙임) 접합부: 그 외 구간보다 오히려 6.5%p **높음**(부호 반대)
  뎅기는 셔플이 자연보다 높게 나왔고, 자연 바이러스 평균 33.3%는 무작위로 찍는
  수준(25%)보다 8.3%p 위에 불과하다 — '신호가 약한' 게 아니라 '신호가 없는' 상태.

따라서 아래 게이팅은 예방적 조치가 아니라 **실측으로 확인된 한계**다. 우회하려면
Evo2가 아닌 다른 모델이 필요하다(ESM-2는 UniRef 학습이라 바이러스 단백질을 포함하나,
2026-07-31 기준 NIM 엔드포인트가 HTTP 500으로 서버측 오류 — 재시도 필요).

organism_domain으로 적용범위를 **선언받아** 판정한다. 선언이 없거나
진핵감염 바이러스면 점수는 계산·보고하되 플래그는 올리지 않는다(applicable=False).
세균·고균(탄저·페스트·야토병 등 실제 생물무기 위협 다수)과 진핵 유전체,
파지는 적용범위 안이라 정상 작동한다.

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
    "match_rate_natural": 0.90,      # 실제 자연서열 실측(적용범위 안)
    "match_rate_shuffled": 0.38,     # 조성 동일 셔플 실측(= 순서정보 파괴 시 바닥)
    "match_rate_low": 0.55,          # 이보다 낮으면 '자연 유전체 통계에서 이탈' 플래그
    "window_confident_conf": 0.70,   # 모델이 이만큼 확신했는데
    "window_confident_wrong": 0.40,  # 일치율이 이보다 낮으면 = 확신하고 틀림 → 국소 이상
}

# 적용범위(applicability domain). Evo2 학습 구성에 따라 판정 가능 여부가 갈린다 —
# 위 docstring의 분류군별 실측이 근거. 값은 호출측이 '선언'한다(서열만으로 분류군을
# 추정하지 않는다 — 추정 실패가 곧 오탐이라 선언받는 게 정직하다).
APPLICABILITY = {
    "bacteria_archaea": {"applicable": True,  "measured_natural": 0.875,
                         "note": "대장균 NC_000913.3 실측 87.5% — 탄저·페스트·야토병 등 세균 위협 포함"},
    "eukaryote":        {"applicable": True,  "measured_natural": 0.903,
                         "note": "효모 NC_001148.4 90.3%, 인간 mtDNA NC_012920.1 91.7% 실측"},
    "phage":            {"applicable": True,  "measured_natural": 1.000,
                         "note": "람다파지 NC_001416.1 실측 100% — 세균 감염 바이러스는 학습에 포함됨"},
    "eukaryotic_virus": {"applicable": False, "measured_natural": 0.301,
                         "note": "Evo2가 진핵숙주 감염 바이러스를 학습에서 제외(Arc 바이오안보 조치) — "
                                 "자연서열도 30% 수준(무작위 25%와 근접)이라 인공 여부를 가릴 수 없음. "
                                 "바이러스끼리 상대비교도 실패함(2026-07-31 실측: 자연-셔플 차이 +3.2%, "
                                 "뎅기는 부호 반대, 키메라 접합부도 부호 반대). "
                                 "코로나·독감·에볼라 등이 여기 해당."},
    "unknown":          {"applicable": False, "measured_natural": None,
                         "note": "분류군 미선언 — 낮은 점수가 '인공'인지 '적용범위 밖'인지 "
                                 "구분할 수 없어 플래그를 올리지 않음. organism_domain을 선언하면 판정함."},
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
                      context: int = 512, predict: int = 12,
                      organism_domain: str = "unknown") -> dict:
    """서열의 자연스러움을 Evo2 next-token 일치율로 실측. 실패해도 예외를 던지지
    않고 {"ok": False, ...}를 돌려준다 — 외부 API 장애가 Stage 0 스크리닝 전체를
    막으면 안 되기 때문(genome_signals의 순수 통계는 그대로 유효하다).

    organism_domain이 적용범위 밖(진핵감염 바이러스·미선언)이면 점수는 계산해
    보고하되 플래그는 올리지 않는다 — Evo2가 그 분류군에서는 자연서열도 낮게
    주기 때문에 플래그가 곧 오탐이 된다(APPLICABILITY 참조).

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

    domain = APPLICABILITY.get(organism_domain) or APPLICABILITY["unknown"]
    applicable = domain["applicable"]

    # 적용범위 밖이면 점수는 그대로 보고하되 플래그는 올리지 않는다 — Evo2가
    # 그 분류군에선 자연서열도 낮게 주므로 플래그가 곧 오탐이기 때문.
    flags: list[dict] = []
    if applicable:
        if match_rate < _REF["match_rate_low"]:
            flags.append({
                "metric": "evo2_match_rate", "value": match_rate,
                "note": f"Evo2 예측 일치율 {match_rate:.1%} < 참고 {_REF['match_rate_low']:.0%} — "
                        f"자연 유전체 통계에서 이탈(참고: 같은 분류군 자연서열 실측 "
                        f"{domain['measured_natural']:.0%}, 셔플 {_REF['match_rate_shuffled']:.0%})",
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
        # 적용범위 판정 — 낮은 점수를 '인공 신호'로 읽어도 되는지 여부.
        "organism_domain": organism_domain,
        "applicable": applicable,
        "applicability_note": domain["note"],
        "domain_natural_baseline": domain["measured_natural"],
        "suppressed_flags": None if applicable else (
            f"적용범위 밖이라 플래그를 올리지 않음(일치율 {match_rate:.1%}는 참고값). "
            f"{domain['note']}"
        ),
        "reference_ranges": _REF,
        "method": (
            "teacher-forced next-token agreement — 서열 여러 지점에서 앞 "
            f"{context}bp만 주고 다음 {predict}bp를 그리디 예측시켜 실제와 대조. "
            "생성 서열은 대조용으로만 쓰고 반환하지 않음(방어적 탐지 전용)."
        ),
        "disclaimer": (
            "낮은 일치율은 '인공 설계' 판정이 아니라 '자연 유전체 통계에서 벗어남'이라는 "
            "추가검토 우선순위 신호다. 학습 데이터에 드문 자연 계통·저품질 시퀀싱·반복영역도 "
            "낮게 나올 수 있으며, 최종 판단은 전문가·계통발생·습식실험 확인이 필요하다. "
            "특히 진핵숙주 감염 바이러스(코로나·독감·에볼라 등)는 Evo2 학습에서 제외되어 "
            "자연서열도 30% 수준이므로 이 지표로 판정할 수 없다(applicable=False)."
        ),
    }

"""Global Anomaly Index — collector.py가 쌓은 누적 신호를 6계층 가중합산.

인수인계서 Part5 ①②③: 신호원마다 "오늘값 vs 과거평균" 이상도(raw_score)를 구하고
출처신뢰도(trust.py, ③)를 곱해 trusted_score를 만든 뒤, 6계층(공식·비공식·행동·
환경·동물·설명불가)으로 묶어 가중합산한 단일 점수.

층 배정은 인수인계서가 신호원 목록까지 정해주지 않아서 다음 기준으로 직접 매핑함
(signal_metrics.py의 LAYERS 참고):
  공식    — 정부기관이 직접 운영하는 API/RSS (KDCA, WHO, CDC EID, 홍콩 CHP, 일본 IDWR, 브라질 InfoDengue)
  비공식  — 학계 큐레이션 매체(CIDRAP) + AI가 검색해 추출한 수치(Africa CDC 앵커, 직접 API 아님)
  행동    — 검색·열람 행태(네이버 검색비율, Wikipedia 조회량, PubMed 논문수)
  환경    — 하수역학(CDC NWSS) — 사람 보고가 아니라 환경 샘플이라 공식신호와 분리
  동물    — CIDRAP 조류인플루엔자 피드를 동물발 신호의 대체재로 사용(전용 동물감시 소스 없음)
  설명불가 — Polymarket "신규 팬데믹" 시장가 — 특정 질병명에 묶이지 않은 군중의 위험인식
"""
from __future__ import annotations
import statistics

from .trust import trust_for
from .signal_metrics import (LAYERS, MIN_HISTORY, SLOW_CADENCE_METRICS, collapse_repeats,
                             has_enough_distinct_history, load_records)

MIN_RELIABLE_SAMPLES = 14  # free_sources 누적이 이 미만이면 caveat 표시


def _latest_value(series: list[float | None]) -> float | None:
    """점수의 입력이 된 '최신 관측값'. _anomaly_score 와 **같은 규칙**(마지막
    non-None)을 써야 한다 — 두 값이 어긋나면 경보 문턱이 점수와 다른 숫자를
    보고 판단하게 된다(tests/test_alert_minimum.py 가 이걸 고정한다)."""
    cleaned = [v for v in series if v is not None]
    return cleaned[-1] if cleaned else None


def _anomaly_score(series: list[float | None]) -> float | None:
    """최신값의 과거 대비 이상도. z-score를 [0,3]에 클램프해 0~100으로 환산.

    음수 방향(평소보다 낮음)은 0점 — 신호 감소는 '부정적 공간 감시'(negative_space.py)가
    다룰 영역이라 여기서는 증가만 이상으로 본다(인수인계서 Part5 ① 개별 공식과 동일한 전제).
    """
    cleaned = [v for v in series if v is not None]
    if len(cleaned) < MIN_HISTORY + 1:
        return None
    *history, latest = cleaned
    # ★ 과거가 '변해온 적이 있어야' z 를 낸다 ★ 표본은 많은데 전부 같은 값이면
    # 표준편차가 '값이 얼마나 변하는가'가 아니라 '값이 언제 바뀌었나'를 재게 되고,
    # 첫 변화에서 z 가 상한까지 튄다(2026-09-20 naver_covid_ratio 실측).
    # 판정하지 않는다 — 없는 것을 0 으로도, 100 으로도 만들지 않는다.
    if not has_enough_distinct_history(history):
        return None
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    if stdev == 0:
        # ★ 위 문턱을 통과하면 여기 못 온다 ★ 서로 다른 값이 3개면 분산은 0 이
        # 아니다. 0 나누기 방어로만 남긴다 — **"과거가 평평하면 0점"으로 읽지
        # 마라.** 그 오해가 09-20 사고의 뿌리였다: 0점은 '이상 없음'이라는
        # 판정이고, 그때 우리가 아는 건 '판정할 수 없다'뿐이었다.
        return None
    z = (latest - mean) / stdev
    return round(max(0.0, min(z, 3.0)) / 3.0 * 100, 1)


def _baseline_mean(series: list[float | None]) -> float | None:
    """`_anomaly_score` 가 쓰는 과거(최신값 제외)의 평균. 점수는 안 바꾼다 — 승격 자리가
    '관측값이 평소 대비 몇 σ 인가'를 카운트 기준으로 다시 볼 수 있게 내보낼 뿐이다.

    `_anomaly_score` 와 **같은 과거**를 쓴다(None 제거 · 마지막 하나가 최신값). 판정할 수
    없는 경우(표본 부족)는 None — 모르는 것을 0 으로 쓰지 않는다.
    """
    cleaned = [v for v in series if v is not None]
    if len(cleaned) < MIN_HISTORY + 1:
        return None
    return round(statistics.mean(cleaned[:-1]), 4)


def _previous_distinct(series: list[float | None]) -> float | None:
    """최신값과 **다른** 가장 최근 관측값. 없으면 None.

    ★ 왜 필요한가 ★ (2026-10-18, PR #83 자기검토) 주간 원천(CDC NWSS)은 같은 값을 매시간 다시 기록한다. 그래서
    `_baseline_mean` 은 새 값이 들어온 뒤 시간마다 그 값 쪽으로 끌려간다(10-16~10-18 평소 약 87,690 → 108,705,
    시간당 약 650). '평소 대비 몇 배' 만 보면 같은 주 안에서 배수가 저절로 줄어 판정이 바뀐다 — 값은 그대로인데.
    직전의 다른 값(= 지난 창의 값)은 그 오염을 안 받는다. 점수·지수에는 영향이 없다(승격 자리만 쓴다).
    """
    cleaned = [v for v in series if v is not None]
    if not cleaned:
        return None
    latest = cleaned[-1]
    for v in reversed(cleaned[:-1]):
        if v != latest:
            return v
    return None


def _tier(gai: float | None) -> str | None:
    if gai is None:
        return None
    if gai >= 90:
        return "🔴 위험"
    if gai >= 80:
        return "🟠 경보"
    if gai >= 70:
        return "🟡 주의"
    return "🟢 정상"


def compute_gai() -> dict:
    records = load_records()
    n_free = sum(1 for r in records if r.get("type") == "free_sources")
    n_ai = sum(1 for r in records if r.get("type") == "ai_sources")

    layer_results = {}
    for key, cfg in LAYERS.items():
        metric_scores = []
        for metric_id, rtype, extractor, trust_category in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            if metric_id in SLOW_CADENCE_METRICS:
                # 원천보다 자주 다시 기록되는 값 — 같은 값의 반복을 한 관측으로 접는다(signal_metrics 주석).
                series = collapse_repeats(series)
            raw_score = _anomaly_score(series)
            if raw_score is None:
                continue
            trust = trust_for(trust_category)
            metric_scores.append({
                "metric": metric_id,
                # 점수를 만든 관측값 자체. 경보 최소값 판정(signal_metrics.
                # meets_alert_minimum)이 이걸 보고, 사람도 "몇 점"이 아니라
                # "몇 건인데 몇 점"을 볼 수 있다 — 근거가 숫자에서 떨어져
                # 나가지 않게 하는 것과 같은 이유다.
                "latest": _latest_value(series),
                # 점수를 만든 과거의 평균. 경보 승격 자리의 카운트 유의도(signal_metrics.
                # meets_count_significance)가 쓴다. 점수·지수에는 영향이 없다.
                "baseline_mean": _baseline_mean(series),
                # 최신값과 다른 가장 최근 값 — 같은 주간 값이 매시간 다시 쌓여 평균이 끌려가도 흔들리지 않는 비교점.
                # 경보 승격 자리의 비현실적 점프 판정(signal_metrics.implausible_jump)이 쓴다. 점수에는 영향이 없다.
                "previous_distinct": _previous_distinct(series),
                "raw_score": raw_score,
                "trust": trust,
                "trusted_score": round(raw_score * trust, 1),
            })
        layer_score = (
            round(statistics.mean(m["trusted_score"] for m in metric_scores), 1)
            if metric_scores else None
        )
        layer_results[key] = {
            "label": cfg["label"],
            "weight": cfg["weight"],
            "score": layer_score,
            "metrics": metric_scores,
        }

    available = {k: v for k, v in layer_results.items() if v["score"] is not None}
    if available:
        weight_sum = sum(v["weight"] for v in available.values())
        gai = round(sum(v["score"] * v["weight"] for v in available.values()) / weight_sum, 1)
    else:
        gai = None

    result = {
        "gai": gai,
        "tier": _tier(gai),
        # anomaly_engine.py·forecast_engine.py도 0~100 점수를 내지만 계산식이
        # 서로 다르다(여긴 6계층 신뢰도가중 z-score 합산). 같은 "70/80/90점"
        # 언어를 쓰는 다른 스코어와 섞이지 않도록 출처를 명시해서 내보낸다.
        "score_model": "gai_v1_layered_trust_weighted",
        "layers": layer_results,
        "sample_size": {"free_sources": n_free, "ai_sources": n_ai},
    }
    if n_free < MIN_RELIABLE_SAMPLES:
        result["caveat"] = (
            f"누적 샘플 {n_free}건(free_sources) — {MIN_RELIABLE_SAMPLES}건 미만이라 "
            "이상도 통계의 신뢰도가 낮음. 수집기가 더 쌓일수록 정확해짐."
        )
    return result

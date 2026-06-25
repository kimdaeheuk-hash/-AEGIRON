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
from .signal_metrics import LAYERS, MIN_HISTORY, load_records

MIN_RELIABLE_SAMPLES = 14  # free_sources 누적이 이 미만이면 caveat 표시


def _anomaly_score(series: list[float | None]) -> float | None:
    """최신값의 과거 대비 이상도. z-score를 [0,3]에 클램프해 0~100으로 환산.

    음수 방향(평소보다 낮음)은 0점 — 신호 감소는 '부정적 공간 감시'(negative_space.py)가
    다룰 영역이라 여기서는 증가만 이상으로 본다(인수인계서 Part5 ① 개별 공식과 동일한 전제).
    """
    cleaned = [v for v in series if v is not None]
    if len(cleaned) < MIN_HISTORY + 1:
        return None
    *history, latest = cleaned
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    if stdev == 0:
        return 0.0
    z = (latest - mean) / stdev
    return round(max(0.0, min(z, 3.0)) / 3.0 * 100, 1)


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
            raw_score = _anomaly_score(series)
            if raw_score is None:
                continue
            trust = trust_for(trust_category)
            metric_scores.append({
                "metric": metric_id,
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
        "layers": layer_results,
        "sample_size": {"free_sources": n_free, "ai_sources": n_ai},
    }
    if n_free < MIN_RELIABLE_SAMPLES:
        result["caveat"] = (
            f"누적 샘플 {n_free}건(free_sources) — {MIN_RELIABLE_SAMPLES}건 미만이라 "
            "이상도 통계의 신뢰도가 낮음. 수집기가 더 쌓일수록 정확해짐."
        )
    return result

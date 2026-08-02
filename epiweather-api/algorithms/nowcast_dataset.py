"""Tier 2 프레임워크 — '신호 → 실제 발병' 성과 학습셋 자동 조립 + 베이스라인 학습기.

배경(기술실사): 지금 이상탐지는 z-score/EARS 휴리스틱이다. Tier 2는 이걸 '아이기론
신호가 실제 발병으로 이어졌는가'를 학습한 모델로 대체하는 것 — 진짜 데이터 해자.
다만 이건 성과 라벨(신호→나중에 확인된 발병)이 쌓여야 유효하다. 그래서 이 모듈은
모델 성능을 지어내지 않고, **학습셋을 자동 조립하는 파이프라인 + 의존성 없는
베이스라인 + 데이터 충분성 게이트**만 제공한다. 운영이 지속되면 학습셋이 커지고,
그때 이 자리에서 실제 모델로 교체한다(training_data.py의 대칭 — 그건 추출 증류,
이건 성과 nowcasting).

★ 정직성 ★
- 데이터가 부족하면 sufficient_data=False로 명시하고 학습을 '거부'한다(소량 데이터
  과적합 방지). 지어낸 정확도를 내지 않는다.
- 라벨(실제 발병 선언)은 outbreak_timeline의 공식 선언 마일스톤에서만 온다.
- 베이스라인은 순수 파이썬 로지스틱 회귀(외부 ML 의존성 없음) — 재현 가능.
"""
from __future__ import annotations
import datetime as dt
import math

import db
from .country_risk import SIGNAL_TYPE_SEVERITY
from .knowledge_graph import _DECLARATION_MILESTONE_KEYS

# 학습에 최소 필요한 표본(honest 게이트 — 이 미만이면 학습 거부).
MIN_POSITIVES = 10
MIN_NEGATIVES = 10

# 특징 벡터 키(순서 고정 — 학습·추론 일관).
FEATURE_KEYS = (
    "signal_count", "weighted_severity_mean", "max_severity",
    "distinct_sources", "distinct_diseases", "recent7_count",
)

# outbreak_timeline event_id → 국가 ISO3(라벨 매핑). 명확한 것만.
EVENT_COUNTRY = {
    "covid19_wuhan_2019": "CHN",
    "ebola_drc_2026": "COD",
    "mers_saudi_2026": "SAU",
}


def _parse_date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def extract_features(window_signals: list[dict], as_of: dt.date) -> dict:
    """한 (국가, as_of) 스냅샷의 신호 특징. window_signals는 lookback 창 안의 신호."""
    if not window_signals:
        return {k: 0.0 for k in FEATURE_KEYS}
    sevs = [SIGNAL_TYPE_SEVERITY.get(s.get("signal_type"), 40) * (s.get("source_trust") or 0.5)
            for s in window_signals]
    recent7 = 0
    for s in window_signals:
        d = _parse_date(s.get("signal_date") or s.get("extracted_at"))
        if d and (as_of - d).days <= 7:
            recent7 += 1
    return {
        "signal_count": float(len(window_signals)),
        "weighted_severity_mean": round(sum(sevs) / len(sevs), 3),
        "max_severity": float(max(sevs)),
        "distinct_sources": float(len({s.get("source") for s in window_signals})),
        "distinct_diseases": float(len({s.get("disease") for s in window_signals if s.get("disease")})),
        "recent7_count": float(recent7),
    }


def _country_declarations() -> dict[str, list[dt.date]]:
    """국가별 공식 발병 선언일(라벨 소스)."""
    out: dict[str, list[dt.date]] = {}
    for e in db.list_timeline_events():
        country = EVENT_COUNTRY.get(e["event_id"])
        if not country:
            continue
        for m in db.get_timeline(e["event_id"]).get("milestones", []):
            if m["milestone"] in _DECLARATION_MILESTONE_KEYS:
                d = _parse_date(m["event_date"])
                if d:
                    out.setdefault(country, []).append(d)
    return out


def assemble_dataset(horizon_days: int = 30, lookback_days: int = 30,
                     step_days: int = 7, limit: int = 5000) -> list[dict]:
    """extracted_signals + outbreak_timeline → (특징 → 라벨) 성과 학습셋.
    라벨=1: as_of로부터 horizon_days 안에 그 국가에서 공식 발병 선언이 있었음."""
    signals = db.list_extracted_signals(limit=limit)
    by_country: dict[str, list[dict]] = {}
    dates: list[dt.date] = []
    for s in signals:
        c = s.get("country_iso3")
        if not c:
            continue
        d = _parse_date(s.get("signal_date") or s.get("extracted_at"))
        if d is None:
            continue
        s = {**s, "_date": d}
        by_country.setdefault(c, []).append(s)
        dates.append(d)
    if not dates:
        return []

    declarations = _country_declarations()
    start, end = min(dates), max(dates)
    rows: list[dict] = []
    for country, sigs in by_country.items():
        decls = declarations.get(country, [])
        as_of = start
        while as_of <= end:
            lo = as_of - dt.timedelta(days=lookback_days)
            window = [s for s in sigs if lo <= s["_date"] <= as_of]
            label = 1 if any(as_of < dd <= as_of + dt.timedelta(days=horizon_days) for dd in decls) else 0
            rows.append({
                "country": country, "as_of": as_of.isoformat(),
                "features": extract_features(window, as_of), "label": label,
            })
            as_of += dt.timedelta(days=step_days)
    return rows


def dataset_readiness(rows: list[dict]) -> dict:
    """학습 가능 여부를 정직하게 판정 — 표본·클래스 균형이 임계 미만이면 학습 거부."""
    pos = sum(1 for r in rows if r["label"] == 1)
    neg = len(rows) - pos
    sufficient = pos >= MIN_POSITIVES and neg >= MIN_NEGATIVES
    return {
        "total_examples": len(rows),
        "positives": pos,
        "negatives": neg,
        "min_required": {"positives": MIN_POSITIVES, "negatives": MIN_NEGATIVES},
        "sufficient_data": sufficient,
        "feature_keys": list(FEATURE_KEYS),
        "note": ("학습 가능 — 단 소량이면 전향적 검증 필수(과적합 주의)." if sufficient else
                 "표본/클래스 부족 — 학습 거부. 운영이 지속되며 성과 라벨이 쌓이면 자동으로 충족된다. "
                 "지어낸 성능을 내지 않는다."),
    }


def _vec(features: dict) -> list[float]:
    return [features.get(k, 0.0) for k in FEATURE_KEYS]


def train_baseline(rows: list[dict], iters: int = 300, lr: float = 0.1) -> dict:
    """순수 파이썬 로지스틱 회귀 베이스라인. 데이터 부족이면 학습 거부(정직).
    표준화 + 경사하강. 소량 학습 성능은 참고용이며 전향적 검증 전엔 신뢰 금지."""
    readiness = dataset_readiness(rows)
    if not readiness["sufficient_data"]:
        return {"trained": False, "reason": "데이터 부족 — 학습 거부", "readiness": readiness}

    X = [_vec(r["features"]) for r in rows]
    y = [float(r["label"]) for r in rows]
    n, d = len(X), len(FEATURE_KEYS)
    # 표준화
    means = [sum(row[j] for row in X) / n for j in range(d)]
    stds = [math.sqrt(sum((row[j] - means[j]) ** 2 for row in X) / n) or 1.0 for j in range(d)]
    Xs = [[(row[j] - means[j]) / stds[j] for j in range(d)] for row in X]

    w = [0.0] * d
    b = 0.0
    for _ in range(iters):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * Xs[i][j] for j in range(d))
            p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
            err = p - y[i]
            for j in range(d):
                gw[j] += err * Xs[i][j]
            gb += err
        for j in range(d):
            w[j] -= lr * gw[j] / n
        b -= lr * gb / n

    correct = 0
    for i in range(n):
        z = b + sum(w[j] * Xs[i][j] for j in range(d))
        pred = 1 if z >= 0 else 0
        correct += (pred == int(y[i]))
    return {
        "trained": True,
        "model": "pure_python_logistic_regression",
        "n": n,
        "train_accuracy": round(correct / n, 3),
        "weights": {FEATURE_KEYS[j]: round(w[j], 4) for j in range(d)},
        "readiness": readiness,
        "warning": "학습 정확도는 참고용 — 전향적(prospective) 검증 전엔 신뢰 금지. "
                   "이건 z-score/EARS를 대체할 '자리'를 증명하는 베이스라인이다.",
    }

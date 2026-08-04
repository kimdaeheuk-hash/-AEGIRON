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
from .country_resolve import signal_countries
from .knowledge_graph import _DECLARATION_MILESTONE_KEYS

# 학습에 최소 필요한 표본(honest 게이트 — 이 미만이면 학습 거부).
MIN_POSITIVES = 10
MIN_NEGATIVES = 10

# 특징 벡터 키(순서 고정 — 학습·추론 일관).
FEATURE_KEYS = (
    "signal_count", "weighted_severity_mean", "max_severity",
    "distinct_sources", "distinct_diseases", "recent7_count",
)

# ── 확장 특징 ────────────────────────────────────────────────────────────
# 왜 필요한가(실측 근거): 기본 6개는 사실상 '뉴스량' 한 축이다. 신호가 있는 행만
# 놓고 양성·음성 중앙값을 비교하면 distinct_sources·distinct_diseases·recent7_count는
# 분리도 0.00(완전히 같음)이고, 가장 분리도가 큰 max_severity는 **방향이 반대**였다
# (양성 20~30 vs 음성 39~40). 그 결과 모델은 신호가 있는 행의 82%에 경보를 낸다 —
# 사실상 '신호 존재 감지기'다. 전향 검증에서 조건부 재현율은 이미 1.000이므로
# 남은 과제는 재현율이 아니라 **과다발화**다.
#
# max_severity가 뒤집힌 이유가 확장 특징의 설계 근거다: 음성의 약 45%가 '이미 선언된
# 발병이 진행 중인 기간'이라 시끄럽다. 모델은 거기서 "시끄러우면 음성"을 배웠다.
# 그래서 그 국면을 지우는 대신 **모델이 볼 수 있게** 특징으로 준다(days_since_declaration).
# 데이터를 버리지 않고 상황을 구분시키는 쪽이 정직하고 운영에도 맞다 —
# 실제 시스템은 이미 선언된 발병이 있는지 알고 있다.
#
# 나머지는 '절대량' 대신 '그 나라 평소 대비'로 본다. COD는 평상시에도 창당 5건이
# 잡히므로 5건은 COD에서 아무 의미가 없지만 조용한 나라에선 큰 사건이다.
EXTRA_FEATURE_KEYS = (
    "outbreak_recently_declared",   # 이미 선언된 발병이 진행 중인가(0/1)
    "days_since_declaration",       # 마지막 선언 이후 경과(0~1로 정규화, 없으면 1)
    "count_vs_country_baseline",    # 창 신호수 / 그 나라 평소 창당 신호수
    "recent_acceleration",          # 최근 7일 속도 / 창 전체 평균 속도
    "disease_concentration",        # 질병 점유율 허핀달(1=한 질병이 독점)
    "novel_disease_for_country",    # 창의 주력 질병이 그 나라 과거에 없던 것인가(0/1)
    "new_or_spike_fraction",        # signal_type이 신규발생·급증인 비율
    "max_source_trust",             # 창 안 최고 신뢰도 출처
)

FEATURE_KEYS_EXTENDED = FEATURE_KEYS + EXTRA_FEATURE_KEYS

# 그 나라 평소 수준을 재는 비교 구간 = lookback의 몇 배를 볼 것인가.
_BASELINE_WINDOWS = 3
# 선언 후 이 기간까지는 '발병 진행 중'으로 본다(WHO 종식선언은 보통 마지막 확진
# 이후 42일 × 2 — 에볼라 기준. 국면 구분용 근사치이며 정밀한 역학 상수가 아니다).
_ACTIVE_OUTBREAK_DAYS = 120
# days_since_declaration 정규화 상한 — 이보다 오래되면 '평시'와 구분이 없다.
_DECL_HORIZON_DAYS = 730.0
_NEW_OR_SPIKE = {"신규발생", "급증"}

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


def extract_features(window_signals: list[dict], as_of: dt.date,
                     context: dict | None = None) -> dict:
    """한 (국가, as_of) 스냅샷의 신호 특징. window_signals는 lookback 창 안의 신호.

    context를 주면 확장 특징까지 계산한다:
      {"prior": [창 이전 그 나라 신호], "declarations": [as_of 이전 선언일], "lookback_days": int}

    ★ 누수 방지 ★ context는 **as_of 이전 정보만** 담아야 한다. 미래 선언일이나 창
    이후 신호가 섞이면 전향 평가가 통째로 무의미해진다 — 호출부(assemble_dataset)가
    as_of로 잘라서 넘긴다."""
    base = {k: 0.0 for k in FEATURE_KEYS}
    if window_signals:
        sevs = [SIGNAL_TYPE_SEVERITY.get(s.get("signal_type"), 40) * (s.get("source_trust") or 0.5)
                for s in window_signals]
        recent7 = 0
        for s in window_signals:
            d = _parse_date(s.get("signal_date") or s.get("extracted_at"))
            if d and (as_of - d).days <= 7:
                recent7 += 1
        base = {
            "signal_count": float(len(window_signals)),
            "weighted_severity_mean": round(sum(sevs) / len(sevs), 3),
            "max_severity": float(max(sevs)),
            "distinct_sources": float(len({s.get("source") for s in window_signals})),
            "distinct_diseases": float(len({s.get("disease") for s in window_signals if s.get("disease")})),
            "recent7_count": float(recent7),
        }
    if context is None:
        return base
    return {**base, **_extra_features(window_signals, as_of, context)}


def _extra_features(window: list[dict], as_of: dt.date, ctx: dict) -> dict:
    lookback = float(ctx.get("lookback_days") or 30)
    prior = ctx.get("prior") or []
    decls = ctx.get("declarations") or []

    # ── 발병 국면: 이미 선언된 발병이 진행 중인가 ──
    last_gap = min(((as_of - d).days for d in decls if d <= as_of), default=None)
    if last_gap is None:
        recently, since = 0.0, 1.0          # 선언 이력 없음 = 가장 '평시'
    else:
        recently = 1.0 if last_gap <= _ACTIVE_OUTBREAK_DAYS else 0.0
        since = round(min(last_gap / _DECL_HORIZON_DAYS, 1.0), 4)

    # ── 그 나라 평소 대비 ──
    # prior는 [창 시작 - lookback*3, 창 시작) 구간이라 창당 평균으로 환산한다.
    baseline_per_window = len(prior) / _BASELINE_WINDOWS
    count = len(window)
    # +1 평활 — 평소 0건인 나라에서 분모가 0이 되어 비율이 발산하는 걸 막는다.
    vs_baseline = round((count + 1.0) / (baseline_per_window + 1.0), 4)

    # ── 최근 가속 ── 최근 7일 속도가 창 전체 평균 속도의 몇 배인가.
    recent7 = base_recent7 = 0
    for s in window:
        d = _parse_date(s.get("signal_date") or s.get("extracted_at"))
        if d and (as_of - d).days <= 7:
            recent7 += 1
    base_recent7 = count * (7.0 / lookback)
    accel = round((recent7 + 0.5) / (base_recent7 + 0.5), 4) if count else 0.0

    # ── 질병 집중도(허핀달) ── 실제 발병은 한 질병으로 수렴하고, 배경 잡음은 흩어진다.
    diseases = [s.get("disease") for s in window if s.get("disease")]
    if diseases:
        shares = [diseases.count(x) / len(diseases) for x in set(diseases)]
        concentration = round(sum(p * p for p in shares), 4)
        dominant = max(set(diseases), key=diseases.count)
        seen_before = {s.get("disease") for s in prior if s.get("disease")}
        novel = 0.0 if dominant in seen_before else 1.0
    else:
        concentration, novel = 0.0, 0.0

    # ── 신호 성격 ── '신규발생·급증'은 '진행중·불명'과 다른 정보다.
    if window:
        ns = sum(1 for s in window if s.get("signal_type") in _NEW_OR_SPIKE)
        new_frac = round(ns / len(window), 4)
        trust = round(max((s.get("source_trust") or 0.0) for s in window), 4)
    else:
        new_frac, trust = 0.0, 0.0

    return {
        "outbreak_recently_declared": recently,
        "days_since_declaration": since,
        "count_vs_country_baseline": vs_baseline,
        "recent_acceleration": accel,
        "disease_concentration": concentration,
        "novel_disease_for_country": novel,
        "new_or_spike_fraction": new_frac,
        "max_source_trust": trust,
    }


def _event_country_map() -> dict[str, str]:
    """event_id → ISO3. 시드(EVENT_COUNTRY) + 과거 백필 레지스트리를 병합.
    백필로 등재된 과거 공식 선언도 라벨로 잡히게 한다(하위호환: 시드는 그대로)."""
    m = dict(EVENT_COUNTRY)
    try:
        from .historical_outbreaks import event_country_map
        m.update(event_country_map())
    except Exception:
        pass
    return m


def _country_declarations() -> dict[str, list[dt.date]]:
    """국가별 공식 발병 선언일(라벨 소스)."""
    out: dict[str, list[dt.date]] = {}
    country_map = _event_country_map()
    for e in db.list_timeline_events():
        country = country_map.get(e["event_id"])
        if not country:
            continue
        for m in db.get_timeline(e["event_id"]).get("milestones", []):
            if m["milestone"] in _DECLARATION_MILESTONE_KEYS:
                d = _parse_date(m["event_date"])
                if d:
                    out.setdefault(country, []).append(d)
    return out


def assemble_dataset(horizon_days: int = 30, lookback_days: int = 30,
                     step_days: int = 7, limit: int = 5000,
                     resolve_location: bool = True,
                     extended: bool = True) -> list[dict]:
    """extracted_signals + outbreak_timeline → (특징 → 라벨) 성과 학습셋.
    라벨=1: as_of로부터 horizon_days 안에 그 국가에서 공식 발병 선언이 있었음.

    resolve_location=True면 country_iso3가 비어 있어도 location 자유문장에서 국가를
    읽어내고, 다국가 문자열("콩고민주공화국, 우간다")은 **양쪽 모두**에 넣는다.
    저장된 country_iso3만 쓰면 2024년 이후 신호 157건 중 150건이 버려져 최근
    3년 커버리지가 0이 된다(전향 평가 최신 폴드 재현율 0.000의 실제 원인).
    False면 예전 동작 그대로 — 커버리지 개선 효과를 비교 측정할 때 쓴다.

    extended=True면 확장 특징(발병 국면·평소 대비·가속·질병 집중도 등)까지 붙인다.
    False면 기본 6개만 — 특징 추가 효과를 같은 시간분할로 비교 측정할 때 쓴다."""
    signals = db.list_extracted_signals(limit=limit)
    by_country: dict[str, list[dict]] = {}
    dates: list[dt.date] = []
    for s in signals:
        if resolve_location:
            countries = signal_countries(s)
        else:
            countries = [s["country_iso3"]] if s.get("country_iso3") else []
        if not countries:
            continue
        d = _parse_date(s.get("signal_date") or s.get("extracted_at"))
        if d is None:
            continue
        s = {**s, "_date": d}
        for c in countries:
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
            context = None
            if extended:
                # ★ 누수 방지 ★ 평소 수준은 **창 시작 이전** 구간에서만, 선언 이력은
                # **as_of 이전** 것만 넘긴다. 라벨이 보는 미래(as_of+horizon)는 절대
                # 들어가면 안 된다 — 들어가면 전향 평가가 통째로 무의미해진다.
                base_lo = lo - dt.timedelta(days=lookback_days * _BASELINE_WINDOWS)
                context = {
                    "prior": [s for s in sigs if base_lo <= s["_date"] < lo],
                    "declarations": [d for d in decls if d <= as_of],
                    "lookback_days": lookback_days,
                }
            rows.append({
                "country": country, "as_of": as_of.isoformat(),
                "features": extract_features(window, as_of, context), "label": label,
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


def feature_order(rows: list[dict]) -> tuple[str, ...]:
    """이 데이터셋이 **실제로 담고 있는** 특징을 정해진 순서로 추린다.

    전역 FEATURE_KEYS로 고정하면 확장 특징이 채점 때 통째로 무시돼, 특징을 추가해도
    아무 변화가 없는 것처럼 보인다(조용히 틀리는 종류의 버그다).

    '확장 키가 전부 있으면 확장'식의 전부-아니면-전무 판정도 같은 함정이다 — 절제
    실험으로 특징 두 개를 빼면 조건이 깨져 나머지 확장 특징까지 통째로 버려지고,
    기본 6개 결과가 나오면서 '그 특징들은 기여가 없다'는 정반대 결론이 나온다
    (실제로 그렇게 한 번 틀렸다). 그래서 있는 것만 순서대로 쓴다."""
    if not rows:
        return FEATURE_KEYS
    present = set(rows[0]["features"])
    keys = tuple(k for k in FEATURE_KEYS_EXTENDED if k in present)
    return keys or FEATURE_KEYS


def _vec(features: dict, keys: tuple[str, ...] = FEATURE_KEYS) -> list[float]:
    return [features.get(k, 0.0) for k in keys]


def train_baseline(rows: list[dict], iters: int = 300, lr: float = 0.1) -> dict:
    """순수 파이썬 로지스틱 회귀 베이스라인. 데이터 부족이면 학습 거부(정직).
    표준화 + 경사하강. 소량 학습 성능은 참고용이며 전향적 검증 전엔 신뢰 금지."""
    readiness = dataset_readiness(rows)
    if not readiness["sufficient_data"]:
        return {"trained": False, "reason": "데이터 부족 — 학습 거부", "readiness": readiness}

    keys = feature_order(rows)
    X = [_vec(r["features"], keys) for r in rows]
    y = [float(r["label"]) for r in rows]
    n, d = len(X), len(keys)
    # 표준화
    means = [sum(row[j] for row in X) / n for j in range(d)]
    stds = [math.sqrt(sum((row[j] - means[j]) ** 2 for row in X) / n) or 1.0 for j in range(d)]
    Xs = [[(row[j] - means[j]) / stds[j] for j in range(d)] for row in X]

    # ★ 클래스 가중치(balanced): 발병은 희귀사건 → 무가중이면 학습기가 다수 음성만
    #   찍는다(양성 재현율≈0). 소수 양성을 neg/pos 비율로 키워 실제로 잡게 한다.
    #   표준 기법이며 데이터를 조작하는 게 아니다.
    pos_total = sum(y)
    neg_total = n - pos_total
    pos_w = (n / (2.0 * pos_total)) if pos_total else 1.0
    neg_w = (n / (2.0 * neg_total)) if neg_total else 1.0
    cw = [pos_w if yi >= 0.5 else neg_w for yi in y]
    wsum = sum(cw) or 1.0

    w = [0.0] * d
    b = 0.0
    for _ in range(iters):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * Xs[i][j] for j in range(d))
            p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
            err = (p - y[i]) * cw[i]
            for j in range(d):
                gw[j] += err * Xs[i][j]
            gb += err
        for j in range(d):
            w[j] -= lr * gw[j] / wsum
        b -= lr * gb / wsum

    correct = tp = fp = fn = 0
    pos_total = int(sum(y))
    for i in range(n):
        z = b + sum(w[j] * Xs[i][j] for j in range(d))
        pred = 1 if z >= 0 else 0
        yi = int(y[i])
        correct += (pred == yi)
        tp += (pred == 1 and yi == 1)
        fp += (pred == 1 and yi == 0)
        fn += (pred == 0 and yi == 1)
    # ★ 정직성: 발병은 희귀사건 → 정확도는 기저율(다수 음성 비율)에 가까워 무의미할 수
    #   있다. '다수 클래스만 찍어도 나오는 정확도'(base_rate)와 반드시 비교하고, 실제
    #   판별력은 양성 클래스 재현율/정밀도로 본다.
    base_rate = round(max(pos_total, n - pos_total) / n, 3) if n else 0.0
    recall = round(tp / (tp + fn), 3) if (tp + fn) else None      # 실제 발병을 잡은 비율
    precision = round(tp / (tp + fp), 3) if (tp + fp) else None   # 발병경보의 적중률
    return {
        "trained": True,
        "model": "pure_python_logistic_regression",
        "n": n,
        "train_accuracy": round(correct / n, 3),
        "majority_class_base_rate": base_rate,
        "positive_recall": recall,
        "positive_precision": precision,
        "positives": pos_total,
        "feature_order": list(keys),   # 채점이 같은 순서를 쓰게 한다
        "weights": {keys[j]: round(w[j], 4) for j in range(d)},
        # 표준화 파라미터와 절편 — 이게 없으면 학습 밖에서 같은 점수를 재현할 수 없어
        # 임계값 곡선을 그릴 수 없다(nowcast_threshold가 쓴다).
        "bias": round(b, 6),
        "feature_means": {keys[j]: round(means[j], 6) for j in range(d)},
        "feature_stds": {keys[j]: round(stds[j], 6) for j in range(d)},
        "decision_threshold": 0.5,
        "readiness": readiness,
        "warning": "학습 정확도만 보지 말 것 — 발병은 희귀사건이라 정확도가 base_rate에 "
                   "가까우면 '다수 음성만 찍는 것'과 다를 바 없다. 양성 재현율/정밀도로 "
                   "판별력을 보고, 전향적(prospective) 검증 전엔 신뢰 금지. "
                   "이건 z-score/EARS를 대체할 '자리'를 증명하는 베이스라인이다.",
    }

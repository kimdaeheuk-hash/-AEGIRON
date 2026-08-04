"""Tier-2 전향적 평가 장치. 이게 없으면 특징을 추가했을 때 판별력이 정말 올랐는지
아니면 학습 데이터를 더 잘 외운 건지 구분할 수 없다 — 특징을 늘릴수록 학습 성적은
거의 항상 오르기 때문이다."""
from __future__ import annotations
import datetime as dt

import pytest

from algorithms.nowcast_eval import (
    temporal_folds, evaluate_temporal, coverage_split, MIN_TEST_POSITIVES,
)
from algorithms.nowcast_dataset import (
    extract_features, feature_order, train_baseline,
    FEATURE_KEYS, FEATURE_KEYS_EXTENDED, EXTRA_FEATURE_KEYS,
)


def _row(country, as_of, label, count=0.0, **extra):
    feats = {k: 0.0 for k in FEATURE_KEYS}
    feats["signal_count"] = count
    feats.update(extra)
    return {"country": country, "as_of": as_of, "label": label, "features": feats}


def _synthetic(n_pos=40, n_neg=400):
    """양성이 시간축에 고르게 퍼진 합성 데이터."""
    rows = []
    d = dt.date(2020, 1, 1)
    for i in range(n_neg):
        rows.append(_row("AAA", (d + dt.timedelta(days=7 * i)).isoformat(), 0, count=1.0))
    for i in range(n_pos):
        rows.append(_row("BBB", (d + dt.timedelta(days=70 * i)).isoformat(), 1, count=9.0))
    return rows


# ── 시간 분리(누수 방지) ───────────────────────────────────────────────
def test_training_window_never_contains_future_rows():
    """★핵심★ 학습 구간에 검정 구간 이후 행이 하나라도 섞이면 전향 평가가 통째로
    무의미해진다. 미래를 본 모델의 성적은 운영 성능이 아니다."""
    rows = _synthetic()
    for train, test in temporal_folds(rows, n_folds=3):
        assert train and test
        assert max(r["as_of"] for r in train) < min(r["as_of"] for r in test)


def test_folds_do_not_overlap_each_other():
    rows = _synthetic()
    seen = set()
    for _, test in temporal_folds(rows, n_folds=3):
        ids = {(r["country"], r["as_of"]) for r in test}
        assert not (ids & seen), "검정 구간이 겹치면 같은 행을 두 번 채점하게 된다"
        seen |= ids


def test_folds_refused_when_positives_too_few():
    """표본이 부족하면 억지로 나누지 않고 거부한다 — 지어낸 성능을 내지 않는다."""
    assert temporal_folds(_synthetic(n_pos=4), n_folds=4) == []


def test_evaluate_refuses_instead_of_inventing_numbers():
    out = evaluate_temporal(_synthetic(n_pos=3), n_folds=4)
    assert out["evaluated"] is False
    assert "부족" in out["reason"]


def test_evaluate_returns_out_of_sample_metrics():
    out = evaluate_temporal(_synthetic(), n_folds=3)
    assert out["evaluated"] is True
    assert out["folds_used"] >= 1
    assert out["out_of_sample"]["sensitivity"] is not None
    assert out["pooled_positives"] >= MIN_TEST_POSITIVES


# ── 커버리지 분해 ──────────────────────────────────────────────────────
def test_coverage_split_separates_blind_from_missed():
    """★핵심★ '데이터가 없어 못 잡은 것'과 '데이터가 있는데 못 잡은 것'을 섞으면
    진단이 정확히 반대로 나온다. 실측에서 놓친 양성이 전부 빈 창이었는데, 합산
    재현율만 보면 '판별력 부족'으로 읽혀 특징 공학에 시간을 쓰게 된다."""
    rows = [_row("A", "2020-01-01", 1, count=0.0),   # 신호 없음 = blind
            _row("A", "2020-02-01", 1, count=5.0),
            _row("A", "2020-03-01", 0, count=2.0)]
    cov = coverage_split(rows)
    assert cov["positives"] == 2
    assert cov["positives_blind"] == 1
    assert cov["positives_with_signal"] == 1
    assert cov["max_achievable_sensitivity"] == 0.5


def test_coverage_ceiling_is_reported_with_evaluation():
    """재현율만 보고 모델을 탓하지 않도록 상한을 같이 실어 보낸다."""
    out = evaluate_temporal(_synthetic(), n_folds=3)
    assert out["sensitivity_ceiling_from_coverage"] is not None
    assert out["conditional_sensitivity"] is not None


# ── 특징 순서(조용히 틀리는 버그) ──────────────────────────────────────
def test_feature_order_uses_only_features_actually_present():
    """★회귀★ '확장 키가 전부 있으면 확장'식 전부-아니면-전무 판정은 절제 실험을
    망친다 — 특징 두 개를 빼면 조건이 깨져 나머지 확장 특징까지 통째로 버려지고,
    기본 6개 결과가 나오면서 '기여가 없다'는 정반대 결론이 나온다."""
    ctx = {"prior": [], "declarations": [], "lookback_days": 30}
    full = extract_features([], dt.date(2020, 1, 1), ctx)
    assert feature_order([{"features": full}]) == FEATURE_KEYS_EXTENDED

    partial = {k: v for k, v in full.items() if k != "novel_disease_for_country"}
    order = feature_order([{"features": partial}])
    assert "novel_disease_for_country" not in order
    # 나머지 확장 특징은 살아 있어야 한다 — 여기가 무너지면 절제 실험이 거짓말한다.
    assert len(order) == len(FEATURE_KEYS_EXTENDED) - 1
    for k in EXTRA_FEATURE_KEYS:
        if k != "novel_disease_for_country":
            assert k in order


def test_model_carries_its_own_feature_order():
    """채점이 학습과 다른 순서를 쓰면 조용히 엉뚱한 점수가 나온다."""
    rows = _synthetic()
    model = train_baseline(rows)
    assert model["trained"] is True
    assert model["feature_order"] == list(FEATURE_KEYS)
    assert set(model["weights"]) == set(model["feature_order"])


def test_base_features_still_work_without_context():
    """확장은 선택 — context 없이 부르면 예전 6개 그대로여야 한다(하위호환)."""
    got = extract_features([], dt.date(2020, 1, 1))
    assert set(got) == set(FEATURE_KEYS)


# ── 확장 특징 ──────────────────────────────────────────────────────────
def _sig(date, disease="에볼라", stype="진행중", trust=0.8, source="who"):
    return {"signal_date": date, "disease": disease, "signal_type": stype,
            "source_trust": trust, "source": source}


def _ctx(prior=None, declarations=None, lookback=30):
    return {"prior": prior or [], "declarations": declarations or [],
            "lookback_days": lookback}


def test_declaration_phase_feature_marks_ongoing_outbreak():
    """음성의 약 45%가 '이미 선언된 발병이 진행 중'이라 시끄러웠고, 그래서 모델이
    '시끄러우면 음성'을 배웠다(max_severity 가중치가 음수로 뒤집혔다). 그 국면을
    지우는 대신 모델이 볼 수 있게 특징으로 준다."""
    as_of = dt.date(2020, 6, 1)
    recent = extract_features([_sig("2020-05-20")], as_of,
                              _ctx(declarations=[dt.date(2020, 5, 1)]))
    assert recent["outbreak_recently_declared"] == 1.0

    old = extract_features([_sig("2020-05-20")], as_of,
                           _ctx(declarations=[dt.date(2015, 5, 1)]))
    assert old["outbreak_recently_declared"] == 0.0
    assert old["days_since_declaration"] == 1.0        # 상한에 걸림 = 사실상 평시

    never = extract_features([_sig("2020-05-20")], as_of, _ctx())
    assert never["outbreak_recently_declared"] == 0.0


def test_future_declarations_cannot_leak_into_features():
    """★핵심 정직성★ 라벨이 보는 미래(as_of 이후 선언)가 특징에 새면 전향 평가가
    통째로 거짓이 된다. 미래 선언일이 섞여 들어와도 무시해야 한다."""
    as_of = dt.date(2020, 6, 1)
    future_only = extract_features([_sig("2020-05-20")], as_of,
                                   _ctx(declarations=[dt.date(2020, 6, 20)]))
    clean = extract_features([_sig("2020-05-20")], as_of, _ctx())
    assert future_only["outbreak_recently_declared"] == clean["outbreak_recently_declared"]
    assert future_only["days_since_declaration"] == clean["days_since_declaration"]


def test_baseline_relative_count_beats_absolute_count():
    """COD는 평상시에도 창당 5건이 잡힌다 — 절대량 5건은 COD에서 아무 의미가 없지만
    조용한 나라에선 큰 사건이다. 같은 5건이 나라에 따라 다르게 읽혀야 한다."""
    as_of = dt.date(2020, 6, 1)
    window = [_sig("2020-05-%02d" % (10 + i)) for i in range(5)]
    noisy = extract_features(window, as_of, _ctx(prior=[_sig("2020-01-01")] * 15))
    quiet = extract_features(window, as_of, _ctx(prior=[]))
    assert noisy["signal_count"] == quiet["signal_count"] == 5.0     # 절대량은 같고
    assert quiet["count_vs_country_baseline"] > noisy["count_vs_country_baseline"]


def test_disease_concentration_and_novelty():
    """실제 발병은 한 질병으로 수렴하고, 배경 잡음은 여러 질병에 흩어진다."""
    as_of = dt.date(2020, 6, 1)
    focused = extract_features([_sig("2020-05-20", "에볼라")] * 4, as_of, _ctx())
    diffuse = extract_features(
        [_sig("2020-05-20", d) for d in ("에볼라", "홍역", "콜레라", "말라리아")], as_of, _ctx())
    assert focused["disease_concentration"] == 1.0
    assert diffuse["disease_concentration"] < 0.3

    known = extract_features([_sig("2020-05-20", "에볼라")], as_of,
                             _ctx(prior=[_sig("2020-01-01", "에볼라")]))
    assert known["novel_disease_for_country"] == 0.0
    assert focused["novel_disease_for_country"] == 1.0


def test_signal_type_and_trust_are_distinguished():
    as_of = dt.date(2020, 6, 1)
    new = extract_features([_sig("2020-05-20", stype="신규발생", trust=0.9),
                            _sig("2020-05-21", stype="진행중", trust=0.4)], as_of, _ctx())
    assert new["new_or_spike_fraction"] == 0.5
    assert new["max_source_trust"] == 0.9


def test_empty_window_stays_all_zero_even_with_context():
    """빈 창은 어떤 문맥이 붙어도 0벡터여야 한다 — 여기서 값이 새면 '신호가 없는데
    경보가 난다'가 된다."""
    got = extract_features([], dt.date(2020, 6, 1), _ctx(prior=[_sig("2020-01-01")] * 9))
    for k in FEATURE_KEYS:
        assert got[k] == 0.0
    assert got["disease_concentration"] == 0.0
    assert got["recent_acceleration"] == 0.0
    assert got["new_or_spike_fraction"] == 0.0

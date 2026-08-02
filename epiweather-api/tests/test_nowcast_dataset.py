"""Tier 2 프레임워크 — 성과 학습셋 조립·특징추출·충분성 게이트·베이스라인 학습기.
핵심: 데이터 부족이면 학습을 거부하고 성능을 지어내지 않는지 확인."""
from __future__ import annotations
import datetime as dt

from algorithms import nowcast_dataset as nd


def test_extract_features_empty_window():
    f = nd.extract_features([], dt.date(2026, 7, 1))
    assert set(f) == set(nd.FEATURE_KEYS)
    assert f["signal_count"] == 0.0


def test_extract_features_counts_and_recency():
    as_of = dt.date(2026, 7, 10)
    sigs = [
        {"signal_type": "신규발생", "source_trust": 1.0, "source": "who",
         "disease": "에볼라", "signal_date": "2026-07-09"},   # recent7
        {"signal_type": "진행중", "source_trust": 0.5, "source": "gnews",
         "disease": "에볼라", "signal_date": "2026-06-20"},   # old
    ]
    f = nd.extract_features(sigs, as_of)
    assert f["signal_count"] == 2.0
    assert f["distinct_sources"] == 2.0
    assert f["distinct_diseases"] == 1.0
    assert f["recent7_count"] == 1.0        # 07-09만 최근 7일


def test_dataset_readiness_insufficient_refuses():
    """표본이 적으면 sufficient_data=False — 지어내지 않음."""
    rows = [{"label": 0, "features": {k: 0.0 for k in nd.FEATURE_KEYS}} for _ in range(5)]
    r = nd.dataset_readiness(rows)
    assert r["sufficient_data"] is False
    assert r["positives"] == 0


def test_train_baseline_refuses_when_insufficient():
    rows = [{"label": 0, "features": {k: 0.0 for k in nd.FEATURE_KEYS}} for _ in range(5)]
    out = nd.train_baseline(rows)
    assert out["trained"] is False
    assert "부족" in out["reason"]


def test_train_baseline_learns_separable_data():
    """충분한 표본이 있으면 베이스라인이 실제로 학습돼 분리 가능한 신호를 잡는다.
    (프레임워크가 '작동'함을 증명 — 실데이터 성능은 별개, 전향적 검증 필요.)"""
    rows = []
    for i in range(15):  # 양성: 신호 많음
        rows.append({"label": 1, "features": {**{k: 0.0 for k in nd.FEATURE_KEYS},
                     "signal_count": 10.0 + i, "weighted_severity_mean": 80.0, "recent7_count": 5.0}})
    for i in range(15):  # 음성: 신호 거의 없음
        rows.append({"label": 0, "features": {**{k: 0.0 for k in nd.FEATURE_KEYS},
                     "signal_count": 1.0, "weighted_severity_mean": 30.0, "recent7_count": 0.0}})
    out = nd.train_baseline(rows)
    assert out["trained"] is True
    assert out["train_accuracy"] >= 0.9          # 명백히 분리 가능 → 높게 학습
    assert "전향적" in out["warning"]             # 과신 금지 경고 유지


def test_assemble_dataset_empty_db_returns_empty(isolated_db):
    assert nd.assemble_dataset() == []


def test_assemble_dataset_labels_from_declarations(isolated_db):
    """COD(콩고) 신호 + outbreak_timeline의 DRC 공식 선언(drc_official) → 양성 라벨 생성."""
    import db as dbmod
    # 선언 이전 시점의 신호
    dbmod.create_extracted_signal(
        source="who", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=["high"], symptom=None, transmission=None, source_trust=0.9,
        signal_date="2026-05-01", raw_text="DRC 에볼라 조짐", country_iso3="COD",
    )
    # 공식 선언 마일스톤(라벨 소스)
    dbmod.upsert_timeline_event("ebola_drc_2026", "에볼라 DRC 2026", "2026-05-15",
                                "drc_official", "DRC 공식 선언", "WHO", "who")
    rows = nd.assemble_dataset(horizon_days=30, lookback_days=30, step_days=7)
    assert any(r["country"] == "COD" and r["label"] == 1 for r in rows)  # 선언 30일 전 창은 양성

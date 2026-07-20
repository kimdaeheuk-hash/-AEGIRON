"""GAI(Global Anomaly Index) — 인수인계서 Part5 ①②의 공식이 실제 코드와
일치하는지 검증. z-score 클램프, tier 경계값, 6계층 가중합산까지 확인.
"""
from __future__ import annotations
import pytest

from algorithms import gai as gai_mod


def test_anomaly_score_clamps_extreme_spike_to_100():
    history = [10, 20, 10, 20]  # 분산이 있어야 z-score가 의미 있음
    assert gai_mod._anomaly_score(history + [1000]) == 100.0


def test_anomaly_score_ignores_decreases_per_negative_space_design():
    """음수 방향(평소보다 낮음)은 0점 — 감소는 negative_space.py가 전담."""
    history = [10, 20, 10, 20]
    assert gai_mod._anomaly_score(history + [0]) == 0.0


def test_anomaly_score_none_when_history_too_short():
    assert gai_mod._anomaly_score([1, 2]) is None  # MIN_HISTORY=3 미만


def test_anomaly_score_zero_variance_history_returns_zero():
    """과거값이 전부 동일(분산 0)이면 stdev=0이라 무조건 0점 — 코드의 실제 동작."""
    assert gai_mod._anomaly_score([5, 5, 5, 999]) == 0.0


@pytest.mark.parametrize("score,expected", [
    (95, "🔴 위험"), (90, "🔴 위험"),
    (85, "🟠 경보"), (80, "🟠 경보"),
    (75, "🟡 주의"), (70, "🟡 주의"),
    (69.9, "🟢 정상"), (0, "🟢 정상"),
])
def test_tier_thresholds_match_handoff_doc(score, expected):
    assert gai_mod._tier(score) == expected


def test_tier_none_when_gai_is_none():
    assert gai_mod._tier(None) is None


def test_compute_gai_weighted_average_uses_documented_layer_weights(monkeypatch):
    """
    인수인계서 공식: GAI = 공식×0.15 + 비공식×0.20 + 행동×0.25 + 환경×0.15
                          + 동물×0.15 + 설명불가×0.10
    실제로는 layer_score(=신뢰도가중 평균) × layer_weight를 available layer만
    골라 가중평균하는 코드 — 그 로직 자체를 검증(레이어 2개로 축소한 통제 데이터).
    """
    fake_layers = {
        "official": {
            "label": "공식신호", "weight": 0.15,
            "metrics": [("official_metric", "free_sources", lambda r: r.get("official_metric"), "who")],
        },
        "behavioral": {
            "label": "행동신호", "weight": 0.25,
            "metrics": [("behavioral_metric", "free_sources", lambda r: r.get("behavioral_metric"), "behavioral_api")],
        },
    }
    records = [
        {"type": "free_sources", "official_metric": 10, "behavioral_metric": 10},
        {"type": "free_sources", "official_metric": 20, "behavioral_metric": 20},
        {"type": "free_sources", "official_metric": 10, "behavioral_metric": 10},
        {"type": "free_sources", "official_metric": 20, "behavioral_metric": 20},
        {"type": "free_sources", "official_metric": 100, "behavioral_metric": 20},  # 최신값
    ]
    monkeypatch.setattr(gai_mod, "LAYERS", fake_layers)
    monkeypatch.setattr(gai_mod, "load_records", lambda: records)

    result = gai_mod.compute_gai()

    # official: z가 크게 튐 -> 100점, trust(who)=1.0 -> layer_score 100.0
    assert result["layers"]["official"]["score"] == 100.0
    # behavioral: latest가 과거 최대치와 같음(z=1.0) -> raw 33.3, trust(behavioral_api)=0.9
    assert result["layers"]["behavioral"]["score"] == pytest.approx(30.0, abs=0.1)

    weight_sum = fake_layers["official"]["weight"] + fake_layers["behavioral"]["weight"]
    expected_gai = round(
        (result["layers"]["official"]["score"] * 0.15
         + result["layers"]["behavioral"]["score"] * 0.25) / weight_sum,
        1,
    )
    assert result["gai"] == expected_gai
    assert result["score_model"] == "gai_v1_layered_trust_weighted"


def test_compute_gai_returns_none_when_no_records(monkeypatch):
    monkeypatch.setattr(gai_mod, "load_records", lambda: [])
    result = gai_mod.compute_gai()
    assert result["gai"] is None
    assert result["tier"] is None

"""GAI(Global Anomaly Index) — 인수인계서 Part5 ①②의 공식이 실제 코드와
일치하는지 검증. z-score 클램프, tier 경계값, 6계층 가중합산까지 확인.
"""
from __future__ import annotations
import pytest

from algorithms import gai as gai_mod


# 과거가 '서로 다른 값 3개 이상'이어야 판정한다(2026-09-20). 아래 픽스처들이
# [10, 20, 10, 20](서로 다른 값 2개)에서 [10, 20, 30, 20]으로 바뀐 이유다 —
# 검증 대상(클램프·감소 무시·가중합산)은 그대로고, 입력만 판정 가능한 계열로 고쳤다.
def test_anomaly_score_clamps_extreme_spike_to_100():
    history = [10, 20, 30, 20]  # 분산이 있어야 z-score가 의미 있음
    assert gai_mod._anomaly_score(history + [1000]) == 100.0


def test_anomaly_score_ignores_decreases_per_negative_space_design():
    """음수 방향(평소보다 낮음)은 0점 — 감소는 negative_space.py가 전담."""
    history = [10, 20, 30, 20]
    assert gai_mod._anomaly_score(history + [0]) == 0.0


def test_anomaly_score_none_when_history_too_short():
    assert gai_mod._anomaly_score([1, 2]) is None  # MIN_HISTORY=3 미만


def test_anomaly_score_withholds_when_history_never_varied():
    """★계약이 바뀌었다 (2026-09-20)★ 예전엔 0점이었다("분산 0이면 0점").

    0점은 '이상 없음'이라는 **판정**이다. 과거가 한 번도 변한 적 없으면 우리가
    아는 건 '판정할 수 없다'뿐이다. 그 둘을 같은 숫자로 쓰면, 표본이 쌓이는
    순간(서로 다른 값이 2개가 되는 순간) 0점이 갑자기 100점으로 튄다 —
    09-20 01:02 에 naver_covid_ratio 가 실제로 그렇게 critical 을 냈다.

    이제 None 이다. gai 는 None 인 지표를 지수에서 건너뛴다.
    """
    assert gai_mod._anomaly_score([5, 5, 5, 999]) is None


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
        {"type": "free_sources", "official_metric": 30, "behavioral_metric": 30},
        {"type": "free_sources", "official_metric": 20, "behavioral_metric": 20},
        {"type": "free_sources", "official_metric": 100, "behavioral_metric": 30},  # 최신값
    ]
    monkeypatch.setattr(gai_mod, "LAYERS", fake_layers)
    monkeypatch.setattr(gai_mod, "load_records", lambda: records)

    result = gai_mod.compute_gai()

    # official: z가 크게 튐 -> 100점, trust(who)=1.0 -> layer_score 100.0
    assert result["layers"]["official"]["score"] == 100.0
    # behavioral: latest가 과거 최대치와 같음 -> raw 47.1, trust(behavioral_api)=0.9
    assert result["layers"]["behavioral"]["score"] == pytest.approx(42.4, abs=0.1)

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

"""갭 #9 — 확률 사전 보정(calibrate_prob).

balanced 가중 학습의 sigmoid 출력은 순위 점수지 확률이 아니다.
순서는 그대로 두되 절댓값을 유병률 기준으로 되돌린다.
"""
from __future__ import annotations

from algorithms.nowcast_threshold import calibrate_prob


def test_rare_positives_deflate():
    """양성이 희귀하면 부풀려진 점수가 내려간다."""
    import pytest

    assert calibrate_prob(0.7, 10, 90) < 0.7
    assert calibrate_prob(0.7, 10, 90) == pytest.approx(
        0.7 / 0.3 * (10 / 90) / (1 + 0.7 / 0.3 * (10 / 90)))


def test_balanced_is_identity():
    """양음 동수면 보정이 항등이다."""
    assert calibrate_prob(0.7, 50, 50) == 0.7


def test_monotone():
    """순서가 바뀌면 운영점 곡선이 깨진다 — 단조 필수."""
    ps = [i / 100 for i in range(1, 100)]
    qs = [calibrate_prob(p, 10, 90) for p in ps]
    assert all(a < b for a, b in zip(qs, qs[1:]))


def test_boundaries_and_degenerate():
    assert calibrate_prob(0.0, 10, 90) == 0.0
    assert calibrate_prob(1.0, 10, 90) == 1.0
    assert calibrate_prob(0.7, 0, 90) == 0.7
    assert calibrate_prob(0.7, 10, 0) == 0.7


def test_stays_probability():
    for p100 in range(1, 100):
        q = calibrate_prob(p100 / 100, 7, 93)
        assert 0.0 < q < 1.0

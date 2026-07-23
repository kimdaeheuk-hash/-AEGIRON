"""극지·영구동토 관찰 층(㉞) — 해빙 압력 계산, 뉴스 신호 변환, 그리고 이 층이
'경보(alert)'가 아니라 'watch' 등급으로 분리되는지(경보 파이프라인과 안 섞임)
확인. 외부 API는 mock(샌드박스 차단)."""
from __future__ import annotations
from unittest.mock import patch

from algorithms import polar_signals as ps
from algorithms.polar_signals import (
    _thaw_pressure, _news_signal, compute_region, polar_watch_all, POLAR_REGIONS,
)


def test_thaw_pressure_bounded_and_responds_to_thaw_and_heat():
    assert _thaw_pressure(0, 0.0) == 0.0
    full = _thaw_pressure(30, 3.0)
    assert full == 100.0
    # 해빙일↑ 또는 온난화↑ 면 압력↑
    assert _thaw_pressure(15, 0.0) < _thaw_pressure(30, 0.0)
    assert _thaw_pressure(0, 0.0) < _thaw_pressure(0, 2.0)


def test_news_signal_none_when_no_ratio():
    assert _news_signal(None) is None
    assert _news_signal(0.0) == 0.0
    assert _news_signal(0.5) == 100.0  # 캡


def _fake_climate(temps):
    return {"temps": temps, "precip": [0.0] * len(temps)}


def _fake_feed(status="ok", hits=3, ratio=0.3):
    return {"status": status, "keyword_hits": hits, "hit_ratio": ratio,
            "sample_titles": ["polar disease news"]}


def test_compute_region_combines_thaw_and_news_as_watch_grade():
    temps = [-5.0] * 60 + [2.0] * 32  # 최근 해빙 발생 + 온난화
    with patch("algorithms.polar_signals.fetch_climate", return_value=_fake_climate(temps)), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed()):
        result = compute_region(POLAR_REGIONS[0])

    assert result["watch_grade"] is True                 # ★ 경보 아님
    assert result["low_probability_high_impact"] is True
    assert result["thaw"]["data_available"] is True
    assert result["thaw"]["thaw_days_30d"] == 30
    assert result["news"]["signal"] == 90.0  # hit_ratio 0.3 × 300 = 90
    assert result["polar_watch_score"] is not None


def test_compute_region_handles_climate_unavailable_but_news_ok():
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed()):
        result = compute_region(POLAR_REGIONS[1])
    assert result["thaw"]["data_available"] is False
    assert result["news"]["signal"] is not None
    # 뉴스만으로도 관찰 점수는 나옴
    assert result["polar_watch_score"] is not None


def test_compute_region_both_unavailable_gives_none_score():
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed(status="error", hits=None, ratio=None)):
        result = compute_region(POLAR_REGIONS[2])
    assert result["polar_watch_score"] is None


def test_polar_watch_all_is_watch_grade_not_alert():
    """★ 핵심 — 전체 응답이 watch 등급이고 '경보 아님'을 명시해야 함."""
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed()):
        result = polar_watch_all()
    assert result["grade"] == "watch"
    assert "경보" in result["note"]  # 경보가 아니라는 명시
    assert len(result["regions"]) == len(POLAR_REGIONS)


def test_polar_watch_includes_antarctic_h5n1_region():
    """남극 H5N1(2023~24 실재 사건) 관찰 지역이 포함됐는지."""
    keys = {r[0] for r in POLAR_REGIONS}
    assert "antarctic_peninsula" in keys
    assert "siberia_yamal" in keys  # 2016 탄저 실증 지역

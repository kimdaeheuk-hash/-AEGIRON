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


# ── 되돌림: 스코프+중복 감지 (2026-11-02) ──────────────────────────

def test_every_polar_slug_has_a_scope_term():
    """스코프 항목이 하나라도 빠지면 그 지역은 전역 뉴스를 받는다."""
    from algorithms.local_news import COUNTRY_TERMS
    for (key, *_rest) in POLAR_REGIONS:
        assert COUNTRY_TERMS.get(f"{key}_news"), key


def test_compute_region_sends_a_scoped_url():
    seen = {}

    def feed(slug, lang, name, url, keywords):
        seen["url"] = url
        return _fake_feed()

    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", side_effect=feed):
        compute_region(POLAR_REGIONS[0])      # siberia_yamal → Ямал
    assert "%D0%AF%D0%BC%D0%B0%D0%BB" in seen["url"]   # Ямал URL 인코딩


def test_identical_feeds_are_marked_duplicate_of():
    titles = ["head1", "head2", "같은 기사 A", "같은 기사 B"]

    def feed(slug, *a, **k):
        d = _fake_feed()
        d["_all_titles"] = list(titles)
        return d

    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", side_effect=feed):
        out = polar_watch_all()
    for r in out["regions"]:
        assert r["news"]["duplicate_of"] == sorted(rr["region"] for rr in out["regions"])
        assert "_titles_hash" not in r["news"]     # 내부는 최종 응답에 없음


def test_distinct_feeds_and_short_lists_are_not_marked():
    def feed(slug, *a, **k):
        d = _fake_feed()
        d["_all_titles"] = ["h1", "h2", f"{slug} 고유 기사"]
        return d

    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", side_effect=feed):
        out = polar_watch_all()
    assert all("duplicate_of" not in r["news"] for r in out["regions"])

    # 머리글뿐(3건 미만)이면 판정 불가 — 지어내지 않는다
    assert ps._titles_hash(["a", "b"]) is None
    assert ps._titles_hash(None) is None


# ── 산식: 표본 게이트+계절 보정 (2026-11-02) ───────────────────────

def test_news_signal_gated_below_twenty_items():
    assert ps._news_signal(0.5, 5) is None
    assert ps._news_signal(0.5, 20) == 100.0
    assert ps._news_signal(0.5, None) == 100.0   # 모르면 게이트 불가 — 그대로 계산


def test_compute_region_marks_too_few_items_instead_of_scoring():
    feed = _fake_feed()
    feed["item_count"] = 5
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=feed):
        out = compute_region(POLAR_REGIONS[0])
    assert out["news"]["signal"] is None
    assert out["news"]["too_few_items"] is True

    feed["item_count"] = 40
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=feed):
        out = compute_region(POLAR_REGIONS[0])
    assert out["news"]["signal"] == 90.0
    assert "too_few_items" not in out["news"]


def test_heat_uses_baseline_anomaly_when_available():
    """계절이 맞는 편차를 쓴다 — 봄·가을 기울기가 온난화로 둔갑하지 않는다."""
    temps = [float(t) for t in range(-10, 82)]      # 가파른 상승(계절 기울기)
    with patch("algorithms.polar_signals.fetch_climate",
               return_value=_fake_climate(temps)), \
         patch("algorithms.polar_signals.fetch_local_feed",
               return_value=_fake_feed(status="error", hits=None, ratio=None)), \
         patch("algorithms.polar_signals.month_baseline",
               return_value={"available": True, "anomaly_c": 1.9}), \
         patch("algorithms.polar_signals.month_trend", return_value={"available": False}):
        out = compute_region(POLAR_REGIONS[1])
    assert out["thaw"]["heat_trend_c"] == 1.9
    assert out["thaw"]["heat_basis"] == "baseline_anomaly"


# ── 동물 채널 H5N1 보조 (2026-11-02) ──────────────────────────────

def test_polar_watch_carries_the_animal_channel_aux():
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed()), \
         patch("algorithms.wahis.requests.get") as g:
        g.return_value.status_code = 200
        g.return_value.text = ('<rss><channel><title>WOAH</title>'
                               '<item><title>H5N1 in penguins</title></item>'
                               '</channel></rss>')
        out = polar_watch_all()
    assert out["h5n1_aux"]["woah_h5n1_hits"] == 1


def test_aux_failure_does_not_kill_polar_watch():
    """보조는 보조다 — 못 읽으면 None+사유지 전체가 죽지 않는다."""
    import requests as rq
    with patch("algorithms.polar_signals.fetch_climate", return_value=None), \
         patch("algorithms.polar_signals.fetch_local_feed", return_value=_fake_feed()), \
         patch("algorithms.wahis.requests.get", side_effect=rq.Timeout("slow")):
        out = polar_watch_all()
    assert out["h5n1_aux"]["woah_h5n1_hits"] is None
    assert out["h5n1_aux"]["reason"] == "Timeout"
    assert len(out["regions"]) == len(POLAR_REGIONS)


def test_heat_falls_back_to_trailing_window_without_baseline():
    temps = [-5.0] * 85 + [2.0] * 7
    with patch("algorithms.polar_signals.fetch_climate",
               return_value=_fake_climate(temps)), \
         patch("algorithms.polar_signals.fetch_local_feed",
               return_value=_fake_feed(status="error", hits=None, ratio=None)), \
         patch("algorithms.polar_signals.month_baseline",
               return_value={"available": False}), \
         patch("algorithms.polar_signals.month_trend", return_value={"available": False}):
        out = compute_region(POLAR_REGIONS[1])
    assert out["thaw"]["heat_trend_c"] == 7.0       # 2.0 − (−5.0)
    assert out["thaw"]["heat_basis"] == "trailing_window"

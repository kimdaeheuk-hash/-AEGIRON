"""현지어 위키 신호 — 표본 부족은 '급증'이 아니라 '모름'이다 (2026-11-02).

기준 14일 조회수가 50건 미만이면 비율을 내지 않는다. 3건→9건도 ratio 3.0이
되는데, 그건 신호가 아니라 표본 부족이다(`local_news` 표본 게이트와 같은 규칙).
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from algorithms import local_signal as ls


def _items(recent_views, base_views, today=None):
    # 고정 날짜는 날짜 폭탄이다(11-02 작성·당일만 통과·11-03 실패 실측). 실측 기준일로 둔다.
    today = today or dt.date.today()
    items = []
    for back in range(1, 29):
        day = today - dt.timedelta(days=back)
        views = recent_views if back <= 14 else base_views
        items.append({"timestamp": day.strftime("%Y%m%d") + "00", "views": views})
    return items


def test_small_baseline_is_undetermined_not_a_surge():
    with patch("algorithms.local_signal._daily_views",
               return_value=_items(9, 3)):
        out = ls.fetch_local_signal("WUH")
    assert out["available"] is False
    assert "표본 부족" in out["reason"]
    assert all(t.get("undetermined") for t in out["titles"])


def test_zero_views_is_unknown_not_normal():
    """예전엔 0/0 → ratio 1.0('평소 수준')이었다 — 없는 자료를 정상으로 판 것이다."""
    with patch("algorithms.local_signal._daily_views",
               return_value=_items(0, 0)):
        out = ls.fetch_local_signal("WUH")
    assert out["available"] is False


def test_healthy_sample_still_scores():
    with patch("algorithms.local_signal._daily_views",
               return_value=_items(300, 100)):
        out = ls.fetch_local_signal("WUH")
    assert out["available"] is True
    assert out["max_anomaly_ratio"] == 3.0
    assert "급증" in out["verdict"]


def test_mixed_titles_use_only_the_determined_ones(monkeypatch):
    calls = {"n": 0}

    def views(lang, title, start, end):
        calls["n"] += 1
        return _items(300, 100) if calls["n"] == 1 else _items(9, 3)

    monkeypatch.setattr(ls, "_daily_views", views)
    out = ls.fetch_local_signal("WUH")
    assert out["available"] is True and out["max_anomaly_ratio"] == 3.0
    assert sum(1 for t in out["titles"] if t.get("undetermined")) == 1


def test_titles_carry_ko_en_fr_labels():
    """문서마다 한·영·불 병기가 붙는다. 원문(title)은 그대로 둔다."""
    with patch("algorithms.local_signal._daily_views",
               return_value=_items(300, 100)):
        out = ls.fetch_local_signal("WUH")
    by_title = {t["title"]: t["label"] for t in out["titles"]}
    assert by_title["流行性感冒"] == {"ko": "독감", "en": "Influenza", "fr": "Grippe"}
    assert by_title["传染病"]["ko"] == "전염병"


def test_every_mapped_city_title_has_a_label():
    """CITY_WIKI에 있는 문서가 병기에서 빠지면 원문만 보인다 — 전부 있어야 한다."""
    missing = [t for _, titles in ls.CITY_WIKI.values() for t in titles
               if t not in ls.TITLE_I18N]
    assert missing == []


def test_unknown_city_is_unavailable():
    out = ls.fetch_local_signal("XXX")
    assert out["available"] is False and "매핑 없음" in out["reason"]

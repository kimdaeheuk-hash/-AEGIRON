"""오지 관찰층 — 프록시 융합 + 희소성 가드 (2026-11-03).

외부 fetch는 전부 mock. 모르면 모른다고 말하는지 본다.
"""
from __future__ import annotations

from algorithms import remote_area as ra


def _feed(status="ok", count=30, ratio=0.2):
    return {"status": status, "hit_ratio": ratio, "item_count": count,
            "keyword_hits": {"cholera": 3}, "sample_titles": ["t"]}


def test_assessed_when_proxies_alive(monkeypatch):
    """프록시 둘이 살면 observed."""
    monkeypatch.setattr(ra, "fetch_climate",
                        lambda lat, lng: {"temps": [30.0] * 20})
    monkeypatch.setattr(ra, "fetch_local_feed",
                        lambda *a, **k: _feed())
    out = ra.assess_territory("drc_east")
    assert out["assessed"] is True
    assert out["verdict"] == "observed"
    assert out["watch_grade"] is True


def test_undetermined_when_sample_thin(monkeypatch):
    """표본 부족이면 판정 불가 — 조용함을 안전으로 읽지 않는다."""
    monkeypatch.setattr(ra, "fetch_climate",
                        lambda lat, lng: {"temps": [30.0] * 20})
    monkeypatch.setattr(ra, "fetch_local_feed",
                        lambda *a, **k: _feed(count=3))
    out = ra.assess_territory("drc_east")
    assert out["assessed"] is False
    assert out["verdict"] == "undetermined"


def test_unknown_territory(monkeypatch):
    """미등록 영토는 사유와 함께 모름."""
    out = ra.assess_territory("atlantis")
    assert out["assessed"] is False


def test_assess_all_keeps_order_and_survives_failure(monkeypatch):
    """전수 평가 — 하나가 터져도 나머지는 돈다."""
    def boom(lat, lng):
        raise RuntimeError("net down")

    monkeypatch.setattr(ra, "fetch_climate", boom)
    monkeypatch.setattr(ra, "fetch_local_feed",
                        lambda *a, **k: _feed())
    out = ra.assess_all()
    assert [r["key"] for r in out] == [r[0] for r in ra.REMOTE_TERRITORIES]
    assert all(r["verdict"] == "undetermined" for r in out)


def test_endpoint_lists_entries(monkeypatch):
    """핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다."""
    import main as main_mod

    monkeypatch.setattr(ra, "fetch_climate",
                        lambda lat, lng: {"temps": [30.0] * 20})
    monkeypatch.setattr(ra, "fetch_local_feed",
                        lambda *a, **k: _feed())
    full = main_mod.remote_watch()
    assert full["count"] == len(ra.REMOTE_TERRITORIES)
    assert full["grade"] == "watch"
    one = main_mod.remote_watch(territory="yemen")
    assert one["count"] == 1 and one["entries"][0]["iso3"] == "YEM"

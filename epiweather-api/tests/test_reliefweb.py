"""구호망 2차 확인층 — ReliefWeb (2026-11-03).

requests.post를 mock — 외부 HTTP 실호출 없음(conftest 가드 준수).
민감도 규칙(등급 표기·정밀위치 미수집·ProMED 미편입 선언)을 본다.
"""
from __future__ import annotations

from algorithms import reliefweb as rw


def _resp(items):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": items}

    return R()


def _item(title, disaster=(), countries=("Yemen",), url="https://rw/x"):
    return {"fields": {
        "title": title, "date": "2026-11-01T00:00:00+00:00",
        "country": [{"name": c} for c in countries], "url": url,
        "disaster": [{"name": d} for d in disaster],
        "source": [{"name": "OCHA"}]}}


def test_filters_disease_reports(monkeypatch):
    """질병 관련만 남긴다. 좌표는 들고 오지 않는다."""
    monkeypatch.setattr(rw.requests, "post", lambda *a, **k: _resp([
        _item("Cholera outbreak in Yemen", disaster=("Cholera",)),
        _item("Road construction update"),
    ]))
    out = rw.fetch_reports()
    assert out["available"] is True
    assert out["fetched"] == 2
    assert out["disease_count"] == 1
    hit = out["disease_reports"][0]
    assert hit["kw_hits"] == ["cholera", "outbreak"]
    assert "lat" not in hit and "lon" not in hit and "coords" not in hit
    assert "검증" in out["grade"]


def test_promed_gap_is_declared(monkeypatch):
    """ProMED 미편입을 선언한다."""
    monkeypatch.setattr(rw.requests, "post", lambda *a, **k: _resp([]))
    out = rw.fetch_reports()
    assert out["promed"]["integrated"] is False


def test_failure_is_unknown_not_empty(monkeypatch):
    """조회 실패는 실패로 말한다 — 0건으로 접지 않는다."""
    def boom(*a, **k):
        raise ConnectionError("net down")

    monkeypatch.setattr(rw.requests, "post", boom)
    out = rw.fetch_reports()
    assert out["available"] is False
    assert "ConnectionError" in out["reason"]


def test_endpoint_returns_payload(monkeypatch):
    """핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다."""
    import main as main_mod

    monkeypatch.setattr(rw.requests, "post", lambda *a, **k: _resp([
        _item("Measles campaign", disaster=("Measles",)),
    ]))
    out = main_mod.relief_watch(limit=5)
    assert out["disease_count"] == 1


def test_403_explains_appname_registration(monkeypatch):
    """403이면 무료 등록 안내를 붙인다."""
    import requests as rq

    def denied(*a, **k):
        raise rq.HTTPError("403 Client Error: Forbidden")

    monkeypatch.setattr(rw.requests, "post", denied)
    out = rw.fetch_reports()
    assert out["available"] is False
    assert "apidoc.reliefweb.int" in out["reason"]

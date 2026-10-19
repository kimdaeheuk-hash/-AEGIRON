"""WAHIS 동물신호 — 못 읽음을 '30일 발병 0건'으로 쓰지 않는다 (2026-10-19).

운영 로그가 매시간 'WAHIS 동물신호: 30일 발병 0건, 감시질병 활성 0종'을 찍었다.
fetch_wahis_outbreaks 가 200 이 아니거나 예외가 나면 조용히 [] 를 돌려줬기 때문이다.
이 값은 지수와 부정적 공간(보고 급감 판정)에 그대로 들어간다. 실제 WAHIS 호출은 mock.
"""
from __future__ import annotations
from unittest.mock import patch, MagicMock

import requests

from algorithms import wahis


def _resp(status=200, payload=None, json_exc=None):
    m = MagicMock(status_code=status)
    if json_exc is not None:
        m.json = MagicMock(side_effect=json_exc)
    else:
        m.json = MagicMock(return_value=payload)
    return m


ITEM_AI = {"disease": {"name": "Highly pathogenic avian influenza"},
           "country": {"name": "Poland"}, "reportDate": "2026-10-10", "cases": 12}
ITEM_ASF = {"disease": "African swine fever", "country": "Viet Nam", "date": "2026-10-12"}


# ── fetch_wahis_outbreaks: 다섯 경로 ─────────────────────────────────────────

def test_success_parses_items():
    with patch("algorithms.wahis.requests.get", return_value=_resp(payload={"data": [ITEM_AI, ITEM_ASF]})):
        outbreaks, reason = wahis.fetch_wahis_outbreaks("k")
    assert reason is None
    assert [o["country"] for o in outbreaks] == ["Poland", "Viet Nam"]
    assert outbreaks[0]["disease"] == "Highly pathogenic avian influenza"


def test_explicit_empty_list_is_real_zero():
    # 응답이 '목록이 비었다'고 분명히 말하면 그것은 진짜 0건이다.
    with patch("algorithms.wahis.requests.get", return_value=_resp(payload={"data": []})):
        outbreaks, reason = wahis.fetch_wahis_outbreaks("k")
    assert outbreaks == [] and reason is None


def test_http_error_is_none_with_status_not_empty_list():
    with patch("algorithms.wahis.requests.get", return_value=_resp(status=404)):
        outbreaks, reason = wahis.fetch_wahis_outbreaks()
    assert outbreaks is None          # 예전엔 [] → '30일 발병 0건'
    assert reason == "HTTP 404"


def test_network_exception_is_none_with_reason():
    with patch("algorithms.wahis.requests.get", side_effect=requests.Timeout("slow")):
        outbreaks, reason = wahis.fetch_wahis_outbreaks()
    assert outbreaks is None
    assert reason == "Timeout"


def test_non_json_body_is_none():
    # 200 인데 HTML 이 오는 경우(로그인 페이지 등) — 파싱 실패를 0건으로 읽지 않는다.
    with patch("algorithms.wahis.requests.get",
               return_value=_resp(json_exc=ValueError("Expecting value"))):
        outbreaks, reason = wahis.fetch_wahis_outbreaks()
    assert outbreaks is None
    assert reason == "ValueError"


def test_unknown_shape_is_none_not_zero():
    # 예전 코드는 data.get("data") or data.get("items") or [] 라 이것도 0건이었다.
    with patch("algorithms.wahis.requests.get",
               return_value=_resp(payload={"message": "Unauthorized"})):
        outbreaks, reason = wahis.fetch_wahis_outbreaks()
    assert outbreaks is None
    assert reason == "응답 형식 불일치"


# ── get_animal_signal: None 이 지표까지 그대로 간다 ───────────────────────────

def test_signal_failure_propagates_none_and_keeps_rss(monkeypatch):
    monkeypatch.setattr(wahis, "fetch_wahis_outbreaks", lambda key=None: (None, "HTTP 401"))
    monkeypatch.setattr(wahis, "fetch_woah_rss_count", lambda: 10)
    monkeypatch.delenv("WAHIS_API_KEY", raising=False)
    sig = wahis.get_animal_signal()
    assert sig["outbreaks_30d"] is None
    assert sig["watch_hits"] is None
    assert sig["api_reason"] == "HTTP 401"
    assert sig["has_api_key"] is False
    assert sig["woah_rss_items"] == 10      # RSS 는 따로 산다
    assert sig["outbreaks"] == []


def test_signal_success_counts_watch_diseases(monkeypatch):
    monkeypatch.setattr(wahis, "fetch_wahis_outbreaks",
                        lambda key=None: ([{"disease": "Highly pathogenic avian influenza"},
                                           {"disease": "African swine fever"},
                                           {"disease": "Something else"}], None))
    monkeypatch.setattr(wahis, "fetch_woah_rss_count", lambda: 10)
    sig = wahis.get_animal_signal()
    assert sig["outbreaks_30d"] == 3
    assert sig["watch_hits"] == 2
    assert sig["api_reason"] is None


def test_signal_metrics_reads_none_not_zero():
    # 지수 층의 실제 추출기가 None 을 그대로 받아야 지수·부정적 공간이 '판정 안 함'으로 둔다.
    from algorithms import signal_metrics
    getters = {m[0]: m[2] for layer in signal_metrics.LAYERS.values() for m in layer["metrics"]}
    failed = {"wahis": {"outbreaks_30d": None, "watch_hits": None, "woah_rss_items": 10}}
    assert getters["wahis_outbreaks_30d"](failed) is None
    assert getters["wahis_watch_hits"](failed) is None
    ok = {"wahis": {"outbreaks_30d": 0, "watch_hits": 0, "woah_rss_items": 10}}
    assert getters["wahis_outbreaks_30d"](ok) == 0      # 진짜 0건은 0 으로 남는다

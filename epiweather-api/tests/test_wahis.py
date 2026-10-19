"""WOAH 동물신호 — RSS 만 쓴다 (2026-10-19 캡틴 결정 "RSS만 써라").

배경: 운영 로그가 매시간 'WAHIS 동물신호: 30일 발병 0건'을 찍었다. WAHIS API 호출이
실패했는데 그 실패가 0 으로 기록됐다(#94 에서 '판정 안 함'으로 고침). 고친 뒤 운영 로그가
실제 사유를 보여 줬다 — `HTTP 400, 키 없음`. 캡틴 결정으로 API 를 걷어 내고 RSS 만 쓴다.
이 시험은 ① API 를 다시 부르지 않음 ② 30일 발병 건수를 0 으로 채우지 않음
③ RSS 를 못 읽으면 사유와 함께 None — 를 고정한다. 실제 호출은 mock.
"""
from __future__ import annotations

import ast
import pathlib
from unittest.mock import patch, MagicMock

import requests

from algorithms import wahis

COLLECTOR_PY = pathlib.Path(__file__).resolve().parents[1] / "collector.py"
RSS = '<?xml version="1.0"?><rss version="2.0"><channel>' + "<item>x</item>" * 10 + "</channel></rss>"


def _resp(status=200, text=RSS):
    return MagicMock(status_code=status, text=text)


# ── RSS 읽기 ──────────────────────────────────────────────────────────

def test_rss_counts_items():
    with patch("algorithms.wahis.requests.get", return_value=_resp()):
        assert wahis.fetch_woah_rss_count() == (10, None)


def test_rss_http_error_is_none_with_status():
    with patch("algorithms.wahis.requests.get", return_value=_resp(status=403, text="")):
        assert wahis.fetch_woah_rss_count() == (None, "HTTP 403")


def test_rss_network_error_is_none_with_reason():
    with patch("algorithms.wahis.requests.get", side_effect=requests.Timeout("slow")):
        assert wahis.fetch_woah_rss_count() == (None, "Timeout")


def test_non_rss_page_is_not_read_as_zero_items():
    # 200 인데 차단·점검 안내 HTML 이 오면 '항목 0건'이 아니라 못 읽음이다.
    with patch("algorithms.wahis.requests.get", return_value=_resp(text="<html>점검 중</html>")):
        assert wahis.fetch_woah_rss_count() == (None, "RSS 형식 아님")


# ── 신호: API 를 부르지 않고, 30일 발병 건수를 0 으로 채우지 않는다 ─────────

def test_signal_calls_only_the_rss_never_the_retired_api():
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return _resp()

    with patch("algorithms.wahis.requests.get", side_effect=fake_get):
        sig = wahis.get_animal_signal()
    assert calls == [wahis.WOAH_RSS_URL]
    assert not any("wahis.woah.org/api" in u for u in calls)
    assert sig["woah_rss_items"] == 10 and sig["rss_reason"] is None
    assert sig["outbreaks_30d"] is None and sig["watch_hits"] is None   # 0 이 아니다
    assert sig["api_status"] == "retired"


def test_signal_carries_rss_failure_reason():
    with patch("algorithms.wahis.requests.get", return_value=_resp(status=503, text="")):
        sig = wahis.get_animal_signal()
    assert sig["woah_rss_items"] is None and sig["rss_reason"] == "HTTP 503"


def test_index_metrics_read_none_not_zero():
    # 지수 층의 실제 추출기가 None 을 그대로 받아야 지수·부정적 공간이 '판정 안 함'으로 둔다.
    from algorithms import signal_metrics
    getters = {m[0]: m[2] for layer in signal_metrics.LAYERS.values() for m in layer["metrics"]}
    with patch("algorithms.wahis.requests.get", return_value=_resp()):
        row = {"wahis": wahis.get_animal_signal()}
    assert getters["wahis_outbreaks_30d"](row) is None
    assert getters["wahis_watch_hits"](row) is None


# ── 수집기: RSS 를 못 읽으면 이 소스는 실패다 ───────────────────────────

def test_collector_marks_source_failed_when_rss_is_unreadable():
    """RSS 가 이 소스의 전부라, 못 읽은 주기에 결과를 남기면 소스 건강이 '정상'으로 센다.
    WAHIS 블록이 그때 예외를 올리고, except 가 result["wahis"] 를 None 으로 둔다."""
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    block = next(t for t in ast.walk(fn) if isinstance(t, ast.Try)
                 and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                         and c.func.id == "get_animal_signal" for c in ast.walk(t)))
    assert any(isinstance(n, ast.Raise) for s in block.body for n in ast.walk(s)), \
        "RSS 를 못 읽어도 예외를 올리지 않는다 — 소스 건강이 실패를 못 본다"
    sets_none = [
        n for h in block.handlers for n in ast.walk(h)
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and n.value.value is None
        and any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                and t.slice.value == "wahis" for t in n.targets)]
    assert sets_none, "실패 시 result['wahis'] = None 으로 두지 않는다"

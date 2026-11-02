"""Tavily 다음 2차 폴백 — GDELT DOC artlist (2026-10-28).

## 왜 만드는가
10-08 장애는 Google 단독이라 1차(Tavily)로 살았다. 하지만 Tavily 키가 비어 있으면
체인이 거기서 멈춘다("대체 공급자 없음") — 1차가 죽는 경우도 마찬가지다. 2차는 키 없이
나가는 무료 GDELT 다: 세 공급자가 동시에 죽지 않는 한 뉴스 층(Sentinel·NewsWatch)은 산다.

## 이 파일이 막아야 하는 것
1. 평문 질의를 GDELT 에 그대로 보내는 것 — GDELT 는 공백을 AND 로 읽어 11개 단어가
   전부 든 기사만 맞힌다(사실상 빈손). 낱말 OR 로 바꿔야 한다.
2. GDELT 가 거부할 질의를 네트워크에 내보내는 것 — 린트(`lint_gdelt_query`)가 먼저 걸러야 한다.
3. 2차가 답한 것을 Google 이 답한 것처럼 내보내는 것 — provider 태그(`gdelt`·`gdelt_news`)
   와 호출부의 "못 찾음≠없음" 규칙이 그대로 덮여야 한다.
4. 셋 다 실패했을 때 사유가 사라지는 것 — 세 사유가 한 줄에 다 실려야 한다.
5. Google·Tavily 가 멀쩡할 때 2차를 부르는 것(불필요 호출·GDELT 속도 예산 낭비).
6. 만들어만 두고 아무도 안 부르는 것(AST 배선).

GDELT artlist 실응답은 샌드박스에서 확인하지 못했다(외부 HTTP 금지). 요청 모양
(`mode=artlist`·`format=json`·`articles[].title/url`)은 GDELT DOC 2.1 공개 문서와
이 저장소의 `gdelt_signals.coverage` 가 다루는 호스트·응답 꼴을 따른다.
프로덕션 첫 2차 주기가 첫 검증이다.
"""
from __future__ import annotations

import ast
import pathlib

import pytest
import requests

from algorithms import alerts as alerts_mod
from algorithms import brief_sections as bs
from algorithms import gdelt_signals as gs
from algorithms import news_fallback as nf
from algorithms import news_watch as nw
from algorithms import pathogen_sentinel as ps
from algorithms.alerts import refresh_alerts

ARTICLES = [
    ("Plague outbreak: Russia quarantines 200 after researcher dies",
     "https://www.deccanherald.com/world/plague-russia"),
    ("Has plague returned to Siberia? Panic after death of lab worker",
     "https://www.euronews.com/health/plague-siberia"),
    ("Nearly 200 People Under Observation After Irkutsk Lab Worker Dies",
     "https://www.themoscowtimes.com/2026/10/05/irkutsk-plague"),
]


class _Resp:
    """requests.Response 흉내 — raise_for_status 와 json 만 쓴다."""

    def __init__(self, status=200, payload=None):
        self.status_code, self._payload = status, payload

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code} Client Error")
            err.response = self
            raise err

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _artlist_ok(pairs=ARTICLES):
    return _Resp(200, {"articles": [{"title": t, "url": u} for t, u in pairs]})


def _google_down(monkeypatch, module, status="503 Server Error"):
    monkeypatch.setattr(module, "fetch_local_feed",
                        lambda *a, **k: {"status": "error", "error": status})


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)
    nw._STATE["provider"] = nw.GOOGLE_NEWS
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    # GDELT 속도 예산(5.5초)은 프로덕션용이다 — 시험에서 실제로 기다리면 스위트가 느려진다.
    monkeypatch.setattr(gs, "_gdelt_throttle", lambda: None)
    yield
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)


# ── gdelt_headlines: 요청 모양 ─────────────────────────────────────

def test_plain_words_become_an_or_query_or_nothing_matches(monkeypatch):
    seen = {}
    monkeypatch.setattr(nf.requests, "get",
                        lambda url, params=None, timeout=None: seen.update(
                            url=url, params=params) or _artlist_ok())
    nf.gdelt_headlines("plague anthrax smallpox")
    assert seen["url"] == nf.GDELT_URL
    assert seen["params"]["query"] == "(plague OR anthrax OR smallpox)"
    assert seen["params"]["mode"] == "artlist"
    assert seen["params"]["format"] == "json"
    assert seen["params"]["sort"] == "datedesc"


def test_a_gdelt_native_query_passes_through_untouched(monkeypatch):
    seen = {}
    monkeypatch.setattr(nf.requests, "get",
                        lambda url, params=None, timeout=None: seen.update(
                            params=params) or _artlist_ok())
    nf.gdelt_headlines("(plague OR anthrax) -sports")
    assert seen["params"]["query"] == "(plague OR anthrax) -sports"


def test_a_rejected_query_never_touches_the_network(monkeypatch):
    def boom(*a, **k):
        pytest.fail("거부된 질의가 네트워크에 나갔다")
    monkeypatch.setattr(nf.requests, "get", boom)
    with pytest.raises(nf.NewsFallbackError, match="gdelt 질의 거부"):
        nf.gdelt_headlines('"ab"')     # 5글자 미만 구문 — 린트가 네트워크 전에 건다


# ── gdelt_headlines: 응답 → `제목 - 매체` ───────────────────────────

def test_articles_become_google_shaped_titles(monkeypatch):
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    out = nf.gdelt_headlines("plague outbreak")
    assert out[0].endswith(" - deccanherald.com") and len(out) == 3


def test_articles_without_a_readable_publisher_keep_the_bare_title(monkeypatch):
    payload = _Resp(200, {"articles": [{"title": "Plague death in lab", "url": "not a url"},
                                       {"title": "", "url": "https://x.com/y"},
                                       "junk"]})
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: payload)
    assert nf.gdelt_headlines("q") == ["Plague death in lab"]


def test_network_failure_carries_the_supplier_and_its_reason(monkeypatch):
    def down(*a, **k):
        raise requests.exceptions.ConnectionError("blocked")
    monkeypatch.setattr(nf.requests, "get", down)
    with pytest.raises(nf.NewsFallbackError, match="gdelt ConnectionError"):
        nf.gdelt_headlines("plague outbreak")


def test_a_response_without_an_articles_list_is_its_own_kind(monkeypatch):
    """GDELT 는 질의를 거부할 때 HTTP 200에 평문을 돌려준다 — articles 가 없으면 그 종류다."""
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _Resp(200, {"articles": None}))
    with pytest.raises(nf.NewsFallbackError, match="articles 목록이 없음"):
        nf.gdelt_headlines("plague outbreak")


# ── Sentinel 체인: Google → Tavily → GDELT ──────────────────────────

def test_sentinel_uses_gdelt_only_after_tavily_fails(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(432, {"detail": "limit"}))
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    titles = ps.fetch_titles(now=1000.0)
    assert len(titles) == 3 and titles[0].endswith(" - deccanherald.com")
    assert ps.last_provider() == ps.GDELT


def test_sentinel_without_a_tavily_key_still_has_gdelt(monkeypatch):
    """키가 없어 1차가 없는 배치는 2차가 살린다 — '대체 공급자 없음'으로 멈추지 않는다."""
    _google_down(monkeypatch, ps, "403 proxy")
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    assert len(ps.fetch_titles()) == 3
    assert ps.last_provider() == ps.GDELT


def test_sentinel_tavily_answering_never_touches_gdelt(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(200, {"results": [
                            {"title": "t", "url": "https://a.com/x"}]}))
    monkeypatch.setattr(ps, "gdelt_headlines",
                        lambda *a, **k: pytest.fail("1차가 답했는데 2차를 불렀다"))
    assert ps.fetch_titles(now=1000.0) == ["t - a.com"]
    assert ps.last_provider() == ps.TAVILY


def test_sentinel_all_three_down_keeps_all_three_reasons(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps, "503 Server Error: Service Unavailable for url: https://news.google.com/rss/search?q=%28plague")
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(432, {"detail": "limit"}))
    def down(*a, **k):
        raise requests.exceptions.ConnectionError("blocked")
    monkeypatch.setattr(nf.requests, "get", down)
    with pytest.raises(ps.SentinelError) as e:
        ps.fetch_titles()
    msg = str(e.value)
    assert "503" in msg and "tavily HTTPError 432" in msg and "2차 gdelt" in msg
    assert ps.last_provider() == ps.GOOGLE      # 실패는 공급자 상태를 바꾸지 않는다


# ── NewsWatch 체인 ─────────────────────────────────────────────────

def test_watch_uses_gdelt_after_tavily_fails_and_says_so(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw)
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(432, {"detail": "limit"}))
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    titles = nw.fetch_headlines()
    assert len(titles) == 3 and nw._STATE["provider"] == nw.GDELT_NEWS


def test_watch_without_a_key_still_has_gdelt(monkeypatch):
    _google_down(monkeypatch, nw, "503 Server Error")
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    assert len(nw.fetch_headlines()) == 3
    assert nw._STATE["provider"] == nw.GDELT_NEWS


def test_watch_all_three_down_keeps_all_three_reasons(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw, "503 Server Error")
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(432, {"detail": "limit"}))
    def down(*a, **k):
        raise requests.exceptions.ConnectionError("blocked")
    monkeypatch.setattr(nf.requests, "get", down)
    with pytest.raises(nw.NewsWatchError) as e:
        nw.fetch_headlines()
    msg = str(e.value)
    assert "503" in msg and "tavily HTTPError 432" in msg and "2차 gdelt" in msg
    assert nw._STATE["provider"] == nw.GOOGLE_NEWS


# ── 경보 파이프라인: 2차의 '없음'도 '모름'이다 ───────────────────────

def _stub_pipeline(monkeypatch):
    from unittest.mock import patch
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: {"gai": 10.0, "layers": {}})
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: {"status": "보낼 신규 경보 없음", "new_critical_high": 0})
    p = patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[])
    p.start()
    monkeypatch.setattr("algorithms.comtrade_signals.last_scan_incomplete", lambda: False)
    return p


def test_gdelt_silence_holds_the_row_instead_of_retiring_it(isolated_db, monkeypatch, capsys):
    """2차가 답한 주기의 '없음'도 '모름'이다 — 1차와 같은 규칙이 GDELT 에도 덮이는지 본다."""
    import db
    p = _stub_pipeline(monkeypatch)
    ok_titles = ['"q OR x" - Google News']
    ok_titles += [f"{t} - {n}" for (t, _), n in zip(ARTICLES, ["A", "B", "C"])]
    try:
        monkeypatch.setattr(ps, "fetch_local_feed",
                            lambda *a, **k: {"status": "ok", "_all_titles": ok_titles})
        refresh_alerts("2026-10-28")
        assert any(r["source"] == "headline:plague" for r in db.list_alerts("2026-10-28"))

        ps._CACHE.update(at=0.0, titles=None)
        _google_down(monkeypatch, ps)
        monkeypatch.setattr(nf.requests, "get",
                            lambda *a, **k: _Resp(200, {"articles": []}))  # 2차는 아무것도 못 찾음
        result = refresh_alerts("2026-10-28")
        assert [r["source"] for r in result["undetermined"]] == ["headline:plague"]
        assert result["retired"] == []
        out = capsys.readouterr().out
        assert "(gdelt 대체 — Google 막힘·없는 행은 내리지 않음)" in out
    finally:
        p.stop()


# ── 후보 근거: 2차가 답한 후보에도 정직성 문구가 붙는다 ───────────────

def test_gdelt_candidates_carry_the_gdelt_note_not_the_tavily_note(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    monkeypatch.setattr(nf.requests, "post",
                        lambda *a, **k: _Resp(432, {"detail": "limit"}))
    monkeypatch.setattr(nf.requests, "get", lambda *a, **k: _artlist_ok())
    (c,) = ps.candidates()
    assert c["source"] == "headline:plague"
    assert "근사" in c["evidence"][-1] and "GDELT" in c["evidence"][-1]
    assert "2차" in c["evidence"][-1]      # 1차(Tavily) 문구가 아니라 2차 문구다


# ── 브리핑: 2차가 답한 요약에 Google 출처를 붙이면 거짓이다 ───────────

def test_brief_section_credits_gdelt_for_a_gdelt_answer(monkeypatch):
    monkeypatch.setattr(nw, "latest_pulse", lambda *a, **k: {
        "summary": "요약", "urgency": "medium", "diseases": ["페스트"],
        "headline_count": 12, "source": "gdelt_news+cerebras",
        "observed_at": "2026-10-28T01:00:00"})
    ds = bs.build_news_pulse_section("ko")["data_source"]
    assert ds.startswith("GDELT 뉴스 검색") and "Google News RSS 제목" not in ds
    assert "gdelt_news+cerebras" in ds


# ── 배선: 만들어만 두고 안 부르면 안 된다 (AST) ──────────────────────

def _names(fn):
    src = ast.parse(pathlib.Path(fn.__code__.co_filename).read_text(encoding="utf-8"))
    target = next(n for n in ast.walk(src)
                  if isinstance(n, ast.FunctionDef) and n.name == fn.__name__)
    return {c.func.id for c in ast.walk(target)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def test_wiring_chains_reach_gdelt():
    assert "_fetch_secondary" in _names(ps.fetch_titles)
    assert "gdelt_headlines" in _names(ps._fetch_secondary)
    assert "_fetch_headlines_secondary" in _names(nw.fetch_headlines)
    assert "gdelt_headlines" in _names(nw._fetch_headlines_secondary)

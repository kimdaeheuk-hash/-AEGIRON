"""Google News 503 이 뉴스 층 셋을 동시에 죽였다 — 대체 공급자(Tavily)를 붙인다 (2026-10-09).

## 사고
10-08 15:00 UTC 부터 `news.google.com` 이 503 만 돌려줬다. 지난 2주는 매일 11·12시 두 주기만 막혔는데
그날은 24주기 중 10주기였고, 같은 원인으로 세 층이 한꺼번에 죽었다:

    NewsWatch   15:02~23:02 9주기 연속 실패 → `중단` (소스 건강 21/23)
    LocalNews   0/179 피드
    Sentinel    `⏸ 판정 안 함` — 페스트 경보가 15시 값에 얼어붙음

## 이 파일이 막아야 하는 것
1. 대체 경로가 답한 주기의 **'없음'을 '사건 없음'으로 읽는 것** — 대체는 관련도 순 상위 일부라 빠짐없지 않다.
   그렇게 읽으면 Google 이 막히는 시간마다 이미 올라 있던 경보가 내려갔다 올라오기를 반복한다.
2. 대체 경로가 답한 것을 **Google 이 답한 것처럼 내보내는 것**(브리핑 출처 문구, 근거의 매체 수).
3. 둘 다 실패했을 때 **사유가 사라지는 것** — 요약 줄은 120자에서 잘린다.
4. Google 이 멀쩡할 때 **대체 공급자를 부르는 것**(쿼터).
5. 만들어만 두고 아무도 안 부르는 것(AST 배선).

⚠️ Tavily 실제 응답은 샌드박스에서 확인하지 못했다(`api.tavily.com` 허용목록 403). 응답 모양은 이 저장소의
기존 호출이 읽는 `results[].title/url` 을 따른다. 프로덕션 첫 대체 주기가 첫 검증이다.
"""
from __future__ import annotations

import ast
import inspect

import pytest
import requests

from algorithms import alerts as alerts_mod
from algorithms import brief_sections as bs
from algorithms import news_fallback as nf
from algorithms import news_watch as nw
from algorithms import pathogen_sentinel as ps
from algorithms.alerts import refresh_alerts

URLS = [
    ("Plague outbreak: Russia quarantines 200 after researcher dies in Siberia",
     "https://www.deccanherald.com/world/plague-russia"),
    ("Has plague returned to Siberia? Panic in Russia after death of lab worker",
     "https://www.euronews.com/health/plague-siberia"),
    ("Nearly 200 People Under Observation After Irkutsk Lab Worker Dies From Plague",
     "https://www.themoscowtimes.com/2026/10/05/irkutsk-plague"),
]


class _Resp:
    """requests.Response 흉내 — raise_for_status 와 json 만 쓴다."""

    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code} Client Error")
            err.response = self
            raise err

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _tavily_ok(pairs=URLS):
    return _Resp(200, {"results": [{"title": t, "url": u, "content": "x"} for t, u in pairs]})


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)
    nw._STATE["provider"] = nw.GOOGLE_NEWS
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    yield
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)


def _google_down(monkeypatch, module, status="503 Server Error"):
    monkeypatch.setattr(module, "fetch_local_feed",
                        lambda *a, **k: {"status": "error", "error": status})


def _google_ok(monkeypatch, module, titles):
    monkeypatch.setattr(module, "fetch_local_feed",
                        lambda *a, **k: {"status": "ok", "_all_titles": ['"q OR x" - Google News', *titles]})


# ── news_fallback: 응답 → `제목 - 매체` ─────────────────────────────────

def test_publisher_is_the_url_domain_and_never_guessed():
    assert nf.publisher_from_url("https://www.reuters.com/a/b") == "reuters.com"
    assert nf.publisher_from_url("https://news.bbc.co.uk/x") == "news.bbc.co.uk"
    assert nf.publisher_from_url("https://user:pw@www.ap.org:8443/x") == "ap.org"
    assert nf.publisher_from_url("not a url") is None
    assert nf.publisher_from_url("") is None and nf.publisher_from_url(None) is None


def test_results_become_google_shaped_titles_and_the_request_is_a_news_search(monkeypatch):
    seen = {}

    def post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, json=json, timeout=timeout)
        return _tavily_ok()
    monkeypatch.setattr(nf.requests, "post", post)
    out = nf.tavily_headlines("plague outbreak", "tvly-key")
    assert out[0] == "Plague outbreak: Russia quarantines 200 after researcher dies in Siberia - deccanherald.com"
    assert seen["url"] == nf.TAVILY_URL
    assert seen["json"]["topic"] == "news" and seen["json"]["days"] == 1
    assert seen["json"]["max_results"] == nf.MAX_RESULTS == 20
    assert seen["timeout"] == nf.TIMEOUT


def test_untitled_results_are_dropped_and_missing_url_leaves_the_title_alone(monkeypatch):
    payload = {"results": [{"title": "  ", "url": "https://a.com/x"}, {"url": "https://b.com"},
                           {"title": "Plague death in lab", "url": None}, "junk"]}
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(200, payload))
    assert nf.tavily_headlines("q", "k") == ["Plague death in lab"]      # 매체를 지어내지 않는다


@pytest.mark.parametrize("resp, expect", [
    (_Resp(432, {"detail": {"error": "plan usage limit exceeded"}}), "HTTPError 432"),
    (_Resp(401, {"detail": "Unauthorized: invalid API key"}), "HTTPError 401"),
    (_Resp(200, {"unexpected": []}), "results 목록이 없음"),
    (_Resp(200, None), "ValueError"),
])
def test_failures_carry_their_kind(monkeypatch, resp, expect):
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: resp)
    with pytest.raises(nf.NewsFallbackError, match=expect):
        nf.tavily_headlines("q", "k")


def test_network_error_is_wrapped_not_leaked(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("proxy denied")
    monkeypatch.setattr(nf.requests, "post", boom)
    with pytest.raises(nf.NewsFallbackError, match="tavily ConnectionError"):
        nf.tavily_headlines("q", "k")


# ── Sentinel: 누가 답하는가 ──────────────────────────────────────────

def test_google_answering_never_touches_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_ok(monkeypatch, ps, ["Plague &amp; anthrax scare - AP"])
    monkeypatch.setattr(ps, "tavily_headlines",
                        lambda *a, **k: pytest.fail("Google 이 멀쩡한데 쿼터를 썼다"))
    assert ps.fetch_titles(now=1000.0) == ["Plague & anthrax scare - AP"]
    assert ps.last_provider() == ps.GOOGLE


def test_google_down_with_key_falls_back_to_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _tavily_ok())
    titles = ps.fetch_titles(now=1000.0)
    assert len(titles) == 3 and titles[0].endswith(" - deccanherald.com")
    assert ps.last_provider() == ps.TAVILY


def test_tavily_titles_still_become_the_irkutsk_candidate_with_an_honest_note(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _tavily_ok())
    (c,) = ps.candidates()
    assert c["source"] == "headline:plague" and "3개 매체" in c["label"]
    assert c["score"] == ps.SENTINEL_SCORE                      # 점수는 공급자와 무관한 고정 구간
    assert "근사" in c["evidence"][-1] and "Tavily" in c["evidence"][-1]


def test_google_candidates_carry_no_fallback_note():
    titles = [f"{t} - {p}" for (t, _), p in zip(URLS, ["Deccan Herald", "Euronews", "The Moscow Times"])]
    (c,) = ps.candidates(titles)
    assert all("Tavily" not in line for line in c["evidence"])


def test_google_down_without_key_says_so_and_still_raises(monkeypatch):
    _google_down(monkeypatch, ps, "403 proxy")
    with pytest.raises(ps.SentinelError) as e:
        ps.fetch_titles()
    msg = str(e.value)
    assert "Google News RSS 수집 실패" in msg and "403 proxy" in msg and "TAVILY_API_KEY" in msg


def test_both_down_keeps_both_reasons_and_the_fallback_survives_the_120_char_log_cut(monkeypatch):
    """alerts.py 는 `str(e)[:120]` 만 찍는다. 대체 사유가 뒤에 있으면 로그에서 사라진다."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps, "503 Server Error: Service Unavailable for url: https://news.google.com/rss/search?q=%28plague")
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(432, {"detail": "limit"}))
    with pytest.raises(ps.SentinelError) as e:
        ps.fetch_titles()
    shown = str(e.value)[:120]
    assert "503" in shown and "tavily HTTPError 432" in shown
    assert ps.last_provider() == ps.GOOGLE                         # 실패는 공급자 상태를 바꾸지 않는다


def test_provider_is_cached_with_the_titles(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, ps)
    calls = []
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: (calls.append(1) or _tavily_ok()))
    ps.fetch_titles(now=1000.0)
    _google_ok(monkeypatch, ps, ["x - y"])                         # 캐시 안에서는 Google 을 다시 안 부른다
    assert ps.fetch_titles(now=1000.0 + 60) and ps.last_provider() == ps.TAVILY
    assert len(calls) == 1                                         # 쿼터는 20분에 한 번


# ── Sentinel: 경보 파이프라인 안에서 (핵심) ──────────────────────────────

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


def test_fallback_silence_holds_the_row_instead_of_retiring_it(isolated_db, monkeypatch, capsys):
    """★핵심★ Google 이 답한 주기에 올라간 행이, 대체가 답한 주기에 '못 찾았다'로 내려가면 안 된다."""
    import db
    p = _stub_pipeline(monkeypatch)
    try:
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
        _google_ok(monkeypatch, ps, [f"{t} - {n}" for (t, _), n in zip(URLS, ["A", "B", "C"])])
        refresh_alerts("2026-10-09")
        assert any(r["source"] == "headline:plague" for r in db.list_alerts("2026-10-09"))

        ps._CACHE.update(at=0.0, titles=None)
        _google_down(monkeypatch, ps)
        monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(200, {"results": []}))   # 대체는 아무것도 못 찾음
        result = refresh_alerts("2026-10-09")
        assert [r["source"] for r in result["undetermined"]] == ["headline:plague"]
        assert result["retired"] == []
        out = capsys.readouterr().out
        assert "(tavily 대체 — Google 막힘·없는 행은 내리지 않음)" in out

        # 대조군 — Google 이 답했는데 제목이 없으면 그때는 내려간다(기존 계약 그대로)
        ps._CACHE.update(at=0.0, titles=None)
        _google_ok(monkeypatch, ps, [])
        result = refresh_alerts("2026-10-09")
        assert result["undetermined"] == []
        assert any(r["source"] == "headline:plague" for r in result["retired"])
    finally:
        p.stop()


def test_fallback_that_does_find_the_event_raises_the_row_and_still_holds_the_rest(isolated_db, monkeypatch):
    import db
    p = _stub_pipeline(monkeypatch)
    try:
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
        _google_down(monkeypatch, ps)
        monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _tavily_ok())
        result = refresh_alerts("2026-10-09")
        rows = [r for r in db.list_alerts("2026-10-09") if r["source"] == "headline:plague"]
        assert len(rows) == 1 and rows[0]["tier"] == "medium"          # 올리는 쪽은 대체도 그대로 한다
        assert [r["source"] for r in result["undetermined"]] == []     # 이번 주기에 살아 있는 행은 hold 대상이 아니다
    finally:
        p.stop()


def test_both_providers_down_still_holds_not_retires(isolated_db, monkeypatch):
    p = _stub_pipeline(monkeypatch)
    try:
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
        _google_ok(monkeypatch, ps, [f"{t} - {n}" for (t, _), n in zip(URLS, ["A", "B", "C"])])
        refresh_alerts("2026-10-09")
        ps._CACHE.update(at=0.0, titles=None)
        _google_down(monkeypatch, ps)
        monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(432, {"detail": "limit"}))
        result = refresh_alerts("2026-10-09")
        assert [r["source"] for r in result["undetermined"]] == ["headline:plague"]
    finally:
        p.stop()


# ── NewsWatch ────────────────────────────────────────────────────────

def test_news_watch_falls_back_and_says_who_answered(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw)
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _tavily_ok())
    titles = nw.fetch_headlines()
    assert len(titles) == 3 and nw._STATE["provider"] == nw.TAVILY_NEWS


def test_news_watch_google_ok_does_not_touch_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_ok(monkeypatch, nw, ["Cholera surge in Yemen - Reuters"])
    monkeypatch.setattr(nw, "tavily_headlines", lambda *a, **k: pytest.fail("쿼터를 썼다"))
    assert nw.fetch_headlines() == ["Cholera surge in Yemen - Reuters"]
    assert nw._STATE["provider"] == nw.GOOGLE_NEWS


def test_news_watch_without_a_key_raises_with_both_facts(monkeypatch):
    _google_down(monkeypatch, nw, "503 Server Error")
    with pytest.raises(nw.NewsWatchError) as e:
        nw.fetch_headlines()
    assert "Google News RSS 수집 실패" in str(e.value) and "TAVILY_API_KEY" in str(e.value)


def test_news_watch_both_down_keeps_the_fallback_reason_visible(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw, "503 Server Error: Service Unavailable for url: https://news.google.com/rss/search?q=%28outbreak")
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(432, {"detail": "limit"}))
    with pytest.raises(nw.NewsWatchError) as e:
        nw.fetch_headlines()
    assert "tavily HTTPError 432" in str(e.value)[:120]


def _stub_llm(monkeypatch):
    monkeypatch.setattr(nw, "_llm_json", lambda *a, **k: (
        {"has_new_signal": True, "summary": "요약", "diseases": ["페스트"], "urgency": "medium"},
        {"total_tokens": 10, "prompt_tokens": 5}))


def test_pulse_source_names_the_headline_provider_and_the_model(monkeypatch):
    _stub_llm(monkeypatch)
    _google_ok(monkeypatch, nw, ["Cholera surge in Yemen - Reuters"])
    assert nw.fetch_news_pulse("cere-key")["source"] == "google_news+cerebras"

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw)
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _tavily_ok())
    assert nw.fetch_news_pulse("cere-key")["source"] == "tavily_news+cerebras"


def test_pulse_with_zero_fallback_headlines_still_names_the_provider(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
    _google_down(monkeypatch, nw)
    monkeypatch.setattr(nf.requests, "post", lambda *a, **k: _Resp(200, {"results": []}))
    out = nw.fetch_news_pulse("cere-key")
    assert out["headline_count"] == 0 and out["source"] == "tavily_news"


# ── 브리핑: 출처 문구가 거짓이 되지 않는다 ───────────────────────────────

def _pulse(source):
    return {"summary": "요약", "urgency": "medium", "diseases": ["페스트"],
            "headline_count": 12, "source": source, "observed_at": "2026-10-09T01:00:00"}


def test_brief_section_does_not_credit_google_for_a_tavily_answer(monkeypatch):
    monkeypatch.setattr(nw, "latest_pulse", lambda *a, **k: _pulse("tavily_news+groq(x)"))
    ds = bs.build_news_pulse_section("ko")["data_source"]
    assert ds.startswith("Tavily 뉴스 검색") and "Google News RSS 제목" not in ds
    assert "tavily_news+groq(x)" in ds


def test_brief_section_credits_google_when_google_answered(monkeypatch):
    monkeypatch.setattr(nw, "latest_pulse", lambda *a, **k: _pulse("google_news+groq(x)"))
    assert bs.build_news_pulse_section("ko")["data_source"].startswith("Google News RSS 제목 12건")


# ── 배선 (AST) — 만들어만 두고 아무도 안 부르는 층 방지 ───────────────────

def _names(fn):
    tree = ast.parse(inspect.getsource(fn))
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
           {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def test_wiring_the_fallback_is_actually_called_and_the_hold_is_tied_to_the_provider():
    assert "tavily_headlines" in _names(ps.fetch_titles)
    assert "tavily_headlines" in _names(nw.fetch_headlines)
    names = _names(alerts_mod.collect_candidate_alerts)
    assert {"last_provider", "_mark_undetermined"} <= names
    # hold 가 공급자 판정 안에 있다 — 무조건 걸면 Google 이 답한 '없음'까지 내리지 못한다
    tree = ast.parse(inspect.getsource(alerts_mod.collect_candidate_alerts))
    guarded = [n for n in ast.walk(tree) if isinstance(n, ast.If)
               and any(isinstance(c, ast.Call) and getattr(c.func, "id", "") == "_mark_undetermined"
                       for b in n.body for c in ast.walk(b))
               and "provider" in ast.dump(n.test)]
    assert guarded, "대체 공급자가 답한 주기의 hold 가 provider 조건 밖으로 나갔다"

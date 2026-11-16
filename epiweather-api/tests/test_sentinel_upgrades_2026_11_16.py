"""고위험 병원체 감시 업그레이드 3건 (2026-11-16) — 한 질의 하나에 매달려 있던 층.

11-16 점검이 "16일 동안 `제목 0건`" 을 찾았고, 1차 수리는 **보이게** 만들었다
(24시간 창 + 일곱 번째 품질 불변식). 캡틴 지시로 층 자체를 튼튼하게 올린다.

이 층은 **이르쿠츠크 항페스트 연구소 연구원 사망(10-02)** 을 놓친 뒤에 생겼다.
'사건 하나가 곧 뉴스' 인 병원체를 카운트 지표로는 못 잡아서다. 그런데 그 층이
**검색 질의 하나**에 매달려 있었고, 그 하나가 조용해지자 16일을 눈 감고 있었다.

## ① 질의를 넓히고 정밀도는 코드가 쥔다

예전: `(plague OR anthrax OR smallpox) (death OR … OR lab leak) when:1d`
지금: `(plague OR anthrax OR smallpox) when:1d`

맥락 묶음을 서버에 걸면 **정밀도에 보탬이 없고 재현율만 깎인다** — 코드 쪽
`HEALTH_CONTEXT` 가 더 넓고(`confirmed`·`cases`·`infected`·`laboratory` …),
`NOT_A_DISEASE` 는 서버 질의로 아예 표현할 수 없다. 곁따라 오는 것: 넓은 질의의
`0건` 은 더는 모호하지 않다 — `plague` 한 낱말은 영어 뉴스에 매일 걸리므로
**넓은 질의가 0건이면 조용한 날이 아니라 고장이다.**

## ② 0건에도 무료 2차(GDELT)에게 한 번 더 묻는다

공급자 하나의 침묵을 세상의 침묵으로 읽지 않는다. Tavily 는 안 부른다(키·쿼터).

## ③ 버린 것을 센다

`후보 0개` 는 '전부 무관했다'와 '걸러내는 쪽이 과하게 걷어냈다'를 같은 글자로
보였다. #30 의 TED 와 같은 모양이고, 버린 건수를 찍으면 한 주기에 갈린다.
"""
import urllib.parse

import pytest

from algorithms import alerts as alerts_mod
from algorithms import news_fallback as nf
from algorithms import pathogen_sentinel as ps


# ── ① 넓은 질의 ─────────────────────────────────────────────────────

def test_the_query_asks_only_for_pathogen_words():
    q = urllib.parse.unquote(ps._url())
    assert "(plague OR anthrax OR smallpox)" in q and "when:1d" in q
    # 맥락 묶음이 질의에서 빠졌다 — 정밀도는 코드가 쥔다
    for word in ("death", "quarantine", "outbreak", "lab leak"):
        assert f"OR {word}" not in q and f"({word}" not in q


def test_the_false_positive_fix_from_112_is_untouched():
    """★ 질의를 넓힌 것이 #112 를 되돌린 게 아니다 ★

    그 수리의 알맹이는 `NOT_A_DISEASE` 의 장난감·밴드 제외이고 그대로 있다.
    (10-28 운영 오탐 전문을 그대로 쓴다.)
    """
    toy = ("JoyToy opens pre-orders for Warhammer 40,000 Death Guard Typhus "
           "and Plague Marine figures - ToyNews")
    assert ps.match_headlines([toy]) == {}
    for band in ("Anthrax guitarist Scott Ian announces tour - Loudwire",
                 "A Plague Tale sequel announced - IGN",
                 "Team plagued by injuries ahead of final - ESPN"):
        assert ps.match_headlines([band]) == {}


def test_widening_recovers_reports_the_old_query_could_lose():
    """`confirmed` 는 HEALTH_CONTEXT 에 있는데 옛 QUERY_CONTEXT 에는 없다.

    이 층을 만든 계기(연구원 사망 단건 보도)가 정확히 이런 모양이었다.
    """
    titles = ["Bubonic plague case confirmed in Mongolia - Reuters",
              "Mongolia confirms bubonic plague infection - AP"]
    found = ps.candidates(titles, provider=ps.GOOGLE)
    assert [c["source"] for c in found] == ["headline:plague"]
    # 옛 질의의 맥락 낱말은 이 제목들에 하나도 없다
    assert not any(w in titles[0].lower() for w in ps.QUERY_CONTEXT)


def test_query_terms_constant_is_still_what_news_watch_asserts():
    """test_news_watch.py 가 이 상수를 본다 — 넓히면서 깨지 않았다."""
    assert {"plague", "anthrax"} <= set(ps.QUERY_TERMS)


# ── ② 0건 → 무료 2차(GDELT) 동료 조회 ───────────────────────────────

@pytest.fixture(autouse=True)
def _fresh_sentinel_cache():
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)
    ps._FAIL.update(at=0.0, err=None)
    yield
    ps._CACHE.update(at=0.0, titles=None, provider=ps.GOOGLE)
    ps._FAIL.update(at=0.0, err=None)


def _google(titles):
    return lambda *a, **k: {"status": "ok", "_all_titles": list(titles)}


def test_an_empty_google_cycle_asks_gdelt_before_concluding(monkeypatch):
    monkeypatch.setattr(ps, "fetch_local_feed", _google([]))
    monkeypatch.setattr(ps, "gdelt_headlines",
                        lambda *a, **k: ["Anthrax outbreak kills herders - Interfax"])
    titles = ps.fetch_titles()
    assert titles and ps.last_provider() == ps.GDELT


def test_tavily_is_never_called_on_an_empty_cycle(monkeypatch):
    """★ 0건 주기는 장애보다 자주 온다 — 키·쿼터가 걸린 공급자를 쓰지 않는다 ★"""
    monkeypatch.setenv(ps.FALLBACK_KEY_ENV, "key-present")
    monkeypatch.setattr(ps, "fetch_local_feed", _google([]))
    called = []
    monkeypatch.setattr(ps, "tavily_headlines",
                        lambda *a, **k: called.append(1) or ["x - y"])
    monkeypatch.setattr(ps, "gdelt_headlines", lambda *a, **k: ["Plague case - AP"])
    ps.fetch_titles()
    assert called == [] and ps.last_provider() == ps.GDELT


def test_when_gdelt_is_also_empty_the_cycle_stays_an_honest_google_zero(monkeypatch):
    """둘 다 0건이면 Google 의 0건 그대로 — 거기서부터는 24시간 창이 받는다."""
    monkeypatch.setattr(ps, "fetch_local_feed", _google([]))
    monkeypatch.setattr(ps, "gdelt_headlines", lambda *a, **k: [])
    assert ps.fetch_titles() == []
    assert ps.last_provider() == ps.GOOGLE      # 대체가 답한 척하지 않는다


def test_a_failing_gdelt_does_not_turn_an_empty_cycle_into_an_error(monkeypatch):
    monkeypatch.setattr(ps, "fetch_local_feed", _google([]))
    monkeypatch.setattr(ps, "gdelt_headlines",
                        lambda *a, **k: (_ for _ in ()).throw(nf.NewsFallbackError("503")))
    assert ps.fetch_titles() == [] and ps.last_provider() == ps.GOOGLE


def test_a_non_empty_google_cycle_never_calls_the_peer(monkeypatch):
    monkeypatch.setattr(ps, "fetch_local_feed", _google(["Plague case confirmed - AP"]))
    called = []
    monkeypatch.setattr(ps, "gdelt_headlines", lambda *a, **k: called.append(1) or [])
    assert ps.fetch_titles() and ps.last_provider() == ps.GOOGLE
    assert called == []


def test_an_outage_still_uses_the_old_chain_tavily_then_gdelt(monkeypatch):
    """장애(예외) 때의 체인은 안 건드렸다 — 그쪽은 드물고 급하다."""
    monkeypatch.setenv(ps.FALLBACK_KEY_ENV, "key-present")
    monkeypatch.setattr(ps, "fetch_local_feed",
                        lambda *a, **k: {"status": "error", "error": "503"})
    monkeypatch.setattr(ps, "tavily_headlines", lambda *a, **k: ["Plague case - AP"])
    assert ps.fetch_titles() and ps.last_provider() == ps.TAVILY


# ── ③ 깔때기 — 버린 것을 센다 ───────────────────────────────────────

_MIXED = [
    "Bubonic plague case confirmed in Mongolia - Reuters",      # 후보가 되는 쪽
    "Mongolia confirms bubonic plague infection - AP",
    "JoyToy opens pre-orders for Warhammer 40,000 Death Guard "
    "Typhus and Plague Marine figures - ToyNews",               # 비질병
    "A Plague Tale sequel announced - IGN",                     # 비질병
    "Anthrax outbreak kills cattle in Siberia - Interfax",      # 매체 1곳
    "Team plagued by injuries ahead of final - ESPN",           # 병원체 낱말 없음
    "Local council debates smallpox memorial plaque - Herald",   # 건강맥락 없음
]


def test_the_funnel_counts_every_reason_a_title_was_dropped():
    ps.candidates(_MIXED, provider=ps.GOOGLE)
    f = ps.last_funnel()
    assert f["titles"] == len(_MIXED) and f["provider"] == ps.GOOGLE
    d = f["drops"]
    assert d["비질병"] == 2
    assert d["병원체낱말없음"] == 1
    assert d["건강맥락없음"] == 1
    assert d["매체부족"] == 1


def test_the_single_publisher_drop_keeps_an_example():
    """★ 가장 아까운 자리 ★ 병원체 보도가 왔는데 매체가 한 곳이라 못 올린 것이다.

    '사건 하나가 곧 뉴스' 인 병원체를 노리는 층이라, 여기 숫자가 꾸준히 쌓이면
    `MIN_PUBLISHERS=2` 자체가 정책 결정거리가 된다 — 그 판단을 하려면 수가 보여야 한다.
    """
    ps.candidates(_MIXED, provider=ps.GOOGLE)
    examples = ps.last_funnel()["drops"]["매체부족_예"]
    assert any("탄저" in e and "Siberia" in e for e in examples)


def test_the_funnel_does_not_change_which_candidates_are_raised():
    """깔때기는 세기만 한다 — 판정은 예전과 같아야 한다."""
    found = ps.candidates(_MIXED, provider=ps.GOOGLE)
    assert [c["source"] for c in found] == ["headline:plague"]
    assert "2개 매체" in found[0]["label"]


def test_match_headlines_still_works_without_a_drops_dict():
    """기존 호출부(인수 하나)를 깨지 않았다.

    이 단계는 `MIN_PUBLISHERS` 보다 앞이라 탄저(매체 1곳)도 여기까지는 들어온다 —
    걸러지는 건 `candidates()` 에서다.
    """
    assert set(ps.match_headlines(_MIXED)) == {"plague", "anthrax"}


def test_the_log_line_carries_the_funnel():
    ps.candidates(_MIXED, provider=ps.GOOGLE)
    text = alerts_mod._sentinel_funnel_text(ps.last_funnel())
    assert "병원체 일치" in text and "매체부족 1" in text and "비질병 2" in text
    assert "Siberia" in text                      # 무엇을 버렸는지까지


def test_the_log_line_is_silent_when_there_is_no_funnel():
    assert alerts_mod._sentinel_funnel_text({}) == ""


def test_the_funnel_is_actually_wired_into_the_printed_line():
    """★ 만들어만 두고 아무도 안 부르면 그물이 아니다 ★"""
    import inspect
    src = inspect.getsource(alerts_mod.collect_candidate_alerts)
    assert "last_funnel" in src and "_sentinel_funnel_text" in src

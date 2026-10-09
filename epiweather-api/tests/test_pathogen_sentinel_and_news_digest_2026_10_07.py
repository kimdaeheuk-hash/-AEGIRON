"""고위험 병원체 단건 보도 감시(3번)와 브리핑 '뉴스 요약'(2번) — 러시아 페스트 연구소 사건(2026-10) 이후.

사건: 이르쿠츠크 항페스트 연구소 연구원 사망(10-02 첫 보도). 아이기론은 NewsWatch 요약에서 사흘 뒤에야
언급했고, 그 요약은 경보 점수에 연결돼 있지 않았다. 질병이 알려져 있어 설명불가 즉시경보도 비켜 갔다.

## 이 파일이 막아야 하는 것
1. 보도 한 줄로 사람을 깨우는 것 — 두 매체 이상, medium 고정 구간, 폰(critical/high) 안 울림.
2. 비유·고유명사(plagued by, A Plague Tale, 밴드 Anthrax)를 병원체로 읽는 것.
3. 조회 실패를 '사건이 사라졌다'로 읽는 것 — 판정 안 함으로 두어야 한다.
4. 점수가 측정인 것처럼 보이는 것 — 근거 문구가 '키워드 일치·고정 구간'이라고 말해야 한다.
5. 낡은 AI 요약을 현재형으로 내보내는 것.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest
import requests

from algorithms import alerts as alerts_mod
from algorithms import news_watch as nw
from algorithms import pathogen_sentinel as ps
from algorithms.alerts import classify_tier, refresh_alerts

IRKUTSK = [
    "Plague outbreak: Russia quarantines 200 after researcher dies in Siberia - Deccan Herald",
    "Has plague returned to Siberia? Panic in Russia after death of lab worker - Euronews",
    "Nearly 200 People Under Observation After Irkutsk Lab Worker Dies From Plague - The Moscow Times",
]


def _feed(titles):
    return lambda *a, **k: {"status": "ok", "_all_titles": ["\"(plague OR anthrax) OR x\" - Google News", *titles]}


# ── 3번: 후보 만들기 ─────────────────────────────────────────

def test_irkutsk_headlines_become_one_plague_candidate():
    (c,) = ps.candidates(IRKUTSK)
    assert c["source"] == "headline:plague"
    assert "3개 매체" in c["label"]
    assert c["score"] == ps.SENTINEL_SCORE == 72.0
    assert classify_tier(c["score"]) == "medium"


def test_score_can_never_reach_high_alone():
    assert ps.SENTINEL_SCORE <= ps.SENTINEL_MAX_SCORE < 80
    assert classify_tier(ps.SENTINEL_MAX_SCORE) == "medium"


def test_evidence_says_it_is_keyword_match_not_a_measurement():
    (c,) = ps.candidates(IRKUTSK)
    assert "서로 다른 매체 3곳이 보도" in c["evidence"][0]
    assert "Plague outbreak: Russia quarantines 200" in c["evidence"][0]        # 실제 제목이 근거로 실린다
    assert "측정값이 아니라 헤드라인 키워드 일치" in c["evidence"][1]
    assert "고정 구간" in c["evidence"][1] and "진위·규모는 확인되지 않았다" in c["evidence"][1]


def test_one_publisher_is_not_enough():
    assert ps.candidates(["Plague death reported in lab - Daily Tabloid",
                          "Another plague death story - Daily Tabloid"]) == []


def test_same_headline_from_the_same_outlet_is_counted_once():
    titles = ["Plague outbreak in Siberia kills researcher - Reuters"] * 3
    assert ps.candidates(titles) == []


def test_publisher_is_never_guessed_when_missing():
    assert ps.split_publisher("Plague outbreak in Siberia kills researcher") == (
        "Plague outbreak in Siberia kills researcher", None)
    assert ps.candidates(["Plague death in Siberia", "Plague outbreak in Siberia kills one"]) == []


@pytest.mark.parametrize("title", [
    "Yankees plagued by injuries as season ends in death spiral - ESPN",
    "A Plague Tale sequel confirmed, studio says - IGN",
    "Anthrax guitarist dies after tour concert - Rolling Stone",
    "Plague Inc. confirmed for new outbreak mode - Polygon",
    "Plague of locusts death toll for crops - Farm Weekly",
])
def test_metaphors_games_and_bands_are_not_pathogens(title):
    assert ps.match_headlines([title]) == {}


def test_headline_without_health_context_is_not_an_event():
    assert ps.match_headlines(["Bubonic plague museum opens in London - BBC"]) == {}


def test_other_pathogens_are_detected_and_ebola_is_deliberately_absent():
    got = ps.match_headlines(["Anthrax outbreak kills cattle, 3 hospitalized - AP",
                              "Smallpox sample leak suspected at lab - Reuters",
                              "Ebola outbreak continues in Congo, cases rise - BBC"])
    assert set(got) == {"anthrax", "smallpox"}


# ── 3번: 조회·캐시 ───────────────────────────────────────────

def test_fetch_titles_drops_the_channel_title_and_unescapes(monkeypatch):
    monkeypatch.setattr(ps, "fetch_local_feed", _feed(["Plague &amp; anthrax scare - AP"]))
    assert ps.fetch_titles(now=1000.0) == ["Plague & anthrax scare - AP"]


def test_fetch_is_cached_for_twenty_minutes(monkeypatch):
    calls = []

    def feed(*a, **k):
        calls.append(1)
        return {"status": "ok", "_all_titles": ["x - y"]}
    monkeypatch.setattr(ps, "fetch_local_feed", feed)
    ps.fetch_titles(now=1000.0)
    ps.fetch_titles(now=1000.0 + 60)
    assert len(calls) == 1
    ps.fetch_titles(now=1000.0 + ps.CACHE_TTL_SEC + 1)
    assert len(calls) == 2


def test_feed_error_is_raised_with_its_reason(monkeypatch):
    monkeypatch.setattr(ps, "fetch_local_feed", lambda *a, **k: {"status": "error", "error": "403 proxy"})
    with pytest.raises(ps.SentinelError, match="403 proxy"):
        ps.fetch_titles()


# ── 3번: 경보 파이프라인 안에서 ──────────────────────────────

def _stub_pipeline(monkeypatch):
    from unittest.mock import patch
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: {"gai": 10.0, "layers": {}})
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    sent = []
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "보낼 신규 경보 없음", "new_critical_high": 0}))
    p = patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[])
    p.start()
    monkeypatch.setattr("algorithms.comtrade_signals.last_scan_incomplete", lambda: False)
    return sent, p


def test_plague_headlines_appear_as_a_medium_alert_and_do_not_page_the_phone(isolated_db, monkeypatch):
    sent, p = _stub_pipeline(monkeypatch)
    try:
        monkeypatch.setattr(ps, "fetch_local_feed", _feed(IRKUTSK))
        result = refresh_alerts("2026-10-07")
    finally:
        p.stop()
    import db
    rows = [r for r in db.list_alerts("2026-10-07") if r["source"] == "headline:plague"]
    assert len(rows) == 1 and rows[0]["tier"] == "medium"
    assert all(not batch for batch in sent)                 # 폰(critical/high)으로 아무것도 안 나갔다


def test_fetch_failure_holds_the_row_instead_of_retiring_it(isolated_db, monkeypatch):
    sent, p = _stub_pipeline(monkeypatch)
    import db
    try:
        monkeypatch.setattr(ps, "fetch_local_feed", _feed(IRKUTSK))
        refresh_alerts("2026-10-07")
        ps._CACHE.update(at=0.0, titles=None)
        ps._FAIL.update(at=0.0, err=None)
        monkeypatch.setattr(ps, "fetch_local_feed", lambda *a, **k: {"status": "error", "error": "503"})
        result = refresh_alerts("2026-10-07")
        assert [r["source"] for r in result["undetermined"]] == ["headline:plague"]
        assert db.list_alerts("2026-10-07")[0].get("suppressed") in (0, None, False)
        # 대조군 — 조회가 성공했는데 제목이 없으면 그때는 내려간다
        ps._CACHE.update(at=0.0, titles=None)
        ps._FAIL.update(at=0.0, err=None)               # 쿨다운이 풀린 뒤의 조회
        monkeypatch.setattr(ps, "fetch_local_feed", _feed([]))
        result = refresh_alerts("2026-10-07")
        assert result["undetermined"] == []
        assert any(r["source"] == "headline:plague" for r in result["retired"])
    finally:
        p.stop()


def test_collect_actually_calls_the_sentinel():
    """배선 — 만들어만 두고 아무도 안 부르는 층 방지(NewsWatch 가 정확히 그렇게 방치됐다)."""
    import ast
    import inspect
    src = ast.parse(inspect.getsource(alerts_mod.collect_candidate_alerts))
    names = {n.id for n in ast.walk(src) if isinstance(n, ast.Name)} | \
            {n.attr for n in ast.walk(src) if isinstance(n, ast.Attribute)}
    assert "sentinel_candidates" in names and "fetch_titles" in names


# ── 2번: 브리핑 '뉴스 요약' ──────────────────────────────────

def _log(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")


def _rec(ts, **pulse):
    base = {"has_new_signal": True, "summary": "러시아에서 페스트 의심 사례가 보고됐다.", "diseases": ["페스트"],
            "urgency": "high", "headline_count": 20, "source": "google_news+groq(x)"}
    return {"type": "free_sources", "timestamp": ts.isoformat(), "news_pulse": {**base, **pulse}}


NOW = dt.datetime(2026, 10, 7, 12, 0, 0)


def test_latest_pulse_returns_the_most_recent_fresh_record(tmp_path):
    f = tmp_path / "log.jsonl"
    _log(f, [_rec(NOW - dt.timedelta(hours=2), summary="오래된 요약"),
             {"type": "ai_sources", "timestamp": NOW.isoformat()},
             _rec(NOW - dt.timedelta(minutes=20), summary="최신 요약")])
    out = nw.latest_pulse(now=NOW, log_file=f)
    assert out["summary"] == "최신 요약" and out["observed_at"].startswith("2026-10-07T11:40")


def test_stale_pulse_is_not_presented_as_current(tmp_path):
    f = tmp_path / "log.jsonl"
    _log(f, [_rec(NOW - dt.timedelta(hours=5))])
    assert nw.latest_pulse(now=NOW, log_file=f) is None


def test_no_new_signal_or_missing_file_gives_none(tmp_path):
    f = tmp_path / "log.jsonl"
    _log(f, [_rec(NOW, has_new_signal=False, summary=None)])
    assert nw.latest_pulse(now=NOW, log_file=f) is None
    assert nw.latest_pulse(now=NOW, log_file=tmp_path / "없음.jsonl") is None


def test_latest_pulse_reads_only_the_tail_of_a_huge_log(tmp_path):
    f = tmp_path / "log.jsonl"
    filler = [{"type": "free_sources", "timestamp": NOW.isoformat(), "x": "y" * 500}] * 2000
    _log(f, [*filler, _rec(NOW - dt.timedelta(minutes=5))])
    out = nw.latest_pulse(now=NOW, log_file=f, tail_bytes=200_000)
    assert out and out["diseases"] == ["페스트"]


def test_section_carries_the_limits_and_is_not_an_alert(monkeypatch):
    from algorithms import brief_sections as bs
    monkeypatch.setattr(nw, "latest_pulse", lambda **k: {
        "has_new_signal": True, "summary": "러시아에서 페스트 의심 사례가 보고됐다.", "diseases": ["페스트"],
        "urgency": "high", "headline_count": 20, "source": "google_news+groq(x)",
        "observed_at": "2026-10-07T11:40:00"})
    for lang in ("ko", "en", "fr"):
        sec = bs.build_news_pulse_section(lang)
        assert sec["id"] == "news_pulse" and sec["grade"] == "watch"
        assert sec["lead"].startswith("러시아에서")
        assert sec["rows"] == [{"disease": "페스트"}]
        assert len(sec["honesty"]) > 40
    ko = bs.build_news_pulse_section("ko")
    assert "경보 점수에 연결돼 있지 않" in ko["honesty"] and "진위·규모는 확인되지 않았" in ko["honesty"]
    assert "보정 안 됨" in ko["why"]                         # 모델의 긴급도는 보정되지 않았다고 밝힌다


def test_section_is_silent_when_there_is_no_fresh_summary(monkeypatch):
    from algorithms import brief_sections as bs
    monkeypatch.setattr(nw, "latest_pulse", lambda **k: None)
    assert bs.build_news_pulse_section("ko") is None


def test_section_is_registered_last_so_it_never_leads_the_brief():
    from algorithms import brief_sections as bs
    assert bs._BUILDERS[-1][0] == "news_pulse"

"""재난 → 발병 감시창 (2026-08-28).

## 왜 만들었나
네팔 홍수를 계기로 확인했더니, 네팔어 뉴스 피드가 찾는 건 **질병 단어뿐**이라
홍수 기사는 아예 안 걸렸다(`test_nepal_coverage.py` 가 그 전제를 잠근다).

    시스템은 '발병 보도가 시작될 때' 네팔을 발견한다.
    그런데 그때는 이미 발병한 뒤다.

홍수 자체는 발병이 아니고 발병은 **뒤에** 온다. 이 파일이 잠그는 건 그 사이
시간을 실제로 쓰고 있는가다.

## 이 파일이 반드시 막아야 하는 것
1. **저장을 안 하면 조용히 반쪽이 된다.** GDACS RSS 는 최근 며칠치만 싣는데
   뎅기 창은 42일까지 열려 있어야 한다. RSS 에서 빠지는 순간 창이 닫히면
   **가장 중요한 후반부가 통째로 사라진다.**
2. **문턱이 조용히 달라지면 안 된다.** 감시창이 고경보 문턱을 낮추는데, 그게
   드러나지 않으면 고경보 수를 아무도 해석할 수 없다.
3. **손으로 넣은 ISO2→ISO3 표.** 오타 하나면 사고가 안 난 나라에 창이 열린다.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from algorithms import disaster_watch as dw
from algorithms import local_news as ln
from algorithms.country_resolve import iso2_to_iso3, resolve_country


# ── 픽스처: 상태 파일을 임시 경로로 격리 ─────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """운영 `data/disaster_watch.json` 을 절대 건드리지 않는다."""
    monkeypatch.setattr(dw, "STATE_FILE", tmp_path / "disaster_watch.json")


def _rss(items: str) -> str:
    return f'<?xml version="1.0"?><rss><channel>{items}</channel></rss>'


def _item(etype="FL", alert="Red", iso3="NPL", country="Nepal",
          date="Tue, 25 Aug 2026 00:00:00 GMT", eid="1000001",
          title="Red alert for flood in Nepal") -> str:
    return (
        f"<item><title>{title}</title>"
        f"<gdacs:eventtype>{etype}</gdacs:eventtype>"
        f"<gdacs:alertlevel>{alert}</gdacs:alertlevel>"
        f"<gdacs:eventid>{eid}</gdacs:eventid>"
        f"<gdacs:iso3>{iso3}</gdacs:iso3>"
        f"<gdacs:country>{country}</gdacs:country>"
        f"<gdacs:fromdate>{date}</gdacs:fromdate>"
        f"</item>"
    )


def _response(text: str, status: int = 200):
    r = requests.Response()
    r.status_code = status
    r._content = text.encode("utf-8")
    return r


# ── GDACS 파싱 ───────────────────────────────────────────────────────

def test_parses_a_flood_event():
    events = dw.parse_gdacs(_rss(_item()))
    assert len(events) == 1
    e = events[0]
    assert e["type"] == "FL" and e["alert"] == "red"
    assert e["iso3"] == "NPL" and e["date"] == "2026-08-25"


def test_multi_country_event_becomes_one_per_country():
    """국경을 넘는 재난에서 한 나라만 남기면 반대편 감시창을 통째로 잃는다."""
    events = dw.parse_gdacs(_rss(_item(iso3="NPL,IND", country="Nepal, India")))
    assert sorted(e["iso3"] for e in events) == ["IND", "NPL"]
    assert len({e["key"] for e in events}) == 2, "나라별로 키가 갈려야 한다"


def test_country_name_is_the_fallback_when_iso3_is_missing():
    """iso3 필드가 비어도 이름으로 해석한다 — 다만 **추측은 안 한다**."""
    events = dw.parse_gdacs(_rss(_item(iso3="", country="Nepal")))
    assert events and events[0]["iso3"] == "NPL"


def test_unreadable_items_are_dropped_not_invented():
    """★국가나 종류를 못 읽은 항목으로 창을 열면 안 된다★

    잘못 붙인 국가코드는 없는 것보다 나쁘다 — 사고가 안 난 나라에 창이 열린다.
    """
    bad = _rss(
        _item(iso3="", country="Somewhere in the Pacific")   # 해석 불가
        + _item(etype="", iso3="NPL")                         # 종류 없음
        + _item(date="not a date", eid="9", iso3="NPL")       # 날짜 못 읽음
        + _item()                                             # 정상 1건
    )
    events = dw.parse_gdacs(bad)
    assert len(events) == 1, f"버려야 할 항목이 살아남았다: {events}"


def test_zero_events_is_an_error_not_silence():
    """0건은 '재난이 없다' 가 아니라 '파서가 못 읽었다' 일 수 있다.

    이 둘이 구분 안 되면 그게 조용한 실패다 — 오늘 하루 내내 나온 그 모양.
    """
    with patch.object(dw.requests, "get", return_value=_response("<rss/>")):
        with pytest.raises(dw.DisasterWatchError) as exc:
            dw.fetch_gdacs_events()
    assert "못 읽었다" in str(exc.value)


def test_network_failure_carries_its_kind():
    with patch.object(dw.requests, "get",
                      side_effect=requests.Timeout("timed out")):
        with pytest.raises(dw.DisasterWatchError) as exc:
            dw.fetch_gdacs_events()
    assert "Timeout" in str(exc.value)


# ── 등급 게이트 ──────────────────────────────────────────────────────

def test_green_alerts_do_not_open_windows():
    """GDACS 는 매일 다수의 Green 을 낸다. 전부 열면 세계의 절반이 감시 대상이
    되고 그 순간 신호가 의미를 잃는다."""
    dw.record_events(dw.parse_gdacs(_rss(_item(alert="Green"))),
                     today=dt.date(2026, 8, 30))
    assert dw.open_windows(dt.date(2026, 8, 30)) == {}


def test_orange_and_red_both_open():
    for level in ("Orange", "Red"):
        dw.record_events(dw.parse_gdacs(_rss(_item(alert=level, eid=level))),
                         today=dt.date(2026, 8, 30))
    assert "NPL" in dw.open_windows(dt.date(2026, 8, 30))


# ── ★ 창이 시간에 따라 열리고 닫히는가 ★ ────────────────────────────

def test_the_window_opens_late_and_closes_late():
    """홍수 당일에는 콜레라 창이 아직 안 열린다 — 잠복기가 있기 때문이다."""
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    flood = dt.date(2026, 8, 25)

    def diseases(days):
        w = dw.open_windows(flood + dt.timedelta(days=days))
        return {x["disease"] for x in w.get("NPL", [])}

    assert diseases(0) == set(), "재난 당일에 이미 열려 있으면 잠복기를 무시한 것이다"
    assert "콜레라·장티푸스" in diseases(5)      # 3~14일
    assert "렙토스피라증" in diseases(5)          # 2~28일
    assert "콜레라·장티푸스" not in diseases(20), "수인성 창은 14일에 닫혀야 한다"
    assert "뎅기·말라리아" in diseases(20)        # 14~42일 — 이때부터가 매개체
    assert diseases(200) == set(), "200일이면 어떤 창도 열려 있으면 안 된다"


def test_vector_window_outlives_the_gdacs_feed():
    """★가장 중요★ 저장하지 않으면 여기서 무너진다.

    GDACS RSS 는 최근 며칠치만 싣는다. 20일 뒤에는 그 항목이 피드에 없다.
    그런데 뎅기 창은 42일까지 열려 있어야 한다 — 저장이 그걸 지킨다.
    """
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    # 이후 주기: GDACS 에 그 이벤트가 더는 없다(빈 목록을 기록)
    dw.record_events([], today=dt.date(2026, 9, 14))

    later = dw.open_windows(dt.date(2026, 9, 14))     # 재난 20일 뒤
    assert "NPL" in later, "피드에서 사라지자 창이 닫혔다 — 저장이 안 되고 있다"
    assert "뎅기·말라리아" in {w["disease"] for w in later["NPL"]}


def test_future_dated_events_do_not_open_windows():
    """예보성 항목(아직 안 일어난 재난)으로 창을 열면 안 된다."""
    dw.record_events(dw.parse_gdacs(_rss(_item(date="Fri, 25 Sep 2026 00:00:00 GMT"))),
                     today=dt.date(2026, 8, 30))
    assert dw.open_windows(dt.date(2026, 8, 30)) == {}


def test_old_events_are_pruned():
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    out = dw.record_events([], today=dt.date(2026, 8, 25)
                           + dt.timedelta(days=dw.EVENT_RETENTION_DAYS + 1))
    assert out["pruned"] == 1 and out["stored"] == 0


def test_retention_outlives_the_longest_window():
    """보관 기간이 가장 긴 창보다 짧으면 그 창은 절대 끝까지 못 간다."""
    assert dw.EVENT_RETENTION_DAYS > dw.MAX_WINDOW_DAYS


def test_upgrade_keeps_the_original_disaster_date():
    """Orange → Red 로 승격돼도 창의 기준일이 흔들리면 안 된다."""
    dw.record_events(dw.parse_gdacs(_rss(_item(alert="Orange"))), today=dt.date(2026, 8, 25))
    dw.record_events(dw.parse_gdacs(_rss(_item(alert="Red"))), today=dt.date(2026, 8, 27))
    w = dw.open_windows(dt.date(2026, 8, 30))["NPL"][0]
    assert w["disaster_date"] == "2026-08-25"
    assert w["alert_level"] == "red"


# ── 규칙 표의 정직성 ─────────────────────────────────────────────────

def test_wildfire_has_no_rule_on_purpose():
    """산불 → 발병 경로가 뚜렷하지 않다. 없는 규칙을 지어내면 표 전체가 못 믿을 게 된다."""
    assert "WF" not in dw.WATCH_RULES


def test_every_rule_carries_its_rationale():
    """근거 없는 숫자가 하나라도 있으면 다음 사람이 그걸 사실로 인용한다."""
    for etype, rules in dw.WATCH_RULES.items():
        for disease, keywords, lo, hi, why in rules:
            assert keywords, f"{etype}/{disease}: 매칭 키워드가 없다"
            assert 0 <= lo < hi, f"{etype}/{disease}: 창 구간이 이상하다 {lo}~{hi}"
            assert len(why) > 20, f"{etype}/{disease}: 근거가 비었다"


def test_report_never_claims_to_be_a_prediction():
    report = dw.disaster_watch_report()
    assert report["is_prediction"] is False
    assert report["windows_calibrated"] is False
    assert "예측이 아니다" in report["note"]


# ── ★ 손으로 넣은 ISO2→ISO3 표 ★ ────────────────────────────────────

def test_every_local_news_feed_maps_to_an_iso3():
    """피드 하나라도 안 풀리면 그 나라는 감시창이 있어도 뉴스에 반영이 안 된다."""
    missing = [f[0] for f in ln.LOCAL_FEEDS if ln._feed_iso3(f[0]) is None]
    assert not missing, f"ISO3 로 안 풀리는 피드: {missing}"


def test_a_country_with_two_feeds_still_resolves():
    """★실제로 걸렸던 버그★ 인도는 힌디어·영어 두 피드라 슬러그가 `gn_in_hi` 다.

    `slug[3:]` 을 그대로 쓰면 `in_hi` 가 돼 **인도만 감시창이 영영 적용되지
    않는다.** 홍수 다발국이라 조용히 넘어갈 수 없는 구멍이었다.
    """
    assert ln._feed_iso3("gn_in_hi") == "IND"
    assert ln._feed_iso3("gn_in_en") == "IND"


def test_iso2_table_agrees_with_the_korean_name_table():
    """★오타를 잡는 유일한 방법★ 손으로 넣은 표는 다른 근거로 대조해야 한다.

    `country_resolve._KO`(한글 국가명 → ISO3)는 내가 안 쓴 기존 표다.
    피드의 한글 국가명이 풀리는 것들만 골라 교차대조한다.
    """
    checked = 0
    for slug, name, _region, _hl, gl, _terms in ln._WORLD_SOURCES_EXTRA:
        expected = resolve_country(name)
        if not expected:
            continue
        checked += 1
        assert iso2_to_iso3(gl) == expected, f"{slug}({name}): {gl} 매핑이 틀렸다"
    assert checked >= 60, f"교차대조 표본이 너무 적다({checked}건) — 검증이 무의미해진다"


def test_unknown_iso2_is_none_not_a_guess():
    assert iso2_to_iso3("ZZ") is None
    assert iso2_to_iso3(None) is None
    assert iso2_to_iso3("") is None


# ── ★ 감시창이 실제로 뉴스를 바꾸는가 ★ ─────────────────────────────

def _feed(slug, ratio):
    return {"slug": slug, "lang": "x", "region": "y", "status": "ok",
            "item_count": 10, "keyword_hits": int(ratio * 10),
            "hit_ratio": ratio, "_all_titles": ["t"]}


def _run_local_news(feeds, windows):
    with patch.object(ln, "LOCAL_FEEDS", [(f["slug"], "x", "y", "u", []) for f in feeds]):
        with patch.object(ln, "fetch_local_feed",
                          side_effect=lambda slug, *a: next(
                              dict(f) for f in feeds if f["slug"] == slug)):
            return ln.fetch_all_local_news(watch_windows=windows)


_NEPAL_WINDOW = {"NPL": [{"disease": "콜레라·장티푸스", "disaster_type": "FL",
                          "days_since_disaster": 6}]}


def test_watch_window_promotes_a_feed_normally_ignored():
    """★이 층의 존재 이유★ 평시라면 넘겼을 보도를 감시창이 붙잡는다."""
    feeds = [_feed("gn_np", 0.10), _feed("gn_kr", 0.10)]

    without = _run_local_news(feeds, None)
    assert without["high_alert_feeds"] == 0, "0.10 은 평시 문턱 0.15 를 못 넘는다"

    with_window = _run_local_news(feeds, _NEPAL_WINDOW)
    promoted = [f["slug"] for f in with_window["high_alert"]]
    assert promoted == ["gn_np"], "감시창이 열린 나라만 올라와야 한다"
    assert with_window["watch_promoted_feeds"] == 1


def test_the_lowered_threshold_is_never_silent():
    """문턱이 조용히 달라지면 고경보 수를 아무도 해석할 수 없다."""
    out = _run_local_news([_feed("gn_np", 0.10)], _NEPAL_WINDOW)
    feed = out["high_alert"][0]
    assert feed["alert_basis"] == "disaster_watch_window"
    assert feed["watch_window"]["diseases"] == ["콜레라·장티푸스"]
    assert feed["watch_window"]["disasters"] == ["FL"]
    assert feed["watch_window"]["min_days_since_disaster"] == 6
    assert out["alert_threshold"] == ln.ALERT_THRESHOLD
    assert out["watch_alert_threshold"] == ln.WATCH_ALERT_THRESHOLD
    assert out["threshold_calibrated"] is False, "임의로 정한 값을 근거처럼 두면 안 된다"


def test_a_feed_over_the_normal_threshold_is_not_marked_as_promoted():
    """평시 문턱을 넘은 피드는 감시창이 없었어도 걸렸다 — 공을 가로채면 안 된다."""
    out = _run_local_news([_feed("gn_np", 0.50)], _NEPAL_WINDOW)
    assert out["high_alert_feeds"] == 1
    assert out["watch_promoted_feeds"] == 0
    assert "alert_basis" not in out["high_alert"][0]


def test_window_for_another_country_changes_nothing_here():
    out = _run_local_news([_feed("gn_np", 0.10)],
                          {"BRA": [{"disease": "뎅기·말라리아", "disaster_type": "FL",
                                    "days_since_disaster": 20}]})
    assert out["high_alert_feeds"] == 0


def test_no_windows_behaves_exactly_like_before():
    """감시창이 죽어도 기존 동작이 그대로여야 한다 — 회귀를 막는다."""
    feeds = [_feed("gn_np", 0.20), _feed("gn_kr", 0.10)]
    assert _run_local_news(feeds, None)["high_alert_feeds"] == 1
    assert _run_local_news(feeds, {})["high_alert_feeds"] == 1


# ── collector 가 순서와 실패를 지키는가 ──────────────────────────────

def test_collector_runs_the_watch_before_local_news():
    """★순서가 뒤집히면 한 시간 늦게 반응하는 층이 된다★

    감시창이 현지어 뉴스의 문턱을 낮추는 입력이므로 먼저 돌아야 한다.
    """
    import inspect
    import collector

    src = inspect.getsource(collector.collect_free_sources)
    assert src.index("collect_disaster_watch") < src.index("fetch_all_local_news")
    assert "watch_windows=open_windows()" in src


def test_collector_says_out_loud_when_the_watch_dies():
    """감시창이 죽으면 뉴스가 평시 문턱으로 돈다 — 조용히 그러면 안 된다."""
    import inspect
    import collector

    src = inspect.getsource(collector.collect_free_sources)
    assert "재난 감시창 실패" in src
    assert "평시 문턱으로 돈다" in src


def test_disaster_watch_is_tracked_in_source_health():
    """이 층이 죽은 걸 모르면 개선이 꺼진 채 도는 상태가 된다."""
    import collector
    assert collector.FREE_SOURCE_HEALTH_KEYS["DisasterWatch"] == "disaster_watch"


# ── 저장 파일이 깨져도 층이 죽지 않는가 ──────────────────────────────

def test_corrupt_state_file_does_not_kill_the_layer():
    dw.STATE_FILE.parent.mkdir(exist_ok=True, parents=True)
    dw.STATE_FILE.write_text("{ 깨진 json", encoding="utf-8")
    assert dw.open_windows() == {}
    # 그리고 다음 주기에 다시 쌓인다
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    assert "NPL" in dw.open_windows(dt.date(2026, 8, 30))


def test_state_survives_a_reload():
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    saved = json.loads(Path(dw.STATE_FILE).read_text(encoding="utf-8"))
    assert len(saved["events"]) == 1
    assert saved["updated_at"]


# ── API 엔드포인트 ───────────────────────────────────────────────────

def test_endpoints_are_public_and_flag_what_they_are_not(monkeypatch):
    """읽기는 공개 GET(설계 원칙)이고, 예측이 아님을 응답 자체가 말해야 한다."""
    import os
    monkeypatch.setenv("EPIWEATHER_SCHEDULER", "off")
    from fastapi.testclient import TestClient
    import main

    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    client = TestClient(main.app)

    body = client.get("/api/disaster-watch").json()
    assert body["is_prediction"] is False
    assert body["windows_calibrated"] is False
    assert "GDACS" in body["data_source"]

    one = client.get("/api/disaster-watch/NPL").json()
    assert one["country_iso3"] == "NPL"


def test_a_country_with_no_disaster_is_an_empty_list_not_a_404(monkeypatch):
    """'재난이 없었다' 도 답이다. 404 로 만들면 '모른다' 와 구분이 안 된다."""
    monkeypatch.setenv("EPIWEATHER_SCHEDULER", "off")
    from fastapi.testclient import TestClient
    import main

    resp = TestClient(main.app).get("/api/disaster-watch/KOR")
    assert resp.status_code == 200
    assert resp.json()["open_windows"] == []


def test_cycle_payload_does_not_repeat_static_text_every_hour():
    """★signals.jsonl 은 매 주기 이 dict 를 통째로 쌓는다★

    규칙표의 근거 문장·키워드 목록은 절대 안 변하는데 매시간 다시 적히면
    하루 1MB 가까이 불어난다. 상세는 `/api/disaster-watch` 가 맡는다.
    """
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    with patch.object(dw, "fetch_gdacs_events", return_value=[]):
        payload = dw.collect_disaster_watch()

    blob = json.dumps(payload, ensure_ascii=False)
    assert "rationale" not in blob, "근거 문장이 매 주기 로그에 다시 적히고 있다"
    assert "keywords" not in blob
    # 그래도 사람이 읽을 최소 정보는 남아야 한다
    win = payload["countries"][0]["open_windows"][0]
    assert {"disease", "disaster_type", "days_since_disaster"} <= set(win)


def test_full_detail_still_available_from_the_report():
    """압축은 로그용이다 — API 는 근거를 그대로 줘야 한다."""
    dw.record_events(dw.parse_gdacs(_rss(_item())), today=dt.date(2026, 8, 25))
    w = dw.disaster_watch_report(dt.date(2026, 8, 30))["countries"][0]["open_windows"][0]
    assert w["rationale"] and w["keywords"]


# ── 2026-08-31 실측으로 잡은 두 구멍 ────────────────────────────────────────
# 캡틴이 "네팔 감시는 어때?" 라고 물어 운영을 들여다보다 나왔다. 감지 자체는
# 멀쩡히 돌고 있었는데, **밖에서 그걸 볼 방법이 없었다.**

def test_log_can_name_which_countries_were_promoted():
    """★핵심★ 승격된 나라 이름이 결과에 있어야 한다.

    예전엔 수집 로그가 "감시창 승격 5개" 라고만 찍었다. 그런데 아침 점검에서
    정말 알아야 하는 건 개수가 아니라 **어디냐** 다 — 네팔이 올라왔는지를
    로그만 보고 알 수 없으면 매번 API 를 따로 뒤져야 한다. GroqWatch 가
    "0개 공항 확인" 한 줄만 남겨 열흘을 헤맸던 것과 같은 모양이다.
    """
    out = _run_local_news([_feed("gn_np", 0.10)], _NEPAL_WINDOW)

    assert out["watch_promoted_countries"] == ["NPL"]


def test_promoted_countries_are_deduplicated_and_sorted():
    """한 나라에 피드가 여럿이어도 이름은 한 번만 — 로그 한 줄에 들어가야 한다."""
    windows = dict(_NEPAL_WINDOW)
    windows["BRA"] = [{"disease": "뎅기·말라리아", "disaster_type": "FL",
                       "days_since_disaster": 20}]
    feeds = [_feed("gn_np", 0.10), _feed("gn_br", 0.10), _feed("gn_kr", 0.10)]

    out = _run_local_news(feeds, windows)

    assert out["watch_promoted_countries"] == ["BRA", "NPL"]   # 정렬·중복 없음


def test_nothing_promoted_reports_an_empty_list_not_a_missing_key():
    """0건도 사실이다 — 키가 아예 없으면 '안 봤다'와 구분이 안 된다."""
    out = _run_local_news([_feed("gn_np", 0.50)], _NEPAL_WINDOW)

    assert out["watch_promoted_countries"] == []


def test_public_api_reflects_the_watch_window():
    """★핵심★ 공개 API 가 감시창을 반영해야 한다.

    실측(2026-08-31): `/api/local-news` 가 fetch_all_local_news() 를 **감시창
    없이** 불렀다. 수집기는 넘기는데 API 는 안 넘겼다. 그래서 네팔 홍수로 창이
    열린 동안 gn_np(0.11)가 수집기에서는 고경보인데 API 로 보면 창이 열렸다는
    표시조차 없는 평범한 피드였다 — 대시보드나 기자가 실제와 다른 그림을 본다.
    """
    import main

    captured = {}

    def fake_fetch(*args, **kwargs):
        captured["windows"] = kwargs.get("watch_windows")
        return {"high_alert": [], "feeds": []}

    with patch.object(ln, "fetch_all_local_news", fake_fetch), \
         patch("algorithms.disaster_watch.open_windows", lambda: _NEPAL_WINDOW):
        main.local_news()

    assert captured["windows"] == _NEPAL_WINDOW, "API 가 감시창을 안 넘기고 있다"


def test_public_api_says_so_when_it_cannot_read_the_windows():
    """감시창을 못 읽으면 조용히 평시 문턱으로 돌지 않고 사유를 밝힌다."""
    import main

    def boom():
        raise OSError("state file gone")

    with patch.object(ln, "fetch_all_local_news",
                      lambda *a, **k: {"high_alert": [], "feeds": []}), \
         patch("algorithms.disaster_watch.open_windows", boom):
        out = main.local_news()

    assert "watch_windows_error" in out, "못 읽었는데 아무 말도 안 하고 있다"
    assert "OSError" in out["watch_windows_error"]

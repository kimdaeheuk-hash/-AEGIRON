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
import urllib.parse
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

def _feed(slug, ratio, item_count=100):
    """기사 수 기본값이 100인 이유: 표본이 MIN_ITEMS_FOR_ALERT(20) 미만이면
    새 가드가 판정 자체를 안 한다. 예전 픽스처는 10건이라 전부 걸렸다."""
    return {"slug": slug, "lang": "x", "region": "y", "status": "ok",
            "item_count": item_count, "keyword_hits": int(ratio * item_count),
            "hit_ratio": ratio, "_all_titles": ["t"]}


def _run_local_news(feeds, windows):
    with patch.object(ln, "LOCAL_FEEDS", [(f["slug"], "x", "y", "u", []) for f in feeds]):
        with patch.object(ln, "fetch_local_feed",
                          side_effect=lambda slug, *a: next(
                              dict(f) for f in feeds if f["slug"] == slug)):
            return ln.fetch_all_local_news(watch_windows=windows)


# 실제 open_windows() 가 주는 모양 그대로 — keywords 가 있어야 창 안/밖을 가른다.
_NEPAL_WINDOW = {"NPL": [{"disease": "콜레라·장티푸스", "disaster_type": "FL",
                          "days_since_disaster": 6,
                          "keywords": ["cholera", "typhoid", "콜레라", "장티푸스", "설사"]}]}


def test_watch_window_promotes_a_feed_normally_ignored():
    """★이 층의 존재 이유★ 평시라면 넘겼을 보도를 감시창이 붙잡는다."""
    # gn_np 는 국가 한정 피드(COUNTRY_TERMS)라 문턱이 0.20/0.11 이다.
    # 0.15 는 평시(0.20)엔 못 미치고 감시창(0.11)은 넘는 값 — 이 층의 요점.
    feeds = [_feed("gn_np", 0.15), _feed("gn_kr", 0.10)]

    without = _run_local_news(feeds, None)
    assert without["high_alert_feeds"] == 0, "감시창 없이는 둘 다 문턱 아래다"

    with_window = _run_local_news(feeds, _NEPAL_WINDOW)
    promoted = [f["slug"] for f in with_window["high_alert"]]
    assert promoted == ["gn_np"], "감시창이 열린 나라만 올라와야 한다"
    assert with_window["watch_promoted_feeds"] == 1


def test_the_lowered_threshold_is_never_silent():
    """문턱이 조용히 달라지면 고경보 수를 아무도 해석할 수 없다."""
    out = _run_local_news([_feed("gn_np", 0.15)], _NEPAL_WINDOW)
    feed = out["high_alert"][0]
    assert feed["alert_basis"] == "disaster_watch_window"
    assert feed["watch_window"]["diseases"] == ["콜레라·장티푸스"]
    assert feed["watch_window"]["disasters"] == ["FL"]
    assert feed["watch_window"]["min_days_since_disaster"] == 6
    assert out["alert_threshold"] == ln.ALERT_THRESHOLD
    assert out["scoped_alert_threshold"] == ln.SCOPED_ALERT_THRESHOLD
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
    out = _run_local_news([_feed("gn_np", 0.15)], _NEPAL_WINDOW)

    assert out["watch_promoted_countries"] == ["NPL"]


def test_promoted_countries_are_deduplicated_and_sorted():
    """한 나라에 피드가 여럿이어도 이름은 한 번만 — 로그 한 줄에 들어가야 한다."""
    windows = dict(_NEPAL_WINDOW)
    windows["BRA"] = [{"disease": "뎅기·말라리아", "disaster_type": "FL",
                       "days_since_disaster": 20}]
    # gn_np 는 국가 한정(문턱 0.11), gn_br·gn_kr 은 아님(문턱 0.08)
    feeds = [_feed("gn_np", 0.15), _feed("gn_br", 0.10), _feed("gn_kr", 0.10)]

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


# ── 되돌림 피드 (2026-08-31) ────────────────────────────────────────────────
# 실측: 179개 피드 중 102개가 서로 완전히 같은 기사를 받고 있었다. 구글 뉴스가
# 자체 뉴스판이 없는 나라에 언어 기본판을 되돌려 주기 때문이다. 잠비아·미국·
# 사모아가 글자 하나까지 같은 기사 100건을 받았다.

def test_country_terms_cover_the_fallback_feeds():
    """되돌림 피드에는 나라 이름이 붙어 있어야 한다 — 안 붙으면 또 겹친다."""
    slugs = {f[0] for f in ln.LOCAL_FEEDS}

    assert len(ln.COUNTRY_TERMS) == 102
    assert set(ln.COUNTRY_TERMS) <= slugs, "없는 피드에 이름을 붙여놨다"
    # 실측에서 되돌림이 확인된 대표들
    for slug in ("gn_zm", "gn_us", "gn_ws", "gn_so", "gn_ss", "gn_ml", "gn_ma"):
        assert slug in ln.COUNTRY_TERMS, f"{slug} 이 되돌림 목록에서 빠졌다"


def test_scoped_feeds_actually_carry_the_country_in_the_query():
    """URL 질의에 나라 이름이 실제로 들어갔는지 — 표만 있고 안 쓰면 소용없다."""
    url = next(f[3] for f in ln.LOCAL_FEEDS if f[0] == "gn_zm")
    plain = next(f[3] for f in ln.LOCAL_FEEDS if f[0] == "gn_cd")

    assert "Zambia" in urllib.parse.unquote(url)
    assert "Zambia" not in urllib.parse.unquote(plain), "한정 대상이 아닌 피드가 바뀌었다"


def test_duplicate_feeds_are_never_reported_as_that_countrys_alert():
    """★★핵심★★ 남의 기사를 그 나라 이름으로 경보하지 않는다.

    되돌림 묶음이 문턱을 넘으면 36개국이 한꺼번에 경보가 뜬다. 그건 그 나라
    신호가 아니라 언어 기본판이다 — **없는 발병을 있다고 말하는 것**이 된다.
    """
    same = ["같은 기사 A", "같은 기사 B", "같은 기사 C", "같은 기사 D"]
    feeds = [_feed("gn_zm", 0.50), _feed("gn_us", 0.50), _feed("gn_cd", 0.50)]
    feeds[0]["_all_titles"] = ["hdr", "hdr2"] + same
    feeds[1]["_all_titles"] = ["hdr", "hdr2"] + same          # 잠비아와 동일
    feeds[2]["_all_titles"] = ["hdr", "hdr2", "다른 기사", "또 다른", "세번째"]

    out = _run_local_news(feeds, None)
    alerted = {f["slug"] for f in out["high_alert"]}

    assert "gn_zm" not in alerted and "gn_us" not in alerted, "겹친 피드가 경보로 나갔다"
    assert "gn_cd" in alerted, "고유 피드까지 막으면 안 된다"
    assert out["duplicated_feeds"] == 2
    assert ["gn_us", "gn_zm"] in out["duplicate_feed_groups"]


def test_duplicate_detection_runs_every_cycle_not_from_a_fixed_list():
    """되돌림은 요청마다 흔들린다 — 목록을 박아두면 놓친다.

    실측(2026-08-31): 네팔이 한 번은 고유였다가 다음 번엔 아프가니스탄·
    스리랑카와 같은 기사를 받았다. 그래서 매 수집마다 제목으로 판정한다.
    """
    same = ["A", "B", "C", "D"]
    # COUNTRY_TERMS 에 없는(=되돌림 목록 밖) 피드끼리 겹쳐도 잡혀야 한다
    feeds = [_feed("gn_cd", 0.50), _feed("gn_kr", 0.50)]
    for f in feeds:
        f["_all_titles"] = ["hdr", "hdr2"] + same

    out = _run_local_news(feeds, None)

    assert out["duplicated_feeds"] == 2, "고정 목록이 아니라 그때그때 봐야 한다"
    assert out["high_alert_feeds"] == 0


def test_too_few_items_is_not_treated_as_a_signal():
    """★핵심★ 표본 부족은 '모른다'다 — 경보도 아니고 정상도 아니다.

    국가 한정을 걸면 기사 5건에 키워드 6종이 잡혀 ratio 1.2 가 나오기도 한다.
    그걸 신호로 읽으면 조용한 나라마다 가짜 경보가 뜬다.
    """
    out = _run_local_news([_feed("gn_zm", 1.2, item_count=5)], None)

    assert out["high_alert_feeds"] == 0, "기사 5건짜리가 경보로 나갔다"
    assert out["too_few_items_feeds"] == ["gn_zm"], "판정 못 한 사실을 안 남겼다"
    assert out["min_items_for_alert"] == 20


def test_scoped_feeds_use_a_higher_threshold_than_plain_ones():
    """국가 한정 피드는 분모가 작아 비율이 구조적으로 높다 — 문턱이 달라야 한다.

    실측: 나라 이름을 넣자 102개 중 73개(72%)가 0.15 를 넘었다. 0.20 은 표본
    20건 이상 81개에서 경보율 28% 로, 현재 운영점(179개 중 약 50개)과 같다.
    """
    ratio = 0.17          # 평시 0.15 위, 국가한정 0.20 아래
    out = _run_local_news([_feed("gn_zm", ratio), _feed("gn_cd", ratio)], None)
    alerted = {f["slug"] for f in out["high_alert"]}

    assert "gn_cd" in alerted, "한정 안 된 피드는 0.15 문턱 그대로여야 한다"
    assert "gn_zm" not in alerted, "한정된 피드에 옛 문턱을 쓰고 있다"
    assert ln.SCOPED_ALERT_THRESHOLD > ln.ALERT_THRESHOLD


def test_the_feed_count_no_longer_pretends_to_be_country_count():
    """"179개 피드" 가 179개국을 본다는 뜻이 아니라는 걸 응답이 말해야 한다."""
    out = _run_local_news([_feed("gn_zm", 0.5), _feed("gn_cd", 0.5)], None)

    for key in ("duplicate_feed_groups", "duplicated_feeds", "distinct_feed_sets",
                "country_scoped_feeds", "too_few_items_feeds"):
        assert key in out, f"{key} 를 안 내보내고 있다"
    assert out["country_scoped_feeds"] == 102


# ── 창 밖 신호 (2026-09-01) ─────────────────────────────────────────────────
# 실측: 네팔에 홍수 감시창(콜레라·렙토스피라)이 6일째 열려 있는데, 정작 그 나라
# 에서 번지던 것은 **조류독감**이었다 — 보건부 전국 경보·중앙동물원 폐쇄·여러
# 지역 살처분. 문턱은 나라 전체에 걸리므로 신호는 잡혔지만 보고서에는
# "감시창 승격 — 렙토스피라증·콜레라" 라고 찍혔다. 잡은 것과 이름표가 달랐다.

def _feed_with_titles(slug, ratio, titles):
    f = _feed(slug, ratio)
    f["_all_titles"] = ["hdr", "hdr2"] + titles
    return f


def test_off_window_signal_is_not_labelled_as_the_expected_disease():
    """★★핵심★★ 창 안 질병이 안 보이면 그렇게 말한다.

    네팔 조류독감을 "콜레라·장티푸스 감시창 승격" 으로 보고하면, 읽는 사람은
    콜레라가 오고 있다고 이해한다. 대응이 완전히 달라진다.
    """
    feeds = [_feed_with_titles("gn_np", 0.15, [
        "Health Ministry issues nationwide alert over spreading bird flu outbreak",
        "Central Zoo closes indefinitely after bird flu outbreak",
    ])]

    out = _run_local_news(feeds, _NEPAL_WINDOW)
    feed = out["high_alert"][0]

    assert feed["watch_window"]["off_window"] is True
    assert feed["watch_window"]["diseases_seen"] == []
    assert out["off_window_signals"][0]["country_iso3"] == "NPL"
    assert out["off_window_signals"][0]["expected"] == ["콜레라·장티푸스"]


def test_in_window_signal_is_reported_as_such():
    """예상한 병이 실제로 오면 그것도 분명히 말한다 — 감시창이 맞아가는 중이다."""
    feeds = [_feed_with_titles("gn_np", 0.15, [
        "Cholera outbreak reported in flood-hit district",
        "설사 환자 급증",
    ])]

    out = _run_local_news(feeds, _NEPAL_WINDOW)
    feed = out["high_alert"][0]

    assert feed["watch_window"]["off_window"] is False
    assert feed["watch_window"]["diseases_seen"] == ["콜레라·장티푸스"]
    assert out["off_window_signals"] == []


def test_off_window_only_counts_feeds_that_actually_alerted():
    """조용한 나라를 창 밖 신호로 만들지 않는다 — 고경보가 난 것만 센다."""
    feeds = [_feed_with_titles("gn_np", 0.01, ["아무 관련 없는 기사"])]

    out = _run_local_news(feeds, _NEPAL_WINDOW)

    assert out["high_alert_feeds"] == 0
    assert out["off_window_signals"] == []


def test_countries_without_a_window_are_never_off_window():
    """창이 없는 나라는 창 밖이라는 개념 자체가 없다."""
    feeds = [_feed_with_titles("gn_kr", 0.50, ["bird flu outbreak"])]

    out = _run_local_news(feeds, _NEPAL_WINDOW)

    assert out["high_alert_feeds"] == 1
    assert "watch_window" not in out["high_alert"][0]
    assert out["off_window_signals"] == []


def test_unjudgeable_window_is_not_called_off_window():
    """★핵심★ 대조할 수 없는 창을 "다른 병이 왔다"고 하지 않는다.

    키워드가 없는 창은 창 안인지 밖인지 **알 수 없다.** 그걸 창 밖으로 단정하면
    없는 경보를 만들어낸다 — 이 저장소가 known.ts·source_health 에서 계속
    고쳐온 "모른다를 단정으로 바꾸는" 바로 그 병이다.
    """
    no_kw = {"NPL": [{"disease": "콜레라·장티푸스", "disaster_type": "FL",
                      "days_since_disaster": 6}]}          # keywords 없음
    feeds = [_feed_with_titles("gn_np", 0.15, ["bird flu outbreak"])]

    out = _run_local_news(feeds, no_kw)
    win = out["high_alert"][0]["watch_window"]

    assert win["window_checkable"] is False, "대조 불가를 표시하지 않고 있다"
    assert win["off_window"] is False, "모르는 것을 창 밖으로 단정했다"
    assert out["off_window_signals"] == []

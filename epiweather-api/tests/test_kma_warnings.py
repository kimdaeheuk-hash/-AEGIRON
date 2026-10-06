"""기상청 특보 → 한국 재난 감시창 (2026-10-06).

## 이 파일이 막아야 하는 것
1. **키가 새는 것.** `requests` 예외 문구에는 `authKey=…` 쿼리가 통째로 들어 있다 — 로그와
   `signals.jsonl` 로 가면 키가 새므로 어떤 경로로도 값이 나가면 안 된다.
2. **해제·주의보를 발효로 읽는 것.** 없는 창을 여는 쪽이 반대보다 나쁘다.
3. **한쪽 입력의 죽음이 다른 쪽을 죽이는 것.** GDACS 와 기상청은 따로 실패한다.
4. **같은 호우가 창을 여럿 여는 것**(구역·날짜별 중복, GDACS 와의 이중 계수).
5. **라이브 미검증을 숨기는 것.** 형식이 예상 밖이면 가짜 사건 대신 사유를 들고 올라온다.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest
import requests

from algorithms import disaster_watch as dw
from algorithms import kma_warnings as kma

FAKE_KEY = "FAKEKEY_abc-123_XYZ"


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(dw, "STATE_FILE", tmp_path / "disaster_watch.json")
    monkeypatch.delenv(kma.KEY_ENV, raising=False)


HEADER = "# REG_UP REG_UP_KO REG_ID REG_KO TM_FC TM_EF WRN LVL CMD"


def _row(wrn="R", lvl="2", cmd="1", ef="202610060900", fc="202610060830", reg="L1010100"):
    return f"11B00000 서울 {reg} 서울 {fc} {ef} {wrn} {lvl} {cmd}"


def _body(*rows, header=HEADER):
    return "\n".join(["#START7777", header, *rows, "#7777END"])


# ── 파서 ────────────────────────────────────────────────────────────

def test_heavy_rain_warning_becomes_one_flood_event():
    out = kma.parse_warnings(_body(_row(reg="A"), _row(reg="B"), _row(reg="C")))
    assert out["rows"] == 3
    assert [(e["type"], e["date"], e["regions"]) for e in out["events"]] == [("FL", "2026-10-06", 3)]
    ev = out["events"][0]
    assert ev["iso3"] == "KOR" and ev["source"] == "kma" and ev["alert"] == "경보"


def test_typhoon_maps_to_tropical_cyclone():
    out = kma.parse_warnings(_body(_row(wrn="T")))
    assert out["events"][0]["type"] == "TC"


def test_advisory_does_not_open_a_window():
    out = kma.parse_warnings(_body(_row(lvl="1")))
    assert out["events"] == [] and out["skipped"] == {"주의보": 1}


@pytest.mark.parametrize("cmd", ["3", "4", "7", "해제"])
def test_cancelled_warning_does_not_open_a_window(cmd):
    out = kma.parse_warnings(_body(_row(cmd=cmd)))
    assert out["events"] == [] and out["skipped"] == {"해제": 1}


def test_unknown_codes_are_skipped_and_counted_not_guessed():
    out = kma.parse_warnings(_body(_row(cmd="9"), _row(lvl="7"), _row(wrn="H"), _row(wrn="R")))
    assert [e["type"] for e in out["events"]] == ["FL"]
    assert out["skipped"] == {"모르는 명령 코드": 1, "모르는 수준 코드": 1, "매핑 없는 특보 종류": 1}


def test_heat_wave_and_cold_wave_are_never_mapped():
    """질병 규칙표에 대응이 없는 특보는 창을 열지 않는다 — 없는 규칙을 지어내지 않는다."""
    out = kma.parse_warnings(_body(_row(wrn="H"), _row(wrn="C"), _row(wrn="S")))
    assert out["events"] == []


def test_korean_labels_are_understood_too():
    out = kma.parse_warnings(_body(_row(wrn="호우", lvl="경보", cmd="발표")))
    assert out["events"][0]["type"] == "FL"


def test_effective_date_is_preferred_over_issue_date():
    out = kma.parse_warnings(_body(_row(ef="202610070300", fc="202610062100")))
    assert out["events"][0]["date"] == "2026-10-07"


def test_comma_separated_response_is_understood():
    body = "#START7777\n# REG_ID,TM_FC,TM_EF,WRN,LVL,CMD\nL1,202610060830,202610060900,R,2,1\n#7777END"
    assert kma.parse_warnings(body)["events"][0]["type"] == "FL"


def test_no_active_warnings_is_an_empty_list_not_an_error():
    out = kma.parse_warnings(_body())
    assert out["events"] == [] and out["rows"] == 0


def test_unrecognized_format_raises_with_evidence_instead_of_inventing():
    with pytest.raises(kma.KmaError, match="열 이름 줄"):
        kma.parse_warnings("<html>점검 중</html>")


def test_all_rows_malformed_raises_instead_of_reporting_no_warnings():
    """'특보가 없다'와 '못 읽었다'는 다르다 — 한 행도 못 읽으면 조용히 빈 결과를 내지 않는다."""
    with pytest.raises(kma.KmaError, match="열 수"):
        kma.parse_warnings(_body("한 줄짜리 이상한 행"))


def test_some_malformed_rows_are_skipped_and_counted():
    out = kma.parse_warnings(_body(_row(), "이상한 행"))
    assert len(out["events"]) == 1 and out["skipped"] == {"열 수 불일치": 1}


# ── 키가 새지 않는다 ────────────────────────────────────────────────

def test_scrub_removes_the_key_value_and_the_query_parameter():
    msg = f"HTTPSConnectionPool: url: /x?fe=f&authKey={FAKE_KEY}&disp=0 failed ({FAKE_KEY})"
    out = kma.scrub(msg, FAKE_KEY)
    assert FAKE_KEY not in out and "authKey=***" in out


def test_fetch_failure_text_never_contains_the_key(monkeypatch):
    def boom(url, params=None, **kw):
        raise requests.ConnectionError(f"Max retries exceeded with url: /x?authKey={params['authKey']}")
    monkeypatch.setattr(kma.requests, "get", boom)
    with pytest.raises(kma.KmaError) as ei:
        kma.fetch_warnings(FAKE_KEY)
    assert FAKE_KEY not in str(ei.value) and ei.value.__cause__ is None and ei.value.__suppress_context__ is True


def test_http_error_text_never_contains_the_key(monkeypatch):
    class Resp:
        def raise_for_status(self):
            raise requests.HTTPError(f"403 for url: https://x/y?authKey={FAKE_KEY}")
    monkeypatch.setattr(kma.requests, "get", lambda *a, **k: Resp())
    with pytest.raises(kma.KmaError) as ei:
        kma.fetch_warnings(FAKE_KEY)
    assert FAKE_KEY not in str(ei.value)


def test_collect_result_carries_no_key_even_when_the_error_text_does(monkeypatch):
    monkeypatch.setenv(kma.KEY_ENV, FAKE_KEY)

    def boom(key=None):
        raise RuntimeError(f"upstream said authKey={FAKE_KEY} is invalid")
    monkeypatch.setattr(kma, "fetch_warnings", boom)
    out = dw.collect_kma_warnings()
    assert out["status"] == "failed" and FAKE_KEY not in json.dumps(out, ensure_ascii=False)


def test_key_is_read_only_from_the_environment_variable():
    import inspect
    src = inspect.getsource(kma)
    assert 'KEY_ENV = "KMA_API_KEY"' in src and "os.environ.get(KEY_ENV)" in src


# ── 수집: 키 없음·실패·성공이 서로 다르다 ───────────────────────────

def test_without_a_key_nothing_is_called_and_status_says_so(monkeypatch):
    monkeypatch.setattr(kma, "fetch_warnings", lambda key=None: pytest.fail("키 없이 호출했다"))
    assert dw.collect_kma_warnings() == {"status": "skipped_no_key"}


def test_success_stores_the_event_and_reports_counts(monkeypatch):
    monkeypatch.setenv(kma.KEY_ENV, FAKE_KEY)
    monkeypatch.setattr(kma, "fetch_warnings", lambda key=None: kma.parse_warnings(_body(_row(), _row(lvl="1"))))
    out = dw.collect_kma_warnings()
    assert out["status"] == "ok" and out["new"] == 1 and out["skipped"] == {"주의보": 1}
    assert len(dw._load_state()["events"]) == 1


def test_gdacs_failure_does_not_stop_kma_but_still_raises(monkeypatch):
    monkeypatch.setenv(kma.KEY_ENV, FAKE_KEY)
    monkeypatch.setattr(kma, "fetch_warnings", lambda key=None: kma.parse_warnings(_body(_row())))
    monkeypatch.setattr(dw, "fetch_gdacs_events", lambda: (_ for _ in ()).throw(dw.DisasterWatchError("GDACS 죽음")))
    with pytest.raises(dw.DisasterWatchError):
        dw.collect_disaster_watch()
    assert len(dw._load_state()["events"]) == 1                     # 기상청 사건은 먼저 저장됐다


def test_kma_failure_does_not_stop_gdacs(monkeypatch):
    monkeypatch.setenv(kma.KEY_ENV, FAKE_KEY)

    def boom(key=None):
        raise kma.KmaError("기상청 죽음")
    monkeypatch.setattr(kma, "fetch_warnings", boom)
    monkeypatch.setattr(dw, "fetch_gdacs_events", lambda: [
        {"key": "FL-1-NPL", "event_id": "1", "type": "FL", "alert": "red", "iso3": "NPL",
         "country": "Nepal", "date": (dt.date.today() - dt.timedelta(days=5)).isoformat(), "title": "t"}])
    out = dw.collect_disaster_watch()
    assert out["kma"]["status"] == "failed" and out["new"] == 1
    assert out["stored"] == 1 and out["watched_country_count"] == 1


def test_collect_wires_the_kma_step():
    import ast
    import inspect
    calls = {n.func.id for n in ast.walk(ast.parse(inspect.getsource(dw.collect_disaster_watch)))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "collect_kma_warnings" in calls


# ── 저장: 에피소드 묶기 ─────────────────────────────────────────────

def _ev(date, regions=1, etype="FL"):
    return {"type": etype, "date": date, "iso3": "KOR", "country": "대한민국", "alert": "경보",
            "source": "kma", "regions": regions, "title": "기상청 호우경보"}


def test_consecutive_days_are_one_episode_anchored_on_the_first_day():
    dw.record_kma_events([_ev("2026-10-01", 3)])
    dw.record_kma_events([_ev("2026-10-03", 9)])
    ev = list(dw._load_state()["events"].values())
    assert len(ev) == 1 and ev[0]["date"] == "2026-10-01"
    assert ev[0]["regions"] == 9 and ev[0]["last_warned"] == "2026-10-03"


def test_an_earlier_day_seen_later_moves_the_anchor_back():
    dw.record_kma_events([_ev("2026-10-03")])
    dw.record_kma_events([_ev("2026-10-01")])
    assert [e["date"] for e in dw._load_state()["events"].values()] == ["2026-10-01"]


def test_a_gap_longer_than_the_limit_is_a_new_episode():
    dw.record_kma_events([_ev("2026-10-01")])
    out = dw.record_kma_events([_ev("2026-10-01") | {"date": "2026-10-09"}])
    assert out["new"] == 1 and out["stored"] == 2


def test_different_kinds_never_merge():
    dw.record_kma_events([_ev("2026-10-01", etype="FL"), _ev("2026-10-01", etype="TC")])
    assert len(dw._load_state()["events"]) == 2


def test_repeating_the_same_cycle_adds_nothing():
    dw.record_kma_events([_ev("2026-10-01")])
    assert dw.record_kma_events([_ev("2026-10-01")])["new"] == 0


# ── 감시창 ──────────────────────────────────────────────────────────

def test_korea_window_opens_with_the_existing_flood_rules():
    today = dt.date(2026, 10, 10)
    dw.record_kma_events([_ev("2026-10-06")], today=today)
    wins = dw.open_windows(today)["KOR"]
    assert {w["disaster_type"] for w in wins} == {"FL"} and {w["source"] for w in wins} == {"kma"}
    assert {w["disease"] for w in wins} == {r[0] for r in dw.WATCH_RULES["FL"] if r[2] <= 4 <= r[3]}


def test_gdacs_and_kma_for_the_same_flood_are_counted_once():
    today = dt.date(2026, 10, 10)
    dw.record_events([{"key": "FL-9-KOR", "event_id": "9", "type": "FL", "alert": "orange",
                       "iso3": "KOR", "country": "South Korea", "date": "2026-10-05", "title": "g"}], today=today)
    dw.record_kma_events([_ev("2026-10-06")], today=today)
    wins = dw.open_windows(today)["KOR"]
    assert {w["source"] for w in wins} == {"gdacs"}


def test_gdacs_event_far_apart_in_time_does_not_hide_the_kma_window():
    today = dt.date(2026, 10, 20)
    dw.record_events([{"key": "FL-9-KOR", "event_id": "9", "type": "FL", "alert": "orange",
                       "iso3": "KOR", "country": "South Korea", "date": "2026-09-20", "title": "g"}], today=today)
    dw.record_kma_events([_ev("2026-10-18")], today=today)
    assert "kma" in {w["source"] for w in dw.open_windows(today)["KOR"]}


def test_existing_gdacs_windows_carry_a_source_field():
    today = dt.date.today()
    dw.record_events([{"key": "FL-1-NPL", "event_id": "1", "type": "FL", "alert": "red", "iso3": "NPL",
                       "country": "Nepal", "date": (today - dt.timedelta(days=5)).isoformat(), "title": "t"}], today=today)
    assert {w["source"] for w in dw.open_windows(today)["NPL"]} == {"gdacs"}


def test_data_source_names_kma_only_when_kma_events_exist():
    assert "기상청" not in dw.disaster_watch_report()["data_source"]
    dw.record_kma_events([_ev(dt.date.today().isoformat())])
    assert "기상청" in dw.disaster_watch_report()["data_source"]


def test_kma_alone_does_not_claim_calibration():
    dw.record_kma_events([_ev(dt.date.today().isoformat())])
    rep = dw.disaster_watch_report()
    assert rep["windows_calibrated"] is False and rep["is_prediction"] is False


# ── 로그 줄 ─────────────────────────────────────────────────────────

def test_log_line_tells_the_three_states_apart():
    import collector
    assert "꺼져 있다(실패 아님)" in collector._kma_line({"status": "skipped_no_key"})
    assert "경보 사건 1건(신규 1)" in collector._kma_line(
        {"status": "ok", "rows": 5, "events": 1, "new": 1, "skipped": {"주의보": 4}})
    assert "제외 주의보 4" in collector._kma_line(
        {"status": "ok", "rows": 5, "events": 1, "new": 1, "skipped": {"주의보": 4}})
    assert collector._kma_line({"status": "failed", "error": "x"}).startswith("❌")
    assert collector._kma_line(None) == "기상청 특보: 상태 모름"

"""소킹 10-12·10-14·10-16·10-17 일지가 올린 수집·파서 쪽 결함 넷 (2026-10-17, 캡틴 지시 "새항목 전부 실행해").

E. KDCA 덜 찬 새 주 — 10-12 월 20:03 UTC `kdca_weekly_total 보고 급감 65.0점(최신값 74.0, 평균 214.48의 0.35배)`
   이 medium 으로 약 6시간 떠 있다가 새벽에 저절로 사라졌다(`week_is_reported` 는 '전 질병이 0' 인 주만 막았다).
F. WHO DON 제목 `질병- 국가`(하이픈 앞 공백 없음) — 21:00 슬롯 샘플에서 못 읽은 제목 18건의 주된 모양.
G. Wikipedia_Ebola — 정오(UTC) 뒤에도 24주기 연속 404 인데 로그가 매시간 `정상 지연` 이라고 적었다.
H. CDC NWSS 수집 — 평균이 한 표본에 지배되는지 읽을 수 있게 최댓값을 함께 남긴다. `site_count` 는 사이트 수가
   아니라 표본 행 수다(키 이름은 기록 호환 때문에 그대로).
"""
from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path

import pytest

import collector
from algorithms import who_don_declarations as don
from algorithms.kdca_anomaly import (PARTIAL_WEEK_GRACE_DAYS, PARTIAL_WEEK_RATIO, _week_start,
                                     latest_week_is_partial, notable_latest_total, week_is_reported)
from algorithms.signal_metrics import _kdca_latest_total

COLLECTOR_PY = Path(collector.__file__)

# ── 관측 재현용 데이터: 위험군 두 질병, 직전 세 주 합계 ≈ 214, 새 주 합계 74 ─────────────────────
W39, W40, W41, W42 = "2026년 39주", "2026년 40주", "2026년 41주", "2026년 42주"


def _weekly(latest_total):
    """홍역 + 수두(둘 다 KDCA_NOTABLE 위험군). 직전 세 주는 각각 합계 ≈ 214(홍역 ~14 + 수두 ~200)."""
    return {
        "홍역": {W39: 14, W40: 13, W41: 15, W42: latest_total // 5},
        "수두": {W39: 200, W40: 201, W41: 199, W42: latest_total - latest_total // 5},
    }


MON_42 = dt.date(2026, 10, 12)       # 2026년 42주의 월요일 — 관측이 시작된 날


# ═══ E. KDCA 덜 찬 새 주 ══════════════════════════════════════════════════════════

def test_week_label_parses_to_the_iso_monday_or_nothing():
    assert _week_start(W42) == MON_42
    assert _week_start("2026년 7주") == dt.date(2026, 2, 9)
    assert _week_start("어딘가") is None and _week_start(None) is None
    assert _week_start("2026년 99주") is None              # 달력에 없는 주 — 추측하지 않는다


def test_the_1012_observation_is_now_undetermined_not_a_drop():
    """월요일 저녁, 새 주 합계 74 vs 직전 중앙값 214 (0.35배) — 옛 동작은 낮은 값(→ 급감 65점)이었다."""
    data = _weekly(74)
    assert week_is_reported(data, W42) is True                     # 0 이 아니라서 옛 가드는 통과시켰다
    assert latest_week_is_partial(data, MON_42) is True
    assert notable_latest_total(data, as_of=MON_42) is None        # '아직 모름' — 낮은 값이 아니다
    assert notable_latest_total(data, as_of=MON_42 + dt.timedelta(days=1)) is None   # 화요일 새벽(알람이 풀린 시각)도 같은 판정


def test_without_the_date_the_old_behaviour_is_kept():
    """나이를 모르면 보류하지 않는다 — 기록에 시각이 없는 옛 레코드가 소급해서 바뀌지 않는다."""
    data = _weekly(74)
    assert notable_latest_total(data) == 74.0
    assert latest_week_is_partial(data, None) is False


def test_after_the_grace_days_a_low_week_is_a_real_drop_again():
    """사흘이 지나도 낮으면 '덜 찬 주'가 아니라 보고 급감으로 읽힌다 — 진짜 붕괴를 영원히 가리지 않는다."""
    data = _weekly(74)
    late = MON_42 + dt.timedelta(days=PARTIAL_WEEK_GRACE_DAYS)
    assert latest_week_is_partial(data, late) is False
    assert notable_latest_total(data, as_of=late) == 74.0


def test_a_filled_week_is_judged_even_on_monday():
    """직전 중앙값의 60% 이상이면 월요일이라도 판정한다 — 월요일 판정을 통째로 막지 않는다."""
    data = _weekly(214)                                            # 비율 1.0
    assert latest_week_is_partial(data, MON_42) is False
    data = _weekly(int(214 * PARTIAL_WEEK_RATIO) + 1)               # 문턱 바로 위
    assert latest_week_is_partial(data, MON_42) is False
    data = _weekly(int(214 * PARTIAL_WEEK_RATIO) - 1)               # 문턱 바로 아래
    assert latest_week_is_partial(data, MON_42) is True


def test_not_enough_history_means_no_judgement_about_partial():
    """직전 주가 둘 미만이면 '평소'를 못 정한다 — 보류하지 않는다(모르는 것을 부분으로 단정하지 않는다)."""
    two_weeks = {"홍역": {W41: 15, W42: 1}}
    assert latest_week_is_partial(two_weeks, MON_42) is False


def test_the_0921_all_zero_case_is_still_undetermined():
    """먼저 고친 사고(새 주 집계 0)는 그대로 막힌다 — 이번 수리가 그 가드를 대체하지 않는다."""
    data = _weekly(0)
    data["홍역"][W42] = 0
    data["수두"][W42] = 0
    assert notable_latest_total(data, as_of=MON_42 + dt.timedelta(days=10)) is None


def test_the_metric_extractor_uses_the_record_time_not_the_clock():
    """옛 기록을 지금 시각으로 재면 틀린다 — 기록의 timestamp 로 새 주 나이를 잰다."""
    data = _weekly(74)
    assert _kdca_latest_total({"kdca_weekly": data, "timestamp": "2026-10-12T20:03:00"}) is None
    assert _kdca_latest_total({"kdca_weekly": data, "timestamp": "2026-10-16T12:00:00"}) == 74.0
    assert _kdca_latest_total({"kdca_weekly": data}) == 74.0                         # 시각 없음 → 옛 동작
    assert _kdca_latest_total({"kdca_weekly": data, "timestamp": "깨진값"}) == 74.0     # 못 읽으면 보지 않는다


# ═══ F. WHO DON 제목 하이픈 ═══════════════════════════════════════════════════════

@pytest.mark.parametrize("title,disease,place,iso", [
    ("Marburg virus disease- Ethiopia", "Marburg virus disease", "Ethiopia", "ETH"),
    ("Avian Influenza A(H5N5)- United States of America", "Avian Influenza A(H5N5)",
     "United States of America", "USA"),
    ("Middle East respiratory syndrome coronavirus- Kingdom of Saudi Arabia",
     "Middle East respiratory syndrome coronavirus", "Kingdom of Saudi Arabia", "SAU"),
])
def test_the_no_space_before_hyphen_titles_from_the_1010_sample_are_read(title, disease, place, iso):
    assert don.split_title(title) == (disease, place)
    out = don.parse_items({"value": [{"Title": title, "PublicationDate": "2026-10-01", "DonId": "x"}]},
                          today=dt.date(2026, 10, 10))
    assert [(d["disease"], d["iso3"]) for d in out["declarations"]] == [(disease, iso)]


def test_the_old_spaced_separator_still_works():
    assert don.split_title("Cholera - Angola") == ("Cholera", "Angola")
    assert don.split_title("Cholera – Angola") == ("Cholera", "Angola")
    assert don.split_title("Cholera — Angola") == ("Cholera", "Angola")


@pytest.mark.parametrize("title", [
    "Hantavirus outbreak linked to cruise ship travel, Multi-locations",   # 하이픈 뒤 공백 없음 = 구분자가 아니다
    "MERS-CoV",                                                              # 병명 안의 하이픈
    "Mpox",
])
def test_a_hyphen_without_a_following_space_is_not_a_separator(title):
    assert don.split_title(title) is None


def test_non_country_places_are_still_skipped_not_guessed():
    """구분자를 읽는 것과 나라로 읽는 것은 다르다 — `Global`·`Multi-locations` 는 여전히 건너뛴다."""
    out = don.parse_items({"value": [
        {"Title": "Yellow fever - Global", "PublicationDate": "2026-10-01", "DonId": "a"},
        {"Title": "Hantavirus outbreak linked to cruise ship travel, Multi-locations",
         "PublicationDate": "2026-10-01", "DonId": "b"},
    ]}, today=dt.date(2026, 10, 10))
    assert out["declarations"] == [] and out["skipped"].get("국가 못 읽음") == 2


# ═══ G. Wikipedia 404 ═══════════════════════════════════════════════════════════

@pytest.mark.parametrize("hour,lag", [(0, True), (3, True), (11, True), (12, False), (13, False), (23, False)])
def test_a_404_is_a_lag_only_before_noon_utc(hour, lag):
    assert collector.wiki_404_is_lag(hour) is lag


class _Resp:
    def __init__(self, status=200, headers=None):
        self.status_code = status
        self.headers = headers or {}


def test_article_status_reports_a_move_without_following_it(monkeypatch):
    seen = {}

    def fake_get(url, **kw):
        seen.update(kw)
        return _Resp(301, {"Location": "https://en.wikipedia.org/wiki/New_title"})
    monkeypatch.setattr(collector.requests, "get", fake_get)
    out = collector.wiki_article_status("Old_title")
    assert "HTTP 301" in out and "New_title" in out
    assert seen["allow_redirects"] is False                         # 따라가면 이동 사실이 가려진다


def test_article_status_never_raises(monkeypatch):
    def boom(url, **kw):
        raise TimeoutError("느림")
    monkeypatch.setattr(collector.requests, "get", boom)
    assert "문서 확인 실패" in collector.wiki_article_status("x")


def test_wikipedia_branch_is_wired_into_the_free_source_collection():
    """만들어만 두고 아무도 안 부르는 층을 막는다 — 정오 이후 404 는 실패로 센다(log_error), 이전은 값 없음."""
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources"][0]
    calls = {c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert {"wiki_404_is_lag", "wiki_article_status", "mark_no_data", "log_error"} <= calls
    # 문서 이름은 상수 한 곳에서 온다 — 요청 URL 과 진단이 같은 이름을 본다
    consts = {t.id for n in ast.walk(fn) for t in ast.walk(n) if isinstance(t, ast.Name)}
    assert "WIKI_EBOLA_TITLE" in consts


# ═══ H. CDC NWSS 수집 ════════════════════════════════════════════════════════════

class _Json:
    def __init__(self, payload, fail=False):
        self._payload, self._fail = payload, fail

    def raise_for_status(self):
        if self._fail:
            raise RuntimeError("HTTP 500")

    def json(self):
        return self._payload


def _stub_nwss(monkeypatch, *, max_fails=False):
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append(params["$select"])
        sel = params["$select"]
        if sel == "sample_collect_date":
            return _Json([{"sample_collect_date": "2026-10-13T00:00:00.000"}])
        if sel.startswith("count(*)"):
            return _Json([{"n": "656", "avg_conc": "1680229.84"}])
        if sel.startswith("max("):
            return _Json([], fail=True) if max_fails else _Json([{"mx": "1100000000"}])
        raise AssertionError(sel)
    monkeypatch.setattr(collector.requests, "get", fake_get)
    return calls


def test_nwss_keeps_the_mean_and_adds_the_max_for_diagnosis(monkeypatch):
    calls = _stub_nwss(monkeypatch)
    out = collector.fetch_cdc_nwss()
    assert out == {"date": "2026-10-07~2026-10-13", "site_count": 656,
                   "mean_concentration": 1680229.8, "max_concentration": 1100000000.0}
    assert len(calls) == 3


def test_a_failing_max_query_never_costs_the_mean(monkeypatch):
    """최댓값은 진단용 보조 값이다 — 본 수집(평균)을 막으면 안 된다."""
    _stub_nwss(monkeypatch, max_fails=True)
    out = collector.fetch_cdc_nwss()
    assert out["mean_concentration"] == 1680229.8 and out["max_concentration"] is None


def test_nwss_record_key_names_are_unchanged_for_old_records():
    """기록 호환 — 키 이름(`site_count`·`mean_concentration`)은 바꾸지 않았다."""
    src = COLLECTOR_PY.read_text(encoding="utf-8")
    assert '"site_count": int(row["n"])' in src and '"mean_concentration"' in src

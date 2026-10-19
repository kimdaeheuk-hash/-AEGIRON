"""주간 추세 예측 (2026-10-19, 캡틴 승인 ②).

배경: 90일 발병 예측은 기한이 길어 피드백 루프가 '측정 대기'에 묶여 있었다(채점 0건).
공식 주간 표본감시(일본 IDWR)의 다음 주 증감을 봉인하고 다음 주 공식 값으로 채점한다.
이 시험은 그 층의 정직성 경계선을 고정한다 — 90일 발병 예측과 섞지 않음, 정답이 없으면
오답이 아니라 판정 안 함, 표본 8건 미만이면 성적을 말하지 않음, 처음 본 값으로 채점.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib

import pytest

from algorithms import weekly_forecast as wf

UTC = dt.timezone.utc
COLLECTOR_PY = pathlib.Path(__file__).resolve().parents[1] / "collector.py"


def _idwr(year, week, flu=None, covid=None, rsv=None, extra=None):
    totals = {}
    if flu is not None:
        totals["Influenza"] = flu
    if covid is not None:
        totals["COVID-19"] = covid
    if rsv is not None:
        totals["RS virus infection"] = rsv
    totals.update(extra or {})
    return {"year": year, "week": week, "national_totals": totals}


def _at(y, m, d, h=6):
    return dt.datetime(y, m, d, h, tzinfo=UTC)


def _no_fetch(y, w):
    return None


def _forecasts(db):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM weekly_forecasts ORDER BY id")]


# ── 주 계산 ─────────────────────────────────────────────────────────

def test_next_week_crosses_year_boundary_including_53_week_years():
    assert wf.next_week(2026, 53) == (2027, 1)      # 2026 은 53주까지 있다
    assert wf.next_week(2025, 52) == (2026, 1)      # 2025 는 52주
    assert wf.next_week(2026, 41) == (2026, 42)


def test_weeks_back_excludes_current_unfinished_week():
    got = wf.weeks_back(dt.date(2026, 10, 19), 3)     # 2026-10-19 = 43주 월요일
    assert got == [(2026, 40), (2026, 41), (2026, 42)]


# ── 값 고르기 ────────────────────────────────────────────────────────

def test_match_value_unique_column():
    assert wf.match_value({"Influenza": 42320, "Mumps": 3}, ("influenza",)) == (42320.0, None)


def test_match_value_refuses_ambiguous_or_missing_columns():
    # 이름이 바뀐 열을 다른 질병 값으로 채우지 않는다.
    assert wf.match_value({"Mumps": 3}, ("influenza",)) == (None, "해당 열 없음")
    two = {"Influenza": 1, "Influenza (hospitalized)": 2}
    assert wf.match_value(two, ("influenza",)) == (None, "열 2개 일치")
    assert wf.match_value({"Influenza": None}, ("influenza",)) == (None, "값 없음")
    assert wf.match_value(None, ("influenza",)) == (None, "합계 없음")


# ── 모델 ────────────────────────────────────────────────────────────

def test_forecast_rising_is_above_half_and_naive_says_up():
    p, naive = wf.forecast_prob([100, 120, 150])
    assert p > 0.5 and naive == 1


def test_forecast_falling_is_below_half_and_naive_says_down():
    p, naive = wf.forecast_prob([150, 120, 100])
    assert p < 0.5 and naive == 0


def test_forecast_is_clamped_and_refuses_zero():
    p, _ = wf.forecast_prob([1, 10, 1000])
    assert p == wf.P_MAX                    # 세 점으로 0.9 위를 말하지 않는다
    assert wf.forecast_prob([0, 10, 20]) is None
    assert wf.forecast_prob([10, 20]) is None


# ── 저장: 처음 본 값으로 채점한다 ──────────────────────────────────────

def test_observation_keeps_first_seen_value(isolated_db):
    now = _at(2026, 10, 19)
    wf.observe_record(_idwr(2026, 40, flu=1000), now)
    wf.observe_record(_idwr(2026, 40, flu=1300), now + dt.timedelta(days=7))   # 나중에 고쳐진 값
    with isolated_db.get_connection() as conn:
        v = conn.execute("SELECT value FROM weekly_observations WHERE series='jp_influenza' "
                         "AND year=2026 AND week=40").fetchone()[0]
    assert v == 1000


# ── 기록: 대상 주당 1건, 미게시 주만 ────────────────────────────────────

def _seed(now, weeks_values, series_kw="flu"):
    for (y, w), v in weeks_values:
        wf.observe_record(_idwr(y, w, **{series_kw: v}), now)


def test_record_needs_three_consecutive_weeks(isolated_db):
    now = _at(2026, 10, 19)
    _seed(now, [((2026, 38), 100), ((2026, 40), 120)])          # 39주 빠짐
    out = wf.record_due(now, (2026, 40))
    assert out["made"] == []
    assert out["skipped"]["jp_influenza"] == "연속 3주 이력 부족"


def test_record_targets_next_unpublished_week_once(isolated_db):
    now = _at(2026, 10, 19)
    _seed(now, [((2026, 38), 100), ((2026, 39), 110), ((2026, 40), 130)])
    first = wf.record_due(now, (2026, 40))
    assert [m["target"] for m in first["made"]] == ["2026-W41"]
    again = wf.record_due(now + dt.timedelta(hours=1), (2026, 40))   # 다음 주기
    assert again["made"] == []                                    # 같은 대상 주에 두 번 쓰지 않는다
    f = _forecasts(isolated_db)[0]
    assert (f["base_week"], f["target_week"], f["base_value"]) == (40, 41, 130)
    assert f["method"] == wf.METHOD and f["outcome"] is None


def test_no_record_when_this_cycle_did_not_confirm_the_latest_published_week(isolated_db):
    """이번 주기 수집이 실패하면 저장된 마지막 주가 실제 최신 게시 주가 아닐 수 있다 —
    그때 기록하면 이미 게시된 주를 '예측'하게 된다. 기록하지 않는다."""
    now = _at(2026, 10, 19)
    _seed(now, [((2026, 38), 100), ((2026, 39), 110), ((2026, 40), 130)])
    out = wf.record_due(now, None)
    assert out["made"] == [] and "확인 못 함" in out["skipped"]["*"]
    # 수집기가 41주를 최신이라 했는데 그 주 값이 없는 계열도 기록하지 않는다(40주 기준으로 쓰면
    # 대상 41주는 이미 게시된 주다).
    out = wf.record_due(now, (2026, 41))
    assert out["made"] == [] and out["skipped"]["jp_influenza"] == "최신 게시 주 값 없음"
    summary = wf.run_cycle(None, _no_fetch, now=now, submit=lambda d: None)
    assert summary["recorded"]["made"] == [] and _forecasts(isolated_db) == []


def test_weekly_forecasts_never_enter_the_90_day_ledger(isolated_db):
    """맞히기 쉬운 방향 예측이 발병 예측 적중률을 부풀리면 안 된다 — 표가 따로다."""
    now = _at(2026, 10, 19)
    _seed(now, [((2026, 38), 100), ((2026, 39), 110)])
    wf.run_cycle(_idwr(2026, 40, flu=130), _no_fetch, now=now, submit=lambda d: None)
    assert _forecasts(isolated_db)
    assert isolated_db.list_predictions() == []


# ── 채점 ────────────────────────────────────────────────────────────

def _one_open_forecast(now):
    _seed(now, [((2026, 38), 100), ((2026, 39), 110), ((2026, 40), 130)])
    wf.record_due(now, (2026, 40))


@pytest.mark.parametrize("actual,outcome", [(150, "up"), (90, "down")])
def test_resolve_up_and_down_against_base_value(isolated_db, actual, outcome):
    now = _at(2026, 10, 19)
    _one_open_forecast(now)
    wf.observe_record(_idwr(2026, 41, flu=actual), now + dt.timedelta(days=7))
    res = wf.resolve_due(now + dt.timedelta(days=7))
    f = _forecasts(isolated_db)[0]
    assert f["outcome"] == outcome and f["actual_value"] == actual
    assert res["resolved"] == [f["id"]]


def test_unchanged_value_is_void_not_scored(isolated_db):
    now = _at(2026, 10, 19)
    _one_open_forecast(now)
    wf.observe_record(_idwr(2026, 41, flu=130), now + dt.timedelta(days=7))
    wf.resolve_due(now + dt.timedelta(days=7))
    f = _forecasts(isolated_db)[0]
    assert f["outcome"] == "void" and "변화 없음" in f["outcome_note"]


def test_missing_answer_stays_open_then_voids_never_counts_as_wrong(isolated_db):
    """정답을 못 받은 것은 오답이 아니다 — 기한 전엔 미결, 기한 뒤엔 판정 안 함."""
    now = _at(2026, 10, 19)
    _one_open_forecast(now)
    wf.resolve_due(now + dt.timedelta(days=14))
    assert _forecasts(isolated_db)[0]["outcome"] is None
    deadline = wf.week_start(2026, 41) + dt.timedelta(days=wf.VOID_AFTER_DAYS)
    wf.resolve_due(dt.datetime.combine(deadline + dt.timedelta(days=1), dt.time(6), UTC))
    f = _forecasts(isolated_db)[0]
    assert f["outcome"] == "void" and "정답 미수신" in f["outcome_note"]
    assert wf.scorecard(_forecasts(isolated_db))["scored"] == 0


# ── 채점표: 표본이 모자라면 성적을 말하지 않는다 ─────────────────────────

def _row(p, outcome, naive=None):
    return {"prob_up": p, "outcome": outcome, "naive_up": naive}


def test_scorecard_below_minimum_is_not_enough():
    card = wf.scorecard([_row(0.7, "up", 1)] * (wf.MIN_SCORED - 1))
    assert card["enough"] is False and card["scored"] == wf.MIN_SCORED - 1


def test_scorecard_brier_hits_and_naive_baseline():
    rows = [_row(0.8, "up", 1), _row(0.8, "down", 1), _row(0.3, "down", 0), _row(0.5, "up", 0),
            _row(0.6, None), _row(0.6, "void")]
    card = wf.scorecard(rows)
    assert card["scored"] == 4 and card["open"] == 1 and card["void"] == 1
    # Brier = ((0.2)^2 + (0.8)^2 + (0.3)^2 + (0.5)^2) / 4
    assert card["brier_model"] == round((0.04 + 0.64 + 0.09 + 0.25) / 4, 4)
    assert card["calls_model"] == 3          # 0.5 는 방향을 말하지 않은 것
    assert card["hits_model"] == 2
    assert (card["hits_naive"], card["calls_naive"]) == (2, 4)
    assert card["brier_coin"] == 0.25


def test_cycle_line_says_not_judged_when_sample_is_small():
    summary = {"recorded": {"made": [], "skipped": {}}, "resolved": {"resolved": [], "voided": []},
               "observed": {"stored": [], "skipped": {}}, "sealed": {"remaining": 0},
               "synced": None, "card": wf.scorecard([_row(0.7, "up", 1)])}
    line = wf.cycle_line(summary)
    assert "성적 판정 안 함" in line and "Brier" not in line


# ── 봉인 ────────────────────────────────────────────────────────────

def test_seal_uses_canonical_hash_and_stops_when_calendar_is_down(isolated_db):
    now = _at(2026, 10, 19)
    _one_open_forecast(now)
    out = wf.seal_pending(submit=lambda digest: None)
    assert out == {"sealed": 0, "failed": 1, "remaining": 1}
    seen = []
    out = wf.seal_pending(submit=lambda digest: seen.append(digest) or "ab12")
    f = _forecasts(isolated_db)[0]
    assert out["sealed"] == 1 and out["remaining"] == 0
    assert f["content_hash"] == seen[0] == wf.canonical_hash(f)
    assert f["ots_proof_hex"] == "ab12"


def test_canonical_hash_ignores_answer_fields():
    base = {"id": 1, "series": "jp_influenza", "base_year": 2026, "base_week": 40,
            "base_value": 130, "target_year": 2026, "target_week": 41, "prob_up": 0.6,
            "naive_up": 1, "method": wf.METHOD, "created_at": "2026-10-19T06:00:00+00:00"}
    assert wf.canonical_hash(base) == wf.canonical_hash({**base, "outcome": "up", "actual_value": 9})


# ── 이력 동기화 ───────────────────────────────────────────────────────

def test_sync_fetches_only_missing_weeks_once_a_day(isolated_db):
    now = _at(2026, 10, 19)
    wf.observe_record(_idwr(2026, 42, flu=200), now)
    calls = []

    def fetch(y, w):
        calls.append((y, w))
        if w == 41:
            return None                               # 아직 게시 전
        if w == 40:
            raise TimeoutError("slow")                # 한 주 실패가 나머지를 막지 않는다
        return _idwr(y, w, flu=100 + w)

    out = wf.sync_history(fetch, now)
    assert (2026, 42) not in calls                    # 이미 있는 주는 안 받는다
    assert len(calls) == wf.SYNC_WEEKS_BACK - 1
    assert out["unpublished"] == 1 and out["errors"] == {"TimeoutError": 1}
    assert out["fetched"] == wf.SYNC_WEEKS_BACK - 3
    assert wf.sync_history(fetch, now + dt.timedelta(hours=23)) is None      # 하루 한 번
    assert wf.sync_history(fetch, now + dt.timedelta(hours=25)) is not None


# ── 매시 주기: 채점이 기록보다 먼저 ────────────────────────────────────

def test_run_cycle_resolves_before_recording_the_next_week(isolated_db):
    now = _at(2026, 10, 19)
    _seed(now, [((2026, 38), 100), ((2026, 39), 110)])
    wf.run_cycle(_idwr(2026, 40, flu=130), _no_fetch, now=now, submit=lambda d: None)
    later = now + dt.timedelta(days=7)
    summary = wf.run_cycle(_idwr(2026, 41, flu=150), _no_fetch, now=later, submit=lambda d: None)
    rows = _forecasts(isolated_db)
    assert [(r["target_week"], r["outcome"]) for r in rows] == [(41, "up"), (42, None)]
    assert summary["card"]["scored"] == 1


# ── 수집기: 한 주 처리부를 떼어도 동작은 같다 ───────────────────────────

def test_fetch_japan_idwr_still_falls_back_through_recent_weeks(monkeypatch):
    import collector
    seen = []

    def week(y, w):
        seen.append(w)
        if len(seen) == 1:
            return None                    # 이번 주 미게시
        if len(seen) == 2:
            raise ValueError("bad csv")    # 다음 주 실패 → 계속
        return {"year": y, "week": w, "national_totals": {"Influenza": 1}}

    monkeypatch.setattr(collector, "fetch_japan_idwr_week", week)
    got = collector.fetch_japan_idwr()
    assert got["national_totals"] == {"Influenza": 1} and len(seen) == 3


# ── 배선: 만들어만 두고 아무도 안 부르는 층이 되지 않게 ─────────────────

def test_collector_cycle_runs_weekly_forecast_and_logs_its_line():
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    run_calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "run_cycle"]
    assert run_calls, "collect_free_sources 가 weekly_forecast.run_cycle 을 부르지 않는다"
    assert any(isinstance(a, ast.Name) and a.id == "fetch_japan_idwr_week"
               for a in run_calls[0].args), "지난 주 동기화에 fetch_japan_idwr_week 를 넘기지 않는다"
    logs_line = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "log"
                 and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                         and c.func.id == "cycle_line" for a in n.args for c in ast.walk(a))]
    assert logs_line, "주간 예측 줄(cycle_line)을 log 로 내보내지 않는다"

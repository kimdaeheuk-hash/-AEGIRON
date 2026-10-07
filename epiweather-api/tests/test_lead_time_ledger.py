"""선행성 원장이 **순서를 지키는지** 지킨다 (2026-09-03).

## 왜 만들었나

캡틴: *"지금까지 한 번밖에 실측을 못한 거야? 이유가 뭐야?"* → 파보니 **한 번도
못 했다.** 유일한 실측이라던 에볼라 DRC 2026 을 열어보니:

    공식 선언일        2026-05-15
    신호일 2026-05-15  →  우리가 기록한 날 2026-06-26   (+42일)
    신호일 2026-05-17  →  우리가 기록한 날 2026-08-10   (+85일)

**선언이 끝나고 두 달 뒤에 넣은 신호로 "선언보다 5일 먼저" 를 재고 있었다.**

원인은 방식 자체였다. 선언이 난 **뒤에** 신호를 거꾸로 뒤지면, 사후에 적재된
것과 그때 손에 있던 것을 가리기 어렵다. 그래서 순서를 뒤집었다 — 문턱을 넘는
순간 그 자리에서 적고, 선언은 그 뒤에 온다.

## ★ 이 파일이 지키는 것 ★

**crossed_at 이 선언보다 앞선다는 사실.** 그게 이 원장의 전부다. 이 순서가
깨지면 원장은 그냥 또 하나의 사후 계산기가 된다.

그리고 **빗나간 것을 지우지 않는 것.** 맞은 것만 남기면 정밀도만 있고 재현율이
사라져 숫자가 무의미해진다.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from algorithms import lead_time_ledger as ledger
from algorithms.lead_time_ledger import (
    OUTCOME_DECLARED, OUTCOME_NO_DECLARATION, OUTCOME_OPEN,
    RESOLUTION_HORIZON_DAYS, ledger_record, list_entries, open_crossing,
    resolve_ledger, scan_and_record,
)

UTC = dt.timezone.utc


def _at(y, m, d):
    return dt.datetime(y, m, d, tzinfo=UTC)


def _declare(dbmod, event_id, name, date):
    dbmod.upsert_timeline_event(event_id, name, date,
                                "who_pheic", "WHO PHEIC 선언", "WHO DON", "who")


# ── 첫 진입만 적는다 ──────────────────────────────────────────────────────

def test_only_the_first_crossing_is_recorded(isolated_db):
    """★★핵심★★ 같은 질병·국가가 계속 문턱 위여도 첫 진입만 남긴다.

    매 주기 갱신하면 crossed_at 이 오늘로 계속 밀려서 **선행일수가 0 으로
    수렴한다.** 그러면 원장이 아무것도 증명하지 못한다.
    """
    first = open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    again = open_crossing("에볼라", "COD", 92.0, 80.0, [1, 2], now=_at(2026, 5, 8))

    assert first is not None
    assert again is None, "두 번째 주기에 또 적었다"
    (row,) = list_entries()
    assert row["crossed_at"].startswith("2026-05-01")
    assert row["severity"] == 85.0, "나중 값으로 덮어썼다"


def test_different_countries_are_tracked_separately(isolated_db):
    """같은 병이라도 나라가 다르면 다른 사건이다."""
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    open_crossing("에볼라", "UGA", 85.0, 80.0, [2], now=_at(2026, 5, 1))

    assert len(list_entries()) == 2


def test_crossing_keeps_its_evidence(isolated_db):
    """★핵심★ 무엇을 보고 넘었다고 했는지 남긴다 — 되짚을 수 없는 기록은 증거가 아니다."""
    entry = open_crossing("에볼라", "COD", 85.0, 80.0, [7, 3, 5], now=_at(2026, 5, 1))

    assert json.loads(entry["signal_ids"]) == [3, 5, 7]
    assert entry["threshold"] == 80.0, "그때의 문턱을 안 남기면 나중에 못 되짚는다"


# ── 순서 — 이 원장의 존재 이유 ────────────────────────────────────────────

def test_declaration_after_our_record_counts_as_lead(isolated_db):
    """★★핵심★★ 우리가 먼저 적고, 선언이 뒤에 오면 그게 선행이다."""
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")

    outcome = resolve_ledger(now=_at(2026, 5, 20))

    (hit,) = outcome["closed_declared"]
    assert hit["lead_days"] == 14
    assert list_entries()[0]["outcome"] == OUTCOME_DECLARED


def test_declaration_before_our_record_is_not_our_lead(isolated_db):
    """★★핵심★★ 이미 선언된 뒤에 문턱을 넘은 건 '먼저 안 것' 이 아니다.

    이 한 줄이 없으면, 선언 기사가 쏟아져서 문턱을 넘은 것을 우리 공으로 센다.
    에볼라 DRC 2026 에서 실제로 그런 일이 났다.
    """
    dbmod = isolated_db
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")
    # 선언 뒤에 넘었다
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 6, 26))

    outcome = resolve_ledger(now=_at(2026, 7, 1))

    assert outcome["closed_declared"] == []
    assert outcome["still_open"] == 1, "선언에 잘못 붙였다"


def _watching(start: dt.date) -> None:
    """정답 경로가 `start` 구간을 보고 있었다는 전제(전날부터 가동, 구간 안에 선언 1건)."""
    from tests._live_channel import seed_live_channel
    seed_live_channel(start - dt.timedelta(days=1), start + dt.timedelta(days=10))


def test_declaration_beyond_the_horizon_is_not_credited(isolated_db):
    """★핵심★ 90일 뒤에 난 선언을 우리 공으로 세지 않는다."""
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 1, 1))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-06-01")   # 151일 뒤
    _watching(dt.date(2026, 1, 1))

    outcome = resolve_ledger(now=_at(2026, 6, 5))

    assert outcome["closed_declared"] == []
    assert outcome["closed_no_declaration"] == 1


# ── 빗나간 것도 남긴다 ────────────────────────────────────────────────────

def test_silent_crossings_are_closed_as_false_alarms(isolated_db):
    """★★핵심★★ 문턱을 넘었는데 선언이 없으면 오경보로 닫는다 — 지우지 않는다.

    맞은 것만 남기면 정밀도만 있고 재현율이 사라진다.
    """
    open_crossing("니파", "IND", 85.0, 80.0, [1], now=_at(2026, 1, 1))
    _watching(dt.date(2026, 1, 1))

    outcome = resolve_ledger(now=_at(2026, 1, 1) + dt.timedelta(days=RESOLUTION_HORIZON_DAYS + 1))

    assert outcome["closed_no_declaration"] == 1
    (row,) = list_entries()
    assert row["outcome"] == OUTCOME_NO_DECLARATION
    assert row["lead_days"] is None
    assert list_entries(outcome=OUTCOME_NO_DECLARATION), "오경보가 사라졌다"


def test_open_crossing_within_horizon_is_left_alone(isolated_db):
    """기한 전이면 건드리지 않는다 — 아직 결과를 모른다."""
    open_crossing("니파", "IND", 85.0, 80.0, [1], now=_at(2026, 1, 1))

    outcome = resolve_ledger(now=_at(2026, 2, 1))

    assert outcome["still_open"] == 1
    assert list_entries()[0]["outcome"] == OUTCOME_OPEN


def test_report_shows_false_alarms_and_precision(isolated_db):
    """★핵심★ 성적표가 오경보를 숨기지 않는다."""
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")
    open_crossing("니파", "IND", 85.0, 80.0, [2], now=_at(2026, 1, 1))
    _watching(dt.date(2026, 1, 1))
    resolve_ledger(now=_at(2026, 5, 20))

    record = ledger_record()

    assert record["measured_events"] == 1
    assert record["false_alarms"] == 1
    assert record["precision"] == 0.5
    assert record["mean_lead_days"] == 14


def test_empty_ledger_says_it_has_no_evidence(isolated_db):
    """★★핵심★★ 0건이면 0건이라고 말한다 — 선행성을 주장하지 않는다."""
    record = ledger_record()

    assert record["measured_events"] == 0
    assert record["mean_lead_days"] is None
    assert "선행성 주장을 할 근거가 없다" in record["note"]
    assert record["is_prospective"] is True


# ── 훑기 — 백필이 가짜 기록을 만들지 못하게 ────────────────────────────────

def _signal(dbmod, disease, iso3, day, signal_type="급증", trust=0.9):
    return dbmod.create_extracted_signal(
        source="msf", disease=disease, location=iso3, signal_type=signal_type,
        severity=["spike"], symptom=None, transmission=None, source_trust=trust,
        signal_date=day, raw_text="t", country_iso3=iso3)


def test_old_signals_backfilled_today_do_not_create_a_crossing(isolated_db):
    """★★핵심★★ 2019년 자료를 오늘 적재해도 오늘의 통과로 세지 않는다.

    이 방어가 없으면 **백필 한 번이 가짜 선행 기록을 만든다** — 그리고 그 뒤
    90일 안에 아무 선언이나 나면 우리 공이 된다.
    """
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2019-06-10")

    opened = scan_and_record(now=_at(2026, 9, 3))

    assert opened == []
    assert list_entries() == []


def test_recent_high_severity_signals_open_a_crossing(isolated_db, monkeypatch):
    """최근 신호가 문턱을 넘으면 적는다."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")

    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY",
                        {"급증": 95})
    opened = scan_and_record(now=_at(2026, 9, 3))

    assert len(opened) == 1
    assert opened[0]["disease"] and opened[0]["country_iso3"] == "COD"
    assert opened[0]["severity"] >= 80


def test_below_threshold_is_not_recorded(isolated_db, monkeypatch):
    """★핵심★ 문턱을 안 넘으면 적지 않는다 — 원장이 잡음으로 채워지면 못 쓴다."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")

    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY", {"급증": 10})
    opened = scan_and_record(now=_at(2026, 9, 3))

    assert opened == []


def test_scan_uses_the_same_threshold_as_the_backtest(isolated_db, monkeypatch):
    """★핵심★ 되짚기와 같은 문턱을 쓴다 — 다르면 두 성적표가 다른 말을 한다."""
    from algorithms.historical_backtest import PRIMARY_THRESHOLD_SCORE

    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")
    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY",
                        {"급증": PRIMARY_THRESHOLD_SCORE})

    (entry,) = scan_and_record(now=_at(2026, 9, 3))

    assert entry["threshold"] == PRIMARY_THRESHOLD_SCORE


def test_zero_trust_signals_do_not_count(isolated_db, monkeypatch):
    """신뢰도 0인 신호로 문턱을 넘지 않는다 — 가중평균이 무너진다."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01", trust=0.0)

    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY", {"급증": 99})

    assert scan_and_record(now=_at(2026, 9, 3)) == []


# ── 수집기·엔드포인트 배선 ─────────────────────────────────────────────────

def test_collector_runs_the_ledger():
    """★핵심★ 수집기가 원장을 돌려야 선제 기록이 쌓인다."""
    import inspect

    import collector

    source = inspect.getsource(collector.collect_free_sources)
    assert "scan_and_record" in source
    assert "resolve_ledger" in source


def test_endpoint_exposes_the_ledger(isolated_db):
    """원장을 밖에서 볼 수 있어야 근거로 쓸 수 있다."""
    from fastapi.testclient import TestClient
    import main

    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    body = TestClient(main.app).get("/api/lead-time-ledger").json()

    assert body["summary"]["measured_events"] == 0
    assert body["entries"][0]["disease"] == "에볼라"


# ── 한 선언은 한 번만 센다 (2026-09-03, 실측 시뮬레이션에서 발견) ──────────

def test_one_declaration_credits_only_one_crossing(isolated_db):
    """★★핵심★★ 선언 하나가 실측 두 건이 되면 안 된다.

    운영 신호로 돌려보니 `에볼라/COD` 와 `에볼라/국가미상` 이 동시에 문턱을
    넘는 경우가 있었다. 각각 채점하면 **선언 하나로 성적표를 두 배로 부풀린다** —
    우리가 우리 성적을 조작하는 셈이다.
    """
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    open_crossing("에볼라", None, 85.0, 80.0, [2], now=_at(2026, 5, 5))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")

    outcome = resolve_ledger(now=_at(2026, 5, 20))

    assert len(outcome["closed_declared"]) == 1
    assert outcome["closed_duplicate"] == 1
    assert ledger_record()["measured_events"] == 1


def test_the_earliest_crossing_gets_the_credit(isolated_db):
    """★핵심★ 가장 먼저 적은 기록이 그 사건의 선행일수다."""
    dbmod = isolated_db
    open_crossing("에볼라", None, 85.0, 80.0, [2], now=_at(2026, 5, 10))
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")

    (hit,) = resolve_ledger(now=_at(2026, 5, 20))["closed_declared"]

    assert hit["country_iso3"] == "COD"
    assert hit["lead_days"] == 14, "늦게 넘은 쪽을 채점했다"


def test_duplicate_is_not_counted_as_a_false_alarm(isolated_db):
    """★핵심★ 중복을 오경보로 세면 정밀도가 억울하게 깎인다."""
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    open_crossing("에볼라", None, 85.0, 80.0, [2], now=_at(2026, 5, 5))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")
    resolve_ledger(now=_at(2026, 5, 20))

    record = ledger_record()

    assert record["false_alarms"] == 0
    assert record["duplicates"] == 1
    assert record["precision"] == 1.0


def test_a_later_cycle_does_not_re_credit_the_same_event(isolated_db):
    """★핵심★ 지난 주기에 채점한 선언을 다음 주기에 또 채점하지 않는다."""
    dbmod = isolated_db
    open_crossing("에볼라", "COD", 85.0, 80.0, [1], now=_at(2026, 5, 1))
    _declare(dbmod, "ebola_cod", "에볼라 COD", "2026-05-15")
    resolve_ledger(now=_at(2026, 5, 20))

    # 다음 주기에 같은 병으로 또 문턱을 넘었다
    open_crossing("에볼라", "UGA", 85.0, 80.0, [3], now=_at(2026, 5, 21))
    outcome = resolve_ledger(now=_at(2026, 5, 25))

    assert outcome["closed_declared"] == []
    assert ledger_record()["measured_events"] == 1

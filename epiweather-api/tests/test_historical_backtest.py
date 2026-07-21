"""실제 발병 이력 기반 백테스트(⑳) — 합성 데이터가 아니라 outbreak_timeline의
실제 마일스톤과 extracted_signals의 실제 신호를 대조하는지, 근거 데이터가
없는 단계마다 정직하게 '검증 불가'로 표시하는지 확인."""
from __future__ import annotations

from algorithms.historical_backtest import backtest_event, backtest_all_known_events


def test_no_timeline_event_returns_unverified(isolated_db):
    result = backtest_event("nonexistent_event")
    assert result["verified"] is False
    assert "등록된 이벤트" in result["reason"]


def test_timeline_without_declaration_milestone_returns_unverified(isolated_db):
    import db as dbmod
    dbmod.upsert_timeline_event(
        "mers_test", "MERS 테스트", "2026-01-01",
        "year_start", "감시 시작", "WHO", "who",
    )
    result = backtest_event("mers_test")
    assert result["verified"] is False
    assert "선언급 마일스톤" in result["reason"]


def test_declaration_without_matching_signals_returns_unverified(isolated_db):
    import db as dbmod
    dbmod.upsert_timeline_event(
        "ebola_test", "에볼라 테스트 이벤트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )
    result = backtest_event("ebola_test")
    assert result["verified"] is False
    assert "실제 신호가 없음" in result["reason"]


def test_signals_below_threshold_reports_no_alert(isolated_db):
    import db as dbmod
    dbmod.upsert_timeline_event(
        "ebola_test", "에볼라 테스트 이벤트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )
    dbmod.create_extracted_signal(
        source="test", disease="에볼라", location="DRC", signal_type="감소",
        severity=[], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-05-10", raw_text="t",
    )
    result = backtest_event("ebola_test")
    assert result["verified"] is True
    assert result["would_have_alerted"] is False


def test_signals_crossing_threshold_before_declaration_computes_positive_lead_days(isolated_db):
    """MSF가 5/9에 경보를 냈고 WHO는 5/16에 선언했다면(실제 seed 데이터와 동일
    패턴), 아이기론의 신호도 그 사이 기간에 잡혀야 lead_days가 양수로 나옴."""
    import db as dbmod
    dbmod.upsert_timeline_event(
        "ebola_test", "에볼라 테스트 이벤트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )
    dbmod.create_extracted_signal(
        source="msf", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=["spike"], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-05-09", raw_text="t",
    )
    result = backtest_event("ebola_test")
    assert result["verified"] is True
    assert result["would_have_alerted"] is True
    assert result["first_high_severity_signal_date"] == "2026-05-09"
    assert result["lead_days"] == 7


def test_backtest_all_known_events_aggregates_verified_cases_only(isolated_db):
    import db as dbmod
    # 검증 가능(신호 있음, 선언보다 3일 먼저 탐지)
    dbmod.upsert_timeline_event(
        "ebola_test", "에볼라 테스트 이벤트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )
    dbmod.create_extracted_signal(
        source="msf", disease="에볼라", location="DRC", signal_type="급증",
        severity=["spike"], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-05-13", raw_text="t",
    )
    # 검증 불가(선언 마일스톤 없음) — 요약 평균에 안 들어가야 함
    dbmod.upsert_timeline_event(
        "mers_test", "MERS 테스트", "2026-01-01",
        "year_start", "감시 시작", "WHO", "who",
    )

    result = backtest_all_known_events()
    assert result["summary"]["events_checked"] == 2
    assert result["summary"]["events_with_verified_lead_time"] == 1
    assert result["summary"]["mean_lead_days"] == 3.0

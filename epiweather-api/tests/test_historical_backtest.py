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


def test_lead_days_output_always_carries_detection_baseline(isolated_db):
    """㉗ — lead_days는 항상 detection_baseline(어느 임계값/severity 모델 위에서
    측정됐는지)을 달고 나와야 함. 기준선 없이 숫자만 인용하지 못하게."""
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
    assert result["would_have_alerted"] is True
    baseline = result["detection_baseline"]
    assert baseline["primary_threshold_tier"] == "high"
    assert baseline["primary_threshold_score"] == 80
    assert "SIGNAL_TYPE_SEVERITY" in baseline["severity_model"]


def test_threshold_sensitivity_reports_lead_days_at_each_threshold(isolated_db):
    """민감도 분석 — 같은 사건의 lead_days를 medium/high/critical 각각에서 계산해
    '숫자가 임계값에 얼마나 흔들리는지' 보여줘야 함. 신규발생(85)은 high(80)는
    넘지만 critical(90)은 못 넘으므로 그 차이가 드러나야 함."""
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
    sens = backtest_event("ebola_test")["threshold_sensitivity"]
    # 신규발생 severity=85: medium(70)·high(80)는 탐지, critical(90)은 미탐지
    assert sens["medium"]["detected"] is True
    assert sens["high"]["detected"] is True
    assert sens["high"]["lead_days"] == 7
    assert sens["critical"]["detected"] is False
    assert sens["critical"]["lead_days"] is None


def test_signals_below_high_still_report_sensitivity(isolated_db):
    """주 임계값(high)을 못 넘어도, 더 낮은 임계값(medium)에서의 결과를
    민감도 분석으로 함께 보여줘야 함(would_have_alerted=False 경로)."""
    import db as dbmod
    dbmod.upsert_timeline_event(
        "ebola_test", "에볼라 테스트 이벤트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )
    # 진행중 severity=60: medium(70)도 못 넘음 → 전부 미탐지지만 sensitivity는 존재
    dbmod.create_extracted_signal(
        source="x", disease="에볼라", location="DRC", signal_type="진행중",
        severity=[], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-05-09", raw_text="t",
    )
    result = backtest_event("ebola_test")
    assert result["would_have_alerted"] is False
    assert "threshold_sensitivity" in result
    assert result["threshold_sensitivity"]["medium"]["detected"] is False


def test_covid_event_attaches_bluedot_comparison_without_false_victory(isolated_db):
    """코로나 이벤트는 아이기론 신호가 전혀 없어도 블루닷 비교(목표 기준선)를
    붙이되, aegiron_lead_days=None으로 '이겼다'고 주장하지 않아야 함(㉕ 정직성)."""
    import db as dbmod
    # main.py._seed_known_timelines의 코로나 시드와 동일 구조를 최소 재현
    dbmod.upsert_timeline_event(
        "covid19_wuhan_2019", "코로나19 우한 초기 2019-2020", "2019-12-31",
        "official_declaration", "중국 WHO 통보", "WHO", "who",
    )
    result = backtest_event("covid19_wuhan_2019")
    assert "bluedot_comparison" in result
    comp = result["bluedot_comparison"]
    assert comp["bluedot_lead_days"] == 9
    assert comp["aegiron_lead_days"] is None  # 당시 시스템 부재 → 실측 없음
    assert "실측 없음" in comp["verdict"]

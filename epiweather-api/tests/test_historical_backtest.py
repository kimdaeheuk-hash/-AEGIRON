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
    row = dbmod.create_extracted_signal(
        source="msf", disease="에볼라", location="DRC", signal_type="급증",
        severity=["spike"], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-05-13", raw_text="t",
    )
    # 선행성 판정은 **적재 시점** 기준이다 — 선언(5/16) 전에 갖고 있었다고 둔다.
    with dbmod.get_connection() as conn:
        conn.execute("UPDATE extracted_signals SET extracted_at = ? WHERE id = ?",
                     ("2026-05-14T00:00:00+00:00", row["id"]))
        conn.commit()
    # 검증 불가(선언 마일스톤 없음) — 요약 평균에 안 들어가야 함
    dbmod.upsert_timeline_event(
        "mers_test", "MERS 테스트", "2026-01-01",
        "year_start", "감시 시작", "WHO", "who",
    )

    result = backtest_all_known_events()
    assert result["summary"]["events_checked"] == 2
    assert result["summary"]["events_with_verified_lead_time"] == 1
    # msf 는 라이브 수집 소스다 — 실측 칸에 들어가야 한다.
    assert result["summary"]["live_measured_events"] == 1
    assert result["summary"]["live_mean_lead_days"] == 3.0
    assert result["summary"]["retrospective_events"] == 0


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


# ── 사후 조립을 실측과 섞지 않는다 (2026-09-03 발견) ──────────────────────

def _declare(dbmod, event_id="ebola_x", date="2026-05-16"):
    dbmod.upsert_timeline_event(event_id, "에볼라 테스트", date,
                                "who_pheic", "WHO PHEIC 선언", "WHO DON", "who")


def _signal(dbmod, source, day, trust=1.0, ingested_at=None):
    """신호를 넣고, 필요하면 **적재 시점**을 지정한다.

    적재 시점이 선행성 판정의 기준이다 — create_extracted_signal 은 항상 '지금'
    을 찍으므로, 과거 사건을 시험하려면 그 값을 되돌려줘야 한다.
    """
    row = dbmod.create_extracted_signal(
        source=source, disease="에볼라", location="DRC", signal_type="급증",
        severity=["spike"], symptom=None, transmission=None, source_trust=trust,
        signal_date=day, raw_text="t")
    if ingested_at:
        with dbmod.get_connection() as conn:
            conn.execute("UPDATE extracted_signals SET extracted_at = ? WHERE id = ?",
                         (f"{ingested_at}T00:00:00+00:00", row["id"]))
            conn.commit()
    return row


def test_backfill_signals_are_labelled_retrospective(isolated_db):
    """★★핵심★★ 사후 조립 데이터로 잰 선행일수를 실측이라 하지 않는다.

    2026-09-03 점검에서 발견한 결함이다. 2018·2019·2020 사건이 "검증됨 · 선행
    56일" 로 나오고 있었는데, 그때 아이기론은 **존재하지 않았다.** 그 신호는
    `nowcast_backfill` 이 지금 GDELT 뉴스량으로 조립해 넣은 것이었고, 그 모듈
    스스로 "전향 검증 전 실전대체 금지" 라고 밝힌 데이터였다.
    """
    import db as dbmod
    _declare(dbmod)
    # 선언(5/16) 뒤인 8/1 에 적재했다 — 그 시점에 우리는 갖고 있지 않았다.
    _signal(dbmod, "gdelt_backfill", "2026-05-13", trust=0.5, ingested_at="2026-08-01")

    (row,) = [r for r in backtest_all_known_events()["results"] if r.get("lead_days")]

    assert row["evidence_class"] == "retrospective"
    assert row["is_live_measurement"] is False
    assert row["signals_known_before_declaration"] == 0
    assert "선언 뒤에 적재된 신호" in row["evidence_note"]
    assert "선행성 증거가 아니다" in row["evidence_note"]


def test_live_and_retrospective_are_never_averaged_together(isolated_db):
    """★★핵심★★ 둘을 한 평균에 섞지 않는다.

    예전엔 합쳐서 18.0일이라는 한 숫자를 냈다. 그 숫자는 대부분 사후 조립분이라,
    제안서에 "18일 먼저 잡습니다" 로 쓰면 근거를 댈 수 없었다.
    """
    import db as dbmod
    _declare(dbmod, "ebola_live", "2026-05-16")
    # 선언 전(5/14)에 이미 갖고 있었다 — 실측 3일
    _signal(dbmod, "msf", "2026-05-13", ingested_at="2026-05-14")
    _declare(dbmod, "ebola_old", "2019-07-17")
    # 선언보다 7년 뒤에 조립해 넣었다 — 사후 37일
    _signal(dbmod, "gdelt_backfill", "2019-06-10", trust=0.5, ingested_at="2026-08-01")

    summary = backtest_all_known_events()["summary"]

    assert summary["live_measured_events"] == 1
    assert summary["live_mean_lead_days"] == 3.0, "사후분이 실측 평균에 섞였다"
    assert summary["retrospective_events"] == 1
    assert summary["retrospective_mean_lead_days"] == 37.0
    assert "mean_lead_days" not in summary, "합친 숫자가 아직 나온다"
    assert summary["mean_lead_days_combined_is_not_evidence"] is True


def test_late_ingested_signals_do_not_create_lead_time(isolated_db):
    """★★핵심★★ 선언 뒤에 넣은 신호는 선행일수를 만들지 못한다.

    2026-09-03 실측에서 나온 결함이다. 소스 이름으로만 가르면(gdelt_backfill 이냐)
    이걸 못 잡는다 — 에볼라 DRC 2026 은 msf·ebola_pheic 라는 정상 소스였는데
    **선언이 끝나고 42~85일 뒤에 적재된 것**이었다. 그걸로 "선언보다 5일" 을
    계산하고 있었다.

    ★ 선언 전에 갖고 있던 신호만이 선행성이다 ★ 소스 이름이 무엇이든.
    """
    import db as dbmod
    _declare(dbmod)                                        # 선언 2026-05-16
    _signal(dbmod, "msf", "2026-05-13", ingested_at="2026-06-26")   # 정상 소스, 늦은 적재

    result = backtest_all_known_events()
    (row,) = [r for r in result["results"] if r.get("lead_days")]

    assert row["evidence_class"] == "live_source", "소스는 라이브가 맞다"
    assert row["is_live_measurement"] is False, "그런데 그때 갖고 있지 않았다"
    assert row["signals_known_before_declaration"] == 0
    assert row["live_lead_days"] is None
    assert result["summary"]["live_measured_events"] == 0


def test_one_signal_in_hand_before_declaration_is_enough(isolated_db):
    """★핵심★ 선언 전에 손에 있던 신호가 임계를 넘으면 그건 실측이다.

    소스가 섞여 있어도 상관없다 — 중요한 건 그때 갖고 있었는가뿐이다.
    """
    import db as dbmod
    _declare(dbmod)
    _signal(dbmod, "msf", "2026-05-13", ingested_at="2026-05-14")
    _signal(dbmod, "gdelt_backfill", "2026-05-12", trust=0.5, ingested_at="2026-08-01")

    result = backtest_all_known_events()
    (row,) = [r for r in result["results"] if r.get("lead_days")]

    assert row["is_live_measurement"] is True
    assert row["signals_known_before_declaration"] == 1, "늦게 넣은 것이 섞였다"
    assert row["live_lead_days"] == 3
    assert result["summary"]["live_measured_events"] == 1


def test_evidence_note_names_the_reason_not_just_a_label(isolated_db):
    """★핵심★ 등급만 붙이고 끝내지 않는다 — 왜 증거가 아닌지 문장으로 남긴다."""
    import db as dbmod
    _declare(dbmod)
    _signal(dbmod, "msf", "2026-05-13", ingested_at="2026-05-14")

    (row,) = [r for r in backtest_all_known_events()["results"] if r.get("lead_days")]

    assert row["is_live_measurement"] is True
    assert "선언일 이전에 이미 수집돼 있던" in row["evidence_note"]
    assert row["signal_sources"] == ["msf"]


def test_summary_points_at_the_only_quotable_number(isolated_db):
    """★핵심★ 무엇을 인용해도 되는지 요약이 직접 말한다."""
    import db as dbmod
    _declare(dbmod)
    _signal(dbmod, "msf", "2026-05-13", ingested_at="2026-05-14")

    note = backtest_all_known_events()["summary"]["evidence_note"]

    assert "live_mean_lead_days 로만" in note
    assert "실전대체 금지" in note

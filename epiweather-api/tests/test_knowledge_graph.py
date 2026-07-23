"""질병 지식 그래프 — lead_days가 추정치임을 정직하게 표시하는지, 그리고
outbreak_timeline 실측 마일스톤으로 검증하는 로직이 맞는지 확인."""
from __future__ import annotations

from algorithms.knowledge_graph import get_disease_graph, verify_chain_lead_time, DISEASE_GRAPH


def test_get_disease_graph_flags_lead_days_as_estimated():
    result = get_disease_graph()
    assert result["lead_days_estimated"] is True

    single = get_disease_graph("Ebola")
    assert single["lead_days_estimated"] is True


def test_unsupported_disease_returns_error():
    result = get_disease_graph("정체불명질병")
    assert "error" in result


def test_verify_chain_lead_time_no_data_returns_unverified(isolated_db):
    result = verify_chain_lead_time("Ebola")
    assert result["verified"] is False
    assert result["cases"] == []


def test_verify_chain_lead_time_unmapped_disease_returns_unverified(isolated_db):
    result = verify_chain_lead_time("Dengue")
    # Dengue는 TIMELINE_EVENT_PREFIXES에 있지만 마일스톤이 없으면 미검증
    assert result["verified"] is False


def test_verify_chain_lead_time_computes_observed_span_from_real_milestones(isolated_db):
    import db as dbmod
    dbmod.upsert_timeline_event(
        "ebola_test_2026", "에볼라 테스트", "2026-05-09",
        "msf_first_alert", "MSF 현장 첫 경보", "MSF", "media",
    )
    dbmod.upsert_timeline_event(
        "ebola_test_2026", "에볼라 테스트", "2026-05-16",
        "who_pheic", "WHO PHEIC 선언", "WHO DON", "who",
    )

    result = verify_chain_lead_time("Ebola")
    assert result["verified"] is True
    case = result["cases"][0]
    assert case["observed_lead_days"] == 7  # 05-09 ~ 05-16
    assert case["event_id"] == "ebola_test_2026"
    graph_claim = max(s["lead_days"] for s in DISEASE_GRAPH["Ebola"]["chain"])
    assert case["graph_claimed_lead_days"] == graph_claim
    assert case["difference_days"] == 7 - graph_claim

    # ㉖ 실측 캘리브레이션: 하드코딩 추정치 옆에 실측 총 선행일수가 함께 나와야 함
    cal = result["calibration"]
    assert cal["calibrated"] is True
    assert cal["sample_size"] == 1
    assert cal["observed_mean_lead_days"] == 7
    assert cal["estimated_max_lead_days"] == graph_claim


def test_calibration_reports_uncalibrated_when_no_real_cases(isolated_db):
    """실측 사례가 없으면 calibrated=False로 정직하게 표기하고 추정치를 유지."""
    result = verify_chain_lead_time("Ebola")
    assert result["verified"] is False
    cal = result["calibration"]
    assert cal["calibrated"] is False
    assert cal["observed_mean_lead_days"] is None
    assert cal["estimated_max_lead_days"] == max(s["lead_days"] for s in DISEASE_GRAPH["Ebola"]["chain"])


def test_verify_chain_lead_time_ignores_non_declaration_milestones(isolated_db):
    """year_start·status_update처럼 '공식 선언'이 아닌 마일스톤만 있으면
    억지로 날짜를 만들지 않고 미검증으로 남아야 함."""
    import db as dbmod
    dbmod.upsert_timeline_event(
        "mers_test_2026", "MERS 테스트", "2026-01-01",
        "year_start", "감시 시작", "WHO", "who",
    )
    dbmod.upsert_timeline_event(
        "mers_test_2026", "MERS 테스트", "2026-06-25",
        "status_update", "현황 갱신", "WHO", "who",
    )

    result = verify_chain_lead_time("MERS")
    assert result["verified"] is False

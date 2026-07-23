"""소스별 헬스·신선도 추적(㉔) — '조용한 실패'가 실제로 눈에 보이는지,
연속 실패가 failing으로 승격되고 성공하면 리셋되는지, 그리고 소스가 죽는
순간을 딱 한 번만 잡아 반복 통보를 막는지 확인."""
from __future__ import annotations
import pytest

from algorithms import source_health as sh


@pytest.fixture(autouse=True)
def isolated_health_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sh, "HEALTH_FILE", tmp_path / "source_health.json")


def test_success_records_last_success_and_resets_streak():
    sh.record_source_result("KDCA", ok=False)
    sh.record_source_result("KDCA", ok=False)
    sh.record_source_result("KDCA", ok=True)

    report = sh.source_health_report()
    kdca = next(s for s in report["sources"] if s["source"] == "KDCA")
    assert kdca["consecutive_failures"] == 0
    assert kdca["status"] == "ok"
    assert kdca["last_success_at"] is not None


def test_consecutive_failures_escalate_to_failing():
    for _ in range(sh.FAILING_STREAK):
        sh.record_source_result("Naver", ok=False)

    report = sh.source_health_report()
    naver = next(s for s in report["sources"] if s["source"] == "Naver")
    assert naver["status"] == "failing"
    assert "Naver" in report["degraded_sources"]


def test_record_cycle_marks_none_valued_source_as_failure():
    result = {"kdca_weekly": {"MERS": {}}, "naver_flu_ratio": None}
    key_map = {"KDCA": "kdca_weekly", "Naver": "naver_flu_ratio"}
    sh.record_cycle(result, key_map)

    report = sh.source_health_report()
    by_source = {s["source"]: s for s in report["sources"]}
    assert by_source["KDCA"]["status"] == "ok"
    assert by_source["Naver"]["consecutive_failures"] == 1


def test_record_cycle_reports_source_only_when_it_crosses_failing_boundary():
    result = {"naver_flu_ratio": None}
    key_map = {"Naver": "naver_flu_ratio"}

    # FAILING_STREAK 도달 직전까지는 newly_failing이 비어있어야 함
    for _ in range(sh.FAILING_STREAK - 1):
        assert sh.record_cycle(result, key_map) == []
    # 경계를 넘는 바로 그 주기에만 1회 보고
    assert sh.record_cycle(result, key_map) == ["Naver"]
    # 이후 계속 실패해도 다시 보고하지 않음(반복 통보 방지)
    assert sh.record_cycle(result, key_map) == []


def test_recovery_after_failing_resets_and_reports_ok():
    result_fail = {"naver_flu_ratio": None}
    result_ok = {"naver_flu_ratio": 55.0}
    key_map = {"Naver": "naver_flu_ratio"}
    for _ in range(sh.FAILING_STREAK):
        sh.record_cycle(result_fail, key_map)
    sh.record_cycle(result_ok, key_map)

    report = sh.source_health_report()
    naver = next(s for s in report["sources"] if s["source"] == "Naver")
    assert naver["status"] == "ok"
    assert naver["consecutive_failures"] == 0
    assert "Naver" not in report["degraded_sources"]


def test_empty_report_when_nothing_tracked():
    report = sh.source_health_report()
    assert report["sources"] == []
    assert report["degraded_sources"] == []
    assert report["total_tracked"] == 0

"""소스별 헬스·신선도 추적(㉔) — '조용한 실패'가 실제로 눈에 보이는지,
연속 실패가 failing으로 승격되고 성공하면 리셋되는지, 그리고 소스가 죽는
순간을 딱 한 번만 잡아 반복 통보를 막는지 확인."""
from __future__ import annotations
import datetime as dt

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


# ── 지속 통보 회귀 (KDCA 2026-08-13 장애) ──────────────────────────────
# 예전엔 '3회째 실패' 순간에만 통보가 나가서, 소스가 나흘·93회를 죽어도 알림은
# 나흘 전 1건뿐이었다. 아래는 "죽어있는 동안 계속 알리고, 살아나면 알린다"를 고정.

def _fail_until_failing(source="KDCA"):
    for _ in range(sh.FAILING_STREAK):
        sh.record_source_result(source, ok=False)


def test_degraded_source_is_reported_until_notified():
    _fail_until_failing()
    pending = sh.pending_notifications()
    assert [d["source"] for d in pending["degraded"]] == ["KDCA"]
    assert pending["degraded"][0]["status"] == "failing"
    assert pending["degraded"][0]["consecutive_failures"] == sh.FAILING_STREAK


def test_no_duplicate_notification_within_renotify_window():
    """방금 알렸으면 다음 주기엔 조용해야 한다(매시간 스팸 방지)."""
    _fail_until_failing()
    sh.mark_notified(["KDCA"])
    sh.record_source_result("KDCA", ok=False)      # 계속 실패 중
    assert sh.pending_notifications()["degraded"] == []


def test_renotifies_after_window_elapses():
    """★핵심★ 아직 죽어있으면 RENOTIFY_HOURS 뒤에 다시 울려야 한다.
    이게 없어서 나흘간 아무도 몰랐다."""
    _fail_until_failing()
    sh.mark_notified(["KDCA"])
    raw = sh._load_raw()
    stale_stamp = sh._now() - dt.timedelta(hours=sh.RENOTIFY_HOURS + 1)
    raw["KDCA"]["last_notified_at"] = stale_stamp.isoformat()
    sh._save_raw(raw)

    sh.record_source_result("KDCA", ok=False)
    assert [d["source"] for d in sh.pending_notifications()["degraded"]] == ["KDCA"]


def test_recovery_is_notified_once_then_quiet():
    _fail_until_failing()
    sh.mark_notified(["KDCA"])
    sh.record_source_result("KDCA", ok=True)

    pending = sh.pending_notifications()
    assert pending["recovered"] == ["KDCA"]
    assert pending["degraded"] == []

    sh.mark_notified(["KDCA"])                      # 복구 통보 완료
    assert sh.pending_notifications()["recovered"] == []


def test_healthy_source_never_notified():
    sh.record_source_result("CIDRAP", ok=True)
    pending = sh.pending_notifications()
    assert pending["degraded"] == [] and pending["recovered"] == []


def test_collector_silent_hours_is_none_when_nothing_recorded():
    assert sh.collector_silent_hours() is None


def test_collector_silent_hours_tracks_last_activity():
    """데드맨 스위치 — collector가 통째로 멈추면 소스별 알림은 아예 안 돈다.
    그 경우를 /api/status 쪽에서 잡을 수 있게 '마지막 활동 이후 시간'을 낸다."""
    sh.record_source_result("KDCA", ok=True)
    assert sh.collector_silent_hours() < 1

    raw = sh._load_raw()
    raw["KDCA"]["last_success_at"] = (sh._now() - dt.timedelta(hours=30)).isoformat()
    sh._save_raw(raw)
    assert sh.collector_silent_hours() >= 29


# ── 제3상태 no_data (2026-08-18) ────────────────────────────────────────
# 예전엔 상태가 성공/실패 둘뿐이라 두 가지 거짓말이 동시에 일어났다:
#  ① 위키 404(집계 지연 = 정상)를 실패로 세서 상시 degraded → 정상인 걸 매일 경보
#  ② OpenSky가 '공항 0개·항공편 None' 껍데기를 줘도 dict라서 229회 연속 성공으로 기록
#     → "21/21 정상"이 실제보다 부풀려짐(죽은 소스가 살아있다고 보고됨)

def test_no_data_is_not_a_failure():
    """정상 지연은 실패가 아니다 — 연속실패를 올리지도, 리셋을 막지도 않는다."""
    sh.record_source_result("Wikipedia_Ebola", ok=False)
    sh.record_source_result("Wikipedia_Ebola", ok=False, no_data=True)

    report = sh.source_health_report()
    row = report["sources"][0]
    assert row["status"] == "no_data"
    assert row["consecutive_failures"] == 0          # 실패 카운터가 리셋됨
    assert "Wikipedia_Ebola" not in report["degraded_sources"]
    assert report["no_data_sources"] == ["Wikipedia_Ebola"]


def test_no_data_never_triggers_telegram():
    """★핵심★ 정상 지연으로 매일 알림이 울리면 캡틴이 알림을 무시하게 된다."""
    for _ in range(10):
        sh.record_source_result("Wikipedia_Ebola", ok=False, no_data=True)
    pending = sh.pending_notifications()
    assert pending["degraded"] == [] and pending["recovered"] == []


def test_no_data_excluded_from_healthy_count():
    """no_data는 '정상'에 안 들어간다 — 21/21이 부풀려지지 않게."""
    sh.record_source_result("CIDRAP", ok=True)
    # 예시는 살아있는 소스로 — 은퇴한 이름(Mobility)은 리포트에서 필터되어
    # 이 테스트가 조용히 아무것도 안 세게 된다.
    sh.record_source_result("GroqWatch", ok=False, no_data=True)
    report = sh.source_health_report()
    assert report["total_tracked"] == 2
    assert report["healthy_count"] == 1              # 2가 아니라 1
    assert report["no_data_sources"] == ["GroqWatch"]


def test_record_cycle_treats_declared_no_data_key_as_no_data():
    """collector가 mark_no_data로 표시한 키는 실패가 아니라 no_data."""
    result = {"wiki_ebola_daily": None, "_no_data_keys": ["wiki_ebola_daily"]}
    sh.record_cycle(result, {"Wikipedia_Ebola": "wiki_ebola_daily"})
    assert sh.source_health_report()["no_data_sources"] == ["Wikipedia_Ebola"]


def test_record_cycle_catches_hollow_payload():
    """★핵심★ 예외는 안 났지만 알맹이가 빈 값을 성공으로 세면 안 된다(OpenSky 사례)."""
    # 껍데기의 원형은 OpenSky 였다(공항 0개·항공편 None 을 담은 dict). 그 소스는
    # 2026-08-28 에 추적에서 빠졌으므로 같은 '모든 값이 None' 모양을 살아있는
    # 소스로 재현한다 — 검사하는 것은 _is_empty 의 일반 동작이다.
    result = {"groq_pulse": {"pulse": None, "tokens_used": None}}
    sh.record_cycle(result, {"GroqWatch": "groq_pulse"})
    report = sh.source_health_report()
    assert report["healthy_count"] == 0
    assert report["no_data_sources"] == ["GroqWatch"]


def test_zero_is_real_data_not_missing():
    """0건은 진짜 정보다 — 조용한 시기를 장애로 오인하면 안 된다."""
    result = {"kdca_weekly": {"콜레라": 0}, "pubmed_ebola_count": 0}
    sh.record_cycle(result, {"KDCA": "kdca_weekly", "PubMed": "pubmed_ebola_count"})
    report = sh.source_health_report()
    assert report["healthy_count"] == 2
    assert report["no_data_sources"] == []


def test_empty_container_counts_as_no_data():
    assert sh._is_empty({}) and sh._is_empty([]) and sh._is_empty("")
    assert not sh._is_empty(0) and not sh._is_empty(False) and not sh._is_empty({"a": 1})

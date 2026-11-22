"""서버 밖 생존 감시. 서버가 죽으면 서버 안의 로그·알림도 같이 조용해지므로 GitHub Actions 에서
바깥으로 본다. 고정하는 것: ① 서버 무응답·주기 멈춤·사이트 무응답을 구분해 말한다 ② 첫 주기 전
(collector_silent_hours=None)은 고장으로 세지 않는다 ③ 문제가 있으면 종료 코드 1(텔레그램 없음, 2026-11-22)
④ 워크플로가 이 스크립트를 실제로 부른다.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("liveness_check", ROOT / "scripts" / "liveness_check.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)

OK_HEALTH = (200, json.dumps({"status": "ok"}))
FRESH = (200, json.dumps({"source_health": {"collector_silent_hours": 0.4}}))
SITE_OK = (200, "<html>")


def test_all_good_is_no_problem():
    assert lc.evaluate(OK_HEALTH, FRESH, SITE_OK) == []


def test_server_down_is_reported_and_status_not_double_counted():
    probs = lc.evaluate((None, "URLError"), (None, "URLError"), SITE_OK)
    assert probs == ["운영 서버 응답 없음 (/health URLError)"]


def test_stale_snapshot_means_scheduler_stalled():
    stale = (200, json.dumps({"source_health": {"collector_silent_hours": 3.2}}))
    assert lc.evaluate(OK_HEALTH, stale, None) == ["매시 주기 멈춤 의심 — 수집 마지막 기록 3.2시간 전"]


def test_one_late_cycle_is_not_a_stall():
    late = (200, json.dumps({"source_health": {"collector_silent_hours": lc.STALL_HOURS}}))
    assert lc.evaluate(OK_HEALTH, late, None) == []


def test_unreadable_status_is_reported():
    assert lc.evaluate(OK_HEALTH, (502, ""), None) == ["운영 상태를 못 읽음 (/api/status HTTP 502)"]


def test_before_first_cycle_is_not_a_failure():
    assert lc.evaluate(OK_HEALTH, (200, json.dumps({"source_health": {"collector_silent_hours": None}})), None) == []


def test_site_down_is_separate():
    assert lc.evaluate(OK_HEALTH, FRESH, (503, "")) == ["웹사이트 응답 없음 (HTTP 503)"]




def test_main_returns_nonzero_when_a_problem_is_seen(monkeypatch):
    """텔레그램을 뺀 뒤(2026-11-22) 알림은 종료 코드뿐 — 문제가 있으면 1, 없으면 0."""
    monkeypatch.setattr(lc, "_get", lambda url, **k: (502, ""))
    assert lc.main(["--api", "https://x"]) == 1

    def ok(url, **k):
        if url.endswith("/health"):
            return OK_HEALTH
        return FRESH
    monkeypatch.setattr(lc, "_get", ok)
    assert lc.main(["--api", "https://x"]) == 0


def test_workflow_calls_the_script_without_telegram():
    wf = (ROOT.parent / ".github" / "workflows" / "liveness.yml").read_text(encoding="utf-8")
    assert "scripts/liveness_check.py" in wf and "cron:" in wf
    # 예약 실행이 빠지므로(10-20 관측) 시간당 두 번 건다.
    assert wf.count("- cron:") == 2
    # 텔레그램 흔적이 없어야 한다.
    assert "TELEGRAM" not in wf and "--prior-failures" not in wf

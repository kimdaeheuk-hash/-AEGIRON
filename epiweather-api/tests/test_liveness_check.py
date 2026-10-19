"""서버 밖 생존 감시 (2026-10-19, 캡틴 승인 ①).

BAIKAL 운영 알림은 서버 안에서 나간다 — 서버가 죽으면 같이 조용해진다. 이 스크립트는
GitHub Actions 에서 바깥으로 본다. 고정하는 것: ① 서버 무응답·주기 멈춤·사이트 무응답을 구분해
말한다 ② 첫 관측 전(available=False)은 고장으로 세지 않는다 ③ 바뀐 순간만 보내고, 계속되면
6회마다, 복구도 한 번 ④ 값 이스케이프 ⑤ 워크플로가 이 스크립트를 실제로 부른다.
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
FRESH = (200, json.dumps({"available": True, "stale": False, "snapshot_age_minutes": 22}))
SITE_OK = (200, "<html>")


def test_all_good_is_no_problem():
    assert lc.evaluate(OK_HEALTH, FRESH, SITE_OK) == []


def test_server_down_is_reported_and_baikal_not_double_counted():
    probs = lc.evaluate((None, "URLError"), (None, "URLError"), SITE_OK)
    assert probs == ["운영 서버 응답 없음 (/health URLError)"]


def test_stale_snapshot_means_scheduler_stalled():
    stale = (200, json.dumps({"available": True, "stale": True, "snapshot_age_minutes": 190}))
    assert lc.evaluate(OK_HEALTH, stale, None) == ["매시 주기 멈춤 의심 — BAIKAL 마지막 관측 190분 전"]


def test_before_first_cycle_is_not_a_failure():
    assert lc.evaluate(OK_HEALTH, (200, json.dumps({"available": False})), None) == []


def test_site_down_is_separate():
    assert lc.evaluate(OK_HEALTH, FRESH, (503, "")) == ["웹사이트 응답 없음 (HTTP 503)"]


def test_send_only_on_change_then_every_six_and_recovery_once():
    probs = ["운영 서버 응답 없음 (/health HTTP 502)"]
    first = lc.decide(probs, prior_failures=0)
    assert first.startswith("🔴 <b>외부 생존 감시: 이상</b>") and "감염병 경보가 아님" in first
    assert lc.decide(probs, prior_failures=1) is None
    assert lc.decide(probs, prior_failures=4) is None
    assert "6회 연속 이상" in lc.decide(probs, prior_failures=5)
    assert lc.decide([], prior_failures=3).startswith("🟢 <b>외부 생존 감시: 복구</b>")
    assert lc.decide([], prior_failures=0) is None


def test_problem_text_is_escaped():
    text = lc.decide(["웹사이트 응답 없음 (<b>&)"], 0)
    assert "<b>&)" not in text and "&lt;b&gt;&amp;)" in text


def test_workflow_calls_the_script_hourly_with_prior_failures():
    wf = (ROOT.parent / ".github" / "workflows" / "liveness.yml").read_text(encoding="utf-8")
    assert "scripts/liveness_check.py" in wf and "--prior-failures" in wf
    assert "cron:" in wf and "TELEGRAM_BOT_TOKEN" in wf

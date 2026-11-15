"""응답 캐시 — 저장본 즉시 + 만료 시 뒤에서 갱신 (2026-11-15 운영 HTTP 로그: risk-index 45초·alerts 45초)."""
from __future__ import annotations

import ast
import threading
import time
from pathlib import Path

from algorithms import response_cache as rc


def test_first_call_computes_then_serves_stored():
    calls = []
    out1 = rc.swr("k", 60, lambda: calls.append(1) or {"v": 1})
    out2 = rc.swr("k", 60, lambda: calls.append(1) or {"v": 2})
    assert calls == [1]
    assert out1["v"] == 1 and out2["v"] == 1
    assert out2["response_cache"]["stale"] is False


def test_expired_serves_stale_immediately_and_refreshes_in_background(monkeypatch):
    rc.swr("k", 60, lambda: {"v": 1})
    now = time.time()
    monkeypatch.setattr(rc.time, "time", lambda: now + 120)
    started = threading.Event()
    release = threading.Event()

    def slow():
        started.set()
        release.wait(2)
        return {"v": 2}

    out = rc.swr("k", 60, slow)
    assert out["v"] == 1 and out["response_cache"]["stale"] is True  # 기다리지 않는다
    assert started.wait(2)
    release.set()
    for _ in range(50):
        if rc._STORE["k"][1].get("v") == 2:
            break
        time.sleep(0.02)
    assert rc._STORE["k"][1]["v"] == 2


def test_failure_is_not_stored():
    try:
        rc.swr("k", 60, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    except RuntimeError:
        pass
    assert "k" not in rc._STORE  # 실패가 ttl 동안 답이 되면 안 된다


def test_seed_and_invalidate():
    rc.seed("pred:a", {"x": 1})
    rc.seed("pred:b", {"x": 2})
    rc.seed("other", {"x": 3})
    rc.invalidate("pred:")
    assert set(rc._STORE) == {"other"}


def test_non_dict_values_are_returned_as_is():
    assert rc.swr("list", 60, lambda: [1, 2]) == [1, 2]


def _func(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def test_slow_endpoints_are_wired_to_the_cache():
    """운영에서 8초 넘게 걸린 조회 API 가 캐시를 거친다 — 누가 다시 직접 계산으로 되돌리면 깨진다."""
    tree = ast.parse(Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8"))
    for name in ("risk_index", "alerts", "status", "negative_space", "unexplained_signals", "polar_watch",
                 "climate_signals", "land_signals", "deforestation_signals", "risk_quantification",
                 "lead_time_ledger", "extracted_signals", "get_predictions"):
        src = ast.unparse(_func(tree, name))
        assert "response_cache.swr(" in src, name


def test_alert_cycle_seeds_alerts_and_prewarms():
    tree = ast.parse(Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8"))
    src = ast.unparse(_func(tree, "_run_alert_cycle")) if any(
        isinstance(n, ast.FunctionDef) and n.name == "_run_alert_cycle" for n in ast.walk(tree)) else ""
    if not src:  # async def
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_run_alert_cycle")
        src = ast.unparse(node)
    assert "response_cache.seed('alerts', result)" in src
    assert "_prewarm_after_cycle()" in src


def test_daily_brief_serves_todays_archive_without_generating(monkeypatch):
    import datetime as dt

    from fastapi.testclient import TestClient

    import main
    from algorithms import daily_brief

    main._DAILY_BRIEF_CACHE.clear()
    today = dt.date.today().isoformat()  # noqa: DTZ011 — 엔드포인트와 같은 기준(로컬 날짜)
    monkeypatch.setattr(main.db, "get_daily_brief", lambda d, lang="ko": {"brief_date": d, "lang": lang, "archived": True})

    def boom(*a, **k):
        raise AssertionError("보관본이 있는데 새로 생성했다")

    monkeypatch.setattr(daily_brief, "generate_daily_brief", boom)
    r = TestClient(main.app).get("/api/daily-brief?lang=ko")
    assert r.status_code == 200
    assert r.json()["archived"] is True and r.json()["brief_date"] == today
    main._DAILY_BRIEF_CACHE.clear()


def test_ai_infer_fast_mode_returns_decision_tree_without_llm(monkeypatch):
    """fast=true 는 LLM 을 부르지 않는다 — 화면이 즉시 그릴 1단계(캡틴: '추론도 엄청 늦게 떠')."""
    from fastapi.testclient import TestClient

    import main
    from algorithms import ai_inference

    monkeypatch.setenv("META_MODEL_API_KEY", "k")
    monkeypatch.setenv("EPIWEATHER_API_KEY", "test-key")

    def boom(*a, **k):
        raise AssertionError("fast 모드에서 LLM 을 불렀다")

    monkeypatch.setattr(ai_inference, "run_ai_inference", boom)
    monkeypatch.setattr(main, "_infer_cache_get", lambda h: None)
    headers = {"X-API-Key": "test-key"}
    r = TestClient(main.app).post(
        "/api/ai/infer", json={"rt": 1.4, "arrival_day": 20, "threat": "novel", "fast": True}, headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "decision_tree_fast"
    assert body["llm_pending"] is True and body["llm_analysis"] is None
    assert body["decision_tree"]

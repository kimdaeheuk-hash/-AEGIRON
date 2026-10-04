"""2026-10-04 #51 배포 직후 프로덕션 로그가 알려준 것들의 수리.

관측 (13:39 UTC, 배포 f700a7d6)

    🧮 social_cholera: 관측값 5 · 과거 평균 1.7306 · 2.49σ (문턱 2.0σ) → 통과
    🧮 social_dengue : 관측값 12 · 과거 평균 5.0578 · 3.09σ (문턱 2.0σ) → 통과
    🌐 무역 스캔: masks 2/6달 → 사용 불가(HTTP 429×4) · gloves 2/6달 … · 부분 스캔 3/3 · 캐시 안 함

1. 2σ 문턱만으로는 소표본 사회 신호가 critical 로 폰을 울리는 걸 못 막았다 → 경보 점수 상한.
2. UN Comtrade 가 429 로 스캔을 막았는데 재시도 없이 그 달을 버렸다 → 429 에만 기다렸다 재시도.
3. `approved_products` 기준 파일이 주간 타이머 때문에 며칠째 없다(추정) → 없는 것만 따로 받는다.
4. 예측의 국가 이름이 한글/영문이 섞여 채점이 못 알아볼 수 있다 → ISO3 로도 맞춘다.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from algorithms import alerts as alerts_mod
from algorithms import comtrade_signals as cs
from algorithms import reference_snapshots as rs
from algorithms.prediction_resolver import MATCH_COUNTRY, MATCH_FULL, MATCH_NONE, match_kind
from algorithms.signal_metrics import (COUNT_NOISE_ALERT_CAP, cap_count_noise_score,
                                       count_significance)


# ── 1. 소표본 사회 신호 경보 점수 상한 ───────────────────────

def test_observed_values_pass_the_sigma_gate_so_the_gate_alone_was_not_enough():
    """프로덕션 값 그대로 — 문턱을 통과한다. 상한이 필요한 이유를 시험이 기억한다."""
    assert count_significance(5, 1.7306) >= 2.0
    assert count_significance(12, 5.0578) >= 2.0


def test_cap_is_below_high_tier():
    assert COUNT_NOISE_ALERT_CAP < alerts_mod.HIGH


def test_cap_applies_only_to_count_noise_metrics():
    assert cap_count_noise_score("social_cholera", 90.0) == COUNT_NOISE_ALERT_CAP
    assert cap_count_noise_score("social_dengue", 87.6) == COUNT_NOISE_ALERT_CAP
    assert cap_count_noise_score("kdca_weekly_total", 90.0) == 90.0     # 공식 지표는 그대로
    assert cap_count_noise_score("social_cholera", 60.0) == 60.0        # 이미 낮으면 안 건드린다


def _gai(metric, latest, mean, score):
    return {"gai": 10.0, "layers": {"behavioral": {
        "label": "행동신호", "weight": 0.2, "score": score,
        "metrics": [{"metric": metric, "latest": latest, "baseline_mean": mean,
                     "raw_score": 100.0, "trust": 0.9, "trusted_score": score}]}}}


def _collect(monkeypatch, gai):
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: gai)
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return alerts_mod.collect_candidate_alerts(
            "2026-10-04", {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}})


def test_social_candidate_cannot_reach_high_even_after_passing_the_gate(monkeypatch, capsys):
    """10-03 의 모양 — 평균 1.73 에서 5명(2.49σ)은 문턱을 통과하지만 critical 이 되지 않는다."""
    out = _collect(monkeypatch, _gai("social_cholera", 5, 1.7306, 90.0))
    cand = [c for c in out if c["source"].endswith("social_cholera")]
    assert len(cand) == 1                                  # 후보로는 남는다 — 화면에는 뜬다
    assert cand[0]["score"] == COUNT_NOISE_ALERT_CAP
    assert alerts_mod.classify_tier(cand[0]["score"]) == "medium"
    assert any("제한" in e for e in cand[0]["evidence"])   # 깎은 사실이 근거에 남는다
    assert "🧢" in capsys.readouterr().out                 # 로그에도 남는다


def test_official_metric_is_not_capped(monkeypatch):
    out = _collect(monkeypatch, _gai("kdca_weekly_total", 900, 100.0, 95.0))
    cand = [c for c in out if c["source"].endswith("kdca_weekly_total")]
    assert cand[0]["score"] == 95.0


def test_cap_does_not_change_the_index_scores():
    """지수는 측정값이다 — 상한은 경보 점수에만 걸린다(gai 모듈을 안 건드렸다)."""
    import inspect
    from algorithms import gai
    assert "cap_count_noise_score" not in inspect.getsource(gai)


# ── 2. 429 재시도 ───────────────────────────────────────────

def _http_error(status, retry_after=None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"Retry-After": retry_after} if retry_after is not None else {}
    err = requests.HTTPError(f"{status}")
    err.response = resp
    return err


def _ok_response(rows=3):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"data": [{"reporterISO": f"C{i}", "primaryValue": 1.0} for i in range(rows)]}
    return r


def _failing_then_ok(n_fail, status=429, retry_after=None):
    bad = MagicMock()
    bad.raise_for_status.side_effect = _http_error(status, retry_after)
    return [bad] * n_fail + [_ok_response()]


def test_429_waits_and_then_succeeds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(cs, "_sleep", lambda s: sleeps.append(s))
    notes: dict = {}
    with patch.object(cs.requests, "get", side_effect=_failing_then_ok(1)):
        out = cs.fetch_public_month("630790", "202608", notes=notes)
    assert out is not None and len(out) == 3
    assert sleeps == [cs.RATE_LIMIT_BACKOFF_SEC]
    assert notes["retried_429"] == 1
    assert "reasons" not in notes                  # 결국 성공했으니 실패 사유는 없다


def test_429_gives_up_after_the_retry_limit_and_records_the_reason(monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: None)
    notes: dict = {}
    with patch.object(cs.requests, "get", side_effect=_failing_then_ok(10)) as g:
        out = cs.fetch_public_month("630790", "202608", notes=notes)
    assert out is None
    assert g.call_count == cs.RATE_LIMIT_RETRIES + 1
    assert notes["reasons"] == {"HTTP 429": 1}     # 포기한 사실은 숨기지 않는다


def test_retry_after_header_is_honored_but_capped(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(cs, "_sleep", lambda s: sleeps.append(s))
    with patch.object(cs.requests, "get", side_effect=_failing_then_ok(1, retry_after="3")):
        cs.fetch_public_month("630790", "202608", notes={})
    assert sleeps == [3.0]
    sleeps.clear()
    with patch.object(cs.requests, "get", side_effect=_failing_then_ok(1, retry_after="9999")):
        cs.fetch_public_month("630790", "202608", notes={})
    assert sleeps == [cs.RATE_LIMIT_MAX_WAIT_SEC]


def test_non_429_failures_are_not_retried(monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: (_ for _ in ()).throw(AssertionError("기다리면 안 됨")))
    for status in (500, 503, 403):
        with patch.object(cs.requests, "get", side_effect=_failing_then_ok(5, status=status)) as g:
            assert cs.fetch_public_month("630790", "202608", notes={}) is None
        assert g.call_count == 1


def test_wait_budget_bounds_total_sleeping_per_product(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(cs, "_sleep", lambda s: sleeps.append(s))
    notes: dict = {}
    always_429 = MagicMock()
    always_429.raise_for_status.side_effect = _http_error(429, "20")
    with patch.object(cs.requests, "get", return_value=always_429):
        for period in ("202601", "202602", "202603", "202604", "202605", "202606"):
            cs.fetch_public_month("630790", period, notes=notes)
    assert sum(sleeps) <= cs.RATE_LIMIT_BUDGET_SEC
    assert notes["retried_429"] >= 1


def test_series_fetch_pauses_between_months(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(cs, "_sleep", lambda s: sleeps.append(s))
    with patch.object(cs.requests, "get", return_value=_ok_response()):
        cs.fetch_public_series("630790", months=4, notes={})
    assert sleeps == [cs.REQUEST_GAP_SEC] * 3      # 첫 달 앞에서는 기다리지 않는다


def test_scan_line_names_the_429_retries():
    scan = {"products": {"masks": {"data_available": True, "countries_observed": 90,
                                   "fetch": {"months_total": 6, "months_ok": 6, "retried_429": 2}}}}
    cs._record_call(scan, scanned_at=time.time(), cache_hit=False, cached=True)
    assert "429 재시도 2회" in cs.trade_scan_line()


# ── 3. 없는 기준 스냅샷 ─────────────────────────────────────

def test_refresh_missing_only_touches_absent_snapshots(monkeypatch):
    called: list[str] = []

    def fake_status(name, now=None):
        return {"present": name != "approved_products"}

    monkeypatch.setattr(rs, "snapshot_status", fake_status)
    monkeypatch.setattr(rs, "refresh", lambda name, now=None: called.append(name) or
                        {"name": name, "refreshed": True, "record_count": 7, "snapshot_date": "2026-10-04",
                         "reason": None})
    out = rs.refresh_missing()
    assert called == ["approved_products"]
    assert out["refreshed"][0]["name"] == "approved_products"


def test_refresh_missing_does_nothing_when_all_present(monkeypatch):
    monkeypatch.setattr(rs, "snapshot_status", lambda name, now=None: {"present": True})
    monkeypatch.setattr(rs, "refresh", lambda *a, **k: pytest.fail("원본을 부르면 안 됨"))
    assert rs.refresh_missing() == {"refreshed": []}


def test_scheduler_hook_is_wired_at_startup_and_hourly():
    """만들어만 두고 아무도 안 부르는 층 방지 — 시작 직후와 매시간 두 군데서 부른다."""
    import ast
    import inspect
    import main
    tree = ast.parse(inspect.getsource(main._scheduler_loop))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "_maybe_refresh_missing_snapshots"]
    assert len(calls) == 2


def test_scheduler_hook_has_a_cooldown_and_logs_the_reason(monkeypatch):
    import asyncio
    import main
    import collector
    logged: list[str] = []
    monkeypatch.setattr(collector, "log", lambda m: logged.append(m))
    monkeypatch.setattr(main, "_last_missing_snapshot_try", None)
    monkeypatch.setattr(rs, "snapshot_status", lambda name, now=None: {"present": False})
    monkeypatch.setattr(rs, "refresh_missing", lambda now=None: {"refreshed": [
        {"name": "approved_products", "refreshed": False, "reason": "수집 실패 — Timeout"}]})
    asyncio.run(main._maybe_refresh_missing_snapshots())
    assert any("approved_products" in m and "수집 실패 — Timeout" in m for m in logged)
    n = len(logged)
    asyncio.run(main._maybe_refresh_missing_snapshots())   # 쿨다운 안 — 다시 안 부른다
    assert len(logged) == n


# ── 4. 예측 국가 이름 ───────────────────────────────────────

def _event(name):
    return {"event_id": "evt-1", "event_name": name}


def test_korean_prediction_country_matches_english_event():
    p = {"country": "콩고민주공화국", "disease": "에볼라"}
    ev = _event("Ebola outbreak in Democratic Republic of the Congo")
    assert match_kind(p, ev) == MATCH_COUNTRY       # 국가는 알아본다 — 질병 표기(에볼라/Ebola)는 별개 문제


def test_english_prediction_country_matches_korean_event():
    p = {"country": "Cambodia", "disease": "h5n1"}
    assert match_kind(p, _event("캄보디아 H5N1 조류인플루엔자")) == MATCH_FULL


def test_other_country_still_does_not_match():
    p = {"country": "Cambodia", "disease": "h5n1"}
    assert match_kind(p, _event("Marburg Rwanda 2024")) == MATCH_NONE


def test_unknown_name_is_not_guessed():
    p = {"country": "Atlantis", "disease": "flu"}
    assert match_kind(p, _event("Atlantis flu")) == MATCH_FULL       # 글자 겹침은 전처럼 동작
    assert match_kind({"country": "아틀란티스", "disease": "flu"}, _event("Atlantis flu")) == MATCH_NONE


def test_country_only_match_never_becomes_correct_via_iso3():
    """ISO3 경로는 국가만 넓힌다 — 질병이 안 겹치면 여전히 correct 가 아니다."""
    p = {"country": "캄보디아", "disease": "뎅기열"}
    assert match_kind(p, _event("Cambodia H5N1 avian influenza")) == MATCH_COUNTRY

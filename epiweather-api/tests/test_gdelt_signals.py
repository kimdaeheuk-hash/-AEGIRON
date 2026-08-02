"""GDELT 과거 커버리지 백테스트(㉟) — 타임라인 파싱, z-score 급증탐지, 그리고
정직성 플래그(뉴스 커버리지 프록시·재구성)가 맞는지 확인. 2017 이전 사건은
정직하게 미지원 표시. 실제 GDELT 호출은 mock(샌드박스 차단)."""
from __future__ import annotations
import datetime as dt
from unittest.mock import patch, MagicMock

from algorithms.gdelt_signals import (
    _parse_gdelt_date, fetch_coverage_timeline, detect_coverage_spike,
    gdelt_reconstruct_event, GDELT_MIN_DATE,
)


def test_parse_gdelt_date_various_formats():
    assert _parse_gdelt_date("20191201T000000Z") == dt.date(2019, 12, 1)
    assert _parse_gdelt_date("2019-12-01T00:00:00Z") == dt.date(2019, 12, 1)
    assert _parse_gdelt_date("garbage") is None


def _timeline_resp(points):
    payload = {"timeline": [{"data": [{"date": d, "value": v} for d, v in points]}]}
    r = MagicMock(status_code=200)
    r.json = lambda: payload
    return r


def test_fetch_coverage_timeline_parses_points():
    pts = [("20191101000000", 0.1), ("20191102000000", 0.2)]
    with patch("algorithms.gdelt_signals.requests.get", return_value=_timeline_resp(pts)):
        result = fetch_coverage_timeline("coronavirus wuhan", dt.date(2019, 11, 1), dt.date(2019, 12, 1))
    assert result == [(dt.date(2019, 11, 1), 0.1), (dt.date(2019, 11, 2), 0.2)]


def test_fetch_coverage_timeline_network_error_returns_none():
    with patch("algorithms.gdelt_signals.requests.get", side_effect=Exception("blocked")):
        assert fetch_coverage_timeline("q", dt.date(2019, 1, 1), dt.date(2019, 2, 1)) is None


def test_detect_coverage_spike_finds_first_zscore_breakout():
    # 앞 40%는 조용(≈0.1), 그다음 급증(0.9)
    base = [(dt.date(2019, 11, 1) + dt.timedelta(days=i), 0.1) for i in range(10)]
    spike = [(dt.date(2019, 11, 11) + dt.timedelta(days=i), 0.9) for i in range(10)]
    points = base + spike
    result = detect_coverage_spike(points)
    assert result == dt.date(2019, 11, 11)  # 급증 첫 날


def test_detect_coverage_spike_none_when_flat():
    points = [(dt.date(2019, 11, 1) + dt.timedelta(days=i), 0.1) for i in range(20)]
    assert detect_coverage_spike(points) is None


def test_reconstruct_event_computes_lead_days():
    # 선언일 12-31, 커버리지는 12-21부터 급증 → 10일 선행
    decl = dt.date(2019, 12, 31)
    base = [(decl - dt.timedelta(days=40) + dt.timedelta(days=i), 0.1) for i in range(30)]
    spike = [(dt.date(2019, 12, 21) + dt.timedelta(days=i), 0.9) for i in range(11)]
    with patch("algorithms.gdelt_signals.fetch_coverage_timeline", return_value=base + spike):
        result = gdelt_reconstruct_event("covid19_wuhan_2019", decl)
    assert result["available"] is True
    assert result["coverage_spiked"] is True
    assert result["coverage_spike_date"] == "2019-12-21"
    assert result["gdelt_lead_days"] == 10
    assert result["signal_source"] == "gdelt_coverage_volume"
    assert result["reconstruction"] is True


def test_reconstruct_event_unmapped_returns_unavailable():
    result = gdelt_reconstruct_event("unknown_event", dt.date(2020, 1, 1))
    assert result["available"] is False
    assert "쿼리 매핑" in result["reason"]


def test_reconstruct_event_pre_2017_honestly_unsupported():
    """GDELT DOC 2.0은 2017 이후만 — 그 이전 사건은 지어내지 않고 미지원 표시."""
    old = GDELT_MIN_DATE - dt.timedelta(days=1)
    result = gdelt_reconstruct_event("ebola_drc_2026", old)
    assert result["available"] is False
    assert "2017" in result["reason"]


def test_reconstruct_event_fetch_failure_flags_unavailable():
    with patch("algorithms.gdelt_signals.fetch_coverage_timeline", return_value=None):
        result = gdelt_reconstruct_event("covid19_wuhan_2019", dt.date(2019, 12, 31))
    assert result["available"] is False
    assert "조회 실패" in result["reason"]


# ── 속도제한·429 재시도 ───────────────────────────────────────────
def test_rate_limited_response_is_retried(monkeypatch):
    """★핵심 회귀★ GDELT는 '5초에 1회'를 요구하고 어기면 429를 준다. 재시도 없이
    None을 돌려주면 호출측이 '자료 없음'과 '속도초과'를 구분 못 해, 백필 16건 중
    14건이 조용히 비었다."""
    import algorithms.gdelt_signals as gs

    calls = []

    class Resp:
        def __init__(self, code): self.status_code = code
        def json(self):
            return {"timeline": [{"data": [{"date": "20240101T000000Z", "value": 1.0}]}]}

    def fake_get(url, **kw):
        calls.append(1)
        return Resp(429 if len(calls) < 3 else 200)

    monkeypatch.setattr(gs.requests, "get", fake_get)
    monkeypatch.setattr(gs.time, "sleep", lambda s: None)      # 테스트는 실제로 안 잔다
    monkeypatch.setattr(gs, "_gdelt_last_call", 0.0)
    out = gs.fetch_coverage_timeline("q", dt.date(2024, 1, 1), dt.date(2024, 2, 1))
    assert len(calls) == 3          # 429 두 번 받고 세 번째에 성공
    assert out and len(out) == 1


def test_persistent_rate_limit_gives_up_and_returns_none(monkeypatch):
    """계속 429면 무한재시도하지 않고 None — 호출측이 건너뛰도록."""
    import algorithms.gdelt_signals as gs

    class Resp:
        status_code = 429

    calls = []
    monkeypatch.setattr(gs.requests, "get", lambda url, **kw: (calls.append(1), Resp())[1])
    monkeypatch.setattr(gs.time, "sleep", lambda s: None)
    monkeypatch.setattr(gs, "_gdelt_last_call", 0.0)
    assert gs.fetch_coverage_timeline("q", dt.date(2024, 1, 1), dt.date(2024, 2, 1)) is None
    assert len(calls) == gs._GDELT_MAX_RETRIES


def test_throttle_enforces_minimum_interval(monkeypatch):
    """호출 간격이 실제로 벌어져야 한다 — 안 그러면 재시도만으로는 부족하다."""
    import algorithms.gdelt_signals as gs

    slept = []
    monkeypatch.setattr(gs.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(gs.time, "monotonic", lambda: 100.0)   # 시간이 안 흐른 상황
    monkeypatch.setattr(gs, "_gdelt_last_call", 100.0)
    gs._gdelt_throttle()
    assert slept and slept[0] >= gs._GDELT_MIN_INTERVAL_SEC - 0.01

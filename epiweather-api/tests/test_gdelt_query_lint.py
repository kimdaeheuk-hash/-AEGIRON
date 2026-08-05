"""GDELT 질의문 검증 + 실패 사유 구분.

왜 중요한가(실측): GDELT는 **질의문이 틀려도 HTTP 200**에 평문 안내를 돌려준다.
예전 구현은 그 예외를 통째로 삼켜 '자료 없음'과 똑같이 None을 반환했고, 그래서
백필 16건 중 2건이 "이 사건은 뉴스가 없었다"로 조용히 비어 있었다. 원인이 속도제한인
줄로 몇 시간 오해했고, 실제로는 질의문 오타 2건이었다:
  · `"Marburg" (Equatorial Guinea)` — 괄호는 OR 묶음에만 허용
  · `"mpox" OR "monkeypox" (Congo OR DRC)` — "mpox"가 5글자 미만 + OR 결합 오류
"""
from __future__ import annotations
import datetime as dt

import pytest

from algorithms.gdelt_signals import (
    lint_gdelt_query, fetch_coverage_detailed, _GDELT_MIN_PHRASE_LEN,
)
from algorithms import historical_outbreaks as ho


class _Resp:
    def __init__(self, status=200, text="", payload=None):
        self.status_code = status
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


# ── 린터 ──────────────────────────────────────────────────────────────
def test_lint_catches_parenthesis_without_or():
    """실제로 이 질의문이 조용히 실패했다."""
    problems = lint_gdelt_query('"Marburg" (Equatorial Guinea)')
    assert problems
    assert any("괄호" in p for p in problems)


def test_lint_catches_phrase_shorter_than_gdelt_minimum():
    """GDELT는 5글자 미만 구문을 거부한다 — `"mpox"`가 4글자라 질의 전체가 실패했다."""
    problems = lint_gdelt_query('"mpox" (Congo OR DRC)')
    assert any("5글자" in p or str(_GDELT_MIN_PHRASE_LEN) in p for p in problems)


def test_lint_catches_or_binding_error():
    """`A OR B (지역)`은 문법은 통과하지만 A가 지역 제한을 안 받는다 —
    전 세계 mpox 기사가 콩고 신호로 들어온다(조용한 의미 오류)."""
    problems = lint_gdelt_query('"monkeypox" OR "orthopox" (Congo OR DRC)')
    assert any("괄호 앞에 OR" in p for p in problems)


@pytest.mark.parametrize("query", [
    '"Lassa fever" Nigeria',
    '"Ebola" (Congo OR DRC)',
    '"Ebola" (Congo OR DRC OR Kivu)',
    '"monkeypox" (Congo OR DRC)',
    '"Marburg" "Equatorial Guinea"',
])
def test_lint_passes_valid_queries(query):
    assert lint_gdelt_query(query) == []


def test_every_registered_outbreak_query_is_valid():
    """★회귀★ 질의문은 사람이 손으로 적는 상수라 오타가 또 생긴다. 전수 검사로 고정."""
    bad = {o["event_id"]: lint_gdelt_query(o["gdelt_query"])
           for o in ho.OUTBREAKS if lint_gdelt_query(o["gdelt_query"])}
    assert not bad, f"질의문 오류: {bad}"


# ── 실패 사유 구분 ────────────────────────────────────────────────────
def test_bad_query_is_rejected_before_network(monkeypatch):
    """어차피 거부당할 질의문은 네트워크를 안 태운다."""
    called = []
    monkeypatch.setattr("algorithms.gdelt_signals.requests.get",
                        lambda *a, **k: called.append(1))
    out = fetch_coverage_detailed('"Marburg" (Equatorial Guinea)',
                                  dt.date(2023, 1, 1), dt.date(2023, 3, 1))
    assert out["error"] == "bad_query"
    assert out["points"] is None
    assert not called, "질의문 오류인데 GDELT를 호출했다"


def test_http_200_with_plain_text_is_not_no_data(monkeypatch):
    """★핵심 회귀★ 200 + 평문 = 질의문 거부다. 이걸 '자료 없음'으로 처리하면
    "이 사건은 뉴스가 없었다"는 정반대 결론이 나온다."""
    monkeypatch.setattr("algorithms.gdelt_signals._gdelt_throttle", lambda: None)
    monkeypatch.setattr(
        "algorithms.gdelt_signals.requests.get",
        lambda *a, **k: _Resp(200, "The specified phrase is too short.\n"))
    out = fetch_coverage_detailed('"valid phrase" Nigeria',
                                  dt.date(2023, 1, 1), dt.date(2023, 3, 1))
    assert out["error"] == "bad_query"
    assert out["error"] != "no_data"
    assert "too short" in out["detail"]


def test_rate_limited_is_distinguished_from_no_data(monkeypatch):
    """429는 '기다리면 되는 실패'라 '고쳐야 하는 실패'와 구분돼야 한다 —
    섞이면 잘못된 곳을 고치게 된다."""
    monkeypatch.setattr("algorithms.gdelt_signals._gdelt_throttle", lambda: None)
    monkeypatch.setattr("algorithms.gdelt_signals.time.sleep", lambda *_: None)
    monkeypatch.setattr("algorithms.gdelt_signals.requests.get",
                        lambda *a, **k: _Resp(429, "Please limit requests"))
    out = fetch_coverage_detailed('"Ebola" Uganda', dt.date(2023, 1, 1), dt.date(2023, 3, 1))
    assert out["error"] == "rate_limited"


def test_genuine_empty_timeline_reports_no_data(monkeypatch):
    """진짜 자료 없음은 no_data로 — 이건 고칠 것도 기다릴 것도 아니다."""
    monkeypatch.setattr("algorithms.gdelt_signals._gdelt_throttle", lambda: None)
    monkeypatch.setattr("algorithms.gdelt_signals.requests.get",
                        lambda *a, **k: _Resp(200, "{}", payload={"timeline": []}))
    out = fetch_coverage_detailed('"Ebola" Uganda', dt.date(2023, 1, 1), dt.date(2023, 3, 1))
    assert out["error"] == "no_data"


def test_successful_fetch_returns_points(monkeypatch):
    monkeypatch.setattr("algorithms.gdelt_signals._gdelt_throttle", lambda: None)
    payload = {"timeline": [{"data": [{"date": "20230115T000000Z", "value": 0.5},
                                      {"date": "20230108T000000Z", "value": 0.2}]}]}
    monkeypatch.setattr("algorithms.gdelt_signals.requests.get",
                        lambda *a, **k: _Resp(200, "{}", payload=payload))
    out = fetch_coverage_detailed('"Ebola" Uganda', dt.date(2023, 1, 1), dt.date(2023, 3, 1))
    assert out["error"] is None
    assert [d for d, _ in out["points"]] == [dt.date(2023, 1, 8), dt.date(2023, 1, 15)]


# ── maintain: 마지막 빈 사건을 끝까지 채우는가 ─────────────────────────
def test_maintain_keeps_filling_until_no_gaps_remain(monkeypatch):
    """★회귀★ 낭비를 막으려던 커버리지 기준(60%)이 **마무리까지 막고 있었다** —
    실측에서 15/16(94%)에 도달하자 maintain이 '기준 충족'으로 건너뛰어, 남은 1건을
    자동으로 메울 경로가 사라졌다. 남은 게 있으면 계속 시도해야 한다."""
    from algorithms import nowcast_backfill as nb
    ids = [o["event_id"] for o in ho.OUTBREAKS]
    monkeypatch.setattr(nb, "already_backfilled", lambda: set(ids[:-1]))   # 1건만 남음
    calls = {}
    monkeypatch.setattr(nb, "run_backfill",
                        lambda **kw: calls.update(kw) or {
                            "signals_created": 0, "event_coverage": 0.94,
                            "coverage_sufficient": True, "failure_reasons": {}})
    out = nb.maintain(max_events=1)
    assert out["action"] == "backfilled", "남은 사건이 있는데 건너뛰었다"
    assert out["remaining_before"] == [ids[-1]]


def test_maintain_stops_only_when_everything_is_covered(monkeypatch):
    """전부 채워졌으면 GDELT를 아예 부르지 않는다(비용 0)."""
    from algorithms import nowcast_backfill as nb
    monkeypatch.setattr(nb, "already_backfilled",
                        lambda: {o["event_id"] for o in ho.OUTBREAKS})
    called = []
    monkeypatch.setattr(nb, "run_backfill", lambda **kw: called.append(1))
    out = nb.maintain(max_events=4)
    assert out["action"] == "skipped"
    assert not called


def test_backfill_records_why_an_event_stayed_empty(monkeypatch):
    """'왜 비었는지'를 남기지 않으면 고칠 실패와 기다릴 실패를 구분 못 한다."""
    from algorithms import nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_detailed",
                        lambda *a, **k: {"points": None, "error": "rate_limited",
                                         "detail": "429"})
    reasons = {}
    n = nb.backfill_signals_for(ho.OUTBREAKS[0], reasons=reasons)
    assert n == 0
    assert reasons[ho.OUTBREAKS[0]["event_id"]]["error"] == "rate_limited"

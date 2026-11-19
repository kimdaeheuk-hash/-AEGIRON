"""429 는 한 종류가 아니다 — 본문에 적힌 '어느 한도인가' 를 건진다 (2026-11-19).

## 배경 (사고 기록)

11-15~19 닷새 동안 Open-Meteo 가 낮에 `429` 로 막혀 극지·기후·오지가 반나절씩 비었다.
#132 가 사유 집계를 넣어 **"한도다(장애가 아니다)"** 까지는 밝혔는데, 거기서 멈췄다:

    _record_failure(f"HTTP {resp.status_code}")   # ← 본문을 버렸다

그래서 **분·시간·일 중 어느 한도인지** 나흘째 몰랐다. 2026-08-25 의 교훈
("실패 이유를 버리면 고칠 수 없다")과 같은 자리, 한 겹 더 깊은 곳이다.

## 왜 이 한 줄이 처방을 가르는가

우리 호출량은 **하루 276회**(극지 8×24 + 기후 15×4 + 오지 6×4)다. 무료 티어는 그보다
한참 크다. 그러면 둘 중 하나다:

    "Daily …"     우리 양으로 일 한도에 닿을 수 없다 ⇒ 송신 IP를 남과 나눠 쓴다(전용 키)
    "Minutely …"  한 주기에 몰아 쏘는 모양이 문제다   ⇒ 간격만 벌리면 공짜로 해결된다

**처방이 정반대다.** 추측으로 유료 결제하지 않기 위한 시험이다.

## 집계 키를 쪼개지 않는다

사유가 없거나 JSON 이 아니면 `HTTP {코드}` 만 남긴다. 아무 글자나 키로 쓰면 같은 고장이
여러 줄로 쪼개져 집계가 거짓말을 한다 — 그리고 **못 읽은 것은 못 읽었다고 말해야 한다**
(없는 사유를 지어내지 않는다).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from algorithms import climate_signals
from algorithms.climate_signals import _REASON_MAX, _http_failure_reason

DAILY = "Daily API request limit exceeded. Please try again tomorrow."
MINUTELY = "Minutely API request limit exceeded. Please try again in one minute."


class _Resp:
    """Open-Meteo 응답 — 본문을 실어 보내는 모양."""

    def __init__(self, status: int, body: object = None, *, raises: bool = False):
        self.status_code = status
        self._body = body
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not JSON")
        return self._body


@pytest.fixture(autouse=True)
def _drain():
    climate_signals.pop_failure_reasons()
    yield
    climate_signals.pop_failure_reasons()


# ───────────────── 알맹이: 어느 한도인지 갈린다 ─────────────────

def test_daily_and_minutely_do_not_collapse_into_one_key():
    """★ 이 시험이 사고의 알맹이다 — 두 한도가 한 글자로 뭉개지면 처방을 못 고른다."""
    daily = _http_failure_reason(_Resp(429, {"error": True, "reason": DAILY}))
    minutely = _http_failure_reason(_Resp(429, {"error": True, "reason": MINUTELY}))

    assert daily != minutely
    assert "Daily" in daily and "Minutely" in minutely
    assert daily.startswith("HTTP 429")       # 코드도 그대로 보인다
    assert minutely.startswith("HTTP 429")


def test_fetch_climate_records_the_reason_not_just_the_code():
    """배선 — `fetch_climate` 가 실제로 본문을 읽는가(계약은 그대로 None)."""
    with patch("algorithms.climate_signals.requests.get",
               return_value=_Resp(429, {"error": True, "reason": DAILY})):
        assert climate_signals.fetch_climate(0, 0) is None      # 계약: 실패는 None
        assert climate_signals.fetch_climate(1, 1) is None

    reasons = climate_signals.pop_failure_reasons()
    assert reasons == {f"HTTP 429 · {DAILY.strip('.')}": 2}, reasons


def test_the_log_line_carries_the_reason():
    """점검이 로그 한 줄로 판정할 수 있어야 한다."""
    with patch("algorithms.climate_signals.requests.get",
               return_value=_Resp(429, {"error": True, "reason": MINUTELY})):
        climate_signals.fetch_climate(0, 0)

    line = climate_signals.failure_reasons_line(climate_signals.pop_failure_reasons())
    assert line is not None
    assert "Minutely" in line
    assert "×1" in line
    assert "Open-Meteo 실패 사유" in line


# ───────── 집계 키를 쪼개지 않는다 (사유를 못 읽은 경우) ─────────

@pytest.mark.parametrize("resp", [
    _Resp(429),                                  # 본문 없음 — #132 시험의 스텁 모양
    _Resp(429, {}),                              # 빈 dict
    _Resp(429, {"error": True}),                 # reason 키 없음
    _Resp(429, {"reason": ""}),                  # 빈 사유
    _Resp(429, {"reason": "   "}),               # 공백뿐
    _Resp(429, ["not", "a", "dict"]),            # dict 아님
    _Resp(429, raises=True),                     # JSON 아님(프록시 HTML 등)
])
def test_no_reason_means_code_only(resp):
    """못 읽었으면 코드만 남긴다 — 없는 사유를 지어내지 않는다."""
    assert _http_failure_reason(resp) == "HTTP 429"


def test_other_status_codes_keep_working():
    """403(프록시)·400(인자 오류)도 같은 자리를 지난다."""
    assert _http_failure_reason(_Resp(403, raises=True)) == "HTTP 403"
    assert _http_failure_reason(_Resp(400, {"reason": "Invalid latitude"})) == \
        "HTTP 400 · Invalid latitude"


def test_the_132_contract_still_holds():
    """#132 의 단언(`{"HTTP 429": 2}`)이 그대로 성립해야 한다 — 그 시험을 안 고쳤다."""
    with patch("algorithms.climate_signals.requests.get", return_value=_Resp(429)):
        climate_signals.fetch_climate(0, 0)
        climate_signals.fetch_climate(1, 1)
    assert climate_signals.pop_failure_reasons() == {"HTTP 429": 2}


# ───────────────────── 경계 ─────────────────────

def test_long_reason_is_truncated_so_one_fault_stays_one_key():
    reason = "X" * 500
    out = _http_failure_reason(_Resp(429, {"reason": reason}))
    assert len(out) <= len("HTTP 429 · ") + _REASON_MAX


def test_whitespace_and_newlines_are_collapsed():
    """줄바꿈이 섞여 와도 같은 고장이 한 키로 모이게."""
    messy = _http_failure_reason(_Resp(429, {"reason": "  Daily API\n  request\tlimit exceeded.  "}))
    clean = _http_failure_reason(_Resp(429, {"reason": "Daily API request limit exceeded"}))
    assert messy == clean == "HTTP 429 · Daily API request limit exceeded"


def test_trailing_period_does_not_split_the_key():
    with_dot = _http_failure_reason(_Resp(429, {"reason": "Daily API request limit exceeded."}))
    without = _http_failure_reason(_Resp(429, {"reason": "Daily API request limit exceeded"}))
    assert with_dot == without


def test_a_weird_body_never_raises():
    """사유를 읽다가 터지면 상태 코드마저 잃는다 — 어떤 본문에도 터지지 않아야 한다."""
    for body in (None, 0, "", [], {"reason": None}, {"reason": 12345}, {"reason": {"a": 1}}):
        out = _http_failure_reason(_Resp(429, body))
        assert out.startswith("HTTP 429")

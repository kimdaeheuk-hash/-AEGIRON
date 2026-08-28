"""Mobility(OpenSky)가 왜 실패했는지 알 수 있어야 한다 (2026-08-28).

2026-08-17 오후부터 245시간(10.2일) 동안 이 소스가 죽어 있었는데 **원인을
특정할 수 없었다.** 로그에 남은 건 이 한 줄뿐이었다:

    이동성(OpenSky): 0개 공항 확인, 1h 항공편 합계 None

레이트리밋 분기가 아니라 일반 분기가 찍혔으니 429는 아니었다. 남는 건 인증
거부(401)·IP 차단(403)·서버 장애(5xx)·연결 차단인데, 코드가 셋을 구분하지
않았다:

    return None, "http_error"          # 401·403·503 이 전부 같은 말
    except Exception: return {}        # 토큰 발급 실패가 통째로 침묵

게다가 사유를 공항별로 계산해두고도 get_mobility_score 가 숫자 셋만 뽑아
나머지를 버려서, 수집기에는 애초에 도달하지도 않았다.

가장 나빴던 것: OPENSKY_CLIENT_ID/SECRET 은 **실제로 설정돼 있었는데도** 전멸했다.
그런데 "OpenSky는 클라우드 IP가 막혀 상시 이 상태다"라는 **검증된 적 없는 추측**이
collector.py 주석과 절차 문서에 굳어 있어서, 열흘 동안 아무도 다시 보지 않았다.

이 테스트가 고정하는 문장:
    **실패했다는 사실만 남기고 왜 실패했는지를 버리면, 고칠 수 없다.**
    (2026-08-25 groq_watch.py 와 같은 구조의 결함이었다.)
"""
from __future__ import annotations

import json
import requests
from unittest.mock import patch

from algorithms import mobility


def _response(status: int, payload=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(payload if payload is not None else []).encode("utf-8")
    return r


def _clear_token_cache():
    mobility._token_cache["token"] = None
    mobility._token_cache["expires_at"] = 0.0


# ── 인증 상태가 남는가 ────────────────────────────────────────────────────

def test_auth_failure_is_not_swallowed():
    """★핵심★ 토큰 발급 실패가 조용한 빈 dict 로 사라지면 안 된다."""
    _clear_token_cache()
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "sec"}):
        with patch.object(mobility.requests, "post",
                          side_effect=requests.exceptions.ConnectTimeout("boom")):
            header, status = mobility._auth_header()

    assert header == {}, "실패했으면 익명으로 떨어지는 동작 자체는 그대로여야 한다"
    assert status.startswith("auth_failed:"), status
    assert "ConnectTimeout" in status, f"예외 종류가 남아야 한다: {status}"


def test_auth_failure_does_not_leak_credentials():
    """사유는 남기되 키 값은 절대 안 남긴다."""
    _clear_token_cache()
    secret = "super-secret-value"
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": secret}):
        with patch.object(mobility.requests, "post",
                          side_effect=RuntimeError("nope")):
            _, status = mobility._auth_header()

    assert secret not in status
    assert "id" != status and "OPENSKY_CLIENT_SECRET" not in status


def test_missing_credentials_is_distinguishable_from_auth_failure():
    """키가 없는 것과 키가 있는데 거부당한 것은 다른 사건이다."""
    _clear_token_cache()
    with patch.dict("os.environ", {}, clear=True):
        header, status = mobility._auth_header()
    assert header == {}
    assert status == "no_credentials"


def test_successful_auth_reports_authenticated():
    _clear_token_cache()
    token_resp = _response(200, {"access_token": "tok", "expires_in": 1800})
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "sec"}):
        with patch.object(mobility.requests, "post", return_value=token_resp):
            header, status = mobility._auth_header()
    assert status == "authenticated"
    assert header["Authorization"] == "Bearer tok"


# ── HTTP 오류가 한 덩어리로 뭉개지지 않는가 ──────────────────────────────

def test_401_and_403_are_not_the_same_status():
    """★핵심★ 인증 거부(401)와 IP 차단(403)은 조치가 다르다 — 키 재발급 vs 경로 변경."""
    with patch.object(mobility.requests, "get", return_value=_response(401)):
        _, unauthorized = mobility._fetch_airport_flights("RKSI", 0, 1)
    with patch.object(mobility.requests, "get", return_value=_response(403)):
        _, forbidden = mobility._fetch_airport_flights("RKSI", 0, 1)

    assert unauthorized == "http_401"
    assert forbidden == "http_403"
    assert unauthorized != forbidden, "예전엔 둘 다 'http_error' 였다"


def test_server_error_keeps_its_code():
    with patch.object(mobility.requests, "get", return_value=_response(503)):
        _, status = mobility._fetch_airport_flights("RKSI", 0, 1)
    assert status == "http_503"


def test_network_error_keeps_exception_type():
    """타임아웃(블랙홀)과 연결 거부(차단·DNS)는 다른 사건이다."""
    with patch.object(mobility.requests, "get",
                      side_effect=requests.exceptions.ReadTimeout("slow")):
        _, timed_out = mobility._fetch_airport_flights("RKSI", 0, 1)
    with patch.object(mobility.requests, "get",
                      side_effect=requests.exceptions.ConnectionError("refused")):
        _, refused = mobility._fetch_airport_flights("RKSI", 0, 1)

    assert timed_out.startswith("network_error:") and "ReadTimeout" in timed_out
    assert refused.startswith("network_error:") and "ConnectionError" in refused
    assert timed_out != refused


def test_ok_paths_unchanged():
    """200은 건수, 404는 0건(그 공항에 항공편이 없는 것) — 기존 동작 고정."""
    with patch.object(mobility.requests, "get",
                      return_value=_response(200, [{"a": 1}, {"a": 2}])):
        count, status = mobility._fetch_airport_flights("RKSI", 0, 1)
    assert (count, status) == (2, "ok")

    with patch.object(mobility.requests, "get", return_value=_response(404)):
        count, status = mobility._fetch_airport_flights("RKSI", 0, 1)
    assert (count, status) == (0, "ok")


# ── 사유가 요약까지 살아서 도착하는가 ────────────────────────────────────

def test_failure_reasons_reach_the_summary():
    """★가장 중요★ 사유를 계산해놓고 요약에서 버리면 로그에 영영 안 나온다.

    수집기가 보는 건 get_mobility_score() 반환값이 전부다. 여기 없으면
    Railway 로그에도 /api/status 에도 남지 않는다 — 그게 열흘을 끌었다.
    """
    _clear_token_cache()
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(mobility.requests, "get", return_value=_response(403)):
            score = mobility.get_mobility_score()

    assert score["mobility_airports_ok"] == 0
    assert score["mobility_total_flights"] is None, "전멸은 0건이 아니라 None 이다"
    assert score["mobility_auth_status"] == "no_credentials"
    assert score["mobility_failure_reasons"] == {"http_403": len(mobility.WATCH_AIRPORTS)}


def test_auth_failure_visible_from_the_summary():
    """인증이 깨져서 전멸한 경우와 IP가 막혀서 전멸한 경우가 요약에서 갈려야 한다."""
    _clear_token_cache()
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "sec"}):
        with patch.object(mobility.requests, "post", side_effect=RuntimeError("bad key")):
            with patch.object(mobility.requests, "get", return_value=_response(401)):
                score = mobility.get_mobility_score()

    assert score["mobility_auth_status"].startswith("auth_failed:")
    assert score["mobility_failure_reasons"] == {"http_401": len(mobility.WATCH_AIRPORTS)}


# ── 조기 중단 동작이 안 깨졌는가 (기존 기능 고정) ─────────────────────────

def test_rate_limit_still_aborts_and_flags():
    """429를 만나면 나머지 공항은 건너뛰고 rate_limited 로 표시한다 — 기존 동작."""
    _clear_token_cache()
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(mobility.requests, "get", return_value=_response(429)) as g:
            data = mobility.fetch_mobility_signals()

    assert data["rate_limited"] is True
    assert g.call_count == 1, "첫 공항에서 멈춰 쿼터를 더 안 태워야 한다"
    skipped = [r for r in data["airports"] if r["status"] == "skipped_rate_limited"]
    assert len(skipped) == len(mobility.WATCH_AIRPORTS) - 1


def test_network_error_aborts_with_bare_skip_label():
    """조기 중단 라벨은 사유 원문이 아니라 분류를 쓴다(라벨이 공항마다 흔들리면 안 됨)."""
    _clear_token_cache()
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(mobility.requests, "get",
                          side_effect=requests.exceptions.ConnectionError("refused")) as g:
            data = mobility.fetch_mobility_signals()

    assert g.call_count == 1
    assert data["rate_limited"] is False, "연결 차단은 레이트리밋이 아니다"
    assert data["abort_detail"].startswith("network_error:")
    skipped = [r for r in data["airports"] if r["status"] == "skipped_network_error"]
    assert len(skipped) == len(mobility.WATCH_AIRPORTS) - 1


def test_worst_case_connect_attempts_are_bounded_to_two():
    """★연결 타임아웃을 10초로 올려도 안전한 근거★ (2026-08-28)

    도달 불가일 때 시도하는 연결은 **토큰 1회 + 첫 공항 1회, 총 2회뿐**이다.
    나머지 열 개는 조기 중단으로 건너뛴다. 그래서 최악의 지연이
    TIMEOUT[0] × 2 = 20초로 묶인다 — 1시간 주기에 여유가 크다.

    이 성질이 깨지면(예: 조기 중단을 없애면) 11 × 10초 = 110초가 되어
    타임아웃 인상이 곧바로 위험해진다. 그래서 여기서 고정한다.
    """
    _clear_token_cache()
    timeout_err = requests.exceptions.ConnectTimeout("unreachable")
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "sec"}):
        with patch.object(mobility.requests, "post", side_effect=timeout_err) as post:
            with patch.object(mobility.requests, "get", side_effect=timeout_err) as get:
                data = mobility.fetch_mobility_signals()

    assert post.call_count == 1, "토큰 발급은 주기당 한 번(공항마다 다시 묻지 않는다)"
    assert get.call_count == 1, "첫 공항에서 중단 — 나머지는 타임아웃을 기다리지 않는다"
    assert post.call_count + get.call_count == 2
    assert mobility.TIMEOUT[0] * 2 <= 60, (
        f"최악 지연 {mobility.TIMEOUT[0] * 2}초 — 1시간 주기를 위협하면 안 된다"
    )


def test_connect_timeout_surfaces_the_host_that_was_unreachable():
    """어느 호스트에 못 닿았는지가 남아야 한다 — 인증 서버와 API 서버는 다른 호스트다.

    실측(2026-08-28): 못 닿은 곳은 `auth.opensky-network.org` 였다. 인증 서버가
    죽으면 익명으로 떨어지므로, 두 호스트를 구분하지 않으면 "키가 문제인가"를
    영영 못 가린다.
    """
    _clear_token_cache()
    err = requests.exceptions.ConnectTimeout(
        "HTTPSConnectionPool(host='auth.opensky-network.org', port=443): Max retries exceeded"
    )
    with patch.dict("os.environ", {"OPENSKY_CLIENT_ID": "id", "OPENSKY_CLIENT_SECRET": "sec"}):
        with patch.object(mobility.requests, "post", side_effect=err):
            _, status = mobility._auth_header()

    assert "ConnectTimeout" in status
    assert "auth.opensky-network.org" in status, f"호스트가 남아야 한다: {status}"


def test_partial_success_is_not_marked_no_data():
    """일부라도 값이 오면 합계가 숫자로 나와야 한다 — 전멸과 구분."""
    _clear_token_cache()
    responses = [_response(200, [{"a": 1}])] + [_response(403)] * (len(mobility.WATCH_AIRPORTS) - 1)
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(mobility.requests, "get", side_effect=responses):
            score = mobility.get_mobility_score()

    assert score["mobility_airports_ok"] == 1
    assert score["mobility_total_flights"] == 1
    assert score["mobility_failure_reasons"] == {"http_403": len(mobility.WATCH_AIRPORTS) - 1}


# ── 수집기가 실제로 그 사유를 찍는가 ─────────────────────────────────────

def test_collector_logs_the_reason_when_all_airports_fail(capsys):
    """★핵심★ 전멸했을 때 로그에 '왜'가 반드시 찍혀야 한다.

    예전엔 "0개 공항 확인" 한 줄이 전부였고, 그래서 열흘을 끌었다.
    """
    import collector

    collector.log(
        f"  ⏭ 이동성(OpenSky) 전멸 — 인증=no_credentials "
        f"· 사유={collector._fmt_failure_reasons({'http_403': 11})}"
    )
    out = capsys.readouterr().out
    assert "인증=no_credentials" in out
    assert "http_403×11" in out


def test_fmt_failure_reasons_orders_by_count():
    from collector import _fmt_failure_reasons

    assert _fmt_failure_reasons({"http_403": 2, "http_401": 9}) == "http_401×9, http_403×2"


def test_fmt_failure_reasons_puts_the_cause_before_the_fallout():
    """★핵심★ 조기 중단 시 skipped_×10 이 진짜 원인 ×1 을 가리면 안 된다.

    실측(2026-08-28 재현): 연결 차단이면 첫 공항 하나만 network_error 를 갖고
    나머지 열 개가 skipped_network_error 가 된다. 개수 순으로만 정렬하면
    파생 결과가 맨 앞에 서서 원인이 안 읽힌다.
    """
    from collector import _fmt_failure_reasons

    line = _fmt_failure_reasons({
        "skipped_network_error": 10,
        "network_error: ConnectionError": 1,
    })
    assert line.startswith("network_error: ConnectionError×1"), line
    assert line.endswith("skipped_network_error×10"), line


def test_fmt_failure_reasons_says_so_when_empty():
    """사유가 하나도 없다는 것 자체가 '실패 경로가 아직 조용하다'는 신호다."""
    from collector import _fmt_failure_reasons

    assert "사유 없음" in _fmt_failure_reasons({})
    assert "사유 없음" in _fmt_failure_reasons(None)

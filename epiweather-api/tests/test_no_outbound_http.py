"""테스트는 바깥 인터넷에 나가지 않는다 — 그 규칙 자체를 고정한다 (2026-08-28).

## 왜 생겼나

CI 가 **42분** 걸리는데 로컬은 3분이었다. 두 번 틀린 뒤에야 원인을 찾았다:

    ① "의존성 설치가 느린 것"     → ❌ 실측 20초였다
    ② "테스트가 네트워크를 쓴다"   → 소켓 탐침이 0건이라 한 번 접었는데,
                                    **탐침이 고장나 있었다** — 이 환경의 프록시가
                                    127.0.0.1 이라 localhost 필터에 다 걸러졌다
    ③ requests 레벨에서 다시 재니: **36개 테스트가 814회 실제 호출**
                                    (api.open-meteo.com · news.google.com ·
                                     comtradeapi.un.org)

    814회 × CI 평균 ~3초 ≈ 2,400초 ≈ 40분   (실측 CI pytest 단계 2,523초)

UN comtrade 는 절차 문서에도 "UN 에 18번 호출해서 처음엔 최대 90초" 라고 적힌
느린 API 다. 그걸 매 푸시마다 진짜로 부르고 있었다.

## 막아도 되는 근거

개발 샌드박스는 외부 접속이 막혀 그 호출이 전부 실패하는데도 **954개가 전부
통과했다.** 코드가 이미 네트워크 없이 동작하도록 방어돼 있다는 뜻이다.
차단은 그 조건을 CI 에서도 **결정적으로** 만들 뿐이다.

실측: 175초 → **28.6초** (로컬 6배). CI 는 네트워크 왕복이 통째로 사라진다.

## 이 파일이 지키는 것

가드가 조용히 사라지면 **CI 가 다시 40분이 되는데 테스트도 로그도 안 깨진다.**
오늘 하루에만 그런 종류의 침묵을 세 번 봤다(GroqWatch·Mobility·은퇴 소스).
그래서 가드의 존재 자체를 여기서 고정한다.
"""
from __future__ import annotations

import pytest
import requests


def test_unmocked_http_is_blocked():
    """★핵심★ 모킹을 빠뜨린 호출은 나가지 못한다."""
    with pytest.raises(requests.exceptions.ConnectionError) as exc:
        requests.get("https://api.open-meteo.com/v1/forecast", timeout=5)

    msg = str(exc.value)
    assert "테스트에서 실제 HTTP 를 막았다" in msg
    assert "api.open-meteo.com" in msg, "어디로 가려 했는지가 메시지에 있어야 한다"


def test_block_message_tells_you_what_to_do():
    """막기만 하고 방법을 안 알려주면 다음 사람이 헤맨다."""
    with pytest.raises(requests.exceptions.ConnectionError) as exc:
        requests.post("https://comtradeapi.un.org/data", timeout=5)

    msg = str(exc.value)
    assert "mock" in msg
    assert "allow_network" in msg
    assert "conftest.py" in msg


def test_blocked_as_connection_error_so_existing_handlers_still_catch_it():
    """★설계 근거★ 새 예외 종류를 만들면 기존 방어를 빠져나간다.

    호출부들은 `except requests.RequestException` / `except Exception` 으로
    네트워크 실패를 이미 다루고 있다. 차단을 ConnectionError 로 하는 이유가
    이것이다 — 코드 입장에서는 그냥 '망이 안 됐다' 와 똑같이 보여야 한다.
    """
    with pytest.raises(requests.RequestException):
        requests.get("https://news.google.com/rss/search?q=test", timeout=5)


def test_session_level_calls_are_blocked_too():
    """`requests.get` 뿐 아니라 Session 을 직접 쓰는 코드도 막힌다."""
    s = requests.Session()
    with pytest.raises(requests.exceptions.ConnectionError):
        s.get("https://api.open-meteo.com/v1/forecast", timeout=5)


def test_mocked_calls_are_unaffected():
    """★가드가 정상 테스트를 방해하지 않는다★

    가드는 `Session.send` 라는 **마지막 관문**에 있다. 테스트가 그보다 앞을
    patch 해두면 거기서 끝나므로 가드에 닿지도 않는다 — 그래서 기존 모킹
    테스트 954개가 그대로 통과한다.
    """
    from unittest.mock import patch

    fake = requests.Response()
    fake.status_code = 200
    fake._content = b'{"ok": true}'

    with patch.object(requests, "get", return_value=fake):
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=5)

    assert r.status_code == 200
    assert r.json() == {"ok": True}


@pytest.mark.allow_network
def test_marker_disables_the_guard():
    """정말 바깥이 필요한 테스트를 위한 탈출구가 실제로 동작하는가.

    여기서는 **실제 호출을 하지 않는다** — CI 를 남의 서비스에 의존시키지 않으려고
    일부러 그렇게 뒀다. 마커가 붙으면 가드가 `Session.send` 를 갈아끼우지 않는다는
    사실만 확인한다(그게 탈출구의 전부다).
    """
    assert requests.Session.send.__name__ != "_blocked", (
        "allow_network 마커가 붙었는데도 가드가 걸려 있다"
    )

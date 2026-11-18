"""무거운 조회 API 의 응답 캐시 — '마지막 결과를 바로 주고, 오래됐으면 뒤에서 새로 계산' (2026-11-15).

## 왜 (실측)

캡틴: "대시보드 창도 너무 늦게 뜨고 각 페이지들이 모두 늦게 떠."
2026-11-15 04:26~04:39 UTC 운영 HTTP 로그 501건:

    /api/daily-brief      중앙값 295초
    /api/risk-index       중앙값  45초 · 최대 182초 · 502 10건
    /api/alerts           중앙값  45초 · 최대 115초 · 502 6건
    /api/status           중앙값  26초
    negative-space·lead-time-ledger·unexplained·polar·climate·land  8~20초

전부 **요청마다 처음부터 다시 계산**한다. 웹(Vercel)이 페이지를 만들 때 이 API 들을 한꺼번에 부르면
한 요청이 다른 요청을 막아 줄줄이 느려지고 일부는 502 로 끊긴다. 계산 결과는 매시간 수집이
끝나야 바뀌므로 매 요청 재계산은 낭비다.

## 동작 (대시보드 캐시 _dashboard_cached 와 같은 원칙을 일반화)

- 신선(ttl 이내): 저장된 결과를 바로 준다.
- 만료: 저장된 결과를 **바로 주고**, 뒤 스레드에서 한 번만 다시 계산한다(몰려도 하나만).
- 처음(저장본 없음): 계산한다. 같은 키로 동시에 들어온 요청은 그 한 번의 결과를 기다린다.
- 계산이 예외면 저장하지 않는다 — 실패가 ttl 동안 답이 되면 안 된다. 만료 저장본이 있으면 그걸 계속 준다.

## 정직성

dict 응답에는 `response_cache` 칸을 붙인다: 계산 시각·나이(초)·만료 여부. 화면이나 사람이
'이 값이 언제 계산된 것인지' 알 수 있게 — 캐시가 값을 지금 것처럼 보이게 만들면 안 된다.
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from collections.abc import Callable
from typing import Any

_STORE: dict[str, tuple[float, Any]] = {}
_LOCKS: dict[str, threading.Lock] = {}
_GUARD = threading.Lock()


def _lock(key: str) -> threading.Lock:
    with _GUARD:
        lk = _LOCKS.get(key)
        if lk is None:
            lk = _LOCKS[key] = threading.Lock()
        return lk


def _stamp(value: Any, computed_at: float, stale: bool) -> Any:
    if not isinstance(value, dict):
        return value
    return {
        **value,
        "response_cache": {
            "computed_at": dt.datetime.fromtimestamp(computed_at, dt.timezone.utc).isoformat(),
            "age_sec": round(time.time() - computed_at, 1),
            "stale": stale,
        },
    }


def _refresh_bg(key: str, builder: Callable[[], Any], lk: threading.Lock) -> None:
    try:
        value = builder()
        _STORE[key] = (time.time(), value)
    except Exception:  # noqa: BLE001, S110 — 실패는 저장하지 않고 만료 저장본을 계속 준다
        pass
    finally:
        lk.release()


def swr(key: str, ttl: float, builder: Callable[[], Any]) -> Any:
    """키의 저장본을 ttl 기준으로 준다. 만료면 저장본을 주고 뒤에서 갱신, 없으면 계산."""
    hit = _STORE.get(key)
    now = time.time()
    if hit is not None and now - hit[0] < ttl:
        return _stamp(hit[1], hit[0], stale=False)
    lk = _lock(key)
    if hit is not None:
        if lk.acquire(blocking=False):
            threading.Thread(target=_refresh_bg, args=(key, builder, lk), daemon=True).start()
        return _stamp(hit[1], hit[0], stale=True)
    with lk:  # 첫 계산 — 같이 들어온 요청은 이 결과를 기다렸다 받는다
        hit = _STORE.get(key)
        if hit is not None:
            return _stamp(hit[1], hit[0], stale=False)
        value = builder()
        _STORE[key] = (time.time(), value)
        return _stamp(value, _STORE[key][0], stale=False)


def seed(key: str, value: Any) -> None:
    """방금 계산한 결과를 저장본으로 넣는다(예: 매시 경보 주기가 낸 refresh_alerts 결과)."""
    _STORE[key] = (time.time(), value)


def prewarm(key: str, builder: Callable[[], Any]) -> bool:
    """저장본을 지금 다시 계산해 넣는다(뒤 스레드에서 부르는 용도). 이미 갱신 중이면 건너뛴다."""
    lk = _lock(key)
    if not lk.acquire(blocking=False):
        return False
    try:
        _STORE[key] = (time.time(), builder())
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        lk.release()


def put(key: str, value: Any) -> None:
    """이미 계산된 값을 저장본으로 넣는다 (2026-11-18).

    매시간 수집기가 같은 자료(극지 관찰)를 이미 받아 왔는데, 관측값 저장·API 가 같은 키로
    또 계산하면 외부 API(Open-Meteo)를 두 번 부른다. 무료 하루 한도가 낮에 바닥나
    11-15~17 사흘 동안 극지·기후가 반나절씩 '판정 안 함'이 됐다. 계산한 쪽이 넣어 두면
    나머지는 ttl 안에서 그 값을 그대로 쓴다. 계산 시각은 넣은 시각이다(_stamp 가 나이를 붙인다).
    """
    _STORE[key] = (time.time(), value)


def invalidate(prefix: str) -> None:
    """쓰기 직후 그 키 묶음의 저장본을 버린다(예: 예측을 새로 기록하면 'pred:' 묶음)."""
    for k in [k for k in _STORE if k.startswith(prefix)]:
        _STORE.pop(k, None)


def clear() -> None:
    """시험·재배포용 — 저장본을 모두 비운다."""
    _STORE.clear()

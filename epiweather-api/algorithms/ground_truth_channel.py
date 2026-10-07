"""정답 경로가 '보고 있었는가' — 침묵을 오답으로 세기 전의 확인 (2026-10-07).

## 왜 만드는가

예측 채점기와 선행성 원장은 기한(90일) 안에 선언이 없으면 `incorrect`/`no_declaration` 으로 닫는다.
그런데 정답 경로(`declaration_ingest`)는 **한 건도 못 적재하는 구조**였다 — 신뢰도 0.90 이상이면서
`신규발생` 인 신호를 만드는 생산자가 없었다(뉴스 추출은 0.65, WHO 표 추출은 `진행중/불명` 만).
정답 경로가 눈이 먼 채로 기한이 지나면 '조용했다'가 아니라 '못 봤다'인데, 그걸 `incorrect` 로 세면
**측정된 것처럼 보이는 적중률 0%** 가 만들어진다. 이 제품이 파는 숫자가 정확히 그것이다.

세 상태(성공/실패/판정 안 함) 중 이 경우는 **판정 안 함**이다 — 닫지 않고 열어 둔다.

## 판정 규칙 (보수적)

판정 구간 `[시작, 기한]` 에 대해 정답 경로가 **실제로 보고 있었다**고 말하려면 둘 다 필요하다.

1. 정답 경로의 첫 적재 시각이 구간 시작 이전이다 — 예측이 나온 날 이미 돌고 있었다.
2. 구간 안의 날짜를 가진 선언이 정답 경로에서 하나라도 적재됐다 — 그 기간에 실제로 뭔가를 보았다.

하나라도 아니면 `blind_reason` 을 돌려주고 호출부는 닫지 않는다. 손으로 적은 백필(`official`)은 센다고
하지 않는다 — 과거 16건은 오늘의 경로가 보고 있었다는 증거가 아니다.
"""
from __future__ import annotations

import datetime as dt

import db

from . import declaration_ingest, who_don_declarations

# 실시간 정답 경로의 source_type. 문자열을 또 적지 않고 각 생산자의 값을 쓴다.
LIVE_SOURCE_TYPES = (declaration_ingest.SOURCE_TYPE, who_don_declarations.SOURCE_TYPE)


def _as_date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def blind_reason(window_start: dt.date, window_end: dt.date) -> str | None:
    """정답 경로가 이 구간을 못 보고 있었다면 그 사유, 보고 있었다면 None."""
    rows = db.list_live_timeline_rows(LIVE_SOURCE_TYPES)
    if not rows:
        return "정답 경로가 한 건도 적재한 적이 없다"
    firsts = [d for d in (_as_date(r.get("created_at")) for r in rows) if d]
    first = min(firsts) if firsts else None
    if first is None or first > window_start:
        return (f"정답 경로의 첫 적재({first.isoformat() if first else '날짜 모름'})가 "
                f"판정 구간 시작({window_start.isoformat()})보다 늦다")
    in_window = any(
        d and window_start <= d <= window_end
        for d in (_as_date(r.get("event_date")) for r in rows)
    )
    if not in_window:
        return "판정 구간 안의 날짜를 가진 선언이 정답 경로에서 하나도 적재되지 않았다"
    return None

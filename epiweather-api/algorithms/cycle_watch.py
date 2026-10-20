"""매시 주기가 빠지거나 멈추면 스스로 말하게 한다 (2026-10-20, 소킹 10-19 22시 결손).

## 왜

10-19 22:00 슬롯은 수집이 끝나고(22:01:37) 경보 계산이 시작된 흔적(22:01:48 `🧢`)까지 찍힌 뒤
`🚨 경보 주기`·`🌊 BAIKAL` 줄이 하나도 없었다. 오류 줄도 없었고 23:00 주기는 정상이었다. 로그만으로는
**주기가 멈췄다가 풀렸는지, 돌았는데 줄이 사라졌는지** 가를 수 없었다 — 원인 판정 못 함.
다음에 같은 일이 나면 값으로 가를 수 있게 두 가지를 남긴다.

1. **완료 장부** — 경보 주기가 끝날 때마다 시각을 볼륨(data/)에 적는다. 다음 주기가 시작할 때 그 사이에
   완료 기록이 없는 정시 슬롯이 있으면 `⚠ 경보 주기 결손` 줄을 찍는다. 장부에 완료가 있는데 로그에 줄이
   없으면 **로그 유실**, 장부에도 없으면 **주기가 안 끝났다**.
2. **멈춤 감시** — 한 단계가 STALL_WARN_SECONDS 를 넘기면 `⏳` 줄과 함께 그 순간 스레드들의 호출 위치를
   찍는다. 어디서 멈췄는지가 추정이 아니라 값이 된다. 단계가 끝나면 몇 분 걸렸는지도 찍는다.

이 층은 주기를 막거나 끊지 않는다 — 보고만 한다(끊으면 스레드는 계속 돌고 다음 주기와 겹친다).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import threading
import traceback
from pathlib import Path

STALL_WARN_SECONDS = 600       # 경보 주기는 평소 수십 초 — 10분이면 멈춤으로 본다
MAX_SLOTS_NAMED = 6            # 결손 슬롯이 많으면 앞의 몇 개만 이름을 적는다
STACK_FRAMES = 12              # 스레드마다 마지막 몇 프레임만
OUR_CODE = ("epiweather-api", "algorithms", "collector.py", "main.py", "db.py")


def load_last_done(path: Path) -> dt.datetime | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8")).get("last_done")
        when = dt.datetime.fromisoformat(raw)
        return when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def save_done(path: Path, when: dt.datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_done": when.isoformat()}), encoding="utf-8")


def missed_slots(last_done: dt.datetime | None, now: dt.datetime) -> list[dt.datetime]:
    """직전 완료와 지금 사이에 완료 기록이 하나도 없는 정시 슬롯(지금 슬롯은 뺀다). 장부가 없으면 모른다(빈 목록)."""
    if last_done is None:
        return []
    slot = last_done.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    current = now.replace(minute=0, second=0, microsecond=0)
    out = []
    while slot < current:
        out.append(slot)
        slot += dt.timedelta(hours=1)
    return out


def gap_line(missed: list[dt.datetime], last_done: dt.datetime) -> str | None:
    if not missed:
        return None
    names = " · ".join(s.strftime("%m-%d %H시") for s in missed[:MAX_SLOTS_NAMED])
    more = f" 외 {len(missed) - MAX_SLOTS_NAMED}개" if len(missed) > MAX_SLOTS_NAMED else ""
    return (f"⚠ 경보 주기 결손: {names}{more} 슬롯 완료 기록 없음 "
            f"(직전 완료 {last_done.strftime('%m-%d %H:%M')} UTC — 배포·재시작 공백이거나 주기가 안 끝났음)")


def stall_line(step: str, started: dt.datetime, seconds: float) -> str:
    return (f"⏳ {step} {int(seconds // 60)}분째 안 끝남 (시작 {started.strftime('%H:%M:%S')} UTC) — "
            f"아래는 지금 스레드들의 호출 위치")


def thread_stacks() -> str:
    """지금 살아 있는 스레드 중 우리 코드를 지나는 것의 마지막 몇 프레임. 어디서 멈췄는지 보려는 것."""
    names = {t.ident: t.name for t in threading.enumerate()}
    blocks = []
    for ident, frame in sys._current_frames().items():
        stack = traceback.extract_stack(frame)
        if not any(any(mark in f.filename for mark in OUR_CODE) for f in stack):
            continue
        lines = [f"    {Path(f.filename).name}:{f.lineno} {f.name}" for f in stack[-STACK_FRAMES:]]
        blocks.append(f"  [스레드 {names.get(ident, ident)}]\n" + "\n".join(lines))
    return "\n".join(blocks) if blocks else "  (우리 코드를 지나는 스레드 없음)"

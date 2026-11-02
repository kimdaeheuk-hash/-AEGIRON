"""스케줄러 작업 중복 실행 방지 — 프로세스 간 파일 락.

왜 필요한가: 스케줄 루프는 순차 await 라 한 프로세스 안에서는 겹칠 수 없지만,
uvicorn 워커를 늘리거나 재배포 신·구가 겹치는 순간 같은 작업이 두 프로세스에서
돈다. 수집 중복은 API 쿼터·비용 문제고, 일일 브리핑 중복은 LLM 이중 과금이다.

방식: 작업마다 data/locks/<job>.lock 파일을 O_EXCL(원자 생성)로 만든다.
있으면 mtime 으로 신선도를 보고, stale_sec 을 넘겼으면 끊긴 프로세스의
잔해로 보고 깨고 뺏는다. heartbeat 없이 mtime 만 쓰는 대신 stale 판정은
'작업 타임아웃 + 여유'로 잡는다 — 타임아웃이 살아 있으면 정상 작업의 락이
stale 로 보일 수 없다.

해제(release)는 자기 pid 가 owner 일 때만 — 남이 stale-break 로 뺏은 락을
늦게 끝난 예전 주인이 지우면 두 프로세스가 동시에 돌게 된다.
"""
from __future__ import annotations

import datetime as dt
import errno
import os
import re
import time
from pathlib import Path

LOCK_DIR_ENV = "EPIWEATHER_LOCK_DIR"
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")


def lock_dir() -> Path:
    """락 디렉터리 — 테스트는 EPIWEATHER_LOCK_DIR 로 격리한다."""
    override = os.environ.get(LOCK_DIR_ENV)
    if override:
        return Path(override)
    return Path(__file__).parent.parent / "data" / "locks"


def _path(name: str, base: Path | None = None) -> Path:
    if not _NAME_RE.match(name):
        raise ValueError(f"잘못된 락 이름: {name!r}")
    return (base or lock_dir()) / f"{name}.lock"


def acquire(name: str, stale_sec: int, base: Path | None = None) -> bool:
    """락을 잡으면 True, 남이 잡고 있으면 False."""
    if stale_sec <= 0:
        raise ValueError("stale_sec 는 양수")
    path = _path(name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"{os.getpid()}\n{dt.datetime.now(dt.timezone.utc).isoformat()}\n"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        return _break_if_stale(path, name, stale_sec, content)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def _break_if_stale(path: Path, name: str, stale_sec: int, content: str) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        age = stale_sec + 1  # stat 실패 = 없는 것이나 마찬가지
    if age <= stale_sec:
        return False
    try:
        path.unlink()
    except OSError:
        return False  # 남이 먼저 깨고 뺏음(또는 권한) — 졌다
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError:
        return False  # 재경쟁에서 짐
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def owner_pid(name: str, base: Path | None = None) -> int | None:
    """락 주인의 pid — 읽히지 않으면 None."""
    try:
        first = _path(name, base).read_text(encoding="utf-8").splitlines()[0]
        return int(first)
    except (OSError, ValueError, IndexError):
        return None


def release(name: str, base: Path | None = None) -> bool:
    """자기 락이면 지우고 True. 남의 락·없는 락이면 손대지 않고 False."""
    if owner_pid(name, base) != os.getpid():
        return False
    try:
        _path(name, base).unlink()
    except OSError:
        return False
    return True

"""job_lock + _watched 가드. 파일락은 tmp 격리, 비동기는 asyncio.run."""
from __future__ import annotations
import asyncio
import os
import time

import collector
import main
from algorithms import job_lock


def test_acquire_release_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    assert job_lock.acquire("job-a", 60) is True
    assert job_lock.release("job-a") is True
    assert job_lock.acquire("job-a", 60) is True  # 해제한 뒤 다시 잡힘
    assert job_lock.release("job-a") is True


def test_second_acquire_blocked_while_held(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    assert job_lock.acquire("job-a", 600) is True
    assert job_lock.acquire("job-a", 600) is False
    assert job_lock.release("job-a") is True


def test_stale_lock_is_broken(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    assert job_lock.acquire("job-a", 600) is True
    # 주인이 죽었다고 가정 — mtime 을 과거로 돌린다
    p = tmp_path / "job-a.lock"
    old = time.time() - 99999
    os.utime(p, (old, old))
    assert job_lock.acquire("job-a", 60) is True
    assert job_lock.release("job-a") is True


def test_release_refuses_foreign_lock(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    (tmp_path / "job-a.lock").write_text("99999999\nx\n", encoding="utf-8")
    assert job_lock.release("job-a") is False  # 남의 락은 안 지움
    assert (tmp_path / "job-a.lock").exists()


def test_bad_name_rejected(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    with pytest.raises(ValueError):
        job_lock.acquire("../escape", 60)
    with pytest.raises(ValueError):
        job_lock.acquire("x", 0)


def test_race_single_winner(tmp_path, monkeypatch):
    import concurrent.futures
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        wins = sum(ex.submit(job_lock.acquire, "race", 600).result() for _ in range(10))
    assert wins == 1


def test_watched_skips_when_locked(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    lines = []
    monkeypatch.setattr(collector, "log", lambda m: lines.append(m))
    assert job_lock.acquire("t-job", 600) is True  # 다른 프로세스가 잡은 척

    ran = []
    async def never():
        ran.append(1)

    out = asyncio.run(main._watched("테스트", never(), job="t-job", timeout=5))
    assert out["skipped"] == "locked" and ran == []
    assert any("건너뜀" in ln for ln in lines)
    assert job_lock.release("t-job") is True  # 테스트 주인이라 해제 가능


def test_watched_timeout_releases_lock(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(collector, "log", lambda m: None)
    monkeypatch.setattr(collector, "log_error", lambda *a: None)

    async def slow():
        await asyncio.sleep(30)

    out = asyncio.run(main._watched("테스트", slow(), job="t-job", timeout=0.05))
    assert out["skipped"] == "timeout"
    assert job_lock.acquire("t-job", 600) is True  # 타임아웃 뒤 락이 풀려 있음
    assert job_lock.release("t-job") is True


def test_watched_success_releases_lock(tmp_path, monkeypatch):
    monkeypatch.setenv(job_lock.LOCK_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(collector, "log", lambda m: None)

    async def fast():
        return None

    out = asyncio.run(main._watched("테스트", fast(), job="t-job", timeout=5))
    assert out == {"ok": True, "step": "테스트"}
    assert job_lock.acquire("t-job", 600) is True
    assert job_lock.release("t-job") is True


def test_watched_job_requires_timeout():
    import pytest

    async def fast():
        return None

    with pytest.raises(ValueError):
        asyncio.run(main._watched("테스트", fast(), job="t-job"))

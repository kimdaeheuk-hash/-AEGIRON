"""조달 선행지표 — 입찰 속도 변화율 (2026-11-03).

이번 7일 vs 직전 7일 공고 건수 배율. 비교 구간 기록이 없으면 판정 안 함.
임시 히스토리 파일이라 운영 데이터를 건드리지 않는다. 외부 HTTP 없음.
"""
from __future__ import annotations

import datetime as dt

from algorithms import procurement_velocity as pv

UTC = dt.timezone.utc


def _at(days_ago, h=12):
    return dt.datetime.now(UTC) - dt.timedelta(days=days_ago, hours=12 - h)


def test_surge_when_recent_doubles(tmp_path, monkeypatch):
    """최근 7일이 직전 7일의 2배면 급변."""
    monkeypatch.setattr(pv, "HISTORY_FILE", tmp_path / "vel.json")
    for d in (13, 10, 8):
        pv.record(4, None, now=_at(d))
    for d in (6, 3, 1):
        pv.record(10, None, now=_at(d))
    kor = pv.velocity()["kor"]
    assert kor["assessed"] is True
    assert kor["ratio"] == 2.5
    assert kor["surge"] is True


def test_no_surge_when_flat(tmp_path, monkeypatch):
    """평탄하면 급변 아님."""
    monkeypatch.setattr(pv, "HISTORY_FILE", tmp_path / "vel.json")
    for d in (13, 6, 1):
        pv.record(5, 2, now=_at(d))
    out = pv.velocity()
    assert out["kor"]["surge"] is False
    assert out["ted"]["surge"] is False


def test_insufficient_history_stays_unassessed(tmp_path, monkeypatch):
    """비교 구간 기록이 없으면 판정 안 함."""
    monkeypatch.setattr(pv, "HISTORY_FILE", tmp_path / "vel.json")
    pv.record(9, None, now=_at(1))
    kor = pv.velocity()["kor"]
    assert kor["assessed"] is False
    assert "직전 7일" in kor["reason"]


def test_sources_are_separate(tmp_path, monkeypatch):
    """KOR/TED 분리 — 한쪽 급변이 다른 쪽으로 번지지 않는다."""
    monkeypatch.setattr(pv, "HISTORY_FILE", tmp_path / "vel.json")
    for d in (13, 10):
        pv.record(5, 1, now=_at(d))
    for d in (6, 1):
        pv.record(5, 5, now=_at(d))
    out = pv.velocity()
    assert out["kor"]["surge"] is False
    assert out["ted"]["surge"] is True


def test_record_never_raises(tmp_path, monkeypatch):
    """기록 실패가 수집을 깨지 않는다."""
    def boom(entries):
        raise IOError("disk full")

    monkeypatch.setattr(pv, "_save", boom)
    pv.record(1, None)  # raise하면 테스트 실패

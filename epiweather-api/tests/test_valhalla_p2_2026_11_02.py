"""발할라 P2 — TED 장부 검증+EUL 문서화+C05 코드 정합.

전부 mock·직접 호출. 외부 HTTP 없음.
EUL은 재조사 결과(API 없음)를 approved_products docstring에 기록 — 제품명을
날조하지 않는다. 이 파일은 TED 뒤집힘과 C05 코드 동봉을 고정한다.
"""
from __future__ import annotations

import datetime as dt
import os
from unittest.mock import patch

os.environ.setdefault("EPIWEATHER_SCHEDULER", "off")

import main
from algorithms import capability_ledger as ledger
from algorithms import disaster_watch as dw
from algorithms import ihr_capacity as ihr
from algorithms import procurement_ted as ted


def _notice(title="Vaccine procurement"):
    return {"publication_number": "2026/S 001-000001", "title": title,
            "description": None, "buyer_name": "HERA",
            "buyer_country": "BEL", "publication_date": "2026-09-01",
            "deadline": "2026-09-20", "estimated_value": 1000000,
            "currency": "EUR", "links": {}}


# ── TED 장부 검증 ─────────────────────────────────────────────────
def test_success_records_ok_and_failure_records_fail(monkeypatch):
    """성공/실패가 장부에 남는다 — 안 되면 조용하지 않다."""
    calls: list = []
    monkeypatch.setattr(ledger, "record",
                        lambda cap, **kw: calls.append((cap, kw.get("ok"))))
    monkeypatch.setattr(ledger, "status", lambda cap: {"verified": False})
    with patch.object(ted, "_search", return_value=[_notice()]):
        ted.watch_ted(days=7)
    assert (ted.TED_CAPABILITY, True) in calls
    with patch.object(ted, "_search", return_value="Timeout"):
        ted.watch_ted(days=7)
    assert (ted.TED_CAPABILITY, False) in calls


def test_verified_flips_only_from_ledger(monkeypatch):
    """장부가 verified를 내려야 True — 손으로 뒤집을 상수가 없다."""
    assert not hasattr(ted, "IS_VERIFIED")
    monkeypatch.setattr(ledger, "record", lambda *a, **k: None)
    monkeypatch.setattr(ledger, "status",
                        lambda cap: {"verified": True,
                                     "claim_basis": "verified_run"})
    with patch.object(ted, "_search", return_value=[_notice()]):
        out = ted.watch_ted(days=7)
    assert out["is_verified"] is True
    assert out["unverified_note"] is None


def test_unverified_note_present_until_first_success(monkeypatch):
    monkeypatch.setattr(ledger, "record", lambda *a, **k: None)
    monkeypatch.setattr(ledger, "status",
                        lambda cap: {"verified": False,
                                     "claim_basis": "configuration_only"})
    with patch.object(ted, "_search", return_value=[_notice()]):
        out = ted.watch_ted(days=7)
    assert out["is_verified"] is False
    assert "대외 자료에" in out["unverified_note"]


def test_ted_verified_survives_ledger_error(monkeypatch):
    """장부를 못 읽으면 False — 검증됨으로 뻥튀기하지 않는다."""
    def boom(cap):
        raise OSError("disk")
    monkeypatch.setattr(ledger, "status", boom)
    assert ted.ted_verified() is False


def test_record_failure_does_not_kill_lookup(monkeypatch):
    """기록 실패가 조회를 막지 않는다."""
    def boom(*a, **k):
        raise OSError("disk")
    monkeypatch.setattr(ledger, "record", boom)
    monkeypatch.setattr(ledger, "status", lambda cap: {"verified": False})
    with patch.object(ted, "_search", return_value=[_notice()]):
        out = ted.watch_ted(days=7)
    assert out["available"] is True and out["bid_count"] == 1


# ── C05 정합: 코드가 이름과 같이 다닌다 ────────────────────────────
_SNAP = {
    "latest_year": 2024,
    "capacities": {"C04": "실험실", "C05": "감시"},
    "source": "test",
    "snapshot_date": "2026-01-01",
    "scores": {
        "AAA": {"2024": {"C04": 100, "C05": 100}},
        "BBB": {"2024": {"C04": 100, "C05": 100}},
        "CCC": {"2024": {"C04": 100, "C05": 100}},
        "NPL": {"2024": {"C04": 20, "C05": 20}},
    },
}


def test_behind_world_carries_codes(monkeypatch):
    """뒤처진 역량에 코드가 붙는다 — C05를 문자열 매칭 없이 가른다."""
    monkeypatch.setattr(ihr, "_snapshot", lambda: _SNAP)
    out = ihr.country_capacity("NPL")
    assert out["available"] is True
    assert out["behind_world"] == ["실험실", "감시"]
    assert out["behind_world_codes"] == ["C04", "C05"]
    assert "C05" in out["behind_world_codes"]


def test_capacity_gap_rows_carry_codes(monkeypatch):
    """capacity-gap 행에도 코드가 실린다."""
    monkeypatch.setattr(ihr, "_snapshot", lambda: _SNAP)
    monkeypatch.setattr(dw, "watched_countries", lambda: ["NPL"])
    out = main.biodefense_capacity_gap()
    assert out["countries"][0]["iso3"] == "NPL"
    assert out["countries"][0]["behind_world_codes"] == ["C04", "C05"]


def test_codes_align_with_names(monkeypatch):
    """코드와 이름 개수가 어긋나면 잇기가 깨진다."""
    monkeypatch.setattr(ihr, "_snapshot", lambda: _SNAP)
    out = ihr.country_capacity("NPL")
    assert len(out["behind_world_codes"]) == len(out["behind_world"])
    assert out["behind_world_count"] == len(out["behind_world_codes"])

"""발할라 P0 — 브리핑 배선+경보 읽기 간선+수기 표 나이.

전부 mock. 외부 HTTP·실제 state 파일·실제 DB 없음.
"""
from __future__ import annotations

import datetime as dt

from algorithms import brief_sections as bs
from algorithms import countermeasure_stockpile as csp
from algorithms import valhalla_watch as vw
from algorithms.alerts import valhalla_watch_line


def _state(proc_age_h=1.0, pipe_age_h=2.0):
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "procurement": {
            "fetched_at": (now - dt.timedelta(hours=proc_age_h)).isoformat(),
            "value": {"bid_count": 5, "ted": {"bid_count": 3},
                      "coverage": ["KOR/나라장터", "EU/TED(미검증)"]}},
        "pipeline": {
            "fetched_at": (now - dt.timedelta(hours=pipe_age_h)).isoformat(),
            "value": {"stages": {"X": "late_trial"},
                      "stage_counts": {"late_trial": 1},
                      "no_registered_trial": [], "lookup_failed": 0}},
    }


def _light():
    return {
        "readiness": {"countermeasure_count": 5, "covered": ["a", "b"],
                      "uncovered": ["c"], "unrated": ["d", "e"],
                      "coverage_rate": 0.4},
        "vaccine_chokepoints": {"single_source_count": 2,
                                "vaccine_type_count": 5},
    }


# ── 브리핑 배선 ───────────────────────────────────────────────────
def test_builder_wired_in_builders():
    assert "valhalla" in [name for name, _ in bs._BUILDERS]


def test_section_reads_stacked_values(monkeypatch):
    """쌓아둔 조달·파이프라인·준비태세를 읽기만 해서 섹션으로."""
    monkeypatch.setattr(vw, "_load_state", lambda: _state())
    monkeypatch.setattr(vw, "_light_layers", _light)
    sec = bs.build_valhalla_section("ko")
    assert sec["id"] == "valhalla" and sec["grade"] == "watch"
    assert "5건" in sec["lead"] and "후기임상" in sec["lead"]
    parts = [r["part"] for r in sec["rows"]]
    assert parts == ["procurement", "pipeline", "readiness",
                     "vaccine_chokepoints"]
    assert sec["rows"][0]["stale"] is False
    assert "경보가 아니" in sec["honesty"]
    assert "조달" in sec["data_source"] and "파이프라인" in sec["data_source"]


def test_section_omitted_when_nothing_stacked(monkeypatch):
    """쌓인 게 없으면 말없이 뺀다."""
    monkeypatch.setattr(vw, "_load_state", lambda: {})
    assert bs.build_valhalla_section("ko") is None


def test_section_marks_stale_parts(monkeypatch):
    """갱신 주기 2배 초과 조각은 stale."""
    monkeypatch.setattr(vw, "_load_state",
                        lambda: _state(proc_age_h=20.0, pipe_age_h=60.0))
    monkeypatch.setattr(vw, "_light_layers", _light)
    sec = bs.build_valhalla_section("ko")
    assert sec["rows"][0]["stale"] is True    # 조달 20h > 6h×2
    assert sec["rows"][1]["stale"] is True    # 파이프라인 60h > 24h×2


def test_section_without_readiness_db(monkeypatch):
    """DB 대응제 없으면 준비태세 줄만 빠지고 섹션은 나간다."""
    monkeypatch.setattr(vw, "_load_state", lambda: _state())
    monkeypatch.setattr(vw, "_light_layers",
                        lambda: {"readiness": {"error": "등록된 대응제가 없다"}})
    sec = bs.build_valhalla_section("ko")
    assert sec is not None
    assert "readiness" not in [r["part"] for r in sec["rows"]]


def test_section_english(monkeypatch):
    monkeypatch.setattr(vw, "_load_state", lambda: _state())
    monkeypatch.setattr(vw, "_light_layers", _light)
    sec = bs.build_valhalla_section("en")
    assert sec["title"] == "Countermeasure readiness"
    assert "Korean procurement" in sec["lead"]


# ── 경보 읽기 간선 ────────────────────────────────────────────────
def test_watch_line_summarizes_stacked_values(monkeypatch):
    monkeypatch.setattr(vw, "_load_state", lambda: _state())
    line = valhalla_watch_line()
    assert line.startswith("🛡️ 발할라:")
    assert "조달 5건/EU 3건" in line and "후기임상" in line
    assert "전 값" in line  # 나이를 붙인다


def test_watch_line_quiet_when_empty(monkeypatch):
    monkeypatch.setattr(vw, "_load_state", lambda: {})
    assert valhalla_watch_line() is None


def test_watch_line_survives_broken_state(monkeypatch):
    def boom():
        raise OSError("disk")
    monkeypatch.setattr(vw, "_load_state", boom)
    assert valhalla_watch_line() is None


# ── 수기 표 나이 ──────────────────────────────────────────────────
def test_table_age_counts_days():
    age = csp.table_age(today=dt.date(2026, 9, 1))
    assert age == {"verified_as_of": "2026-09-01", "age_days": 0, "stale": False}
    age = csp.table_age(today=dt.date(2026, 12, 1))
    assert age["age_days"] == 91 and age["stale"] is True


def test_stockpile_status_carries_table_age():
    out = csp.stockpile_status("ebola")
    assert out["has_global_stockpile"] is True
    assert out["table"]["verified_as_of"] == "2026-09-01"
    assert isinstance(out["table"]["age_days"], int)


def test_gap_report_flags_stale_table(monkeypatch):
    """재검토 주기를 넘긴 표는 보고에 stale+재확인 문구가 붙는다."""
    monkeypatch.setattr(csp, "TABLE_VERIFIED_AS_OF", "2020-01-01")
    report = csp.gap_report(["에볼라"])
    assert report["table_stale"] is True
    assert "재확인해야 한다" in " ".join(report["limits"])
    # 판정값 자체는 그대로 — stale은 표의 상태지 판정의 상태가 아니다
    assert report["covered"] == ["에볼라"]

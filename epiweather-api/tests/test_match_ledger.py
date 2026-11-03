"""대응제 매칭원장 — "오늘 이 비축이 이 변이를 막는가" (2026-11-03).

## 이 파일이 지키는 것

- holds/recheck/gap/unknown 4판정 — recheck는 변이 전이 + 커버일 때만.
- 변이 전이를 수치 할인으로 바꾸지 않는다(정성 플래그만).
- 같은 날 중복 기록 안 함(UNIQUE).
- 연결된 변이 감시 없으면 숨기지 않고 note에 명시.

isolated_db 픽스처라 운영 DB를 건드리지 않는다. 외부 HTTP 없음.
"""
from __future__ import annotations

import datetime as dt

from algorithms.match_ledger import (
    latest_verdicts,
    list_verdicts,
    record_daily_verdict,
)
from algorithms.variant_ledger import record_cycle as record_variants

UTC = dt.timezone.utc


def _cm(name="mRNA 백신", targets=("SARS-CoV-2",), eff=0.6, dom=True):
    return {"name": name, "type": "vaccine", "targets": list(targets),
            "declared_efficacy": eff, "domestic_producible": dom}


def _threat(pathogen="SARS-CoV-2", sev=0.6):
    return {"pathogen": pathogen, "severity": sev}


def _vsig(dominant="JN.1", new=()):
    return {"label": "SARS-CoV-2", "available": True, "build_updated": "2026-11-01",
            "n_recent_sequences": 100, "n_prior_sequences": 100,
            "dominant_clade": dominant, "dominant_share": 0.5,
            "new_clades": list(new), "new_clade_count": len(new), "note": None}


def _at(d, h=12):
    return dt.datetime(2026, 11, d, h, tzinfo=UTC)


def test_holds_when_covered_and_no_variant_transition(isolated_db):
    """커버 + 변이 전이 없음이면 holds."""
    record_variants({"ncov_open_global_6m": _vsig()}, now=_at(1))
    rows = record_daily_verdict([_cm()], [_threat()], now=_at(2))
    assert len(rows) == 1
    assert rows[0]["verdict"] == "holds"
    assert rows[0]["coverage_status"] == "covered"
    assert rows[0]["variant_build"] == "ncov_open_global_6m"


def test_recheck_when_variant_transitioned(isolated_db):
    """커버 + 최근 7일 내 우세 변경이면 recheck(수치 할인 아님)."""
    record_variants({"ncov_open_global_6m": _vsig(dominant="JN.1")}, now=_at(1))
    record_variants({"ncov_open_global_6m": _vsig(dominant="KP.3")}, now=_at(2))
    rows = record_daily_verdict([_cm()], [_threat()], now=_at(2))
    assert rows[0]["verdict"] == "recheck"
    assert rows[0]["best_efficacy"] == 0.6  # ★ 할인 안 함 — 선언값 그대로
    assert "재확인" in (rows[0]["note"] or "")


def test_gap_and_unknown(isolated_db):
    """미커버는 gap, 효능 미기재는 unknown."""
    rows = record_daily_verdict(
        [_cm(targets=("H5N1",)), _cm(name="미기재 백신", eff=None)],
        [_threat("H5N1", 0.8), _threat("MERS", 0.7), _threat("SARS-CoV-2")],
        now=_at(2),
    )
    by_p = {r["pathogen"]: r["verdict"] for r in rows}
    assert by_p["H5N1"] == "holds"
    assert by_p["MERS"] == "gap"
    assert by_p["SARS-CoV-2"] == "unknown"


def test_same_day_records_once(isolated_db):
    """같은 날 두 번 돌려도 1행."""
    record_daily_verdict([_cm()], [_threat()], now=_at(2, 1))
    rows = record_daily_verdict([_cm()], [_threat()], now=_at(2, 15))
    assert rows == []
    assert len(list_verdicts()) == 1


def test_unmapped_threat_says_so(isolated_db):
    """연결된 변이 감시 없으면 숨기지 않고 명시."""
    rows = record_daily_verdict([_cm(targets=("Ebola",))], [_threat("Ebola", 0.5)],
                              now=_at(2))
    assert rows[0]["variant_build"] is None
    assert rows[0]["variant_flag"] is None
    assert rows[0]["note"] == "연결된 변이 감시 없음"
    assert rows[0]["verdict"] == "holds"


def test_latest_verdicts_returns_newest_day(isolated_db):
    """화면 '오늘의 판정'은 가장 최근 판정일."""
    record_daily_verdict([_cm()], [_threat()], now=_at(1))
    record_daily_verdict([_cm()], [_threat("H5N1", 0.8)], now=_at(2))
    got = latest_verdicts()
    assert len(got) == 1 and got[0]["pathogen"] == "H5N1"


def test_endpoint_lists_verdicts(isolated_db):
    """핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다."""
    import main as main_mod

    record_daily_verdict([_cm()], [_threat()], now=_at(2))
    full = main_mod.valhalla_match_ledger()
    assert full["count"] == 1
    latest = main_mod.valhalla_match_ledger(latest_only=True)
    assert latest["count"] == 1
    assert latest["entries"][0]["verdict"] == "holds"
    scoped = main_mod.valhalla_match_ledger(verdict="gap")
    assert scoped["count"] == 0


def _fake_snapshot():
    return {
        "source": "test", "snapshot_date": "2026-01-01", "latest_year": 2023,
        "capacities": {"C05": "감시", "C06": "실험실"},
        "scores": {"KOR": {"2023": {"C05": 100, "C06": 100}},
                   "AAA": {"2023": {"C05": 20, "C06": 20}}},
    }


def test_country_posture_combines_capacity_and_verdicts(isolated_db, monkeypatch):
    """국가 현황판: 신고 역량 + 최신 매칭 판정. lru 캐시 무효화 포함."""
    import main as main_mod
    from algorithms import ihr_capacity as ic

    for fn in (ic._snapshot, ic.world_medians):
        clear = getattr(fn, "cache_clear", None)
        if clear:
            clear()
    monkeypatch.setattr(ic, "_snapshot", _fake_snapshot)
    record_daily_verdict([_cm()], [_threat()], now=_at(2))
    got = main_mod.valhalla_country_posture("kor")
    assert got["iso3"] == "KOR"
    assert got["capacity"]["available"] is True
    assert got["capacity"]["is_self_assessed"] is True
    assert got["verdict_counts"] == {"holds": 1}
    assert "자가평가" in got["note"]
    for fn in (ic._snapshot, ic.world_medians):
        clear = getattr(fn, "cache_clear", None)
        if clear:
            clear()


def test_country_posture_unknown_country_stays_unknown(isolated_db, monkeypatch):
    """수록 없는 나라는 0점이 아니라 모름."""
    import main as main_mod
    from algorithms import ihr_capacity as ic

    for fn in (ic._snapshot, ic.world_medians):
        clear = getattr(fn, "cache_clear", None)
        if clear:
            clear()
    monkeypatch.setattr(ic, "_snapshot", _fake_snapshot)
    got = main_mod.valhalla_country_posture("ZZZ")
    assert got["capacity"]["available"] is False
    for fn in (ic._snapshot, ic.world_medians):
        clear = getattr(fn, "cache_clear", None)
        if clear:
            clear()

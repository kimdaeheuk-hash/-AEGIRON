"""반증 질문 생성 — 판정을 뒤집을 증거를 묻는다 (2026-11-03).

규칙 기반·결정적. 외부 HTTP 없음. isolated_db 사용.
"""
from __future__ import annotations

import datetime as dt

from algorithms.refutation import questions_for_threat

UTC = dt.timezone.utc


def _seed(dbmod):
    dbmod.create_countermeasure(
        "타미플루 비축", "antiviral", ["H5N1"], 0.55, True,
        None, None, None)
    dbmod.create_countermeasure(
        "미기재 백신", "vaccine", ["MERS"], None, False,
        None, None, None)


def test_gap_asks_for_countermeasure(isolated_db):
    """미커버는 '어떤 대응제가 오면 바뀌나'를 묻는다."""
    import db as dbmod

    _seed(dbmod)
    out = questions_for_threat("Dengue")
    assert out["assessed"] is True
    assert out["coverage_status"] == "uncovered"
    assert any(q["flips_to"] == "covered" for q in out["questions"])


def test_unrated_asks_for_efficacy(isolated_db):
    """판정불가는 '어떤 효능 자료가 오면 서나'를 묻는다."""
    import db as dbmod

    _seed(dbmod)
    out = questions_for_threat("MERS")
    assert out["coverage_status"] == "unrated"
    assert any("미기재 백신" in q["evidence_needed"] for q in out["questions"])


def test_recheck_asks_for_reconfirmation(isolated_db):
    """recheck 판정은 효능 재측정을 묻는다."""
    import db as dbmod
    from algorithms.match_ledger import record_daily_verdict
    from algorithms.variant_ledger import record_cycle

    _seed(dbmod)
    dbmod.create_countermeasure(
        "mRNA 백신", "vaccine", ["SARS-CoV-2"], 0.6, True, None, None, None)
    sig = {"label": "x", "available": True, "build_updated": "2026-11-01",
           "n_recent_sequences": 10, "n_prior_sequences": 10,
           "dominant_share": 0.5, "new_clades": [], "new_clade_count": 0,
           "note": None}
    record_cycle({"ncov_open_global_6m": {**sig, "dominant_clade": "A"}},
                 now=dt.datetime(2026, 11, 1, 12, tzinfo=UTC))
    record_cycle({"ncov_open_global_6m": {**sig, "dominant_clade": "B"}},
                 now=dt.datetime(2026, 11, 2, 12, tzinfo=UTC))
    record_daily_verdict(
        dbmod.list_countermeasures(), [{"pathogen": "SARS-CoV-2"}],
        now=dt.datetime(2026, 11, 3, 12, tzinfo=UTC))
    out = questions_for_threat("SARS-CoV-2")
    assert out["latest_match_verdict"] == "recheck"
    assert any(q["flips_to"] == "holds" for q in out["questions"])


def test_no_stockpile_stays_unassessed(isolated_db):
    """비축 없으면 모름."""
    out = questions_for_threat("H5N1")
    assert out == {"pathogen": "H5N1", "assessed": False,
                   "reason": "등록된 비축 없음"}


def test_endpoint_returns_questions(isolated_db):
    """핸들러를 직접 부른다 — TestClient가 아니라 소켓이 필요 없다."""
    import db as dbmod
    import main as main_mod

    _seed(dbmod)
    out = main_mod.valhalla_refutation("H5N1")
    assert out["assessed"] is True
    assert out["coverage_status"] == "covered"

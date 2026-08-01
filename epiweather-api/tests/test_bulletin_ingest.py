"""보건 보고서 신호 → extracted_signals 적재. 스키마 의미에서 나온 제약을 고정한다.
실제 DB는 안 건드린다(dbmod 주입)."""
from __future__ import annotations

from algorithms import bulletin_ingest as bi


class FakeDB:
    """create_extracted_signal / list_recent_signals_by_source만 흉내내는 최소 스텁."""

    def __init__(self, existing=None):
        self.existing = existing or []
        self.rows = []

    def list_recent_signals_by_source(self, source, days=21, limit=50):
        return self.existing

    def create_extracted_signal(self, **kwargs):
        row = dict(kwargs)
        row["id"] = len(self.rows) + 1
        self.rows.append(row)
        return row


def _signal(**over) -> dict:
    base = {
        "source": "who_afro_bulletin", "disease": "Bundibugyo", "location": "DRC",
        "grade": "Grade 3", "layout": "who_afro_events",
        "metrics": {"total_cases": 1963, "deaths": 719},
        "signal_date": "2026-07-12", "raw_text": "DRC | Bundibugyo | 1 963 | 719",
        "cross_check": {"checked": True, "numbers_unverified": 0},
    }
    base.update(over)
    return base


# ── 국가코드 ──────────────────────────────────────────────────────
def test_iso3_resolves_common_who_spellings():
    assert bi.iso3_for("DRC") == "COD"
    assert bi.iso3_for("Democratic Republic of the Congo") == "COD"
    assert bi.iso3_for("Uganda") == "UGA"
    assert bi.iso3_for("France") == "FRA"


def test_iso3_handles_trailing_marks():
    """WHO 표는 'Country*'처럼 각주 표시가 붙어 온다."""
    assert bi.iso3_for("Democratic Republic of the Congo*") == "COD"


def test_iso3_returns_none_when_unknown():
    """모르면 비운다 — 틀린 국가코드는 지도·유입경로를 통째로 틀리게 한다."""
    assert bi.iso3_for("Atlantis") is None
    assert bi.iso3_for(None) is None


# ── 비질병 이벤트 차단 ────────────────────────────────────────────
def test_non_disease_events_are_not_ingested():
    """★핵심★ known_disease=False는 '설명 불가 → 즉시경보'를 뜻한다.
    사이클론·인도적 위기를 넣으면 가짜 즉시경보가 난다."""
    for label in ("Cyclone Gezani", "Complex Humanitarian crisis",
                  "Landslide", "Impact of Sudan crisis", "Flood"):
        assert bi.to_extracted_signal(_signal(disease=label)) is None


def test_disease_events_pass_the_filter():
    for label in ("Bundibugyo", "Cholera", "Measles", "Lassa fever"):
        assert bi.to_extracted_signal(_signal(disease=label)) is not None


def test_ingested_disease_rows_are_always_known():
    """질병으로 확인된 것만 들어오므로 known_disease는 항상 True여야 한다."""
    assert bi.to_extracted_signal(_signal())["known_disease"] is True


# ── severity는 WHO 등급 그대로 ────────────────────────────────────
def test_severity_uses_who_grade_not_our_judgement():
    assert bi.to_extracted_signal(_signal(grade="Grade 3"))["severity"] == ["grade_3"]
    assert bi.to_extracted_signal(_signal(grade="Protracted 2"))["severity"] == ["protracted_2"]
    assert bi.to_extracted_signal(_signal(grade="Ungraded"))["severity"] == ["ungraded"]
    assert bi.to_extracted_signal(_signal(grade=None))["severity"] == []


# ── 신뢰도는 교차검증 결과로 ──────────────────────────────────────
def test_trust_drops_when_numbers_unverified():
    verified = bi.to_extracted_signal(_signal())
    unverified = bi.to_extracted_signal(
        _signal(cross_check={"checked": True, "numbers_unverified": 3}))
    assert verified["source_trust"] == 0.90
    assert unverified["source_trust"] == 0.70


def test_trust_defaults_when_cross_check_missing():
    assert bi.to_extracted_signal(_signal(cross_check=None))["source_trust"] == 0.90


# ── signal_type ───────────────────────────────────────────────────
def test_signal_type_ongoing_only_for_monitored_events_table():
    """문서가 '감시 중 이벤트'로 정의한 표에서 온 것만 진행중. 급증·감소는
    이전 회차 비교가 없으므로 쓰지 않는다."""
    assert bi.to_extracted_signal(_signal())["signal_type"] == "진행중"
    assert bi.to_extracted_signal(_signal(layout=None))["signal_type"] == "불명"


def test_metrics_are_preserved_in_raw_text():
    """수치를 남겨야 나중에 사람이 원본과 대조할 수 있다."""
    raw = bi.to_extracted_signal(_signal())["raw_text"]
    assert "total_cases=1963" in raw and "deaths=719" in raw


# ── 적재·중복 ─────────────────────────────────────────────────────
def test_ingest_inserts_and_counts():
    db = FakeDB()
    out = bi.ingest([_signal(), _signal(disease="Cholera", location="Uganda")], dbmod=db)
    assert out["inserted"] == 2 and out["skipped_duplicate"] == 0
    assert out["iso3_resolved"] == 2
    assert {r["country_iso3"] for r in db.rows} == {"COD", "UGA"}


def test_ingest_skips_rows_already_present():
    """같은 보고서를 두 번 넣어도 중복이 쌓이면 안 된다."""
    existing = [{"disease": "Bundibugyo", "location": "DRC", "signal_date": "2026-07-12",
                 "raw_text": "DRC | Bundibugyo | 1 963 | 719 [deaths=719 total_cases=1963]"}]
    db = FakeDB(existing=existing)
    out = bi.ingest([_signal()], dbmod=db)
    assert out["inserted"] == 0 and out["skipped_duplicate"] == 1


def test_ingest_deduplicates_within_one_batch():
    db = FakeDB()
    out = bi.ingest([_signal(), _signal()], dbmod=db)
    assert out["inserted"] == 1 and out["skipped_duplicate"] == 1


def test_ingest_counts_non_disease_separately():
    db = FakeDB()
    out = bi.ingest([_signal(), _signal(disease="Cyclone Gezani")], dbmod=db)
    assert out["inserted"] == 1 and out["skipped_non_disease"] == 1


def test_ingest_survives_db_errors():
    class Broken(FakeDB):
        def create_extracted_signal(self, **kwargs):
            raise RuntimeError("DB down")

    out = bi.ingest([_signal()], dbmod=Broken())
    assert out["ok"] is True and out["failed"] == 1 and out["inserted"] == 0


def test_ingest_survives_dedup_query_failure():
    class NoList(FakeDB):
        def list_recent_signals_by_source(self, source, days=21, limit=50):
            raise RuntimeError("no table")

    out = bi.ingest([_signal()], dbmod=NoList())
    assert out["inserted"] == 1        # 중복조회 실패가 적재를 막으면 안 된다

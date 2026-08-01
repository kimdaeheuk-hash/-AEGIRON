"""보고서 자동 수집 — 비용이 걸린 부분(이미 적재한 회차는 PDF를 열지 않는다)을
특히 고정한다. 실제 IRIS·VLM 호출은 monkeypatch로 대체."""
from __future__ import annotations

import pytest

from algorithms import bulletin_collect as bc


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, tmp_path):
    """시도 기록 파일을 테스트마다 격리한다. 안 하면 실제 data/ 파일에 써서
    다음 테스트가 '이미 처리됨'으로 건너뛰고, 저장소도 오염된다(실제로 겪음)."""
    monkeypatch.setattr(bc, "STATE_FILE", tmp_path / "processed.json")


class FakeDB:
    def __init__(self, existing_dates=()):
        self.existing = [{"signal_date": d} for d in existing_dates]
        self.rows = []

    def list_recent_signals_by_source(self, source, days=21, limit=50):
        return self.existing

    def create_extracted_signal(self, **kwargs):
        row = dict(kwargs)
        self.rows.append(row)
        return row


def _report(number: int, issued: str) -> dict:
    return {"uuid": f"u{number}", "report_number": number, "issued": issued,
            "title": f"Weekly External Situation Report {number}",
            "pdf": {"name": f"sitrep{number}.pdf", "size_bytes": 100,
                    "url": f"https://iris.who.int/x/{number}"}}


def _patch(monkeypatch, reports, fetched=b"%PDF", tables_ok=True, signals=None):
    """수집 경로 전체를 스텁으로 대체하고, PDF를 몇 번 열었는지 센다."""
    opened = []
    import algorithms.who_iris as wi
    import algorithms.pdf_table_extract as pt
    import algorithms.bulletin_signals as bs

    monkeypatch.setattr(wi, "latest_situation_reports",
                        lambda limit=6, topic=None, search_size=30: reports)

    def fake_fetch(url, max_bytes=None):
        opened.append(url)
        return fetched

    monkeypatch.setattr(wi, "fetch_bytes", fake_fetch)
    monkeypatch.setattr(pt, "extract_tables",
                        lambda pdf, max_pages=4, **kw: {"ok": tables_ok, "pages": [],
                                                        "pages_selected": [1, 2]})
    monkeypatch.setattr(bs, "extract_signals",
                        lambda parsed, source=None, signal_date=None: {
                            "ok": True, "signal_count": len(signals or []),
                            "signals": [dict(s, signal_date=signal_date)
                                        for s in (signals or [])]})
    return opened


_SIGNAL = {"source": "who_sitrep_bundibugyo", "disease": "Bundibugyo", "location": "DRC",
           "grade": None, "layout": None, "metrics": {"confirmed": 3262, "deaths": 1437},
           "raw_text": "DRC row", "cross_check": {"checked": True, "numbers_unverified": 0}}


def test_already_ingested_reports_are_not_downloaded(monkeypatch):
    """★비용 핵심★ 이미 적재한 회차는 PDF를 열지도 않아야 한다 —
    표 추출이 회차당 VLM 4회 호출이라, 매일 확인해도 새 회차가 없으면 비용이 0이어야."""
    reports = [_report(11, "2026-07-26"), _report(10, "2026-07-19")]
    opened = _patch(monkeypatch, reports, signals=[_SIGNAL])
    db = FakeDB(existing_dates=["2026-07-26", "2026-07-19"])
    out = bc.collect_new_reports(db)
    assert out["skipped_existing"] == 2 and out["parsed"] == 0
    assert opened == []                       # 한 번도 안 열었다


def test_only_new_reports_are_parsed(monkeypatch):
    reports = [_report(11, "2026-07-26"), _report(10, "2026-07-19")]
    opened = _patch(monkeypatch, reports, signals=[_SIGNAL])
    db = FakeDB(existing_dates=["2026-07-19"])
    out = bc.collect_new_reports(db)
    assert out["parsed"] == 1 and out["skipped_existing"] == 1
    assert len(opened) == 1
    assert out["processed"][0]["issued"] == "2026-07-26"


def test_max_new_caps_a_single_run(monkeypatch):
    """첫 실행이 과거 회차를 전부 긁어 호출량이 튀는 걸 막는 안전장치."""
    reports = [_report(n, f"2026-07-{n:02d}") for n in range(1, 7)]
    opened = _patch(monkeypatch, reports, signals=[_SIGNAL])
    out = bc.collect_new_reports(FakeDB(), max_new=2)
    assert out["parsed"] == 2 and len(opened) == 2


def test_download_failure_is_counted_not_raised(monkeypatch):
    reports = [_report(11, "2026-07-26")]
    _patch(monkeypatch, reports, fetched=None, signals=[_SIGNAL])
    out = bc.collect_new_reports(FakeDB())
    assert out["ok"] is True and out["failed"] == 1 and out["parsed"] == 0


def test_table_extraction_failure_is_counted(monkeypatch):
    reports = [_report(11, "2026-07-26")]
    _patch(monkeypatch, reports, tables_ok=False, signals=[_SIGNAL])
    out = bc.collect_new_reports(FakeDB())
    assert out["failed"] == 1 and out["parsed"] == 0


def test_iris_failure_does_not_raise(monkeypatch):
    import algorithms.who_iris as wi

    def boom(**kw):
        raise RuntimeError("IRIS down")

    monkeypatch.setattr(wi, "latest_situation_reports", boom)
    out = bc.collect_new_reports(FakeDB())
    assert out["ok"] is False and "IRIS 조회 실패" in out["reason"]


def test_no_reports_returns_cleanly(monkeypatch):
    _patch(monkeypatch, [])
    out = bc.collect_new_reports(FakeDB())
    assert out["ok"] is True and out["parsed"] == 0 and out["reports_seen"] == 0


# ── 시도 기록(신호 0건 회차 재파싱 방지) ─────────────────────────
def test_zero_signal_report_is_not_reparsed(monkeypatch):
    """★비용 핵심★ 표를 못 찾아 신호 0건인 회차는 DB에 흔적이 없어 매일 다시
    파싱된다(실측에서 7/19 회차가 그랬다). 시도 자체를 기록해 막아야 한다."""
    reports = [_report(10, "2026-07-19")]

    opened = _patch(monkeypatch, reports, signals=[])       # 신호 0건
    out1 = bc.collect_new_reports(FakeDB())
    assert out1["parsed"] == 1 and out1["inserted"] == 0 and len(opened) == 1

    opened2 = _patch(monkeypatch, reports, signals=[])      # 같은 회차 재실행
    out2 = bc.collect_new_reports(FakeDB())
    assert out2["skipped_existing"] == 1 and out2["parsed"] == 0
    assert opened2 == []                                    # 다시 열지 않는다


def test_state_file_survives_corruption(monkeypatch, tmp_path):
    """기록 파일이 깨져도 수집은 계속돼야 한다."""
    bad = tmp_path / "processed.json"
    bad.write_text("{ 깨진 json", encoding="utf-8")
    monkeypatch.setattr(bc, "STATE_FILE", bad)
    assert bc.load_processed() == {}


def test_state_file_prunes_old_entries(monkeypatch, tmp_path):
    """기록이 무한히 자라지 않게 오래된 항목은 정리한다."""
    import datetime as dt
    monkeypatch.setattr(bc, "STATE_FILE", tmp_path / "processed.json")
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=500)).isoformat()
    fresh = dt.datetime.now(dt.timezone.utc).isoformat()
    bc.save_processed({"src|old": old, "src|new": fresh})
    assert set(bc.load_processed()) == {"src|new"}

"""발병국 대응 조치 — WHO DON 'Response' 단락 낱말 읽기 (2026-11-16, 캡틴 "발병국가가 어떻게 대처하고 있는가")."""
from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path

from algorithms import don_response as dr

MAIN = Path(__file__).resolve().parents[1] / "main.py"
TODAY = dt.date(2026, 11, 16)


def _item(**over):
    base = {
        "Title": "Ebola virus disease - Democratic Republic of the Congo",
        "PublicationDate": "2026-11-10T00:00:00Z",
        "DonId": "2026-DON630",
        "UrlName": "2026-DON630",
        "Response": (
            "<p>The Ministry of Health declared an outbreak on 5 November. Contact tracing is ongoing and "
            "1,200 contacts are being followed. Ring vaccination started in Ituri. "
            "WHO has deployed experts and is supporting infection prevention and control in health facilities.</p>"
        ),
    }
    base.update(over)
    return base


def test_reads_measures_with_evidence_sentence_and_source():
    out = dr.parse_responses({"value": [_item()]}, TODAY)
    by = {r["measure"]: r for r in out["rows"]}
    assert set(by) >= {"emergency_declared", "contact_tracing", "vaccination", "ipc", "who_support", "rapid_response"}
    assert all(r["iso3"] == "COD" for r in out["rows"])
    assert by["vaccination"]["evidence"] == "Ring vaccination started in Ituri."
    assert by["contact_tracing"]["evidence"].startswith("Contact tracing is ongoing")
    assert by["vaccination"]["url"].endswith("/item/2026-DON630")
    assert by["vaccination"]["published"] == "2026-11-10" and by["vaccination"]["country_from"] == "title"
    assert out["with_response"] == 1


def test_does_not_overclaim_from_single_vaccine_word():
    text = "No vaccine is currently licensed for this disease. Patients receive supportive care."
    assert [m["measure"] for m in dr.measures_in(text)] == []


def test_counts_missing_response_unreadable_country_and_old_items():
    items = [
        _item(Response=""),
        _item(Title="Yellow fever - Global", Overview="Cases were reported worldwide.", DonId="X1"),
        _item(PublicationDate="2020-01-01T00:00:00Z", DonId="X2"),
    ]
    out = dr.parse_responses({"value": items}, TODAY)
    assert out["rows"] == []
    assert out["no_response"] == 1 and out["no_country"] == 1 and out["out_of_window"] == 1


def test_multi_country_marks_shared():
    item = _item(Title="Marburg virus disease - Rwanda and Uganda")
    rows = dr.parse_responses({"value": [item]}, TODAY)["rows"]
    assert {r["iso3"] for r in rows} == {"RWA", "UGA"}
    assert all(r["shared_countries"] == 2 for r in rows)


def test_ingest_is_idempotent_and_endpoint_serves(isolated_db):
    from fastapi.testclient import TestClient

    import main

    first = dr.ingest_responses({"value": [_item()]}, TODAY)
    again = dr.ingest_responses({"value": [_item()]}, TODAY)
    assert first["new"] == first["rows"] > 0 and again["new"] == 0
    assert "조치" in dr.summary(first) and "대응 단락 있음 1" in dr.summary(first)
    body = TestClient(main.app).get("/api/response-measures?country=cod&days=800").json()
    assert body["country"] == "COD" and body["row_count"] == first["rows"]
    assert body["labels"]["vaccination"] == {"ko": "백신 접종", "en": "Vaccination", "fr": "Vaccination"}
    assert "효과는 판정하지 않음" in body["basis"]


def test_wired_into_21utc_slot_with_same_payload():
    src = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(src)
    slot = next(ast.unparse(n) for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef) and "ingest_don" in ast.unparse(n))
    assert "asyncio.to_thread(ingest_don, don_payload)" in slot
    assert "asyncio.to_thread(ingest_responses, don_payload)" in slot  # WHO 를 두 번 부르지 않음

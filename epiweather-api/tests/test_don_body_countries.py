"""WHO DON — 제목에 나라가 없으면 본문 앞부분에서 읽는다 (2026-10-25, 캡틴 지시 "국가 못 읽음 13건 본문에서 읽게").

운영 로그(10-20~10-24)가 못 읽은 항목에 `Summary` · `Overview` · `Epidemiology` 본문 필드가 있음을 보여 줬다.
고정하는 것: ① `Multi-locations` · 나라 없는 제목을 본문 앞 두 문장에서 읽는다 ② 기관 이름 속 나라(미국 CDC)는
안 읽는다 ③ 나라가 너무 많으면(Global 류) 못 읽음으로 남긴다 ④ 본문에서 읽은 선언은 출처에 `(본문)` 이 붙고
요약 줄에 건수가 나온다 ⑤ 본문으로 읽힌 발표는 못 읽은 목록에서 빠진다 ⑥ HTML 태그·엔티티를 걷는다.
"""
from __future__ import annotations

import datetime as dt

import db
from algorithms import who_don_declarations as don

TODAY = dt.date(2026, 10, 25)


def _item(title, summary, i="B1", date="2026-10-20", key="Summary"):
    return {"Title": title, "PublicationDate": f"{date}T00:00:00Z", "DonId": i, key: summary}


def test_multi_location_title_is_read_from_the_body():
    items = {"value": [
        _item("Hantavirus outbreak linked to cruise ship travel, Multi-locations",
              "<p>On 2 October 2026, the Ministry of Health of Argentina notified WHO of a cluster of hantavirus "
              "cases among passengers of a cruise ship.</p><p>The ship had called at ports in Chile.</p>"
              "<p>Later text mentions Brazil, Peru and Uruguay.</p>")]}
    out = don.parse_items(items, TODAY)
    assert [d["iso3"] for d in out["declarations"]] == ["ARG", "CHL"]
    assert all(d["source"].endswith("(본문)") for d in out["declarations"])
    assert out["declarations"][0]["disease"] == "Hantavirus outbreak linked to cruise ship travel"
    assert out["skipped"] == {"본문에서 나라 읽음": 1}
    assert out["unread"] == [] and out["readable_keys"] == ["B1"]


def test_title_without_any_country_uses_the_body():
    out = don.parse_items({"value": [_item("Avian Influenza A(H9N2)",
                                           "Between 1 and 30 September 2026, the National Health Commission of China "
                                           "reported two human cases.", key="Overview")]}, TODAY)
    assert [(d["disease"], d["iso3"]) for d in out["declarations"]] == [("Avian Influenza A(H9N2)", "CHN")]


def test_agency_names_are_not_outbreak_countries():
    out = don.parse_items({"value": [_item("Measles - Multi-locations",
                                           "WHO and the United States Centers for Disease Control and Prevention "
                                           "are supporting Kenya.")]}, TODAY)
    assert [d["iso3"] for d in out["declarations"]] == ["KEN"]


def test_too_many_countries_stays_unread():
    many = "Cases were reported in Brazil, Peru, Colombia, Bolivia, Ecuador, Venezuela and Guyana."
    out = don.parse_items({"value": [_item("Yellow fever - Global", many)]}, TODAY)
    assert out["declarations"] == [] and out["skipped"] == {"국가 못 읽음": 1}
    assert [u["key"] for u in out["unread"]] == ["B1"]


def test_no_body_stays_unread_as_before():
    out = don.parse_items({"value": [{"Title": "Yellow fever - Global", "PublicationDate": "2026-10-20",
                                      "DonId": "B2"}]}, TODAY)
    assert out["skipped"] == {"국가 못 읽음": 1}


def test_ingest_removes_body_read_items_from_the_unread_list(isolated_db):
    db.record_ground_truth_unread("who_don", [{"key": "B1", "published": "2026-10-20", "title": "x",
                                               "reason": "국가 못 읽음"}], [])
    payload = {"value": [_item("Hantavirus outbreak linked to cruise ship travel, Multi-locations",
                               "The Ministry of Health of Argentina notified WHO.")]}
    out = don.ingest_don(payload, TODAY)
    assert out["등재"] == 1 and "본문에서 나라 읽음 1" in don.summary(out)
    assert db.list_ground_truth_unread(("who_don",)) == []


def test_full_text_scanner_finds_every_country_and_prefers_long_names():
    from algorithms.country_resolve import countries_in_text
    assert countries_in_text("Guinea-Bissau, Guinea and Equatorial Guinea") == ["GNB", "GIN", "GNQ"]
    assert countries_in_text("Cases in Nigeria and Niger.") == ["NGA", "NER"]
    assert countries_in_text("Argentina reported a cluster aboard a cruise ship.") == ["ARG"]


def test_body_text_takes_two_sentences_and_strips_markup():
    text = don.body_text({"Summary": "<p>One &amp; two. Three.</p> <p>Four.</p>"})
    assert text == "One & two. Three."

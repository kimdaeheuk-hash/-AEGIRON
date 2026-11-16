"""발병 타임라인 표시 필드 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데').

event_name 은 예측 채점의 대조 키라 그대로 두고, 화면이 제 언어로 다시 쓰도록
iso3 · year · disease_key 만 덧붙인다. 모르는 질병은 null(지어내지 않음).
"""
from __future__ import annotations


def test_timeline_rows_carry_display_fields_without_touching_event_name(isolated_db):
    db = isolated_db
    mixed = "Ebola disease caused by Bundibugyo virus, Democratic Republic of the Congo 에볼라 Kenya and Nigeria 2026"
    db.upsert_timeline_event("eboladisease_ken_2026", mixed, "2026-11-01", "official_declaration",
                             "d", "who_don", "official_live")
    db.upsert_timeline_event("shamondavirusinhuman_fra_2026", "Shamonda virus in human France 2026",
                             "2026-10-01", "official_declaration", "d", "who_don", "official_live")
    db.upsert_timeline_event("covid19_wuhan_2019", "코로나19 우한 초기 2019-2020", "2019-12-31",
                             "official_declaration", "d", "who", "who")
    rows = {r["event_id"]: r for r in db.list_timeline_events()}

    ebola = rows["eboladisease_ken_2026"]
    assert ebola["event_name"] == mixed  # 대조 키는 그대로
    assert (ebola["iso3"], ebola["year"], ebola["disease_key"]) == ("KEN", 2026, "에볼라")

    shamonda = rows["shamondavirusinhuman_fra_2026"]
    assert (shamonda["iso3"], shamonda["disease_key"]) == ("FRA", None)  # 모르는 질병은 지어내지 않음

    seed = rows["covid19_wuhan_2019"]
    assert (seed["iso3"], seed["year"]) == (None, None)  # 꼬리 모양이 아니면 판정 안 함
    assert seed["disease_key"] == "코로나19"

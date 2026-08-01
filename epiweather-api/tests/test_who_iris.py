"""WHO IRIS 수집 — 검색·번들 파싱·필터링을 결정론적으로 검증.
실제 IRIS 호출은 monkeypatch로 대체(네트워크 의존 금지)."""
from __future__ import annotations

from algorithms import who_iris as wi


def _search_payload(items: list[dict]) -> dict:
    return {"_embedded": {"searchResult": {"_embedded": {"objects": [
        {"_embedded": {"indexableObject": it}} for it in items]}}}}


def _item(uuid: str, name: str, issued: str = "2026-03-22") -> dict:
    return {"uuid": uuid, "name": name,
            "metadata": {"dc.date.issued": [{"value": issued}]}}


def test_search_items_extracts_fields(monkeypatch):
    monkeypatch.setattr(wi, "_get", lambda p, **kw: _search_payload([
        _item("u1", "Weekly Bulletin on Outbreak and other Emergencies: Week 12")]))
    items = wi.search_items("x")
    assert items[0]["uuid"] == "u1" and items[0]["issued"] == "2026-03-22"
    assert "Week 12" in items[0]["title"]


def test_search_items_returns_empty_on_failure(monkeypatch):
    def boom(p, **kw):
        raise RuntimeError("IRIS down")

    monkeypatch.setattr(wi, "_get", boom)
    assert wi.search_items("x") == []          # 예외를 던지지 않는다


def test_search_items_skips_objects_without_uuid(monkeypatch):
    monkeypatch.setattr(wi, "_get", lambda p, **kw: _search_payload([
        {"name": "uuid 없음"}, _item("u2", "제목")]))
    assert [i["uuid"] for i in wi.search_items("x")] == ["u2"]


# ── 번들 → 비트스트림 ─────────────────────────────────────────────
def _bundles_and_streams(monkeypatch, streams_by_bundle: dict[str, list[dict]]):
    def fake(path, **kw):
        if path.endswith("/bundles"):
            return {"_embedded": {"bundles": [
                {"uuid": f"b-{n}", "name": n} for n in streams_by_bundle]}}
        bundle = path.split("/bundles/")[1].split("/")[0].replace("b-", "")
        return {"_embedded": {"bitstreams": streams_by_bundle[bundle]}}

    monkeypatch.setattr(wi, "_get", fake)


def _bs(name: str, size: int = 100) -> dict:
    return {"name": name, "sizeBytes": size,
            "_links": {"content": {"href": f"https://iris.who.int/x/{name}"}}}


def test_item_files_picks_pdf_and_text(monkeypatch):
    _bundles_and_streams(monkeypatch, {
        "ORIGINAL": [_bs("OEW12-1622032026.pdf", 2452909)],
        "TEXT": [_bs("OEW12-1622032026.pdf.txt", 72069)],
        "THUMBNAIL": [_bs("thumb.jpg")],
        "LICENSE": [_bs("license.txt")],
    })
    files = wi.item_files("u1")
    assert files["pdf"]["name"].endswith(".pdf")
    assert files["text"]["name"].endswith(".txt")
    # THUMBNAIL·LICENSE 번들은 애초에 훑지 않는다
    assert {e["bundle"] for e in files["all"]} == {"ORIGINAL", "TEXT"}


def test_item_files_survives_failure(monkeypatch):
    def boom(path, **kw):
        raise RuntimeError("down")

    monkeypatch.setattr(wi, "_get", boom)
    assert wi.item_files("u1") == {"pdf": None, "text": None, "all": []}


# ── 주간보고서 선별 ───────────────────────────────────────────────
def test_latest_bulletins_filters_out_other_publications(monkeypatch):
    """검색어만으로는 인플루엔자 주보 등이 섞여 나온다 — 제목과 OEW 파일명으로
    걸러 엉뚱한 문서를 신호로 넣지 않아야 한다."""
    monkeypatch.setattr(wi, "search_items", lambda q, size=25: [
        {"uuid": "u1", "title": "Weekly Bulletin on Outbreak and other Emergencies: Week 12",
         "issued": "2026-03-22", "language": "en"},
        {"uuid": "u2", "title": "Influenza Weekly Bulletin", "issued": "2026-03-20",
         "language": "en"},
        {"uuid": "u3", "title": "Weekly Bulletin on Outbreak and other Emergencies: Week 11",
         "issued": "2026-03-15", "language": "en"},
    ])
    files = {"u1": {"pdf": _bs("OEW12-1622032026.pdf"), "text": None, "all": []},
             "u2": {"pdf": _bs("F_wk21_2026_Flu_Bulletin.pdf"), "text": None, "all": []},
             "u3": {"pdf": _bs("F_wk11_Flu.pdf"), "text": None, "all": []}}
    monkeypatch.setattr(wi, "item_files", lambda uuid: files[uuid])
    got = wi.latest_outbreak_bulletins(limit=5)
    # u2는 제목에서, u3는 파일명 규칙(OEW*)에서 걸러진다
    assert [b["uuid"] for b in got] == ["u1"]


def test_latest_bulletins_respects_limit(monkeypatch):
    monkeypatch.setattr(wi, "search_items", lambda q, size=25: [
        {"uuid": f"u{i}", "title": f"Weekly Bulletin on Outbreak and other Emergencies: Week {i}",
         "issued": "2026-03-01", "language": "en"} for i in range(1, 6)])
    monkeypatch.setattr(wi, "item_files",
                        lambda uuid: {"pdf": _bs("OEW01-x.pdf"), "text": None, "all": []})
    assert len(wi.latest_outbreak_bulletins(limit=2)) == 2


def test_bulletin_archive_extracts_week_number(monkeypatch):
    """dc.date.issued가 흔들리는 항목이 있어 제목에서 주차를 따로 뽑아야 한다."""
    monkeypatch.setattr(wi, "search_items", lambda q, size=60: [
        {"uuid": "u1", "title": "Weekly Bulletin on Outbreak and other Emergencies: Week 21",
         "issued": "2026-03-24", "language": "en"},
        {"uuid": "u2", "title": "Some other WHO report", "issued": "2026-03-01", "language": "en"},
    ])
    archive = wi.bulletin_archive()
    assert len(archive) == 1 and archive[0]["week"] == 21

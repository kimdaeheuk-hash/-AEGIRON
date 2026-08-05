"""WHO 상황보고서 표 인식 실패 2건의 회귀 방지.

실측 배경(WHO 외부 상황보고서 11회차, 2026-05-18~07-26 전수 재현):
  · 2026-05-31 → 신호 0건. 국가 칸의 각주 번호("1 Democratic Republic of the Congo")를
    _to_number가 1.0으로 읽어 '숫자면 라벨이 아니다' 규칙에 걸려 행이 통째로 버려졌다.
  · 2026-07-19 → 신호 0건. 국가 요약표가 0페이지에 있는데 페이지 점수 순위에서
    상세표에 밀려 VLM에 보내지지도 않았다. 상세표는 국가 칸이 원본 병합셀이라
    빈칸으로 와서 44행에서 신호가 하나도 안 나온다.
수정 후 11/11 회차에서 국가 신호가 나오고, DRC 확진 추이가 105→321→550→808→1048→
1307→1624→1963→2423→3262으로 단조증가한다(정합성 확인).
"""
from __future__ import annotations

from algorithms.bulletin_signals import (
    rows_to_signals, map_header, looks_like_epi_table,
    _is_pure_number, _strip_footnote, _is_stat_banner,
)
from algorithms.pdf_table_extract import find_table_pages, _ALWAYS_INCLUDE_FIRST

BS = chr(92)   # LaTeX 줄바꿈이 헤더 끝에 남는다


# ── 각주가 붙은 국가명 ────────────────────────────────────────────────
def test_footnote_prefixed_country_is_not_treated_as_a_number():
    """★핵심 회귀★ _to_number는 의도적으로 관대하다('5 Suspected' → 5.0). 그걸로
    라벨을 판정하면 각주 붙은 국가명이 숫자로 읽혀 행이 사라진다."""
    assert _is_pure_number("1 Democratic Republic of the Congo") is False
    assert _is_pure_number("Uganda2") is False
    assert _is_pure_number("321") is True
    assert _is_pure_number("15.0%") is True
    assert _is_pure_number("1 170") is True      # WHO는 천단위에 공백을 쓴다
    assert _is_pure_number("") is False


def test_footnote_markers_are_stripped_from_labels():
    assert _strip_footnote("1 Democratic Republic of the Congo") == "Democratic Republic of the Congo"
    assert _strip_footnote("2 Uganda") == "Uganda"
    assert _strip_footnote("Uganda2") == "Uganda"
    # 이름의 일부인 숫자는 지키다 — 'COVID-19'의 19를 깎으면 병명이 망가진다.
    assert _strip_footnote("COVID-19") == "COVID-19"


def test_2026_05_31_summary_table_yields_signals():
    """실제로 0건이던 표. 헤더가 LaTeX 줄바꿈으로 11칸, 데이터는 8칸이다."""
    rows = [
        ["Country", "Confirmed Cases", "Confirmed Deaths", "Probable Cases", "Probable Deaths",
         "**Total Cases (Confirmed " + BS, "Probable)**",
         "**Total Deaths (Confirmed " + BS, "Probable)**",
         "**CFR (%) Confirmed " + BS, "Probable**"],
        ["1 Democratic Republic of the Congo", "321", "48", "-", "", "321", "48", "15.0%"],
        ["2 Uganda", "11", "1", "1", "1", "12", "2", "16.7%"],
    ]
    sigs = rows_to_signals(rows, signal_date="2026-05-31")
    assert len(sigs) == 2
    drc = next(s for s in sigs if "Congo" in (s["location"] or ""))
    assert drc["location"] == "Democratic Republic of the Congo"   # 각주 없이
    assert drc["metrics"]["confirmed"] == 321.0
    assert drc["metrics"]["deaths"] == 48.0
    assert drc["metrics"]["cfr"] == 0.15


def test_2026_05_18_suspected_column_table_yields_signals():
    """1회차는 '의심' 열이 앞에 오고 국가명 뒤에 각주가 붙는다("Uganda2")."""
    rows = [
        ["Country", "1Suspected Cases", "1Suspected Deaths", "CFR (%) Suspected",
         "Confirmed Cases", "Confirmed Deaths", "CFR (%) Confirmed"],
        ["Democratic Republic of the Congo", "516", "131", "25.4%", "33", "4", "12.1%"],
        ["Uganda2", "-", "-", "-", "2", "1", "50.0%"],
        ["Total", "516", "131", "25.4%", "35", "5", "14.3%"],
    ]
    sigs = rows_to_signals(rows, signal_date="2026-05-18")
    assert [s["location"] for s in sigs] == ["Democratic Republic of the Congo", "Uganda"]
    # 의심 수치가 확진으로 둔갑하면 안 된다 — 축이 다르다.
    drc = sigs[0]
    assert drc["metrics"]["confirmed"] == 33.0
    assert drc["metrics"]["probable_total_cases"] == 516.0
    # 합계 행은 나라가 아니다 — 'Total'이라는 유령 국가가 생기면 추이가 오염된다.
    assert all(s["location"] != "Total" for s in sigs)


# ── 표지 통계 배너를 표로 오인하지 않기 ────────────────────────────────
def test_key_figures_banner_is_not_an_epi_table():
    """★회귀★ VLM은 표지 통계 배너도 표로 내보낸다. 헤더로 읽으면
    "Active Cases in Isolation"이 지역 라벨이 되어 유령 지역 신호가 생긴다."""
    banner = [
        ["5 Provinces 47 Health Zones Affected", "4 Provinces 40 Health Zones Active Transmission",
         "469 Cases Recovered", "87.3% Bed Occupancy", "10 519 Contacts to follow"],
        ["734 Active Cases", "121 Health Worker Cases", "36 Health Worker Deaths",
         "841 Bed Capacity", "18 Testing Laboratories"],
    ]
    assert _is_stat_banner(banner[0]) is True
    assert looks_like_epi_table(banner) is False
    assert rows_to_signals(banner, signal_date="2026-07-19") == []


def test_real_table_header_is_not_mistaken_for_a_banner():
    """숫자가 든 열 이름이 있어도('Cases (last 21 d)') 과반이 아니면 진짜 표다."""
    header = ["Country", "Province / Region", "Health zone / district", "Cum. cases",
              "Cum. deaths", "CFR %", "Cases (last 21 d)", "Deaths (last 21 d)",
              "Date last case", "Days since last case"]
    assert _is_stat_banner(header) is False


# ── 국가 열 vs 하위행정구역 열 ────────────────────────────────────────
def test_country_column_label_must_resolve_to_a_country():
    """국가 축 표라고 판정했는데 어느 나라로도 안 읽히면 표 오독이다."""
    rows = [["Country", "Confirmed Cases", "Confirmed Deaths"],
            ["Active Cases in Isolation", "723", "12"],
            ["Uganda", "20", "2"]]
    sigs = rows_to_signals(rows, signal_date="2026-07-26")
    assert [s["location"] for s in sigs] == ["Uganda"]


def test_subnational_labels_are_kept():
    """지역 열은 국가로 안 읽혀도 버리지 않는다 — 하위 단위 신호는 그 자체로 쓸모 있다."""
    rows = [["Province", "Confirmed cases", "Confirmed deaths"],
            ["Ituri", "639", "211"]]
    assert map_header(rows[0])["label_kind"] == "subnational"
    sigs = rows_to_signals(rows, signal_date="2026-07-19")
    assert [s["location"] for s in sigs] == ["Ituri"]


# ── 페이지 선택 ──────────────────────────────────────────────────────
def test_first_page_is_always_selected(monkeypatch):
    """★회귀★ 국가 요약표는 실측 11회차 **전부 0페이지**에 있는데, 점수순으로는
    보건지역 상세표(숫자가 훨씬 많다)에 밀려 3회차에서 빠졌다. 상세표는 국가 칸이
    병합셀이라 빈칸으로 와서 국가 신호를 못 만든다 — 요약표를 잃으면 그 회차가
    통째로 0건이 된다."""
    import algorithms.pdf_table_extract as pte

    class _Page:
        def __init__(self, text):
            self._t = text

        def get_text(self):
            return self._t

    class _Doc:
        # 0페이지는 표 후보 기준은 넘지만 점수가 낮고, 뒤 페이지들이 숫자로 압도한다
        # (WHO 상황보고서의 실제 배치: 요약표 vs 보건지역 상세표).
        pages = [_Page("Country confirmed deaths cases fatality outbreak "
                       + " ".join(f"{i}00" for i in range(10)))] + \
                [_Page("confirmed deaths cases " + " ".join(f"{i}0 000" for i in range(40)))
                 for _ in range(5)]
        page_count = 6

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __iter__(self):
            return iter(self.pages)

    monkeypatch.setattr(pte, "page_count", lambda b: 6)
    import sys
    import types
    fake = types.ModuleType("fitz")
    fake.open = lambda **kw: _Doc()
    monkeypatch.setitem(sys.modules, "fitz", fake)

    chosen = find_table_pages(b"x", limit=3)
    assert 0 in chosen, f"0페이지가 빠졌다: {chosen}"
    assert len(chosen) == 3


def test_always_include_first_is_documented_constant():
    assert _ALWAYS_INCLUDE_FIRST >= 1


def test_empty_cover_page_is_not_pinned(monkeypatch):
    """표지·목차처럼 표 후보 기준도 못 넘는 앞장은 고정하지 않는다 —
    문서마다 VLM 호출 1회가 헛나가기 때문이다(요약표가 점수 경쟁에서 지는 것만 막으면 된다)."""
    import sys
    import types

    import algorithms.pdf_table_extract as pte

    class _Page:
        def __init__(self, text):
            self._t = text

        def get_text(self):
            return self._t

    thin = _Page("표지와 목차뿐")
    dense = _Page(" ".join(["1,234"] * 12) + " cases deaths confirmed case fatality outbreak")

    class _Doc:
        pages = [thin, thin, dense, thin, dense]
        page_count = 5

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __iter__(self):
            return iter(self.pages)

    monkeypatch.setattr(pte, "page_count", lambda b: 5)
    fake = types.ModuleType("fitz")
    fake.open = lambda **kw: _Doc()
    monkeypatch.setitem(sys.modules, "fitz", fake)
    assert find_table_pages(b"x", limit=8) == [2, 4]


# ── VLM 비결정성 대응 ────────────────────────────────────────────────
def test_empty_report_is_retried_once(monkeypatch, isolated_db):
    """★회귀★ VLM은 같은 페이지를 같은 조건으로 보내도 매번 같은 표를 주지 않는다.
    실측(2026-07-26): 국가 요약표가 어떤 실행에선 응답에서 통째로 빠져 신호 0건이
    났는데, 그 페이지만 세 번 다시 보내니 세 번 다 정상 3건이 나왔다.
    회차 전체가 0건이면 한 번 다시 시도해야 그 주 보고서를 안 잃는다."""
    from algorithms import bulletin_collect as bc

    calls = {"extract": 0}
    good = {"ok": True, "pages_selected": [0],
            "pages": [{"page": 1, "ok": True,
                       "tables": [{"rows": [["Country", "Confirmed Cases", "Confirmed Deaths"],
                                            ["Uganda", "20", "2"]]}]}]}
    empty = {"ok": True, "pages_selected": [0],
             "pages": [{"page": 1, "ok": True, "tables": []}]}

    def fake_extract(pdf, max_pages=4):
        calls["extract"] += 1
        return empty if calls["extract"] == 1 else good      # 첫 호출만 비어 있음

    monkeypatch.setattr("algorithms.pdf_table_extract.extract_tables", fake_extract)
    monkeypatch.setattr("algorithms.who_iris.fetch_bytes", lambda url: b"%PDF")
    monkeypatch.setattr("algorithms.who_iris.latest_situation_reports",
                        lambda **kw: [{"report_number": 1, "issued": "2026-07-26",
                                       "pdf": {"url": "http://x/1.pdf"}}])
    monkeypatch.setattr(bc, "load_processed", lambda: {})
    monkeypatch.setattr(bc, "save_processed", lambda s: None)

    out = bc.collect_new_reports(max_new=1)
    assert calls["extract"] == 2, "0건인데 재시도하지 않았다"
    assert out["processed"][0]["signals_found"] > 0
    assert out["processed"][0]["retried_empty"] is True


def test_successful_report_is_not_retried(monkeypatch, isolated_db):
    """신호가 나온 회차는 다시 부르지 않는다 — 재시도 비용은 실패했을 때만 든다."""
    from algorithms import bulletin_collect as bc

    calls = {"extract": 0}
    good = {"ok": True, "pages_selected": [0],
            "pages": [{"page": 1, "ok": True,
                       "tables": [{"rows": [["Country", "Confirmed Cases", "Confirmed Deaths"],
                                            ["Uganda", "20", "2"]]}]}]}

    def fake_extract(pdf, max_pages=4):
        calls["extract"] += 1
        return good

    monkeypatch.setattr("algorithms.pdf_table_extract.extract_tables", fake_extract)
    monkeypatch.setattr("algorithms.who_iris.fetch_bytes", lambda url: b"%PDF")
    monkeypatch.setattr("algorithms.who_iris.latest_situation_reports",
                        lambda **kw: [{"report_number": 1, "issued": "2026-07-26",
                                       "pdf": {"url": "http://x/1.pdf"}}])
    monkeypatch.setattr(bc, "load_processed", lambda: {})
    monkeypatch.setattr(bc, "save_processed", lambda s: None)

    out = bc.collect_new_reports(max_new=1)
    assert calls["extract"] == 1
    assert out["processed"][0]["retried_empty"] is False

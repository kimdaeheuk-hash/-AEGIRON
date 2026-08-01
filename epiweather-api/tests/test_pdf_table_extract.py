"""보건 보고서 PDF 표 추출 — LaTeX 표 파싱과 교차검증을 결정론적으로 검증.
실제 VLM 호출·PDF 렌더링은 monkeypatch로 대체(네트워크·바이너리 의존 금지)."""
from __future__ import annotations

from algorithms import pdf_table_extract as pt


# ── LaTeX tabular 파싱 ────────────────────────────────────────────
REAL_TABLE = (
    "\\begin{tabular}{ccccccccc}\n"
    "**Event** & **Total Cases** & **Confirmed cases** & **Deaths** & **Case Fatality Rate**\\\\\n"
    "Mpox & 1,170 & 1,170 & 19 & 1.6%\\\\\n"
    "Cholera & 40 & 2 & 1 & 2.5%\\\\\n"
    "\\end{tabular}"
)


def test_parse_latex_table_recovers_rows_and_columns():
    rows = pt.parse_latex_table(REAL_TABLE)
    assert rows[0] == ["Event", "Total Cases", "Confirmed cases", "Deaths", "Case Fatality Rate"]
    assert rows[1] == ["Mpox", "1,170", "1,170", "19", "1.6%"]
    assert rows[2][0] == "Cholera" and rows[2][3] == "1"


def test_parse_latex_table_strips_bold_and_superscript():
    rows = pt.parse_latex_table(
        "\\begin{tabular}{cc}**WEEK 28: 5<sup>th</sup> July** & **KENYA**\\\\\\end{tabular}")
    assert rows == [["WEEK 28: 5 July", "KENYA"]]


def test_parse_latex_table_handles_missing_wrapper():
    """\\begin{tabular} 없이 행만 와도 파싱되어야 한다(모델 출력이 흔들릴 때 대비)."""
    rows = pt.parse_latex_table("Mpox & 1,170 & 19\\\\\nCholera & 40 & 1\\\\")
    assert rows == [["Mpox", "1,170", "19"], ["Cholera", "40", "1"]]


def test_parse_latex_table_empty_input():
    assert pt.parse_latex_table("") == []


def test_parse_latex_table_drops_layout_commands():
    """★회귀★ \\multicolumn 같은 서식 명령이 데이터 행처럼 섞여 나오던 문제
    (실제 WHO 보고서 파싱에서 확인됨)."""
    rows = pt.parse_latex_table(
        "\\begin{tabular}{ccc}\n"
        "Mpox & 1,170 & 19\\\\\n"
        "\\multicolumn{9}{c}\\\\\n"
        "Cholera & 40 & 1\\\\\n"
        "\\end{tabular}")
    assert rows == [["Mpox", "1,170", "19"], ["Cholera", "40", "1"]]


def test_parse_latex_table_unescapes_percent():
    """★회귀★ 81.5\\% 가 그대로 새어나오던 문제."""
    rows = pt.parse_latex_table("DRC & 1,963 & 81.5\\% & 33\\\\")
    assert rows == [["DRC", "1,963", "81.5%", "33"]]


# ── 교차검증 ──────────────────────────────────────────────────────
def test_cross_check_flags_numbers_absent_from_raw_text():
    """원문에 없는 숫자는 VLM 오독 후보로 잡아야 한다."""
    rows = [["Mpox", "1,170", "19"], ["Cholera", "9999", "40"]]
    out = pt.cross_check_numbers(rows, "Mpox 1170 cases 19 deaths; Cholera 40 cases")
    assert out["checked"] is True
    assert out["numbers_unverified"] == 1
    assert out["unverified_samples"] == ["9999"]
    assert out["numbers_verified"] == 3


def test_cross_check_normalizes_thousands_separator():
    out = pt.cross_check_numbers([["1,170"]], "total 1170 cases")
    assert out["numbers_unverified"] == 0


def test_cross_check_ignores_single_digits():
    """한 자리 수는 우연히 일치하므로 검증 대상에서 제외한다."""
    out = pt.cross_check_numbers([["5"]], "no digits here")
    assert out["numbers_verified"] == 0 and out["numbers_unverified"] == 0


def test_cross_check_skipped_without_raw_text():
    out = pt.cross_check_numbers([["1,170"]], "")
    assert out["checked"] is False and "생략" in out["reason"]


# ── 오케스트레이터 ────────────────────────────────────────────────
def _stub(monkeypatch, blocks, pages=2, raw="Mpox 1170 cases 19 deaths"):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(pt, "page_count", lambda b: pages)
    monkeypatch.setattr(pt, "render_page_png", lambda b, i, dpi=150: b"png")
    monkeypatch.setattr(pt, "pdftotext_raw", lambda b: raw)
    monkeypatch.setattr(pt, "_parse_page", lambda png, key: blocks)


def test_extract_tables_returns_structured_rows(monkeypatch):
    _stub(monkeypatch, [{"type": "Table", "text": REAL_TABLE},
                        {"type": "Text", "text": "Kenya is responding to multiple emergencies"}])
    out = pt.extract_tables(b"%PDF", max_pages=1)
    assert out["ok"] is True and out["pages_parsed"] == 1
    page = out["pages"][0]
    assert page["table_count"] == 1
    assert page["tables"][0]["rows"][1][0] == "Mpox"
    assert page["text_blocks"][0]["type"] == "Text"


def test_extract_tables_respects_max_pages(monkeypatch):
    _stub(monkeypatch, [{"type": "Table", "text": REAL_TABLE}], pages=13)
    out = pt.extract_tables(b"%PDF", max_pages=2)
    assert out["pages_attempted"] == 2 and out["pdf_pages"] == 13


def test_extract_tables_without_key_returns_not_ok(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    out = pt.extract_tables(b"%PDF")
    assert out["ok"] is False and "NVIDIA_API_KEY" in out["reason"]


def test_extract_tables_survives_page_failure(monkeypatch):
    _stub(monkeypatch, [], pages=1)

    def boom(png, key):
        raise RuntimeError("VLM down")

    monkeypatch.setattr(pt, "_parse_page", boom)
    out = pt.extract_tables(b"%PDF", max_pages=1)
    assert out["ok"] is False and out["pages_failed"] == 1


def test_extract_tables_marks_machine_extracted(monkeypatch):
    """추출값이 사람 검증본이 아님을 결과가 항상 명시해야 한다."""
    _stub(monkeypatch, [{"type": "Table", "text": REAL_TABLE}], pages=1)
    out = pt.extract_tables(b"%PDF", max_pages=1)
    assert out["is_machine_extracted"] is True
    assert "오독" in out["disclaimer"]


# ── 표 페이지 자동 선택 ───────────────────────────────────────────
def test_find_table_pages_prefers_dense_epi_pages(monkeypatch):
    """★회귀★ 앞에서부터 N장 방식은 표가 뒤쪽에 몰린 문서를 통째로 놓친다
    (실제 WHO 지역 주간보고서에서 신호 0건이 났던 원인)."""
    class FakePage:
        def __init__(self, text): self._t = text
        def get_text(self): return self._t

    class FakeDoc:
        def __init__(self, pages): self._p = pages; self.page_count = len(pages)
        def __iter__(self): return iter(self._p)
        def __enter__(self): return self
        def __exit__(self, *a): return False

    thin = FakePage("표지와 목차뿐")
    dense = FakePage(" ".join(["1,234"] * 12) + " cases deaths confirmed case fatality outbreak")
    pages = [thin, thin, dense, thin, dense]

    import types
    fake_fitz = types.SimpleNamespace(open=lambda **kw: FakeDoc(pages))
    monkeypatch.setitem(__import__("sys").modules, "fitz", fake_fitz)
    assert pt.find_table_pages(b"%PDF", limit=8) == [2, 4]


def test_find_table_pages_falls_back_when_no_candidate(monkeypatch):
    """후보가 없으면 최소한 앞쪽이라도 시도한다 — 조용히 아무것도 안 하면 안 된다."""
    monkeypatch.setattr(pt, "page_count", lambda b: 5)
    import types
    class FakeDoc:
        page_count = 5
        def __iter__(self): return iter([])
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setitem(__import__("sys").modules, "fitz",
                        types.SimpleNamespace(open=lambda **kw: FakeDoc()))
    assert pt.find_table_pages(b"%PDF", limit=3) == [0, 1, 2]


def test_extract_tables_reports_selected_pages(monkeypatch):
    _stub(monkeypatch, [{"type": "Table", "text": REAL_TABLE}], pages=16)
    monkeypatch.setattr(pt, "find_table_pages", lambda b, limit=8: [8, 9, 10])
    out = pt.extract_tables(b"%PDF", max_pages=3)
    assert out["pages_selected"] == [9, 10, 11]      # 1-based로 노출

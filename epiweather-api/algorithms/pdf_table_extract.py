"""보건 보고서 PDF에서 '표'를 구조화 추출 — 지금까지 못 읽던 신호를 연다.

배경: WHO AFRO 주간 상황보고서, 각국 보건부 역학주보 같은 문서에 국가·질병별
확진자수·사망자수·치명률이 **표**로 들어있다. 그런데 기존 텍스트 추출(pdftotext)은
두 가지로 실패한다(2026-07-31 WHO AFRO 28주차 케냐 보고서로 실측):
  1) 글자 깨짐 — 폰트 합자 인코딩 탓에 multiple→mul2ple, counties→coun2es,
     reporting→repor9ng 로 나온다.
  2) 표 붕괴 — 헤더와 값이 뒤섞여 "Mpox 1,170 1,170 19"의 19가 사망자인지 다른
     칸인지 알 수 없다. 즉 **숫자를 신호로 쓸 수 없다.**

nemotron-parse(VLM)는 페이지 이미지를 받아 블록별 좌표·의미분류(Table/Text/
Section-header)와 LaTeX tabular 형식의 표를 돌려준다. 같은 문서 실측 결과:
  "multiple", "counties" 정상 + 표 완전 복원 —
  Mpox | 1,170 | 1,170 | 19 | 1.6% | 1,376 | 39 | 31 July 2024 | Protracted 2
  Cholera | 40 | 2 | 1 | 2.5% | ... / Measles | 480 | 85 | 5 Suspected | 0.2% | ...

★ 다만 완벽하지 않다 ★ 같은 페이지에서 요약상자의 "0 Grade 3"을 "0 Grade 1"로
한 칸 오독했고, 본문에서 "reported from"을 "reported rom"으로 흘렸다. 그래서
**pdftotext 원문과 교차검증**을 함께 돌린다: 표에서 뽑은 숫자가 원문에 실제로
존재하는지 확인해 오독 후보를 표시한다. 둘 다 기계 출력이므로 어느 한쪽도
맹신하지 않는다는 게 요점이다.

★ 안전 경계선 ★ 이 모듈은 공개 보건 문서를 읽기만 한다. 추출값은 '보고된 수치'
이지 우리 추정이 아니며, 오독 가능성 때문에 is_machine_extracted=True로 표시한다.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile

import requests

from . import nvidia as _nvidia

# 기본 엔드포인트(NVIDIA 클라우드). 실제 호출 URL은 요청 시점에 nvidia.parse_url()로
# 해석 — AEGIRON_NVIDIA_ONPREM_BASE 설정 시 온프렘으로 라우팅된다. 이 층을 라우팅에서
# 빠뜨리면 문서 이미지가 클라우드로 나가는데도 '완전 주권'으로 보고된다(실제로 그랬음).
PARSE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-parse"
MAX_TOKENS = 8000        # 이 모델의 컨텍스트 상한이 9000 — 넘기면 400
RENDER_DPI = 150
TIMEOUT = 300


def render_page_png(pdf_bytes: bytes, page_index: int, dpi: int = RENDER_DPI) -> bytes | None:
    """PDF 한 페이지를 PNG로. pymupdf가 없으면 None(호출측이 건너뜀)."""
    try:
        import fitz
    except ImportError:
        return None
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if page_index >= doc.page_count:
                return None
            return doc[page_index].get_pixmap(dpi=dpi).tobytes("png")
    except Exception:
        return None


def page_count(pdf_bytes: bytes) -> int:
    try:
        import fitz
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count
    except Exception:
        return 0


_EPI_KEYWORD = re.compile(r"case fatality|cfr|deaths|cases|confirmed|outbreak", re.I)
_BIG_NUMBER = re.compile(r"\b\d[\d,]{2,}\b")


# 표 페이지 점수와 무관하게 반드시 보내는 앞쪽 페이지 수.
#
# 왜 필요한가(실측, WHO 상황보고서 11회차 전수 조사): 국가 요약표("Country |
# Confirmed Cases | ...")가 **11회차 전부 0페이지**에 있는데, 점수 순위로는
# 3회차(7/12·7/19·7/26)에서 상위 3장 밖으로 밀렸다. 점수가 '큰 숫자 개수 + 역학
# 키워드'라, 보건지역 수십 행짜리 **상세표가 압도적으로 높은 점수**를 받기 때문이다.
# 그런데 상세표는 국가 칸이 원본에서 병합돼 있어 VLM 출력에선 빈칸이라 국가 단위
# 신호를 만들 수 없다(실측 7/19: 44행 → 신호 0건). 정작 쓸 수 있는 건 압축된
# 요약표인데 점수 경쟁에서 지는 구조였다.
_ALWAYS_INCLUDE_FIRST = 1


def find_table_pages(pdf_bytes: bytes, min_numbers: int = 8,
                     min_keywords: int = 3, limit: int = 8,
                     always_first: int = _ALWAYS_INCLUDE_FIRST) -> list[int]:
    """VLM에 보낼 가치가 있는 페이지만 **로컬에서 공짜로** 골라낸다(0-based).

    왜 필요한가: 페이지마다 VLM 호출 1회라 16페이지짜리 보고서를 통째로 넣으면
    비용·시간이 그만큼 든다. 그런데 실측해보니 WHO AFRO 지역 주간보고서는 앞부분이
    지도·목차라 표가 없고 역학 표는 뒤쪽(9~14p)에 몰려 있었다 — 앞에서부터 3장만
    보는 기본값으로는 데이터를 통째로 놓친다(실제로 신호 0건이 났다).

    판별은 pymupdf 텍스트만 쓴다: 큰 숫자 밀도와 역학 키워드가 둘 다 높은 페이지가
    표 페이지다. 텍스트 추출이 깨져 있어도(합자 문제) 숫자와 영단어는 남으므로
    이 용도엔 충분하다. 후보가 없으면 앞에서부터 채워 최소한 시도는 하게 한다.

    always_first장은 점수와 무관하게 항상 포함한다 — 순수 점수순은 요약표를
    상세표에 밀어내는 것이 실측으로 확인됐다(_ALWAYS_INCLUDE_FIRST 주석 참고)."""
    try:
        import fitz
    except ImportError:
        return list(range(min(limit, page_count(pdf_bytes))))
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            scored = []
            for idx, page in enumerate(doc):
                text = page.get_text()
                numbers = len(_BIG_NUMBER.findall(text))
                keywords = len(_EPI_KEYWORD.findall(text))
                if numbers >= min_numbers and keywords >= min_keywords:
                    scored.append((numbers + keywords, idx))
            total = doc.page_count
    except Exception:
        return list(range(min(limit, page_count(pdf_bytes))))

    if not scored:
        return list(range(min(limit, total)))

    # 앞쪽 고정분을 먼저 확보하고, 남은 자리를 점수순으로 채운다.
    # ★ 단, **이미 표 후보로 통과한 페이지만** 고정한다 — 표지·목차처럼 내용이 없는
    # 앞장을 무조건 보내면 문서마다 VLM 호출 1회가 헛나간다. 요약표가 점수 경쟁에서
    # 지는 것만 막으면 되지, 자격 없는 페이지를 밀어 넣을 이유는 없다.
    qualified = {idx for _s, idx in scored}
    pinned = [i for i in range(min(always_first, total, limit)) if i in qualified]
    scored.sort(reverse=True)
    chosen = list(pinned)
    for _score, idx in scored:
        if len(chosen) >= limit:
            break
        if idx not in chosen:
            chosen.append(idx)
    return sorted(chosen)


def _parse_page(png: bytes, api_key: str) -> list[dict]:
    """nemotron-parse 호출 → 블록 목록. 응답은 content가 아니라 tool_calls의
    markdown_bbox 함수 인자로 온다(실측 확인)."""
    import json

    b64 = base64.b64encode(png).decode()
    r = requests.post(
        _nvidia.parse_url(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}],
            "max_tokens": MAX_TOKENS,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    calls = (r.json()["choices"][0]["message"] or {}).get("tool_calls") or []
    if not calls:
        return []
    blocks = json.loads(calls[0]["function"]["arguments"])
    while blocks and isinstance(blocks, list) and blocks and isinstance(blocks[0], list):
        blocks = blocks[0]          # 중첩 배열로 오는 경우가 있음
    return [b for b in blocks if isinstance(b, dict)]


_BOLD = re.compile(r"\*\*(.*?)\*\*")
_SUP = re.compile(r"<sup>.*?</sup>")
# 레이아웃 명령(\multicolumn{9}{c}, \hline 등)은 데이터가 아니라 표 서식이다 —
# 그대로 두면 "\multicolumn{9}{c}"가 한 행처럼 섞여 들어온다(실측에서 확인).
_LAYOUT_CMD = re.compile(r"\\(multicolumn|multirow|hline|cline|toprule|midrule|bottomrule)"
                         r"(\{[^{}]*\})*")
_LATEX_ESCAPE = re.compile(r"\\([%&_#$])")


def _clean_cell(cell: str) -> str:
    cell = _BOLD.sub(r"\1", cell)
    cell = _SUP.sub("", cell)
    cell = _LAYOUT_CMD.sub("", cell)
    cell = _LATEX_ESCAPE.sub(r"\1", cell)      # 81.5\% → 81.5%
    return cell.replace("\\\\", "").strip()


def parse_latex_table(text: str) -> list[list[str]]:
    """nemotron-parse가 주는 \\begin{tabular}...\\end{tabular}를 행렬로.
    레이아웃 명령만 남는 행은 데이터가 아니므로 버린다."""
    body = text
    start = body.find("\\begin{tabular}")
    if start != -1:
        brace = body.find("}", body.find("{", start + len("\\begin{tabular}")))
        body = body[brace + 1:] if brace != -1 else body[start:]
    end = body.find("\\end{tabular}")
    if end != -1:
        body = body[:end]
    rows = []
    for raw in body.split("\\\\"):
        raw = raw.strip()
        if not raw:
            continue
        cells = [_clean_cell(c) for c in raw.split("&")]
        if any(cells):
            rows.append(cells)
    return rows


def pdftotext_raw(pdf_bytes: bytes) -> str:
    """교차검증용 원문. pdftotext가 없으면 빈 문자열(교차검증만 생략됨)."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            path = f.name
        out = subprocess.run(["pdftotext", path, "-"], capture_output=True, timeout=120)
        return out.stdout.decode("utf-8", errors="replace") if out.returncode == 0 else ""
    except Exception:
        return ""
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


_NUM = re.compile(r"\d[\d,]*")


def cross_check_numbers(rows: list[list[str]], raw_text: str) -> dict:
    """표에서 뽑은 숫자가 pdftotext 원문에도 있는지 확인. 원문에 없는 숫자는
    VLM 오독 후보다(실측에서 'Grade 3'→'Grade 1' 같은 오독이 있었음).
    원문이 비어 있으면 검증 자체를 생략하고 checked=False로 정직하게 표시."""
    if not raw_text:
        return {"checked": False, "reason": "pdftotext 원문 없음 — 교차검증 생략"}
    normalized = raw_text.replace(",", "")
    found, missing = 0, []
    for row in rows:
        for cell in row:
            for m in _NUM.findall(cell):
                plain = m.replace(",", "")
                if len(plain) < 2:          # 한 자리 수는 우연히 일치하므로 제외
                    continue
                if plain in normalized:
                    found += 1
                else:
                    missing.append(m)
    total = found + len(missing)
    return {
        "checked": True,
        "numbers_verified": found,
        "numbers_unverified": len(missing),
        "unverified_samples": missing[:8],
        "verified_rate": round(found / total, 3) if total else None,
        "note": "원문에 없는 숫자는 VLM 오독 후보 — 사람이 확인해야 함.",
    }


def extract_tables(pdf_bytes: bytes, api_key: str | None = None,
                   max_pages: int = 3, pages: list[int] | None = None,
                   auto_select: bool = True) -> dict:
    """PDF에서 표를 구조화 추출하고 원문과 교차검증. 실패해도 예외를 던지지 않는다.

    auto_select=True면 find_table_pages로 표가 있을 법한 페이지만 고른다 —
    앞에서부터 N장 방식은 표가 뒤쪽에 몰린 문서에서 데이터를 통째로 놓친다.
    max_pages: 페이지마다 API 1회(수 초~수십 초)라 기본값을 작게 둔다."""
    key = api_key or os.environ.get("NVIDIA_API_KEY")
    if not key:
        return {"ok": False, "reason": "NVIDIA_API_KEY 없음 — 표 추출 생략"}
    total_pages = page_count(pdf_bytes)
    if total_pages == 0:
        return {"ok": False, "reason": "PDF를 열 수 없음(pymupdf 미설치 또는 손상)"}

    if pages is not None:
        targets = pages
    elif auto_select:
        targets = find_table_pages(pdf_bytes, limit=max_pages)
    else:
        targets = list(range(min(max_pages, total_pages)))
    raw_text = pdftotext_raw(pdf_bytes)

    results, errors = [], 0
    for idx in targets:
        png = render_page_png(pdf_bytes, idx)
        if png is None:
            errors += 1
            continue
        try:
            blocks = _parse_page(png, key)
        except Exception as e:
            errors += 1
            results.append({"page": idx + 1, "ok": False, "error": type(e).__name__})
            continue
        # 블록은 문서 읽기 순서대로 온다 — 표 바로 앞의 섹션 제목을 문맥으로 붙인다.
        # 실측 근거: WHO 보고서의 국가별 표는 질병 열이 없고 병명이 위쪽 제목에만
        # 있다("## Bundibugyo Virus Disease (BVD) outbreak in the DRC and Uganda").
        # 이걸 안 물려주면 숫자는 잡는데 무슨 병인지 몰라 질병별 경보가 안 뜬다.
        # 바로 앞 제목만 보면 놓친다: 병명 제목과 표 사이에 다른 소제목이 끼어드는
        # 경우가 있다(실측: "## Bundibugyo Virus Disease..." 다음에 "### Kenya
        # Preparedness..."가 오고 그 뒤에 표). 그래서 같은 페이지에서 지금까지 나온
        # 제목을 순서대로 함께 넘겨, 소비측이 뒤로 거슬러 찾을 수 있게 한다.
        tables, texts = [], []
        headers_so_far: list[str] = []
        for b in blocks:
            btype, btext = b.get("type"), (b.get("text") or "").strip()
            if btype in ("Section-header", "Title") and btext:
                headers_so_far.append(_clean_cell(btext))
            if btype == "Table":
                rows = parse_latex_table(btext)
                if rows:
                    tables.append({"rows": rows, "row_count": len(rows),
                                   "column_count": max(len(r) for r in rows),
                                   "context_header": headers_so_far[-1] if headers_so_far else None,
                                   "context_headers": list(headers_so_far),
                                   "cross_check": cross_check_numbers(rows, raw_text)})
            elif btext:
                texts.append({"type": btype, "text": btext})
        results.append({"page": idx + 1, "ok": True, "tables": tables,
                        "table_count": len(tables), "text_blocks": texts})

    parsed = [p for p in results if p.get("ok")]
    return {
        "ok": bool(parsed),
        "model": MODEL,
        "pdf_pages": total_pages,
        "pages_selected": [i + 1 for i in targets],   # 1-based, 사람이 보는 페이지 번호
        "pages_attempted": len(targets),
        "pages_parsed": len(parsed),
        "pages_failed": errors,
        "total_tables": sum(p.get("table_count", 0) for p in parsed),
        "pages": results,
        "is_machine_extracted": True,
        "method": (
            "nemotron-parse(VLM)로 페이지 이미지를 블록 단위(표/본문/제목)로 구조화한 뒤, "
            "표에서 뽑은 숫자를 pdftotext 원문과 교차검증한다."
        ),
        "disclaimer": (
            "기계 추출값이라 오독이 있을 수 있다(실측에서 요약상자 한 칸 오독·본문 철자 "
            "누락 확인됨). cross_check의 unverified 항목은 원문에 없는 숫자이므로 사람이 "
            "확인해야 한다. 추출값은 '문서에 보고된 수치'이지 이 시스템의 추정치가 아니다."
        ),
    }

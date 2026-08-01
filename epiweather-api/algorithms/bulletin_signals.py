"""보건 보고서 표 → 정규화 신호. pdf_table_extract의 출력을 실제 경보 재료로 바꾼다.

배경: pdf_table_extract가 WHO 주간보고서의 표를 복원하는 데까지는 성공했다
(케냐 Mpox 1,170례·19사망, DRC 1,963확진·719사망 등 실측). 그런데 표는 사람이
읽는 물건이지 신호가 아니다 — 이 모듈이 행을 질병·국가·수치로 매핑해서
db.create_extracted_signal이 받을 수 있는 모양으로 만든다.

실측한 두 가지 표 모양(WHO AFRO 주간 상황보고서, 2026-07-31 확인):
  ① 질병 축: Event | Total Cases | Confirmed cases | Deaths | Case Fatality Rate | ...
             예) Mpox | 1,170 | 1,170 | 19 | 1.6% | 1,376 | 39 | 31 July 2024 | Protracted 2
  ② 국가 축: Country* | Cumulative Confirmed | Recovered | Confirmed Deaths | ... | Active zones
             예) DRC | 1,963 | 331 | 719 | 81.5% | 33
②는 질병 열이 아예 없다(특정 발병 섹션 안의 표라 문맥에 질병이 있음). 그런 경우
**질병을 추측해서 채우지 않고 None으로 둔다** — 지어낸 라벨이 신호에 섞이면
경보 전체의 신뢰가 무너지기 때문이다.

★ 정직성 규칙 ★
- 헤더를 못 알아본 열은 버린다(위치로 추측하지 않는다).
- 질병·국가를 둘 다 못 잡거나 숫자가 하나도 없는 행은 신호로 만들지 않는다.
- 값은 '문서가 보고한 수치'다. is_machine_extracted와 교차검증 결과를 함께 달아
  사람이 검증해야 함을 명시한다.
"""
from __future__ import annotations

import re

# 헤더 키워드 → 정규화 필드. 소문자 부분일치로 본다(표기가 문서마다 흔들림).
_HEADER_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("deaths", ("death",)),
    ("cfr", ("fatality", "cfr")),
    ("confirmed", ("confirmed",)),
    ("recovered", ("recovered",)),
    ("contacts", ("contact",)),
    ("total_cases", ("total case", "cumulative", "cases", "case")),
]
_DISEASE_HEADER = ("event", "disease", "condition", "outbreak")
_COUNTRY_HEADER = ("country", "countries", "province", "region", "county")

_NUM = re.compile(r"-?\d[\d,\s]*\.?\d*")
_PCT = re.compile(r"(\d+\.?\d*)\s*%")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _flatten(text: str) -> str:
    """셀 안 줄바꿈·연속 공백을 한 칸으로. 표 셀은 폭에 맞춰 줄바꿈돼 오기 때문에
    그대로 두면 라벨이 쪼개진다."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def _to_number(cell: str) -> float | None:
    """'1,170' → 1170.0, '918 000' → 918000.0, '5 Suspected' → 5.0, 'N/A' → None.

    WHO 문서는 천 단위 구분에 공백을 쓴다('21 800 000') — 쉼표만 처리하면 21로
    읽혀 신호가 6자리 틀린다."""
    match = _NUM.search(cell or "")
    if not match:
        return None
    cleaned = re.sub(r"[,\s]", "", match.group(0))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_ratio(cell: str) -> float | None:
    """'1.6%' → 0.016. 퍼센트 기호가 없으면 비율로 못 읽으므로 None."""
    match = _PCT.search(cell or "")
    if not match:
        return None
    try:
        return round(float(match.group(1)) / 100, 5)
    except ValueError:
        return None


def map_header(header: list[str]) -> dict:
    """헤더 행 → {필드: 열 인덱스}. 못 알아본 열은 넣지 않는다(위치 추측 금지)."""
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(header):
        cell = _norm(raw)
        if not cell:
            continue
        if "label" not in mapping and any(k in cell for k in _DISEASE_HEADER):
            mapping["label"], mapping["label_kind"] = idx, "disease"   # type: ignore[assignment]
            continue
        if "label" not in mapping and any(k in cell for k in _COUNTRY_HEADER):
            mapping["label"], mapping["label_kind"] = idx, "country"   # type: ignore[assignment]
            continue
        for field, keywords in _HEADER_MAP:
            if field in mapping:
                continue
            if any(k in cell for k in keywords):
                mapping[field] = idx
                break
    return mapping


def looks_like_epi_table(rows: list[list[str]]) -> bool:
    """역학 표인지 — 라벨 열과 숫자 필드가 최소 하나씩 잡혀야 한다."""
    if len(rows) < 2:
        return False
    mapping = map_header(rows[0])
    numeric = [f for f, _ in _HEADER_MAP if f in mapping]
    return "label" in mapping and bool(numeric)


# ── WHO AFRO '감시 중인 전체 이벤트' 표 (헤더 없는 고정 레이아웃) ──────
# 실측 구조(2026-08-01, OEW12 10~13페이지):
#   국가 | 이벤트 | 등급 | 발생일 | 시작일 | 갱신일 | 총계 | 확진 | 사망 | 치명률
#   예) Guinea | Lassa fever | Ungraded | 10-Mar-26 | 10-Mar-26 | 22-Mar-26 | 1 | 1 | 1 | 100.00%
# VLM이 큰 표를 조각으로 쪼개 내보내기 때문에 **헤더 행이 없는 단편**으로 온다.
# 그래서 헤더 대신 '등급 열' 서명으로 이 레이아웃을 식별한다.
_GRADE = re.compile(r"^(grade\s*\d|protracted\s*\d|ungraded)$", re.I)
_AFRO_MIN_COLS = 9
_AFRO_NUM_START = 6          # 국가·이벤트·등급 + 날짜 3개 다음부터 숫자


def parse_afro_event_row(row: list[str]) -> dict | None:
    """WHO AFRO 이벤트 행 → {country, disease, grade, metrics}. 아니면 None.

    숫자 열은 빈칸·'-'가 섞여 위치가 밀리므로 위치로 전부 매핑하지 않는다.
    확실한 것만 취한다: 총계(날짜 뒤 첫 숫자), 치명률('%' 있는 칸), 사망(치명률
    바로 앞 숫자). 치명률 칸이 없으면 사망 위치가 모호해지므로 사망은 비운다
    — 사이클론 같은 비질병 이벤트가 섞여 있어 잘못 넣으면 가짜 사망자가 된다."""
    if len(row) < _AFRO_MIN_COLS or not _GRADE.match((row[2] or "").strip()):
        return None
    # 셀 안에서 줄바꿈된 라벨을 그대로 두면 질병명이 "Impact of Sudan\ncris"처럼
    # 나와 하류 질병 매칭이 깨진다 — 공백류를 한 칸으로 정규화한다.
    country, disease = _flatten(row[0]), _flatten(row[1])
    if not country or not disease or _to_number(country) is not None:
        return None

    tail = row[_AFRO_NUM_START:]
    metrics: dict[str, float] = {}

    for cell in tail:                                   # 총계 = 날짜 뒤 첫 숫자
        value = _to_number(cell)
        if value is not None:
            metrics["total_cases"] = value
            break

    pct_idx = next((i for i, c in enumerate(tail) if "%" in (c or "")), None)
    if pct_idx is not None:
        ratio = _to_ratio(tail[pct_idx])
        if ratio is not None:
            metrics["cfr"] = ratio
        for cell in reversed(tail[:pct_idx]):           # 사망 = 치명률 직전 숫자
            value = _to_number(cell)
            if value is not None:
                metrics["deaths"] = value
                break

    if not metrics:
        return None
    return {"country": country, "disease": disease,
            "grade": (row[2] or "").strip(), "metrics": metrics}


def afro_rows_to_signals(rows: list[list[str]], source: str, signal_date: str | None,
                         cross_check: dict | None) -> list[dict]:
    """헤더 없는 AFRO 이벤트 단편 → 신호. 한 행도 서명에 안 맞으면 빈 목록."""
    signals = []
    for row in rows:
        parsed = parse_afro_event_row(row)
        if not parsed:
            continue
        signals.append({
            "source": source,
            "disease": parsed["disease"],
            "location": parsed["country"],
            "grade": parsed["grade"],
            "metrics": parsed["metrics"],
            "signal_date": signal_date,
            "raw_text": " | ".join(c for c in row if c).strip(),
            "is_machine_extracted": True,
            "cross_check": cross_check,
            "layout": "who_afro_events",
        })
    return signals


# 섹션 제목에서 질병명을 찾을 때 쓰는 사전. 임의 문자열을 병명으로 삼으면
# "Summary of ongoing emergencies" 같은 제목이 병명이 되어 신호가 오염되므로,
# 알려진 병명이 제목에 실제로 있을 때만 쓴다.
_KNOWN_DISEASES = [
    "bundibugyo", "ebola", "marburg", "cholera", "measles", "mpox", "monkeypox",
    "polio", "poliomyelitis", "diphtheria", "lassa", "dengue", "chikungunya",
    "yellow fever", "meningitis", "hepatitis", "malaria", "plague", "anthrax",
    "influenza", "covid", "rift valley fever", "typhoid", "rabies", "tuberculosis",
]


def disease_from_header(header: str | None) -> str | None:
    """섹션 제목에서 알려진 병명을 찾아 돌려준다. 없으면 None.

    WHO 보고서의 국가별 표는 질병 열이 없고 병명이 위쪽 제목에만 있다
    (예: "## Bundibugyo Virus Disease (BVD) outbreak in the DRC and Uganda").
    제목을 통째로 병명으로 쓰면 오염되므로 사전에 있는 병명만 취한다."""
    if not header:
        return None
    low = header.lower()
    matches = [d for d in _KNOWN_DISEASES if d in low]
    if not matches:
        return None
    # 'bundibugyo ebola'처럼 여러 개 걸리면 더 구체적인(긴) 쪽을 쓴다.
    return max(matches, key=len).title()


def rows_to_signals(rows: list[list[str]], source: str = "who_bulletin",
                    signal_date: str | None = None,
                    cross_check: dict | None = None,
                    context_header: str | None = None,
                    context_headers: list[str] | None = None) -> list[dict]:
    """표 한 개 → 신호 목록. 역학 표가 아니면 빈 목록.

    헤더 있는 표(케냐 국가보고서 형식)를 먼저 보고, 아니면 헤더 없는 AFRO 이벤트
    레이아웃을 시도한다 — 지역 주간보고서의 감시 이벤트 표가 그 형태다."""
    if not looks_like_epi_table(rows):
        return afro_rows_to_signals(rows, source, signal_date, cross_check)
    mapping = map_header(rows[0])
    label_idx = mapping["label"]
    label_kind = mapping.get("label_kind", "disease")

    signals: list[dict] = []
    for row in rows[1:]:
        if label_idx >= len(row):
            continue
        label = (row[label_idx] or "").strip()
        if not label or _to_number(label) is not None:
            continue                    # 빈 칸이거나 숫자면 라벨이 아니다

        metrics: dict[str, float] = {}
        for field, _ in _HEADER_MAP:
            idx = mapping.get(field)
            if idx is None or idx >= len(row):
                continue
            value = _to_ratio(row[idx]) if field == "cfr" else _to_number(row[idx])
            if value is not None:
                metrics[field] = value
        if not metrics:
            continue                    # 숫자가 하나도 없으면 신호가 아니다

        disease = label if label_kind == "disease" else None
        disease_source = "table_column" if disease else None
        if disease is None:
            # 국가 축 표는 병명이 표에 없다 — 섹션 제목에서 가져오되 출처를 남긴다.
            # 바로 앞 제목에 병명이 없으면 같은 페이지의 앞선 제목들을 뒤로 거슬러
            # 찾는다(병명 제목과 표 사이에 다른 소제목이 끼어드는 경우가 있음).
            from_header = disease_from_header(context_header)
            for candidate in reversed(context_headers or []):
                if from_header:
                    break
                from_header = disease_from_header(candidate)
            if from_header:
                disease, disease_source = from_header, "section_header"

        signals.append({
            "source": source,
            "disease": disease,
            "disease_source": disease_source,
            "location": label if label_kind == "country" else None,
            "metrics": metrics,
            "signal_date": signal_date,
            "context_header": context_header,
            "raw_text": " | ".join(c for c in row if c).strip(),
            # 기계 추출값임을 신호 자체가 들고 다니게 한다.
            "is_machine_extracted": True,
            "cross_check": cross_check,
        })
    return signals


def extract_signals(parsed: dict, source: str = "who_bulletin",
                    signal_date: str | None = None) -> dict:
    """pdf_table_extract.extract_tables()의 출력 전체 → 신호 목록.

    표마다 교차검증 결과를 그대로 물려서, 나중에 어떤 신호가 검증 안 된 숫자에서
    나왔는지 추적할 수 있게 한다."""
    if not parsed.get("ok"):
        return {"ok": False, "reason": parsed.get("reason", "표 추출 실패"), "signals": []}

    signals: list[dict] = []
    epi_tables = 0
    for page in parsed.get("pages", []):
        if not page.get("ok"):
            continue
        for table in page.get("tables", []):
            rows = table.get("rows") or []
            got = rows_to_signals(rows, source=source, signal_date=signal_date,
                                  cross_check=table.get("cross_check"),
                                  context_header=table.get("context_header"),
                                  context_headers=table.get("context_headers"))
            if got:
                epi_tables += 1
                for signal in got:
                    signal["page"] = page.get("page")
                signals.extend(got)

    unverified = sum(1 for s in signals
                     if (s.get("cross_check") or {}).get("numbers_unverified"))
    return {
        "ok": True,
        "signals": signals,
        "signal_count": len(signals),
        "epi_tables": epi_tables,
        "tables_seen": sum(p.get("table_count", 0) for p in parsed.get("pages", []) if p.get("ok")),
        "signals_from_unverified_tables": unverified,
        "is_machine_extracted": True,
        "note": (
            "값은 '문서가 보고한 수치'다. 헤더를 못 알아본 열은 버렸고, 질병·국가를 "
            "추측으로 채우지 않았다(국가 축 표는 disease=None). 교차검증에서 원문에 "
            "없던 숫자가 있으면 그 표에서 나온 신호는 사람이 확인해야 한다."
        ),
    }

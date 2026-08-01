"""WHO IRIS(공식 문서 리포지터리) 수집 — 발병 주간보고서 PDF를 안정적으로 가져온다.

배경: pdf_table_extract.py로 WHO AFRO 주간보고서의 표를 읽어내는 데는 성공했지만
(케냐 Mpox 1,170례·DRC 719사망 등 실제 추출 확인), **문서를 가져오는 경로**가
불안정해서 실전에 못 걸고 있었다. afro.who.int는 URL 패턴이 일반화되지 않고
(2026년 28주차만 존재하고 25~27주차는 404) 발행물 페이지가 엉뚱한 PDF를 링크한다.

iris.who.int는 WHO 공식 문서 리포지터리이고 **DSpace 7.6**이라 정식 REST API가
있다(2026-08-01 확인). 스크래핑이 아니라 API로 가져오므로 사이트 개편에 훨씬 덜
취약하다. 검색 → 항목 → 번들 → 비트스트림(PDF) 경로가 전부 문서화된 엔드포인트다.

유용한 부수 효과: 각 항목에 ORIGINAL(PDF) 말고 **TEXT 번들(.txt)**이 함께 있다 —
WHO가 자체 추출한 텍스트라, pdf_table_extract의 숫자 교차검증 원문으로 바로 쓸 수
있다(로컬에 pdftotext가 없어도 됨). 다만 그 텍스트도 표는 뭉개져 있어서(실측 확인)
구조 복원은 여전히 pdf_table_extract가 필요하다 — 교차검증용 원문으로만 쓴다.

★★ 신선도 한계(반드시 알고 쓸 것) ★★
IRIS 리포지터리 자체는 최신이다(2026-08-01 확인 시 전날 발행물까지 색인됨).
그런데 **발병 주간보고서 시리즈만 최신분이 빠져 있다**: IRIS에서 찾히는 최신은
2026년 12주차(3월)인데, afro.who.int에는 같은 시점에 28주차(7월)가 올라와 있었다.
메타데이터도 흔들린다(제목 "Week 21"인데 dc.date.issued가 2026-03-24).

따라서 역할을 나눈다:
  - IRIS          : **과거 아카이브 축적용**. 2025년치까지 주차별로 촘촘히 있어
                    기준선(baseline) 확대에 적합하다. API라 수집이 안정적이다.
  - afro.who.int  : 최신분 확보용. 단 URL 패턴이 일반화되지 않아 수집이 불안정하다.
실시간 조기경보를 IRIS만으로 돌리면 몇 달 늦는다 — 이 점을 착각하면 안 된다.

주간보고서 파일명 규칙(실측): OEW{주차}-{시작일}{종료일}{연도}.pdf
  예) OEW12-1622032026.pdf = 12주차, 2026년 3월 16~22일

★ 안전 경계선 ★ 공개된 WHO 문서를 읽기만 한다. 수집한 수치는 '기관이 보고한 값'
이지 이 시스템의 추정이 아니다.
"""
from __future__ import annotations

import re

import requests

API = "https://iris.who.int/server/api"
TIMEOUT = 60
UA = {"User-Agent": "EpiWeather/1.0 (public health monitoring)"}

# 발병 주간보고서(Outbreak and other Emergencies Weekly) 제목·파일명 패턴.
BULLETIN_TITLE = re.compile(r"weekly bulletin on outbreak", re.I)
BULLETIN_FILE = re.compile(r"^OEW\d+", re.I)


def _get(path: str, **params) -> dict:
    r = requests.get(f"{API}{path}", params=params or None, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _meta(item: dict, key: str) -> str | None:
    values = (item.get("metadata") or {}).get(key)
    return values[0].get("value") if values else None


def search_items(query: str, size: int = 10, sort: str = "dc.date.issued,DESC") -> list[dict]:
    """IRIS 전문 검색. 실패하면 빈 목록(호출측이 조용히 넘어갈 수 있게)."""
    try:
        data = _get("/discover/search/objects", query=query, dsoType="item",
                    size=size, sort=sort)
    except Exception:
        return []
    objects = (data.get("_embedded", {}).get("searchResult", {})
               .get("_embedded", {}).get("objects", []))
    items = []
    for obj in objects:
        item = obj.get("_embedded", {}).get("indexableObject") or {}
        if not item.get("uuid"):
            continue
        items.append({
            "uuid": item["uuid"],
            "title": item.get("name") or "",
            "issued": _meta(item, "dc.date.issued"),
            "language": _meta(item, "dc.language.iso"),
        })
    return items


def item_files(uuid: str) -> dict:
    """항목의 번들을 훑어 PDF(ORIGINAL)와 추출텍스트(TEXT) 링크를 찾는다."""
    out: dict = {"pdf": None, "text": None, "all": []}
    try:
        bundles = _get(f"/core/items/{uuid}/bundles").get("_embedded", {}).get("bundles", [])
    except Exception:
        return out
    for bundle in bundles:
        name = bundle.get("name")
        if name not in ("ORIGINAL", "TEXT"):
            continue                       # THUMBNAIL·LICENSE는 필요 없음
        try:
            streams = (_get(f"/core/bundles/{bundle['uuid']}/bitstreams")
                       .get("_embedded", {}).get("bitstreams", []))
        except Exception:
            continue
        for bitstream in streams:
            entry = {
                "bundle": name,
                "name": bitstream.get("name") or "",
                "size_bytes": bitstream.get("sizeBytes"),
                "url": (bitstream.get("_links", {}).get("content", {}) or {}).get("href"),
            }
            if not entry["url"]:
                continue
            out["all"].append(entry)
            if name == "ORIGINAL" and entry["name"].lower().endswith(".pdf") and not out["pdf"]:
                out["pdf"] = entry
            elif name == "TEXT" and entry["name"].lower().endswith(".txt") and not out["text"]:
                out["text"] = entry
    return out


def latest_outbreak_bulletins(limit: int = 5, search_size: int = 25) -> list[dict]:
    """최신 '발병 주간보고서'를 PDF 링크까지 붙여 반환.

    검색어만으로는 인플루엔자 주보 등 다른 정기간행물도 섞여 나오므로, 제목과
    파일명(OEW*)으로 한 번 더 거른다 — 엉뚱한 문서를 신호로 넣지 않기 위함."""
    candidates = search_items('"Weekly Bulletin on Outbreak and other Emergencies"',
                              size=search_size)
    results = []
    for item in candidates:
        if not BULLETIN_TITLE.search(item["title"]):
            continue
        files = item_files(item["uuid"])
        pdf = files.get("pdf")
        if not pdf or not BULLETIN_FILE.match(pdf["name"]):
            continue                       # OEW 규칙에 안 맞으면 다른 간행물로 본다
        results.append({**item, "pdf": pdf, "text": files.get("text")})
        if len(results) >= limit:
            break
    return results


_WEEK_IN_TITLE = re.compile(r"Week\s*(\d+)", re.I)


def bulletin_archive(size: int = 60) -> list[dict]:
    """기준선 축적용 — 주간보고서 아카이브를 주차 정보와 함께 모아 온다.

    dc.date.issued가 흔들리는 항목이 있어(제목 Week 21인데 3월 발행으로 기록됨)
    제목에서 주차 번호를 따로 뽑아 함께 돌려준다. 정렬·중복제거는 호출측이 판단할
    수 있게 원자료를 유지한다 — 여기서 임의로 버리지 않는다."""
    items = search_items('title:"Weekly Bulletin on Outbreak"', size=size)
    out = []
    for item in items:
        if not BULLETIN_TITLE.search(item["title"]):
            continue
        match = _WEEK_IN_TITLE.search(item["title"])
        out.append({**item, "week": int(match.group(1)) if match else None})
    return out


def fetch_bytes(url: str, max_bytes: int = 40 * 1024 * 1024) -> bytes | None:
    """비트스트림 내려받기. 너무 크면 받지 않는다(메모리 보호)."""
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT * 3, stream=True)
        r.raise_for_status()
        chunks, total = [], 0
        for chunk in r.iter_content(65536):
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        return b"".join(chunks)
    except Exception:
        return None

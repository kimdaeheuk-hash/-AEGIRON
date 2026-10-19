"""한국 국제선 국가별 실제 운송 실적 — 공공데이터포털 '파일 데이터'를 자동으로 받는다 (2026-10-19, ⑦).

## 왜

유입 보고서·확산 모델의 한국 연결은 OpenFlights **2014년 노선 개수**다. 승객 수도 편수도
아니고 12년 묵었다. 공공데이터포털에 **활용신청·로그인 없이 받는 파일 데이터**가 있다:

    15062056 인천국제공항공사_항공사별 노선별 운송실적 — 월별·항공사별·노선별·국가별
             운항편수·여객 수(유임+무임+환승)·화물. 반기 갱신(1월: 전년 1~12월, 7월: 당해 1~6월).

한국공항공사 수송실적(15002638)도 받아 봤으나(캡틴, 2026-10-19) **국가 열이 없고**(공항 × 요일 ×
국내/국제 합계) 집계 기간 단위도 파일만으로 확인되지 않아 쓰지 않는다. 그래서 이 스냅샷은 **인천만**
덮는다 — 김해·김포·제주 국제선(일본·중국·동남아 단거리 위주)은 빠진다. 화면·보고서에 그렇게 적는다.

## 받는 방법 — 확인하지 못한 부분을 숨기지 않는다

개발 환경에서는 data.go.kr 에 접속하지 못해 **다운로드 경로와 CSV 열 이름을 직접 보지 못했다.**
그래서 이 모듈은 단계마다 실패 사유를 남기고(어느 단계·HTTP 상태·찾은 열 이름), 운영 첫 실행
로그(`기준 스냅샷 kor_route_stats …`)가 실제 모양을 알려 준다. 시도 순서:

  ① 데이터셋 페이지(fileData.do)를 받아 첨부파일 ID(FILE_…)와 상세 키(uddi:…)를 찾는다
  ② 첨부파일 ID 가 있으면 공통 다운로드 경로로 받는다
  ③ 없으면 상세 키로 다운로드 정보(JSON)를 물어 첨부파일 ID 를 얻은 뒤 ②
  받은 것이 HTML(안내·차단 페이지)이면 CSV 로 읽지 않고 실패로 센다.

## 열·국가

캡틴이 받아 준 실제 파일(2026-10-19)로 머리글을 확인하고 그 이름 그대로 읽는다(아래 주석). 열이
바뀌면 고르려 들지 않고 '없는 열'과 머리글을 사유로 남긴다 — 다른 열의 값을 지어 쓰지 않는다.
국가 이름은 country_resolve 로 ISO3 에 붙이고, 그 표에 없는 15개는 이 자료 전용 표(NAME_TO_ISO3)로
붙인다. 그래도 못 붙인 이름은 목록으로 남긴다(버리고 조용히 넘어가지 않는다).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re

import requests

DATASETS = (
    {"key": "incheon", "pk": 15062056, "label": "인천국제공항공사_항공사별 노선별 운송실적"},
)
PAGE_URL = "https://www.data.go.kr/data/{pk}/fileData.do"
DOWNLOAD_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do"
DOWNLOAD_INFO_URL = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
HEADERS = {"User-Agent": "Mozilla/5.0 (AEGIRON research; public file data)"}
TIMEOUT = 60


class FetchError(RuntimeError):
    """단계와 사유를 담는 실패 — 운영 로그에 그대로 찍힌다."""


# ── 내려받기 ─────────────────────────────────────────────────────────

def _looks_html(raw: bytes) -> bool:
    head = raw[:300].lstrip().lower()
    return head.startswith(b"<!doctype") or head.startswith(b"<html") or b"<head" in head


def find_ids(page_html: str) -> tuple[list[str], list[str]]:
    """페이지에서 첨부파일 ID 와 상세 키 후보(중복 없이, 나온 순서)."""
    atch = list(dict.fromkeys(re.findall(r"FILE_\d{10,}", page_html)))
    uddi = list(dict.fromkeys(re.findall(r"uddi:[0-9A-Za-z-]{20,}", page_html)))
    return atch, uddi


def _download(session, atch_id: str, sn: str | int = 1) -> bytes:
    r = session.get(DOWNLOAD_URL, params={"atchFileId": atch_id, "fileDetailSn": sn},
                    headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        raise FetchError(f"파일 받기 HTTP {r.status_code}")
    if _looks_html(r.content):
        raise FetchError("파일 받기 응답이 HTML(안내·차단 페이지) — CSV 아님")
    return r.content


def download_csv(pk: int, session=None) -> tuple[bytes, dict]:
    """데이터셋 pk 의 CSV 원문과 경로 정보. 실패는 FetchError(단계·사유)."""
    s = session or requests.Session()
    r = s.get(PAGE_URL.format(pk=pk), headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        raise FetchError(f"① 페이지 HTTP {r.status_code}")
    atch, uddi = find_ids(r.text)
    title = re.search(r"<title>(.*?)</title>", r.text, re.S)
    info = {"page_title": title.group(1).strip()[:120] if title else None,
            "atch_candidates": len(atch), "uddi_candidates": len(uddi)}
    errors = []
    for a in atch[:3]:
        try:
            raw = _download(s, a)
            return raw, {**info, "route": "atchFileId", "atch_file_id": a}
        except (FetchError, requests.RequestException) as e:
            errors.append(f"② {a[:14]}…: {e}")
    for u in uddi[:3]:
        try:
            j = s.get(DOWNLOAD_INFO_URL, params={"publicDataPk": pk, "publicDataDetailPk": u,
                                                 "fileDetailSn": 1},
                      headers=HEADERS, timeout=TIMEOUT)
            if j.status_code != 200:
                errors.append(f"③ 다운로드 정보 HTTP {j.status_code}")
                continue
            data = j.json()
            found = data.get("atchFileId") or (data.get("fileDataRegistVO") or {}).get("atchFileId")
            sn = data.get("fileDetailSn") or 1
            if not found:
                errors.append(f"③ 다운로드 정보에 atchFileId 없음(키: {sorted(data)[:8]})")
                continue
            raw = _download(s, found, sn)
            return raw, {**info, "route": "uddi→atchFileId", "atch_file_id": found}
        except (FetchError, requests.RequestException, ValueError) as e:
            errors.append(f"③ {type(e).__name__}: {e}")
    if not atch and not uddi:
        raise FetchError(f"① 페이지에서 첨부파일 ID·상세 키를 못 찾음(제목: {info['page_title']})")
    raise FetchError(" / ".join(errors)[:600])


def decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise FetchError("CSV 인코딩을 읽지 못함(utf-8·cp949·euc-kr)")


# ── 열·국가 (2026-10-19 캡틴이 받아 준 실제 파일로 확인) ─────────────────
#
# 인천(15062056, 2026-07-07 등록본, UTF-8 BOM, 7,688행):
#   년도,월,항공사(ICAO),항공사(IATA),항공사명,국제_국내,노선,국가,공항,도착_출발,정기_부정기,
#   여객_화물,운항(편),유임승객(명),무임승객(명),환승객(명),직화물(kg),환적화물(kg),우편물(kg),수하물(kg)
#   — 총여객 열은 없다. 여객 = 유임 + 무임 + 환승(데이터셋 설명과 같은 정의). 숫자 뒤에 공백이 붙는다.
INCHEON_REQUIRED = ("년도", "월", "국제_국내", "국가", "운항(편)")
INCHEON_PAX = ("유임승객(명)", "무임승객(명)", "환승객(명)")

# country_resolve 가 못 붙이는 이름(실제 파일에서 15개 확인). 공용 표에 넣지 않는다 — '조지아'처럼
# 뉴스 본문에선 미국 주와 겹치는 이름이 있어서, 이 자료(항공 실적의 국가 열) 안에서만 쓴다.
# 하와이는 미국 주라 USA 로 합치고, 괌·사이판·마카오는 별도 지역 코드 그대로 둔다(지어 합치지 않음).
NAME_TO_ISO3 = {
    "하와이": "USA", "괌": "GUM", "사이판": "MNP", "마카오": "MAC",
    "체코": "CZE", "카자흐스탄": "KAZ", "아제르바이잔": "AZE", "룩셈부르크": "LUX",
    "헝가리": "HUN", "투르크메니스탄": "TKM", "우즈베키스탄": "UZB", "키르기즈스탄": "KGZ",
    "아르메니아": "ARM", "조지아": "GEO", "크로아티아": "HRV",
}


def _num(v) -> float | None:
    if v is None:
        return None
    t = str(v).replace(",", "").strip()
    if t in ("", "-"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _rows(text: str, required: tuple[str, ...]) -> tuple[list[str], list[list[str]], dict]:
    reader = csv.reader(io.StringIO(text))
    header = [h.strip() for h in (next(reader, None) or [])]
    missing = [c for c in required if c not in header]
    if not header or missing:
        raise FetchError(f"열이 다름 — 없는 열 {missing} · 머리글 {header[:24]}")
    return header, [r for r in reader if r and len(r) >= len(header)], {c: header.index(c) for c in header}


def aggregate(text: str) -> dict:
    """인천 CSV → 국제선 국가별 여객(유임+무임+환승)·운항편수. 한국(국내) 행은 뺀다."""
    from .country_resolve import resolve_country

    header, rows, ix = _rows(text, INCHEON_REQUIRED + INCHEON_PAX)
    by_country: dict[str, dict] = {}
    unmapped: dict[str, float] = {}
    periods, skipped_domestic = set(), 0
    for row in rows:
        if row[ix["국제_국내"]].strip() != "국제":
            skipped_domestic += 1
            continue
        periods.add(f"{row[ix['년도']].strip()} {row[ix['월']].strip()}")
        name = row[ix["국가"]].strip()
        pax = sum(_num(row[ix[c]]) or 0 for c in INCHEON_PAX)
        flights = _num(row[ix["운항(편)"]]) or 0
        iso3 = NAME_TO_ISO3.get(name) or resolve_country(name)
        if iso3 is None:
            unmapped[name] = unmapped.get(name, 0) + pax
            continue
        if iso3 == "KOR":
            continue
        c = by_country.setdefault(iso3, {"passengers": 0, "flights": 0, "name": name})
        c["passengers"] += int(pax)
        c["flights"] += int(flights)
    return {
        "rows": len(rows), "skipped_domestic": skipped_domestic,
        "period": [min(periods), max(periods)] if periods else None,
        "by_country": by_country,
        "unmapped": dict(sorted(unmapped.items(), key=lambda kv: -kv[1])[:30]),
    }


def fetch_snapshot(session=None) -> dict:
    """기준 스냅샷 payload(인천). 실패는 FetchError — 기존 스냅샷은 reference_snapshots 가 지킨다."""
    try:
        raw, route = download_csv(DATASETS[0]["pk"], session)
        agg = aggregate(decode(raw))
    except (FetchError, requests.RequestException) as e:
        raise FetchError(f"인천 자료 실패 — {e}") from e
    return build_payload(agg, route, fetched_by="auto")


def build_payload(agg: dict, route: dict, fetched_by: str) -> dict:
    return {
        "snapshot_date": dt.date.today().isoformat(),
        "fetched_by": fetched_by,
        "source": "공공데이터포털 파일 데이터 15062056(인천국제공항공사 항공사별 노선별 운송실적)",
        "source_url": PAGE_URL.format(pk=DATASETS[0]["pk"]),
        "basis": "인천공항 국제선 국가별 여객 수(유임+무임+환승, 도착+출발)·운항편수 — 자료 기간 합계",
        "scope_note": "인천공항만 — 김해·김포·제주 등 국제선은 빠짐",
        "period": agg["period"],
        "route": route,
        "rows": agg["rows"],
        "unmapped": agg["unmapped"],
        "by_country": agg["by_country"],
    }

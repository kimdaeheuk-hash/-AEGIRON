"""기준 스냅샷 수집 — 원본에서 받아 payload를 만든다. **파일은 쓰지 않는다.**

## 왜 스크립트에서 꺼냈나 (2026-09-04)

WHO 사전적격성 백신(284건)과 IHR 역량(194개국)은 `scripts/` 안의 CLI 로만
받을 수 있었다. 그래서 **아무도 안 불렀다** — 주간작업은 기준선·국가지표만
갱신하고, 이 두 파일은 사람이 손으로 돌려야 새로 받아졌다.

점검(2026-09-04) 결과 두 파일 모두 `snapshot_date`가 2026-09-02에 멈춰 있었고,
**나이를 재는 코드가 코드베이스에 하나도 없었다.** 파일이 몇 달 묵어도 발할라는
계속 `available: true`로 자신 있게 답한다. 이건 어제 고친 '설정을 근거로 능력을
주장하는' 패턴과 같은 종류다 — 파일이 있다는 것과 데이터가 최신이라는 것은
다른 말이다.

수집을 여기로 옮기면 운영(주간작업)이 직접 부를 수 있다. 스크립트는 이 함수를
부르는 얇은 껍데기로 남는다.

## ★ 여기서는 파일을 쓰지 않는다 ★

받아온 것을 검증 없이 덮어쓰면, 원본 표 구조가 바뀐 날 **멀쩡하던 스냅샷이
쓰레기로 덮인다.** 8월 KDCA 쉼표 사고가 정확히 그 모양이었다(파서가 깨지자
한 주치 데이터가 통째로 날아갔다). 그래서 이 모듈은 payload를 **돌려주기만**
하고, 검증·기록은 reference_snapshots가 맡는다.
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import re
import time

import requests

# ══════════════════════════════════════════════
# WHO 사전적격성 백신
# ══════════════════════════════════════════════
PQ_BASE = "https://extranet.who.int/prequal/vaccines/prequalified-vaccines"
PQ_COLUMNS = ["prequalified_date", "vaccine_type", "brand", "presentation",
              "doses", "manufacturer", "regulatory_authority"]
PQ_MAX_PAGES = 30

# 규제기관 이름 → 그 기관이 속한 나라(ISO3).
# ★ 규제기관은 제조지가 아니라 감독 관할이다 ★ 회사가 다른 나라 공장에서 만들 수
# 있다. 그래서 이 표를 '생산국'이 아니라 '감독국'으로 쓴다.
NRA_COUNTRY: dict[str, str] = {
    "Central Drugs Standard Control Organization": "IND",
    "Ministry of Food and Drug Safety": "KOR",
    "European Medicines Agency": "EUR",              # 초국가 기관 — 나라가 아니다
    "Federal Agency for Medicines and Health Products": "BEL",
    "National Agency of Drug and Food Control Indonesia": "IDN",
    "National Medical Products Administration": "CHN",
    "Bulgarian Drug Agency": "BGR",
    "Agence nationale de sécurité du médicament et des produits de santé": "FRA",
    "CBER/FDA": "USA",
    "US Food and Drug Administration- Office of Vaccine Research and Review": "USA",
    "Centro para el Control Estatal de la Calidad de los Medicamentos": "CUB",
    "Medicines Evaluation Board (MEB)": "NLD",
    "Agencia Nacional da Vigilancia Sanitaria": "BRA",
    "Federal Service on Surveillance in Healthcare (ROSZDRAVNADZOR)": "RUS",
    "Federal Service on Surveillance in Healthcare (ROSZDRAVNADZOR) "
    "of the Russian Federation": "RUS",
    "Danish Medicines Agency": "DNK",
    "Ministère de la Santé publique": "SEN",
    "Pharmaceutical and Medical Devices Agency": "JPN",
    "Health Canada - Santé Canada": "CAN",
    "Paul-Ehrlich-Institut": "DEU",
    "Medical Products Agency": "SWE",
    "Swissmedic": "CHE",
    "Therapeutic Goods Administration": "AUS",
    "Japan BCG Laboratory": "JPN",
    "Thai Food and Drug Administration": "THA",
    "Ministry of Health of the Republic of Kazakhstan": "KAZ",
    "Instituto Nacional de Vigilancia de Medicamentos y Alimentos": "COL",
    "Vietnam Administration of Medical Science": "VNM",
}


def _cells(row_html: str) -> list[str]:
    out = []
    for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S):
        text = re.sub(r"<[^>]+>", "", cell)
        out.append(re.sub(r"\s+", " ", htmllib.unescape(text)).strip())
    return out


def _pq_page(page: int) -> list[list[str]]:
    resp = requests.get(PQ_BASE, params={"page": page}, timeout=120,
                        headers={"User-Agent": "AEGIRON/1.0"})
    resp.raise_for_status()
    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, re.S):
        cells = _cells(row_html)
        if len(cells) == len(PQ_COLUMNS):
            rows.append(cells)
    return rows


def fetch_vaccine_supply(sleep: float = 0.5) -> dict:
    """WHO 사전적격성 백신 목록 payload. HTML 표를 긁는다(JSON API가 없다).

    표 구조가 바뀌면 열 수가 안 맞아 행이 0건이 되므로, 건수 검증은
    reference_snapshots가 기존 스냅샷과 대조해서 한다."""
    records, seen = [], set()
    for page in range(0, PQ_MAX_PAGES):
        rows = _pq_page(page)
        fresh = [r for r in rows if tuple(r) not in seen]
        for r in fresh:
            seen.add(tuple(r))
        if not fresh:
            break
        records.extend(dict(zip(PQ_COLUMNS, r)) for r in fresh)
        if sleep:
            time.sleep(sleep)

    unmapped = sorted({r["regulatory_authority"] for r in records
                       if r["regulatory_authority"] not in NRA_COUNTRY})
    for record in records:
        # ★ 모르는 기관을 아무 나라로 넣지 않는다 ★ None으로 두고 따로 센다.
        record["authority_country"] = NRA_COUNTRY.get(record["regulatory_authority"])

    return {
        "source": "WHO Prequalified Vaccines (사전적격성 목록)",
        "source_url": PQ_BASE,
        "snapshot_date": dt.date.today().isoformat(),
        "record_count": len(records),
        "vaccine_type_count": len({r["vaccine_type"] for r in records}),
        "manufacturer_count": len({r["manufacturer"] for r in records}),
        "unmapped_authorities": unmapped,
        "records": records,
        "limits": [
            "WHO 사전적격성은 UN 조달용 심사다. 여기 없다고 그 나라가 백신을 못 "
            "만든다는 뜻이 아니다 — 자국 시장만 겨냥한 백신은 신청하지 않는다.",
            "규제기관은 감독 관할이지 제조지가 아니다. 회사가 다른 나라 공장에서 "
            "만들 수 있다.",
            "목록에 제조사가 한 곳뿐이라고 세상에 한 곳뿐인 것은 아니다. "
            "사전적격성을 받은 곳이 하나라는 뜻이다.",
        ],
    }


# ══════════════════════════════════════════════
# WHO IHR 국가 역량(SPAR)
# ══════════════════════════════════════════════
GHO = "https://ghoapi.azureedge.net/api"

# WHO SPAR 2차 도구(2021~)의 15개 역량. 코드 순서가 곧 WHO 문서의 순서다.
CAPACITIES = {
    "C01": "정책·법·제도",
    "C02": "IHR 조정·국가연락창구",
    "C03": "재원",
    "C04": "실험실",
    "C05": "감시",
    "C06": "인력",
    "C07": "보건위기 관리",
    "C08": "보건의료 서비스 제공",
    "C09": "감염 예방·관리",
    "C10": "위험 소통·주민 참여",
    "C11": "입국지점·국경 보건",
    "C12": "인수공통감염병",
    "C13": "식품 안전",
    "C14": "화학 사고",
    "C15": "방사선 비상",
}


def _gho_capacity(code: str) -> list[dict]:
    resp = requests.get(f"{GHO}/IHRSPAR2_{code}", timeout=120)
    resp.raise_for_status()
    return resp.json().get("value") or []


def fetch_ihr_capacity() -> dict:
    """WHO GHO의 IHR SPAR 국가 자가평가 payload.

    ★ 자가평가다 ★ 각국이 스스로 매긴 점수이지 WHO가 검증한 값이 아니다.
    그 사실을 payload 안에 박아둔다 — 파일만 보는 사람도 알아야 한다."""
    by_country: dict[str, dict] = {}
    years: set[int] = set()

    for code in CAPACITIES:
        for row in _gho_capacity(code):
            # ★ 집계행을 국가로 세지 않는다 ★
            if row.get("SpatialDimType") != "COUNTRY":
                continue
            iso3, year = row.get("SpatialDim"), row.get("TimeDim")
            raw = (row.get("Value") or "").strip()
            if not iso3 or not year or not raw.isdigit():
                continue
            years.add(year)
            by_country.setdefault(iso3, {}).setdefault(str(year), {})[code] = int(raw)

    if not years:
        # 연도가 하나도 없으면 max()가 터진다. 빈 수집을 payload로 만들지 않는다.
        raise RuntimeError("GHO에서 유효한 연도를 하나도 못 받았다")

    return {
        "source": "WHO Global Health Observatory — IHR State Party Self-Assessment "
                  "Annual Report (SPAR, 2차 도구)",
        "source_url": f"{GHO}/IHRSPAR2_C05",
        "snapshot_date": dt.date.today().isoformat(),
        "latest_year": max(years),
        "years": sorted(years),
        "capacities": CAPACITIES,
        "country_count": len(by_country),
        # ★ 이 자료의 성격 ★ 파일 자체에 박아둔다.
        "is_self_assessed": True,
        "assessment_note": "각국이 스스로 매긴 점수다. WHO가 검증한 값이 아니다.",
        "scores": by_country,
    }


# ══════════════════════════════════════════════
# 규제 승인 제품 (openFDA)
# ══════════════════════════════════════════════
# ★ 이 샌드박스에서 엔드포인트를 실제로 찔러보지 못했다 ★ 개발 환경의 외부
# 접속이 조직 정책으로 막혀 있다(403). 그래서 응답 파싱을 방어적으로 짜고,
# 저장 전 검증(reference_snapshots.validate)이 이상한 결과를 걸러내게 둔다.
# 운영에서 처음 도는 날 능력 장부에 성공/실패가 남으므로, 안 되면 조용하지 않다.
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_LIMIT = 20          # 예시 몇 개만 있으면 된다. 전수 수집이 목적이 아니다.
OPENFDA_SLEEP = 0.4         # 키 없이 쓰는 공개 API — 예의상 간격을 둔다.


def _openfda_products(term: str, timeout: int = 30) -> tuple[int, list[str]]:
    """적응증에 그 낱말이 있는 승인 제품 수와 이름 몇 개. (총건수, 예시).

    404 는 '결과 없음'이다 — openFDA 는 매칭이 없으면 404 를 준다. 실패가 아니다.
    그 둘을 섞으면 조회 실패가 '승인 제품 없음'이라는 발견으로 둔갑한다."""
    resp = requests.get(
        OPENFDA_LABEL_URL,
        params={"search": f'indications_and_usage:"{term}"', "limit": OPENFDA_LIMIT},
        timeout=timeout,
        headers={"User-Agent": "AEGIRON/1.0"},
    )
    if resp.status_code == 404:
        return 0, []
    resp.raise_for_status()
    body = resp.json() or {}

    total = ((body.get("meta") or {}).get("results") or {}).get("total")
    if total is None:
        raise RuntimeError("openFDA 응답에 meta.results.total 이 없음(형식 변경 의심)")

    names: list[str] = []
    for row in body.get("results") or []:
        of = row.get("openfda") or {}
        for key in ("brand_name", "generic_name"):
            for value in of.get(key) or []:
                if value and value not in names:
                    names.append(value)
                    break
            if names and names[-1]:
                break
    return int(total), names[:5]


def fetch_approved_products() -> dict:
    """위협별 승인 제품 현황 payload.

    ★ 조회 실패를 '없음'으로 접지 않는다 ★ 실패한 위협은 by_threat 에 아예 넣지
    않는다. 그러면 소비자(approved_products.products_for)가 '이 스냅샷이 조회하지
    않은 위협'으로 읽어 unknown 으로 센다 — 0 으로 세는 것과 전혀 다르다."""
    from .approved_products import THREAT_SEARCH_TERMS

    by_threat: dict[str, dict] = {}
    failed: list[str] = []
    for pathogen, terms in THREAT_SEARCH_TERMS.items():
        if not terms:
            continue                       # 정의상 검색 불가(Novel) — 조회 안 함
        total, examples = 0, []
        ok = False
        for term in terms:
            try:
                count, names = _openfda_products(term)
            except Exception:              # noqa: BLE001
                continue                   # 이 낱말만 실패 — 다음 낱말로
            ok = True
            total = max(total, count)
            for n in names:
                if n not in examples:
                    examples.append(n)
            time.sleep(OPENFDA_SLEEP)
        if not ok:
            failed.append(pathogen)        # 이 위협은 한 낱말도 못 물었다
            continue
        by_threat[pathogen] = {"product_count": total, "examples": examples[:5],
                               "terms": terms}

    if not by_threat:
        raise RuntimeError("모든 위협 조회 실패 — 스냅샷을 만들지 않는다")

    return {
        "source": "openFDA drug/label (미국 FDA 라벨 적응증 검색)",
        "source_url": OPENFDA_LABEL_URL,
        "snapshot_date": dt.date.today().isoformat(),
        "by_threat": by_threat,
        "threat_count": len(by_threat),
        "lookup_failed": failed,
        "limits": [
            "미국 FDA 허가다. 한국에서 쓸 수 있다는 뜻이 아니다 — 국내 허가는 "
            "식약처 자료가 필요하고 아직 못 본다.",
            "허가가 있다는 것이지 물량이 있다는 뜻이 아니다. 생산량·재고·수출통제는 "
            "이 자료에 없다.",
            "적응증 낱말 검색이라, 라벨 표현이 다르면 안 걸린다. 없다고 승인 제품이 "
            "없는 것은 아니다.",
        ],
    }


# ══════════════════════════════════════════════
# 한국 국제선 국가별 운송 실적(공공데이터포털 파일 데이터) — 2026-10-19 ⑦
# ══════════════════════════════════════════════

def fetch_kor_route_stats() -> dict:
    """세부 경로·열 고르기는 kor_route_stats 모듈에 있다(확인 못 한 부분과 실패 사유 포함)."""
    from .kor_route_stats import fetch_snapshot
    return fetch_snapshot()

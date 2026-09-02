# -*- coding: utf-8 -*-
"""WHO 사전적격성(PQ) 백신 목록을 내려받아 스냅샷으로 저장한다.

## 왜 필요했나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해! 바이오산업이 발할라에서 진행되지 않아?"*

맞는 지적이었다. 발할라에는 **생산 주권** 이라는 축이 원래 설계돼 있는데
(`biodefense_readiness.compute_readiness` 의 `domestic_producible`), 그 값이
**손으로 넣은 참/거짓** 이었다. 시연 데이터에만 있고 실제 근거가 없었다.

## 자료 — WHO Prequalified Vaccines

UN 기관이 조달하려면 통과해야 하는 목록이다. 백신마다 **제조사**와 **감독
규제기관**이 붙어 있어서, "어느 나라가 이 백신을 만들 수 있는가" 를 볼 수 있다.

실측(2026-09-02): 284건 · 56종 · 제조사 51곳 · 규제기관 20곳.

    인도 CDSCO      130건 (46%)
    한국 식약처       23건  ← 세계 2위
    유럽 EMA         22건

★ HTML 표를 긁는다 ★ JSON API 를 찾아봤지만 없었다(`/prequal/api/vaccines` 404).
표 구조가 바뀌면 여기서 먼저 깨지도록 열 수를 검사한다.
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import json
import re
import time
from pathlib import Path

import requests

BASE = "https://extranet.who.int/prequal/vaccines/prequalified-vaccines"
OUT = Path(__file__).resolve().parent.parent / "algorithms" / "reference" / "who_prequalified_vaccines.json"
COLUMNS = ["prequalified_date", "vaccine_type", "brand", "presentation",
           "doses", "manufacturer", "regulatory_authority"]

# 규제기관 이름 → 그 기관이 속한 나라(ISO3).
# ★ 규제기관은 제조지가 아니라 감독 관할이다 ★ 회사가 다른 나라 공장에서 만들 수
# 있다. 그래서 이 표를 '생산국' 이 아니라 '감독국' 으로 쓴다.
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


def fetch_page(page: int) -> list[list[str]]:
    resp = requests.get(BASE, params={"page": page}, timeout=120,
                        headers={"User-Agent": "AEGIRON/1.0"})
    resp.raise_for_status()
    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, re.S):
        cells = _cells(row_html)
        if len(cells) == len(COLUMNS):
            rows.append(cells)
    return rows


def main() -> None:
    records, seen = [], set()
    for page in range(0, 30):
        rows = fetch_page(page)
        fresh = [r for r in rows if tuple(r) not in seen]
        for r in fresh:
            seen.add(tuple(r))
        print(f"  page {page}: {len(rows)}행 (신규 {len(fresh)})")
        if not fresh:
            break
        records.extend(dict(zip(COLUMNS, r)) for r in fresh)
        time.sleep(0.5)

    if len(records) < 100:
        raise SystemExit(f"수집이 너무 적다({len(records)}건) — 표 구조가 바뀐 듯하다")

    unmapped = sorted({r["regulatory_authority"] for r in records
                       if r["regulatory_authority"] not in NRA_COUNTRY})
    for record in records:
        # ★ 모르는 기관을 아무 나라로 넣지 않는다 ★ None 으로 두고 따로 센다.
        record["authority_country"] = NRA_COUNTRY.get(record["regulatory_authority"])

    payload = {
        "source": "WHO Prequalified Vaccines (사전적격성 목록)",
        "source_url": BASE,
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{OUT}")
    print(f"{len(records)}건 · {payload['vaccine_type_count']}종 · "
          f"제조사 {payload['manufacturer_count']}곳")
    if unmapped:
        print("★ 나라를 모르는 규제기관:", unmapped)


if __name__ == "__main__":
    main()

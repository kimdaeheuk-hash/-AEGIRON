# -*- coding: utf-8 -*-
"""WHO 국제보건규칙(IHR) 자가평가 15개 역량을 내려받아 스냅샷으로 저장한다.

## 왜 스냅샷인가

이 자료는 **1년에 한 번** 갱신된다. 매 호출마다 WHO 를 15번 때리는 건 낭비이고,
WHO 가 잠깐 안 되는 날 국가 비교가 통째로 사라진다. 항공노선(`flight_routes_
by_country.json`)과 같은 방식으로 파일에 떠 놓고 쓴다.

    python scripts/collect_ihr_capacity.py

## ★ 240행 중 국가는 193개다 ★

WHO OData 는 국가 행 사이에 지역·전세계 집계행을 섞어 준다(UNREGION 40 ·
REGION 6 · GLOBAL 1). `SpatialDimType == "COUNTRY"` 로 거르지 않으면 국가 수를
240 으로 잘못 세고, "아프리카 지역" 을 한 나라처럼 순위에 넣게 된다.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import requests

GHO = "https://ghoapi.azureedge.net/api"
OUT = Path(__file__).resolve().parent.parent / "algorithms" / "reference" / "ihr_capacity.json"

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


def fetch_capacity(code: str) -> list[dict]:
    resp = requests.get(f"{GHO}/IHRSPAR2_{code}", timeout=120)
    resp.raise_for_status()
    return resp.json().get("value") or []


def main() -> None:
    by_country: dict[str, dict] = {}
    years: set[int] = set()

    for code, name_ko in CAPACITIES.items():
        rows = fetch_capacity(code)
        for row in rows:
            # ★ 집계행을 국가로 세지 않는다 ★
            if row.get("SpatialDimType") != "COUNTRY":
                continue
            iso3, year = row.get("SpatialDim"), row.get("TimeDim")
            raw = (row.get("Value") or "").strip()
            if not iso3 or not year or not raw.isdigit():
                continue
            years.add(year)
            entry = by_country.setdefault(iso3, {})
            entry.setdefault(str(year), {})[code] = int(raw)
        print(f"  {code} {name_ko} — {len(rows)}행")

    latest = max(years)
    payload = {
        "source": "WHO Global Health Observatory — IHR State Party Self-Assessment "
                  "Annual Report (SPAR, 2차 도구)",
        "source_url": "https://ghoapi.azureedge.net/api/IHRSPAR2_C05",
        "snapshot_date": dt.date.today().isoformat(),
        "latest_year": latest,
        "years": sorted(years),
        "capacities": CAPACITIES,
        "country_count": len(by_country),
        # ★ 이 자료의 성격 ★ 파일 자체에 박아둔다 — 파일만 보는 사람도 알아야 한다.
        "is_self_assessed": True,
        "assessment_note": "각국이 스스로 매긴 점수다. WHO 가 검증한 값이 아니다.",
        "scores": by_country,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{OUT}\n국가 {len(by_country)}개 · 연도 {sorted(years)} · 최신 {latest}")


if __name__ == "__main__":
    main()

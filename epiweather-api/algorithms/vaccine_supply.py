"""백신 공급 구조 — "이걸 만들 수 있는 데가 세상에 몇 곳인가" (2026-09-02).

## 왜 만들었나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해! 바이오산업이 발할라에서 진행되지
않아?"*

발할라에는 **생산 주권** 축이 원래 설계돼 있었다 — `compute_readiness()` 가
받는 `domestic_producible` 이 그것이다. 그런데 그 값이 **손으로 넣은 참/거짓**
이었고, 시연 데이터에만 있었다. 축은 있는데 데이터가 없었다.

## 자료 — WHO 사전적격성 백신 목록

UN 기관이 조달하려면 통과해야 하는 심사다. 백신마다 제조사와 감독 규제기관이
붙어 있다. 실측(2026-09-02): **284건 · 56종 · 제조사 51곳 · 규제기관 20곳.**

    인도 CDSCO   130건 (46%)
    한국 식약처    23건   ← 세계 2위
    유럽 EMA      22건

## ★ 여기서 나오는 진짜 발견 — 공급 병목 ★

56종 중 **17종은 사전적격성을 받은 제조사가 한 곳뿐이다.** 그중에:

    에볼라 백신          머크 한 곳     ← 국제 비상 비축 품목인데 공급원이 하나다
    팬데믹 인플루엔자(H5N1)  아스트라제네카 한 곳

비축이 있다는 것과 공급이 안전하다는 것은 다른 말이다. 그 하나가 멈추면
비축은 다시 안 채워진다. 이건 비축 목록만 봐서는 절대 안 보인다.

## ★ 이 모듈이 말하지 않는 것 ★

- **"이 나라는 백신을 못 만든다" 고 말하지 않는다.** 사전적격성은 UN 조달용
  심사라, 자국 시장만 겨냥한 백신은 아예 신청하지 않는다. 목록에 없는 것과
  못 만드는 것은 다르다.
- **규제기관은 감독 관할이지 제조지가 아니다.** 회사가 다른 나라 공장에서
  만들 수 있다. 그래서 '생산국' 이 아니라 **'감독국'** 이라고 부른다.
- **제조사가 하나라고 세상에 하나인 것은 아니다.** 사전적격성을 받은 곳이
  하나라는 뜻이다. 그래도 UN 조달 경로에서는 그게 곧 병목이다.
- **생산량을 말하지 않는다.** 몇 도즈를 만들 수 있는지는 이 목록에 없다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent / "reference" / "who_prequalified_vaccines.json"

# 우리가 감시하는 질병 이름 → WHO 백신 종류 이름에 들어 있는 낱말.
# ★ 우리 표기가 아니라 WHO 표기로 물어야 한다 ★
DISEASE_VACCINE_TERMS: dict[str, list[str]] = {
    "에볼라": ["Ebola"],
    "콜레라": ["Cholera"],
    "황열": ["Yellow Fever"],
    "수막구균 수막염": ["Menigococcal", "Meningococcal"],   # WHO 표기에 오탈자가 있다
    "엠폭스": ["Mpox", "Smallpox"],
    "인플루엔자(조류·계절)": ["Influenza"],
    "홍역": ["Measles"],
    "뎅기열": ["Dengue"],
    "일본뇌염": ["Japanese Encephalitis"],
    "장티푸스": ["Typhoid"],
    "소아마비": ["Polio"],
    "결핵": ["BCG", "Tuberculosis"],
    "간염": ["Hepatitis"],
    "말라리아": ["Malaria"],
    "폐렴구균": ["Pneumococcal"],
    "로타바이러스": ["Rotavirus"],
    "인유두종바이러스": ["Human Papillomavirus"],
    "광견병": ["Rabies"],
    # ── 사전적격성 백신이 아직 없는 위협들 ────────────────────────────────
    # ★ 검색어를 빼면 안 된다 ★ 빼면 "표에 없는 병"(= 우리가 안 찾아봤다)으로
    # 나오는데, 실제로는 "찾아봤는데 없다"(= 발견) 이다. 이 둘은 완전히 다르다.
    # 2026-09-02 실측: WHO 사전적격성 56종에 이들 백신은 하나도 없다.
    "MERS": ["MERS", "Middle East Respiratory"],
    "니파": ["Nipah"],
    "라싸열": ["Lassa"],
    "마버그": ["Marburg"],
    "지카": ["Zika"],
    "치쿤구니야": ["Chikungunya"],
    "탄저": ["Anthrax"],
    "한타바이러스": ["Hantavirus", "Hantaan"],
}


def _current_path() -> Path:
    """주간작업이 볼륨에 받은 새 사본이 있으면 그쪽(reference_snapshots.newest)."""
    from .reference_snapshots import newest
    return newest(REFERENCE)


@lru_cache(maxsize=1)
def _snapshot() -> dict | None:
    try:
        return json.loads(_current_path().read_text(encoding="utf-8"))
    except Exception:                                 # noqa: BLE001
        return None


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def supply_for_disease(disease: str) -> dict:
    """그 병의 백신을 사전적격성 받은 곳이 몇 곳인가. **모르면 모른다고 한다.**"""
    snap = _snapshot()
    if not snap:
        return _unavailable(f"기준 파일이 없다: {REFERENCE.name} "
                            "(scripts/collect_vaccine_supply.py 로 만든다)")

    terms = DISEASE_VACCINE_TERMS.get(disease)
    if not terms:
        # ★ 표에 없는 병을 '백신 없음' 으로 접지 않는다 ★
        return _unavailable(f"백신 검색어 표에 없는 병: {disease}")

    hits = [r for r in snap["records"]
            if any(t.lower() in (r["vaccine_type"] or "").lower() for t in terms)]
    if not hits:
        return {
            "available": True, "disease": disease, "prequalified_count": 0,
            "manufacturers": [], "authority_countries": [],
            "is_single_source": None,
            "note": "WHO 사전적격성 목록에 없다. 백신이 없다는 뜻이 아니라 "
                    "UN 조달용 심사를 받은 제품이 없다는 뜻이다.",
        }

    makers = sorted({r["manufacturer"] for r in hits})
    countries = sorted({r["authority_country"] for r in hits if r["authority_country"]})
    return {
        "available": True,
        "disease": disease,
        "prequalified_count": len(hits),
        "vaccine_types": sorted({r["vaccine_type"] for r in hits}),
        "manufacturers": makers,
        "manufacturer_count": len(makers),
        # ★ 병목 판정 ★ 사전적격성 제조사가 하나뿐이면 UN 조달 경로가 한 줄이다.
        "is_single_source": len(makers) == 1,
        "authority_countries": countries,
        "korea_supervises": "KOR" in countries,
        "source": snap["source"],
        "snapshot_date": snap["snapshot_date"],
        "limits": snap["limits"],
    }


def chokepoints() -> dict:
    """제조사가 한 곳뿐인 백신들. **UN 조달 경로의 병목이다.**"""
    snap = _snapshot()
    if not snap:
        return _unavailable(f"기준 파일이 없다: {REFERENCE.name}")

    by_type: dict[str, set[str]] = {}
    for record in snap["records"]:
        by_type.setdefault(record["vaccine_type"], set()).add(record["manufacturer"])

    single = sorted(
        ({"vaccine_type": vaccine, "manufacturer": next(iter(makers))}
         for vaccine, makers in by_type.items() if len(makers) == 1),
        key=lambda r: r["vaccine_type"],
    )
    return {
        "available": True,
        "vaccine_type_count": len(by_type),
        "single_source_count": len(single),
        "single_source": single,
        "snapshot_date": snap["snapshot_date"],
        "limits": snap["limits"] + [
            "이 목록은 위험 순위가 아니다. 제조사가 여럿이어도 한 공장에서 "
            "나올 수 있고, 생산량은 이 자료에 없다.",
        ],
    }


def country_portfolio(iso3: str) -> dict:
    """그 나라 규제기관이 감독하는 사전적격성 백신. **'만들 수 있는 전부' 가 아니다.**"""
    snap = _snapshot()
    if not snap:
        return _unavailable(f"기준 파일이 없다: {REFERENCE.name}")

    iso3 = (iso3 or "").strip().upper()
    hits = [r for r in snap["records"] if r.get("authority_country") == iso3]
    if not hits:
        return {
            "available": True, "iso3": iso3, "prequalified_count": 0,
            "vaccine_types": [], "manufacturers": [],
            "note": "이 나라 규제기관이 감독하는 사전적격성 백신이 없다. "
                    "백신을 못 만든다는 뜻이 아니다 — UN 조달용 심사를 받은 "
                    "제품이 없다는 뜻이다.",
        }

    return {
        "available": True,
        "iso3": iso3,
        "prequalified_count": len(hits),
        "vaccine_types": sorted({r["vaccine_type"] for r in hits}),
        "manufacturers": sorted({r["manufacturer"] for r in hits}),
        "world_share": round(len(hits) / snap["record_count"], 3),
        "snapshot_date": snap["snapshot_date"],
        "limits": snap["limits"],
    }

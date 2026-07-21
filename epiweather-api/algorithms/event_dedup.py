"""이벤트 중복제거 — 인수인계서 Part5 ⑩.

WHO 에볼라 + Perplexity 에볼라 + Wikipedia 에볼라처럼 여러 출처가 같은
사건을 각자 보고하면, NLP 구조화 추출(⑦)이 만든 extracted_signals 행은
디스크상으로는 별개다. 이 모듈이 disease 기준으로 같은 사건임을 식별해
신뢰도 가중 평균으로 병합한다 — "같은 에볼라 사건을 출처 3개가 또
알려왔다"는 식의 중복 경보를 막는 게 목적.

질병명은 자유문장 추출이라 표기가 들쭉날쭉해서(예: "에볼라" vs
"에볼라 바이러스(Bundibugyo)" vs "ebola") 작은 별칭 사전으로 정규화한다.
사전에 없는 질병명은 병합하지 않고 단독 이벤트로 둔다(잘못 합치는 것보다
안 합치는 쪽이 안전).

국가명은 nlp_extract.py(⑦)가 직접 뽑아내는 country_iso3(ISO 3166-1 alpha-3)로
정확매칭한다 — country_iso3가 없는 구형 레코드만 location 자유문장 별칭매칭으로
폴백한다(country_risk._record_matches_country).
"""
from __future__ import annotations

import db
from .country_risk import COUNTRIES, SIGNAL_TYPE_SEVERITY, _record_matches_country
from .gai import _tier

DISEASE_ALIASES = {
    "에볼라": ["에볼라", "ebola", "붕디부고", "bundibugyo"],
    "MERS": ["mers", "메르스", "중동호흡기증후군"],
    "콜레라": ["콜레라", "cholera"],
    "조류인플루엔자": ["조류인플루엔자", "조류 인플루엔자", "avian flu", "h5n1", "조류독감"],
    "뎅기열": ["뎅기열", "dengue"],
    "코로나19": ["코로나", "covid", "sars-cov-2"],
}


def normalize_disease(raw: str | None) -> str | None:
    if not raw:
        return None
    lowered = raw.lower()
    for canonical, aliases in DISEASE_ALIASES.items():
        if any(a.lower() in lowered for a in aliases):
            return canonical
    return raw.strip()


def _matched_countries(record: dict) -> list[str]:
    return [cid for cid, c in COUNTRIES.items() if _record_matches_country(record, cid, c["aliases"])]


def dedupe_events(limit: int = 500) -> list[dict]:
    records = db.list_extracted_signals(limit=limit)

    groups: dict[str, list[dict]] = {}
    for r in records:
        key = normalize_disease(r["disease"])
        if key is None:
            key = f"__unclassified_{r['id']}"  # 질병명 불명 — 병합하지 않고 단독 유지
        groups.setdefault(key, []).append(r)

    events = []
    for disease_key, members in groups.items():
        countries: set[str] = set()
        for m in members:
            countries.update(_matched_countries(m))

        scored = [(SIGNAL_TYPE_SEVERITY.get(m["signal_type"], 40), m["source_trust"]) for m in members]
        weight_sum = sum(t for _, t in scored)
        merged_score = round(sum(s * t for s, t in scored) / weight_sum, 1) if weight_sum else None

        dates = [m["signal_date"] for m in members if m["signal_date"]]
        disease_label = members[0]["disease"] if disease_key.startswith("__unclassified_") else disease_key

        events.append({
            "disease": disease_label,
            "countries": sorted(countries),
            "merged_score": merged_score,
            "tier": _tier(merged_score) if merged_score is not None else None,
            "source_count": len(members),
            "sources": sorted({m["source"] for m in members}),
            "latest_signal_date": max(dates) if dates else None,
            "members": [
                {
                    "source": m["source"], "signal_type": m["signal_type"],
                    "source_trust": m["source_trust"], "signal_date": m["signal_date"],
                    "extracted_at": m["extracted_at"],
                }
                for m in members
            ],
        })

    events.sort(key=lambda e: (e["merged_score"] is None, -(e["merged_score"] or 0)))
    return events

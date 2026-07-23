"""이벤트 중복제거 — 인수인계서 Part5 ⑩ (㉚에서 교차언어 의미 클러스터링 추가).

WHO 에볼라 + Perplexity 에볼라 + Wikipedia 에볼라처럼 여러 출처가 같은
사건을 각자 보고하면, NLP 구조화 추출(⑦)이 만든 extracted_signals 행은
디스크상으로는 별개다. 이 모듈이 같은 사건임을 식별해 신뢰도 가중 평균으로
병합한다 — "같은 에볼라 사건을 출처 3개가 또 알려왔다"는 식의 중복 경보 방지.

두 가지 클러스터링 방식(응답의 clustering_method로 항상 구분해 노출):
  1) disease_name_fallback(기본, 결정론적): 질병명을 작은 별칭 사전으로 정규화해
     같은 이름끼리 묶는다. 빠르고 재현 가능하지만, 질병명 표기가 문자로 안
     겹치면(예: 태국어 "람파 정체불명 폐렴" vs 영어 "unknown pneumonia in
     northern Thailand") 같은 사건을 별개로 센다.
  2) semantic_llm(api_key 있을 때): Claude가 여러 언어·표기의 신호를 '뜻'으로
     묶는다 — 질병명이 문자로 안 겹쳐도 같은 실제 발병이면 하나로. EIOS/EMM이
     20년 들여 만든 다국어 클러스터링을 후발주자 이점(LLM)으로 흉내낸다.
     실패/키 없음이면 1)로 자동 폴백(회귀 없음). 억지로 합치지 않게 "확실히
     같은 사건일 때만 병합"을 지시 — 기존 "안 합치는 쪽이 안전" 원칙 유지.

국가명은 nlp_extract.py(⑦)가 직접 뽑아내는 country_iso3로 정확매칭한다 —
country_iso3가 없는 구형 레코드만 location 자유문장 별칭매칭으로 폴백한다.
"""
from __future__ import annotations
import json
from collections import Counter

import db
from .country_risk import COUNTRIES, SIGNAL_TYPE_SEVERITY, _record_matches_country
from .gai import _tier

CLUSTER_MODEL = "claude-haiku-4-5-20251001"

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


CLUSTER_PROMPT = """다음은 감염병 감시 신호 목록이야(여러 언어·표기 섞여 있음). 같은 '실제 발병 사건'을
가리키는 신호끼리 묶어. 질병명 표기가 언어마다 달라도(예: "람파 정체불명 폐렴" vs "unknown
pneumonia northern Thailand") 같은 병원체·같은 지역·겹치는 시기면 같은 사건이야.

중요 규칙:
- 확실히 같은 사건일 때만 묶어. 조금이라도 애매하면 각각 단독으로 둬(잘못 합치는 것보다 안전).
- 병원체가 다르거나(에볼라 vs 콜레라), 지역이 명백히 다르거나, 시기가 동떨어지면 절대 합치지 마.
- 모든 id는 정확히 한 그룹에만. 단독 사건은 그 id 하나만 든 그룹으로.

JSON 객체만 출력(다른 텍스트 절대 금지):
{{"clusters": [[id, id, ...], [id], ...]}}

신호 목록:
{items}"""


def semantic_cluster(records: list[dict], api_key: str) -> dict | None:
    """records를 같은 실제 사건끼리 묶어 {record_id: cluster_index} 반환.
    Claude 호출/파싱 실패 시 None(호출자가 결정론적 방식으로 폴백)."""
    if not records:
        return {}
    import anthropic

    items = [
        {
            "id": r["id"], "disease": r.get("disease"), "location": r.get("location"),
            "iso3": r.get("country_iso3"), "date": r.get("signal_date"),
            "text": (r.get("raw_text") or "")[:200],
        }
        for r in records
    ]
    valid_ids = {r["id"] for r in records}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLUSTER_MODEL, max_tokens=1500,
            messages=[{"role": "user", "content": CLUSTER_PROMPT.format(
                items=json.dumps(items, ensure_ascii=False)
            )}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        clusters = data.get("clusters")
        if not isinstance(clusters, list):
            return None
    except Exception:
        return None

    assignment: dict = {}
    for idx, group in enumerate(clusters):
        if not isinstance(group, list):
            return None
        for rid in group:
            if rid in valid_ids and rid not in assignment:  # 중복 배정은 먼저 나온 그룹 우선
                assignment[rid] = idx
    # 모델이 빠뜨린 id는 각각 단독 사건으로 — 유실 방지
    next_idx = len(clusters)
    for rid in valid_ids:
        if rid not in assignment:
            assignment[rid] = next_idx
            next_idx += 1
    return assignment


def _build_event(label: str | None, members: list[dict]) -> dict:
    countries: set[str] = set()
    for m in members:
        countries.update(_matched_countries(m))

    scored = [(SIGNAL_TYPE_SEVERITY.get(m["signal_type"], 40), m["source_trust"]) for m in members]
    weight_sum = sum(t for _, t in scored)
    merged_score = round(sum(s * t for s, t in scored) / weight_sum, 1) if weight_sum else None
    dates = [m["signal_date"] for m in members if m["signal_date"]]

    return {
        "disease": label,
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
    }


def _most_common_disease(members: list[dict]) -> str | None:
    diseases = [m["disease"] for m in members if m.get("disease")]
    if not diseases:
        return None
    return Counter(diseases).most_common(1)[0][0]


def dedupe_events(limit: int = 500, api_key: str | None = None) -> list[dict]:
    """api_key가 있으면 Claude 교차언어 의미 클러스터링(㉚), 없거나 실패하면
    질병명 정규화 기반 결정론적 병합으로 폴백. 어느 방식을 썼는지 각 이벤트의
    clustering_method로 정직하게 표시한다."""
    records = db.list_extracted_signals(limit=limit)

    method = "disease_name_fallback"
    grouped: list[tuple[str | None, list[dict]]] = []

    if api_key:
        assignment = semantic_cluster(records, api_key)
        if assignment is not None:
            method = "semantic_llm"
            by_cluster: dict[int, list[dict]] = {}
            for r in records:
                by_cluster.setdefault(assignment[r["id"]], []).append(r)
            grouped = [(_most_common_disease(members), members) for members in by_cluster.values()]

    if method == "disease_name_fallback":
        by_key: dict[str, list[dict]] = {}
        for r in records:
            key = normalize_disease(r["disease"])
            if key is None:
                key = f"__unclassified_{r['id']}"  # 질병명 불명 — 병합하지 않고 단독 유지
            by_key.setdefault(key, []).append(r)
        for key, members in by_key.items():
            label = members[0]["disease"] if key.startswith("__unclassified_") else key
            grouped.append((label, members))

    events = []
    for label, members in grouped:
        event = _build_event(label, members)
        event["clustering_method"] = method
        events.append(event)

    events.sort(key=lambda e: (e["merged_score"] is None, -(e["merged_score"] or 0)))
    return events

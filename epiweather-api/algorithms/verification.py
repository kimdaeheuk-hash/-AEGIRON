"""Verification Layer — Phase 2 ⑭ 느리지만 정확한 검증.

Sentinel이 올린 pending 항목을 Perplexity(주) → Tavily(폴백)로 검색해
실제 사건인지 확인하고 DB에 confirmed | dismissed를 기록.

30~60분 주기로 실행 권장 (AI API 비용이 있음).
키가 없으면 해당 단계는 건너뛰고 사유를 반환.
"""
from __future__ import annotations
import os
import datetime as dt

import db

PERPLEXITY_KEY_ENV = "PERPLEXITY_API_KEY"
TAVILY_KEY_ENV     = "TAVILY_API_KEY"

LAYER_KEYWORDS = {
    "official":     ["outbreak", "disease", "confirmed cases", "death"],
    "informal":     ["epidemic", "unusual illness", "health alert"],
    "behavioral":   ["illness spike", "fever", "hospital surge"],
    "environmental":["wastewater", "sewage surveillance"],
    "animal":       ["avian flu", "animal disease", "bird flu", "livestock"],
    "unexplained":  ["unexplained illness", "unknown disease", "mystery illness"],
}


def _perplexity_search(query: str, api_key: str) -> str | None:
    try:
        import requests
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 300,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def _tavily_search(query: str, api_key: str) -> str | None:
    try:
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": 3},
            timeout=20,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return " | ".join(r.get("content", "")[:200] for r in results[:3])
    except Exception:
        pass
    return None


def _assess_evidence(evidence: str, metric: str, layer: str) -> tuple[bool, float]:
    """
    검색 결과를 보고 '실제 사건인가' 판단.
    키워드 일치 개수로 단순 점수 매김 (LLM 없이도 돌아가도록).
    confirmed_threshold 이상이면 confirmed.
    """
    if not evidence:
        return False, 0.0
    text = evidence.lower()
    keywords = LAYER_KEYWORDS.get(layer, ["outbreak", "disease"])
    hits = sum(1 for kw in keywords if kw in text)
    confidence = min(hits / max(len(keywords), 1), 1.0)
    return confidence >= 0.3, round(confidence, 2)


def verify_pending(max_items: int = 10) -> dict:
    """
    pending 항목을 최대 max_items개 검증해 DB 업데이트 후 결과 요약 반환.
    """
    pkey = os.environ.get(PERPLEXITY_KEY_ENV)
    tkey = os.environ.get(TAVILY_KEY_ENV)

    if not pkey and not tkey:
        return {
            "verified": 0,
            "skipped": 0,
            "note": "PERPLEXITY_API_KEY / TAVILY_API_KEY 없음 — 자동 검증 불가. "
                    "수동 검증: POST /api/sentinel/{id}/verify",
        }

    pending = db.list_sentinel_queue(status="pending", limit=max_items)
    confirmed_count = 0
    dismissed_count = 0

    for item in pending:
        layer   = item["layer"]
        metric  = item["metric"]
        ratio   = item["spike_ratio"]
        keywords = " ".join(LAYER_KEYWORDS.get(layer, ["outbreak"]))
        query = (
            f"Recent {layer} disease signal spike: {metric} increased {ratio}x above baseline. "
            f"Search for: {keywords} news in last 7 days. "
            f"Is there actual evidence of an outbreak or health emergency? Answer briefly."
        )

        evidence = None
        if pkey:
            evidence = _perplexity_search(query, pkey)
        if not evidence and tkey:
            evidence = _tavily_search(query, tkey)

        confirmed, confidence = _assess_evidence(evidence or "", metric, layer)
        status = "confirmed" if confirmed else "dismissed"

        db.update_sentinel_verification(
            sentinel_id=item["id"],
            status=status,
            evidence=evidence,
            confidence=confidence,
        )

        if confirmed:
            confirmed_count += 1
        else:
            dismissed_count += 1

    return {
        "verified": confirmed_count + dismissed_count,
        "confirmed": confirmed_count,
        "dismissed": dismissed_count,
        "note": "Perplexity" if pkey else "Tavily",
    }

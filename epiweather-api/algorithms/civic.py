"""Stage 1: 민간 신호 융합 — 정부 대비 선행성 계산."""
from __future__ import annotations
from .common import CIVIC


def fuse_civic(active_ids: list[str]) -> dict:
    """
    활성화된 민간 신호들의 최대 선행일·품질가중 융합 점수 계산.
    """
    sources = [s for s in CIVIC if s["id"] in active_ids]

    if not sources:
        return {
            "lead_days": 0,
            "fused_quality": 0.0,
            "sources": [],
            "government_baseline": {"id": "gov", "nm": "정부 공식 발표", "lead": 0},
        }

    lead_days = max(s["lead"] for s in sources)

    # 품질(q)×볼륨(v) 가중 융합 점수
    fused_q = sum(s["q"] * s["v"] for s in sources) / len(sources)

    return {
        "lead_days": lead_days,
        "fused_quality": round(fused_q, 3),
        "active_count": len(sources),
        "sources": [
            {
                "id": s["id"],
                "nm": s["nm"],
                "sub": s["sub"],
                "lead_days": s["lead"],
                "quality": s["q"],
                "volume": s["v"],
                "active": True,
            }
            for s in sources
        ],
        "inactive_sources": [
            {
                "id": s["id"],
                "nm": s["nm"],
                "lead_days": s["lead"],
                "active": False,
            }
            for s in CIVIC if s["id"] not in active_ids
        ],
        "government_baseline": {"id": "gov", "nm": "정부 공식 발표", "lead": 0},
    }

"""질병 지식 그래프 — Phase 3. 원인-결과 인과 네트워크.

"조류독감 → 가금류 폐사 → 농장 폐쇄 → 인간 감염" 같은
역학적 인과 체인을 그래프로 표현.

현재 신호와 매핑하면:
  - cidrap_avian_flu 급증 → H5N1 인간 전파 위험 경고
  - wiki_ebola_daily 급증 → DRC 유입 경로 추적
  - supply_alert_count 급증 → 공식 발표 전 지역사회 전파 중

API: GET /api/knowledge-graph/{disease}
     GET /api/knowledge-graph
"""
from __future__ import annotations
from typing import Any

DISEASE_GRAPH: dict[str, dict] = {
    "H5N1": {
        "name": "조류인플루엔자 H5N1",
        "risk_level": "high",
        "chain": [
            {"node": "야생조류 H5N1 유행",    "signal": "cidrap_avian_flu",      "lead_days": 30},
            {"node": "가금류 집단폐사",        "signal": "wahis_outbreaks_30d",   "lead_days": 21},
            {"node": "농장 폐쇄·살처분",       "signal": "wahis_watch_hits",      "lead_days": 14},
            {"node": "인간 감염자 첫 보고",    "signal": "cidrap_avian_flu",      "lead_days":  7},
            {"node": "공식 WHO 발표",          "signal": "who_afro_items",        "lead_days":  0},
        ],
        "korea_pathway": "인천공항 → 경기·전남 가금류 농장 → 서울 대형병원",
        "key_signal": "cidrap_avian_flu",
    },
    "Ebola": {
        "name": "에볼라 바이러스병",
        "risk_level": "critical",
        "chain": [
            {"node": "박쥐·유인원 접촉 사례",  "signal": "wiki_ebola_daily",      "lead_days": 21},
            {"node": "농촌 의원 집단 발열",    "signal": "local_news_kw_hits",    "lead_days": 14},
            {"node": "현지 MSF 현장 경보",     "signal": "local_news_kw_hits",    "lead_days": 10},
            {"node": "DRC 보건부 공식 선언",   "signal": "who_afro_items",        "lead_days":  7},
            {"node": "WHO PHEIC",              "signal": "who_afro_items",        "lead_days":  0},
        ],
        "korea_pathway": "인천공항 직항(없음) → 환승(두바이·도하) → 접촉 전파",
        "key_signal": "wiki_ebola_daily",
    },
    "MERS": {
        "name": "중동호흡기증후군 MERS-CoV",
        "risk_level": "high",
        "chain": [
            {"node": "낙타 군집 MERS 감지",   "signal": "wahis_watch_hits",      "lead_days": 30},
            {"node": "리야드 병원 집단감염",   "signal": "cidrap_mers",           "lead_days": 14},
            {"node": "WHO DON 발령",           "signal": "cidrap_mers",           "lead_days":  7},
            {"node": "한국 유입 (2015 선례)",  "signal": "naver_flu_ratio",       "lead_days":  3},
            {"node": "공식 확진 발표",         "signal": "who_afro_items",        "lead_days":  0},
        ],
        "korea_pathway": "인천공항 (중동 직항) → 대형병원 응급실 → 병원 내 전파",
        "key_signal": "cidrap_mers",
    },
    "Dengue": {
        "name": "뎅기열",
        "risk_level": "medium",
        "chain": [
            {"node": "폭염·강수량 급증",       "signal": "environmental",         "lead_days": 45},
            {"node": "모기 지수 급등",         "signal": "environmental",         "lead_days": 30},
            {"node": "방콕·하노이 지역 급증",  "signal": "wiki_dengue_daily",     "lead_days": 14},
            {"node": "해외 귀국자 발열 신고",  "signal": "naver_flu_ratio",       "lead_days":  7},
            {"node": "KDCA 공식 집계",         "signal": "kdca_weekly_total",     "lead_days":  0},
        ],
        "korea_pathway": "인천공항 → 귀국자 발열 → 지역사회 모기 매개 가능성 (10월 이후 낮음)",
        "key_signal": "wiki_dengue_daily",
    },
    "Novel": {
        "name": "원인불명 신종 감염병",
        "risk_level": "unknown",
        "chain": [
            {"node": "원인불명 폐렴 클러스터", "signal": "local_news_kw_hits",    "lead_days": 21},
            {"node": "병원 내 의료진 감염",    "signal": "supply_alert_count",    "lead_days": 14},
            {"node": "소셜·검색 이상 급증",    "signal": "naver_flu_ratio",       "lead_days":  7},
            {"node": "AI 갭필링 이상 탐지",    "signal": "medrxiv_epi_papers",    "lead_days":  5},
            {"node": "WHO 국제 보건 알림",     "signal": "who_afro_items",        "lead_days":  0},
        ],
        "korea_pathway": "인천공항 (감지 전 유입 가능) → 대형병원 응급실 → 의료진 → 지역사회",
        "key_signal": "local_news_kw_hits",
    },
}


def get_disease_graph(disease: str | None = None) -> dict[str, Any]:
    """특정 질병 또는 전체 인과 그래프 반환."""
    if disease:
        key = next((k for k in DISEASE_GRAPH if k.lower() == disease.lower()), None)
        if not key:
            return {"error": f"지원하지 않는 질병. 지원 목록: {list(DISEASE_GRAPH)}"}
        return {key: DISEASE_GRAPH[key]}
    return {
        "diseases": list(DISEASE_GRAPH.keys()),
        "graph":    DISEASE_GRAPH,
        "summary":  [
            {
                "disease":     k,
                "name":        v["name"],
                "risk_level":  v["risk_level"],
                "chain_steps": len(v["chain"]),
                "key_signal":  v["key_signal"],
                "max_lead_days": max(s["lead_days"] for s in v["chain"]),
            }
            for k, v in DISEASE_GRAPH.items()
        ],
    }


def match_active_signals(active_metrics: list[str]) -> list[dict]:
    """
    현재 이상 탐지된 신호(metric 이름 목록)와 지식 그래프를 매핑해
    "어떤 인과 체인이 활성화됐는가" 경고 반환.
    """
    warnings: list[dict] = []
    for disease, info in DISEASE_GRAPH.items():
        triggered = [
            step for step in info["chain"]
            if step["signal"] in active_metrics
        ]
        if triggered:
            earliest_lead = max(s["lead_days"] for s in triggered)
            warnings.append({
                "disease":        disease,
                "name":           info["name"],
                "risk_level":     info["risk_level"],
                "triggered_steps": triggered,
                "estimated_lead_days": earliest_lead,
                "korea_pathway":  info["korea_pathway"],
            })
    warnings.sort(key=lambda w: w["estimated_lead_days"], reverse=True)
    return warnings

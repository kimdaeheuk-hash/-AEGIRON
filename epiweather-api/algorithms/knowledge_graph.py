"""질병 지식 그래프 — Phase 3. 원인-결과 인과 네트워크.

"조류독감 → 가금류 폐사 → 농장 폐쇄 → 인간 감염" 같은
역학적 인과 체인을 그래프로 표현.

현재 신호와 매핑하면:
  - cidrap_avian_flu 급증 → H5N1 인간 전파 위험 경고
  - wiki_ebola_daily 급증 → DRC 유입 경로 추적
  - supply_alert_count 급증 → 공식 발표 전 지역사회 전파 중

주의: 각 체인의 lead_days는 실제 통계 분석이 아니라 과거 사례를 참고해
손으로 추정한 값이다(과거 발병마다 30/21/14/7/0으로 딱 떨어지는 게 그
증거 — 실측이라면 이렇게 규칙적일 수 없음). outbreak_timeline에 실제
발병 사례의 마일스톤이 쌓이면 verify_chain_lead_time()으로 추정치와
실측을 비교할 수 있다 — 사례가 쌓일수록 이 그래프 자체가 더 정확해지는
게 목표. 지금은 비교 결과만 보여주고 그래프를 자동으로 고치진 않는다
(사례 1건으로 5단계 체인을 다시 쓰면 과적합).

API: GET /api/knowledge-graph/{disease}
     GET /api/knowledge-graph
     GET /api/knowledge-graph/{disease}/verify
"""
from __future__ import annotations
import datetime as dt
from typing import Any

import db

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
        return {key: DISEASE_GRAPH[key], "lead_days_estimated": True}
    return {
        "diseases": list(DISEASE_GRAPH.keys()),
        "graph":    DISEASE_GRAPH,
        "lead_days_estimated": True,  # 아래 verify_chain_lead_time()으로 실측 대비 검증 가능
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


# outbreak_timeline 이벤트(main.py._seed_known_timelines가 심어둔 것 등)의
# event_id 접두사 → DISEASE_GRAPH 키 매핑. 실제 발병 사례가 이 접두사로
# 새로 기록되면(POST /api/timeline) 자동으로 검증 대상이 됨.
TIMELINE_EVENT_PREFIXES = {"Ebola": "ebola_", "MERS": "mers_", "Dengue": "dengue_"}

# 이 마일스톤 키 중 하나가 있으면 "공식 선언 시점"으로 간주. status_update나
# year_start처럼 임의로 찍은 앵커는 선언 순간이 아니라서 절대 안 씀 —
# 잘못된 milestone을 "공식 선언"으로 오인하면 검증 자체가 의미 없어짐.
_DECLARATION_MILESTONE_KEYS = ("who_pheic", "drc_official", "official_declaration")


def verify_chain_lead_time(disease: str) -> dict:
    """
    DISEASE_GRAPH의 lead_days(추정치)를 outbreak_timeline의 실제 마일스톤
    날짜와 비교. "첫 신호 마일스톤" ~ "공식 선언 마일스톤" 사이 실측 일수를
    그래프가 주장하는 총 선행일수(체인의 최댓값)와 대조한다.

    비교 가능한 사례가 없으면(공식선언 마일스톤 미기록·마일스톤 1개뿐 등)
    verified=False와 사유만 반환 — 억지로 숫자를 만들지 않는다.
    """
    info = DISEASE_GRAPH.get(disease)
    if not info:
        return {"disease": disease, "verified": False, "note": "지원하지 않는 질병"}

    prefix = TIMELINE_EVENT_PREFIXES.get(disease)
    if not prefix:
        return {"disease": disease, "verified": False, "note": "타임라인 이벤트 매핑 없음"}

    events = [e for e in db.list_timeline_events() if e["event_id"].startswith(prefix)]
    claimed_lead_days = max(s["lead_days"] for s in info["chain"])

    cases = []
    for e in events:
        milestones = db.get_timeline(e["event_id"])["milestones"]
        if len(milestones) < 2:
            continue
        dates_by_key = {m["milestone"]: m["event_date"] for m in milestones}
        declaration_date = next(
            (dates_by_key[k] for k in _DECLARATION_MILESTONE_KEYS if k in dates_by_key), None
        )
        if declaration_date is None:
            continue
        first_date = min(m["event_date"] for m in milestones)
        observed_days = (dt.date.fromisoformat(declaration_date) - dt.date.fromisoformat(first_date)).days
        cases.append({
            "event_id": e["event_id"],
            "first_signal_date": first_date,
            "official_declaration_date": declaration_date,
            "observed_lead_days": observed_days,
            "graph_claimed_lead_days": claimed_lead_days,
            "difference_days": observed_days - claimed_lead_days,
        })

    return {
        "disease": disease,
        "verified": bool(cases),
        "cases": cases,
        # 실측 사례가 있으면 하드코딩 추정치 옆에 '실측 캘리브레이션' 값을 함께
        # 노출한다(㉖). 그래프의 5단계 체인을 자동으로 덮어쓰진 않는다 — 사례
        # 1건으로 전체 체인을 다시 쓰면 과적합이라(모듈 상단 설계원칙), 대신
        # "심사 자료에 넣을 수 있는 실측 총 선행일수"를 투명하게 제공한다.
        "calibration": _calibration_summary(claimed_lead_days, cases),
        "note": None if cases else "비교 가능한 실측 타임라인 사례 없음(공식선언 마일스톤 미기록 등)",
    }


def _calibration_summary(claimed_lead_days: int, cases: list[dict]) -> dict:
    """추정 총 선행일수(하드코딩) vs 실측 총 선행일수(사례 평균/중앙값).
    실측 없으면 calibrated=False로 정직하게 표기하고 추정치를 그대로 둔다."""
    if not cases:
        return {
            "estimated_max_lead_days": claimed_lead_days,
            "observed_mean_lead_days": None,
            "observed_median_lead_days": None,
            "sample_size": 0,
            "calibrated": False,
            "recommendation": "실측 사례 없음 — 추정치 유지(표본 쌓이면 자동 캘리브레이션)",
        }
    import statistics as _st
    observed = [c["observed_lead_days"] for c in cases]
    mean_obs = round(_st.mean(observed), 1)
    median_obs = round(_st.median(observed), 1)
    return {
        "estimated_max_lead_days": claimed_lead_days,
        "observed_mean_lead_days": mean_obs,
        "observed_median_lead_days": median_obs,
        "sample_size": len(observed),
        "calibrated": True,
        "recommendation": (
            f"실측 {len(observed)}건 기준 총 선행일수 평균 {mean_obs}일"
            f"(추정치 {claimed_lead_days}일). 표본이 작을수록 보수적으로 인용할 것."
        ),
    }

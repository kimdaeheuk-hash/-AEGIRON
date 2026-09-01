"""대응제 개발 파이프라인 — "없다" 가 다 같은 없음이 아니다 (2026-09-01).

## 왜 만들었나

캡틴: *"발할라를 대규모 업데이트로 가야겠군! 정보가 너무 없어! 국가 바이오
안보 분야로 진입을 해야 국가사업을 할 수 있어!"*

맞는 지적이었다. 앞서 만든 비축 격차(`countermeasure_stockpile`)는 **있다/없다
두 칸**뿐이었다. 그런데 "없다" 안에 전혀 다른 상태가 섞여 있다:

    마버그   3상 진행 중 — 몇 년 안에 나올 수 있다
    니파     임상 단계 표기도 없다 — 아직 멀다

이 둘을 같은 "비축 없음" 으로 묶으면 **대비 우선순위를 정할 수 없다.**
국가 바이오안보 기획에서 필요한 것은 정확히 그 구분이다.

## 데이터 — ClinicalTrials.gov API v2

미국 NIH 가 운영하는 세계 최대 임상시험 등록부다. **무료·키 불필요**를 실측
확인했다(2026-09-01). 병원체 이름으로 물으면 연구 수와 임상 단계가 나온다.

    에볼라   81건 · PHASE3 COMPLETED
    마버그    9건 · PHASE2 ACTIVE
    MERS     6건 · PHASE1/2 COMPLETED
    라싸열    4건 · PHASE1 ACTIVE
    니파      5건 · 단계 미표기

## ★ 임상시험 수는 준비도가 아니다 ★

이 파일이 가장 조심하는 지점이다. 연구가 81건이라고 그 병에 잘 대비돼 있다는
뜻이 아니다:

- 연구 수는 **관심의 양**이지 **물량**이 아니다. 3상을 통과해도 생산·비축은
  전혀 다른 문제다.
- 등록부에 없다고 개발이 없는 것도 아니다. 군사·기밀 프로그램은 여기 안 올라온다.
- 단계는 그 병원체 전체가 아니라 **그 시험 하나**의 단계다.

그래서 이 층은 **"어디까지 와 있나"** 만 말하고 준비도 점수를 내지 않는다.
비축 유무(`countermeasure_stockpile`)와 합쳐서 읽어야 뜻이 생긴다.
"""
from __future__ import annotations

import requests

CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT = 40

# 임상 단계를 순서로 본다. 값이 클수록 시장에 가깝다.
# ★ 이건 순서이지 점수가 아니다 ★ PHASE3 이 PHASE1 의 세 배 좋다는 뜻이 아니다.
_PHASE_RANK = {
    "EARLY_PHASE1": 1, "PHASE1": 2, "PHASE1/PHASE2": 2,
    "PHASE2": 3, "PHASE2/PHASE3": 4, "PHASE3": 5, "PHASE4": 6,
}
_PHASE_KO = {
    0: "임상 단계 미표기", 1: "초기 1상", 2: "1상", 3: "2상",
    4: "2/3상", 5: "3상", 6: "4상(시판 후)",
}

# 아이기론이 신호를 잡는 위협 → ClinicalTrials.gov 검색어.
# ★ 우리 표기가 아니라 그쪽 표기로 물어야 한다 ★ "엠폭스" 로 물으면 안 나온다.
PATHOGEN_QUERIES: dict[str, str] = {
    "에볼라": "Ebola", "마버그": "Marburg", "라싸열": "Lassa Fever",
    "니파": "Nipah Virus", "MERS": "MERS-CoV", "엠폭스": "Mpox",
    "콜레라": "Cholera", "황열": "Yellow Fever", "수막구균 수막염": "Meningococcal",
    "뎅기열": "Dengue", "지카": "Zika", "치쿤구니야": "Chikungunya",
    "말라리아": "Malaria", "홍역": "Measles", "탄저": "Anthrax",
    "한타바이러스": "Hantavirus",
    "인플루엔자(조류·계절)": "Avian Influenza",
}


def _phase_rank(phases: list[str]) -> int:
    return max((_PHASE_RANK.get(p, 0) for p in phases), default=0)


def fetch_pipeline(query: str, timeout: int = TIMEOUT) -> dict:
    """한 병원체의 대응제 임상 현황. 실패하면 **사유를 들고 온다.**"""
    try:
        resp = requests.get(
            CTGOV_URL,
            params={
                "query.cond": query,
                "query.intr": "vaccine OR antiviral OR monoclonal antibody",
                "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED",
                "pageSize": 100, "countTotal": "true",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        body = resp.json() or {}
    except Exception as exc:                      # noqa: BLE001
        return {"available": False, "query": query,
                "reason": f"조회 실패: {type(exc).__name__}"}

    studies = body.get("studies") or []
    total = body.get("totalCount")
    if total is None:
        return {"available": False, "query": query,
                "reason": "응답에 totalCount 가 없음(형식 변경 의심)"}
    if total == 0:
        # ★ 0건은 '개발이 없다' 가 아니다 ★ 등록부에 없을 뿐이다.
        return {
            "available": True, "query": query, "study_count": 0,
            "furthest_phase": None, "furthest_phase_ko": None,
            "note": "등록된 연구가 없다. 개발이 없다는 뜻이 아니라 이 등록부에 "
                    "없다는 뜻이다 — 군사·기밀 프로그램은 등재되지 않는다.",
        }

    best_rank, best_title, completed_late = 0, None, 0
    for study in studies:
        section = study.get("protocolSection") or {}
        phases = (section.get("designModule") or {}).get("phases") or []
        rank = _phase_rank(phases)
        status = (section.get("statusModule") or {}).get("overallStatus")
        if rank >= 5 and status == "COMPLETED":
            completed_late += 1
        if rank > best_rank:
            best_rank = rank
            best_title = ((section.get("identificationModule") or {})
                          .get("briefTitle") or None)

    return {
        "available": True,
        "query": query,
        "study_count": total,
        "studies_examined": len(studies),
        "furthest_phase": best_rank or None,
        "furthest_phase_ko": _PHASE_KO.get(best_rank),
        "completed_late_phase": completed_late,
        "example_title": best_title,
        "source": "ClinicalTrials.gov API v2 (미국 NIH)",
    }


def readiness_stage(pipeline: dict, has_stockpile: bool) -> dict:
    """비축 유무 + 임상 단계 → 대비 단계. **점수를 내지 않는다.**

    다섯 칸으로만 나눈다. 숫자를 매기면 "니파 32점" 같은 것이 문서에 실리고,
    그 32 를 설명할 근거가 우리에겐 없다.
    """
    if has_stockpile:
        return {"stage": "stockpiled", "stage_ko": "국제 비상 비축 있음",
                "meaning": "발병 시 즉시 요청할 물량이 있다. 충분하다는 뜻은 아니다."}
    if not pipeline.get("available"):
        return {"stage": "unknown", "stage_ko": "판정 불가",
                "meaning": pipeline.get("reason") or "임상 현황을 확인하지 못했다."}

    phase = pipeline.get("furthest_phase") or 0
    if pipeline.get("completed_late_phase"):
        return {"stage": "approved_path", "stage_ko": "후기 임상 완료",
                "meaning": "3상 이상을 마친 연구가 있다. 비축은 없으므로 "
                           "발병 시 조달·생산 협상부터 시작해야 한다."}
    if phase >= 4:
        return {"stage": "late_trial", "stage_ko": "후기 임상 진행 중",
                "meaning": "몇 년 안에 쓸 수 있게 될 여지가 있다."}
    if phase >= 2:
        return {"stage": "early_trial", "stage_ko": "초기 임상",
                "meaning": "실용화까지 상당한 시간이 필요하다."}
    if pipeline.get("study_count"):
        return {"stage": "research_only", "stage_ko": "연구 단계",
                "meaning": "등록된 연구는 있으나 임상 단계 표기가 없다."}
    return {"stage": "no_registered_trial", "stage_ko": "등록 연구 없음",
            "meaning": "이 등록부에 연구가 없다. 개발이 없다는 뜻은 아니다."}

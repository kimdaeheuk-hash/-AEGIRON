"""반증 질문 생성 — "이 판정을 뒤집으려면 어떤 증거?" (2026-11-03).

헤임달 방어 생성 로드맵 3번. 규칙 기반·결정적 — LLM이 아니라 원장 데이터를
읽어, 판정을 바꿀 수 있는 증거를 질문으로 만든다. HUGINN 수집 지시로 닫는
루프의 입력(수집 지시 자동 발행은 다음 단계 — 여기서는 질문 목록까지).

판정별 질문:
- gap: 어떤 대응제가 등록되면 covered가 되는가(필요 효능 명시)
- unknown: 어떤 효능 자료가 오면 판정이 서는가(후보 나열)
- recheck: 변이 전이 후 효능 재측정 시 holds 복귀
- holds: 어떤 변이 출현 시 재확인이 걸리는가(연결 빌드 명시)
- 변이 미연결: 감시 연결 시 판정 강화
"""
from __future__ import annotations

import json

import db
from .biodefense_readiness import COVERAGE_MIN_EFFICACY, compute_readiness
from .match_ledger import THREAT_BUILD_MAP, list_verdicts


def _latest_verdict(pathogen: str) -> dict | None:
    rows = list_verdicts(days=30, pathogen=pathogen, limit=1)
    return rows[0] if rows else None


def questions_for_threat(pathogen: str) -> dict:
    """위협 1개의 반증 질문 목록. 실데이터 없으면 사유와 함께 모름."""
    stored = db.list_countermeasures()
    if not stored:
        return {"pathogen": pathogen, "assessed": False,
                "reason": "등록된 비축 없음"}
    res = compute_readiness(stored, [{"pathogen": pathogen}])
    row = res["matrix"][0]
    status = row["coverage_status"]
    verdict_row = _latest_verdict(pathogen)
    verdict = verdict_row["verdict"] if verdict_row else None
    build = THREAT_BUILD_MAP.get((pathogen or "").strip().lower())

    questions: list[dict] = []
    if status == "uncovered":
        questions.append({
            "question": f"{pathogen}을 표적으로 하는 대응제가 등록되면 판정이 바뀐다",
            "flips_to": "covered",
            "evidence_needed": f"targets에 {pathogen} 포함 + 선언 효능 "
                               f"{COVERAGE_MIN_EFFICACY} 이상",
            "source_hint": "비축 등록(/api/biodefense/stockpile)",
        })
    elif status == "unrated":
        cands = row.get("unrated_countermeasures", [])
        questions.append({
            "question": f"효능 미기재 {len(cands)}건의 선언 효능이 입수되면 판정이 선다",
            "flips_to": "covered 또는 gap(효능값에 따라)",
            "evidence_needed": "대응제별 선언 효능(라벨/문헌): " + ", ".join(cands[:5]),
            "source_hint": "라벨·문헌 효능 기재",
        })
    if verdict == "recheck" and verdict_row:
        flag = {}
        try:
            flag = json.loads(verdict_row.get("variant_flag") or "{}")
        except ValueError:
            pass
        questions.append({
            "question": "변이 전이 후 선언 효능이 재확인되면 holds로 복귀한다",
            "flips_to": "holds",
            "evidence_needed": (f"{flag.get('transition')}({flag.get('observed_at', '?')[:10]}) "
                                f"이후 효능 재측정 자료"),
            "source_hint": "변이원장 전이 추적 + 효능 문헌",
        })
    if status == "covered" and build:
        questions.append({
            "question": f"{build} 빌드에 신규 계통·우세 변경이 오면 재확인이 걸린다",
            "flips_to": "recheck(자동)",
            "evidence_needed": "변이원장 전이 기록(수집 주기마다 자동 대조)",
            "source_hint": "변이원장",
        })
    if status == "covered" and not build:
        questions.append({
            "question": "변이 감시가 연결되면 효능 전제까지 감시된다",
            "flips_to": "감시 강화(판정 변경 아님)",
            "evidence_needed": f"{pathogen} 대응 변이 빌드 편입",
            "source_hint": "Nextstrain 빌드 추가",
        })
    return {"pathogen": pathogen, "assessed": True,
            "coverage_status": status, "latest_match_verdict": verdict,
            "questions": questions,
            "loop_note": "수집 지시 자동 발행은 다음 단계 — 여기서는 질문 목록까지."}

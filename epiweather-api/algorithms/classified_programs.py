"""사내 프로그램 거버넌스 — Stage 0/8을 '사내 최고 보안등급 프로그램'으로 관리.

Stage 0(설계-탐지 이중성 유전체 스크리닝)과 Stage 8(대응제 준비태세)은 일반
감시 층과 성격이 다르다 — 민감도가 높아 담당 조직·프로그램 코드명·보안등급을
명시적으로 분리한다. 이 모듈은 그 거버넌스 메타데이터를 한 곳에서 관리하고,
각 사내 제한 엔드포인트 응답에 부착한다.

주의: 프로그램명·조직명·등급은 전부 아이기론(AEGIRON) 자체 내부 구조 정의이며,
실제 정부기관 소속이나 공식 기밀등급이 아니다(사업자등록·정부협약 이전 단계).
보안등급은 라벨만이 아니라 실제 접근통제(인증 필수)와 함께 강제한다.
"""
from __future__ import annotations

# 아이기론 기밀 프로그램 레지스트리.
CLASSIFIED_PROGRAMS = {
    "stage0": {
        "program_code": "HEIMDALL",
        "program_name_ko": "헤임달",
        "stage": 0,
        "mission_ko": "생물학적 위협 유전체 스크리닝 — 설계-탐지 이중성 기반 인공설계 신호 탐지",
        "owning_center_ko": "아이기론 R&D 연구센터",
        "owning_unit_ko": "생물안보연구실",
        "owning_center_en": "AEGIRON R&D Center · Biosecurity Lab",
        "designation_ko": "사내 R&D 프로그램",
        "classification": "AEGIRON-RESTRICTED",
        "classification_ko": "사내 최고 보안등급",
    },
    "stage8": {
        "program_code": "VALHALLA",
        "program_name_ko": "발할라",
        "stage": 8,
        "mission_ko": "대응제 준비태세 — 비축 커버리지·생산 주권·회복력 격차 정량화",
        "owning_center_ko": "아이기론 R&D 연구센터",
        "owning_unit_ko": "대응제연구실",
        "owning_center_en": "AEGIRON R&D Center · Countermeasures Lab",
        "designation_ko": "사내 R&D 프로그램",
        "classification": "AEGIRON-RESTRICTED",
        "classification_ko": "사내 최고 보안등급",
    },
}

_ACCESS_NOTE_KO = (
    "본 프로그램은 사내 최고 보안등급으로, 인증(API 키) 필수·모든 접근이 "
    "감사로그(api_key_usage) 대상이다. 결과의 대외 공개·재배포는 담당 부서 승인 필요."
)


def classification(key: str) -> dict:
    """기밀 프로그램 메타데이터 + 접근·감사 고지. 알 수 없는 키면 빈 dict."""
    prog = CLASSIFIED_PROGRAMS.get(key)
    if not prog:
        return {}
    return {
        **prog,
        "is_classified": True,
        "access_control": "auth_required",
        "audit_logged": True,
        "access_note": _ACCESS_NOTE_KO,
    }

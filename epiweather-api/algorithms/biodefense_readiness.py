"""Stage 8 대응제 준비태세 — '가짜 분자 중화 예측' 대신 '실제 커버리지·주권 격차 정량화'.

배경: 기존 Stage 8은 "병원체 유전체 → 미래 변이 → 비축 대응제 중화"를 결정론적
장난감 수식으로 흉내냈다. 진짜 분자 수준 중화 예측은 구조·면역 모델링(BioNeMo·
에피톱 데이터)이 있어야 하고, 그걸 파이썬 수식으로 지어내면 '가짜 정밀도'라 오히려
신뢰를 잃는다.

그래서 이 모듈은 팔 수 없는 것을 흉내내지 않고, 실제로 방어 가능한 것을 계산한다:
국가 바이오안보 기획의 핵심 질문 — **"어떤 위협을 우리 비축이 못 막는가(coverage
gap), 그리고 막는 것 중 국산 생산이 안 되는 게 뭔가(생산 주권 gap)"**.

정직성:
- 효능은 '예측'이 아니라 각 대응제의 '선언된(published/라벨) 효능'을 집계한다.
  분자 중화 예측(변이별 escape)은 Phase 2 통합(BioNeMo·CEPI)임을 명시한다.
- 데이터가 없으면 지어내지 않는다 — 커버리지 불명은 covered=False로 보수적 처리.
- '생산 주권' 격차는 한국의 백신·치료제 자립 정책과 직결되는 실제 기획 지표.
"""
from __future__ import annotations

# 커버리지 판정 임계값(선언 효능이 이 이상이어야 '실질 커버'로 봄).
COVERAGE_MIN_EFFICACY = 0.30


def compute_readiness(countermeasures: list[dict], threats: list[dict]) -> dict:
    """대응제(비축) × 위협 커버리지 매트릭스와 격차를 계산.

    countermeasures 항목: {name, type, targets:[pathogen...], declared_efficacy:0~1,
                          domestic_producible: bool}
    threats 항목: {pathogen, severity(0~1, 선택)}
    """
    threat_rows = []
    uncovered = []
    sovereignty_gap = []

    for th in threats:
        pathogen = th.get("pathogen")
        # 이 위협을 표적으로 하고 선언 효능이 임계 이상인 대응제들
        covering = [
            cm for cm in countermeasures
            if pathogen in cm.get("targets", [])
            and (cm.get("declared_efficacy") or 0) >= COVERAGE_MIN_EFFICACY
        ]
        best = max((cm.get("declared_efficacy") or 0) for cm in covering) if covering else 0.0
        domestic = any(cm.get("domestic_producible") for cm in covering)

        row = {
            "pathogen": pathogen,
            "severity": th.get("severity"),
            "covered": bool(covering),
            "best_declared_efficacy": round(best, 3) if covering else None,
            "covering_countermeasures": [cm["name"] for cm in covering],
            "domestic_production": domestic,
        }
        threat_rows.append(row)

        if not covering:
            uncovered.append(pathogen)                  # 아예 못 막는 위협
        elif not domestic:
            sovereignty_gap.append(pathogen)            # 막지만 국산 생산 불가(주권 격차)

    n = len(threats)
    covered_n = sum(1 for r in threat_rows if r["covered"])
    domestic_n = sum(1 for r in threat_rows if r["covered"] and r["domestic_production"])

    return {
        "threats_assessed": n,
        "coverage": {
            "covered": covered_n,
            "uncovered": len(uncovered),
            "coverage_rate": round(covered_n / n, 3) if n else None,
            "uncovered_threats": uncovered,
        },
        "sovereignty": {
            "domestically_covered": domestic_n,
            "import_dependent_covered": len(sovereignty_gap),
            "sovereignty_rate": round(domestic_n / covered_n, 3) if covered_n else None,
            "import_dependent_threats": sovereignty_gap,
        },
        "matrix": threat_rows,
        "method": "declared_efficacy_coverage_v1",
        "coverage_min_efficacy": COVERAGE_MIN_EFFICACY,
        "disclaimer": (
            "효능은 '예측'이 아니라 각 대응제의 선언(라벨/문헌) 효능 집계다. 변이별 분자 "
            "중화 예측(escape)은 구조·면역 모델(BioNeMo·CEPI 표준) 연동이 필요한 Phase 2 "
            "이며, 여기서는 지어내지 않는다. 커버리지 불명은 보수적으로 미커버 처리."
        ),
    }


# 시연용 예시 데이터(실제 비축이 아니라 구조 설명용) — is_illustrative로 명시.
_ILLUSTRATIVE_COUNTERMEASURES = [
    {"name": "타미플루(오셀타미비르) 비축", "type": "antiviral",
     "targets": ["Influenza", "H5N1"], "declared_efficacy": 0.55, "domestic_producible": True},
    {"name": "코로나 mRNA 백신 플랫폼", "type": "vaccine",
     "targets": ["SARS-CoV-2", "Novel"], "declared_efficacy": 0.6, "domestic_producible": True},
    {"name": "수입 단클론항체(에볼라)", "type": "mAb",
     "targets": ["Ebola"], "declared_efficacy": 0.7, "domestic_producible": False},
]
_ILLUSTRATIVE_THREATS = [
    {"pathogen": "H5N1", "severity": 0.8},
    {"pathogen": "SARS-CoV-2", "severity": 0.6},
    {"pathogen": "Ebola", "severity": 0.9},
    {"pathogen": "MERS", "severity": 0.7},        # 비축 없음 → 미커버
]


def illustrative_readiness() -> dict:
    """입력 없이 구조를 보여주는 시연용. is_illustrative=True로 실제 비축이 아님을 명시."""
    result = compute_readiness(_ILLUSTRATIVE_COUNTERMEASURES, _ILLUSTRATIVE_THREATS)
    result["is_illustrative"] = True
    result["note"] = "예시 데이터입니다. 실제 운영 시 국가 비축 목록·선언 효능을 입력하세요."
    return result

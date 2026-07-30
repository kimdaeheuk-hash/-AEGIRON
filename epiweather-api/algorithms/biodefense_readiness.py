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

# 기본 감시 위협목록 — severity는 WHO 실측 치명률(CFR, 확인일 2026-07-30).
# Novel은 정의상 과거 발병 데이터가 없어 severity를 비워둠(지어내지 않음).
DEFAULT_THREATS = [
    {"pathogen": "H5N1", "severity": 0.48},     # WHO/CDC 1997~2025 누적 993례/477사망
    {"pathogen": "Ebola", "severity": 0.50},    # WHO 팩트시트, 역대 평균(25~90% 범위)
    {"pathogen": "MERS", "severity": 0.361},    # WHO 2012~2025.5 누적 2,626례/947사망
    {"pathogen": "Dengue", "severity": 0.0004}, # WHO 연간 약 5천만 감염/2.2만 사망(경증 포함 전체 평균)
    {"pathogen": "Novel"},                      # 정의상 과거 CFR 없음 — severity 비움
]


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

    # severity 가중 지표 — severity 미입력 위협은 중립값 0.5로 처리(있는 것만
    # 우대·없는 것만 불이익 주지 않기 위함). 정렬용으로만 -1(맨 뒤)을 따로 씀.
    def _weighted_rate(rows: list[dict], predicate) -> float | None:
        total = sum((r["severity"] if r["severity"] is not None else 0.5) for r in rows)
        if total == 0:
            return None
        covered_weight = sum(
            (r["severity"] if r["severity"] is not None else 0.5) for r in rows if predicate(r)
        )
        return round(covered_weight / total, 3)

    severity_weighted_coverage_rate = _weighted_rate(threat_rows, lambda r: r["covered"])

    uncovered_rows = [r for r in threat_rows if not r["covered"]]
    priority_uncovered = sorted(
        uncovered_rows, key=lambda r: r["severity"] if r["severity"] is not None else -1, reverse=True,
    )

    covered_rows = [r for r in threat_rows if r["covered"]]
    severity_weighted_sovereignty_rate = (
        _weighted_rate(covered_rows, lambda r: r["domestic_production"]) if covered_rows else None
    )
    import_dependent_rows = [r for r in covered_rows if not r["domestic_production"]]
    priority_import_dependent = sorted(
        import_dependent_rows, key=lambda r: r["severity"] if r["severity"] is not None else -1, reverse=True,
    )

    return {
        "threats_assessed": n,
        "resilience": _resilience_analysis(countermeasures, threats),
        "logistics": _stockpile_logistics(countermeasures, threats),
        "coverage": {
            "covered": covered_n,
            "uncovered": len(uncovered),
            "coverage_rate": round(covered_n / n, 3) if n else None,
            "uncovered_threats": uncovered,
            "severity_weighted_rate": severity_weighted_coverage_rate,
            "priority_uncovered_threats": [
                {"pathogen": r["pathogen"], "severity": r["severity"]} for r in priority_uncovered
            ],
        },
        "sovereignty": {
            "domestically_covered": domestic_n,
            "import_dependent_covered": len(sovereignty_gap),
            "sovereignty_rate": round(domestic_n / covered_n, 3) if covered_n else None,
            "import_dependent_threats": sovereignty_gap,
            "severity_weighted_sovereignty_rate": severity_weighted_sovereignty_rate,
            "priority_import_dependent_threats": [
                {"pathogen": r["pathogen"], "severity": r["severity"]} for r in priority_import_dependent
            ],
        },
        "matrix": threat_rows,
        "method": "declared_efficacy_coverage_v1",
        "coverage_min_efficacy": COVERAGE_MIN_EFFICACY,
        "disclaimer": (
            "효능은 '예측'이 아니라 각 대응제의 선언(라벨/문헌) 효능 집계다. 변이별 분자 "
            "중화 예측(escape)은 구조·면역 모델(BioNeMo·CEPI 표준) 연동이 필요한 Phase 2 "
            "이며, 여기서는 지어내지 않는다. 커버리지 불명은 보수적으로 미커버 처리. "
            "severity_weighted 지표는 severity 미입력 위협을 중립값(0.5)으로 처리한다."
        ),
    }


def _resilience_analysis(countermeasures: list[dict], threats: list[dict]) -> dict:
    """새 각도: 커버리지'만'으론 안 보이는 취약성 — 대응제가 딱 하나뿐인 위협(단일
    故障점)과, 커버되지만 전부 수입에만 의존하는 위협을 잡는다."""
    single_point = []
    import_only = []
    for th in threats:
        pathogen = th.get("pathogen")
        covering = [cm for cm in countermeasures
                    if pathogen in cm.get("targets", [])
                    and (cm.get("declared_efficacy") or 0) >= COVERAGE_MIN_EFFICACY]
        if len(covering) == 1:
            single_point.append(pathogen)                       # 대응제 1개뿐 → 취약
        if covering and not any(cm.get("domestic_producible") for cm in covering):
            import_only.append(pathogen)                        # 전부 수입 의존
    return {
        "single_point_of_failure": single_point,
        "single_point_count": len(single_point),
        "import_only_covered": import_only,
        "note": "대응제가 하나뿐인 위협은 그 하나가 실패(내성·escape·공급중단)하면 즉시 무방비.",
    }


def _stockpile_logistics(countermeasures: list[dict], threats: list[dict]) -> dict:
    """새 각도: 비축 소진일수 — courses(비축 인분)와 예상 수요로 '며칠 버티나' 계산.
    courses/population/attack_rate가 있는 대응제만 계산(없으면 지어내지 않고 skip)."""
    rows = []
    for cm in countermeasures:
        courses = cm.get("courses")
        if courses is None:
            continue
        pop = cm.get("population")
        attack = cm.get("attack_rate")
        demand = (pop * attack) if (pop and attack) else None
        rows.append({
            "name": cm["name"],
            "courses": courses,
            "projected_demand": round(demand) if demand else None,
            "coverage_fraction": round(min(courses / demand, 1.0), 3) if demand else None,
            "shortfall": round(demand - courses) if (demand and demand > courses) else 0,
        })
    return {
        "assessed": len(rows),
        "items": rows,
        "note": "courses(비축 인분)·population·attack_rate가 입력된 대응제만 계산. "
                "없으면 지어내지 않고 제외.",
    }


# 시연용 예시 데이터(실제 비축이 아니라 구조 설명용) — is_illustrative로 명시.
_ILLUSTRATIVE_COUNTERMEASURES = [
    {"name": "타미플루(오셀타미비르) 비축", "type": "antiviral",
     "targets": ["Influenza", "H5N1"], "declared_efficacy": 0.55, "domestic_producible": True,
     "courses": 10_000_000, "population": 51_000_000, "attack_rate": 0.30},
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

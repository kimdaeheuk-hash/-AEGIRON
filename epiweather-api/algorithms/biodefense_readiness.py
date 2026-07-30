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

# EU HERA(2021년 신설)의 3대 위협군 분류 체계 참고(확인일 2026-07-30) —
# 16개 회원국 22개 rescEU 비축소가 이 3개 군으로 나눠 관리됨. AMR·CBRN은
# 이 시스템이 아직 추적하는 대응제·위협이 하나도 없어 tracked=False로
# 정직하게 표시한다(가짜 위협 항목을 만들어 채우지 않음).
HERA_CATEGORIES = {
    "pandemic_pathogen": {"name_ko": "팬데믹 잠재력 병원체", "tracked": True},
    "amr": {"name_ko": "항생제 내성(AMR)", "tracked": False},
    "cbrn": {"name_ko": "화생방핵(CBRN)", "tracked": False},
}

# 기본 감시 위협목록 — severity는 WHO/CDC 실측 치명률(CFR, 확인일 2026-07-30).
# Novel은 정의상 과거 발병 데이터가 없어 severity를 비워둠(지어내지 않음).
#
# pathogen_domain은 유전체 파운데이션 모델(Evo2)의 적용범위 판정용 분류군이다
# (algorithms.evo2_naturalness.APPLICABILITY와 같은 값 체계). Evo2는 진핵숙주
# 감염 바이러스를 학습에서 제외해서, 바이러스 위협은 유전체 스크리닝으로 판정할
# 수 없고 세균 위협은 가능하다 — 이 차이가 실제 탐지역량 격차라 명시적으로 든다.
DEFAULT_THREATS = [
    {"pathogen": "H5N1", "severity": 0.48, "category": "pandemic_pathogen",
     "pathogen_domain": "eukaryotic_virus"},    # WHO/CDC 1997~2025 누적 993례/477사망
    {"pathogen": "Ebola", "severity": 0.50, "category": "pandemic_pathogen",
     "pathogen_domain": "eukaryotic_virus"},    # WHO 팩트시트, 역대 평균(25~90% 범위)
    {"pathogen": "MERS", "severity": 0.361, "category": "pandemic_pathogen",
     "pathogen_domain": "eukaryotic_virus"},    # WHO 2012~2025.5 누적 2,626례/947사망
    {"pathogen": "Dengue", "severity": 0.0004, "category": "pandemic_pathogen",
     "pathogen_domain": "eukaryotic_virus"},    # WHO 연간 약 5천만 감염/2.2만 사망(경증 포함 전체 평균)
    {"pathogen": "Novel", "category": "pandemic_pathogen"},                      # 정의상 과거 CFR 없음 — severity 비움
    # 세균 위협(CDC Category A 생물테러 인자) — HERA의 CBRN 군. 유전체 스크리닝
    # 적용범위 안이라 Evo2 기반 Stage 0 판정이 실제로 작동하는 위협들이다.
    {"pathogen": "Anthrax", "severity": 0.45, "category": "cbrn",
     "pathogen_domain": "bacteria_archaea"},    # CDC: 2001 미국 우편물 공격 흡입탄저 11례/5사망 — 치료에도 45%
    {"pathogen": "Plague", "severity": 0.65, "category": "cbrn",
     "pathogen_domain": "bacteria_archaea"},    # WHO 팩트시트 미치료 30~100%(가래톳 30~60%, 폐페스트 사실상 100%)의 중간값
    {"pathogen": "Tularemia", "severity": 0.45, "category": "cbrn",
     "pathogen_domain": "bacteria_archaea"},    # CDC/문헌: 미치료 폐·티푸스형 30~60%의 중간값(치료 시 약 2%)
]

# 유전체 스크리닝(Stage 0, Evo2 기반) 적용범위별 실측 기준선 — 근거는
# algorithms.evo2_naturalness 모듈 docstring의 분류군별 실측(2026-07-30).
_SCREENING_DOMAIN_NOTE = {
    "bacteria_archaea": "세균·고균 — Evo2 적용범위 안(대장균 자연서열 실측 87.5%). 판정 가능.",
    "eukaryote": "진핵 유전체 — Evo2 적용범위 안(효모 90.3%·인간 mtDNA 91.7% 실측). 판정 가능.",
    "phage": "세균 감염 바이러스 — Evo2 적용범위 안(람다파지 100% 실측). 판정 가능.",
    "eukaryotic_virus": "진핵숙주 감염 바이러스 — Evo2 학습에서 제외되어 자연서열도 30%대. "
                        "유전체 스크리닝으로 인공 여부 판정 불가.",
}


def genomic_screening_capability(threats: list[dict]) -> dict:
    """새 각도: 대응제 커버리지와 별개로 **'우리 유전체 스크리닝이 이 위협을 애초에
    판정할 수 있는가'** 를 위협별로 집계한다(탐지역량 격차).

    Stage 0의 Evo2 기반 스크리닝은 진핵숙주 감염 바이러스에 대해 원리적으로
    작동하지 않는다(Arc가 바이오안보 목적으로 학습에서 제외 — evo2_naturalness의
    분류군별 실측 참조). 그 한계를 화면 문구로만 얼버무리지 않고 위협별로 계산해
    노출한다: 막을 수 있느냐(커버리지)와 별개로 '알아볼 수 있느냐'가 방어의 전제다.

    pathogen_domain 미선언 위협은 판정 가능으로 세지 않는다(보수적 처리)."""
    assessable, not_assessable, undeclared = [], [], []
    for th in threats:
        pathogen = th.get("pathogen")
        domain = th.get("pathogen_domain")
        if not domain:
            undeclared.append(pathogen)
        elif domain == "eukaryotic_virus":
            not_assessable.append({"pathogen": pathogen, "pathogen_domain": domain,
                                   "reason": _SCREENING_DOMAIN_NOTE[domain]})
        elif domain in _SCREENING_DOMAIN_NOTE:
            assessable.append({"pathogen": pathogen, "pathogen_domain": domain,
                               "note": _SCREENING_DOMAIN_NOTE[domain]})
        else:
            undeclared.append(pathogen)     # 미지원 값도 보수적으로 미판정 처리

    n = len(threats)
    return {
        "threats_assessed": n,
        "genomically_assessable": len(assessable),
        "assessable_rate": round(len(assessable) / n, 3) if n else None,
        "assessable_threats": assessable,
        "not_assessable_threats": not_assessable,
        "undeclared_domain_threats": undeclared,
        "basis": "evo2_naturalness 분류군별 실측(2026-07-30, evo2-40b NIM, NCBI 레퍼런스 자연서열)",
        "note": (
            "대응제 커버리지와 다른 축이다 — '막을 수 있는가'가 아니라 '유전체로 "
            "알아볼 수 있는가'. 판정 불가 위협은 유전체 스크리닝 외의 경로(역학·임상·"
            "인텔 신호)에 의존해야 한다는 뜻이며, 이 시스템의 실제 탐지 사각지대다."
        ),
    }


def threat_category_coverage(threats: list[dict]) -> dict:
    """EU HERA 3대 위협군 기준으로 지금 뭘 추적 중이고 뭘 아예 안 보고 있는지
    요약. AMR·CBRN은 실제로 추적하는 항목이 없으므로 threats_assessed=0,
    tracked=False로 정직하게 노출(HERA_CATEGORIES와 별개로 실제 입력값 기준)."""
    counts: dict[str, int] = {cat: 0 for cat in HERA_CATEGORIES}
    for th in threats:
        cat = th.get("category")
        if cat in counts:
            counts[cat] += 1
    return {
        "framework": "EU HERA 3대 위협군 기준(2026-07-30 확인)",
        "categories": [
            {
                "category": cat,
                "name_ko": meta["name_ko"],
                "tracked": counts[cat] > 0,
                "threats_assessed": counts[cat],
            }
            for cat, meta in HERA_CATEGORIES.items()
        ],
    }


# 통계청 2025년 추계인구(확인일 2026-07-30). 각국 팬데믹계획(일본 등)에서
# 공통적으로 쓰이는 항바이러스제 인구비축 국제 권고치(WHO 팬데믹 대비 지침 기반).
KOREA_POPULATION_2025 = 51_684_564
INTL_ANTIVIRAL_TARGET_PCT = 0.25


def international_benchmark(countermeasures: list[dict], population: int = KOREA_POPULATION_2025) -> dict:
    """국제 팬데믹 대비계획 공통 권고치(항바이러스제 인구 25% 비축)와 실제
    등록된 항바이러스제 비축량을 비교. courses가 있는 antiviral만 집계 —
    없으면 지어내지 않고 assessed=False. 백신·PPE 등 다른 유형엔 이 25%
    기준 자체가 적용되지 않으므로 포함하지 않는다."""
    antivirals = [cm for cm in countermeasures if cm.get("type") == "antiviral" and cm.get("courses")]
    if not antivirals:
        return {
            "assessed": False,
            "reason": "courses(비축 인분)가 입력된 항바이러스제 없음",
        }
    total_courses = sum(cm["courses"] for cm in antivirals)
    coverage_pct = round(total_courses / population, 4)
    return {
        "assessed": True,
        "population": population,
        "population_source": "통계청 2025년 추계인구(2026-07-30 확인)",
        "total_antiviral_courses": total_courses,
        "population_coverage_pct": coverage_pct,
        "international_target_pct": INTL_ANTIVIRAL_TARGET_PCT,
        "meets_target": coverage_pct >= INTL_ANTIVIRAL_TARGET_PCT,
        "note": "각국 팬데믹 대비계획에서 공통적으로 쓰이는 인구 25% 항바이러스제 "
                "비축 권고치와 비교. 백신·PPE 등 다른 대응제 유형엔 이 기준이 적용되지 않음.",
    }


# 해외 체계 요약(정적 참고자료, 계산값 아님 — 확인일 2026-07-30).
REFERENCE_SYSTEMS = [
    {
        "region": "EU", "name": "HERA + rescEU", "established": 2021,
        "summary": "16개 회원국에 22개 rescEU 비축소(17개 가동) 운영. 팬데믹 잠재력 "
                   "병원체·항생제내성(AMR)·화생방핵(CBRN) 3대 위협군으로 분류해 공동조달·비축.",
        "source": "EU HERA 공식 발표",
    },
    {
        "region": "US", "name": "SNS(전략적 국가비축) + BARDA", "established": None,
        "summary": "대규모 연방 비축(Strategic National Stockpile), Project BioShield로 "
                   "조달·개발. 공개된 통합 커버리지 대시보드는 확인 안 됨.",
        "source": "ASPR/BARDA 공식자료",
    },
    {
        "region": "Japan", "name": "신종인플루엔자 등 대책 특별조치법", "established": 2012,
        "summary": "팬데믹 대비를 전담 법률로 명문화. 항바이러스제 인구 25% 비축 등 "
                   "국제 공통 권고치의 근거가 되는 체계.",
        "source": "일본 후생노동성",
    },
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
        "threat_category_coverage": threat_category_coverage(threats),
        "genomic_screening_capability": genomic_screening_capability(threats),
        "international_benchmark": international_benchmark(countermeasures),
        "international_reference_systems": REFERENCE_SYSTEMS,
        "disclaimer": (
            "효능은 '예측'이 아니라 각 대응제의 선언(라벨/문헌) 효능 집계다. 변이별 분자 "
            "중화 예측(escape)은 구조·면역 모델(BioNeMo·CEPI 표준) 연동이 필요한 Phase 2 "
            "이며, 여기서는 지어내지 않는다. 커버리지 불명은 보수적으로 미커버 처리. "
            "severity_weighted 지표는 severity 미입력 위협을 중립값(0.5)으로 처리한다. "
            "유전체 파운데이션 모델(Evo2)로 병원체 변이를 예측하는 경로는 진핵숙주 감염 "
            "바이러스에 대해 실측상 작동하지 않는다(학습 제외) — genomic_screening_capability "
            "참조. 세균 위협에는 적용 가능하므로 그 범위를 위협별로 명시한다."
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

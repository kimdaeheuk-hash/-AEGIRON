"""Stage 8 대응제 준비태세 — 커버리지·주권 격차를 실제로 집계하는지, 데이터 없으면
보수적으로(미커버) 처리하는지, 분자 예측을 지어내지 않는지 확인."""
from __future__ import annotations

from algorithms import biodefense_readiness as br


_CM = [
    {"name": "국산 항바이러스", "type": "antiviral", "targets": ["H5N1"],
     "declared_efficacy": 0.5, "domestic_producible": True},
    {"name": "수입 항체", "type": "mAb", "targets": ["Ebola"],
     "declared_efficacy": 0.7, "domestic_producible": False},
    {"name": "저효능 후보", "type": "antiviral", "targets": ["MERS"],
     "declared_efficacy": 0.1, "domestic_producible": True},  # 임계 미만 → 미커버
]
_THREATS = [
    {"pathogen": "H5N1"}, {"pathogen": "Ebola"},
    {"pathogen": "MERS"}, {"pathogen": "SARS-CoV-2"},  # 비축 없음
]


def test_coverage_counts_and_uncovered():
    r = br.compute_readiness(_CM, _THREATS)
    assert r["threats_assessed"] == 4
    assert r["coverage"]["covered"] == 2                 # H5N1, Ebola
    # MERS는 효능 0.1<0.3이라 미커버, SARS-CoV-2는 비축 없음
    assert set(r["coverage"]["uncovered_threats"]) == {"MERS", "SARS-CoV-2"}


def test_sovereignty_gap_flags_import_dependent():
    """막긴 하지만 국산 생산 불가한 위협(에볼라=수입항체)을 주권 격차로 잡는다."""
    r = br.compute_readiness(_CM, _THREATS)
    assert r["sovereignty"]["import_dependent_threats"] == ["Ebola"]
    assert r["sovereignty"]["domestically_covered"] == 1   # H5N1만 국산 커버


def test_low_efficacy_treated_as_uncovered_not_fabricated():
    r = br.compute_readiness(_CM, [{"pathogen": "MERS"}])
    assert r["coverage"]["covered"] == 0                  # 0.1<임계 → 보수적 미커버


def test_disclaimer_flags_molecular_prediction_as_phase2():
    r = br.compute_readiness(_CM, _THREATS)
    assert "Phase 2" in r["disclaimer"]
    assert "escape" in r["disclaimer"]


def test_illustrative_is_flagged():
    r = br.illustrative_readiness()
    assert r["is_illustrative"] is True
    assert r["coverage"]["coverage_rate"] is not None


# ── 새 각도: 회복력(단일故障점) + 물류(소진일수) ─────────────────
def test_resilience_flags_single_point_of_failure():
    """대응제가 딱 하나뿐인 위협은 단일故障점 — 커버리지만으론 안 보이는 취약성."""
    r = br.compute_readiness(_CM, _THREATS)
    res = r["resilience"]
    # H5N1(국산항체 1개), Ebola(수입항체 1개) 각각 대응제 1개뿐
    assert set(res["single_point_of_failure"]) == {"H5N1", "Ebola"}
    assert res["import_only_covered"] == ["Ebola"]


def test_logistics_computes_days_of_supply():
    """비축 인분 vs 예상 수요로 커버 비율·부족분 계산. courses 없으면 제외."""
    cm = [{"name": "타미플루", "type": "antiviral", "targets": ["H5N1"],
           "declared_efficacy": 0.5, "domestic_producible": True,
           "courses": 3_000_000, "population": 10_000_000, "attack_rate": 0.30}]
    r = br.compute_readiness(cm, [{"pathogen": "H5N1"}])
    item = r["logistics"]["items"][0]
    assert item["projected_demand"] == 3_000_000    # 1000만 * 0.3
    assert item["coverage_fraction"] == 1.0          # 300만 비축 = 수요
    assert item["shortfall"] == 0


def test_logistics_skips_when_no_courses():
    r = br.compute_readiness(_CM, _THREATS)   # _CM엔 courses 없음
    assert r["logistics"]["assessed"] == 0     # 지어내지 않고 제외


# ── severity(위협 심각도) 가중치 반영 ─────────────────────────────
_CM_SEV = [
    {"name": "국산 항바이러스", "type": "antiviral", "targets": ["H5N1"],
     "declared_efficacy": 0.5, "domestic_producible": True},
    {"name": "수입 항체", "type": "mAb", "targets": ["Ebola"],
     "declared_efficacy": 0.7, "domestic_producible": False},
]
_THREATS_SEV = [
    {"pathogen": "H5N1", "severity": 0.9},     # 고위험, 커버됨(국산)
    {"pathogen": "Ebola", "severity": 0.3},    # 저위험, 커버됨(수입의존)
    {"pathogen": "MERS", "severity": 0.95},    # 최고위험, 미커버 — 우선순위 1순위여야 함
]


def test_severity_weighted_coverage_rate_computed():
    r = br.compute_readiness(_CM_SEV, _THREATS_SEV)
    # 커버된 severity(0.9+0.3=1.2) / 전체(0.9+0.3+0.95=2.15)
    assert r["coverage"]["severity_weighted_rate"] == round(1.2 / 2.15, 3)


def test_priority_uncovered_threats_sorted_by_severity_desc():
    r = br.compute_readiness(_CM_SEV, _THREATS_SEV)
    priority = r["coverage"]["priority_uncovered_threats"]
    assert priority[0]["pathogen"] == "MERS"   # 가장 위험한 미커버 위협이 1순위


def test_severity_weighted_sovereignty_rate_computed():
    r = br.compute_readiness(_CM_SEV, _THREATS_SEV)
    # 커버된 것 중(H5N1 0.9 국산, Ebola 0.3 수입) → 국산비중 0.9/1.2
    assert r["sovereignty"]["severity_weighted_sovereignty_rate"] == round(0.9 / 1.2, 3)


def test_priority_import_dependent_threats_uses_severity_order():
    r = br.compute_readiness(_CM_SEV, _THREATS_SEV)
    assert r["sovereignty"]["priority_import_dependent_threats"][0]["pathogen"] == "Ebola"


def test_severity_weighted_rate_treats_missing_severity_as_neutral():
    r = br.compute_readiness(_CM, _THREATS)  # 기존 fixture, severity 필드 없음
    assert r["coverage"]["severity_weighted_rate"] is not None


# ── 기본 위협목록(DEFAULT_THREATS) — 실측 WHO 치명률(CFR) 회귀 방지 ────────
def test_default_threats_covers_viral_and_bacterial_pathogens():
    """바이러스 4종 + Novel + 세균 3종(CDC Category A). 세균 위협은 유전체
    스크리닝 적용범위 안이라 실제로 판정 가능한 축을 만든다."""
    pathogens = {t["pathogen"] for t in br.DEFAULT_THREATS}
    assert pathogens == {"H5N1", "Ebola", "MERS", "Dengue", "Novel",
                         "Anthrax", "Plague", "Tularemia"}


def test_default_threats_severity_reflects_real_cfr_ordering():
    """H5N1·Ebola·MERS는 치명률이 높아 Dengue보다 훨씬 심각도가 높아야 함
    (실제 WHO 수치 기반 — 임의 순서 아님)."""
    by_pathogen = {t["pathogen"]: t.get("severity") for t in br.DEFAULT_THREATS}
    assert by_pathogen["H5N1"] > by_pathogen["Dengue"]
    assert by_pathogen["Ebola"] > by_pathogen["Dengue"]
    assert by_pathogen["MERS"] > by_pathogen["Dengue"]
    assert by_pathogen["Novel"] is None  # 정의상 과거 CFR 없음 — 지어내지 않음


def test_default_threats_used_in_readiness_produce_meaningful_priority_order():
    """DEFAULT_THREATS를 실제로 계산에 태우면 우선순위 미커버 목록이 치명률
    순서를 따라야 함(H5N1·Ebola·MERS가 Dengue보다 먼저 나와야 함)."""
    r = br.compute_readiness([], br.DEFAULT_THREATS)  # 대응제 없음 → 전부 미커버
    order = [t["pathogen"] for t in r["coverage"]["priority_uncovered_threats"]]
    assert order.index("Dengue") > order.index("H5N1")
    assert order.index("Dengue") > order.index("Ebola")
    assert order.index("Dengue") > order.index("MERS")


# ── EU HERA 3대 위협군 분류 ────────────────────────────────────────
def test_threat_category_coverage_marks_amr_untracked_cbrn_tracked():
    """세균 위협(탄저·페스트·야토병) 추가로 HERA의 CBRN 군이 실제 추적 대상이
    됐다. AMR은 여전히 추적 항목이 하나도 없어 tracked=False로 정직하게 남는다."""
    r = br.compute_readiness(_CM, br.DEFAULT_THREATS)
    cats = {c["category"]: c for c in r["threat_category_coverage"]["categories"]}
    assert cats["pandemic_pathogen"]["tracked"] is True
    assert cats["pandemic_pathogen"]["threats_assessed"] == 5
    assert cats["amr"]["tracked"] is False
    assert cats["amr"]["threats_assessed"] == 0
    assert cats["cbrn"]["tracked"] is True
    assert cats["cbrn"]["threats_assessed"] == 3


def test_threat_category_coverage_handles_empty_threats():
    cov = br.threat_category_coverage([])
    for c in cov["categories"]:
        assert c["tracked"] is False
        assert c["threats_assessed"] == 0


# ── 국제기준(항바이러스제 인구 25% 비축) 벤치마크 ───────────────────
def test_international_benchmark_not_assessed_without_antiviral_courses():
    r = br.international_benchmark(_CM)  # _CM의 antiviral 항목엔 courses 없음
    assert r["assessed"] is False


def test_international_benchmark_computes_real_population_coverage():
    cm = [{"name": "국가 비축 항바이러스제", "type": "antiviral", "targets": ["H5N1"],
           "domestic_producible": True, "courses": 12_920_000}]
    r = br.international_benchmark(cm, population=51_684_564)
    assert r["assessed"] is True
    assert r["population_coverage_pct"] == round(12_920_000 / 51_684_564, 4)
    assert r["meets_target"] is True  # 약 25% ≈ 국제권고 25% 충족


def test_international_benchmark_below_target_flagged_false():
    cm = [{"name": "소량 비축", "type": "antiviral", "targets": ["H5N1"],
           "domestic_producible": True, "courses": 1_000_000}]
    r = br.international_benchmark(cm, population=51_684_564)
    assert r["meets_target"] is False


def test_international_benchmark_ignores_non_antiviral_types():
    cm = [{"name": "백신", "type": "vaccine", "targets": ["Novel"],
           "domestic_producible": True, "courses": 50_000_000}]
    r = br.international_benchmark(cm)
    assert r["assessed"] is False


def test_compute_readiness_includes_reference_systems():
    r = br.compute_readiness(_CM, _THREATS)
    regions = {s["region"] for s in r["international_reference_systems"]}
    assert regions == {"EU", "US", "Japan"}


# ── 유전체 스크리닝 탐지역량 격차 ──────────────────────────────────
def test_genomic_screening_capability_splits_bacteria_from_viruses():
    """Evo2는 진핵숙주 감염 바이러스를 학습에서 제외해 판정할 수 없고 세균은
    가능하다 — 이 실측 한계가 위협별로 정확히 갈려 나와야 한다."""
    cap = br.genomic_screening_capability(br.DEFAULT_THREATS)
    assessable = {t["pathogen"] for t in cap["assessable_threats"]}
    not_assessable = {t["pathogen"] for t in cap["not_assessable_threats"]}
    assert assessable == {"Anthrax", "Plague", "Tularemia"}
    assert not_assessable == {"H5N1", "Ebola", "MERS", "Dengue"}
    assert cap["undeclared_domain_threats"] == ["Novel"]   # 미선언은 보수적 처리


def test_genomic_screening_capability_reports_reason_for_viruses():
    cap = br.genomic_screening_capability(br.DEFAULT_THREATS)
    reason = cap["not_assessable_threats"][0]["reason"]
    assert "학습에서 제외" in reason and "판정 불가" in reason


def test_genomic_screening_capability_rate_excludes_undeclared():
    """미선언(Novel)은 판정 가능으로 세지 않는다 — 8개 중 세균 3개만."""
    cap = br.genomic_screening_capability(br.DEFAULT_THREATS)
    assert cap["threats_assessed"] == 8
    assert cap["genomically_assessable"] == 3
    assert cap["assessable_rate"] == round(3 / 8, 3)


def test_genomic_screening_capability_handles_empty_and_unknown_domain():
    empty = br.genomic_screening_capability([])
    assert empty["genomically_assessable"] == 0 and empty["assessable_rate"] is None
    weird = br.genomic_screening_capability([{"pathogen": "X", "pathogen_domain": "오타"}])
    assert weird["genomically_assessable"] == 0
    assert weird["undeclared_domain_threats"] == ["X"]


def test_compute_readiness_exposes_screening_capability():
    r = br.compute_readiness(_CM, br.DEFAULT_THREATS)
    assert r["genomic_screening_capability"]["genomically_assessable"] == 3
    assert "Evo2" in r["disclaimer"]

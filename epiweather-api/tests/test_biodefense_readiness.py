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


def test_illustrative_reflects_real_bundibugyo_gap():
    """실사례 검증: 2026 DRC 분디부조형 에볼라는 백신 없음 → VALHALLA가 미커버로 잡는다.
    자이르형은 백신(Ervebo) 있어 커버되지만 수입의존(주권 격차)."""
    r = br.illustrative_readiness()
    assert "Ebola_Bundibugyo" in r["coverage"]["uncovered_threats"]   # 백신 없음 → 미커버
    assert "Ebola_Zaire" in r["resilience"]["import_only_covered"]     # 백신 있으나 수입
    assert "분디부조" in r["real_case_note"]

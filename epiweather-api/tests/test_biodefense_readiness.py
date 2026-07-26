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

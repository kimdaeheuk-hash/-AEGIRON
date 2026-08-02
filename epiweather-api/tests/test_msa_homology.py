"""Stage 0 상동성 신호 — 커버리지 판정과 실패 폴백을 결정론적으로 검증.
실제 MSA 검색은 monkeypatch로 대체(테스트가 네트워크·쿼터에 의존하면 안 됨)."""
from __future__ import annotations

import pytest

from algorithms import msa_homology as mh


def _a3m(entries: list[tuple[str, float, int, int, int]]) -> str:
    """(id, identity, qstart, qend, qlen) 목록을 a3m 헤더 형식으로."""
    lines = [">Query|-|Query", "MKT"]
    for hid, ident, qs, qe, ql in entries:
        lines.append(f">{hid}\t500\t{ident}\t1e-100\t{qs}\t{qe}\t{ql}\t0\t{qe - qs}\t{ql}")
        lines.append("MKT")
    return "\n".join(lines)


def _payload(dbs: dict[str, str]) -> dict:
    return {"alignments": {db: {"a3m": {"alignment": a3m, "format": "a3m"}}
                           for db, a3m in dbs.items()}}


PROTEIN = "M" + "KTVRQERLKSIFRTAYELLQDPNAWSGVKEHCFNTGVLQMSDPRTYIAG" * 3   # 148aa


def test_no_key_returns_not_ok(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    out = mh.assess_homology(PROTEIN)
    assert out["ok"] is False and "NVIDIA_API_KEY" in out["reason"]


def test_too_short_protein_rejected(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    out = mh.assess_homology("MKTVRQ")
    assert out["ok"] is False and "50aa 미만" in out["reason"]


def test_full_coverage_natural_protein_has_no_flags(monkeypatch):
    """자연 단백질처럼 전장을 덮는 상동체가 있으면 플래그 없음."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(mh, "_search", lambda p, k: _payload({
        "Uniref30_2302": _a3m([("UniRef100_X", 0.99, 0, 399, 400)]),
    }))
    out = mh.assess_homology(PROTEIN)
    assert out["ok"] is True
    assert out["best_coverage"] == pytest.approx(0.9975, abs=1e-3)
    assert out["flag_count"] == 0
    assert out["applies_to_viruses"] is True


def test_partial_coverage_flags_chimera(monkeypatch):
    """키메라처럼 어떤 상동체도 전장을 못 덮으면 재조합 후보로 플래그."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(mh, "_search", lambda p, k: _payload({
        "Uniref30_2302": _a3m([("UniRef100_A", 0.98, 0, 220, 400),
                               ("UniRef100_B", 0.90, 210, 260, 400)]),
    }))
    out = mh.assess_homology(PROTEIN)
    assert out["best_coverage"] == pytest.approx(0.55, abs=1e-3)
    assert [f["metric"] for f in out["flags"]] == ["msa_partial_coverage"]


def test_best_coverage_taken_across_databases(monkeypatch):
    """보수적 처리 — 어느 DB든 전장을 덮는 게 있으면 키메라로 몰지 않는다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(mh, "_search", lambda p, k: _payload({
        "Uniref30_2302": _a3m([("A", 0.9, 0, 200, 400)]),      # 50%
        "PDB70_220313": _a3m([("7XYZ_A", 0.95, 0, 398, 400)]),  # 99.5%
    }))
    out = mh.assess_homology(PROTEIN)
    assert out["best_coverage"] > 0.99 and out["flag_count"] == 0


def test_no_hits_flags_unknown_rather_than_artificial(monkeypatch):
    """히트가 0이면 '인공'이 아니라 '판정 불가'로 다뤄야 한다(신종 병원체 오탐 방지)."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(mh, "_search", lambda p, k: _payload({"Uniref30_2302": ">Query\nMKT"}))
    out = mh.assess_homology(PROTEIN)
    assert out["total_hits"] == 0
    assert [f["metric"] for f in out["flags"]] == ["msa_no_homolog"]
    assert "판정 불가" in out["flags"][0]["note"]


def test_search_failure_does_not_raise(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")

    def boom(p, k):
        raise RuntimeError("NIM down")

    monkeypatch.setattr(mh, "_search", boom)
    out = mh.assess_homology(PROTEIN)
    assert out["ok"] is False and "MSA 검색 실패" in out["reason"]


# ── 염기서열 → 단백질 변환 ────────────────────────────────────────
def test_translate_stops_at_stop_codon():
    assert mh._translate("ATGGCTTAAATGGCT") == "MA"      # TAA에서 중단


def test_protein_from_nucleotide_translates_complete_orf():
    """반복서열은 역상보 가닥에도 무정지 구간이 생기므로 길이를 정확히 못 박지
    않는다 — 6프레임 중 '가장 긴' 것을 고른다는 계약만 검증한다."""
    nt = "GGG" + "ATG" + "GCT" * 58 + "TAA" + "GGG"
    out = mh.protein_from_nucleotide(nt)
    assert out["ok"] is True
    assert out["protein_length"] >= 59
    assert out["protein_length"] == len(out["protein"])


def test_truncated_cds_without_stop_codon_still_translates():
    """★회귀 테스트★ 정지코돈 없이 잘린 CDS 조각(실제 입력에서 흔함)도 제대로
    번역해야 한다. ATG~정지코돈 방식으로 찾으면 진짜 리딩프레임을 놓치고 엉뚱한
    짧은 구간을 잡아 상동성 검색이 통째로 헛돈다(실측에서 히트 0개로 드러난 버그)."""
    nt = "ATG" + "GCT" * 120          # 정지코돈 없음, 121aa 상당
    out = mh.protein_from_nucleotide(nt)
    assert out["ok"] is True
    assert out["protein_length"] == 121
    assert out["protein"].startswith("MAAA")


def test_longest_peptide_picks_longest_stretch_across_frames():
    """정지코돈으로 끊긴 짧은 구간보다 긴 무정지 구간을 골라야 한다."""
    nt = "ATGGCTTAA" + "ATG" + "GCT" * 80      # 앞 2aa 조각 vs 뒤 81aa
    best = mh.longest_peptide_6frame(nt)
    assert len(best["protein"]) >= 81


def test_protein_from_nucleotide_rejects_short_input():
    out = mh.protein_from_nucleotide("ATGGCTTAA")
    assert out["ok"] is False and "상동성 검색 불가" in out["reason"]


def test_assess_from_nucleotide_reports_translated_region(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(mh, "_search", lambda p, k: _payload({
        "Uniref30_2302": _a3m([("UniRef100_X", 0.99, 0, 399, 400)]),
    }))
    out = mh.assess_from_nucleotide("ATG" + "GCT" * 58 + "TAA")
    assert out["ok"] is True
    # 번역 구간 길이(bp)와 단백질 길이(aa)가 항상 정합해야 한다
    assert out["translated_region"]["length_bp"] == out["protein_length_aa"] * 3

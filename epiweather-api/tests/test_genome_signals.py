"""Stage 0 유전체 신호 — CAI·CpG O/E·엔트로피를 '실제로' 계산하는지 결정론적 검증.
방어적 스크리닝(판정 아님)임을 결과가 명시하는지 확인."""
from __future__ import annotations

from algorithms import genome_signals as gs


def test_normalize_strips_and_converts_u_to_t():
    assert gs.normalize_seq("acg u\n123 T") == "ACGTT"


def test_gc_content():
    assert gs.gc_content("GGCC") == 1.0
    assert gs.gc_content("AATT") == 0.0
    assert gs.gc_content("") is None


def test_shannon_entropy_known_values():
    assert gs.shannon_entropy("AAAA") == 0.0          # 단일 염기 → 0비트
    assert gs.shannon_entropy("CGCGCG") == 1.0        # 두 염기 균등 → 1비트


def test_cpg_observed_expected_known():
    # "CGCGCG": CG 관측 3, C=3 G=3 len=6 → 기대 1.5 → O/E 2.0
    assert gs.cpg_observed_expected("CGCGCG") == 2.0


def test_cai_optimal_vs_rare_codon():
    opt = gs.cai("CTGCTGCTG")   # Leu CTG = 인간 최선호 → w=1
    rare = gs.cai("CTACTACTA")  # Leu CTA = 저빈도
    assert opt["cai"] == 1.0 and opt["codons_scored"] == 3
    assert rare["cai"] < 0.25   # 7.2/39.6 ≈ 0.18
    assert opt["cai"] > rare["cai"]


def test_cai_requires_coding_frame():
    assert gs.cai("ATGGCC") is not None          # 길이 6, 프레임 OK
    assert gs.cai("ATGGC") is None               # 3의 배수 아님


def test_restriction_scan_detects_ecori():
    counts = gs.restriction_scan("GGGGAATTCGGG")  # GAATTC = EcoRI
    assert counts["EcoRI"] >= 1


def test_screen_short_sequence_refused():
    r = gs.screen_sequence("ACGT")
    assert r["ok"] is False
    assert r["is_screening_only"] is True


def test_screen_normal_sequence_reports_metrics_and_disclaimer():
    seq = "ATGGCCATTGTAATGGGCCGCTGCAAAGGGTGCCCGATAGTT"  # >30nt
    r = gs.screen_sequence(seq)
    assert r["ok"] is True
    assert r["gc_content"] is not None
    assert r["shannon_entropy_bits"] is not None
    assert r["cpg_observed_expected"] is not None
    assert r["is_screening_only"] is True          # 판정 아님을 명시
    assert "전문가" in r["disclaimer"]


def test_low_complexity_sequence_flags_entropy():
    """반복·저복잡도 서열은 엔트로피 주의 플래그 — 방어 스크리닝의 핵심 신호."""
    r = gs.screen_sequence("A" * 40)
    assert r["ok"] is True
    assert any(f["metric"] == "shannon_entropy" for f in r["flags"])

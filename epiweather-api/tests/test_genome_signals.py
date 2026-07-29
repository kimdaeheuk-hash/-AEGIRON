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


# ── 새 각도: 국소 조성 이상 + 균등간격 시그니처 ──────────────────
def test_window_composition_flags_local_insert():
    """전체 평균엔 묻히는 국소 조성 이상(외래 삽입 후보)을 슬라이딩 윈도로 잡는다."""
    seq = ("AT" * 150) + ("GC" * 150) + ("AT" * 150)  # 가운데만 GC-rich
    r = gs.window_composition_anomaly(seq, window=100, step=50)
    assert r["assessed"] is True
    assert r["anomaly_count"] > 0   # GC-rich 삽입 구간이 잡힘


def test_window_composition_uniform_no_anomaly():
    r = gs.window_composition_anomaly("ATGC" * 200, window=100, step=50)
    assert r["assessed"] is True
    assert r["anomaly_count"] == 0  # 균질 서열 → 이상 없음


def test_restriction_even_spacing_signature():
    """BsaI 부위가 100bp 간격으로 균등 → 조립 시그니처로 플래그."""
    seq = ("GGTCTC" + "A" * 94) * 5   # 100bp마다 BsaI, 5개
    r = gs.restriction_even_spacing(seq)
    assert "BsaI" in r["even_spacing_flagged"]
    assert r["by_enzyme"]["BsaI"]["gap_cv"] == 0.0


def test_restriction_even_spacing_irregular_not_flagged():
    seq = "GGTCTC" + "A" * 10 + "GGTCTC" + "A" * 300 + "GGTCTC" + "A" * 30 + "GGTCTC"
    r = gs.restriction_even_spacing(seq)
    assert "BsaI" not in r["even_spacing_flagged"]  # 불규칙 간격 → 아님


# ── ORF 자동탐지(리딩프레임 안 맞아도 CAI 계산) ─────────────────
_CODING_WITH_STOP = "ATGGGGAAGGTGAAGGTCGGAGTCAACGGATTTGGTCGTATTGGGCGCCTGGTCACCAGGTAA"  # 63nt, ATG~TAA


def test_find_longest_orf_detects_shifted_frame():
    shifted = "CC" + _CODING_WITH_STOP  # 프레임 2칸 밀림, 3의 배수 아님
    orf = gs.find_longest_orf(shifted)
    assert orf is not None
    assert orf["sequence"] == _CODING_WITH_STOP
    assert orf["frame"] == 2


def test_cai_best_effort_falls_back_to_orf_when_frame_off():
    shifted = "CC" + _CODING_WITH_STOP
    assert gs.cai(shifted) is None                     # 직접 계산은 프레임 안 맞아 실패
    r = gs.cai_best_effort(shifted)
    assert r is not None
    assert r["orf_used"] is not None                    # 자동탐지 사용했음을 숨기지 않음
    assert r["orf_used"]["length"] == len(_CODING_WITH_STOP)


def test_cai_best_effort_no_orf_flag_when_already_in_frame():
    r = gs.cai_best_effort(_CODING_WITH_STOP)
    assert r is not None
    assert r["orf_used"] is None                        # 이미 프레임 맞음 → 자동탐지 안 씀


# ── 모호 염기(N 등) 처리 — 조용히 삭제·이어붙이지 않음 ──────────
def test_clean_segments_splits_on_ambiguous_bases():
    seq = "ACGT" * 10 + "NNNNN" + "TGCA" * 10
    segments = gs.clean_segments(seq)
    assert len(segments) == 2
    assert all(set(s) <= set("ACGT") for s in segments)


def test_count_ambiguous_bases_ignores_headers_and_whitespace():
    assert gs.count_ambiguous_bases(">seq1\nACGT NNN 123 acgt") == 3


def test_screen_sequence_reports_ambiguous_and_uses_longest_segment():
    long_segment = "ATGC" * 20          # 80nt, 분석 대상이 되어야 함
    short_segment = "ACGT" * 5           # 20nt, 30 미만이라 단독으론 스크리닝 불가
    seq = short_segment + ("N" * 10) + long_segment
    r = gs.screen_sequence(seq)
    assert r["ok"] is True
    assert r["analyzed_segment_length"] == len(long_segment)
    assert r["segments_found"] == 2
    assert r["ambiguous_bases_removed"] == 10
    assert "segments_note" in r


# ── 레퍼런스 서열 비교(실측 z-score, 임의 임계값 아님) ───────────
def test_compare_to_reference_needs_at_least_three_refs():
    assert gs.compare_to_reference(_CODING_WITH_STOP, [_CODING_WITH_STOP, _CODING_WITH_STOP]) is None


def test_compare_to_reference_returns_zscore_and_percentile():
    refs = [_CODING_WITH_STOP, _CODING_WITH_STOP[:-3] + "AAA", _CODING_WITH_STOP[:-6] + "AAAAAA"]
    r = gs.compare_to_reference(_CODING_WITH_STOP, refs)
    assert r is not None
    assert r["n_reference_sequences"] == 3
    assert "z_score" in r["gc_content"]
    assert "percentile" in r["gc_content"]


def test_screen_sequence_attaches_reference_comparison_when_provided():
    refs = [_CODING_WITH_STOP, _CODING_WITH_STOP[:-3] + "AAA", _CODING_WITH_STOP[:-6] + "AAAAAA"]
    seq = _CODING_WITH_STOP + "ATGC" * 5   # >30nt
    r = gs.screen_sequence(seq, reference_sequences=refs)
    assert "reference_comparison" in r
    assert r["reference_comparison"]["n_reference_sequences"] == 3

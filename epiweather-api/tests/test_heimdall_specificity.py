"""헤임달 특이도 측정 하네스의 배선 시험 (네트워크·실데이터 없음).

스크립트(scripts/heimdall_specificity.py)는 서열을 FASTA 로 받아 기존 스크리너를
블랙박스로 호출하고 거짓 양성 비율을 집계만 한다. 여기서는 그 **집계·파서·종료 코드**가
맞게 도는지를 본다 — 집계 로직은 스크리너를 스텁으로 고정해 스크리너의 판정과 독립으로,
실제 호출은 저복잡도 한 건으로만. 공개 서열은 러너(워크플로)가 받는다.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "heimdall_specificity", ROOT / "scripts" / "heimdall_specificity.py")
hs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hs)


def _fake_screen(flag_map):
    """서열 문자열 → 결과 dict 를 돌려주는 스텁. 집계 로직을 스크리너와 독립으로 검증."""
    def screen(seq):
        if len(seq) < 30:
            return {"ok": False, "reason": "too short"}
        n = flag_map.get(seq, 0)
        return {"ok": True, "flag_count": n,
                "flags": [{"metric": f"m{i}"} for i in range(n)],
                "gc_content": 0.5, "shannon_entropy_bits": 1.9,
                "cpg_observed_expected": 0.8}
    return screen


def test_parse_fasta_reads_multiple_records():
    text = ">one\nATGC\nATGC\n>two\nGGGG\n"
    assert hs.parse_fasta(text) == [("one", "ATGCATGC"), ("two", "GGGG")]


def test_evaluate_counts_flag_rate_and_distribution(monkeypatch):
    clean, dirty = "C" * 60, "G" * 60
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({clean: 0, dirty: 2}))
    report = hs.evaluate([("clean", clean), ("dirty", dirty), ("short", "ATGC")])
    assert report["records_in_file"] == 3
    assert report["screened"] == 2 and report["too_short_skipped"] == 1
    assert report["flagged"] == 1 and report["false_positive_rate"] == 0.5
    assert report["flagged_ids"] == ["dirty"]
    assert report["metric_distribution"]["gc_content"]["n"] == 2


def test_main_passes_under_threshold(tmp_path, monkeypatch):
    seq = "C" * 60
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({seq: 0}))
    fasta = tmp_path / "natural.fasta"
    fasta.write_text(f">a\n{seq}\n>b\n{seq}\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    assert hs.main([str(fasta), "--report", str(report_path), "--max-false-positive-rate", "0.5"]) == 0
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["screened"] == 2 and saved["false_positive_rate"] == 0.0


def test_main_fails_when_rate_exceeds_threshold(tmp_path, monkeypatch):
    seq = "G" * 60
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({seq: 3}))
    fasta = tmp_path / "x.fasta"
    fasta.write_text(f">h1\n{seq}\n>h2\n{seq}\n", encoding="utf-8")
    assert hs.main([str(fasta), "--max-false-positive-rate", "0.5"]) == 1


def test_real_screener_flags_extreme_low_complexity():
    """실제 스크리너 한 건만 — 극단 저복잡도(단일 염기 반복)는 올라가야 한다(거짓 양성 아님).
    통계적 구성물일 뿐 생물학 설계 정보가 아니다."""
    report = hs.evaluate([("homopolymer", "A" * 200)])
    assert report["screened"] == 1 and report["flagged"] == 1


def test_empty_fasta_is_an_error(tmp_path):
    fasta = tmp_path / "empty.fasta"
    fasta.write_text("\n\n", encoding="utf-8")
    assert hs.main([str(fasta)]) == 2


def test_chunk_sequence_drops_short_tail():
    assert hs.chunk_sequence("A" * 25, 10) == ["A" * 10, "A" * 10]
    assert hs.chunk_sequence("A" * 9, 10) == []


def test_evaluate_chunks_counts_per_chunk(monkeypatch):
    """긴 서열 하나가 '한 건'이 아니라 조각 수만큼 세어지는지 — 길이 보정의 핵심 배선."""
    clean, dirty = "C" * 40, "G" * 40
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({dirty: 1}))
    long_seq = clean * 3 + dirty  # 조각 4개 중 1개만 플래그
    report = hs.evaluate_chunks([("long", long_seq), ("tiny", "C" * 10)], 40)
    assert report["chunks_screened"] == 4 and report["chunks_flagged"] == 1
    assert report["chunk_flag_rate"] == 0.25
    assert report["flags_by_metric"] == {"m0": 1}
    assert report["records_shorter_than_chunk"] == ["tiny"]
    assert report["per_source"][0]["chunks_flagged"] == 1


def test_length_breakdown_buckets_screened_records(monkeypatch):
    short, long_ = "C" * 60, "G" * 20_000
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({long_: 1}))
    records = [("s", short), ("l", long_)]
    out = hs.length_breakdown(records, hs.evaluate(records))
    assert out["<10k"] == {"screened": 1, "flagged": 0, "flag_rate": 0.0}
    assert out["10k-100k"] == {"screened": 1, "flagged": 1, "flag_rate": 1.0}
    assert out[">=100k"]["screened"] == 0 and out[">=100k"]["flag_rate"] is None


def test_main_gates_on_first_chunk_size_when_given(tmp_path, monkeypatch):
    """서열 단위로는 100% 플래그여도, 조각 비율이 상한 아래면 통과(판정 기준이 조각으로 바뀜)."""
    clean, dirty = "C" * 40, "G" * 40
    monkeypatch.setattr(hs, "screen_sequence", _fake_screen({clean * 3 + dirty: 1, dirty: 1}))
    fasta = tmp_path / "x.fasta"
    fasta.write_text(f">a\n{clean * 3 + dirty}\n", encoding="utf-8")
    report_path = tmp_path / "r.json"
    args = [str(fasta), "--report", str(report_path), "--max-false-positive-rate", "0.5"]
    assert hs.main(args) == 1                               # 서열 단위: 1/1 → 빨간불
    assert hs.main(args + ["--chunk-sizes", "40,80"]) == 0  # 조각 40: 1/4 → 통과
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert [c["chunk_size"] for c in saved["chunked"]] == [40, 80]
    assert "length_breakdown" in saved


def test_bad_chunk_sizes_is_an_error(tmp_path):
    fasta = tmp_path / "x.fasta"
    fasta.write_text(">a\n" + "C" * 60 + "\n", encoding="utf-8")
    assert hs.main([str(fasta), "--chunk-sizes", "0"]) == 2

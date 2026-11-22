# -*- coding: utf-8 -*-
"""헤임달 스크리너 특이도 측정 — 공개 자연 서열에서 거짓 양성이 얼마나 나오나.

## 무엇을 재나 (정직성)

헤임달의 `genome_signals.screen_sequence` 는 **판정이 아니라 우선순위 신호**다. 이 신호가
제품으로 쓸 만하려면 먼저 "자연 서열을 괜히 올리지 않는가"(특이도)가 수치로 있어야 한다.
이 스크립트는 그 한 가지만 잰다: **공개 자연 서열 묶음(FASTA)에 스크리너를 돌려, 몇 %가
플래그되는지**와 **각 지표의 분포**를 리포트로 남긴다.

측정하지 않는 것(그래서 주장하지 않는다):
- 민감도(위험 서열을 잡는가) — 양성 대조군이 없으면 못 잰다. 이 스크립트 범위 밖이다.
- '이 서열은 안전하다/위험하다'는 판정. 특이도는 거짓 양성 비율일 뿐이다.

## 길이 보정 — 같은 길이 조각 (2026-11-22)

첫 실행(6/6 플래그)은 서열을 길이와 상관없이 "한 건"으로 셌다. 수백만 염기 전체 유전체와
수천 염기 서열을 같은 한 건으로 세면, 긴 서열일수록 어딘가 한 곳은 걸릴 기회가 많다 —
그 결과만으로는 "스크리너가 예민하다"와 "측정 단위가 불공정하다"를 가를 수 없다.
그래서 `--chunk-sizes` 를 주면 각 서열을 **같은 길이 조각**으로 잘라 조각마다 스크리너를
돌리고, 조각 단위 플래그 비율을 함께 낸다. 서열 단위 결과는 **길이 구간별**로도 나눈다.

한계(그래서 주장하지 않는다): 조각으로 자르면 스크리너가 보는 기준선(조각 안의 분포)도
바뀐다. 조각 비율은 "길이를 맞추면 어떻게 되나"를 보는 진단이지, 스크리너 자체의
정답 특이도가 아니다. 남는 끝 조각(지정 길이 미만)은 버린다(길이를 맞추려고).

## 어떻게 (역할 분리)

이 스크립트는 **네트워크를 쓰지 않는다.** 서열은 FASTA 파일로 받는다(러너가 공개
데이터베이스에서 받아 둔다 — .github/workflows/heimdall-validation.yml). 스크리너는
블랙박스로 호출만 한다(여기서 지표를 다시 구현하지 않는다). 그래서 이 파일은
시험에서 작은 합성 문자열로 배선만 검증할 수 있다(test_heimdall_specificity.py).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# 스크리너는 블랙박스다 — 결과 dict 만 읽는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithms.genome_signals import screen_sequence  # noqa: E402

# 리포트에 분포를 낼 수치 지표(스크리너 결과 dict 의 키). 없으면 그 서열에서 건너뛴다.
_NUMERIC_METRICS = ("gc_content", "shannon_entropy_bits", "cpg_observed_expected")


def parse_fasta(text: str) -> list[tuple[str, str]]:
    """FASTA 텍스트 → [(헤더, 서열)]. 표준 최소 파서."""
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header = line[1:].strip() or "(no id)"
            chunks = []
        elif line.strip():
            chunks.append(line.strip())
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def _summary(values: list[float]) -> dict | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    if not clean:
        return None
    return {
        "n": len(clean),
        "min": round(min(clean), 4),
        "max": round(max(clean), 4),
        "mean": round(statistics.mean(clean), 4),
        "stdev": round(statistics.pstdev(clean), 4) if len(clean) > 1 else 0.0,
    }


def evaluate(records: list[tuple[str, str]]) -> dict:
    """각 서열에 스크리너를 돌려 플래그 비율과 지표 분포를 집계한다. 네트워크 없음."""
    screened = 0
    flagged: list[str] = []
    too_short: list[str] = []
    metric_values: dict[str, list[float]] = {m: [] for m in _NUMERIC_METRICS}
    per_record: list[dict] = []

    for header, seq in records:
        result = screen_sequence(seq)
        if not result.get("ok"):
            too_short.append(header)
            per_record.append({"id": header, "ok": False, "reason": result.get("reason")})
            continue
        screened += 1
        n_flags = int(result.get("flag_count", 0) or 0)
        if n_flags > 0:
            flagged.append(header)
        for m in _NUMERIC_METRICS:
            v = result.get(m)
            if isinstance(v, (int, float)):
                metric_values[m].append(v)
        per_record.append({
            "id": header, "ok": True, "flag_count": n_flags,
            "flagged_metrics": [f.get("metric") for f in result.get("flags", [])],
        })

    flag_rate = round(len(flagged) / screened, 4) if screened else None
    return {
        "records_in_file": len(records),
        "screened": screened,
        "too_short_skipped": len(too_short),
        "flagged": len(flagged),
        "false_positive_rate": flag_rate,  # 자연 서열 묶음이므로 플래그 = 거짓 양성
        "flagged_ids": flagged,
        "metric_distribution": {m: _summary(vs) for m, vs in metric_values.items()},
        "per_record": per_record,
        "disclaimer": (
            "자연 공개 서열에서의 거짓 양성 비율(특이도)만 측정. 민감도·'안전/위험' 판정이 아니다. "
            "스크리너는 우선순위 신호이지 판정이 아니다."
        ),
    }


# 서열 단위 결과를 나눌 길이 구간(염기 수). 경계는 판단 상수 — 바꾸려면 여기만.
LENGTH_BUCKETS = ((0, 10_000, "<10k"), (10_000, 100_000, "10k-100k"),
                  (100_000, None, ">=100k"))


def _bucket(length: int) -> str:
    for lo, hi, label in LENGTH_BUCKETS:
        if length >= lo and (hi is None or length < hi):
            return label
    return LENGTH_BUCKETS[-1][2]


def length_breakdown(records: list[tuple[str, str]], report: dict) -> dict:
    """서열 단위 플래그를 길이 구간별로 센다(스크리닝된 것만)."""
    flagged = set(report.get("flagged_ids", []))
    screened_ids = {r["id"] for r in report.get("per_record", []) if r.get("ok")}
    out = {label: {"screened": 0, "flagged": 0} for _, _, label in LENGTH_BUCKETS}
    for header, seq in records:
        if header not in screened_ids:
            continue
        b = out[_bucket(len(seq))]
        b["screened"] += 1
        b["flagged"] += int(header in flagged)
    for b in out.values():
        b["flag_rate"] = round(b["flagged"] / b["screened"], 4) if b["screened"] else None
    return out


def chunk_sequence(seq: str, size: int) -> list[str]:
    """같은 길이(size) 조각으로 자른다. 남는 끝(size 미만)은 버린다."""
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [seq[i:i + size] for i in range(0, len(seq) - size + 1, size)]


def evaluate_chunks(records: list[tuple[str, str]], size: int) -> dict:
    """각 서열을 size 길이 조각으로 잘라 조각마다 스크리너를 돌리고 집계한다."""
    screened = flagged = skipped = 0
    metric_counts: dict[str, int] = {}
    per_source: list[dict] = []
    shorter_than_chunk: list[str] = []
    for header, seq in records:
        chunks = chunk_sequence(seq, size)
        if not chunks:
            shorter_than_chunk.append(header)
            continue
        s_screened = s_flagged = 0
        for chunk in chunks:
            result = screen_sequence(chunk)
            if not result.get("ok"):
                skipped += 1
                continue
            s_screened += 1
            if int(result.get("flag_count", 0) or 0) > 0:
                s_flagged += 1
                for f in result.get("flags", []):
                    m = f.get("metric") or "(unknown)"
                    metric_counts[m] = metric_counts.get(m, 0) + 1
        screened += s_screened
        flagged += s_flagged
        per_source.append({
            "id": header, "length": len(seq), "chunks_screened": s_screened,
            "chunks_flagged": s_flagged,
            "chunk_flag_rate": round(s_flagged / s_screened, 4) if s_screened else None,
        })
    return {
        "chunk_size": size,
        "chunks_screened": screened,
        "chunks_flagged": flagged,
        "chunks_skipped": skipped,
        "chunk_flag_rate": round(flagged / screened, 4) if screened else None,
        "flags_by_metric": dict(sorted(metric_counts.items())),
        "records_shorter_than_chunk": shorter_than_chunk,
        "per_source": per_source,
    }


def _parse_sizes(text: str | None) -> list[int]:
    if not text:
        return []
    sizes = [int(t) for t in text.split(",") if t.strip()]
    if any(n <= 0 for n in sizes):
        raise ValueError("chunk sizes must be positive integers")
    return sizes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="헤임달 스크리너 특이도 측정(자연 서열 거짓 양성 비율).")
    ap.add_argument("fasta", help="자연 공개 서열 FASTA 파일 경로(러너가 받아 둔 것).")
    ap.add_argument("--report", help="리포트 JSON 출력 경로(없으면 stdout).")
    ap.add_argument("--max-false-positive-rate", type=float, default=0.5,
                    help="이 비율을 넘으면 종료 코드 1(작업 빨간불). 기본 0.5.")
    ap.add_argument("--chunk-sizes", default="",
                    help="쉼표로 구분한 조각 길이(염기). 주면 조각 단위 비율도 재고, "
                         "**첫 번째 크기의 조각 비율**로 상한을 판정한다. 비우면 서열 단위로 판정.")
    args = ap.parse_args(argv)
    try:
        sizes = _parse_sizes(args.chunk_sizes)
    except ValueError as exc:
        print(f"--chunk-sizes 오류: {exc}", file=sys.stderr)
        return 2

    text = Path(args.fasta).read_text(encoding="utf-8", errors="replace")
    records = parse_fasta(text)
    if not records:
        print("FASTA 에서 서열을 하나도 못 읽음", file=sys.stderr)
        return 2

    report = evaluate(records)
    report["length_breakdown"] = length_breakdown(records, report)
    report["chunked"] = [evaluate_chunks(records, n) for n in sizes]
    out = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(out, encoding="utf-8")
    print(out)

    print(f"\n[서열 단위] 스크리닝 {report['screened']}건 · 플래그 {report['flagged']}건 · "
          f"비율 {report['false_positive_rate']}", file=sys.stderr)
    for label, b in report["length_breakdown"].items():
        print(f"  길이 {label}: {b['flagged']}/{b['screened']} (비율 {b['flag_rate']})", file=sys.stderr)
    for c in report["chunked"]:
        print(f"[조각 {c['chunk_size']}염기] {c['chunks_flagged']}/{c['chunks_screened']} "
              f"(비율 {c['chunk_flag_rate']}) · 지표별 {c['flags_by_metric']}", file=sys.stderr)

    if report["chunked"]:
        gate_name = f"조각 {report['chunked'][0]['chunk_size']}염기 비율"
        fpr = report["chunked"][0]["chunk_flag_rate"]
    else:
        gate_name, fpr = "서열 단위 비율", report["false_positive_rate"]
    if fpr is not None and fpr > args.max_false_positive_rate:
        print(f"::error::{gate_name} {fpr} > 상한 {args.max_false_positive_rate}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

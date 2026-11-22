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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="헤임달 스크리너 특이도 측정(자연 서열 거짓 양성 비율).")
    ap.add_argument("fasta", help="자연 공개 서열 FASTA 파일 경로(러너가 받아 둔 것).")
    ap.add_argument("--report", help="리포트 JSON 출력 경로(없으면 stdout).")
    ap.add_argument("--max-false-positive-rate", type=float, default=0.5,
                    help="이 비율을 넘으면 종료 코드 1(작업 빨간불). 기본 0.5.")
    args = ap.parse_args(argv)

    text = Path(args.fasta).read_text(encoding="utf-8", errors="replace")
    records = parse_fasta(text)
    if not records:
        print("FASTA 에서 서열을 하나도 못 읽음", file=sys.stderr)
        return 2

    report = evaluate(records)
    out = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(out, encoding="utf-8")
    print(out)

    fpr = report["false_positive_rate"]
    print(f"\n스크리닝 {report['screened']}건 · 플래그 {report['flagged']}건 · "
          f"거짓 양성 비율 {fpr}", file=sys.stderr)
    if fpr is not None and fpr > args.max_false_positive_rate:
        print(f"::error::거짓 양성 비율 {fpr} > 상한 {args.max_false_positive_rate}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

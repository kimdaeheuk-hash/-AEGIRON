#!/usr/bin/env python
"""Evo2 적용범위 재현 검증 스크립트 — "왜 바이러스는 안 되는가"의 근거.

왜 필요한가: Stage 0의 Evo2 스크리닝은 진핵숙주 감염 바이러스에 대해 판정을
거부한다(evo2_naturalness.APPLICABILITY). 이건 임의 결정이 아니라 실측 결과인데,
숫자만 docstring에 적어두면 나중에 "정말 그런가"를 다시 확인할 방법이 없다.
심사·실사에서 근거를 요구받을 때 그 자리에서 돌려 보여줄 수 있도록 실험 자체를
저장소에 남긴다.

두 실험을 순서대로 돌린다:
  실험 1 (분류군)  자연서열만 넣어 분류군별 점수를 비교 — 바이러스만 바닥인가?
  실험 2 (상대기준) 바이러스 안에서 자연 vs 셔플 vs 키메라 — 상대비교로는 되는가?

사전 등록 기준(결과를 보고 고치지 않는다):
  A. 자연 vs 셔플 일치율 차이 >= 15%p
  B. 자연 바이러스들끼리 표준편차 <= 5%p (공통 기준선 설정 가능해야 함)
  C. 키메라 접합부가 그 외 구간보다 >= 15%p 낮을 것
  A와 B를 둘 다 만족해야 "바이러스에도 적용 가능"으로 본다.

실행:
  cd epiweather-api
  PYTHONIOENCODING=utf-8 python -u scripts/validate_evo2_applicability.py
  (NVIDIA_API_KEY 필요. 약 120회 NIM 호출 = 20~30분, NCBI는 키 불필요)

최근 실행 결과는 이 파일 하단 "실행 기록" 참고.
"""
from __future__ import annotations

import os
import random
import statistics
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.evo2_naturalness import score_naturalness  # noqa: E402

N_WINDOWS = 10
REGION_LEN = 4000
NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 분류군별 대표 레퍼런스(전부 NCBI 공개 자연서열).
TAXA = [
    ("박테리오파지 람다", "NC_001416.1", "phage"),
    ("인간 mtDNA", "NC_012920.1", "eukaryote"),
    ("효모 16번염색체", "NC_001148.4", "eukaryote"),
    ("대장균", "NC_000913.3", "bacteria_archaea"),
    ("SARS-CoV-2", "NC_045512.2", "eukaryotic_virus"),
    ("인플루엔자A HA", "NC_026433.1", "eukaryotic_virus"),
    ("에볼라 자이르", "NC_002549.1", "eukaryotic_virus"),
]

# 실험 2용 바이러스 세트.
VIRUSES = [
    ("SARS-CoV-2", "NC_045512.2"),
    ("인플루엔자A", "NC_026433.1"),
    ("에볼라", "NC_002549.1"),
    ("MERS", "NC_019843.3"),
    ("뎅기1형", "NC_001477.1"),
]

CHANCE_LEVEL = 0.25   # 염기 4종 → 무작위로 찍어도 25%


def fetch(acc: str, start: int = 1, stop: int = REGION_LEN) -> str:
    r = requests.get(NCBI, params={"db": "nuccore", "id": acc, "rettype": "fasta",
                                   "retmode": "text", "seq_start": start,
                                   "seq_stop": stop}, timeout=60)
    r.raise_for_status()
    return "".join(ln.strip() for ln in r.text.splitlines()
                   if ln and not ln.startswith(">")).upper()


def rate(seq: str, n: int = N_WINDOWS) -> dict:
    """적용범위 게이팅과 무관하게 원점수를 본다(게이팅 근거 자체를 재는 실험이므로)."""
    out = score_naturalness(seq, n_windows=n, organism_domain="eukaryotic_virus")
    if not out.get("ok"):
        raise RuntimeError(out.get("reason"))
    return out


def experiment_1_taxa() -> None:
    print("=" * 72)
    print("실험 1 — 분류군별 자연서열 점수 (무작위 찍기 = 25%)")
    print("=" * 72)
    by_group: dict[str, list[float]] = {}
    for name, acc, group in TAXA:
        mr = rate(fetch(acc))["match_rate"]
        by_group.setdefault(group, []).append(mr)
        print(f"  {name:18s} {acc:14s} {group:18s} {mr:>7.1%}")

    virus = statistics.mean(by_group.get("eukaryotic_virus", [0]))
    others = [v for g, vs in by_group.items() if g != "eukaryotic_virus" for v in vs]
    other_mean = statistics.mean(others) if others else 0.0
    print("-" * 72)
    print(f"  진핵감염 바이러스 평균 {virus:.1%}  /  그 외 평균 {other_mean:.1%}"
          f"  (차이 {other_mean - virus:+.1%})")
    print(f"  → 바이러스는 찍기(25%)보다 {virus - CHANCE_LEVEL:+.1%}, "
          f"그 외는 {other_mean - CHANCE_LEVEL:+.1%}")


def experiment_2_relative() -> None:
    print("\n" + "=" * 72)
    print("실험 2 — 바이러스 상대 기준선: 자연 vs 셔플 vs 키메라")
    print("=" * 72)
    seqs = {name: fetch(acc) for name, acc in VIRUSES}

    print(f"  {'바이러스':14s} {'자연':>8s} {'셔플':>8s} {'차이':>9s}")
    nat_rates, diffs = [], []
    for name, _ in VIRUSES:
        seq = seqs[name]
        nat = rate(seq)["match_rate"]
        shf = rate("".join(random.Random(11).sample(seq, len(seq))))["match_rate"]
        nat_rates.append(nat)
        diffs.append(nat - shf)
        print(f"  {name:14s} {nat:>7.1%} {shf:>8.1%} {nat - shf:>+8.1%}")

    mean_diff, nat_sd = statistics.mean(diffs), statistics.pstdev(nat_rates)
    crit_a, crit_b = mean_diff >= 0.15, nat_sd <= 0.05
    print("-" * 72)
    print(f"  기준A 자연-셔플 차이 >= 15%p : {'통과' if crit_a else '미달'} ({mean_diff:+.1%})")
    print(f"  기준B 자연 표준편차 <= 5%p   : {'통과' if crit_b else '미달'} ({nat_sd:.1%})")

    # 키메라 — 실제 탐지 대상(조각 이어붙이기)에 가까운 시험.
    half = REGION_LEN // 2
    chimera = seqs["SARS-CoV-2"][:half] + seqs["에볼라"][:half]
    res = rate(chimera, n=12)
    near = [w for w in res["windows"] if w.get("ok") and abs(w["position"] - half) <= 400]
    far = [w for w in res["windows"] if w.get("ok") and abs(w["position"] - half) > 400]
    if near and far:
        nm, fm = (statistics.mean(w["match_rate"] for w in near),
                  statistics.mean(w["match_rate"] for w in far))
        crit_c = (fm - nm) >= 0.15
        print(f"  기준C 키메라 접합부 저하    : {'통과' if crit_c else '미달'} "
              f"(접합부 {nm:.1%} vs 그 외 {fm:.1%})")
    else:
        crit_c = False
        print("  기준C 판정 불가(접합부 근처 윈도 없음)")

    print("\n" + "=" * 72)
    print(f"최종: A={'O' if crit_a else 'X'} B={'O' if crit_b else 'X'} C={'O' if crit_c else 'X'}")
    print("=> 바이러스에도 적용 가능" if (crit_a and crit_b)
          else "=> 적용 불가 — eukaryotic_virus 게이팅 유지가 옳음")


if __name__ == "__main__":
    if not os.environ.get("NVIDIA_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not os.environ.get("NVIDIA_API_KEY"):
        sys.exit("NVIDIA_API_KEY 없음 — .env 또는 환경변수에 설정 필요")
    experiment_1_taxa()
    experiment_2_relative()


# ── 실행 기록 ────────────────────────────────────────────────────────
# 2026-07-30  evo2-40b NIM, 각 4kb, 윈도 6개
#   실험 1: 람다파지 100.0% / 인간 mtDNA 91.7% / 효모 90.3% / 대장균 87.5%
#           SARS-CoV-2 33.3% / 인플루엔자A 31.9% / 에볼라 25.0%
#           → 진핵감염 바이러스 30.1% vs 그 외 92.4% (차이 62.3%p)
#           파지(세균 감염)가 100%인데 진핵감염만 바닥 = '학습 제외'의 직접 증거
#
# 2026-07-31  evo2-40b NIM, 각 4kb, 윈도 10개
#   실험 2: 인플루엔자A 44.2/32.5(+11.7) · SARS-CoV-2 36.7/26.7(+10.0)
#           에볼라 31.7/25.8(+5.8) · MERS 32.4/32.5(-0.1) · 뎅기1형 21.7/33.3(-11.7)
#           기준A 미달(+3.2%) · 기준B 미달(7.3%) · 기준C 미달(부호 반대, 접합부가 오히려 높음)
#   해석: 뎅기는 셔플이 자연보다 높게 나왔고 키메라 접합부도 방향이 반대다.
#         자연 바이러스 평균 33.3%는 찍기(25%)보다 8.3%p 위에 불과 —
#         '신호가 약한' 게 아니라 '신호가 없는' 상태로 판정.
#   결론: 상대 기준선으로도 안 된다. eukaryotic_virus 게이팅은 예방조치가 아니라
#         실측으로 확인된 한계다. 우회로를 찾으려면 Evo2가 아닌 다른 모델이 필요하다
#         (ESM-2는 UniRef 학습이라 바이러스 단백질을 포함하나, 2026-07-31 기준
#          NIM 엔드포인트가 HTTP 500/Nvcf-Status:errored로 서버측 오류 — 재시도 필요).

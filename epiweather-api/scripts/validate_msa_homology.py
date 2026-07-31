"""MSA-Search 2차 검증 — 1차에서 나온 가설을 '새 데이터'로 확인.

1차(탐색): 자연 5종 전부 99.8%, 키메라 5종 55~75%. 겹침 없음(25%p 간격).
  → 가설: "자연계에 질의 전체를 덮는 상동체가 있으면 자연, 없으면 이어붙인 것"
  1차의 사전등록 기준(<=70% AND 접합부 ±30aa)은 실패했다 — 임계값이 빡빡했고
  접합부 기준은 개념 오류(국소정렬은 접합부를 지나 이어짐). 같은 데이터로 기준만
  바꿔 재채점하면 자기충족이므로, 새 검체로 다시 건다.

2차 사전 등록 기준(결과 보고 고치지 않는다):
  자연  : 커버리지 >= 90%  → 5/5 필요
  키메라: 커버리지 <  90%  → 5/5 필요
  접합부 위치 기준은 폐기(1차에서 개념 오류로 확인됨).

핵심 오탐 시험: 덜 연구된 바이러스(라싸·니파·한탄)를 일부러 넣는다. 신종·희귀
병원체는 DB에 상동체가 빈약해 키메라처럼 보일 수 있고, 그러면 이 지표는 실전에서
'처음 보는 병원체'를 전부 인공으로 오탐하게 된다 — Evo2에서 겪은 것과 같은 함정.
"""
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
KEY = os.environ["NVIDIA_API_KEY"]
URL = "https://health.api.nvidia.com/v1/biology/colabfold/msa-search/predict"
NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 1차에서 쓰지 않은 새 검체. 뒤 3종은 상대적으로 덜 연구된 병원체(오탐 시험).
PROTEINS = {
    "마버그 GP":   "YP_001531156.1",
    "지카 폴리단백": "YP_009428568.1",
    "라싸 GPC":    "NP_694870.1",
    "니파 G":      "NP_112026.1",
    "한탄 GPC":    "NP_941975.1",
}
SEG, HALF, THRESHOLD = 400, 200, 0.90


def fetch_protein(acc: str) -> str:
    r = requests.get(NCBI, params={"db": "protein", "id": acc,
                                   "rettype": "fasta", "retmode": "text"}, timeout=60)
    r.raise_for_status()
    body = r.text
    if "Error" in body[:200] or ">" not in body:
        raise RuntimeError(f"NCBI 조회 실패: {acc}")
    return "".join(ln.strip() for ln in body.splitlines()
                   if ln and not ln.startswith(">")).upper()


def best_coverage(seq: str) -> float:
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}",
                                    "Content-Type": "application/json"},
                      json={"sequence": seq}, timeout=900)
    r.raise_for_status()
    best = 0.0
    for _db, val in (r.json().get("alignments") or {}).items():
        for line in val.get("a3m", {}).get("alignment", "").splitlines():
            if not line.startswith(">"):
                continue
            parts = line.split("\t")
            if len(parts) < 10:
                continue
            try:
                qs, qe, ql = int(parts[4]), int(parts[5]), int(parts[6])
            except ValueError:
                continue
            if ql > 0:
                best = max(best, (qe - qs) / ql)
    return best


print("새 검체 수집 중(1차에서 안 쓴 바이러스)...")
seqs = {}
for name, acc in PROTEINS.items():
    try:
        full = fetch_protein(acc)
        if len(full) < SEG:
            print(f"  [건너뜀] {name} — 전장 {len(full)}aa < {SEG}aa")
            continue
        seqs[name] = full[:SEG]
        print(f"  {name:14s} {acc:18s} 전장 {len(full)}aa")
    except Exception as e:
        print(f"  [실패] {name} {acc} — {e}")

names = list(seqs)
if len(names) < 5:
    print(f"\n검체가 {len(names)}종뿐 — 5종 필요. 접근번호 확인 필요.")

print("\n" + "=" * 74)
print(f"A. 자연(새 검체) — 기준: 커버리지 >= {THRESHOLD:.0%}")
print("=" * 74)
nat_pass = 0
for name in names:
    t0 = time.time()
    cov = best_coverage(seqs[name])
    ok = cov >= THRESHOLD
    nat_pass += ok
    print(f"  {name:14s} 커버리지 {cov:6.1%}  {'통과' if ok else '미달 ← 오탐!'}   [{time.time() - t0:.0f}초]")

print("\n" + "=" * 74)
print(f"B. 키메라(새 조합) — 기준: 커버리지 < {THRESHOLD:.0%}")
print("=" * 74)
PAIRS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
chi_pass = 0
tested = 0
for i, j in PAIRS:
    if i >= len(names) or j >= len(names):
        continue
    a, b = names[i], names[j]
    cov = best_coverage(seqs[a][:HALF] + seqs[b][HALF:HALF * 2])
    ok = cov < THRESHOLD
    chi_pass += ok
    tested += 1
    print(f"  {a[:10]:10s}+{b[:10]:10s} 커버리지 {cov:6.1%}  {'통과' if ok else '미달 ← 놓침!'}")

print("\n" + "=" * 74)
print(f"자연 {nat_pass}/{len(names)} 통과, 키메라 {chi_pass}/{tested} 통과")
ok_all = nat_pass == len(names) == 5 and chi_pass == tested == 5
print("=> 2차 검증 통과 — 붙일 가치 있음" if ok_all
      else "=> 2차 검증 실패 — 붙이지 말 것")


# ── 실행 기록 ────────────────────────────────────────────────────────
# 2026-07-31  colabfold msa-search NIM, 각 400aa
#   1차(탐색, 다른 검체): 자연 5종(SARS-CoV-2·에볼라·MERS·인플루엔자A·뎅기1) 전부 99.8%
#                        키메라 5종 55.5~74.8%
#     1차 사전등록 기준(<=70% AND 접합부 ±30aa)은 실패했다. 접합부 기준이 개념
#     오류였고(국소정렬은 접합부를 지나 이어짐) 임계값도 빡빡했다. 같은 데이터로
#     기준만 바꿔 재채점하지 않고, 아래 2차를 '새 검체'로 다시 걸어서 확인했다.
#   2차(이 스크립트): 자연 5/5 전부 99.8% 통과, 키메라 5/5 52.5~57.5% 통과
#     ★ 오탐 시험 통과 — 덜 연구된 라싸·니파·한탄도 전부 99.8%로 정상 판정.
#     Evo2가 빠졌던 '희귀·신종 병원체 오탐' 함정을 DB 검색 방식은 피한다.
#   실서열 E2E(엔드포인트 경유): 자연 SARS-CoV-2 스파이크 CDS 99.8%(히트 298,
#     최상위 7A92_A 동일도 1.0) / 키메라 52.5% → msa_partial_coverage 플래그.

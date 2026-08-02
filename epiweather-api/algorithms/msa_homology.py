"""Stage 0 상동성 신호 — "자연계에 이 서열 전체를 설명하는 단백질이 있는가".

배경: genome_signals.py는 조성 통계(CAI·CpG)를, evo2_naturalness.py는 순서의
자연스러움을 본다. 그런데 Evo2는 진핵숙주 감염 바이러스를 학습에서 제외해서
**이 시스템이 감시하는 병원체 대부분(코로나·독감·에볼라)에 쓸 수 없다**
(evo2_naturalness 참조). 이 모듈이 그 구멍을 메운다.

방법: 단백질 서열을 공개 상동성 DB(UniRef30·colabfold_envdb·PDB70)에 검색해
**질의 전체를 덮는 자연 단백질이 존재하는지** 본다. 자연 단백질이면 근연 서열이
전장을 덮고, 여러 생물의 조각을 이어붙인 서열이면 어떤 자연 단백질도 전체를
덮지 못하고 커버리지가 뚝 떨어진다 — 재조합·키메라의 직접적 흔적이다.

★ 왜 이게 Evo2보다 중요한가 ★
학습된 모델이 아니라 **DB 검색**이라 '학습에서 빠진 분류군' 문제가 없다.
바이러스에도 그대로 작동한다 — 아래 실측이 그 증거.

실측 검증(2026-07-31, colabfold msa-search NIM, 각 400aa, 2라운드 독립 수행):
  1차(탐색)  자연 5종(SARS-CoV-2·에볼라·MERS·인플루엔자A·뎅기1) 전부 99.8%
             키메라 5종 55.5~74.8%
  2차(사전등록 기준으로 새 검체) 자연 5종(마버그·지카·라싸·니파·한탄) 전부 99.8%
             키메라 5종 52.5~57.5%   → 자연 5/5, 키메라 5/5 통과
  1차의 원래 기준(<=70% + 접합부 위치)은 실패했다. 접합부 기준은 개념 오류였고
  (국소정렬은 접합부를 지나 이어짐) 임계값도 빡빡했다. 같은 데이터로 기준만 바꿔
  재채점하지 않고 **새 검체로 다시 걸어서** 통과시킨 것이 위 2차다.

  ★ 오탐 시험 통과 ★ 2차에 덜 연구된 병원체(라싸·니파·한탄)를 일부러 넣었고
  전부 99.8%가 나왔다 — 희귀·신종 병원체를 인공으로 오탐하지 않는다는 뜻.
  Evo2에서 겪은 함정을 여기서는 피한다.

★ 안전 경계선(genome_signals·evo2_naturalness와 동일) ★
- 방어적 스크리닝 전용. 서열을 설계·합성·최적화하거나 회피법을 제공하지 않는다.
- 낮은 커버리지 = '인공' 판정이 아니라 '자연 상동체로 전부 설명되지 않음'이라는
  추가검토 우선순위다. 최종 판단은 전문가·계통발생·습식실험이 필요하다.
"""
from __future__ import annotations

import os

import requests

MSA_URL = "https://health.api.nvidia.com/v1/biology/colabfold/msa-search/predict"
TIMEOUT = 900          # 검색 1회에 약 40초. 여유를 크게 둔다.
MIN_AA = 50            # 너무 짧으면 상동성 검색이 의미 없음

# 실측 기반 참고범위(위 docstring의 2라운드 검증값).
_REF = {
    "coverage_natural": 0.998,      # 자연 단백질 실측(10종 전부 동일)
    "coverage_chimera_max": 0.748,  # 키메라 실측 최대(1차 포함)
    "coverage_low": 0.90,           # 이 미만이면 '전장 상동체 없음' 플래그
}


def _translate(nt: str) -> str:
    """뉴클레오타이드 → 아미노산(표준 유전암호). 종결코돈에서 끊는다."""
    from .genome_signals import _CODON_AA

    aa = []
    for i in range(0, len(nt) - 2, 3):
        residue = _CODON_AA.get(nt[i:i + 3])
        if residue is None:
            break                  # 모호 염기 등 — 거기서 중단
        if residue == "*":
            break
        aa.append(residue)
    return "".join(aa)


def longest_peptide_6frame(seq: str) -> dict | None:
    """6프레임(순방향 3 + 역상보 3)에서 **정지코돈 없이 이어지는 가장 긴 번역 구간**.

    genome_signals.find_longest_orf(ATG~정지코돈)를 쓰지 않는 이유: 실제 입력은
    잘린 CDS 조각인 경우가 많아 정지코돈이 안 나타난다. 그러면 진짜 리딩프레임이
    ORF로 인식되지 않고 엉뚱한 짧은 ORF가 뽑혀 상동성 검색이 통째로 헛돈다
    (실제로 SARS-CoV-2 스파이크 CDS 조각에서 히트 0개가 나던 버그). 조각 서열의
    코딩 잠재력을 볼 때는 '무정지 최장 구간'이 표준 처리다."""
    from .genome_signals import _CODON_AA, _rc

    best: dict | None = None
    for strand, s in (("+", seq), ("-", _rc(seq))):
        for frame in range(3):
            peptide: list[str] = []
            start = frame
            for i in range(frame, len(s) - 2, 3):
                residue = _CODON_AA.get(s[i:i + 3])
                if residue is None or residue == "*":
                    if best is None or len(peptide) > len(best["protein"]):
                        best = {"strand": strand, "frame": frame, "start": start,
                                "end": i, "protein": "".join(peptide)}
                    peptide, start = [], i + 3
                else:
                    peptide.append(residue)
            if best is None or len(peptide) > len(best["protein"]):
                best = {"strand": strand, "frame": frame, "start": start,
                        "end": start + len(peptide) * 3, "protein": "".join(peptide)}
    return best


def protein_from_nucleotide(raw: str) -> dict:
    """염기서열에서 무정지 최장 구간을 찾아 단백질로 번역. Stage 0 입력은 염기서열
    이지만 상동성 DB는 전부 단백질이라 이 변환이 필요하다. 어느 구간을 썼는지 명시."""
    from .genome_signals import clean_segments

    segments = clean_segments(raw)
    seq = max(segments, key=len) if segments else ""
    if len(seq) < MIN_AA * 3:
        return {"ok": False, "reason": f"연속 구간이 {MIN_AA * 3}bp 미만 — 상동성 검색 불가"}
    best = longest_peptide_6frame(seq)
    if best is None or len(best["protein"]) < MIN_AA:
        got = len(best["protein"]) if best else 0
        return {"ok": False,
                "reason": f"무정지 최장 번역 구간이 {got}aa — {MIN_AA}aa 미만이라 상동성 검색 불가"}
    return {
        "ok": True,
        "protein": best["protein"],
        "protein_length": len(best["protein"]),
        "translated_region": {"strand": best["strand"], "frame": best["frame"],
                              "start": best["start"], "end": best["end"],
                              "length_bp": best["end"] - best["start"]},
    }


def _search(protein: str, api_key: str) -> dict:
    r = requests.post(
        MSA_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"sequence": protein},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _parse_hits(payload: dict) -> tuple[float, list[dict], dict[str, int]]:
    """a3m 헤더에서 (최고 커버리지, 상위 히트, DB별 히트수)를 뽑는다.

    헤더 형식: >ID\\t점수\\t동일도\\tE값\\tqstart\\tqend\\tqlen\\ttstart\\ttend\\ttlen
    보수적 선택: 여러 DB 중 '가장 잘 덮는' 히트를 기준으로 삼는다 — 어느 DB든
    전장을 덮는 자연 단백질이 있으면 키메라로 몰지 않는다(오탐 억제)."""
    best_cov = 0.0
    hits: list[dict] = []
    counts: dict[str, int] = {}
    for db, val in (payload.get("alignments") or {}).items():
        n = 0
        for line in val.get("a3m", {}).get("alignment", "").splitlines():
            if not line.startswith(">"):
                continue
            parts = line.split("\t")
            if len(parts) < 10:
                continue                         # Query 자기 자신 등 메타 없는 줄
            try:
                identity = float(parts[2])
                evalue = float(parts[3])
                qs, qe, ql = int(parts[4]), int(parts[5]), int(parts[6])
            except ValueError:
                continue
            if ql <= 0:
                continue
            n += 1
            cov = (qe - qs) / ql
            hits.append({"id": parts[0].lstrip(">"), "database": db,
                         "coverage": round(cov, 4), "identity": identity,
                         "e_value": evalue, "query_start": qs, "query_end": qe})
            best_cov = max(best_cov, cov)
        counts[db] = n
    hits.sort(key=lambda h: (-h["coverage"], -h["identity"]))
    return best_cov, hits[:5], counts


def assess_homology(protein: str, api_key: str | None = None) -> dict:
    """단백질 서열의 자연 상동체 커버리지를 실측. 실패해도 예외를 던지지 않고
    {"ok": False, ...}를 돌려준다 — 외부 API 장애가 Stage 0 전체를 막으면 안 된다."""
    key = api_key or os.environ.get("NVIDIA_API_KEY")
    if not key:
        return {"ok": False, "reason": "NVIDIA_API_KEY 없음 — 상동성 검색 생략",
                "is_screening_only": True}
    if len(protein) < MIN_AA:
        return {"ok": False, "reason": f"단백질이 {MIN_AA}aa 미만 — 상동성 검색 불가",
                "is_screening_only": True}

    try:
        payload = _search(protein, key)
    except Exception as e:
        return {"ok": False, "reason": f"MSA 검색 실패({type(e).__name__}) — 네트워크·키·쿼터 확인",
                "is_screening_only": True}

    coverage, top_hits, counts = _parse_hits(payload)
    total_hits = sum(counts.values())

    flags: list[dict] = []
    if total_hits == 0:
        flags.append({
            "metric": "msa_no_homolog", "value": 0,
            "note": "자연 상동체가 전혀 검색되지 않음 — 신종 병원체 또는 DB 미수록. "
                    "커버리지 판정 불가이므로 계통발생 확인 필요.",
        })
    elif coverage < _REF["coverage_low"]:
        flags.append({
            "metric": "msa_partial_coverage", "value": round(coverage, 4),
            "note": f"자연 상동체가 질의의 {coverage:.1%}만 덮음 "
                    f"(자연 단백질 실측 {_REF['coverage_natural']:.1%}, "
                    f"키메라 실측 최대 {_REF['coverage_chimera_max']:.1%}) — "
                    "여러 출처 조각을 이어붙인 재조합·키메라 후보.",
        })

    return {
        "ok": True,
        "query_length_aa": len(protein),
        "best_coverage": round(coverage, 4),
        "total_hits": total_hits,
        "hits_by_database": counts,
        "top_hits": top_hits,          # 식별자 포함 — 근연 서열 추적에 사용 가능
        "flags": flags,
        "flag_count": len(flags),
        "is_screening_only": True,
        "reference_ranges": _REF,
        "applies_to_viruses": True,    # Evo2와 달리 바이러스에도 유효(실측 확인)
        "method": (
            "공개 상동성 DB(UniRef30·colabfold_envdb·PDB70) 검색 후 '질의 전체를 덮는 "
            "자연 단백질이 존재하는가'를 최고 커버리지로 판정. 학습 모델이 아니라 DB "
            "검색이라 Evo2의 '학습 제외 분류군' 문제가 없다."
        ),
        "disclaimer": (
            "낮은 커버리지는 '인공 설계' 판정이 아니라 '자연 상동체로 전부 설명되지 "
            "않음'이라는 추가검토 우선순위다. DB에 아직 수록되지 않은 신종 자연 병원체도 "
            "낮게 나올 수 있으며(검증에서 라싸·니파·한탄 등 희귀 병원체는 정상 판정됨), "
            "최종 판단은 전문가·계통발생·습식실험 확인이 필요하다."
        ),
    }


def assess_from_nucleotide(raw: str, api_key: str | None = None) -> dict:
    """염기서열 입력용 — 최장 ORF를 번역해 상동성 판정. Stage 0 배선용."""
    translated = protein_from_nucleotide(raw)
    if not translated.get("ok"):
        return {**translated, "is_screening_only": True}
    result = assess_homology(translated["protein"], api_key=api_key)
    result["translated_region"] = translated["translated_region"]
    result["protein_length_aa"] = translated["protein_length"]
    return result

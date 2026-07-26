"""Stage 0 유전체 신호 — 서열의 '자연스러움' 통계를 실제로 계산하는 방어적 스크리너.

배경: 기존 Stage 0은 CAI·CpG·엔트로피를 '실제로 계산'하지 않고 Claude에게 그
지표에 대해 논평만 시켰다(존재하지 않는 숫자를 해설). 이 모듈이 그 지표를 실제로
계산해 장난감에서 실측으로 끌어올린다 — 전부 표준·공개 생물정보학 방법이고 순수
파이썬(외부 API·모델 불필요).

★ 안전 경계선(중요) ★
- 이건 **방어적 스크리닝**이다: 주어진 서열이 자연 진화와 통계적으로 다른 신호를
  보이는지 '탐지·플래그'만 한다(바이오안보 스크리닝이 하는 방어 기능).
- 서열을 설계·합성·최적화하거나 '스크리닝을 회피하는 법'은 제공하지 않는다.
- 결과는 '정밀 우선순위 지표'이지 판정이 아니다 — 최종 판정은 전문가·습식실험이
  필요함을 항상 명시한다(is_screening_only=True).

계산 지표(전부 공개 표준):
- GC 함량, Shannon 엔트로피(비트)
- CpG 관측/기대비(O/E) — 척추동물 감염 바이러스는 CpG 억제가 흔함, 강한 이탈은 정보
- 최대 이탈 다이뉴클레오타이드 O/E
- CAI(Codon Adaptation Index) — 인간 코돈 사용표 기준 상대 적응도(코딩서열일 때)
- 흔한 제한효소 인식부위 카운트(클로닝 흔적 스크리닝)

참고: CAI는 Sharp & Li 1987; CpG O/E·다이뉴클레오타이드 편향은 표준 서열 통계.
"""
from __future__ import annotations
import math
from collections import Counter

# 표준 유전암호(코돈→아미노산). '*'=종결.
_CODON_AA = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L", "CTT": "L", "CTC": "L",
    "CTA": "L", "CTG": "L", "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V", "TCT": "S", "TCC": "S",
    "TCA": "S", "TCG": "S", "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T", "GCT": "A", "GCC": "A",
    "GCA": "A", "GCG": "A", "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q", "AAT": "N", "AAC": "N",
    "AAA": "K", "AAG": "K", "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W", "CGT": "R", "CGC": "R",
    "CGA": "R", "CGG": "R", "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# 인간(Homo sapiens) 코돈 사용빈도(천분율, Kazusa). CAI 기준표.
_HUMAN_FREQ = {
    "TTT": 17.6, "TTC": 20.3, "TTA": 7.7, "TTG": 12.9, "CTT": 13.2, "CTC": 19.6,
    "CTA": 7.2, "CTG": 39.6, "ATT": 16.0, "ATC": 20.8, "ATA": 7.5, "ATG": 22.0,
    "GTT": 11.0, "GTC": 14.5, "GTA": 7.1, "GTG": 28.1, "TCT": 15.2, "TCC": 17.7,
    "TCA": 12.2, "TCG": 4.4, "CCT": 17.5, "CCC": 19.8, "CCA": 16.9, "CCG": 6.9,
    "ACT": 13.1, "ACC": 18.9, "ACA": 15.1, "ACG": 6.1, "GCT": 18.4, "GCC": 27.7,
    "GCA": 15.8, "GCG": 7.4, "TAT": 12.2, "TAC": 15.3, "TAA": 1.0, "TAG": 0.8,
    "CAT": 10.9, "CAC": 15.1, "CAA": 12.3, "CAG": 34.2, "AAT": 17.0, "AAC": 19.1,
    "AAA": 24.4, "AAG": 31.9, "GAT": 21.8, "GAC": 25.1, "GAA": 29.0, "GAG": 39.6,
    "TGT": 10.6, "TGC": 12.6, "TGA": 1.6, "TGG": 13.2, "CGT": 4.5, "CGC": 10.4,
    "CGA": 6.2, "CGG": 11.4, "AGT": 12.1, "AGC": 19.5, "AGA": 12.2, "AGG": 12.0,
    "GGT": 10.8, "GGC": 22.2, "GGA": 16.5, "GGG": 16.5,
}


def _human_w() -> dict[str, float]:
    """상대 적응도 w = (코돈 빈도)/(동의코돈 그룹 내 최대 빈도). CAI용."""
    by_aa: dict[str, float] = {}
    for codon, aa in _CODON_AA.items():
        if aa == "*":
            continue
        by_aa[aa] = max(by_aa.get(aa, 0.0), _HUMAN_FREQ[codon])
    return {c: _HUMAN_FREQ[c] / by_aa[aa] for c, aa in _CODON_AA.items() if aa != "*"}


_HUMAN_W = _human_w()

# 흔한 클로닝 제한효소 인식부위(팰린드롬/타입IIS). 방어 스크리닝용 카운트만.
_RESTRICTION_SITES = {
    "EcoRI": "GAATTC", "BamHI": "GGATCC", "HindIII": "AAGCTT", "NotI": "GCGGCCGC",
    "XhoI": "CTCGAG", "SalI": "GTCGAC", "BsaI": "GGTCTC", "BsmBI": "CGTCTC",
    "SapI": "GCTCTTC", "PstI": "CTGCAG",
}


def normalize_seq(raw: str) -> str:
    """대문자화, U→T, A/C/G/T만 남김(FASTA 헤더·공백·숫자 제거)."""
    up = (raw or "").upper().replace("U", "T")
    return "".join(c for c in up if c in "ACGT")


def gc_content(seq: str) -> float | None:
    if not seq:
        return None
    return round((seq.count("G") + seq.count("C")) / len(seq), 4)


def shannon_entropy(seq: str) -> float | None:
    """뉴클레오타이드 Shannon 엔트로피(비트, 최대 2.0). 낮으면 반복·저복잡도."""
    if not seq:
        return None
    n = len(seq)
    h = 0.0
    for base in "ACGT":
        p = seq.count(base) / n
        if p > 0:
            h -= p * math.log2(p)
    return round(h, 4)


def _dinuc_oe(seq: str, di: str) -> float | None:
    """다이뉴클레오타이드 관측/기대비. 기대 = f(x)*f(y)*len."""
    if len(seq) < 2:
        return None
    obs = sum(1 for i in range(len(seq) - 1) if seq[i:i + 2] == di)
    x, y = di[0], di[1]
    exp = (seq.count(x) * seq.count(y)) / len(seq)
    if exp == 0:
        return None
    return round(obs / exp, 4)


def cpg_observed_expected(seq: str) -> float | None:
    return _dinuc_oe(seq, "CG")


def max_dinuc_deviation(seq: str) -> dict | None:
    """1.0에서 가장 크게 벗어난 다이뉴클레오타이드 O/E."""
    worst = None
    for a in "ACGT":
        for b in "ACGT":
            oe = _dinuc_oe(seq, a + b)
            if oe is None:
                continue
            dev = abs(oe - 1.0)
            if worst is None or dev > worst["deviation"]:
                worst = {"dinucleotide": a + b, "oe": oe, "deviation": round(dev, 4)}
    return worst


def cai(seq: str) -> dict | None:
    """Codon Adaptation Index(인간 기준). 코딩서열(길이 3의 배수)일 때만.
    Met(ATG)·Trp(TGG)·종결코돈은 관례상 제외. 0~1, 1에 가까울수록 인간 코돈에 최적화."""
    if len(seq) < 6 or len(seq) % 3 != 0:
        return None
    logs = []
    used = 0
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i + 3]
        aa = _CODON_AA.get(codon)
        if aa in (None, "*", "M", "W"):
            continue
        w = _HUMAN_W.get(codon)
        if w and w > 0:
            logs.append(math.log(w))
            used += 1
    if used < 1:
        return None
    return {"cai": round(math.exp(sum(logs) / len(logs)), 4), "codons_scored": used}


def restriction_scan(seq: str) -> dict:
    """흔한 제한효소 인식부위 카운트(양가닥). 클로닝 흔적 방어 스크리닝용."""
    rc = seq.translate(str.maketrans("ACGT", "TGCA"))[::-1]
    counts = {}
    for name, site in _RESTRICTION_SITES.items():
        counts[name] = seq.count(site) + (rc.count(site) if site != _rc(site) else 0)
    return counts


def _rc(s: str) -> str:
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]


# 자연 서열의 대략적 참고범위(휴리스틱) — 강한 이탈만 '주의'로 플래그.
# 하드 판정선이 아니라 우선순위용 참고범위임을 결과에 명시한다.
_REF = {
    "shannon_min": 1.7,        # 이보다 낮으면 저복잡도·반복 의심
    "cpg_oe_low": 0.20,        # 극단적 CpG 억제
    "dinuc_dev_high": 0.60,    # 특정 다이뉴클레오타이드 O/E가 1에서 크게 이탈
}


def screen_sequence(raw: str) -> dict:
    """서열 하나에 대한 방어적 자연스러움 스크리닝. 지표 + 주의 플래그 + 고지."""
    seq = normalize_seq(raw)
    if len(seq) < 30:
        return {"ok": False, "reason": "유효 뉴클레오타이드 30개 미만 — 스크리닝 불가",
                "clean_length": len(seq), "is_screening_only": True}

    ent = shannon_entropy(seq)
    cpg = cpg_observed_expected(seq)
    worst = max_dinuc_deviation(seq)
    cai_res = cai(seq)

    flags: list[dict] = []
    if ent is not None and ent < _REF["shannon_min"]:
        flags.append({"metric": "shannon_entropy", "value": ent,
                      "note": f"엔트로피 {ent}bit < 참고 {_REF['shannon_min']} — 저복잡도·반복 가능성"})
    if cpg is not None and cpg < _REF["cpg_oe_low"]:
        flags.append({"metric": "cpg_oe", "value": cpg,
                      "note": f"CpG O/E {cpg} — 극단적 CpG 억제(합성 약독화 등에서 보고됨)"})
    if worst and worst["deviation"] > _REF["dinuc_dev_high"]:
        flags.append({"metric": "dinucleotide_bias", "value": worst,
                      "note": f"{worst['dinucleotide']} O/E {worst['oe']} — 강한 다이뉴클레오타이드 편향"})

    return {
        "ok": True,
        "clean_length": len(seq),
        "gc_content": gc_content(seq),
        "shannon_entropy_bits": ent,
        "cpg_observed_expected": cpg,
        "max_dinucleotide_deviation": worst,
        "cai_human": cai_res,      # 코딩서열 아니면 None
        "restriction_sites": restriction_scan(seq),
        "flags": flags,
        "flag_count": len(flags),
        # 판정이 아니라 우선순위 도구임을 못박는다.
        "is_screening_only": True,
        "disclaimer": (
            "방어적 스크리닝 지표(공개 표준 통계)로, 서열이 '인공 설계'라는 판정이 아니라 "
            "'추가 검토 우선순위'다. 자연 서열도 참고범위를 벗어날 수 있으며, 최종 판단은 "
            "전문가·계통발생·습식실험 확인이 필요하다."
        ),
        "methods": {
            "cai": "Sharp & Li 1987 (인간 코돈 사용표 기준)",
            "cpg_oe": "관측/기대 다이뉴클레오타이드 비(표준)",
            "reference_ranges": _REF,
        },
    }

"""질병별 실측 역학 파라미터(R0·CFR) — SEIR 캘리브레이션 소스.

배경: Stage 5 SEIR가 원래 flu/novel/severe 3-tier 예시 상수로만 돌아 "모델 추정"에
머물렀다. 여기 문헌 기반 실측치를 두어, 알려진 질병이면 그 병원체의 R0/CFR로
캘리브레이션한다 → "모델 추정"이 "질병별 실측 기반 추정"으로 한 단계 올라간다.

★ 정직성 ★
- 각 값은 공개 문헌의 실측 '추정치'이며 발병·지역·시기마다 편차가 크다. 점추정을
  쓰되 range와 source를 함께 보관해 소비자가 불확실성을 보게 한다.
- 사람간 지속전파가 없는 병원체(니파·MERS·라싸·H5N1)는 R0<1로 둔다 — SEIR가
  대규모 확산을 안 만드는 게 '정직'이다(개별 치명률은 높아도 유행은 제한적).
- 등재 안 된 질병은 lookup이 None → 호출측이 generic 3-tier로 폴백(지어내지 않음).
"""
from __future__ import annotations

# key: 표준 질병명. R0/cfr는 점추정, *_range는 (하한, 상한). cfr는 분율(0.5=50%).
DISEASE_PARAMS = {
    "ebola": {"nm": "에볼라", "R0": 1.8, "R0_range": (1.5, 2.5),
              "cfr": 0.50, "cfr_range": (0.25, 0.90),
              "source": "WHO Ebola factsheet — 발병별 CFR 25~90%, 평균 약 50%",
              "aliases": ("에볼라", "ebola", "ebov")},
    "marburg": {"nm": "마르부르크", "R0": 1.6, "R0_range": (1.2, 2.1),
                "cfr": 0.50, "cfr_range": (0.24, 0.88),
                "source": "WHO Marburg factsheet — CFR 24~88%",
                "aliases": ("마르부르크", "marburg")},
    "nipah": {"nm": "니파바이러스", "R0": 0.5, "R0_range": (0.3, 0.9),
              "cfr": 0.60, "cfr_range": (0.40, 0.75),
              "source": "WHO Nipah — 사람간 전파 제한적(R0<1), 방글라데시 발병 CFR 40~75%",
              "aliases": ("니파", "nipah")},
    "mers": {"nm": "MERS", "R0": 0.7, "R0_range": (0.3, 1.0),
             "cfr": 0.34, "cfr_range": (0.30, 0.40),
             "source": "WHO MERS-CoV — 지속전파 없음(원내 클러스터 위주), CFR ~34%",
             "aliases": ("mers", "메르스", "중동호흡기")},
    "sars": {"nm": "SARS", "R0": 2.75, "R0_range": (2.0, 4.0),
             "cfr": 0.10, "cfr_range": (0.07, 0.15),
             "source": "SARS 2003 WHO — R0 2~4, CFR ~10%",
             "aliases": ("sars", "사스")},
    "covid19": {"nm": "COVID-19", "R0": 2.7, "R0_range": (2.0, 3.5),
                "cfr": 0.015, "cfr_range": (0.005, 0.03),
                "source": "COVID-19 조상주 추정 — R0 2~3.5, 초기 CFR ~1.5%(IFR 더 낮음)",
                "aliases": ("covid", "코로나", "corona", "sars-cov-2", "신종코로나")},
    "influenza_pandemic": {"nm": "판데믹 인플루엔자", "R0": 1.8, "R0_range": (1.5, 2.0),
                           "cfr": 0.025, "cfr_range": (0.01, 0.03),
                           "source": "1918 판데믹 인플루엔자 추정 — R0 ~1.8, CFR ~2.5%",
                           "aliases": ("판데믹 독감", "신종플루", "pandemic influenza", "h1n1")},
    "influenza_seasonal": {"nm": "계절 인플루엔자", "R0": 1.3, "R0_range": (1.1, 1.5),
                           "cfr": 0.001, "cfr_range": (0.0005, 0.002),
                           "source": "계절 인플루엔자 — R0 ~1.3, CFR ~0.1%",
                           "aliases": ("계절 독감", "계절 인플루엔자", "seasonal influenza", "독감", "인플루엔자")},
    "measles": {"nm": "홍역", "R0": 14.0, "R0_range": (12.0, 18.0),
                "cfr": 0.02, "cfr_range": (0.001, 0.05),
                "source": "홍역 — 극고전파(R0 12~18), CFR 미접종·저소득 0.1~5%",
                "aliases": ("홍역", "measles")},
    "mpox": {"nm": "엠폭스", "R0": 1.5, "R0_range": (1.0, 2.0),
             "cfr": 0.03, "cfr_range": (0.001, 0.10),
             "source": "엠폭스 — clade II <1%, clade I(Ib) 1~10%",
             "aliases": ("엠폭스", "mpox", "monkeypox", "원숭이두창")},
    "cholera": {"nm": "콜레라", "R0": 2.0, "R0_range": (1.5, 2.5),
                "cfr": 0.02, "cfr_range": (0.005, 0.05),
                "source": "콜레라 — 치료 시 <1%, 미치료 시 최대 50%",
                "aliases": ("콜레라", "cholera")},
    "lassa": {"nm": "라싸열", "R0": 0.5, "R0_range": (0.2, 0.9),
              "cfr": 0.15, "cfr_range": (0.10, 0.20),
              "source": "라싸열 — 주로 설치류 매개(R0<1), 입원 사례 CFR ~15%",
              "aliases": ("라싸", "lassa")},
    "h5n1": {"nm": "H5N1 조류인플루엔자", "R0": 0.5, "R0_range": (0.1, 1.0),
             "cfr": 0.50, "cfr_range": (0.40, 0.60),
             "source": "H5N1 — 현재 지속적 사람간 전파 없음(R0<1), 스필오버 사례 CFR ~50%",
             "aliases": ("h5n1", "조류인플루엔자", "조류독감", "avian influenza", "고병원성")},
}


def lookup(disease: str | None) -> dict | None:
    """질병명(자유문장 포함)에서 실측 파라미터를 찾는다. 없으면 None(→ generic 폴백)."""
    if not disease:
        return None
    d = disease.lower()
    for key, p in DISEASE_PARAMS.items():
        if any(a.lower() in d for a in p["aliases"]):
            return {"key": key, **{k: v for k, v in p.items() if k != "aliases"}}
    return None


def as_threat_params(p: dict) -> dict:
    """lookup 결과를 SEIR(simulate)가 받는 {R0, cfr, nm} 형태로."""
    return {"R0": p["R0"], "cfr": p["cfr"], "nm": p["nm"]}

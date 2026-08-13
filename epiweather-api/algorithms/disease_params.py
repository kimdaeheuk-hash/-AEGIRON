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

★★ 발병률 상한(max_attack_rate) — 왜 필요한가 ★★
R0가 1을 넘는다고 인구 전체를 태우지 않는다. 에볼라는 R0 1.8이지만 체액 직접접촉
으로만 전파돼 자기제한적이다 — 서아프리카 2014~16년에 약 2,860만 인구권에서 확진
28,652명, 발병률 **0.1%**였다. 그런데 상한 없는 SEIR를 인구 500만에 돌리면 감염
198만(40%)·사망 98.9만이 나온다. 역사상 최대 발병 사망(11,325명)의 **87배**다.

R0는 '발병 초기, 대응 전' 조건에서 측정된 값이라 전체 유행곡선에 그대로 쓰면 안 된다.
그래서 역사적으로 일반화된 유행을 만든 적 없는 병원체엔 발병률 상한을 건다.
값은 역사 실측 발병률에 여유를 둔 판단치이며(측정 상수가 아님) 근거를 함께 적는다.
지속전파가 실제로 일어나는 병원체(홍역·독감·COVID·콜레라·엠폭스)는 상한을 두지 않는다
— 그건 SEIR가 맞는 모델이다.

historical_max_deaths는 '이 모델값이 현실과 얼마나 떨어졌는지' 소비자가 직접 보정할 수
있게 붙인다. 모델값이 이걸 크게 넘으면 호출측이 자동으로 플래그를 단다.
"""
from __future__ import annotations

# key: 표준 질병명. R0/cfr는 점추정, *_range는 (하한, 상한). cfr는 분율(0.5=50%).
DISEASE_PARAMS = {
    "ebola": {"nm": "에볼라", "R0": 1.8, "R0_range": (1.5, 2.5),
              "cfr": 0.50, "cfr_range": (0.25, 0.90),
              "source": "WHO Ebola factsheet — 발병별 CFR 25~90%, 평균 약 50%",
              "max_attack_rate": 0.01, "historical_max_deaths": 11325,
              "cap_basis": "서아프리카 2014~16 WHO 최종집계(확진 28,652·사망 11,325, 인구권 대비 발병률 약 0.1%). 상한 1%는 역사 최악의 약 10배 여유.",
              "aliases": ("에볼라", "ebola", "ebov")},
    "marburg": {"nm": "마르부르크", "R0": 1.6, "R0_range": (1.2, 2.1),
                "cfr": 0.50, "cfr_range": (0.24, 0.88),
                "source": "WHO Marburg factsheet — CFR 24~88%",
              "max_attack_rate": 0.001, "historical_max_deaths": 227,
              "cap_basis": "앙골라 2004~05 최대 발병(사망 227·확진 252). 에볼라보다 발병 규모가 훨씬 작아 상한을 0.1%로 — 0.5%로 뒀더니 모델값이 역사 최대의 34배가 나왔다.",
                "aliases": ("마르부르크", "marburg")},
    "nipah": {"nm": "니파바이러스", "R0": 0.5, "R0_range": (0.3, 0.9),
              "cfr": 0.60, "cfr_range": (0.40, 0.75),
              "source": "WHO Nipah — 사람간 전파 제한적(R0<1), 방글라데시 발병 CFR 40~75%",
              "max_attack_rate": 0.002, "historical_max_deaths": 105,
              "cap_basis": "말레이시아 1998~99 최대(사망 105). 이후 방글라데시 발병은 수십 명 규모, R0<1.",
              "aliases": ("니파", "nipah")},
    "mers": {"nm": "MERS", "R0": 0.7, "R0_range": (0.3, 1.0),
             "cfr": 0.34, "cfr_range": (0.30, 0.40),
             "source": "WHO MERS-CoV — 지속전파 없음(원내 클러스터 위주), CFR ~34%",
              "max_attack_rate": 0.002, "historical_max_deaths": 950,
              "cap_basis": "2012~ 누적 사망 약 950명(전 세계). 원내 클러스터 위주로 지속전파 없음.",
             "aliases": ("mers", "메르스", "중동호흡기")},
    "sars": {"nm": "SARS", "R0": 2.75, "R0_range": (2.0, 4.0),
             "cfr": 0.10, "cfr_range": (0.07, 0.15),
             "source": "SARS 2003 WHO — R0 2~4, CFR ~10%",
              "max_attack_rate": 0.005, "historical_max_deaths": 774,
              "cap_basis": "2003 전 세계 확진 8,096·사망 774로 봉쇄 종식. 지속 유행을 만든 적 없음.",
             "aliases": ("sars", "사스")},
    "covid19": {"nm": "COVID-19", "R0": 2.7, "R0_range": (2.0, 3.5),
                "cfr": 0.015, "cfr_range": (0.005, 0.03),
                "source": "COVID-19 조상주 추정 — R0 2~3.5, 초기 CFR ~1.5%(IFR 더 낮음)",
                "max_attack_rate": None,   # 지속전파 실재 — SEIR가 맞는 모델
                "historical_max_deaths": 7000000,
                "aliases": ("covid", "코로나", "corona", "sars-cov-2", "신종코로나")},
    "influenza_pandemic": {"nm": "판데믹 인플루엔자", "R0": 1.8, "R0_range": (1.5, 2.0),
                           "cfr": 0.025, "cfr_range": (0.01, 0.03),
                           "source": "1918 판데믹 인플루엔자 추정 — R0 ~1.8, CFR ~2.5%",
                "max_attack_rate": None,   # 지속전파 실재 — SEIR가 맞는 모델
                "historical_max_deaths": 50000000,
                           "aliases": ("판데믹 독감", "신종플루", "pandemic influenza", "h1n1")},
    "influenza_seasonal": {"nm": "계절 인플루엔자", "R0": 1.3, "R0_range": (1.1, 1.5),
                           "cfr": 0.001, "cfr_range": (0.0005, 0.002),
                           "source": "계절 인플루엔자 — R0 ~1.3, CFR ~0.1%",
                "max_attack_rate": None,   # 지속전파 실재 — SEIR가 맞는 모델
                "historical_max_deaths": 650000,
                           "aliases": ("계절 독감", "계절 인플루엔자", "seasonal influenza", "독감", "인플루엔자")},
    "measles": {"nm": "홍역", "R0": 14.0, "R0_range": (12.0, 18.0),
                "cfr": 0.02, "cfr_range": (0.001, 0.05),
                "source": "홍역 — 극고전파(R0 12~18), CFR 미접종·저소득 0.1~5%",
                "max_attack_rate": None,   # 지속전파 실재 — SEIR가 맞는 모델
                "historical_max_deaths": 107500,
                "aliases": ("홍역", "measles")},
    "mpox": {"nm": "엠폭스", "R0": 1.5, "R0_range": (1.0, 2.0),
             "cfr": 0.03, "cfr_range": (0.001, 0.10),
             "source": "엠폭스 — clade II <1%, clade I(Ib) 1~10%",
                "max_attack_rate": None,   # 지속전파 실재 — SEIR가 맞는 모델
                "historical_max_deaths": 1000,
             "aliases": ("엠폭스", "mpox", "monkeypox", "원숭이두창")},
    "cholera": {"nm": "콜레라", "R0": 2.0, "R0_range": (1.5, 2.5),
                "cfr": 0.02, "cfr_range": (0.005, 0.05),
                "source": "콜레라 — 치료 시 <1%, 미치료 시 최대 50%",
                # 지속전파는 실재하나 실제 발병률은 제한적 — 아이티 2010~19년 인구 약
                # 1,000만에서 확진 82만(약 8%), 사망 약 1만. 상한 20%는 그 2.5배 여유.
                "max_attack_rate": 0.20,
                "historical_max_deaths": 10000,
                "cap_basis": "아이티 2010~19 최대 유행(확진 약 82만·사망 약 1만, 발병률 약 8%). 상한 없이 돌리니 역사 최대의 18배가 나와 상한을 걸었다.",
                "aliases": ("콜레라", "cholera")},
    "lassa": {"nm": "라싸열", "R0": 0.5, "R0_range": (0.2, 0.9),
              "cfr": 0.15, "cfr_range": (0.10, 0.20),
              "source": "라싸열 — 주로 설치류 매개(R0<1), 입원 사례 CFR ~15%",
              "max_attack_rate": 0.002, "historical_max_deaths": 200,
              "cap_basis": "나이지리아 유행기 연 150~200명 수준. 주로 설치류 매개(R0<1).",
              "aliases": ("라싸", "lassa")},
    "h5n1": {"nm": "H5N1 조류인플루엔자", "R0": 0.5, "R0_range": (0.1, 1.0),
             "cfr": 0.50, "cfr_range": (0.40, 0.60),
             "source": "H5N1 — 현재 지속적 사람간 전파 없음(R0<1), 스필오버 사례 CFR ~50%",
              "max_attack_rate": 0.001, "historical_max_deaths": 470,
              "cap_basis": "2003~ 누적 사망 약 470명. 지속적 사람간 전파 없음.",
             "aliases": ("h5n1", "조류인플루엔자", "조류독감", "avian influenza", "고병원성")},
    # 환경전파형 — 사람 간 전파가 '없다'(오염된 물 에어로졸 흡입). SEIR로 확산곡선을
    # 그리는 게 애초에 안 맞아 R0를 사실상 0(0.1)로 두고 발병률 상한을 매우 작게 건다.
    # 개입 수단도 NPI(격리·거리두기)가 아니라 '오염원(냉각탑·급수) 제거·소독'이다.
    "legionella": {"nm": "레지오넬라증", "R0": 0.1, "R0_range": (0.0, 0.1),
                   "cfr": 0.10, "cfr_range": (0.05, 0.25),
                   "source": "레지오넬라증 — 환경(수인성) 노출형, 사람간 전파 없음. CFR ~10%(원내·치료지연 ~25%)",
                   "max_attack_rate": 0.0005, "historical_max_deaths": 34,
                   "cap_basis": "1976 필라델피아 최초 발병 사망 34명(재향군인병 명명 계기). 냉각탑·급수 오염원 국지 노출이라 지역 발병 규모가 작다.",
                   "transmission_mode": "environmental",
                   "intervention_note": "사람간 전파 없음 — NPI(격리·거리두기) 무의미. 대응은 오염원(냉각탑·대형건물 급수·온수) 조사·소독.",
                   "aliases": ("레지오넬라", "legionella", "재향군인병", "legionnaires")},
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


# 모델 사망자가 역사상 최대의 이 배수를 넘으면 '현실과 동떨어짐'으로 표시한다.
# 상한값 자체가 판단치라 내가 못 잡는 경우가 남는다 — 그때 코드가 잡게 하는 안전망.
IMPLAUSIBLE_RATIO = 10.0


def plausibility(disease_key: str | None, modeled_deaths: float) -> dict:
    """모델 사망자를 역사상 최대 발병과 대조한다.

    왜 필요한가: 상한 없는 SEIR가 에볼라 사망을 98.9만으로 냈다 — 역사상 최대
    발병(11,325명)의 87배다. 파라미터가 실측이어도 적용이 틀리면 이런 값이 나오고,
    경고 문구로는 안 막힌다(87배는 '방향성' 문제가 아니다).
    발병률 상한으로 1차 교정하되, 상한값 자체가 판단치라 놓치는 경우가 남는다.
    여기서 자동으로 대조해 남은 것을 드러낸다."""
    p = DISEASE_PARAMS.get(disease_key or "")
    hist = (p or {}).get("historical_max_deaths")
    if not hist:
        return {"checked": False,
                "reason": "이 질병의 역사적 최대 발병 기준이 없어 대조 불가"}
    ratio = round(modeled_deaths / hist, 1) if hist else None
    implausible = bool(ratio and ratio > IMPLAUSIBLE_RATIO)
    return {
        "checked": True,
        "modeled_deaths": round(modeled_deaths),
        "historical_max_deaths": hist,
        "ratio_vs_historical": ratio,
        "implausible": implausible,
        "note": (
            f"모델값이 역사상 최대 발병의 {ratio}배 — 현실과 동떨어졌을 가능성이 크다. "
            f"발병률 상한(max_attack_rate) 재검토 필요. 이 값을 대외 자료에 쓰지 말 것."
            if implausible else
            f"모델값이 역사상 최대 발병의 {ratio}배 수준 — 최악 시나리오로 설명 가능한 범위."
        ),
    }


def as_threat_params(p: dict) -> dict:
    """lookup 결과를 SEIR(simulate)가 받는 형태로. max_attack_rate를 함께 넘겨야
    접촉 제한 병원체가 인구 전체를 태우지 않는다(빠뜨리면 87배 과대추정 재발)."""
    return {"R0": p["R0"], "cfr": p["cfr"], "nm": p["nm"],
            "max_attack_rate": p.get("max_attack_rate")}

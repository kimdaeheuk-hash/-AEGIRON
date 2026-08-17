"""KDCA 국내 법정감염병 — 질병별 개별 급증 탐지.

배경: 원래 KDCA는 감시목록(9종)에 있는 것만 수집하고, 다시 그걸 '하나의 총합'으로
합산해 신호로 썼다. 이러면 두 가지 문제가 생긴다:
  ① 목록 밖 질병(레지오넬라 등)은 통째로 유실된다.
  ② 목록을 넓혀 상재성 고volume 질병(수두·결핵 등)을 총합에 넣으면, 총합이 그것들로
     뒤덮여 신종·위험 질병의 급증이 파묻힌다.
그래서 '전부 수집하되 질병별로 자기 기준선과 비교'한다. 레지오넬라가 평소 5건인데
이번 주 40건이면 — 전체 총합이 평온해도 그 질병만의 급증(8배)으로 잡힌다. 이러면
88종이든 전부든 안전하게 넓혀도 된다(각자 판단되니까).

집계 신호(kdca_weekly_total)는 여전히 쓰되, 상재성 질병에 안 휩쓸리게 '위험군만'
합산한다(KDCA_NOTABLE). 위험군 밖 질병은 개별 급증 탐지로만 본다.

★ 정직성 ★
- 급증은 '자기 최근 기준선 대비'다 — 절대 건수가 아니라 상대 변화라서 질병마다
  규모가 달라도 공평하게 잡힌다. 기준선이 0이면 from_zero로 표시(비율 억지 계산 안 함).
- 표본이 2주 미만이면 판단 보류(급증 아님).
"""
from __future__ import annotations

# 위험군(고위험·대유행 잠재 + 국내 집단발병 실적) — '집계 총합'에 넣는 대상.
# 그 밖의 법정감염병은 전부 수집하되 개별 급증으로만 감시(총합 오염 방지).
KDCA_NOTABLE = [
    # 고위험·대유행 잠재
    "중동호흡기증후군(MERS)", "중증급성호흡기증후군(SARS)", "에볼라바이러스병",
    "마버그열", "라싸열", "크리미안콩고출혈열", "신종인플루엔자", "신종감염병증후군",
    "두창", "페스트", "탄저", "보툴리눔독소증", "야토병",
    # 호흡기·백신예방
    "홍역", "수두", "유행성이하선염", "백일해", "풍진", "폴리오", "디프테리아",
    "결핵", "수막구균 감염증", "성홍열",
    # 수인성·식품매개 (레지오넬라 포함 — 놓쳤던 그 구멍)
    "콜레라", "장티푸스", "파라티푸스", "세균성이질", "장출혈성대장균감염증",
    "A형간염", "레지오넬라증",
    # 매개체·인수공통
    "말라리아", "뎅기열", "지카바이러스 감염증", "일본뇌염", "쯔쯔가무시증",
    "신증후군출혈열", "중증열성혈소판감소증후군(SFTS)", "큐열", "브루셀라증",
    "비브리오패혈증",
]

SPIKE_MIN_COUNT = 5        # 이 미만이면 소수 변동이라 급증으로 안 봄
SPIKE_RATIO_THRESHOLD = 2.0  # 최근 기준선의 2배 이상이면 급증
_FROM_ZERO_RATIO = 1_000_000.0  # 0→발생을 신호값으로 환산할 때 쓰는 큰 수(JSON은 inf 불가)


def disease_spikes(kdca_weekly: dict | None, notable: set | None = None,
                   min_count: float = SPIKE_MIN_COUNT,
                   ratio_threshold: float = SPIKE_RATIO_THRESHOLD,
                   limit: int = 40) -> list[dict]:
    """질병별로 '최근 주 vs 이전 주들 평균'을 비교해 급증을 잡는다.
    전체 총합이 평온해도 단일 질병 급증(레지오넬라 등)을 개별로 드러낸다."""
    notable = notable if notable is not None else set(KDCA_NOTABLE)
    out: list[dict] = []
    for disease, weekmap in (kdca_weekly or {}).items():
        weeks = sorted(weekmap)
        if len(weeks) < 2:
            continue                      # 기준선 없음 → 판단 보류
        latest = float(weekmap[weeks[-1]])
        prior = [float(weekmap[w]) for w in weeks[:-1]]
        baseline = sum(prior) / len(prior) if prior else 0.0
        if latest < min_count:
            continue
        if baseline > 0:
            ratio = latest / baseline
            from_zero = False
        elif latest > 0:
            ratio = None                  # 0에서 튀어오름 — 비율 억지 계산 안 함
            from_zero = True
        else:
            continue
        if from_zero or ratio >= ratio_threshold:
            out.append({
                "disease": disease,
                "latest_week": weeks[-1],
                "latest_count": latest,
                "baseline_mean": round(baseline, 2),
                "ratio": (None if from_zero else round(ratio, 2)),
                "from_zero": from_zero,
                "is_notable": disease in notable,
            })
    # 위험군 우선, 그다음 급증 강도 내림차순(0→발생은 최상위로).
    out.sort(key=lambda s: (s["is_notable"],
                            _FROM_ZERO_RATIO if s["from_zero"] else s["ratio"]),
             reverse=True)
    return out[:limit]


def notable_latest_total(kdca_weekly: dict | None, notable: set | None = None) -> float | None:
    """집계 총합 — 위험군(KDCA_NOTABLE)만 최근 주 합산. 상재성 질병이 총합을
    오염시키지 않게 한다(기존 kdca_weekly_total 기준선을 지킴)."""
    if not kdca_weekly:
        return None
    notable = notable if notable is not None else set(KDCA_NOTABLE)
    weeks = {w for wm in kdca_weekly.values() for w in wm}
    if not weeks:
        return None
    latest = max(weeks)
    return float(sum(wm.get(latest, 0) for d, wm in kdca_weekly.items() if d in notable))


def max_spike_signal(spikes: list[dict] | None) -> float | None:
    """신호 메트릭용 — 가장 강한 질병별 급증 강도(0→발생은 큰 수로 환산)."""
    if not spikes:
        return None
    vals = [_FROM_ZERO_RATIO if s["from_zero"] else s["ratio"] for s in spikes]
    return max(vals) if vals else None


def parse_kdca_count(raw) -> int | None:
    """KDCA resultVal → 건수. 파싱 못 하면 None(= '값 없음', 0과 구분).

    KDCA API는 건수를 문자열로 주는데 형식이 한 가지가 아니다:
      - 1000 이상이면 천단위 쉼표가 붙는다("1,296"). int()가 그대로 터진다.
      - 아직 감시 대상이 아닌 질병·기간은 숫자가 아니라 "-"로 온다.
    '전부 수집'(allowlist 폐지) 이후로는 어떤 질병이 들어올지 미리 알 수 없으므로,
    한 항목이 이상해도 그 항목만 버리고 나머지 질병은 반드시 살려야 한다 —
    예전엔 여기서 터지면 그 주 KDCA 수집이 통째로 없어졌다(2026-08-13~17 실제 발생).

    0이 아니라 None을 돌려주는 이유: "이번 주 0건 신고"와 "값을 못 읽었다"는 전혀
    다른 사실이다. 후자를 0으로 적으면 없는 안전을 지어내는 셈이 된다.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    text = str(raw).strip().replace(",", "").replace(" ", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return None

"""빙하 산맥 지역 — 홍수가 어디서 왔는지 맥락을 붙인다 (2026-09-01).

## 왜 만들었나

2026-08-26 네팔 Rasuwa 홍수(사망 359명+·실종 1,000명+, 히말라야 한 세대 만의
최악)를 조사하다 나왔다. 처음엔 빙하호 붕괴(GLOF)로 보도됐지만 위성영상과
지진계 분석은 다른 것을 가리켰다:

    랑탕리룽 북면에서 **빙하가 붕괴**했다. 사고 당시 날씨는 맑았다.
    얼음·암반 파괴 → 암석·빙하 눈사태 → 토석류 → 하천 일시 폐색 →
    불안정한 천연댐 붕괴 → 홍수. **연쇄 재해**였다.

그리고 이건 히말라야만의 일이 아니다. 전 세계 **1,500만 명**이 빙하 홍수에
노출돼 있고 그중 절반 이상이 인도·파키스탄·페루·중국에 산다. 850~2022년
27개국에서 3,151건이 기록됐고 20세기에 6배 늘었다.
(Nature Communications 2023, Taylor et al. — "Glacial lake outburst floods
threaten millions globally")

## ★ 이 파일이 하지 않는 것 ★

**GLOF 를 예측하지 않는다.** 그건 빙하호에 수위 센서를 박고 위성으로 보는
일이고(인도 시킴, 중앙아시아 GLOFCA 등), 우리 데이터로는 못 한다. 무료 실시간
빙하 API 는 조사 결과 **존재하지 않는다.**

**잠복기 창을 건드리지 않는다.** 콜레라 잠복기는 홍수의 원인이 빙하든 몬순이든
같다. 그건 문헌값이고 여기서 손댈 것이 아니다.

## 그럼 무엇을 하나 — 맥락을 붙인다

GDACS 는 빙하 붕괴 홍수도 그냥 `FL`(홍수)로 준다(네팔·중국 건을 실측 확인).
즉 **우리는 이미 그 사건을 받고 있었다.** 모르는 것은 그게 어디서 왔는지다.

그 차이가 실제로 중요하다:

    | | 몬순 홍수 | 빙하 홍수 |
    | 예고 | 비가 온다 | **맑은 날 갑자기** |
    | 위치 | 인구 밀집 저지대 | **고산 오지** |
    | 의료 접근 | 있음 | **부족** |
    | 보고 속도 | 빠름 | **느림** |

**보고가 느린 지역일수록 낮은 문턱으로 봐야 할 이유가 크다.** 지금 감시창은
둘을 구분하지 못한다. 이 파일이 그 구분을 준다.

## 표의 성격

빙하 산맥이 있느냐는 **지리적 사실**이라 잘 안 변한다(빙하가 물러나도 산맥은
남고, 물러나는 중에 오히려 호수가 늘어 위험이 커진다). 그래서 국경표
(`country_borders.py`)와 같은 방식으로 정적 표에 적는다.

노출 등급은 위 Nature Communications 연구의 "1,500만 중 절반 이상이 인도·
파키스탄·페루·중국" 을 근거로 한다. **이건 인구 노출 규모이지 발생 확률이
아니다** — 확률은 우리가 알 수 없다.
"""
from __future__ import annotations

ExposureTier = str  # "highest" | "high" | "moderate"

# 근거: 위 연구가 지목한 네 나라를 highest 로 둔다(1,500만 중 절반 이상).
# 나머지는 빙하 산맥의 규모와 하류 인구를 보고 high/moderate 로 나눴다 —
# ★ 이 구분은 순위이지 측정값이 아니다 ★ 대외 자료에 확률처럼 인용하지 말 것.
GLACIER_REGIONS: dict[str, dict] = {
    # ── 고산 아시아 — 세계 최대 집중 지역 ─────────────────────────────
    "IND": {"ranges": ["히말라야", "카라코람"], "exposure": "highest"},
    "PAK": {"ranges": ["카라코람", "힌두쿠시", "히말라야"], "exposure": "highest"},
    "CHN": {"ranges": ["히말라야", "카라코람", "쿤룬", "톈산"], "exposure": "highest"},
    "NPL": {"ranges": ["히말라야"], "exposure": "high"},
    "BTN": {"ranges": ["히말라야"], "exposure": "high"},
    "AFG": {"ranges": ["힌두쿠시", "파미르"], "exposure": "high"},
    "TJK": {"ranges": ["파미르"], "exposure": "high"},
    "KGZ": {"ranges": ["톈산", "파미르"], "exposure": "high"},
    "KAZ": {"ranges": ["톈산"], "exposure": "moderate"},
    "UZB": {"ranges": ["톈산"], "exposure": "moderate"},

    # ── 안데스 — 히말라야와 맞먹는 위험인데 연구가 거의 없다 ────────────
    "PER": {"ranges": ["안데스(코르디예라 블랑카)"], "exposure": "highest"},
    "BOL": {"ranges": ["안데스"], "exposure": "high"},
    "CHL": {"ranges": ["안데스", "파타고니아 빙원"], "exposure": "high"},
    "ARG": {"ranges": ["안데스", "파타고니아 빙원"], "exposure": "high"},
    "ECU": {"ranges": ["안데스"], "exposure": "moderate"},
    "COL": {"ranges": ["안데스"], "exposure": "moderate"},

    # ── 캅카스 ────────────────────────────────────────────────────────
    "GEO": {"ranges": ["캅카스"], "exposure": "moderate"},
    "RUS": {"ranges": ["캅카스", "알타이", "캄차카"], "exposure": "moderate"},

    # ── 알프스 ────────────────────────────────────────────────────────
    "CHE": {"ranges": ["알프스"], "exposure": "moderate"},
    "ITA": {"ranges": ["알프스"], "exposure": "moderate"},
    "FRA": {"ranges": ["알프스"], "exposure": "moderate"},
    "AUT": {"ranges": ["알프스"], "exposure": "moderate"},

    # ── 북유럽·아이슬란드 ─────────────────────────────────────────────
    # 아이슬란드는 화산 아래 빙하가 있어 분출 때 융빙홍수(jökulhlaup)가 난다.
    "ISL": {"ranges": ["빙하(화산성 융빙홍수)"], "exposure": "moderate"},
    "NOR": {"ranges": ["스칸디나비아 빙하"], "exposure": "moderate"},

    # ── 북미 ──────────────────────────────────────────────────────────
    "USA": {"ranges": ["알래스카", "캐스케이드", "로키"], "exposure": "moderate"},
    "CAN": {"ranges": ["코스트산맥", "로키", "북극권"], "exposure": "moderate"},

    # ── 오세아니아 ────────────────────────────────────────────────────
    "NZL": {"ranges": ["서던알프스"], "exposure": "moderate"},
}

_TIER_ORDER = {"highest": 3, "high": 2, "moderate": 1}


def is_glacier_region(iso3: str) -> bool:
    """빙하 산맥이 있는 나라인가. 모르는 코드는 False — 추측하지 않는다."""
    return bool(iso3) and iso3.strip().upper() in GLACIER_REGIONS


def glacier_context(iso3: str) -> dict | None:
    """그 나라의 빙하 맥락. 없으면 None 이지 빈 dict 가 아니다.

    ★ 여기 담기는 것은 '어디인가' 이지 '위험이 얼마인가' 가 아니다 ★
    확률을 낼 수 없으므로 내지 않는다. 대신 **왜 이 맥락이 중요한지**를
    같이 실어 보낸다 — 숫자만 떨어져 나가면 보고서에서 오독된다.
    """
    entry = GLACIER_REGIONS.get((iso3 or "").strip().upper())
    if not entry:
        return None
    return {
        "glacier_region": True,
        "ranges": entry["ranges"],
        "exposure_tier": entry["exposure"],
        "why_it_matters": (
            "빙하 기원 홍수는 비 없이 맑은 날 갑자기 오고, 고산 오지를 치며, "
            "의료 접근이 나빠 발병 보고가 느리다. 보고가 느린 지역일수록 "
            "낮은 문턱으로 볼 이유가 크다."
        ),
        "not_a_prediction": (
            "이 표시는 '빙하 홍수였다'는 판정이 아니라 '빙하 산맥이 있는 "
            "나라에서 난 홍수'라는 지리적 사실이다. 원인 규명은 위성·지진계 "
            "분석의 몫이고 우리는 그걸 하지 않는다."
        ),
    }


def regions_by_tier(tier: ExposureTier) -> list[str]:
    """등급별 나라 목록. 대외 자료가 커버리지를 말할 때 쓴다."""
    return sorted(k for k, v in GLACIER_REGIONS.items() if v["exposure"] == tier)


def coverage_summary() -> dict:
    """무엇을 덮고 무엇을 못 하는지 함께 낸다."""
    return {
        "countries": len(GLACIER_REGIONS),
        "by_tier": {t: regions_by_tier(t) for t in ("highest", "high", "moderate")},
        "basis": (
            "Nature Communications 2023 — 전 세계 1,500만 명이 빙하호 붕괴 홍수에 "
            "노출, 그중 절반 이상이 인도·파키스탄·페루·중국. 850~2022년 27개국 "
            "3,151건 기록, 20세기에 6배 증가."
        ),
        "limits": [
            "GLOF 를 예측하지 않는다 — 무료 실시간 빙하 API 가 존재하지 않는다.",
            "노출 등급은 인구 규모 순위이지 발생 확률이 아니다.",
            "이 나라의 홍수가 빙하 기원이라는 판정이 아니라, 빙하 산맥이 있는 "
            "나라에서 났다는 지리적 사실이다.",
        ],
    }

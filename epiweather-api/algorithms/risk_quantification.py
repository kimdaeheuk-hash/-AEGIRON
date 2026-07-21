"""팬데믹 리스크 계량화 — 인수인계서 확장(㉓, "빈 시장" 통합).

시장 지형: BlueDot은 "탐지"(어디서 무슨 일이 나는가)를, Metabiota는 "계량화"
(그 리스크를 보험·재보험이 가격 매길 수 있게 숫자화)를 판다. 아이기론은
탐지·정직성·트랙레코드는 갖췄지만 "보험·금융이 쓸 수 있는 비교가능한 정량
지표"가 없었다 — 이 모듈이 그 빈 곳을 메운다.

★ 정직성 경계선(이 프로젝트의 핵심 원칙과 직결) ★
"이 나라에서 N% 확률로 팬데믹 발생" 같은 절대 확률은 만들지 않는다 — 그런
확률을 뒷받침할 실제 기저율(base rate) 데이터가 아직 없어서, 만들면 근거
없는 숫자를 보험사에 파는 셈이 된다. 대신:
  - 노출 지수(exposure_index, 0~100): 이미 수집된 실제 신호를 합성한 "상대
    비교용" 지표. 절대 확률이 아님(is_probability=False로 못박음).
  - 상대 백분위(percentile): 지금 전체 국가 중 어디쯤인가 — 순위는 정직하게 계산 가능.
  - 실증 근거(empirical_basis): 실제 이력 백테스트(㉑)로 검증된 선행탐지
    사례 수 — 이 지표가 얼마나 실측에 뿌리내렸는지 소비자가 직접 판단하도록 공개.
가중치(0.45/0.35/0.20)는 실증 보정된 값이 아니라 "정책적 가중치"임을 명시하고
(weights_calibrated=False), 구성요소를 전부 노출해 소비자가 재가중할 수 있게 한다.
"""
from __future__ import annotations

from .country_risk import (
    compute_country_risk, _vulnerability_components, COUNTRIES, discovered_tier2_countries,
)

# 정책적 가중치(실증 보정 아님 — weights_calibrated=False로 항상 명시).
# 근거(정성적): 지금 신호가 실제로 뜨고 있는가(신호강도)가 가장 강한 즉시성
# 동인이라 최고 가중, 터졌을 때 얼마나 나쁜가(취약성)가 그다음, 얼마나 멀리
# 퍼지는가(확산 잠재력=공항연결성)가 세 번째.
W_SIGNAL = 0.45
W_VULNERABILITY = 0.35
W_SPREAD = 0.20


def quantify_country_exposure(country_id: str) -> dict:
    """단일 국가의 노출 지수 — compute_country_risk(㉑까지 쌓인 실제 신호·취약성)를
    재사용해 합성. country_id가 Tier-1/Tier-2 어디에도 근거가 없으면 KeyError."""
    cr = compute_country_risk(country_id)  # Tier-2 신호 없으면 여기서 KeyError

    raw = cr["raw_score"]  # 0~100(순수 이상도, GAI와 동일 척도) 또는 None
    signal_pressure = round(min(raw, 100) / 100, 3) if raw is not None else 0.0
    vuln = cr["vulnerability_index"]  # 0~1

    comps, _ = _vulnerability_components(country_id)
    spread = comps["airport_connectivity"]  # 0~1

    exposure = round(
        100 * (W_SIGNAL * signal_pressure + W_VULNERABILITY * vuln + W_SPREAD * spread),
        1,
    )

    return {
        "country": country_id,
        "name": cr["name"],
        "coverage_tier": cr["coverage_tier"],
        "exposure_index": exposure,
        "components": {
            "signal_pressure": signal_pressure,   # 지금 신호가 얼마나 강한가(0~1)
            "vulnerability": vuln,                 # 터지면 얼마나 나쁜가(0~1)
            "spread_potential": spread,            # 얼마나 멀리 퍼지는가(0~1, 공항연결성)
        },
        "weights": {"signal": W_SIGNAL, "vulnerability": W_VULNERABILITY, "spread": W_SPREAD},
        "has_active_signal": raw is not None,
        # 소비자(특히 보험·금융)에게 "이건 절대 확률이 아니다"를 못박는 플래그.
        "is_probability": False,
        "weights_calibrated": False,   # 가중치는 정책값이지 실증 보정값이 아님
        "vulnerability_source": cr["vulnerability_source"],  # real_data | seed_fallback
    }


def quantify_portfolio() -> dict:
    """전체 국가(Tier-1 + 신호 있는 Tier-2)의 노출 지수를 계산하고, 상대 백분위와
    실증 근거를 붙여 반환 — 재보험사가 국가 포트폴리오를 비교·랭킹하는 용도."""
    ids = set(COUNTRIES) | discovered_tier2_countries()
    entries = []
    for cid in ids:
        try:
            entries.append(quantify_country_exposure(cid))
        except KeyError:
            continue  # Tier-2 후보인데 실제 신호가 사라진 경우 — 억지로 넣지 않음

    entries.sort(key=lambda e: -e["exposure_index"])

    # 상대 백분위: 노출 지수 기준으로 "이보다 낮거나 같은 국가 비율"(0~100).
    n = len(entries)
    for rank, e in enumerate(entries):
        # rank 0 = 최고 노출 → 백분위 100에 가깝게
        e["percentile"] = round(100 * (n - rank) / n, 1) if n else None

    # 실증 근거: 실제 이력 백테스트로 "선행탐지"가 검증된 사례 수 — 이 지수
    # 전체가 얼마나 실측에 뿌리내렸는지 정직하게 공개(순환 임포트 피해 지연 임포트).
    from .historical_backtest import backtest_all_known_events
    bt = backtest_all_known_events()

    return {
        "countries": entries,
        "empirical_basis": {
            "verified_lead_time_cases": bt["summary"]["events_with_verified_lead_time"],
            "mean_observed_lead_days": bt["summary"]["mean_lead_days"],
            "note": "노출 지수는 상대 비교용 모델 지표이며 절대 발생 확률이 아님. "
                    "위 사례 수가 이 모델의 실측 근거 규모 — 표본이 작을수록 보수적으로 해석할 것.",
        },
        "disclaimer": "exposure_index는 정책적 가중치로 합성한 상대 지표다. "
                      "보험·금융용 실제 요율 산정에 쓰려면 자체 기저율로 재보정이 필요하다.",
    }

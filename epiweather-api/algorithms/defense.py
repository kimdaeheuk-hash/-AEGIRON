"""Stage 5: SEIR 방어 시뮬레이션 — 표준 SEIR + 시간가변 개입."""
from __future__ import annotations
from .common import clamp, THREAT, PRESETS

N = 5_000_000
HOSP_CAP = 12_000
HOSP_FRAC = 0.08


def simulate(lev: dict, threat: str, days: int = 200, params: dict | None = None) -> dict:
    """
    SEIR + 시간가변 Reff.
    σ=1/4(잠복기 4일), γ=1/7(감염기 7일).
    개입 ramp-up 14일에 걸쳐 점진 적용 (21일 이후부터).
    params가 주어지면 그 {R0, cfr}로 캘리브레이션(질병별 실측), 없으면 generic tier.
    """
    sp = params or THREAT[threat]

    # ★ 도달 가능 인구(reachable) ★
    # R0가 1을 넘는다고 인구 전체를 태우지 않는다. 에볼라는 R0 1.8이지만 체액
    # 직접접촉으로만 퍼져 자기제한적이다 — 상한 없이 500만에 돌리면 사망 98.9만이
    # 나와 역사상 최대 발병(11,325명)의 87배가 된다. R0는 '초기·대응 전' 값이라
    # 전체 유행곡선에 그대로 쓰면 안 되기 때문이다.
    # 그래서 접촉 제한 병원체는 '실제로 닿을 수 있는 인구'만 감수성 집단으로 두고,
    # 혼합 분모도 그 값을 쓴다(인구 전체와 섞이지 않는다는 뜻).
    # 지속전파가 실재하는 병원체(홍역·독감·COVID 등)는 상한이 None이라 N 그대로 —
    # 그건 SEIR가 맞는 모델이다. 근거는 disease_params.max_attack_rate 참조.
    cap = (params or {}).get("max_attack_rate")
    reachable = float(N) if not cap else max(1000.0, N * float(cap))

    s, e, i, d = reachable - 21, 20.0, 1.0, 0.0
    sig, gam = 1 / 4, 1 / 7
    iv = 21

    peak, p_day, ofd = 0.0, 0, 0
    I_curve: list[float] = []

    for t in range(days):
        ramp = clamp((t - iv) / 14, 0, 1)
        npi = (lev.get("quar", 0) + lev.get("dist", 0)) * ramp
        vax = min(lev.get("vax", 0), max(0, t - iv) * lev.get("vaxsp", 0))
        ve = lev.get("vuln", 0) * ramp * 0.25

        Reff = sp["R0"] * (1 - clamp(npi, 0, 0.85)) * (1 - vax * 0.85) * (1 - ve * 0.3)
        beta = Reff * gam
        nE = beta * s * i / reachable
        nI = sig * e
        nR = gam * i
        ecfr = sp["cfr"] * (1 - lev.get("anti", 0) * 0.4 * ramp) * (1 - ve)

        s -= nE
        e += nE - nI
        i += nI - nR
        d += nR * ecfr
        s = max(0, s)
        e = max(0, e)
        i = max(0, i)

        I_curve.append(i)
        if i > peak:
            peak = i
            p_day = t
        if i * HOSP_FRAC > HOSP_CAP:
            ofd += 1

    return {
        "I_curve": [round(v) for v in I_curve],
        "peak_infected": round(peak),
        "peak_day": p_day,
        "total_deaths": round(d),
        "hosp_overflow_days": ofd,
        # 어떤 인구를 대상으로 돈 결과인지 드러낸다 — 상한이 걸렸는지 소비자가 알아야 한다.
        "population_modeled": round(reachable),
        "attack_rate_capped": bool(cap),
    }


def run_defense(lev: dict, threat: str, params: dict | None = None) -> dict:
    """개입 있는 시나리오 vs 무대응 비교. params로 질병별 실측 R0/CFR 캘리브레이션 가능."""
    result = simulate(lev, threat, params=params)
    baseline = simulate(PRESETS["none"], threat, params=params)

    saved = max(0, baseline["total_deaths"] - result["total_deaths"])
    saved_pct = round(saved / baseline["total_deaths"] * 100) if baseline["total_deaths"] > 0 else 0

    sp = params or THREAT[threat]
    ramp_lev = (lev.get("quar", 0) + lev.get("dist", 0))
    vax_eff = lev.get("vax", 0) * 0.85
    vuln_eff = lev.get("vuln", 0) * 0.25 * 0.3
    rt = sp["R0"] * (1 - clamp(ramp_lev, 0, 0.85)) * (1 - vax_eff) * (1 - vuln_eff)

    return {
        "threat": threat,
        "levers": lev,
        "result": result,
        "baseline_no_intervention": baseline,
        "saved_lives": saved,
        "saved_pct": saved_pct,
        "effective_rt": round(rt, 3),
        "transmission_controlled": rt < 1,
    }

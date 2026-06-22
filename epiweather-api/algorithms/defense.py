"""Stage 5: SEIR 방어 시뮬레이션 — 표준 SEIR + 시간가변 개입."""
from __future__ import annotations
from .common import clamp, THREAT, PRESETS

N = 5_000_000
HOSP_CAP = 12_000
HOSP_FRAC = 0.08


def simulate(lev: dict, threat: str, days: int = 200) -> dict:
    """
    SEIR + 시간가변 Reff.
    σ=1/4(잠복기 4일), γ=1/7(감염기 7일).
    개입 ramp-up 14일에 걸쳐 점진 적용 (21일 이후부터).
    """
    sp = THREAT[threat]
    s, e, i, d = float(N - 21), 20.0, 1.0, 0.0
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
        nE = beta * s * i / N
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
    }


def run_defense(lev: dict, threat: str) -> dict:
    """개입 있는 시나리오 vs 무대응 비교."""
    result = simulate(lev, threat)
    baseline = simulate(PRESETS["none"], threat)

    saved = max(0, baseline["total_deaths"] - result["total_deaths"])
    saved_pct = round(saved / baseline["total_deaths"] * 100) if baseline["total_deaths"] > 0 else 0

    sp = THREAT[threat]
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

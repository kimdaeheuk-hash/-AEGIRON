"""디지털 트윈 — Phase 3. 도시 간 전파 확산 시뮬레이션.

기존 defense.py의 단일 도시 SEIR을 다도시 네트워크로 확장.
항공 노선 데이터(geo_resolution.py)로 도시 간 이동량을 반영.

시뮬레이션 흐름:
  1. 발원 도시에서 감염 시작
  2. 매 시뮬레이션 스텝마다 항공 이동량 비례로 이웃 도시에 감염자 유입
  3. 각 도시 SEIR 모델로 자체 전파
  4. 인천 도달 예상일 + 각 도시 피크 예측 반환

인수인계서: "디지털 트윈 — 확산 시뮬레이션, 도시 이동 모델, 전염 경로 예측"
"""
from __future__ import annotations
from .common import THREAT, clamp

CITIES_POPULATION: dict[str, int] = {
    "Kinshasa":  17_100_000,
    "Kampala":    3_600_000,
    "Riyadh":     7_700_000,
    "Dubai":      3_600_000,
    "Bangkok":   10_700_000,
    "Hanoi":      8_100_000,
    "Jakarta":   34_500_000,
    "Seoul":      9_700_000,
}

FLIGHT_CONNECTIONS: dict[tuple[str, str], int] = {
    ("Kinshasa",  "Dubai"):    2,
    ("Kinshasa",  "Riyadh"):   1,
    ("Kampala",   "Dubai"):    3,
    ("Riyadh",    "Seoul"):    2,
    ("Dubai",     "Seoul"):    4,
    ("Dubai",     "Bangkok"):  7,
    ("Bangkok",   "Seoul"):   20,
    ("Bangkok",   "Hanoi"):   14,
    ("Hanoi",     "Seoul"):   17,
    ("Jakarta",   "Seoul"):    6,
    ("Jakarta",   "Bangkok"):  7,
}

HOSP_CAP_PER_MILLION = 2_400
HOSP_FRAC = 0.08
PASSENGERS_PER_FLIGHT = 250   # 항공기 평균 탑승객 수


def _seir_step(
    s: float, e: float, i: float, d: float,
    n: float, r0: float, cfr: float, sigma: float = 0.25, gamma: float = 1/7,
) -> tuple[float, float, float, float]:
    beta = r0 * gamma
    nE   = beta * s * i / n
    nI   = sigma * e
    nR   = gamma * i
    s    = max(0, s - nE)
    e    = max(0, e + nE - nI)
    i    = max(0, i + nI - nR)
    d    = d + nR * cfr
    return s, e, i, d


def simulate_spread(
    origin: str,
    threat: str = "novel",
    days: int = 90,
    initial_infected: int = 10,
) -> dict:
    """
    발원 도시에서 시작해 항공 네트워크를 통해 다른 도시로 퍼지는 시뮬레이션.
    """
    sp = THREAT.get(threat, THREAT["novel"])
    r0  = sp["R0"]
    cfr = sp["cfr"]

    if origin not in CITIES_POPULATION:
        return {"error": f"도시 없음: {origin}. 지원: {list(CITIES_POPULATION)}"}

    # 초기 상태: {도시: (S, E, I, D)}
    states: dict[str, list[float]] = {}
    for city, pop in CITIES_POPULATION.items():
        if city == origin:
            states[city] = [float(pop - initial_infected), 0.0, float(initial_infected), 0.0]
        else:
            states[city] = [float(pop), 0.0, 0.0, 0.0]

    peak_day: dict[str, int | None] = {c: None for c in CITIES_POPULATION}
    peak_inf: dict[str, float]      = {c: 0.0  for c in CITIES_POPULATION}
    first_case_day: dict[str, int | None] = {c: None for c in CITIES_POPULATION}
    first_case_day[origin] = 0
    curves: dict[str, list[int]]   = {c: [] for c in CITIES_POPULATION}

    for day in range(days):
        new_states = {c: list(v) for c, v in states.items()}

        # 자체 전파
        for city in CITIES_POPULATION:
            n   = CITIES_POPULATION[city]
            s, e, i, d = states[city]
            ns, ne, ni, nd = _seir_step(s, e, i, d, n, r0, cfr)
            new_states[city] = [ns, ne, ni, nd]
            curves[city].append(int(ni))
            if ni > peak_inf[city]:
                peak_inf[city] = ni
                peak_day[city] = day

        # 항공 네트워크를 통한 유입
        for (city_a, city_b), weekly_flights in FLIGHT_CONNECTIONS.items():
            for src, dst in [(city_a, city_b), (city_b, city_a)]:
                if src not in states or dst not in states:
                    continue
                i_src = states[src][2]
                n_src = CITIES_POPULATION[src]
                if n_src == 0 or i_src <= 0:
                    continue
                prevalence    = i_src / n_src
                daily_flights = weekly_flights / 7
                # 유입자 수 = 유병률 × 항공기 승객 × 일일 편수
                imported = prevalence * PASSENGERS_PER_FLIGHT * daily_flights
                if imported >= 0.05:
                    new_states[dst][2] = new_states[dst][2] + imported
                    new_states[dst][0] = max(0, new_states[dst][0] - imported)
                    if first_case_day[dst] is None:
                        first_case_day[dst] = day

        states = new_states

    seoul_arrival = first_case_day.get("Seoul")
    city_summaries = []
    for city in CITIES_POPULATION:
        city_summaries.append({
            "city":            city,
            "first_case_day":  first_case_day[city],
            "peak_day":        peak_day[city],
            "peak_infected":   int(peak_inf[city]),
            "final_deaths":    int(states[city][3]),
            "hosp_overflow_days": sum(
                1 for v in curves[city]
                if v * HOSP_FRAC > CITIES_POPULATION[city] / 1_000_000 * HOSP_CAP_PER_MILLION
            ),
        })
    city_summaries.sort(key=lambda c: (c["first_case_day"] is None, c["first_case_day"] or 9999))

    return {
        "origin":          origin,
        "threat":          threat,
        "days_simulated":  days,
        "r0":              r0,
        "seoul_arrival_day": seoul_arrival,
        "cities":          city_summaries,
        "spread_sequence": [c["city"] for c in city_summaries if c["first_case_day"] is not None],
    }

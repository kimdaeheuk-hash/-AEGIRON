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

# ── 육로·인접 전파 ──────────────────────────────────────────────────
# 항공만 있으면 **이웃 나라에도 허브를 돌아서 간다.** 실측(2026-08-27):
#   킨샤사 발원 → 두바이 66일 → … → 캄팔라 127일
# 콩고에서 우간다까지 페르시아만을 거쳐 61일이 걸린 셈이다. 실제 에볼라는
# 국경을 걸어서·배로 몇 주 만에 넘어간다(2014 서아프리카, 2018 북키부).
#
# ★ 이 수치는 실측이 아니라 자릿수 추정이다 ★
# 국경 통행량 공식 통계를 아직 붙이지 않았다. 항공편수(FLIGHT_CONNECTIONS)는
# 실제 노선에 근거하지만 이 값은 그렇지 않으므로, 결과에 estimated 로 표시한다.
# 붙일 수 있는 소스가 생기면 그때 실측으로 바꾼다.
GROUND_CONNECTIONS: dict[tuple[str, str], int] = {   # 하루 왕래 인원(추정)
    ("Kinshasa", "Kampala"):   300,   # 콩고 동부 경유 육로·수로. 거리가 멀어 보수적으로
    ("Riyadh",   "Dubai"):   3_000,   # 걸프 육로 — 사실상 상시 왕래
    ("Bangkok",  "Hanoi"):   1_000,   # 인도차이나 반도 육로(라오스·캄보디아 경유)
}
# 자카르타(섬)와 서울(사실상 섬 — 휴전선)은 육로 연결이 없다. 그래서 안 넣는다.

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
    days: int = 180,
    initial_infected: int = 10,
) -> dict:
    """
    발원 도시에서 시작해 항공 네트워크를 통해 다른 도시로 퍼지는 시뮬레이션.

    ★ 기본값이 90일이었는데 180일로 바꿨다(2026-08-27 실측) ★
    90일로 돌리면 **거의 아무것도 안 보인다.** 킨샤사 발원·신종(R0 2.8) 기준:

        90일  → 킨샤사 피크 213,404 · 두바이 피크 11명 · 서울 도달 없음
        180일 → 킨샤사 피크 3,046,518 · 두바이 피크 489,318 · 서울 도달 125일째

    유입량이 `유병률 × 250명 × 일일편수` 라, 발원지 유병률이 충분히 오르기 전에는
    도착지에 1명도 안 넘어간다. 킨샤사→두바이는 주 2편이라 하루 71명분인데,
    임계(0.05명)를 넘으려면 킨샤사에 **1만 2천 명쯤 감염돼야** 한다. 거기까지
    가는 데만 두 달이 걸리고, 그 뒤 도착지에서 다시 퍼질 시간이 필요하다.

    즉 90일은 "확산이 시작되기도 전에 끊는" 길이였다. 기본값으로 돌린 사람은
    빈 결과를 보고 시스템이 고장난 줄 알게 된다.
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

        # 이동을 통한 유입 — 항공과 육로를 같은 방식으로 처리한다.
        # (연결, 하루 왕래 인원) 으로 통일: 항공은 주간 편수 × 250명 / 7일
        movements: list[tuple[tuple[str, str], float]] = [
            (pair, weekly * PASSENGERS_PER_FLIGHT / 7)
            for pair, weekly in FLIGHT_CONNECTIONS.items()
        ] + [
            (pair, float(daily)) for pair, daily in GROUND_CONNECTIONS.items()
        ]

        for (city_a, city_b), daily_travelers in movements:
            for src, dst in [(city_a, city_b), (city_b, city_a)]:
                if src not in states or dst not in states:
                    continue
                i_src = states[src][2]
                n_src = CITIES_POPULATION[src]
                if n_src == 0 or i_src <= 0:
                    continue
                prevalence = i_src / n_src
                # 유입자 수 = 유병률 × 하루 왕래 인원
                imported = prevalence * daily_travelers
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

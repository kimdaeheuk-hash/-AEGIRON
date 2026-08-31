"""디지털 트윈 — 전 세계 확산 시뮬레이션.

## 무엇이 바뀌었나 (2026-08-31)

**노드가 8개 도시에서 159개 나라로 바뀌었다.**

이전 모델은 도시 8곳과 항공 11개 노선만 알았다. 그래서 확산이 그 8곳 밖으로
나가지 못했다 — 나이지리아도 인도도 브라질도 시뮬레이션에 존재하지 않았고,
"거기까지 안 갔다"가 아니라 **애초에 갈 곳이 없었다.**

이제 육로 국경이 있는 모든 나라가 노드다(`country_borders.py`, 317개 국경 쌍).
전파는 두 갈래로 일어난다:

  * **육로** — 국경을 맞댄 나라끼리. 지리적 사실이라 전 세계가 다 있다.
  * **항공** — 실제 노선을 아는 구간만. 아직 11개 노선뿐이다.

## 아직 부족한 것

항공망이 육로망보다 훨씬 성기다. 국경은 217개국 것을 다 적을 수 있지만
노선 여객량은 실측 소스가 필요하고, 그건 아직 없다. 그래서 **먼 대륙 간
확산은 실제보다 느리게 나온다** — 노선이 없는 게 아니라 우리가 모르는 것이다.
결과에 `air_network_coverage` 로 이 한계를 같이 내보낸다.

## 도시가 아니라 나라인 이유

도시 단위로 가려면 도시별 인구·도시 간 이동량이 다 필요한데, 그건 8곳까지가
한계였다. 나라 단위는 국경이라는 **확실한 지리 사실** 위에 세울 수 있어서
전 세계로 넓혀도 지어낸 값이 늘지 않는다.
"""
from __future__ import annotations

import io
import json
import os
from functools import lru_cache

from .common import THREAT
from .country_borders import (
    LAND_BORDERS, POPULATION, is_open, POPULATION_IS_APPROXIMATE,
)

# 발원지로 도시 이름을 받아온 기존 호출을 계속 받아준다.
# (예전 8개 도시 모델의 인터페이스 — 도시는 그 나라의 대표 도시로 해석한다.)
CITY_TO_COUNTRY: dict[str, str] = {
    "Kinshasa": "COD", "Kampala": "UGA", "Riyadh": "SAU", "Dubai": "ARE",
    "Bangkok":  "THA", "Hanoi":   "VNM", "Jakarta": "IDN", "Seoul": "KOR",
}

COUNTRY_NAME: dict[str, str] = {
    "COD": "콩고민주공화국", "UGA": "우간다", "SAU": "사우디아라비아",
    "ARE": "아랍에미리트", "THA": "태국", "VNM": "베트남",
    "IDN": "인도네시아", "KOR": "대한민국",
}

# ── 항공망 ──────────────────────────────────────────────────────────────────
# ★ 2026-08-31: 손으로 적던 11개 노선을 실측 데이터로 바꿨다 ★
# 11개뿐이던 시절엔 아메리카 대륙이 그래프에서 통째로 떨어져 나가, 미국·브라질이
# 1년을 돌려도 "미도달"로 찍혔다. 안 퍼진 게 아니라 갈 길을 몰랐던 것이다.
#
# 지금은 나라쌍 2,057개를 캐시에서 읽는다(OurAirports + OpenFlights, 둘 다 무료).
# 캐시를 굽는 건 scripts/collect_flight_routes.py 이고, **시뮬레이션은 파일만
# 읽는다** — 돌리는 중에 인터넷에 나가지 않는다.
# ★ data/ 가 아니라 코드 옆에 둔다 ★ epiweather-api/data/ 는 실행 중에 생기는
# 캐시·DB 스냅샷을 담는 곳이라 저장소에서 통째로 제외돼 있다. 항공 노선표는
# 코드와 같이 배포돼야 하는 **참조 데이터**라, 거기 두면 운영에서 사라진다.
FLIGHT_ROUTES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reference", "flight_routes_by_country.json",
)

# 노선 1개 = 하루 몇 명인가.
# ★ 이 계수는 찍은 값이 아니라 실제 시장에서 역산해 맞춘 값이다 ★
# 원본에 편수·승객 수가 없어서 나라쌍별 '노선 개수'만 나온다. 그래서 널리
# 알려진 연간 여객 개략치로 굵은 시장 네 곳을 역산했다(2026-08-31):
#
#     스페인-영국  994개 노선 · 연 5,000만명 → 노선당 138명/일
#     멕시코-미국  742개 노선 · 연 3,000만명 → 노선당 111명/일
#     캐나다-미국  729개 노선 · 연 2,500만명 → 노선당  94명/일
#     영국-미국    410개 노선 · 연 2,000만명 → 노선당 134명/일
#
# 서로 독립인 네 시장이 94~138명으로 모였다. 가운데인 120을 쓴다.
# 연간 여객은 개략치이므로 이 계수도 자릿수 맞추기지 정밀값이 아니다.
PASSENGERS_PER_ROUTE_PER_DAY = 120


@lru_cache(maxsize=1)
def load_flight_routes() -> tuple[dict[tuple[str, str], int], str | None]:
    """(나라쌍 → 노선 수, 못 읽은 이유). 없으면 **비었다고 말한다** — 조용히 넘기지 않는다."""
    try:
        with io.open(FLIGHT_ROUTES_PATH, encoding="utf-8") as fh:
            payload = json.load(fh)
    except FileNotFoundError:
        return {}, ("항공 노선 캐시가 없다. "
                    "`python scripts/collect_flight_routes.py` 를 먼저 돌려야 한다.")
    except (json.JSONDecodeError, OSError) as exc:
        return {}, f"항공 노선 캐시를 읽지 못했다: {exc}"

    routes: dict[tuple[str, str], int] = {}
    for key, count in (payload.get("route_counts") or {}).items():
        a, _, b = key.partition("|")
        if a and b and count:
            routes[(a, b)] = int(count)
    if not routes:
        return {}, "항공 노선 캐시가 비어 있다."
    return routes, None

# ── 육로 통행량 ─────────────────────────────────────────────────────────────
# ★ 실측이 아니라 자릿수 추정이다 ★
# 국경별 통행량 공식 통계는 아직 안 붙였다. 대신 **작은 쪽 나라 인구의 일정
# 비율**이 매일 국경을 넘는다고 본다 — 큰 나라끼리 맞댄 국경이 더 붐빈다는
# 것만 반영하는, 최소한의 가정이다.
#
# 모델에 없는 것: 지형(히말라야와 평지가 같다), 도로망, 비자, 계절.
# 그래서 상한을 둔다 — 인구만으로 수십만 명을 만들어내지 않게.
LAND_CROSSING_RATE = 0.0002        # 작은 쪽 인구의 0.02% / 일
LAND_CROSSING_MIN = 200            # 국경이 있으면 최소 이만큼은 오간다
LAND_CROSSING_MAX = 50_000         # 지형·정치를 모르므로 상한을 건다

HOSP_CAP_PER_MILLION = 2_400
HOSP_FRAC = 0.08
IMPORT_THRESHOLD = 0.05            # 이만큼은 넘어가야 "한 명 건너갔다"고 본다


def _land_traffic(a: str, b: str) -> float:
    """국경 하루 왕래 인원(추정). 인구를 모르는 나라는 0 — 지어내지 않는다."""
    pop_a, pop_b = POPULATION.get(a), POPULATION.get(b)
    if pop_a is None or pop_b is None:
        return 0.0
    raw = min(pop_a, pop_b) * LAND_CROSSING_RATE
    return float(min(max(raw, LAND_CROSSING_MIN), LAND_CROSSING_MAX))


def build_movement_network() -> list[tuple[str, str, float, str]]:
    """(나라A, 나라B, 하루 왕래 인원, 경로종류) 목록.

    항공과 육로를 하나로 합쳐 돌려준다 — 시뮬레이션 입장에서는 둘 다
    "하루 몇 명이 오가는 연결"이라 계산이 같다. 다만 **근거가 다르므로**
    종류를 같이 들고 다닌다(air = 실제 노선, land = 인구 기반 추정).
    """
    edges: list[tuple[str, str, float, str]] = []

    # 육로 — 국경이 있고 통행이 열린 곳 전부
    for iso, neighbours in LAND_BORDERS.items():
        for nb in neighbours:
            if iso >= nb or not is_open(iso, nb):   # 쌍당 한 번만
                continue
            traffic = _land_traffic(iso, nb)
            if traffic > 0:
                edges.append((iso, nb, traffic, "land"))

    # 항공 — 실측 노선 수를 하루 왕래 인원으로 환산
    known = set(POPULATION)
    routes, _ = load_flight_routes()
    for (a, b), route_count in routes.items():
        if a not in known or b not in known:
            continue          # 노드에 없는 나라(섬나라 일부·속령)는 건너뛴다
        edges.append((a, b, route_count * PASSENGERS_PER_ROUTE_PER_DAY, "air"))

    return edges


def reachable_from(origin_iso: str) -> set[str]:
    """발원국에서 **경로를 타고 갈 수 있는** 나라들.

    ★ 이게 없으면 모델이 거짓 안전 신호를 낸다 ★
    항공 노선을 11개만 알기 때문에 아메리카 대륙은 그래프에서 통째로 떨어져
    있다. 그 상태로 결과를 내면 미국·브라질이 "미도달"로 찍히는데, 이건
    "안 퍼졌다"가 아니라 **우리가 가는 길을 모른다**는 뜻이다. 둘은 완전히
    다른 말이고, 섞으면 보는 사람이 안전하다고 오해한다.
    """
    graph: dict[str, set[str]] = {}
    for a, b, _, _ in build_movement_network():
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    seen = {origin_iso}
    queue = [origin_iso]
    while queue:
        node = queue.pop()
        for nb in graph.get(node, ()):
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return seen


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


def resolve_origin(origin: str) -> str | None:
    """도시 이름·ISO3 어느 쪽으로 줘도 받는다. 모르면 None — 추측하지 않는다."""
    if origin in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[origin]
    up = origin.upper()
    return up if up in POPULATION else None


def simulate_spread(
    origin: str,
    threat: str = "novel",
    days: int = 180,
    initial_infected: int = 10,
) -> dict:
    """발원국에서 시작해 육로·항공으로 전 세계에 퍼지는 시뮬레이션.

    ★ 기간 기본값이 180일인 이유 ★ (2026-08-27 실측)
    90일로 돌리면 **확산이 시작되기도 전에 끊긴다.** 유입량이
    `유병률 × 하루 왕래 인원` 이라, 발원지 유병률이 충분히 오르기 전에는
    도착지에 한 명도 안 넘어간다. 기본값으로 돌린 사람이 빈 결과를 보고
    시스템이 고장난 줄 알게 되는 길이였다.

    origin 은 도시 이름("Kinshasa")이나 ISO3 국가코드("COD") 둘 다 받는다.
    """
    sp = THREAT.get(threat, THREAT["novel"])
    r0, cfr = sp["R0"], sp["cfr"]

    origin_iso = resolve_origin(origin)
    if origin_iso is None:
        return {
            "error": f"모르는 발원지: {origin}. "
                     f"도시 이름({', '.join(CITY_TO_COUNTRY)}) 또는 "
                     f"ISO3 국가코드(예: NGA, BRA, IND)로 주세요."
        }

    nodes = list(POPULATION)
    edges = build_movement_network()

    # 상태: {나라: [S, E, I, D]}
    states: dict[str, list[float]] = {}
    for iso in nodes:
        pop = float(POPULATION[iso])
        if iso == origin_iso:
            states[iso] = [pop - initial_infected, 0.0, float(initial_infected), 0.0]
        else:
            states[iso] = [pop, 0.0, 0.0, 0.0]

    peak_day: dict[str, int | None] = {c: None for c in nodes}
    peak_inf: dict[str, float] = {c: 0.0 for c in nodes}
    first_case_day: dict[str, int | None] = {c: None for c in nodes}
    first_case_day[origin_iso] = 0
    arrival_route: dict[str, str | None] = {c: None for c in nodes}
    overflow_days: dict[str, int] = {c: 0 for c in nodes}

    for day in range(days):
        new_states = {c: list(v) for c, v in states.items()}

        # 각 나라 자체 전파
        for iso in nodes:
            n = float(POPULATION[iso])
            ns, ne, ni, nd = _seir_step(*states[iso], n, r0, cfr)
            new_states[iso] = [ns, ne, ni, nd]
            if ni > peak_inf[iso]:
                peak_inf[iso] = ni
                peak_day[iso] = day
            if ni * HOSP_FRAC > n / 1_000_000 * HOSP_CAP_PER_MILLION:
                overflow_days[iso] += 1

        # 이동을 통한 유입 — 육로와 항공을 같은 식으로 계산한다
        for a, b, daily_travelers, kind in edges:
            for src, dst in ((a, b), (b, a)):
                i_src = states[src][2]
                if i_src <= 0:
                    continue
                prevalence = i_src / POPULATION[src]
                imported = prevalence * daily_travelers
                if imported < IMPORT_THRESHOLD:
                    continue
                new_states[dst][2] += imported
                new_states[dst][0] = max(0.0, new_states[dst][0] - imported)
                if first_case_day[dst] is None:
                    first_case_day[dst] = day
                    arrival_route[dst] = kind      # 육로로 왔는지 항공으로 왔는지

        states = new_states

    reached = [c for c in nodes if first_case_day[c] is not None]
    reached.sort(key=lambda c: (first_case_day[c], -peak_inf[c]))

    summaries = [{
        "country":        iso,
        "name":           COUNTRY_NAME.get(iso, iso),
        "first_case_day": first_case_day[iso],
        "arrival_route":  arrival_route[iso],
        "peak_day":       peak_day[iso],
        "peak_infected":  int(peak_inf[iso]),
        "final_deaths":   int(states[iso][3]),
        "hosp_overflow_days": overflow_days[iso],
    } for iso in reached]

    # 안 퍼진 나라를 두 부류로 가른다 — 섞으면 안 된다
    connected = reachable_from(origin_iso)
    not_reached, no_route = [], []
    for iso in nodes:
        if first_case_day[iso] is not None:
            continue
        (not_reached if iso in connected else no_route).append(iso)

    air_pairs = {(a, b) if a < b else (b, a) for a, b, _, k in edges if k == "air"}
    _, air_load_error = load_flight_routes()

    return {
        "origin":           origin,
        "origin_country":   origin_iso,
        "threat":           threat,
        "days_simulated":   days,
        "r0":               r0,
        "countries_modeled": len(nodes),
        "countries_reached": len(reached),
        "seoul_arrival_day": first_case_day.get("KOR"),
        "countries":        summaries,
        "spread_sequence":  [s["country"] for s in summaries],
        # 길은 있는데 기간 안에 안 온 나라
        "not_reached":      sorted(not_reached),
        # ★ 길 자체를 모르는 나라 ★ "안전"이 아니라 "모른다"이다
        "no_route_modeled": sorted(no_route),
        # ── 이 결과를 어디까지 믿어도 되는지 ────────────────────────────
        "limits": {
            "air_network_coverage": f"항공 {len(air_pairs)}개 나라쌍 · "
                                    f"육로 {sum(1 for *_, k in edges if k == 'land')}개 국경",
            "air_routes_loaded": air_load_error is None,
            "air_routes_error": air_load_error,
            "air_data_year": "2014 (OpenFlights, 2017-02 갱신)",
            "land_traffic_is_estimated": True,
            "population_is_approximate": POPULATION_IS_APPROXIMATE,
            "unreachable_countries": len(no_route),
            "note": "항공 노선은 2014년 기준 실측 데이터입니다 — 나라 사이 연결 "
                    "유무는 잘 안 변하지만 편수는 많이 바뀌었습니다. 노선 수를 "
                    "사람 수로 바꾼 계수(노선당 120명/일)는 굵은 시장 네 곳에서 "
                    "역산한 자릿수 값입니다. 육로 통행량은 인구 기반 추정이며 "
                    "지형·비자·계절을 반영하지 않습니다.",
            "no_route_warning": (
                f"{len(no_route)}개국은 발원지에서 갈 경로를 이 모델이 "
                f"모릅니다(항공 노선 미보유). **안전하다는 뜻이 아닙니다.**"
            ) if no_route else None,
        },
    }

"""디지털 트윈이 실제 지리대로 퍼지는지, 그리고 **모르는 걸 안다고 하지 않는지**.

이 파일은 실측으로 잡은 고장 세 가지를 다시 못 나게 막는다.

1. **기간이 짧아 아무것도 안 보이던 것** (2026-08-27)
   기본값이 90일이었다. 90일이면 확산이 시작되기도 전에 끊긴다 —
   킨샤사 발원 신종(R0 2.8)에서 서울 도달이 아예 안 잡혔다. 지금은 180일.

2. **육로가 없어 이웃 나라를 허브로 돌아가던 것** (2026-08-27)
   콩고 발원인데 이웃 우간다가 두바이를 거쳐 127일째 감염됐다.
   페르시아만이 옆 나라보다 61일 빨랐다.

3. **못 가는 곳을 "안 퍼졌다"고 하던 것** (2026-08-31)
   전 세계로 넓히고 나니 미국·브라질이 365일에도 미도달로 찍혔다.
   원인은 아메리카행 항공 노선이 데이터에 하나도 없어서 **그래프상 닿을
   길이 없는** 것이었다. 이건 "안전"이 아니라 "모른다"다.
"""
from __future__ import annotations

import pytest

from algorithms.country_borders import (
    LAND_BORDERS, POPULATION, CLOSED_BORDERS, neighbours, open_neighbours,
    border_pairs,
)
from algorithms.digital_twin import (
    simulate_spread, build_movement_network, reachable_from, CITY_TO_COUNTRY,
)


def _row(result: dict, iso: str) -> dict | None:
    return next((c for c in result["countries"] if c["country"] == iso), None)


# ── 1. 기간 ─────────────────────────────────────────────────────────────────

def test_default_horizon_is_long_enough_to_show_spread():
    """★핵심★ 기본값으로 돌렸을 때 서울 도달이 실제로 잡혀야 한다."""
    r = simulate_spread(origin="Kinshasa", threat="novel")

    assert r["days_simulated"] >= 180, "기본 기간이 180일 미만이면 확산이 안 보인다"
    assert r["seoul_arrival_day"] is not None, (
        "기본값으로 돌렸는데 서울 도달이 안 잡힌다 — 90일 시절의 그 증상이다"
    )


def test_ninety_days_would_have_hidden_everything():
    """왜 90일을 버렸는지 남긴다 — 되돌리려는 사람이 근거를 보게."""
    short = simulate_spread(origin="Kinshasa", threat="novel", days=90)
    long_ = simulate_spread(origin="Kinshasa", threat="novel", days=180)

    assert short["seoul_arrival_day"] is None
    assert long_["seoul_arrival_day"] is not None
    assert long_["countries_reached"] > short["countries_reached"] * 2


def test_faster_pathogen_arrives_sooner():
    """물리적으로 맞는 방향인지 — R0 가 높으면 더 빨리 도달해야 한다.

    기간을 365일로 잡는다. 180일로 재면 느린 병원체가 "미도달"로 나와서
    비교 자체가 안 된다 — 안 오는 게 아니라 창이 짧은 것이다.

        항공 실측을 붙인 뒤(2026-08-31):
        중증(3.4) 104일 · 신종(2.8) 127일 · 독감(2.2) 170일
    """
    severe = simulate_spread(origin="Kinshasa", threat="severe", days=365)
    novel  = simulate_spread(origin="Kinshasa", threat="novel",  days=365)
    flu    = simulate_spread(origin="Kinshasa", threat="flu",    days=365)

    assert severe["r0"] > novel["r0"] > flu["r0"]
    for r in (severe, novel, flu):
        assert r["seoul_arrival_day"] is not None, "365일이면 셋 다 도달해야 비교가 된다"
    assert severe["seoul_arrival_day"] < novel["seoul_arrival_day"] < flu["seoul_arrival_day"]
    # 사망자 규모도 같은 순서여야 한다.
    # (도달 *국가 수* 로는 이제 비교가 안 된다 — 항공 실측을 붙인 뒤로는
    #  셋 다 1년이면 159개국에 다 간다. 차이는 '어디까지'가 아니라 '언제·얼마나'다.)
    deaths = lambda r: sum(c["final_deaths"] for c in r["countries"])
    assert deaths(severe) > deaths(novel) > deaths(flu)


def test_origin_country_actually_grows():
    """발원지에서 실제로 유행이 일어나는지 — 0이면 SEIR 자체가 죽은 것이다."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    origin = _row(r, "COD")

    assert origin["first_case_day"] == 0
    assert origin["peak_infected"] > 1_000_000
    assert origin["final_deaths"] > 0


# ── 2. 발원지 입력 ──────────────────────────────────────────────────────────

def test_unknown_origin_is_rejected_not_guessed():
    """모르는 발원지는 조용히 기본값으로 바꾸지 않고 오류로 말한다."""
    r = simulate_spread(origin="Atlantis", threat="novel")

    assert "error" in r
    assert "Atlantis" in r["error"]


def test_iso3_code_works_as_origin():
    """전 세계로 넓힌 뒤로는 나라 코드로도 시작할 수 있어야 한다."""
    r = simulate_spread(origin="NGA", threat="novel", days=180)

    assert "error" not in r
    assert r["origin_country"] == "NGA"
    assert _row(r, "NGA")["first_case_day"] == 0


@pytest.mark.parametrize("city", sorted(CITY_TO_COUNTRY))
def test_legacy_city_names_still_work(city):
    """예전 8개 도시 이름으로 부르던 호출을 깨뜨리지 않는다."""
    r = simulate_spread(origin=city, threat="novel", days=180)

    assert "error" not in r
    assert _row(r, CITY_TO_COUNTRY[city])["first_case_day"] == 0


# ── 3. 육로 전파 ────────────────────────────────────────────────────────────

def test_neighbour_gets_hit_before_the_far_hub():
    """★핵심★ 이웃 나라가 먼 허브보다 먼저 걸려야 한다.

    육로를 넣기 전 실측: 콩고 발원인데 우간다가 두바이를 거쳐 127일째였다.
    실제 에볼라는 국경을 걸어서·배로 넘는다(2014 서아프리카, 2018 북키부).
    """
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    uganda, uae = _row(r, "UGA"), _row(r, "ARE")

    assert uganda is not None, "이웃 우간다가 아예 안 걸리면 육로가 안 먹는 것이다"
    assert uae is not None
    assert uganda["first_case_day"] < uae["first_case_day"], (
        "이웃 나라가 페르시아만보다 늦으면 육로 전파가 죽어 있다"
    )
    assert uganda["arrival_route"] == "land"


def test_spread_goes_far_beyond_the_old_eight_cities():
    """★핵심★ 전 세계로 넓힌 게 실제로 효과가 있는지.

    예전 모델은 노드가 8개뿐이라 나이지리아도 이집트도 존재하지 않았다.
    """
    r = simulate_spread(origin="Kinshasa", threat="novel", days=365)

    assert r["countries_modeled"] > 100
    assert r["countries_reached"] > 50, "전 세계 노드를 깔았는데 몇 나라만 걸린다"
    for iso in ("NGA", "EGY", "ETH", "SDN"):
        assert _row(r, iso) is not None, f"{iso} 에 육로로 못 갔다 — 사슬이 끊겼다"


def test_land_chain_follows_real_geography():
    """육로 사슬이 지리 순서를 지키는지 — 콩고→중앙아프리카→카메룬→나이지리아."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=365)
    days = {c["country"]: c["first_case_day"] for c in r["countries"]}

    assert days["COD"] < days["CAF"] < days["CMR"] < days["NGA"], (
        "중간 나라를 건너뛰고 먼저 걸린다 — 국경 표가 틀렸거나 그래프가 샌다"
    )


# ── 4. 국경 표 자체 ─────────────────────────────────────────────────────────

def test_border_table_matches_known_geography():
    """잘 알려진 국경 수와 맞는지 — 표를 손으로 적었으니 대조가 필요하다."""
    known = {"CHN": 14, "RUS": 14, "BRA": 10, "DEU": 9, "COD": 9, "TUR": 8}

    for iso, count in known.items():
        assert len(neighbours(iso)) == count, f"{iso} 국경 수가 {count}개가 아니다"


def test_borders_are_symmetric():
    """A가 B와 접하면 B도 A와 접해야 한다 — 손으로 적으면 한쪽을 빠뜨린다."""
    for iso, nbs in LAND_BORDERS.items():
        for nb in nbs:
            assert iso in LAND_BORDERS[nb], f"{iso}-{nb} 국경이 한쪽에만 있다"


def test_every_bordered_country_has_a_population():
    """인구가 없으면 SEIR을 못 돌린다 — 0으로 때우지 않고 여기서 잡는다."""
    missing = [c for c in LAND_BORDERS if c not in POPULATION]

    assert missing == [], f"인구 없는 나라: {missing}"


def test_closed_borders_carry_no_traffic():
    """휴전선처럼 닫힌 국경은 지리에는 남기되 사람은 안 넘긴다."""
    assert "PRK" in neighbours("KOR")          # 지리적으로는 접해 있고
    assert open_neighbours("KOR") == frozenset()  # 통행은 없다

    land_pairs = {
        (a, b) if a < b else (b, a)
        for a, b, _, kind in build_movement_network() if kind == "land"
    }
    for pair in CLOSED_BORDERS:
        assert pair not in land_pairs, f"{pair} 는 닫힌 국경인데 사람이 오간다"


def test_border_pairs_are_deduplicated():
    """국경 쌍이 중복되면 통행량이 두 배로 계산된다."""
    pairs = border_pairs()

    assert len(pairs) == len(set(pairs))
    assert all(a < b for a, b in pairs), "쌍 순서가 정규화되지 않았다"


# ── 5. 모르는 것을 안다고 하지 않기 ─────────────────────────────────────────

def test_real_flight_data_closed_the_americas_hole():
    """★핵심★ 항공 실측을 붙여서 아메리카 대륙이 닿게 됐는지.

    손으로 적은 11개 노선만 있던 시절엔 미국·브라질이 365일에도 미도달로
    찍혔다. 안 퍼져서가 아니라 아메리카행 노선이 데이터에 하나도 없어서
    **그래프상 갈 길이 없었던** 것이다(2026-08-31 실측).
    """
    r = simulate_spread(origin="Kinshasa", threat="novel", days=365)
    reached = {c["country"] for c in r["countries"]}

    assert r["no_route_modeled"] == [], "아직도 닿을 수 없는 나라가 남아 있다"
    for iso in ("USA", "BRA", "CAN", "MEX", "GBR", "ARG"):
        assert iso in reached, f"{iso} 에 못 갔다 — 항공망이 다시 끊겼다"
    # 육로가 먼저, 먼 대륙은 항공으로 — 경로 종류가 지리와 맞아야 한다
    assert _row(r, "UGA")["arrival_route"] == "land"
    assert _row(r, "USA")["arrival_route"] == "air"


def test_missing_flight_cache_never_reads_as_safe(monkeypatch):
    """★★핵심★★ 항공 캐시가 없어도 "안 퍼졌다"고 말하지 않는다.

    캐시 파일이 빠지면 항공망이 통째로 사라져서 예전 상태로 돌아간다.
    그때 아메리카가 `not_reached`(=안 왔다)로 나오면 보는 사람은 안전하다고
    읽는다 — 조기경보가 낼 수 있는 최악의 거짓말이다. 그런 상황에서는
    `no_route_modeled`(=갈 길을 모른다)로 나와야 하고, 경고도 붙어야 한다.
    """
    import algorithms.digital_twin as dt
    monkeypatch.setattr(dt, "load_flight_routes",
                        lambda: ({}, "캐시 없음(시험)"))

    r = dt.simulate_spread(origin="Kinshasa", threat="novel", days=365)

    assert "USA" in r["no_route_modeled"], "갈 길이 없는데 미도달로 섞였다"
    assert "USA" not in r["not_reached"]
    assert r["limits"]["air_routes_loaded"] is False
    assert r["limits"]["air_routes_error"]
    assert "안전" in r["limits"]["no_route_warning"]


def test_the_two_buckets_never_overlap():
    """미도달과 경로 미보유는 서로소여야 한다 — 겹치면 어느 쪽도 못 믿는다."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=365)
    reached = {c["country"] for c in r["countries"]}

    assert not (set(r["not_reached"]) & set(r["no_route_modeled"]))
    assert not (reached & set(r["not_reached"]))
    assert not (reached & set(r["no_route_modeled"]))
    assert len(reached) + len(r["not_reached"]) + len(r["no_route_modeled"]) \
        == r["countries_modeled"], "어느 부류에도 안 들어간 나라가 있다"


def test_reachability_matches_what_actually_got_infected():
    """도달한 나라는 전부 연결 성분 안에 있어야 한다 — 그래프와 결과가 따로 놀면 안 된다."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=365)
    connected = reachable_from("COD")

    for c in r["countries"]:
        assert c["country"] in connected, (
            f"{c['country']} 가 감염됐는데 연결 성분 밖이다 — 계산이 어긋났다"
        )


def test_limits_are_always_reported():
    """한계를 늘 같이 내보낸다 — 결과만 보고 실측이라고 오해하지 않게."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    limits = r["limits"]

    assert limits["air_routes_loaded"] is True, "항공 실측 캐시를 못 읽고 있다"
    assert limits["land_traffic_is_estimated"] is True
    assert limits["population_is_approximate"] is True
    # 항공 데이터가 몇 년 것인지 늘 밝힌다 — 2014년 기준이라 오해하기 쉽다
    assert "2014" in limits["air_data_year"]


# ── 6. 항공 노선 캐시 자체 ──────────────────────────────────────────────────
# scripts/collect_flight_routes.py 가 구운 파일이다. 시뮬레이션은 이것만 읽고
# 인터넷에 나가지 않는다.

def test_flight_cache_is_present_and_substantial():
    """캐시가 있어야 하고, 손으로 적던 11개와 자릿수가 달라야 한다."""
    from algorithms.digital_twin import load_flight_routes

    routes, error = load_flight_routes()

    assert error is None, f"항공 캐시를 못 읽는다: {error}"
    assert len(routes) > 1_000, "노선 수가 너무 적다 — 수집이 반쯤 실패했다"


def test_flight_cache_matches_known_big_markets():
    """굵은 국제선 시장이 실제로 굵게 나오는지 — 조인이 어긋나면 여기서 걸린다."""
    from algorithms.digital_twin import load_flight_routes

    routes, _ = load_flight_routes()

    for pair in (("ESP", "GBR"), ("MEX", "USA"), ("CAN", "USA"), ("GBR", "USA")):
        assert routes.get(pair, 0) > 300, f"{pair} 가 굵게 안 나온다"


def test_flight_cache_has_no_domestic_pairs():
    """같은 나라끼리는 항공 간선이 아니다 — SEIR 이 이미 나라 안 전파를 다룬다."""
    from algorithms.digital_twin import load_flight_routes

    routes, _ = load_flight_routes()

    assert not [p for p in routes if p[0] == p[1]]
    assert all(a < b for a, b in routes), "나라쌍 순서가 정규화되지 않았다"

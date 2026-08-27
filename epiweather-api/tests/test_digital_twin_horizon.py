"""디지털 트윈 기본 기간이 너무 짧으면 아무것도 안 보인다 (2026-08-27 실측).

기본값이 90일이었다. 그런데 90일로 돌리면 **확산이 시작되기도 전에 끊긴다.**
킨샤사 발원·신종(R0 2.8) 실측:

    90일  → 킨샤사 피크 213,404 · 두바이 피크 11명 · 서울 도달 없음
    180일 → 킨샤사 피크 3,046,518 · 두바이 피크 489,318 · 서울 도달 125일째

이유는 유입식에 있다. `유입 = 유병률 × 250명 × 일일편수` 이고 임계가 0.05명이라,
킨샤사→두바이(주 2편, 하루 71명분)에서 한 명이라도 넘어가려면 킨샤사에
**1만 2천 명쯤** 감염돼 있어야 한다. 거기까지 두 달, 그 뒤 도착지 전파에 또 시간이
필요하다.

**기본값으로 돌린 사람은 빈 결과를 보고 시스템이 고장난 줄 안다.**
그게 이 테스트가 막으려는 것이다.
"""
from __future__ import annotations

import pytest

from algorithms.digital_twin import (
    simulate_spread, CITIES_POPULATION, GROUND_CONNECTIONS, FLIGHT_CONNECTIONS,
)


def _city(result: dict, name: str) -> dict:
    return next(c for c in result["cities"] if c["city"] == name)


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

    assert short["seoul_arrival_day"] is None      # 90일엔 서울에 안 온다
    assert long_["seoul_arrival_day"] is not None  # 180일엔 온다

    # 도착지 규모 차이가 네 자릿수다 — "조금 덜 보이는" 정도가 아니다
    assert _city(short, "Dubai")["peak_infected"] < 100
    assert _city(long_, "Dubai")["peak_infected"] > 100_000


def test_faster_pathogen_arrives_sooner():
    """물리적으로 맞는 방향인지 — R0 가 높으면 더 빨리 도달해야 한다."""
    severe = simulate_spread(origin="Kinshasa", threat="severe", days=180)
    novel = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    flu = simulate_spread(origin="Kinshasa", threat="flu", days=180)

    assert severe["r0"] > novel["r0"] > flu["r0"]
    assert severe["seoul_arrival_day"] < novel["seoul_arrival_day"] < flu["seoul_arrival_day"]


def test_origin_city_actually_grows():
    """발원지에서 실제로 유행이 일어나는지 — 이게 0이면 SEIR 자체가 죽은 것이다."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    origin = _city(r, "Kinshasa")

    assert origin["first_case_day"] == 0
    assert origin["peak_infected"] > 1_000_000     # 인구 1,710만
    assert origin["final_deaths"] > 0


def test_unknown_origin_is_rejected_not_guessed():
    """모르는 도시는 조용히 기본값으로 바꾸지 않고 오류로 말한다."""
    r = simulate_spread(origin="Pyongyang", threat="novel")

    assert "error" in r
    assert "Pyongyang" in r["error"]


@pytest.mark.parametrize("city", list(CITIES_POPULATION))
def test_every_city_can_be_an_origin(city):
    """8개 도시 어디서 시작해도 발원지에서는 유행이 일어나야 한다."""
    r = simulate_spread(origin=city, threat="novel", days=180)

    assert "error" not in r
    assert _city(r, city)["first_case_day"] == 0
    assert _city(r, city)["peak_infected"] > 0


# ── 육로·인접 전파 (2026-08-27 추가) ────────────────────────────────────────

def test_neighbour_gets_hit_before_the_far_hub():
    """★핵심★ 이웃 나라가 먼 허브보다 먼저 걸려야 한다.

    육로를 넣기 전 실측: 킨샤사(콩고) 발원인데 우간다 캄팔라가
    **두바이를 거쳐 127일째** 감염됐다. 페르시아만이 이웃 나라보다 61일 빨랐다.
    실제 에볼라는 국경을 걸어서·배로 넘는다(2014 서아프리카, 2018 북키부).

    육로 추가 후: 캄팔라 53일 · 두바이 66일 — 순서가 뒤집혔다.
    """
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)
    kampala = _city(r, "Kampala")
    dubai = _city(r, "Dubai")

    assert kampala["first_case_day"] is not None
    assert kampala["first_case_day"] < dubai["first_case_day"], (
        "이웃 우간다가 두바이보다 늦게 걸리면 육로 전파가 안 먹고 있는 것이다"
    )


def test_ground_route_changes_the_scale_not_just_the_timing():
    """규모도 달라진다 — 675명과 64만 명은 대응이 완전히 다른 숫자다."""
    r = simulate_spread(origin="Kinshasa", threat="novel", days=180)

    assert _city(r, "Kampala")["peak_infected"] > 100_000


def test_islands_have_no_ground_route():
    """자카르타(섬)·서울(휴전선)은 육로로 잇지 않는다 — 지리를 지어내지 않는다."""
    ground_cities = {c for pair in GROUND_CONNECTIONS for c in pair}

    assert "Jakarta" not in ground_cities
    assert "Seoul" not in ground_cities


def test_ground_pairs_are_real_neighbours():
    """육로로 이은 쌍이 실제로 인접한 곳인지 — 아무 도시나 잇지 않았는지."""
    expected = {("Kinshasa", "Kampala"), ("Riyadh", "Dubai"), ("Bangkok", "Hanoi")}

    assert set(GROUND_CONNECTIONS) == expected


def test_a_pair_can_have_both_air_and_ground():
    """★같은 도시 쌍에 항공과 육로가 둘 다 있는 건 정상이다★

    처음 이 테스트를 "겹치면 안 된다"로 썼다가 방콕–하노이에서 걸렸다.
    거긴 항공편(주 14편)도 있고 육로(라오스·캄보디아 경유)도 있다 —
    현실이 그렇고, 사람은 양쪽으로 다닌다. 그래서 **합산되는 것이 맞다.**

    항공과 육로를 따로 둔 이유는 겹침을 막으려는 게 아니라 **근거가 다르기**
    때문이다. 항공편수는 실제 노선에 근거하고, 육로 왕래는 자릿수 추정이다.
    """
    overlap = set(FLIGHT_CONNECTIONS) & set(GROUND_CONNECTIONS)

    assert ("Bangkok", "Hanoi") in overlap    # 둘 다 있는 게 정상
    # 그래도 각각은 따로 관리된다 — 나중에 육로를 실측으로 바꿀 때 갈라야 하므로
    assert FLIGHT_CONNECTIONS is not GROUND_CONNECTIONS

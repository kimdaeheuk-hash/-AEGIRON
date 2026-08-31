"""location 자유문장 → ISO3 해석. 이 해석이 실패하면 Tier-2 학습셋에서 신호가
통째로 버려진다 — 실측에서 2024년 이후 신호 157건 중 150건이 그렇게 사라져
최근 3년 커버리지가 0이 됐다. 그래서 회귀 방지가 중요하다."""
from __future__ import annotations
import pytest

from algorithms.country_resolve import (
    resolve_countries, resolve_country, signal_countries,
)


@pytest.mark.parametrize("loc,expected", [
    # 한글 — bulletin_ingest.iso3_for는 [^a-z ]를 지워서 전부 None이 됐다.
    ("우간다", ["UGA"]),
    ("콩고민주공화국", ["COD"]),
    ("콩고 민주공화국", ["COD"]),
    ("민주콩고", ["COD"]),
    ("대한민국", ["KOR"]),
    ("한국", ["KOR"]),
    # 띄어쓰기 흔들림 — 실제 수집 데이터에 '사우디 아라비아'로 들어왔다.
    ("사우디 아라비아", ["SAU"]),
    ("사우디아라비아", ["SAU"]),
    # 영문·약어
    ("Democratic Republic of the Congo", ["COD"]),
    ("DRC", ["COD"]),
    ("DR Congo", ["COD"]),
])
def test_single_country_forms(loc, expected):
    assert resolve_countries(loc) == expected


@pytest.mark.parametrize("loc,expected", [
    ("콩고민주공화국, 우간다", ["COD", "UGA"]),
    ("Democratic Republic of the Congo and Uganda", ["COD", "UGA"]),
    ("DRC(콩고민주공화국), 우간다", ["COD", "UGA"]),
    ("콩고민주공화국, 우간다, 프랑스", ["COD", "UGA", "FRA"]),
    ("캄보디아, 필리핀, 베트남", ["KHM", "PHL", "VNM"]),
])
def test_multi_country_keeps_every_country(loc, expected):
    """★핵심★ 국경을 넘는 발병에서 "콩고민주공화국, 우간다"는 두 나라 모두의
    증거다. 하나만 남기면 반대편 나라의 조기신호를 통째로 잃는다. 실측에서 이
    형태가 90건 넘게 있었고 전부 국가 없이 저장돼 있었다."""
    assert resolve_countries(loc) == expected


@pytest.mark.parametrize("loc", [
    "전 세계", "크루즈선", "대서양 크루즈선", "국제 크루즈선",
    "서태평양", "WHO 서태평양지역", "아프리카", "30 countries",
    "가자지구", None, "",
])
def test_non_countries_are_refused_not_guessed(loc):
    """★정직성★ 지역·선박·'전 세계'를 국가로 승격시키면 있지도 않은 커버리지가
    생긴다. 잘못 붙인 국가코드는 없는 것보다 나쁘다 — 그 나라에 없던 발병
    신호를 만들어내기 때문이다."""
    assert resolve_countries(loc) == []


@pytest.mark.parametrize("loc,expected", [
    ("남수단", ["SSD"]),          # '수단'으로 떨어지면 안 된다
    ("수단", ["SDN"]),
    ("수단, 남수단", ["SDN", "SSD"]),
    ("남아프리카공화국", ["ZAF"]),   # '아프리카' 차단 규칙에 잡히면 안 된다
    ("중앙아프리카공화국", ["CAF"]),
    ("콩고공화국", ["COG"]),        # 콩고민주공화국과 다른 나라다
])
def test_longest_name_wins(loc, expected):
    assert resolve_countries(loc) == expected


def test_specific_country_survives_alongside_blocked_region():
    """차단어가 섞여 있어도 구체적 국가는 살린다 — 조각 단위로 판정하기 때문."""
    assert resolve_countries("전 세계 70개 이상 국가, 남수단, 수단") == ["SSD", "SDN"]
    assert resolve_countries("대서양 크루즈선, 아르헨티나") == ["ARG"]
    assert resolve_countries("WHO 서부태평양 지역(사모아)") == ["WSM"]


def test_duplicates_collapse():
    assert resolve_countries("DRC, 콩고민주공화국, DR Congo") == ["COD"]


def test_resolve_country_returns_primary():
    assert resolve_country("콩고민주공화국, 우간다") == "COD"
    assert resolve_country("크루즈선") is None


def test_signal_countries_merges_stored_and_location():
    """저장된 country_iso3는 하나뿐이라 국경 반대편을 잃는다 — location에서 보충한다."""
    got = signal_countries({"country_iso3": "COD", "location": "콩고민주공화국, 우간다"})
    assert got == ["COD", "UGA"]


def test_signal_countries_ignores_malformed_stored_code():
    """모델 오출력(소문자·전체국명)이 그대로 들어오면 무시하고 location으로 간다."""
    assert signal_countries({"country_iso3": "congo", "location": "우간다"}) == ["UGA"]
    assert signal_countries({"country_iso3": None, "location": None}) == []


# ── 2026-08-31 실측으로 잡은 두 가지 ────────────────────────────────────────
# 항공 노선 데이터의 국가명을 훑다가 나왔다. 235개 이름 중 107개가 해석에
# 실패했는데, 그 안에 남아프리카공화국이 있었다.

def test_south_africa_is_not_thrown_away_as_a_continent():
    """★핵심★ 영문 'South Africa' 가 대륙 언급으로 오인돼 버려지고 있었다.

    '아프리카/africa' 는 대륙 표현이라 걸러내는데, 그 필터가 South Africa 를
    같이 삼켰다. 한글 '남아프리카공화국'은 뒤의 '공화국' 덕에 살아남아서
    한쪽 언어에서만 조용히 사라졌다 — 영문 기사·WHO 문서가 주 입력인데
    남아공이 안 잡히면 조기경보에 구멍이 생긴다.
    """
    assert resolve_country("South Africa") == "ZAF"
    assert resolve_country("남아프리카공화국") == "ZAF"
    assert resolve_countries("South Africa and Nigeria") == ["ZAF", "NGA"]


def test_continent_mentions_are_still_filtered_out():
    """대륙·지역 표현은 그대로 막혀야 한다 — 남아공만 예외로 뺀 것이다."""
    assert resolve_country("Southern Africa") is None
    assert resolve_country("across Africa") is None
    assert resolve_country("아프리카") is None


def test_the_two_congos_are_told_apart():
    """★핵심★ 괄호로 가르는 두 콩고를 뒤바꾸지 않는다.

    조각 분리자가 괄호에서 먼저 쪼개는 바람에 "Congo (Kinshasa)" 가 앞 조각
    "Congo" 만 보고 COG(콩고공화국)로 갔다. 킨샤사는 COD(콩고민주공화국)
    수도이고 우리 시뮬레이션의 발원지다 — 발병을 이웃 나라에 붙이던 셈이다.
    """
    assert resolve_country("Congo (Kinshasa)") == "COD"
    assert resolve_country("Congo (Brazzaville)") == "COG"
    # 괄호 표기가 다른 나라와 같이 나와도 둘 다 살아야 한다
    assert resolve_countries("Congo (Kinshasa), Uganda") == ["COD", "UGA"]
    # 괄호 없는 기존 표기도 그대로
    assert resolve_country("DR Congo") == "COD"
    assert resolve_country("Republic of Congo") == "COG"

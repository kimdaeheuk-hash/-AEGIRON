"""빙하 산맥 맥락이 **판정을 넘어서지 않는지** 지킨다 (2026-09-01).

## 왜 만들었나

2026-08-26 네팔 Rasuwa 홍수(사망 359명+·실종 1,000명+)를 조사하다 나왔다.
랑탕리룽 북면 빙하가 붕괴해 암석·빙하 눈사태 → 토석류 → 하천 폐색 →
천연댐 붕괴로 이어진 **연쇄 재해**였고, 사고 당시 날씨는 맑았다.

GDACS 는 이걸 그냥 `FL`(홍수)로 준다. 즉 **우리는 사건을 받고 있었지만 어디서
왔는지는 몰랐다.** 빙하 기원 홍수는 비 없이 갑자기 오고 고산 오지를 치며
의료 접근이 나빠 발병 보고가 느리다 — 낮은 문턱으로 볼 이유가 더 큰 경우다.

## ★ 이 파일이 막는 것 ★

맥락이 판정으로 미끄러지는 것. 여기서 하는 일은 "빙하 산맥이 있는 나라다"
라는 **지리적 사실**을 붙이는 것이지, "이 홍수는 빙하 때문이다" 라는 원인
규명도 "여기가 위험하다" 는 확률 주장도 아니다.
"""
from __future__ import annotations

import pytest

from algorithms.glacier_regions import (
    GLACIER_REGIONS, coverage_summary, glacier_context, is_glacier_region,
    regions_by_tier,
)


def test_countries_named_by_the_research_are_the_highest_tier():
    """근거가 있는 등급만 최상위에 둔다.

    Nature Communications 2023: 전 세계 1,500만 명 노출, 그중 절반 이상이
    인도·파키스탄·페루·중국. 그 넷이 highest 다.
    """
    assert set(regions_by_tier("highest")) == {"IND", "PAK", "PER", "CHN"}


def test_major_ranges_are_covered():
    """주요 빙하 산맥이 빠지지 않는다."""
    all_ranges = " ".join(r for v in GLACIER_REGIONS.values() for r in v["ranges"])

    for name in ("히말라야", "카라코람", "안데스", "파미르", "톈산",
                 "알프스", "캅카스", "파타고니아"):
        assert name in all_ranges, f"{name} 이 표에서 빠졌다"


def test_andes_is_not_neglected():
    """★핵심★ 안데스를 빼놓지 않는다.

    조사에서 나온 것: 안데스는 고산 아시아와 맞먹는 노출 규모인데 연구는
    거의 없다(2017~2021 연구의 36%가 히말라야). 페루는 세계 3위 노출국이다.
    """
    andes = {k for k, v in GLACIER_REGIONS.items()
             if any("안데스" in r or "파타고니아" in r for r in v["ranges"])}

    assert andes >= {"PER", "BOL", "CHL", "ARG", "ECU", "COL"}
    assert GLACIER_REGIONS["PER"]["exposure"] == "highest"


def test_unknown_country_gets_none_not_an_empty_shell():
    """★핵심★ 빙하가 없는 나라는 None 이다 — 빈 dict 로 채우지 않는다.

    빈 dict 를 돌려주면 화면에서 '빙하 정보 있음'으로 읽힌다.
    """
    assert glacier_context("KOR") is None
    assert glacier_context("") is None
    assert glacier_context("ZZZ") is None
    assert is_glacier_region("KOR") is False


def test_context_never_claims_causation():
    """★★핵심★★ '빙하 때문이다' 라고 말하지 않는다.

    원인 규명은 위성·지진계 분석의 몫이다. 우리가 아는 것은 그 나라에 빙하
    산맥이 있다는 지리뿐이고, 그걸 원인으로 미끄러뜨리면 지어낸 판정이 된다.
    """
    ctx = glacier_context("NPL")

    assert ctx["not_a_prediction"]
    assert "판정이 아니라" in ctx["not_a_prediction"]
    assert "지리적 사실" in ctx["not_a_prediction"]


def test_exposure_tier_is_not_sold_as_probability():
    """등급은 인구 노출 순위이지 발생 확률이 아니다 — 그렇게 밝힌다."""
    limits = " ".join(coverage_summary()["limits"])

    assert "확률이 아니" in limits
    assert "예측하지 않는다" in limits


def test_coverage_states_what_it_cannot_do():
    """무료 실시간 빙하 API 가 없다는 사실을 숨기지 않는다."""
    summary = coverage_summary()

    assert summary["countries"] == len(GLACIER_REGIONS)
    assert summary["basis"], "근거 출처가 없다"
    assert any("실시간" in l for l in summary["limits"])


@pytest.mark.parametrize("iso3", sorted(GLACIER_REGIONS))
def test_every_entry_is_well_formed(iso3):
    """항목마다 산맥과 등급이 있어야 한다 — 반쯤 채운 줄을 두지 않는다."""
    entry = GLACIER_REGIONS[iso3]

    assert len(iso3) == 3 and iso3.isupper()
    assert entry["ranges"], f"{iso3} 에 산맥 이름이 없다"
    assert entry["exposure"] in ("highest", "high", "moderate")


def test_disaster_watch_attaches_the_context():
    """재난 감시창 보고에 실제로 붙는지 — 만들어놓고 안 쓰면 소용없다."""
    import inspect

    from algorithms import disaster_watch

    source = inspect.getsource(disaster_watch.disaster_watch_report)
    assert "glacier_context" in source, "보고에 빙하 맥락을 안 붙이고 있다"
    assert "glacier_regions_watched" in source

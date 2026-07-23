"""BlueDot 대비 벤치마크(㉕) — 인용 기반 비교가 정직하게 계산되는지, 특히
아이기론 실측이 없는 사건(코로나 등)에서 '이겼다'고 절대 주장하지 않는지 확인.
이게 이 기능의 정직성 핵심 — 시스템 부재 시점 사건은 목표 기준선만 표기해야 함."""
from __future__ import annotations

from algorithms.benchmark_baselines import (
    bluedot_record_for, compare_to_bluedot, BLUEDOT_RECORDS,
)


def test_bluedot_record_has_sources_citation():
    """모든 벤치마크 레코드는 검증 가능한 출처 URL을 반드시 가져야 함(지어낸 숫자 금지)."""
    for key, rec in BLUEDOT_RECORDS.items():
        assert rec["sources"], f"{key}에 출처 없음"
        assert all(s.startswith("http") for s in rec["sources"])
        assert rec["lead_days_vs_official"] > 0


def test_unknown_event_has_no_benchmark():
    assert bluedot_record_for("nonexistent") is None
    assert compare_to_bluedot("nonexistent", 5) is None


def test_covid_with_no_aegiron_data_does_not_claim_victory():
    """★ 핵심 정직성 — 아이기론 실측이 없으면(None) '이겼다'가 아니라
    '실측 없음, 목표 기준선만 표기'로 나와야 함."""
    result = compare_to_bluedot("covid19_wuhan_2019", None)
    assert result["aegiron_lead_days"] is None
    assert result["difference_days"] is None
    assert "실측 없음" in result["verdict"]
    assert result["bluedot_lead_days"] == 9


def test_head_to_head_when_aegiron_faster():
    result = compare_to_bluedot("covid19_wuhan_2019", 12)  # 가정: 아이기론 12일 선행
    assert result["difference_days"] == 3  # 12 - 9
    assert "더 빠름" in result["verdict"]


def test_head_to_head_when_bluedot_faster():
    result = compare_to_bluedot("covid19_wuhan_2019", 5)
    assert result["difference_days"] == -4
    assert "블루닷이" in result["verdict"]


def test_head_to_head_tie():
    result = compare_to_bluedot("covid19_wuhan_2019", 9)
    assert result["difference_days"] == 0
    assert "동일" in result["verdict"]

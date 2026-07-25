"""일일 브리핑(㊱) — 방송 러시트 조립·정직성 플래그·조용한 날·이중언어·LLM 폴백.
_gather()를 mock해서 실제 DB/네트워크 없이 조립 로직만 검증한다(교차언어
클러스터링·기존 폴백 테스트와 동일한 격리 방식)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.daily_brief import generate_daily_brief


_ACTIVE = {
    "threats": [
        {"disease": "dengue", "countries": ["BRA", "THA"], "merged_score": 82.0,
         "tier": "high", "source_count": 3, "sources": ["gnews", "who"]},
        {"disease": "measles", "countries": ["USA"], "merged_score": 61.0,
         "tier": "medium", "source_count": 2, "sources": ["cdc"]},
    ],
    "alerts": [{"label": "dengue 급증 브라질", "tier": "high", "score": 82.0, "source": "gnews"}],
    "top_countries": [
        {"country": "BRA", "name": "브라질", "risk_score": 55.0, "tier": "high", "has_signal": True},
    ],
    "name_lookup": {"BRA": "브라질", "THA": "태국", "USA": "미국"},
}

_QUIET = {"threats": [], "alerts": [], "top_countries": [], "name_lookup": {}}


def test_active_day_builds_threat_segments():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko")
    assert brief["quiet_day"] is False
    assert brief["is_official_alert"] is False
    assert brief["generation_method"] == "template_fallback"
    threat_segs = [s for s in brief["segments"] if s["kind"] == "threat"]
    assert len(threat_segs) == 2
    # 각 세그먼트가 방송 3종 세트(대본·자막·화면지시)를 갖췄는지
    for s in threat_segs:
        assert s["anchor_script"]
        assert s["lower_third"]
        assert s["visual_cue"].startswith("map_focus:")
    assert "브라질" in brief["headline"]


def test_quiet_day_stays_quiet():
    """새 위협이 없으면 없다고 말한다 — 방송 채우려 위기 지어내지 않음."""
    with patch("algorithms.daily_brief._gather", return_value=_QUIET):
        brief = generate_daily_brief(lang="ko")
    assert brief["quiet_day"] is True
    assert len(brief["segments"]) == 1
    assert brief["segments"][0]["kind"] == "quiet"
    assert "없" in brief["headline"] or "없" in brief["summary"]


def test_english_version_uses_english_strings():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="en")
    assert brief["lang"] == "en"
    assert "AEGIRON" in brief["program_name"]
    assert "signal" in brief["segments"][0]["anchor_script"].lower()
    assert "official" in brief["disclosure"].lower()


def test_unknown_lang_falls_back_to_korean():
    with patch("algorithms.daily_brief._gather", return_value=_QUIET):
        brief = generate_daily_brief(lang="zz")
    assert brief["lang"] == "ko"


def test_disclosure_always_present_and_marks_ai_and_not_official():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko")
    assert "공식 경보가 아니" in brief["disclosure"]
    assert "AI" in brief["disclosure"]


def test_ticker_includes_country_risk_lines():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko")
    assert any("브라질" in line for line in brief["ticker"])


def test_llm_polish_success_marks_method_and_keeps_structure():
    edited = '[{"segment_id": "threat_1", "anchor_script": "다듬어진 대본"}]'
    fake = MagicMock()
    fake.content = [MagicMock(text=edited)]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", return_value=fake_client):
        brief = generate_daily_brief(lang="ko", api_key="k")
    assert brief["generation_method"] == "llm_polished"
    first = next(s for s in brief["segments"] if s["segment_id"] == "threat_1")
    assert first["anchor_script"] == "다듬어진 대본"
    # 숫자·출처 등 구조는 그대로 유지
    assert first["sources"] == ["gnews", "who"]


def test_llm_polish_failure_falls_back_to_template():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", side_effect=Exception("blocked")):
        brief = generate_daily_brief(lang="ko", api_key="k")
    assert brief["generation_method"] == "template_fallback"
    assert brief["segments"][0]["anchor_script"]  # 원래 템플릿 대본 유지

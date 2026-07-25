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


def test_format_rotates_by_date():
    """매일 같은 형태면 질린다 — 날짜별로 다른 작가(포맷)가 나와야 함."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        ids = {generate_daily_brief(today=f"2026-07-{d:02d}")["format"]["id"]
               for d in range(20, 25)}
    assert len(ids) >= 3  # 5일치에 최소 3종 이상 포맷


def test_format_param_pins_a_specific_writer():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25", fmt="deepdive")
    assert brief["format"]["id"] == "deepdive"
    assert "집중 분석" in brief["segments"][0]["anchor_script"]


def test_available_formats_listed():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25")
    ids = {f["id"] for f in brief["available_formats"]}
    assert ids == {"breaking", "deepdive", "field", "data", "duo"}


def test_facts_unchanged_across_formats():
    """포맷이 달라도 등급·출처·국가 같은 사실은 그대로여야 함."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        a = generate_daily_brief(today="2026-07-25", fmt="breaking")["segments"][0]
        b = generate_daily_brief(today="2026-07-25", fmt="data")["segments"][0]
    assert a["tier"] == b["tier"]
    assert a["sources"] == b["sources"]
    assert a["countries"] == b["countries"]
    assert a["anchor_script"] != b["anchor_script"]  # 말투는 다름


def test_duo_format_has_two_female_presenters_and_dialogue():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25", fmt="duo")
    assert len(brief["presenters"]) == 2
    assert all(p["appearance"]["gender"] == "female" for p in brief["presenters"])
    # 두 진행자는 서로 다른 페르소나(옷도 다름)
    ids = {p["presenter_id"] for p in brief["presenters"]}
    assert len(ids) == 2
    seg = brief["segments"][0]
    assert "dialogue" in seg and len(seg["dialogue"]) == 2


def test_single_format_has_one_presenter():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25", fmt="breaking")
    assert len(brief["presenters"]) == 1


def test_presenter_is_female_synthetic_and_neat():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko", today="2026-07-25")
    p = brief["presenter"]
    assert p["is_synthetic_ai_presenter"] is True   # 실존 인물 아님
    assert p["appearance"]["gender"] == "female"
    assert p["voice"]["gender"] == "female"
    assert "outfit" in p["appearance"]
    # 유튜브 영상 생성 프롬프트에 합성 인물임이 박혀 있어야 함
    assert "not a real person" in p["image_prompt"].lower()


def test_presenter_outfit_rotates_daily_but_face_is_constant():
    """옷은 매일 달라야 하고, 얼굴·헤어·메이크업은 날짜가 바뀌어도 동일해야 함."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        day1 = generate_daily_brief(today="2026-07-25")["presenter"]
        day2 = generate_daily_brief(today="2026-07-26")["presenter"]
    assert day1["appearance"]["outfit"] != day2["appearance"]["outfit"]   # 옷은 매일 다름
    assert day1["appearance"]["hair"] == day2["appearance"]["hair"]       # 얼굴/헤어 고정
    assert day1["appearance"]["makeup"] == day2["appearance"]["makeup"]
    assert day1["presenter_id"] == day2["presenter_id"]                   # 같은 페르소나


def test_presenter_outfit_is_deterministic_for_same_date():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        a = generate_daily_brief(today="2026-07-25")["presenter"]["appearance"]["outfit"]
        b = generate_daily_brief(today="2026-07-25")["presenter"]["appearance"]["outfit"]
    assert a == b  # 같은 날은 재현 가능


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

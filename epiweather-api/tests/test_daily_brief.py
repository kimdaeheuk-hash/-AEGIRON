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
    """새 위협이 없으면 없다고 말한다 — 방송 채우려 위기 지어내지 않음.
    홍보(promo) 세그먼트가 붙어도 quiet_day는 실제 위협 기준으로 True 유지."""
    with patch("algorithms.daily_brief._gather", return_value=_QUIET):
        brief = generate_daily_brief(lang="ko")
    assert brief["quiet_day"] is True
    kinds = [s["kind"] for s in brief["segments"]]
    assert "threat" not in kinds
    assert brief["segments"][0]["kind"] == "quiet"
    assert "없" in brief["headline"] or "없" in brief["summary"]


def test_english_version_uses_english_strings():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="en", fmt="breaking")  # 포맷 고정(날짜 무관 결정론적)
    assert brief["lang"] == "en"
    assert "AEGIRON" in brief["program_name"]
    assert "signal" in brief["segments"][0]["anchor_script"].lower()
    assert "official" in brief["disclosure"].lower()


def test_unknown_lang_falls_back_to_english():
    """모르는 언어의 폴백을 한국어에서 **영어로 바꿨다**(2026-08-06).

    예전엔 한국어로 되돌렸는데, 그 규칙이 프랑스어 요청을 오류 없이 한국어로
    바꿔놓는 원인이었다. 웹에서는 그게 '프랑스어 페이지에 한국어 원문'으로
    드러난다. 이제 프랑스어는 정식 지원하고, 그래도 모르는 언어가 오면 읽을 수
    있는 사람이 더 많은 영어로 보낸다."""
    with patch("algorithms.daily_brief._gather", return_value=_QUIET):
        brief = generate_daily_brief(lang="zz")
    assert brief["lang"] == "en"


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


def test_duo_format_has_anchor_plus_analyst_and_dialogue():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25", fmt="duo")
    assert len(brief["presenters"]) == 2
    roles = {p["role"] for p in brief["presenters"]}
    assert roles == {"anchor", "cohost"}
    # 앵커는 항상 여성, 분석위원은 풀에서 로테이션(성별 다양)
    anchor = next(p for p in brief["presenters"] if p["role"] == "anchor")
    assert anchor["gender"] == "female"
    ids = {p["presenter_id"] for p in brief["presenters"]}
    assert len(ids) == 2
    seg = brief["segments"][0]
    assert "dialogue" in seg and len(seg["dialogue"]) == 2


def test_analyst_pool_has_three_including_one_male():
    from algorithms.daily_brief import _ANALYSTS
    assert len(_ANALYSTS) == 3
    genders = [a["gender"] for a in _ANALYSTS]
    assert genders.count("male") == 1 and genders.count("female") == 2


def test_reporter_pool_is_large_and_mixed_gender():
    """기자 풀이 넉넉해야 매일 다른 기자가 나와 시청자가 질리지 않는다."""
    from algorithms.daily_brief import _REPORTERS
    assert len(_REPORTERS) >= 6
    genders = [r["gender"] for r in _REPORTERS]
    assert genders.count("male") >= 3 and genders.count("female") >= 3


def test_korean_version_uses_korean_faces_english_uses_american():
    """한국판은 한국인, 영어판은 미국인 얼굴로 생성돼야 함."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        ko = generate_daily_brief(lang="ko", today="2026-07-25", fmt="field")
        en = generate_daily_brief(lang="en", today="2026-07-25", fmt="field")
    for p in ko["presenters"]:
        assert p["ethnicity"] == "Korean"
        assert "Korean" in p["image_prompt"]
    for p in en["presenters"]:
        assert p["ethnicity"] == "American"
        assert "American" in p["image_prompt"]


def test_english_names_are_american_not_romanized_korean():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        en = generate_daily_brief(lang="en", today="2026-07-26", fmt="duo")
    analyst = next(p for p in en["presenters"] if p["role"] == "cohost")
    assert analyst["name"] in {"AEGIRON AI Analyst Emma", "AEGIRON AI Analyst Olivia",
                               "AEGIRON AI Analyst James"}


def test_male_presenter_gets_male_voice_and_suit():
    """남성 분석위원이 뽑히는 날엔 남성 목소리·정장(넥타이)로 나와야 함."""
    from algorithms.daily_brief import _presenter_spec, _ANALYSTS
    male = next(a for a in _ANALYSTS if a["gender"] == "male")
    spec = _presenter_spec("2026-07-25", "ko", male)
    assert spec["gender"] == "male"
    assert spec["voice"]["gender"] == "male"
    assert "tie" in spec["appearance"]["outfit"]
    assert "male news presenter" in spec["image_prompt"]


def test_single_format_has_one_presenter():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(today="2026-07-25", fmt="breaking")
    assert len(brief["presenters"]) == 1


def test_field_format_adds_reporter_and_anchor_handoff():
    """현장 리포트는 앵커 + 현장기자 2인이고, 앵커가 현장기자에게 연결하는 대화 구조."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko", today="2026-07-25", fmt="field")
    roles = {p["role"] for p in brief["presenters"]}
    assert roles == {"anchor", "reporter"}
    # 현장기자는 남녀 풀에서 로테이션, 현장(마이크) 세팅
    reporter = next(p for p in brief["presenters"] if p["role"] == "reporter")
    assert reporter["gender"] in {"male", "female"}
    assert "microphone" in reporter["image_prompt"]
    # 위협 세그먼트가 앵커→현장기자 대화로 구성
    seg = next(s for s in brief["segments"] if s["kind"] == "threat")
    speakers = {d["speaker"] for d in seg["dialogue"]}
    assert speakers == {"anchor", "reporter"}


def test_promo_segment_appended_and_separated_from_news():
    """작가가 뉴스 끝에 아이기론을 홍보하되, 실제 발병 보도와 kind로 분리돼야 함."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko", today="2026-07-25")
    promo = [s for s in brief["segments"] if s["kind"] == "promo"]
    assert len(promo) == 1
    assert promo[0]["segment_id"] == "about"
    assert "아이기론" in promo[0]["lower_third"]  # 브랜드 자막으로 소개임을 명시
    assert promo[0]["anchor_script"].strip()
    # 홍보는 위협 등급·출처를 달지 않는다(가짜 경보로 안 보이게)
    assert promo[0]["tier"] is None and promo[0]["sources"] == []


def test_promo_point_rotates_and_marks_future_as_roadmap():
    """홍보 포인트는 날짜별로 다르고, 미래 항목은 '계획'으로 정직하게 표시."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        scripts = {generate_daily_brief(today=f"2026-07-{d:02d}")["segments"][-1]["anchor_script"]
                   for d in range(1, 9)}
        # 미래(로드맵) 포인트가 뜨는 날엔 '계획' 표기가 있어야 함
        future_days = [generate_daily_brief(today=f"2026-07-{d:02d}")["segments"][-1]
                       for d in range(1, 9)]
    assert len(scripts) >= 4  # 8일치에 최소 4종 이상 홍보 포인트
    for seg in future_days:
        if seg.get("is_future"):
            assert "계획" in seg["anchor_script"] or "roadmap" in seg["anchor_script"]


def test_podcast_block_assembles_audio_timeline_with_voices():
    """팟캐스트 에피소드 형태 — 화자별 목소리가 붙은 대사 순서 리스트. 오디오는
    아이기론이 만들지 않고(페이퍼클립 위임) 재료만 준다."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko", today="2026-07-25", fmt="duo")
    pod = brief["podcast"]
    assert pod["title"] == brief["headline"]
    assert pod["language"] == "ko-KR"
    assert pod["cadence"] == "daily"
    tl = pod["audio_timeline"]
    assert len(tl) >= 3
    # 각 라인은 화자·목소리·텍스트를 갖춤 (TTS 반복문으로 바로 합성 가능)
    for entry in tl:
        assert entry["text"].strip()
        assert entry["voice"]["gender"] in {"male", "female"}
        assert entry["presenter_id"]
    # 마지막 줄은 고지(소리로도 읽힘)
    assert tl[-1]["text"] == brief["disclosure"]
    # 대담 포맷이면 두 화자가 audio_timeline에 등장
    speakers = {e["speaker"] for e in tl}
    assert "anchor" in speakers and "cohost" in speakers


def test_podcast_english_uses_en_us_language():
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="en", today="2026-07-25")
    assert brief["podcast"]["language"] == "en-US"


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
    assert day1["appearance"]["grooming"] == day2["appearance"]["grooming"]
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

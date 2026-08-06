"""브리핑 다국어 — 조용히 다른 언어가 섞여 나가지 않는지 확인.

배경(실측 2026-08-06): 이 모듈은 원래 `lang`이 'ko'가 아니면 무조건 영어를 쓰는
2분기 구조였고, 게이트가 `lang if lang in ("ko","en") else "ko"`라 **프랑스어를
요청하면 오류 없이 한국어가 돌아왔다.** 웹에서 그대로 렌더링하면 프랑스어 페이지에
한국어 원문이 아무 설명 없이 실린다 — 조용히 틀리는 실패라 가장 위험하다.

또 문장만 번역하고 고유명사를 놔두면 읽는 사람에게는 번역이 안 된 것과 같다.
실제로 이렇게 나왔다: "watching 오즈 바이러스 signal in 한국"
"""
from __future__ import annotations

import pytest

from algorithms import daily_brief as db
from algorithms.name_i18n import disease_name, country_name


# ── 언어 표 완결성 ────────────────────────────────────────────────
def test_all_language_tables_are_complete():
    """★핵심★ 표 하나에 키를 빠뜨리면 그 자리만 다른 언어로 조용히 섞인다.
    가져오기 시점에 죽는 편이 배포 후 발견하는 것보다 낫다."""
    db._assert_lang_tables()   # 누락이 있으면 RuntimeError


def test_french_is_supported():
    assert "fr" in db.SUPPORTED_LANGS


@pytest.mark.parametrize("lang", ["ko", "en", "fr"])
def test_requested_language_is_the_language_returned(lang, isolated_db):
    """★회귀★ 요청한 언어가 그대로 나와야 한다. 예전에는 fr → ko로 조용히 바뀌었다."""
    brief = db.generate_daily_brief(lang=lang)
    assert brief["lang"] == lang
    assert brief["program_name"] == db._PROGRAM_NAME[lang]
    assert brief["podcast"]["language"] == db._AUDIO_LOCALE[lang]


def test_unknown_language_falls_back_to_english_not_korean(isolated_db):
    """모르는 언어는 영어로 — 한국어로 되돌리면 읽을 수 있는 사람이 더 적다."""
    brief = db.generate_daily_brief(lang="de")
    assert brief["lang"] == db.FALLBACK_LANG == "en"


# ── 고유명사 지역화 ───────────────────────────────────────────────
def test_disease_names_are_localised():
    assert disease_name("에볼라", "en") == "Ebola"
    assert disease_name("에볼라", "fr") == "Ebola"
    assert disease_name("홍역", "fr") == "rougeole"
    assert disease_name("말라리아", "fr") == "paludisme"
    assert disease_name("Lassa fever", "ko") == "라싸열"


def test_unknown_disease_keeps_its_original_name():
    """★정직성★ 모르는 병명을 어설프게 옮기면 다른 병으로 읽힐 수 있다.
    원문이 남아 있으면 최소한 검색은 되고 번역 누락도 눈에 보인다."""
    assert disease_name("Xyzzy fever", "fr") == "Xyzzy fever"
    assert disease_name(None, "fr") is None


def test_unknown_cause_variants_collapse():
    """'원인 미상의 폐렴·중증 호흡기 질환' 같은 긴 표기도 잡아야 한다."""
    for raw in ("원인 미상의 폐렴·중증 호흡기 질환", "원인불명 호흡기 질환/폐렴", "원인불명 신호"):
        assert disease_name(raw, "en") == "disease of unknown cause"
        assert disease_name(raw, "fr") == "maladie d’origine inconnue"


def test_ebola_subtype_is_recognised_across_spellings():
    for raw in ("Ebola (Bundibugyo)", "에볼라(Bundibugyo virus)", "붕디부고 에볼라 바이러스"):
        assert "Bundibugyo" in disease_name(raw, "en")


def test_country_names_are_localised():
    assert country_name("UGA", "fr") == "Ouganda"
    assert country_name("COD", "fr") == "RD Congo"
    assert country_name("KOR", "en") == "South Korea"
    assert country_name("KOR", "ko") == "한국"


def test_unknown_country_falls_back_without_inventing():
    assert country_name("ZZZ", "fr", fallback="Somewhere") == "Somewhere"
    assert country_name(None, "fr") == ""


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_korean_leaks_into_foreign_briefing(lang, isolated_db):
    """★핵심 회귀★ 문장만 번역하고 병명·국가명을 놔두면 읽는 사람에게는 번역이
    안 된 것과 같다. 실측 사례: "watching 오즈 바이러스 signal in 한국"."""
    import re
    hangul = re.compile(r"[가-힣]")
    brief = db.generate_daily_brief(lang=lang)

    checked = [brief["headline"], brief["summary"], brief["closing"], brief["disclosure"]]
    checked += brief["ticker"]
    checked += [s.get("anchor_script") or "" for s in brief["segments"]]
    checked += [s.get("lower_third") or "" for s in brief["segments"]]

    leaked = [t for t in checked if t and hangul.search(t)]
    assert not leaked, f"{lang} 브리핑에 한국어가 남았다: {leaked[:3]}"

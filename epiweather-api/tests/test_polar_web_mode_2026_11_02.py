"""극지 영토 감시 카드의 수집주기 표기가 실제 주기(매시간)와 일치한다 (2026-11-02).

스케줄러(`main.py` `_FREE_INTERVAL_SEC = 3600` + 정시 대기)는 극지를 매시간
수집하는데, 웹 사전 3종은 `mode: 'daily'`(→ '매일 자동')로 표기하고 있었다.
수집주기를 속이면 "어제 자료"로 오해한다. 웹에 유닛 러너가 없으니 pytest에서
사전 파일을 직접 읽어 고정한다.
"""
from __future__ import annotations

import pathlib
import re

WEB_DICT = (pathlib.Path(__file__).parent.parent.parent
            / "epiweather-web" / "src" / "i18n" / "dict")


def _polar_mode(lang: str) -> str:
    text = (WEB_DICT / f"{lang}.ts").read_text(encoding="utf-8")
    m = re.search(r"id: 'polar_signals',\s*name: '.*?',\s*body: '.*?',\s*mode: '(\w+)'",
                  text, re.S)
    assert m, f"{lang}.ts에 polar_signals 카드가 없음"
    return m.group(1)


def test_polar_card_says_hourly_in_all_three_languages():
    assert {lang: _polar_mode(lang) for lang in ("ko", "en", "fr")} == {
        "ko": "hourly", "en": "hourly", "fr": "hourly"}


def test_hourly_label_exists_so_the_mode_is_not_a_dangling_key():
    """mode 값이 사전의 engineModes에 없으면 화면에 빈 문자열이 나간다."""
    for lang in ("ko", "en", "fr"):
        text = (WEB_DICT / f"{lang}.ts").read_text(encoding="utf-8")
        assert re.search(r"hourly: '[^']+'", text), f"{lang}.ts에 hourly 라벨 없음"

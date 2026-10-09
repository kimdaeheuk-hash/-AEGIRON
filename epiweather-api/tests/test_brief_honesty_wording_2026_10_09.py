"""브리핑 문구 두 가지 — AI가 뽑은 사람 수와 개발자 문구 (2026-10-09 브리핑 검토).

## 무엇이 보였나
브리핑이 이렇게 나갔다:

    • 아프리카 CDC 확진: 8,625명 → 14일 후 7,961명
    조건1(병원방문 급증)은 증후군감시 데이터 소스가 없어 측정 불가 — 조건2·3은 추출 시점에
    모델이 직접 판단한 known_disease 필드로 판정함. source='unexplained_cluster'(능동 검색)가 …
    … thaw_days는 기후 정상값 대비 이상이 아니라 해빙 활동 프록시.

1. 사람 수처럼 읽히는 숫자가 **줄어든다.** 그 값은 웹 검색 문장에서 AI 가 뽑은 것이고 코드 스스로
   "누적값인지 주간값인지 확인하지 않았다"(negative_space.py)고 적어둔 지표다. 브리핑은 사람 숫자를
   맨 앞에 세우고 폰은 "명"을 붙인다 — 고지가 없으면 나아지는 상황처럼 읽힌다.
2. 개발자용 문구(`known_disease`, `unexplained_cluster`, `alerts.py`, `thaw_days`)가 읽는 사람에게
   그대로 나갔다. 정직성은 지켜졌지만 암호였다.

## 이 파일이 막아야 하는 것
- 고지가 **필요 없는 자리에 붙는 것**(경고 피로)도, **필요한 자리에서 빠지는 것**도.
- 고지가 손으로 적은 지표 이름 목록에 매달리는 것 — 카테고리 표가 바뀌면 같이 바뀌어야 한다.
- 폰(텔레그램)이 이 고지를 빼먹는 것(2026-09-20 출구 감사에서 한 번 겪었다).
- 사람용 문장에 식별자가 다시 섞이는 것.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from algorithms import brief_sections as bs
from algorithms import notifier
from algorithms import polar_signals
from algorithms import signal_metrics

LANGS = ("ko", "en", "fr")

# 사람이 읽는 문장에 있으면 안 되는 모양: snake_case 식별자 · 파일명 · 키=값
JARGON = re.compile(r"[a-z]+_[a-z0-9_]+|\.py\b|\bsource\s*=")


def _forecast_payload(metrics):
    return {
        "score_7d": 51.2, "score_14d": 51.5, "tier_7d": "정상", "tier_14d": "정상",
        "confidence": "medium",
        "top_alerts": [
            {"metric": m, "layer": "informal", "current_val": 8625.0,
             "forecast_7d": {"val": 8300.0}, "forecast_14d": {"val": 7961.0}}
            for m in metrics
        ],
    }


def _forecast(metrics, lang="ko"):
    with patch("algorithms.forecast_engine.forecast_summary", return_value=_forecast_payload(metrics)):
        return bs.build_forecast_section(lang)


# ── 1. AI 가 뽑은 사람 수는 그렇다고 말한다 ───────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_ai_extracted_people_count_carries_the_note(lang):
    sec = _forecast(["africa_cdc_confirmed", "africa_cdc_deaths"], lang)
    assert sec["honesty"].endswith(bs._FORECAST_AI_COUNT_NOTE[lang])
    assert sec["honesty"].startswith(bs._FORECAST_HONESTY[lang])           # 기존 고지는 그대로 앞에 있다
    assert all(r["counts_people"] and r["ai_extracted"] for r in sec["rows"])


def test_the_korean_note_says_what_is_not_known_and_what_a_decline_does_not_mean():
    note = bs._FORECAST_AI_COUNT_NOTE["ko"]
    assert "AI" in note and "웹 검색" in note
    assert "누적" in note and "주간" in note and "확인하지 않았" in note
    assert "나아진다는 뜻이 아닙니다" in note


def test_no_note_when_the_people_count_is_not_ai_extracted():
    """경고 피로 — 사람 수 지표라도 AI 추출이 아니면 이 고지를 붙이지 않는다."""
    sec = _forecast(["kdca_confirmed_cases"])                               # 'cases' → 사람 수, 레지스트리엔 없음
    assert sec["rows"][0]["counts_people"] is True and sec["rows"][0]["ai_extracted"] is False
    assert sec["honesty"] == bs._FORECAST_HONESTY["ko"]


def test_no_note_when_an_ai_extracted_metric_is_not_a_people_count():
    sec = _forecast(["local_news_llm_relevant"])                            # AI 추출이지만 사람 수가 아니다
    assert sec["rows"][0]["ai_extracted"] is True and sec["rows"][0]["counts_people"] is False
    assert sec["honesty"] == bs._FORECAST_HONESTY["ko"]


def test_one_ai_people_row_among_others_is_enough_to_attach_the_note():
    sec = _forecast(["kdca_weekly_total", "kdca_confirmed_cases", "africa_cdc_confirmed"])
    assert sec["honesty"].endswith(bs._FORECAST_AI_COUNT_NOTE["ko"])


def test_ai_flag_is_read_from_the_category_table_not_from_a_hand_written_list(monkeypatch):
    assert bs._is_ai_extracted("africa_cdc_confirmed") is True
    assert bs._is_ai_extracted("kdca_weekly_total") is False
    assert bs._is_ai_extracted("no_such_metric") is False
    assert bs._is_ai_extracted(None) is False

    # 카테고리 표를 바꾸면 따라 바뀐다 — 이름 목록에 매달려 있지 않다는 증거
    patched = {k: {**v, "metrics": [(m[0], m[1], m[2], "government" if m[0] == "africa_cdc_confirmed" else m[3])
                                    for m in v["metrics"]]}
               for k, v in signal_metrics.LAYERS.items()}
    monkeypatch.setattr(signal_metrics, "LAYERS", patched)
    assert bs._is_ai_extracted("africa_cdc_confirmed") is False
    assert _forecast(["africa_cdc_confirmed"])["honesty"] == bs._FORECAST_HONESTY["ko"]


def test_the_phone_message_carries_the_note_right_under_the_numbers():
    """폰은 rows 에 '명' 을 붙인다. 그 바로 아래 honesty 가 같이 가야 한다(2026-09-20 출구 감사)."""
    sec = _forecast(["africa_cdc_confirmed", "africa_cdc_deaths"])
    lines = "\n".join(notifier._special_lines({"special_sections": [sec]}))
    assert "8,625명" in lines and "7,961명" in lines
    note = "웹 검색 결과 문장에서 AI가 뽑은 값이며, 누적 수치인지 주간 수치인지 확인하지 않았습니다"
    assert note in lines
    assert lines.index("7,961명") < lines.index(note)                       # 숫자 아래에 붙는다


# ── 2. 개발자 문구가 사용자 문장에 없다 ───────────────────────────────────

DEV_CAVEAT = ("조건1(병원방문 급증)은 증후군감시 데이터 소스가 없어 측정 불가 — 조건2·3은 추출 시점에 "
              "모델이 직접 판단한 known_disease 필드로 판정함. source='unexplained_cluster'(능동 검색)가 "
              "아닌 다른 출처는 … alerts.py는 그래서 unexplained_cluster만 즉시경보로 올림.")


def _unexplained(lang):
    payload = {"alerts": [{"source": "unexplained_cluster", "location": "러시아 시베리아",
                           "signal_date": "2026-10-01", "tier": "🔴 즉시경보", "message": "m"}],
               "caveat": DEV_CAVEAT}
    with patch("algorithms.unexplained.scan_unexplained", return_value=payload):
        return bs.build_unexplained_section(lang)


@pytest.mark.parametrize("lang", LANGS)
def test_unexplained_honesty_is_a_human_sentence_and_not_the_api_caveat(lang):
    sec = _unexplained(lang)
    assert sec["honesty"] == bs._UNEXPLAINED_HONESTY[lang]
    assert sec["honesty"] != DEV_CAVEAT
    assert not JARGON.search(sec["honesty"]), JARGON.search(sec["honesty"])


def test_the_korean_unexplained_text_keeps_all_three_facts():
    t = bs._UNEXPLAINED_HONESTY["ko"]
    assert "증후군 감시 데이터가 연결돼 있지 않아" in t and "확인하지 못합니다" in t     # (1) 병원 방문은 못 잰다
    assert "AI가" in t and "의료기관의 확인이 아닙니다" in t                              # (2) 판정은 AI 의 판단
    assert "능동 검색" in t and "즉시경보" in t and "오탐 가능성이 더 높" in t           # (3) 즉시경보 조건·오탐


def test_the_api_caveat_for_developers_is_left_alone(isolated_db):
    """브리핑만 사람 말로 바꿨다 — /api 의 caveat 는 개발자용으로 그대로 둔다."""
    from algorithms import unexplained
    out = unexplained.scan_unexplained()
    assert "known_disease" in out["caveat"] and "증후군감시 데이터 소스가 없어" in out["caveat"]


def _constant_value_of_key(module, key):
    """모듈 소스에서 `"key": "<문자열>"` 의 문자열을 AST 로 읽는다(실제 프로덕션 문구)."""
    tree = ast.parse(Path(inspect.getsourcefile(module)).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Constant) \
                        and isinstance(v.value, str):
                    return v.value
    raise AssertionError(f"{key} 문구를 못 찾았다")


@pytest.mark.parametrize("key", ["note", "disclaimer"])
def test_the_production_polar_text_has_no_identifiers(key):
    """실제 프로덕션 문구를 읽는다 — 시험이 자기가 만든 입력만 검사하면 이 사고를 못 잡는다."""
    text = _constant_value_of_key(polar_signals, key)
    assert not JARGON.search(text), JARGON.search(text)


def test_the_polar_disclaimer_keeps_its_meaning():
    text = _constant_value_of_key(polar_signals, "disclaimer")
    assert "해빙일 수는" in text and "프록시" in text and "기후 정상값 대비 이상이 아니라" in text


def test_no_prose_field_of_any_section_carries_an_identifier():
    """한 번에 전부 — 섹션 산문(lead·why·honesty·title·data_source)에 식별자가 다시 섞이면 걸린다."""
    polar = {"regions": [{"region": "siberia_yamal", "name": "시베리아 야말(러시아)",
                          "thaw": {"permafrost_thaw_pressure": 60.0, "thaw_days_30d": 30, "heat_trend_c": -14.5},
                          "news": {"sample_titles": []}}],
             "grade": "watch",
             "note": _constant_value_of_key(polar_signals, "note"),
             "disclaimer": _constant_value_of_key(polar_signals, "disclaimer"),
             "data_source": "Open-Meteo(기온) + Google News(극지 질병 뉴스)"}
    with patch("algorithms.polar_signals.polar_watch_all", return_value=polar), \
         patch("algorithms.forecast_engine.forecast_summary",
               return_value=_forecast_payload(["africa_cdc_confirmed"])), \
         patch("algorithms.unexplained.scan_unexplained",
               return_value={"alerts": [{"source": "unexplained_cluster", "signal_date": "2026-10-01"}],
                             "caveat": DEV_CAVEAT}):
        sections = {s["id"]: s for s in bs.build_special_sections("ko")}
    for sid in ("polar", "forecast", "unexplained"):
        for field in ("title", "lead", "why", "honesty"):
            text = sections[sid].get(field)
            if text:
                assert not JARGON.search(text), f"{sid}.{field}: {JARGON.search(text).group(0)}"

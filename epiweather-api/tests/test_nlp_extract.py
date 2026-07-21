"""NLP 구조화 추출 — country_iso3 필드가 모델 오출력에도 안전하게 정규화되는지 확인.
별칭사전 없이 전세계 매칭이 가능해지려면 이 검증이 핵심(잘못된 형식이 그대로
DB에 들어가면 하류 매칭이 전부 깨짐)."""
from __future__ import annotations

import json
from unittest.mock import patch

import anthropic

from algorithms.nlp_extract import extract_signal, extract_from_global_watch


class _FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, payload: dict):
        self.content = [_FakeBlock(json.dumps(payload, ensure_ascii=False))]


class _FakeMessages:
    def __init__(self, payload: dict):
        self._payload = payload

    def create(self, **kwargs):
        return _FakeResponse(self._payload)


class _FakeClient:
    def __init__(self, payload: dict):
        self.messages = _FakeMessages(payload)


def _stub_client(monkeypatch, payload: dict):
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: _FakeClient(payload))


def _base_payload(**overrides) -> dict:
    payload = {
        "disease": "에볼라", "location": "콩고민주공화국", "signal_type": "신규발생",
        "severity": ["spike"], "symptom": None, "transmission": None,
        "date": None, "known_disease": True,
    }
    payload.update(overrides)
    return payload


def test_valid_iso3_code_is_kept(monkeypatch):
    _stub_client(monkeypatch, _base_payload(country_iso3="COD"))
    result = extract_signal("텍스트", source="who_emro", api_key="fake")
    assert result["country_iso3"] == "COD"


def test_lowercase_iso3_is_rejected_not_coerced(monkeypatch):
    """모델이 소문자로 출력해도 임의로 대문자 변환하지 않고 null로 버림 —
    형식이 안 맞으면 잘못된 값을 추측 보정하지 않는다는 정직성 원칙."""
    _stub_client(monkeypatch, _base_payload(country_iso3="cod"))
    result = extract_signal("텍스트", source="who_emro", api_key="fake")
    assert result["country_iso3"] is None


def test_full_country_name_is_rejected(monkeypatch):
    _stub_client(monkeypatch, _base_payload(country_iso3="Congo"))
    result = extract_signal("텍스트", source="who_emro", api_key="fake")
    assert result["country_iso3"] is None


def test_missing_country_iso3_defaults_to_none(monkeypatch):
    payload = _base_payload()
    payload.pop("country_iso3", None)
    _stub_client(monkeypatch, payload)
    result = extract_signal("텍스트", source="who_emro", api_key="fake")
    assert result["country_iso3"] is None


def test_null_country_iso3_for_multi_country_text_stays_none(monkeypatch):
    """"아프리카 전역"처럼 국가 하나로 특정 안 되는 텍스트는 모델이 null을
    내야 하고, 그 null이 그대로 보존돼야 함(억지로 국가를 채우지 않음)."""
    _stub_client(monkeypatch, _base_payload(location="아프리카 전역", country_iso3=None))
    result = extract_signal("텍스트", source="africa_cdc", api_key="fake")
    assert result["country_iso3"] is None


# ── 중복 원문 재추출 방지 ────────────────────────────────────────


def test_new_text_from_never_seen_source_is_extracted(isolated_db):
    """처음 보는 원문은 당연히 Claude를 호출해야 함."""
    watch = {"signals": [{"id": "who_emro", "text": "새로운 기사 내용"}]}
    with patch("algorithms.nlp_extract.extract_signal") as mock_extract:
        mock_extract.return_value = {"source": "who_emro", "disease": "에볼라"}
        result = extract_from_global_watch(watch, api_key="fake")
    mock_extract.assert_called_once()
    assert len(result) == 1


def test_identical_text_from_same_source_within_window_is_skipped(isolated_db):
    """같은 source가 최근에 뽑아낸 것과 원문이 완전히 같으면 Claude를 다시
    호출하지 않아야 함 — 고정 피드가 매시간 같은 기사를 다시 줄 때 비용 낭비 방지."""
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who_emro", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date="2026-07-20", raw_text="이미 본 기사 내용",
    )
    watch = {"signals": [{"id": "who_emro", "text": "이미 본 기사 내용"}]}
    with patch("algorithms.nlp_extract.extract_signal") as mock_extract:
        result = extract_from_global_watch(watch, api_key="fake")
    mock_extract.assert_not_called()
    assert result == []


def test_updated_text_from_same_source_is_still_extracted(isolated_db):
    """같은 source라도 원문이 바뀌었으면(기사 갱신) 재추출해야 함 —
    완전 일치만 건너뛰므로 실제 갱신을 놓치지 않음."""
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who_emro", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date="2026-07-20", raw_text="어제 기사 내용",
    )
    watch = {"signals": [{"id": "who_emro", "text": "오늘 갱신된 기사 내용"}]}
    with patch("algorithms.nlp_extract.extract_signal") as mock_extract:
        mock_extract.return_value = {"source": "who_emro", "disease": "에볼라"}
        result = extract_from_global_watch(watch, api_key="fake")
    mock_extract.assert_called_once()
    assert len(result) == 1


def test_same_text_from_different_source_is_not_deduped(isolated_db):
    """같은 문구라도 source가 다르면(예: 다른 기관이 우연히 같은 표현) 독립
    출처로 취급 — source별로 최근기록을 따로 조회하므로 안전함."""
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who_emro", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date="2026-07-20", raw_text="공통 문구",
    )
    watch = {"signals": [{"id": "africa_cdc", "text": "공통 문구"}]}
    with patch("algorithms.nlp_extract.extract_signal") as mock_extract:
        mock_extract.return_value = {"source": "africa_cdc", "disease": "에볼라"}
        result = extract_from_global_watch(watch, api_key="fake")
    mock_extract.assert_called_once()
    assert len(result) == 1

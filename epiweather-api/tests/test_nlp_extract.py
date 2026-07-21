"""NLP 구조화 추출 — country_iso3 필드가 모델 오출력에도 안전하게 정규화되는지 확인.
별칭사전 없이 전세계 매칭이 가능해지려면 이 검증이 핵심(잘못된 형식이 그대로
DB에 들어가면 하류 매칭이 전부 깨짐)."""
from __future__ import annotations

import json

import anthropic

from algorithms.nlp_extract import extract_signal


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

"""갭 #7 — sensitive OR 게이팅 + 로컬 추출 실구현.

sensitive 인자를 예전엔 읽지 않아 민감 표시를 해도 외부로 나갔다.
전부 mock. 외부 HTTP 없음.
"""
from __future__ import annotations

from unittest.mock import patch

from algorithms import aegiron_model as am


def _reset(monkeypatch):
    monkeypatch.setattr(am, "_LOCAL_MODEL", None)
    monkeypatch.setattr(am, "_LOCAL_TRIED", False)
    monkeypatch.setattr(am, "_REASONING_EFFORT_REJECTED", False)
    monkeypatch.delenv(am.REQUIRE_LOCAL_ENV, raising=False)
    monkeypatch.delenv(am.LOCAL_MODEL_PATH_ENV, raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)


_JSON = ('{"disease": "에볼라", "location": "DRC", "signal_type": "신규발생",'
         ' "severity": ["사망"], "symptom": null, "transmission": null,'
         ' "country_iso3": null, "date": null, "known_disease": true}')


def test_sensitive_alone_blocks_external(monkeypatch):
    """REQUIRE_LOCAL이 꺼져 있어도 sensitive=True면 외부는 차단."""
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("algorithms.nlp_extract.extract_signal_detailed") as m:
        r = am.extract_signal("민감 텍스트", sensitive=True)
    m.assert_not_called()
    assert r["blocked"] is True
    assert r["ai_provider"] == "local_required_unavailable"
    assert "sensitive=True" in r["reason"]
    assert "REQUIRE_LOCAL" not in r["reason"]  # 건 것은 sensitive뿐


def test_nonsensitive_still_falls_back(monkeypatch):
    """민감 아니면 기존처럼 외부 폴백(동작 불변)."""
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("algorithms.nlp_extract.extract_signal_detailed",
               return_value=({"disease": "에볼라"}, None)):
        r = am.extract_signal("공개 뉴스", sensitive=False)
    assert r["ai_provider"] == "external_llm_fallback"
    assert r.get("blocked") is not True


def test_sensitive_passes_on_sovereign_path(monkeypatch):
    """민감 표시라도 주권 경로(자체호스팅)는 쓴다 — 차단은 외부가 대상."""
    _reset(monkeypatch)
    monkeypatch.setenv("AEGIRON_NIM_API_KEY", "nim-key")
    monkeypatch.setenv(am.NIM_BASE_URL_ENV, "https://nim.internal/v1")

    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": _JSON}}],
                    "usage": {}}

    with patch("requests.post", return_value=_R()):
        r = am.extract_signal("민감 텍스트", sensitive=True)
    assert r["ai_provider"] == "aegiron_nim_selfhosted"
    assert r.get("blocked") is not True


def test_require_local_trigger_named(monkeypatch):
    """차단 사유에 무엇이 막았는지 남는다."""
    _reset(monkeypatch)
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    r = am.extract_signal("공개 뉴스", sensitive=False)
    assert r["blocked"] is True
    assert "AEGIRON_REQUIRE_LOCAL=on" in r["reason"]


def test_local_pipeline_extracts(monkeypatch):
    """로컬 파이프라인 실구현 — NIM/Meta와 같은 스키마로 나온다."""
    _reset(monkeypatch)
    fake = lambda prompt, **kw: [{"generated_text": _JSON}]
    monkeypatch.setattr(am, "_load_local_model", lambda: fake)
    out = am._local_extract("DRC 에볼라", "test-src")
    assert out is not None
    assert out["disease"] == "에볼라" and out["source"] == "test-src"
    assert out["signal_type"] == "신규발생"


def test_local_pipeline_strips_prompt_echo(monkeypatch):
    """프롬프트를 되뇌는 파이프라인도 파싱된다."""
    _reset(monkeypatch)
    from algorithms.nlp_extract import build_prompt

    def fake(prompt, **kw):
        return [{"generated_text": prompt + _JSON}]

    monkeypatch.setattr(am, "_load_local_model", lambda: fake)
    out = am._local_extract("DRC 에볼라", "test-src")
    assert out is not None and out["disease"] == "에볼라"


def test_local_pipeline_garbage_falls_through(monkeypatch):
    """로컬 출력이 깨지면 None — 다음 경로로 넘어간다."""
    _reset(monkeypatch)
    fake = lambda prompt, **kw: [{"generated_text": "not json"}]
    monkeypatch.setattr(am, "_load_local_model", lambda: fake)
    assert am._local_extract("DRC 에볼라") is None


def test_local_model_absent_is_none(monkeypatch):
    """모델 없으면 None(기존 폴백 흐름 그대로)."""
    _reset(monkeypatch)
    monkeypatch.setattr(am, "_load_local_model", lambda: None)
    assert am._local_extract("DRC 에볼라") is None


def test_local_extract_wired_into_flow(monkeypatch):
    """추출 흐름 ③에서 로컬이 쓰인다."""
    _reset(monkeypatch)
    fake = lambda prompt, **kw: [{"generated_text": _JSON}]
    monkeypatch.setattr(am, "_load_local_model", lambda: fake)
    r, _ = am.extract_signal_detailed("DRC 에볼라", source="who")
    assert r["ai_provider"] == "aegiron_local"
    assert r["data_sovereign"] is True

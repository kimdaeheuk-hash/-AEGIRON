"""모델 추상화 계층(독자 API 구조) — 로컬 우선→LLM 폴백, 주권 게이팅.
지금은 로컬 모델이 없어 폴백이 정상이며 그 사실을 정직하게 표시하는지 확인."""
from __future__ import annotations
from unittest.mock import patch

import algorithms.aegiron_model as am


def _reset(monkeypatch):
    # 로컬모델 로딩 캐시 초기화(테스트 격리)
    am._LOCAL_MODEL = None
    am._LOCAL_TRIED = False
    monkeypatch.delenv(am.LOCAL_MODEL_PATH_ENV, raising=False)
    monkeypatch.delenv(am.REQUIRE_LOCAL_ENV, raising=False)


def test_provider_status_falls_back_when_no_local(monkeypatch):
    _reset(monkeypatch)
    s = am.provider_status()
    assert s["active_provider"] == "external_llm_fallback"
    assert s["local_model_configured"] is False
    assert s["local_model_loaded"] is False


def test_extract_uses_llm_fallback_and_tags_provider(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("algorithms.nlp_extract.extract_signal", return_value={"disease": "에볼라"}) as m:
        r = am.extract_signal("DRC 에볼라 발생", source="who")
    m.assert_called_once()
    assert r["disease"] == "에볼라"
    assert r["ai_provider"] == "external_llm_fallback"   # 폴백임을 정직하게 표시


def test_sensitive_data_blocked_when_require_local(monkeypatch):
    """국가 주권 요건: 민감 데이터인데 로컬 모델 없고 REQUIRE_LOCAL=on이면 외부
    폴백을 차단(국외유출 방지). 지어내지 않고 blocked로 정직 표시."""
    _reset(monkeypatch)
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    r = am.extract_signal("민감 유전체 데이터", sensitive=True)
    assert r["blocked"] is True
    assert r["ai_provider"] == "local_required_unavailable"


def test_no_key_and_no_local_reports_unavailable(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = am.extract_signal("텍스트")
    assert r["ai_provider"] == "unavailable"

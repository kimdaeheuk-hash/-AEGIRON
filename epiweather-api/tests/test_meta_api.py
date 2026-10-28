"""Meta Model API 추출 경로 — 규약·배선·게이팅.

Meta 키가 있으면 NIM 다음 홉으로 Muse Spark를 시도한다(해커톤 제출 요건).
외부 호출은 전부 mock 한다(conftest 가드가 실제 HTTP를 막는다).
"""
from __future__ import annotations
from unittest.mock import patch

import algorithms.aegiron_model as am
from algorithms import meta_api
from algorithms import capability_ledger as cl


def _reset(monkeypatch):
    am._LOCAL_MODEL = None
    am._LOCAL_TRIED = False
    for env in [am.LOCAL_MODEL_PATH_ENV, am.REQUIRE_LOCAL_ENV, am.NIM_BASE_URL_ENV,
                am.NIM_MODEL_ENV, am._nvidia.ONPREM_BASE_ENV, am.META_FIRST_ENV,
                am.META_EXTRACT_ENV, meta_api.KEY_ENV, meta_api.DOC_KEY_ENV,
                meta_api.BASE_URL_ENV, meta_api.MODEL_ENV, "ANTHROPIC_API_KEY",
                *am.NIM_API_KEY_ENVS]:
        monkeypatch.delenv(env, raising=False)


def _resp(payload_json=None, *, finish_reason="stop", usage=None):
    """requests.post가 돌려줄 가짜 응답(OpenAI 호환 스키마)."""
    message = {} if payload_json is None else {"content": payload_json}
    body = {"choices": [{"message": message, "finish_reason": finish_reason}]}
    if usage is not None:
        body["usage"] = usage

    class _R:
        def raise_for_status(self):
            return None

        def json(self):
            return body
    return _R()


_META_JSON = ('{"disease": "에볼라", "location": "DRC", "country_iso3": "COD", '
              '"signal_type": "신규발생", "severity": ["spike"], "symptom": null, '
              '"transmission": null, "date": null, "known_disease": true}')


# ── 규약 단일 소스 ──

def test_key_prefers_dedicated_name_then_doc_name(monkeypatch):
    _reset(monkeypatch)
    assert meta_api.meta_key() is None
    monkeypatch.setenv(meta_api.DOC_KEY_ENV, "doc-key")
    assert meta_api.meta_key() == "doc-key"
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    assert meta_api.meta_key() == "meta-key"


def test_base_and_model_defaults_and_overrides(monkeypatch):
    _reset(monkeypatch)
    assert meta_api.base_url() == "https://api.meta.ai/v1"
    assert meta_api.model() == "muse-spark-1.3"
    assert meta_api.chat_url() == "https://api.meta.ai/v1/chat/completions"
    monkeypatch.setenv(meta_api.BASE_URL_ENV, "https://meta.internal.local/v1/")
    monkeypatch.setenv(meta_api.MODEL_ENV, "muse-spark-1.2")
    assert meta_api.base_url() == "https://meta.internal.local/v1"
    assert meta_api.model() == "muse-spark-1.2"


def test_hosted_is_not_sovereign_but_selfhosted_is():
    assert meta_api.is_host_sovereign("https://api.meta.ai/v1") is False
    assert meta_api.is_host_sovereign("https://meta.internal.local/v1") is True


def test_status_reports_config_and_observation_separately(monkeypatch):
    _reset(monkeypatch)
    s = meta_api.meta_status()
    assert s["key_present"] is False
    assert s["verified"] is False
    assert s["claim_basis"] == "not_configured"
    monkeypatch.setenv(meta_api.KEY_ENV, "k")
    s = meta_api.meta_status()
    assert s["key_present"] is True
    assert s["claim_basis"] == "configuration_only"  # 설정만 있지 관측은 없다


def test_record_writes_ledger_without_breaking_caller(monkeypatch):
    _reset(monkeypatch)
    meta_api.record_layer_call("https://api.meta.ai/v1", ok=True)
    assert cl.status("meta_text")["verified"] is True
    meta_api.record_layer_call("https://api.meta.ai/v1", ok=False, error="boom")
    st = cl.status("meta_text")
    assert st["verified"] is False
    assert st["last_error"] == "boom"


# ── AEGIRON 배선 ──

def test_meta_extracts_and_tags_provider(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_resp(_META_JSON)) as m:
        r = am.extract_signal("DRC 에볼라 신규발생", source="who")
    m.assert_called_once()
    url = m.call_args.args[0]
    assert url == "https://api.meta.ai/v1/chat/completions"
    payload = m.call_args.kwargs["json"]
    assert payload["model"] == "muse-spark-1.3"
    # ★ 검증 안 된 파라미터를 보내지 않는다 ★ chat_template_kwargs는 NVIDIA 문서
    # 꼴이라 Meta가 받는지 모르는데, 보내면 400 분기를 타게 된다.
    assert "chat_template_kwargs" not in payload
    assert r["disease"] == "에볼라"
    assert r["ai_provider"] == "meta_model_api"
    assert r["data_sovereign"] is False  # Meta 호스팅은 준주권이라 정직 표시


def test_doc_key_name_also_drives_meta_path(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.DOC_KEY_ENV, "doc-key")
    with patch("requests.post", return_value=_resp(_META_JSON)):
        r = am.extract_signal("DRC 에볼라", source="who")
    assert r["ai_provider"] == "meta_model_api"


def test_default_order_is_nim_first(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_resp(_META_JSON)) as m:
        r = am.extract_signal("DRC 에볼라", source="who")
    m.assert_called_once()  # NIM이 살았으니 Meta까지 안 간다
    assert "nvidia.com" in m.call_args.args[0]
    assert r["ai_provider"] == "nvidia_nim_hosted"


def test_nim_failure_falls_through_to_meta(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")

    def _route(url, **kw):
        if "api.meta.ai" in url:
            return _resp(_META_JSON)
        raise RuntimeError("nim down")

    with patch("requests.post", side_effect=_route) as m:
        r, attempts = am.extract_signal_detailed("DRC 에볼라", source="who")
    assert m.call_count == 2
    assert r["ai_provider"] == "meta_model_api"
    assert any(a.startswith("nvidia_nim_hosted:") for a in attempts)


def test_meta_first_switch_puts_meta_ahead_of_nim(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv(am.META_FIRST_ENV, "on")
    with patch("requests.post", return_value=_resp(_META_JSON)) as m:
        r = am.extract_signal("DRC 에볼라", source="who")
    m.assert_called_once()
    assert "api.meta.ai" in m.call_args.args[0]
    assert r["ai_provider"] == "meta_model_api"


def test_meta_switch_off_skips_meta_path(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv(am.META_EXTRACT_ENV, "off")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("requests.post") as m, \
         patch("algorithms.nlp_extract.extract_signal_detailed",
               return_value=({"disease": "에볼라"}, None)):
        r = am.extract_signal("DRC 에볼라", source="who")
    m.assert_not_called()  # Meta 키가 있어도 스위치가 끄면 안 나간다
    assert r["ai_provider"] == "external_llm_fallback"


def test_require_local_blocks_hosted_meta_before_sending(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    with patch("requests.post") as m:
        r = am.extract_signal("민감 유전체 데이터", sensitive=True)
    m.assert_not_called()
    assert r["blocked"] is True
    assert r["ai_provider"] == "local_required_unavailable"


def test_require_local_passes_sovereign_meta(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    monkeypatch.setenv(meta_api.BASE_URL_ENV, "https://meta.internal.local/v1")
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    with patch("requests.post", return_value=_resp(_META_JSON)):
        r = am.extract_signal("민감 유전체 데이터", sensitive=True)
    assert r.get("blocked") is not True
    assert r["ai_provider"] == "meta_model_api"
    assert r["data_sovereign"] is True


def test_meta_empty_content_falls_through_with_reason(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    empty = _resp(None, finish_reason="length",
                 usage={"completion_tokens": 1500})
    with patch("requests.post", return_value=empty):
        r, attempts = am.extract_signal_detailed("DRC 에볼라", source="who")
    assert r["ai_provider"] == "unavailable"  # 뒤에 남은 경로가 없으면 불가
    assert any(a.startswith("meta_model_api: 빈응답") for a in attempts)
    assert "출력토큰 1500/1500" in " ".join(attempts)  # 분모는 Meta 한도


def test_success_is_observed_in_ledger(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    with patch("requests.post", return_value=_resp(_META_JSON)):
        am.extract_signal("DRC 에볼라", source="who")
    assert cl.status("meta_text")["verified"] is True


def test_provider_status_reports_meta(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    s = am.provider_status()
    assert s["meta_configured"] is True
    assert s["meta_sovereign"] is False
    assert s["meta_model"] == "muse-spark-1.3"
    assert s["active_provider"] == "meta_model_api"
    assert s["meta"]["key_present"] is True
    assert s["meta_verified"] is False  # 설정만 있지 관측은 없다


def test_extraction_available_with_meta_key_only(monkeypatch):
    _reset(monkeypatch)
    assert am.extraction_available() is False
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    assert am.extraction_available() is True

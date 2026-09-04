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
    monkeypatch.delenv(am.NIM_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(am.NIM_MODEL_ENV, raising=False)
    monkeypatch.delenv(am._nvidia.ONPREM_BASE_ENV, raising=False)
    for env in am.NIM_API_KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


def test_provider_status_falls_back_when_no_local(monkeypatch):
    _reset(monkeypatch)
    s = am.provider_status()
    assert s["active_provider"] == "external_llm_fallback"
    assert s["local_model_configured"] is False
    assert s["local_model_loaded"] is False


def test_extract_uses_llm_fallback_and_tags_provider(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    # 폴백 경로는 extract_signal_detailed 를 부른다(사유까지 받아야 하므로).
    # 얇은 래퍼(extract_signal)를 패치하면 진짜 함수가 그대로 불려 나간다.
    with patch("algorithms.nlp_extract.extract_signal_detailed",
               return_value=({"disease": "에볼라"}, None)) as m:
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


# ── NVIDIA NIM 경로 ──

def _nim_response(payload_json: str):
    """requests.post가 돌려줄 가짜 응답(OpenAI 호환 스키마)."""
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": payload_json}}]}
    return _Resp()


_NIM_JSON = ('{"disease": "에볼라", "location": "DRC", "country_iso3": "COD", '
             '"signal_type": "신규발생", "severity": ["spike"], "symptom": null, '
             '"transmission": null, "date": null, "known_disease": true}')


def test_hosted_nim_extracts_and_tags_semisovereign(monkeypatch):
    """NVIDIA 호스팅 NIM(기본 엔드포인트) → 추출 성공, data_sovereign=False로 정직 표시."""
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    with patch("requests.post", return_value=_nim_response(_NIM_JSON)) as m:
        r = am.extract_signal("DRC 에볼라 신규발생", source="who")
    m.assert_called_once()
    assert r["disease"] == "에볼라"
    assert r["country_iso3"] == "COD"
    assert r["ai_provider"] == "nvidia_nim_hosted"
    assert r["data_sovereign"] is False


def test_selfhosted_nim_is_sovereign(monkeypatch):
    """온프렘 base_url이면 완전 주권(data_sovereign=True)으로 표시."""
    _reset(monkeypatch)
    monkeypatch.setenv("AEGIRON_NIM_API_KEY", "nim-key")
    monkeypatch.setenv(am.NIM_BASE_URL_ENV, "https://nim.internal.aegiron.local/v1")
    with patch("requests.post", return_value=_nim_response(_NIM_JSON)):
        r = am.extract_signal("DRC 에볼라", source="who")
    assert r["ai_provider"] == "aegiron_nim_selfhosted"
    assert r["data_sovereign"] is True


def test_sensitive_blocked_before_hosted_nim_call(monkeypatch):
    """민감 데이터 + REQUIRE_LOCAL이면 호스팅 NIM(외부 클라우드)으로 '보내기 전에' 차단."""
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    with patch("requests.post") as m:
        r = am.extract_signal("민감 유전체 데이터", sensitive=True)
    m.assert_not_called()                       # 외부로 한 번도 안 나감
    assert r["blocked"] is True
    assert r["ai_provider"] == "local_required_unavailable"


def test_sensitive_allowed_on_selfhosted_nim(monkeypatch):
    """민감 데이터라도 자체 호스팅(완전 주권) NIM이면 통과."""
    _reset(monkeypatch)
    monkeypatch.setenv("AEGIRON_NIM_API_KEY", "nim-key")
    monkeypatch.setenv(am.NIM_BASE_URL_ENV, "https://nim.internal.aegiron.local/v1")
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    with patch("requests.post", return_value=_nim_response(_NIM_JSON)):
        r = am.extract_signal("민감 유전체 데이터", sensitive=True)
    assert r["ai_provider"] == "aegiron_nim_selfhosted"
    assert r.get("blocked") is not True


def test_nim_failure_falls_back_to_llm(monkeypatch):
    """NIM 호출이 실패하면(네트워크 등) 비민감 데이터는 외부 LLM으로 폴백."""
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("requests.post", side_effect=RuntimeError("nim down")), \
         patch("algorithms.nlp_extract.extract_signal_detailed",
               return_value=({"disease": "에볼라"}, None)):
        r, attempts = am.extract_signal_detailed("DRC 에볼라", source="who")
    assert r["ai_provider"] == "external_llm_fallback"
    # ★ 폴백이 살렸어도 NIM이 죽은 사실은 남는다 ★ 이게 없으면 "폴백이 매번
    # 구해주는 중"과 "NIM이 잘 돌고 있음"이 로그에서 똑같아 보인다.
    assert attempts == ["nvidia_nim_hosted: RuntimeError"]


def test_provider_status_reports_nim(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    s = am.provider_status()
    assert s["active_provider"] == "nvidia_nim_hosted"
    assert s["nim_configured"] is True
    assert s["nim_sovereign"] is False


def test_require_local_blocks_external_even_for_nonsensitive(monkeypatch):
    """완전 주권 모드: 주권 경로 없으면 '공개 뉴스'(비민감)도 외부 LLM 폴백 차단.
    온프렘 다운 시 미국 API로 새어나가지 않는다는 실질 보장."""
    _reset(monkeypatch)
    monkeypatch.setenv(am.REQUIRE_LOCAL_ENV, "on")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("algorithms.nlp_extract.extract_signal") as m:
        r = am.extract_signal("공개 뉴스 텍스트", sensitive=False)  # 민감 아님
    m.assert_not_called()                        # 외부로 한 번도 안 나감
    assert r["blocked"] is True
    assert r["ai_provider"] == "local_required_unavailable"


def test_onprem_base_makes_text_path_sovereign(monkeypatch):
    """공유 온프렘(AEGIRON_NVIDIA_ONPREM_BASE) 하나로 텍스트 추출도 완전 주권 경로."""
    _reset(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.setenv(am._nvidia.ONPREM_BASE_ENV, "https://nim.internal.aegiron.gov")
    with patch("requests.post", return_value=_nim_response(_NIM_JSON)):
        r = am.extract_signal("DRC 에볼라", source="who")
    assert r["ai_provider"] == "aegiron_nim_selfhosted"
    assert r["data_sovereign"] is True
    assert am.provider_status()["nvidia"]["fully_sovereign"] is True

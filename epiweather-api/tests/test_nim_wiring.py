"""NIM 배선 — 운영 수집 경로가 실제로 aegiron_model을 거치는지 확인.

배경(2026-09-03 실측): Railway 운영에 NVIDIA_API_KEY가 들어가 있는데도 수집기가
매시간 Claude만 불렀다. aegiron_model.extract_signal에 운영 호출자가 하나도 없어서
'키만 있고 안 쓰이는' 상태가 유지됐다. 아래 테스트는 그 배선이 다시 끊어지면
잡는다 — 배선은 눈에 안 보여서, 끊겨도 로그가 조용하다.
"""
from __future__ import annotations

from unittest.mock import patch

import algorithms.aegiron_model as am
from algorithms.nlp_extract import extract_from_global_watch_detailed


def _record(source: str, raw_text: str) -> dict:
    return {
        "source": source, "disease": "에볼라", "location": "DRC",
        "country_iso3": "COD", "signal_type": "신규발생", "severity": [],
        "symptom": None, "transmission": None, "source_trust": 0.65,
        "signal_date": None, "known_disease": True, "raw_text": raw_text,
    }


def _nim_env(monkeypatch, key="nim-key", base=None):
    monkeypatch.setenv("NVIDIA_API_KEY", key)
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_REQUIRE_LOCAL", raising=False)
    if base:
        monkeypatch.setenv("AEGIRON_NIM_BASE_URL", base)
    else:
        monkeypatch.delenv("AEGIRON_NIM_BASE_URL", raising=False)
    monkeypatch.delenv("AEGIRON_NVIDIA_ONPREM_BASE", raising=False)


# ── 배선 자체 ────────────────────────────────────────────────────
def test_global_watch_extraction_goes_through_nim_when_configured(isolated_db, monkeypatch):
    """★핵심★ NIM 키가 있으면 수집 경로가 Claude가 아니라 NIM을 부른다.
    예전엔 nlp_extract.extract_signal을 직접 불러서 NIM이 영영 안 쓰였다."""
    _nim_env(monkeypatch)
    watch = {"signals": [{"id": "who_emro", "text": "새 기사"}]}

    with patch.object(am, "_nim_extract_detailed",
                      return_value=(_record("who_emro", "새 기사"), None)) as nim, \
            patch("algorithms.nlp_extract.extract_signal_detailed") as claude:
        out = extract_from_global_watch_detailed(watch, api_key="anthropic-key")

    nim.assert_called_once()
    claude.assert_not_called()          # NIM이 처리했으면 외부 LLM은 안 부른다
    assert len(out["records"]) == 1
    assert out["providers"] == {"nvidia_nim_hosted": 1}


def test_falls_back_to_external_llm_when_nim_fails(isolated_db, monkeypatch):
    """NIM이 죽으면 조용히 멈추지 말고 외부 LLM으로 폴백하되, 폴백했다는 사실이
    providers에 남아야 한다 — 'NIM 켰는데 왜 계속 Claude냐'를 로그로 알 수 있게."""
    _nim_env(monkeypatch)
    watch = {"signals": [{"id": "who_emro", "text": "새 기사"}]}

    with patch.object(am, "_nim_extract_detailed",
                      return_value=(None, "HTTPError 404")), \
            patch("algorithms.nlp_extract.extract_signal_detailed",
                  return_value=(_record("who_emro", "새 기사"), None)):
        out = extract_from_global_watch_detailed(watch, api_key="anthropic-key")

    assert out["providers"] == {"external_llm_fallback": 1}
    assert len(out["records"]) == 1


def test_hosted_nim_marked_as_not_sovereign(isolated_db, monkeypatch):
    """NVIDIA 호스팅은 준주권이다 — 자체 호스팅과 같은 이름으로 뭉뚱그리지 않는다."""
    _nim_env(monkeypatch)
    with patch.object(am, "_nim_extract_detailed", return_value=(_record("s", "t"), None)):
        record, prov = am.extract_record("t", source="s")
    assert prov["ai_provider"] == "nvidia_nim_hosted"
    assert prov["data_sovereign"] is False


def test_selfhosted_nim_marked_sovereign(isolated_db, monkeypatch):
    _nim_env(monkeypatch, base="https://nim.internal.aegiron.kr/v1")
    with patch.object(am, "_nim_extract_detailed", return_value=(_record("s", "t"), None)):
        record, prov = am.extract_record("t", source="s")
    assert prov["ai_provider"] == "aegiron_nim_selfhosted"
    assert prov["data_sovereign"] is True


# ── 저장 안전성 ──────────────────────────────────────────────────
def test_blocked_result_never_becomes_a_record(isolated_db, monkeypatch):
    """★회귀★ 주권 차단 응답({"blocked": True})을 그대로 create_extracted_signal에
    넘기면 TypeError로 수집 사이클이 통째로 죽는다. 레코드로 승격되면 안 된다."""
    _nim_env(monkeypatch)
    monkeypatch.setenv("AEGIRON_REQUIRE_LOCAL", "on")   # 호스팅 NIM은 차단됨
    watch = {"signals": [{"id": "who_emro", "text": "민감 원문"}]}

    out = extract_from_global_watch_detailed(watch, api_key="anthropic-key")

    assert out["records"] == []
    assert out["blocked"] == 1
    assert out["providers"] == {}


def test_record_is_storable_and_keeps_provider(isolated_db, monkeypatch):
    """추출 레코드는 그대로 DB에 들어가야 하고, 어느 모델이 뽑았는지 남아야 한다."""
    _nim_env(monkeypatch)
    with patch.object(am, "_nim_extract_detailed",
                      return_value=(_record("who_emro", "원문"), None)):
        record, _ = am.extract_record("원문", source="who_emro")

    saved = isolated_db.create_extracted_signal(**record)      # 부가키가 섞이면 TypeError
    assert saved["ai_provider"] == "nvidia_nim_hosted"

    fetched = isolated_db.list_extracted_signals(limit=1)[0]
    assert fetched["ai_provider"] == "nvidia_nim_hosted"


def test_is_extraction_rejects_non_record_shapes():
    assert am.is_extraction(_record("s", "t")) is True
    assert am.is_extraction({"ai_provider": "unavailable", "reason": "키 없음"}) is False
    assert am.is_extraction({"blocked": True, "ai_provider": "x"}) is False
    assert am.is_extraction(None) is False


# ── 게이트 ───────────────────────────────────────────────────────
def test_extraction_available_with_nim_key_only(monkeypatch):
    """★회귀★ 수집기 게이트가 ANTHROPIC_API_KEY만 보던 탓에, NIM만 켠 환경에서
    추출·설명불가 감시가 통째로 건너뛰어졌다."""
    _nim_env(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_LOCAL_MODEL", raising=False)
    assert am.extraction_available(None) is True


def test_extraction_unavailable_with_no_backend(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_LOCAL_MODEL", raising=False)
    assert am.extraction_available(None) is False


# ── 텍스트 추출만 되돌리는 스위치 ────────────────────────────────
def test_nim_extract_switch_off_keeps_claude(isolated_db, monkeypatch):
    """NVIDIA_API_KEY는 유전체·MSA·문서 층과 공유한다. 유전체 때문에 키를 넣은
    사람이 추출 모델까지 자기도 모르게 갈아끼우면 안 되므로, 텍스트만 끄는
    스위치가 재배포 없이 동작해야 한다."""
    _nim_env(monkeypatch)
    monkeypatch.setenv("AEGIRON_NIM_EXTRACT", "off")
    watch = {"signals": [{"id": "who_emro", "text": "새 기사"}]}

    with patch.object(am, "_nim_extract_detailed") as nim, \
            patch("algorithms.nlp_extract.extract_signal_detailed",
                  return_value=(_record("who_emro", "새 기사"), None)):
        out = extract_from_global_watch_detailed(watch, api_key="anthropic-key")

    nim.assert_not_called()
    assert out["providers"] == {"external_llm_fallback": 1}


def test_switch_off_does_not_disable_other_nvidia_layers(monkeypatch):
    """스위치는 '텍스트 추출'만 끈다 — 유전체/MSA 층 설정은 그대로여야 한다."""
    from algorithms import nvidia
    _nim_env(monkeypatch)
    monkeypatch.setenv("AEGIRON_NIM_EXTRACT", "off")
    assert am._nim_config() is None                 # 텍스트 경로는 꺼짐
    status = nvidia.nvidia_status()
    assert status["shared_key_present"] is True     # 나머지 층은 살아있음
    assert status["any_nvidia_key_present"] is True

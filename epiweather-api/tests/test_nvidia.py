"""NVIDIA 키 규약 단일 소스 — 공유 키 하나로 전 서비스 동작, 텍스트 전용 오버라이드."""
from __future__ import annotations

from algorithms import nvidia


def _clear(monkeypatch):
    monkeypatch.delenv(nvidia.SHARED_KEY_ENV, raising=False)
    monkeypatch.delenv(nvidia.TEXT_KEY_OVERRIDE_ENV, raising=False)


def test_no_key_all_absent(monkeypatch):
    _clear(monkeypatch)
    assert nvidia.nvidia_api_key() is None
    assert nvidia.text_nim_key() is None
    s = nvidia.nvidia_status()
    assert s["any_nvidia_active"] is False
    assert all(svc["key_available"] is False for svc in s["services"])


def test_shared_key_powers_all_services(monkeypatch):
    """NVIDIA_API_KEY 하나면 유전체·문서·텍스트 서비스가 전부 키 확보."""
    _clear(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "shared")
    assert nvidia.nvidia_api_key() == "shared"
    assert nvidia.text_nim_key() == "shared"   # 텍스트도 공유 키로 폴백
    s = nvidia.nvidia_status()
    assert s["shared_key_present"] is True
    assert all(svc["key_available"] is True for svc in s["services"])


def test_text_override_takes_precedence_for_text_only(monkeypatch):
    """AEGIRON_NIM_API_KEY는 텍스트 층에만 우선 적용, 유전체는 공유 키 그대로."""
    _clear(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "shared")
    monkeypatch.setenv(nvidia.TEXT_KEY_OVERRIDE_ENV, "text-only")
    assert nvidia.nvidia_api_key() == "shared"      # 유전체 = 공유 키
    assert nvidia.text_nim_key() == "text-only"     # 텍스트 = 오버라이드


def test_text_override_alone_activates_only_text(monkeypatch):
    """공유 키 없이 텍스트 오버라이드만 있으면 텍스트만 키 확보(유전체는 미확보)."""
    _clear(monkeypatch)
    monkeypatch.setenv(nvidia.TEXT_KEY_OVERRIDE_ENV, "text-only")
    assert nvidia.nvidia_api_key() is None
    assert nvidia.text_nim_key() == "text-only"
    s = nvidia.nvidia_status()
    by_id = {svc["id"]: svc for svc in s["services"]}
    assert by_id["text_signal_extraction"]["key_available"] is True
    assert by_id["evo2_naturalness"]["key_available"] is False

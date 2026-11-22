"""NVIDIA 유전체 층(Evo2·MSA) 주소 — 개편 2차(2026-11-22) 뒤 남은 것만.

텍스트·문서 층과 주권 종합 판정은 지웠다(호출부가 없어졌다). 남은 계약:
온프렘 주소가 있으면 유전체 두 엔진이 그쪽으로 가고, 없으면 NVIDIA 공용 클라우드로 간다.
"""
from __future__ import annotations

from algorithms import nvidia


def test_default_is_public_cloud(monkeypatch):
    monkeypatch.delenv(nvidia.ONPREM_BASE_ENV, raising=False)
    assert nvidia.evo2_url().startswith(nvidia.CLOUD_HEALTH_BASE)
    assert nvidia.is_host_sovereign(nvidia.msa_url()) is False


def test_onprem_base_routes_both_genome_engines(monkeypatch):
    monkeypatch.setenv(nvidia.ONPREM_BASE_ENV, "https://nim.internal.example/")
    for url in (nvidia.evo2_url(), nvidia.msa_url()):
        assert url.startswith("https://nim.internal.example")
        assert nvidia.is_host_sovereign(url) is True


def test_unknown_layer_is_not_recorded(monkeypatch):
    calls = []
    import algorithms.capability_ledger as cl
    monkeypatch.setattr(cl, "record", lambda *a, **k: calls.append(a))
    nvidia.record_layer_call("text", "https://x", ok=True)
    assert calls == []
    nvidia.record_layer_call("genome", "https://x", ok=True)
    assert calls and calls[0][0] == "nvidia_genome"

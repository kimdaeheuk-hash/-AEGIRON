"""헤임달 P2 — 요청시 3종 감사+범위밖 라우팅+검증스크립트 정합.

전부 mock·정적 검사. 외부 HTTP 없음(conftest 가드 준수).
실제 NIM 재현 실행(키·네트워크 필요)은 CI·운영에서 수동 수행.
"""
from __future__ import annotations

import ast
import datetime as dt
import importlib.util
import inspect
import py_compile
from pathlib import Path

import pytest

from algorithms import baikal
from algorithms import capability_ledger as ledger
from algorithms import evo2_naturalness as evo2
from algorithms import msa_homology as mh
from algorithms import nvidia as nv

API_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = API_ROOT / "scripts" / "validate_evo2_applicability.py"


# ── 엔진별 장부 이중 기록 ─────────────────────────────────────────
def test_dual_write_layer_and_engine(monkeypatch):
    """capability를 주면 층 집계+엔진 ID 둘 다에 남는다."""
    calls: list = []
    monkeypatch.setattr(ledger, "record",
                        lambda cap, **kw: calls.append(cap))
    nv.record_layer_call("genome", "https://x", True,
                         capability="nvidia_genome_msa")
    assert calls == ["nvidia_genome", "nvidia_genome_msa"]


def test_no_capability_keeps_single_write(monkeypatch):
    """안 주면 기존처럼 층 집계만(하위 호환)."""
    calls: list = []
    monkeypatch.setattr(ledger, "record",
                        lambda cap, **kw: calls.append(cap))
    nv.record_layer_call("genome", "https://x", True)
    assert calls == ["nvidia_genome"]


def test_msa_search_tags_engine_id(monkeypatch):
    """MSA 검색 1회가 엔진 ID로 기록된다."""
    mh._BREAKER["consecutive_fails"] = 0
    mh._BREAKER["open_until"] = 0.0
    seen: dict = {}

    def fake_record(layer, url, ok, error=None, capability=None):
        seen["capability"] = capability

    monkeypatch.setattr(mh._nvidia, "record_layer_call", fake_record)

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"alignments": {}}

    monkeypatch.setattr(mh.requests, "post", lambda *a, **k: _Resp())
    mh._search("M" * 60, "k")
    assert seen["capability"] == "nvidia_genome_msa"
    mh._BREAKER["consecutive_fails"] = 0
    mh._BREAKER["open_until"] = 0.0


# ── BAIKAL 요청시-엔진 감사 ───────────────────────────────────────
def _rec():
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "timestamp": now.isoformat(),
        "genomic_variants": {
            "x": {"available": True, "label": "X", "dominant_clade": "A",
                  "dominant_share": 0.9, "new_clade_count": 0,
                  "n_recent_sequences": 5}},
    }


def _fake_status(cap):
    if cap == "nvidia_genome_evo2":
        return {"verified": True, "claim_basis": "verified_run",
                "last_success_at": "2026-11-02T00:00:00+00:00",
                "consecutive_failures": 0, "last_error": None}
    return {"verified": False, "claim_basis": "observed_failure",
            "last_success_at": None, "consecutive_failures": 4,
            "last_error": "HTTPError: 503"}


def test_audit_section_lists_three_engines():
    res = baikal.judge_heimdall(_rec(), dt.datetime.now(dt.timezone.utc),
                                ledger_status=_fake_status)
    engines = res["readings"]["on_request_engines"]
    assert [e["engine"] for e in engines] == [
        "evo2_naturalness", "msa_homology", "genome_signals"]
    assert engines[0]["state"] == "ok"
    assert engines[0]["claim_basis"] == "verified_run"
    assert engines[1]["state"] == "failed"
    assert engines[1]["consecutive_failures"] == 4
    # genome_signals는 로컬이라 unverified가 아니라 local
    assert engines[2]["state"] == "local"


def test_audit_does_not_fold_into_status():
    """요청시 엔진이 죽어도 수집 주기 상태는 그대로(관측보다 많이 말하지 않음)."""
    res = baikal.judge_heimdall(_rec(), dt.datetime.now(dt.timezone.utc),
                                ledger_status=_fake_status)
    assert res["status"] == "ok"


def test_audit_present_on_early_returns():
    """주기 기록이 없어도 요청시-엔진 감사는 붙는다."""
    res = baikal.judge_heimdall(None, dt.datetime.now(dt.timezone.utc),
                                ledger_status=_fake_status)
    assert res["status"] == "undetermined"
    assert len(res["readings"]["on_request_engines"]) == 3


def test_audit_survives_ledger_error():
    """장부 읽기 실패는 unverified로, 판정 전체가 죽지 않는다."""
    res = baikal.judge_heimdall(
        _rec(), dt.datetime.now(dt.timezone.utc),
        ledger_status=lambda cap: (_ for _ in ()).throw(OSError("disk")))
    engines = res["readings"]["on_request_engines"]
    assert engines[0]["state"] == "unverified"
    assert res["status"] == "ok"


# ── Evo2 범위밖 라우팅 ────────────────────────────────────────────
def test_virus_routes_to_msa(monkeypatch):
    """진핵감염 바이러스는 MSA로 보내라 안내한다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(evo2, "_predict_next",
                        lambda prefix, n, key: ("ACGTACGT", [0.9] * 8))
    out = evo2.score_naturalness("ACGT" * 20, context=20, predict=4,
                                 organism_domain="eukaryotic_virus")
    assert out["ok"] is True and out["applicable"] is False
    alt = out["recommended_alternative"]
    assert alt["engine"] == "msa_homology" and alt["via"] == "use_msa"


def test_in_scope_has_no_alternative(monkeypatch):
    """적용범위 안이면 라우팅 필드는 비어 있다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setattr(evo2, "_predict_next",
                        lambda prefix, n, key: ("ACGTACGT", [0.9] * 8))
    out = evo2.score_naturalness("ACGT" * 20, context=20, predict=4,
                                 organism_domain="bacteria_archaea")
    assert out["applicable"] is True
    assert out["recommended_alternative"] is None


# ── 검증 스크립트 정합 가드 ───────────────────────────────────────
def test_validation_script_compiles():
    assert SCRIPT.exists()
    py_compile.compile(str(SCRIPT), doraise=True)


def test_validation_script_kwargs_match_signature():
    """스크립트가 score_naturalness에 넘기는 인자가 현 서명 안에 있어야
    '재현 가능' 주장이 깨지지 않는다."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "score_naturalness":
                used.update(k.arg for k in node.keywords if k.arg)
    assert used, "스크립트에서 score_naturalness 호출을 못 찾음"
    params = set(inspect.signature(evo2.score_naturalness).parameters)
    assert used <= params, f"서명에 없는 인자: {used - params}"


def test_validation_script_tables_intact():
    """TAXA·VIRUSES 표가 비어 있지 않고 실행 기록 주석이 있어야 한다."""
    spec = importlib.util.spec_from_file_location("validate_evo2_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    groups = {g for _, _, g in mod.TAXA}
    assert len(mod.TAXA) >= 7 and "eukaryotic_virus" in groups
    assert len(groups) >= 3 and len(mod.VIRUSES) >= 5
    assert "실행 기록" in SCRIPT.read_text(encoding="utf-8")

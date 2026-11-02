"""헤임달 P1 — MSA 재시도+서킷브레이커, Variants 병렬+외부화.

전부 mock 기반. 실제 HTTP·실제 sleep 없음(conftest 가드 준수).
"""
from __future__ import annotations

import datetime as dt

import pytest
import requests

from algorithms import genomic_variants as gv
from algorithms import msa_homology as mh

PROTEIN = "M" + "KTVRQERLKSIFRTAYELLQDPNAWSGVKEHCFNTGVLQMSDPRTYIAG" * 3  # 148aa


@pytest.fixture
def breaker_reset():
    mh._BREAKER["consecutive_fails"] = 0
    mh._BREAKER["open_until"] = 0.0
    yield
    mh._BREAKER["consecutive_fails"] = 0
    mh._BREAKER["open_until"] = 0.0


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(mh, "_sleep", lambda s: None)


@pytest.fixture
def no_ledger(monkeypatch):
    monkeypatch.setattr(mh._nvidia, "record_layer_call", lambda *a, **k: None)


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {"alignments": {}}

    def raise_for_status(self):
        if self.status_code >= 400:
            e = requests.HTTPError(f"HTTP {self.status_code}")
            e.response = self
            raise e

    def json(self):
        return self._payload


def _post_factory(script, calls):
    def fake_post(*a, **k):
        calls.append(k.get("timeout"))
        item = script[min(len(calls) - 1, len(script) - 1)]
        if isinstance(item, Exception):
            raise item
        return item
    return fake_post


def _payload_full():
    head = ">X\t500\t0.99\t1e-100\t0\t399\t400\t0\t399\t400"
    return {"alignments": {"Uniref30": {"a3m": {"alignment": head + "\nMKT"}}}}


# ── MSA 재시도 ────────────────────────────────────────────────────
def test_retry_then_success(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """5xx 두 번 후 성공 — 3회 호출되고 ok."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    script = [_Resp(503), _Resp(500), _Resp(200, _payload_full())]
    monkeypatch.setattr(mh.requests, "post", _post_factory(script, calls))
    out = mh.assess_homology(PROTEIN)
    assert len(calls) == 3
    assert out["ok"] is True and out["best_coverage"] > 0.99


def test_retry_exhausted_still_not_ok(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """계속 5xx면 RETRIES+1회만 보내고 실패 반환."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(mh.requests, "post",
                        _post_factory([_Resp(503)], calls))
    out = mh.assess_homology(PROTEIN)
    assert len(calls) == mh.RETRIES + 1
    assert out["ok"] is False and "MSA 검색 실패" in out["reason"]


def test_401_does_not_retry(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """4xx(인증)는 재시도 없이 1회만."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(mh.requests, "post", _post_factory([_Resp(401)], calls))
    out = mh.assess_homology(PROTEIN)
    assert len(calls) == 1
    assert out["ok"] is False


def test_429_quota_does_not_retry(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """429(쿼터)는 더 태우지 말고 1회만."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(mh.requests, "post", _post_factory([_Resp(429)], calls))
    out = mh.assess_homology(PROTEIN)
    assert len(calls) == 1
    assert out["ok"] is False


def test_timeout_is_retried(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """연결 타임아웃은 재시도 대상."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    script = [requests.Timeout("conn"), _Resp(200, _payload_full())]
    monkeypatch.setattr(mh.requests, "post", _post_factory(script, calls))
    out = mh.assess_homology(PROTEIN)
    assert len(calls) == 2 and out["ok"] is True


def test_connect_read_timeout_split(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """연결(짧게)·읽기(길게) 분리 전달."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(mh.requests, "post",
                        _post_factory([_Resp(200, _payload_full())], calls))
    mh.assess_homology(PROTEIN)
    assert calls[0] == (mh.CONNECT_TIMEOUT, mh.TIMEOUT)


# ── MSA 서킷브레이커 ──────────────────────────────────────────────
def test_breaker_opens_after_threshold(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """연속 실패가 임계 도달 — 이후 호출은 HTTP 없이 즉시 실패."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    monkeypatch.setattr(mh.requests, "post", _post_factory([_Resp(503)], calls))
    for _ in range(mh.BREAKER_THRESHOLD):
        out = mh.assess_homology(PROTEIN)
        assert out["ok"] is False and "breaker_open" not in out
    before = len(calls)
    out = mh.assess_homology(PROTEIN)
    assert out["ok"] is False and out.get("breaker_open") is True
    assert "서킷브레이커" in out["reason"]
    assert len(calls) == before  # HTTP 안 나감


def test_breaker_resets_on_success(monkeypatch, breaker_reset, no_sleep, no_ledger):
    """성공 한 번이면 연속 실패 카운터 초기화."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    calls: list = []
    script = ([_Resp(503)] * (mh.RETRIES + 1)          # 1차: 전부 실패
              + [_Resp(200, _payload_full())]           # 2차: 성공 → 리셋
              + [_Resp(503)] * (mh.RETRIES + 1))        # 3차: 다시 실패
    monkeypatch.setattr(mh.requests, "post", _post_factory(script, calls))
    mh.assess_homology(PROTEIN)                       # 1 실패
    assert mh.assess_homology(PROTEIN)["ok"] is True  # 성공 → 리셋
    out = mh.assess_homology(PROTEIN)                 # 다시 1 실패
    assert out["ok"] is False and "breaker_open" not in out
    assert mh._BREAKER["consecutive_fails"] == 1


# ── Variants 병렬+외부화 ──────────────────────────────────────────
def _tree(prefix):
    today = dt.date.today().isoformat()
    recent = gv._year_frac(10)
    prior = gv._year_frac(100)
    tips = [
        {"node_attrs": {"clade_membership": {"value": "A"},
                        "num_date": {"value": recent}}},
        {"node_attrs": {"clade_membership": {"value": "A"},
                        "num_date": {"value": recent}}},
        {"node_attrs": {"clade_membership": {"value": "B"},
                        "num_date": {"value": prior}}},
    ]
    return {"meta": {"updated": today}, "tree": {"children": tips}}


def test_parallel_collects_all_builds(monkeypatch):
    """3빌드 전부 수집, 키 집합은 직렬 때와 동일."""
    monkeypatch.delenv("AEGIRON_VARIANT_BUILDS", raising=False)
    monkeypatch.setattr(gv, "_fetch_dataset", _tree)
    out = gv.get_genomic_variant_signals()
    assert set(out) == {"ncov_open_global_6m", "mpox", "rsv_a_genome"}
    assert all(v["available"] for v in out.values())
    assert out["mpox"]["dominant_clade"] == "A"


def test_one_build_failure_does_not_stop_others(monkeypatch):
    """빌드 하나 실패해도 나머지 수집."""
    monkeypatch.delenv("AEGIRON_VARIANT_BUILDS", raising=False)

    def flaky(prefix):
        if prefix == "/mpox":
            return None
        return _tree(prefix)

    monkeypatch.setattr(gv, "_fetch_dataset", flaky)
    out = gv.get_genomic_variant_signals()
    assert out["mpox"]["available"] is False
    assert out["rsv_a_genome"]["available"] is True


def test_watchlist_env_override(monkeypatch):
    """AEGIRON_VARIANT_BUILDS로 목록 교체."""
    monkeypatch.setenv("AEGIRON_VARIANT_BUILDS", "/x|X,/y/z|Y")
    monkeypatch.setattr(gv, "_fetch_dataset", _tree)
    out = gv.get_genomic_variant_signals()
    assert set(out) == {"x", "y_z"}
    assert out["x"]["label"] == "X"


def test_watchlist_env_bad_value_falls_back(monkeypatch):
    """파싱 실패 값은 기본 목록으로."""
    monkeypatch.setenv("AEGIRON_VARIANT_BUILDS", "not-a-prefix")
    assert gv._watchlist() == gv.WATCHLIST
    monkeypatch.setenv("AEGIRON_VARIANT_BUILDS", "/x|")
    assert gv._watchlist() == gv.WATCHLIST

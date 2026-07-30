"""Stage 0 Evo2 자연스러움 — 일치율 계산과 실패 폴백을 결정론적으로 검증.
실제 NIM 호출은 monkeypatch로 대체(테스트가 네트워크·쿼터에 의존하면 안 됨)."""
from __future__ import annotations

import pytest

from algorithms import evo2_naturalness as ev


@pytest.fixture()
def seq_1000():
    """길이 1000의 결정론적 비주기 서열 — context 512 + predict 12를 넉넉히 넘김.
    ACGT 반복 같은 주기 서열을 쓰면 아래 fake가 prefix로 위치를 되찾을 때
    후보가 여러 개라 테스트가 실제 동작을 검증하지 못한다(시드 고정 난수 사용)."""
    import random
    return "".join(random.Random(7).choices("ACGT", k=1000))


def test_no_key_returns_not_ok_instead_of_raising(monkeypatch, seq_1000):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    out = ev.score_naturalness(seq_1000)
    assert out["ok"] is False and "NVIDIA_API_KEY" in out["reason"]
    assert out["is_screening_only"] is True


def test_too_short_sequence_reports_reason(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    out = ev.score_naturalness("ACGT" * 10)          # 40bp — context에 한참 못 미침
    assert out["ok"] is False and "Evo2 평가 불가" in out["reason"]


def test_perfect_prediction_gives_match_rate_1(monkeypatch, seq_1000):
    """모델이 실제 서열을 그대로 맞히면 일치율 1.0, 플래그 없음."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")

    def fake(prefix, n_tokens, api_key):
        # prefix가 서열 어디서 끝났는지 되찾아 그 다음 염기를 그대로 반환(완벽 예측)
        idx = seq_1000.index(prefix) + len(prefix)
        return seq_1000[idx:idx + n_tokens], [0.95] * n_tokens

    monkeypatch.setattr(ev, "_predict_next", fake)
    out = ev.score_naturalness(seq_1000, n_windows=3)
    assert out["ok"] is True
    assert out["match_rate"] == 1.0
    assert out["flag_count"] == 0
    assert out["windows_scored"] == 3


def test_confidently_wrong_window_flags_local_anomaly(monkeypatch, seq_1000):
    """모델이 높은 확신으로 전부 틀리면 국소 이상 + 낮은 일치율 둘 다 플래그.
    (플래그는 적용범위 안에서만 올라가므로 세균·고균으로 선언해 검증)"""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")

    def fake(prefix, n_tokens, api_key):
        # 확신 0.9인데 전부 오답 — 실제 염기의 상보염기를 주면 100% 빗나감이 보장된다
        # ("G"만 반복하면 실제로 G인 자리가 우연히 맞아 윈도별 일치율이 흔들림)
        idx = seq_1000.index(prefix) + len(prefix)
        actual = seq_1000[idx:idx + n_tokens]
        return actual.translate(str.maketrans("ACGT", "TGCA")), [0.9] * n_tokens

    monkeypatch.setattr(ev, "_predict_next", fake)
    out = ev.score_naturalness(seq_1000, n_windows=3, organism_domain="bacteria_archaea")
    assert out["ok"] is True
    assert out["match_rate"] < ev._REF["match_rate_low"]
    metrics = {f["metric"] for f in out["flags"]}
    assert {"evo2_match_rate", "evo2_local_anomaly"} <= metrics
    assert len(out["local_anomaly_positions"]) == 3


def test_all_calls_failing_returns_not_ok(monkeypatch, seq_1000):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")

    def boom(prefix, n_tokens, api_key):
        raise RuntimeError("NIM down")

    monkeypatch.setattr(ev, "_predict_next", boom)
    out = ev.score_naturalness(seq_1000, n_windows=2)
    assert out["ok"] is False and "모두 실패" in out["reason"]


def test_partial_failure_still_scores(monkeypatch, seq_1000):
    """일부 윈도가 실패해도 나머지로 점수를 낸다(전부 버리지 않음)."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    calls = {"n": 0}

    def flaky(prefix, n_tokens, api_key):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("일시 오류")
        idx = seq_1000.index(prefix) + len(prefix)
        return seq_1000[idx:idx + n_tokens], [0.95] * n_tokens

    monkeypatch.setattr(ev, "_predict_next", flaky)
    out = ev.score_naturalness(seq_1000, n_windows=3)
    assert out["ok"] is True
    assert out["windows_failed"] == 1 and out["windows_scored"] == 2
    assert out["match_rate"] == 1.0


def _wrong_predictor(seq_1000):
    """실제와 100% 어긋나게 예측하는 fake — '낮은 점수' 상황을 만든다."""
    def fake(prefix, n_tokens, api_key):
        idx = seq_1000.index(prefix) + len(prefix)
        actual = seq_1000[idx:idx + n_tokens]
        return actual.translate(str.maketrans("ACGT", "TGCA")), [0.9] * n_tokens
    return fake


def test_eukaryotic_virus_low_score_does_not_flag(monkeypatch, seq_1000):
    """★회귀 테스트★ 진핵감염 바이러스(코로나·독감·에볼라)는 Evo2 학습에서
    제외돼 자연서열도 30%대다. 여기서 플래그를 올리면 감시 대상 병원체가
    전부 오탐이 된다 — 점수는 보고하되 플래그는 반드시 비어 있어야 한다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(ev, "_predict_next", _wrong_predictor(seq_1000))
    out = ev.score_naturalness(seq_1000, n_windows=3, organism_domain="eukaryotic_virus")
    assert out["ok"] is True
    assert out["match_rate"] < ev._REF["match_rate_low"]   # 점수는 낮게 나오지만
    assert out["applicable"] is False
    assert out["flags"] == [] and out["flag_count"] == 0    # 플래그는 안 올린다
    assert "적용범위 밖" in out["suppressed_flags"]


def test_unknown_domain_defaults_to_not_flagging(monkeypatch, seq_1000):
    """분류군 미선언이면 낮은 점수가 '인공'인지 '적용범위 밖'인지 구분 불가 →
    안전한 쪽(플래그 없음)으로 기본 동작."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(ev, "_predict_next", _wrong_predictor(seq_1000))
    out = ev.score_naturalness(seq_1000, n_windows=3)      # organism_domain 생략
    assert out["organism_domain"] == "unknown"
    assert out["applicable"] is False and out["flags"] == []


def test_in_domain_low_score_does_flag(monkeypatch, seq_1000):
    """적용범위 안(세균·고균)에서는 낮은 점수가 실제 신호이므로 플래그를 올린다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(ev, "_predict_next", _wrong_predictor(seq_1000))
    out = ev.score_naturalness(seq_1000, n_windows=3, organism_domain="bacteria_archaea")
    assert out["applicable"] is True
    assert {f["metric"] for f in out["flags"]} == {"evo2_match_rate", "evo2_local_anomaly"}
    assert out["suppressed_flags"] is None


def test_unrecognized_domain_falls_back_to_unknown(monkeypatch, seq_1000):
    """오타·미지원 값이 들어와도 조용히 통과시키지 않고 안전한 unknown으로 처리."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(ev, "_predict_next", _wrong_predictor(seq_1000))
    out = ev.score_naturalness(seq_1000, n_windows=2, organism_domain="바이러스오타")
    assert out["applicable"] is False and out["flags"] == []


def test_generated_sequence_is_not_returned(monkeypatch, seq_1000):
    """방어적 탐지 전용 — 모델 생성 서열이 결과에 새어나가면 안 된다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    marker = "TTTTTTTTTTTT"

    def fake(prefix, n_tokens, api_key):
        return marker[:n_tokens], [0.9] * n_tokens

    monkeypatch.setattr(ev, "_predict_next", fake)
    out = ev.score_naturalness(seq_1000, n_windows=2)
    assert marker[:12] not in repr(out)

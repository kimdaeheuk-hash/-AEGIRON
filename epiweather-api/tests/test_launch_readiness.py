"""런칭 준비도 관문 (2026-08-30).

## 왜 코드여야 하나
"런칭해도 되나"는 사람이 감으로 답하던 질문이었고, 그러면 **낙관 쪽으로 밀린다** —
만든 사람은 잘 돌아간 날을 더 많이 기억하기 때문이다. 관문을 코드로 박으면 답이
라이브 데이터에서 나온다.

## 이 파일이 고정하는 것 — 전부 '관문이 헐거워지지 않는가'다
1. ★ 선행일수 실측 0건이면 유료 예보 관문이 열리지 않는다 ★ — 논지 그 자체다
2. ★ 판정 불가(None)를 통과로 세지 않는다 ★ — '모른다'로 런칭하지 않는다
3. 품질 저하가 있으면 무료 베타도 막힌다
4. disclosure 에 막힌 이유가 빠짐없이 실린다 — 숨기면 나머지 정직성까지 죽는다
"""
from __future__ import annotations

import pytest

from algorithms import launch_readiness as lr


def _gate(report, key):
    return next(g for g in report["gates"] if g["key"] == key)


@pytest.fixture
def _all_green(monkeypatch):
    """수집·품질을 통과 상태로 고정. 선행일수/캘리브레이션은 각 테스트가 정한다."""
    monkeypatch.setattr(lr, "_collection_gate", lambda: lr._gate(
        "collection", "수집 파이프라인", True, "정상 21/21", "-", ["beta", "paid"]))
    monkeypatch.setattr(lr, "_quality_gate", lambda: lr._gate(
        "quality", "조용한 저하 감지", True, "불변식 정상 5/5", "-", ["beta", "paid"]))


# ── ★핵심★ 실측 없이 유료 런칭이 열리지 않는다 ─────────────────────

def test_zero_measured_lead_time_blocks_paid_launch(_all_green, monkeypatch):
    """★이 관문이 이 모듈의 존재 이유★

    코드로 열 수 없는 관문을 일부러 뒀다. 실제 발병을 먼저 잡아야만 열린다 —
    숫자를 지어내 여는 순간 이 모듈은 정반대의 물건이 된다.
    """
    monkeypatch.setattr(
        "algorithms.prediction_resolver.lead_time_record",
        lambda: {"measured_events": 0, "is_evidence": False,
                 "median_lead_days": None, "best_lead_days": None},
    )
    report = lr.readiness_report()

    assert _gate(report, "lead_time")["passed"] is False
    assert report["ready_for"]["paid_forecast"] is False
    assert "lead_time" in report["blockers"]["paid_forecast"]
    # 무료 베타는 막지 않는다 — 실측을 쌓는 유일한 방법이 그것이기 때문이다.
    assert report["ready_for"]["free_beta"] is True


def test_measured_lead_time_opens_the_gate(_all_green, monkeypatch):
    monkeypatch.setattr(
        "algorithms.prediction_resolver.lead_time_record",
        lambda: {"measured_events": 2, "is_evidence": True,
                 "median_lead_days": 12.0, "best_lead_days": 20},
    )
    report = lr.readiness_report()

    assert _gate(report, "lead_time")["passed"] is True
    assert "12" in _gate(report, "lead_time")["detail"]


# ── ★모른다로 런칭하지 않는다★ ─────────────────────────────────────

def test_unknown_gate_blocks_just_like_a_failure(monkeypatch):
    """판정 불가를 통과로 세면, 지표가 고장난 날 런칭 신호가 초록이 된다."""
    monkeypatch.setattr(lr, "_quality_gate", lambda: lr._gate(
        "quality", "조용한 저하 감지", None, "판정 불가: OSError",
        "-", ["beta", "paid"]))

    report = lr.readiness_report()

    assert _gate(report, "quality")["passed"] is None
    assert report["ready_for"]["free_beta"] is False
    assert "quality" in report["blockers"]["free_beta"]


def test_quality_degradation_blocks_even_the_free_beta(monkeypatch):
    """조용한 저하가 있는 채로는 무료 베타도 내보내지 않는다."""
    monkeypatch.setattr(lr, "_quality_gate", lambda: lr._gate(
        "quality", "조용한 저하 감지", False, "저하 중인 불변식 1개: LLM 재분류",
        "-", ["beta", "paid"]))

    report = lr.readiness_report()
    assert report["ready_for"]["free_beta"] is False


# ── 고지(disclosure) ────────────────────────────────────────────────

def test_disclosure_lists_every_blocked_gate(_all_green, monkeypatch):
    """★숨겼다가 발각되면 나머지 정직성까지 같이 죽는다★"""
    monkeypatch.setattr(
        "algorithms.prediction_resolver.lead_time_record",
        lambda: {"measured_events": 0, "is_evidence": False,
                 "median_lead_days": None, "best_lead_days": None},
    )
    report = lr.readiness_report()
    joined = " ".join(report["disclosure"])

    assert "선행일수" in joined
    assert "캘리브레이션" in joined
    # 투자 데모는 불리언이 아니다 — '통과'가 아니라 '고지'의 문제이기 때문이다.
    assert isinstance(report["ready_for"]["investor_demo"], str)


def test_calibration_gate_reports_uncalibrated_params():
    """미보정 파라미터가 한자리에 모여야 무엇을 근거처럼 인용하면 안 되는지 보인다."""
    gate = lr._calibration_gate()

    assert gate["passed"] is False
    assert "임의값" in gate["detail"] or "문헌" in gate["detail"]


def test_calibration_flags_have_a_single_source():
    """★플래그만 뒤집는 거짓말을 막는다★

    예전엔 `windows_calibrated: False` 가 응답 dict 안 리터럴이었다. 그러면
    실제로 보정하고도 응답은 영영 미보정이라 말하거나, 반대로 리터럴만 True 로
    고쳐놓고 보정은 안 하는 일이 생긴다. 런칭 관문이 이 값을 보므로 한 곳에서만 정한다.
    """
    from algorithms import disaster_watch as dw

    assert hasattr(dw, "WINDOWS_CALIBRATED")
    assert hasattr(dw, "THRESHOLD_CALIBRATED")
    assert dw.WINDOWS_CALIBRATED is False, "문헌값을 그대로 두고 뒤집으면 안 된다"


def test_ledger_alone_can_open_the_lead_time_gate(_all_green, monkeypatch):
    """★핵심★ 선행성 원장만으로도 관문이 열린다.

    예측 채점은 90일 기한이라 첫 결과가 늦다. 원장은 문턱을 넘는 순간 선제적으로
    적어두므로 다음 공식 선언이 나면 그 자리에서 채점된다 — 실제로는 이쪽이
    먼저 열릴 가능성이 높다.
    """
    monkeypatch.setattr(
        "algorithms.prediction_resolver.lead_time_record",
        lambda: {"measured_events": 0, "is_evidence": False},
    )
    monkeypatch.setattr(
        "algorithms.lead_time_ledger.ledger_record",
        lambda: {"measured_events": 1, "mean_lead_days": 9.0,
                 "false_alarms": 2, "open_crossings": 3},
    )
    report = lr.readiness_report()

    gate = _gate(report, "lead_time")
    assert gate["passed"] is True
    assert "원장 실측 1건" in gate["detail"]
    assert "오경보 2건" in gate["detail"], "오경보를 숨기면 정밀도 없는 성적표가 인용된다"


def test_blocked_gate_shows_what_is_being_tracked(_all_green, monkeypatch):
    """★핵심★ 막혀 있을 때 '지금 몇 건을 추적 중인지'를 보여준다 — 죽은 게 아니다."""
    monkeypatch.setattr(
        "algorithms.prediction_resolver.lead_time_record",
        lambda: {"measured_events": 0, "is_evidence": False},
    )
    monkeypatch.setattr(
        "algorithms.lead_time_ledger.ledger_record",
        lambda: {"measured_events": 0, "false_alarms": 0, "open_crossings": 4},
    )
    gate = _gate(lr.readiness_report(), "lead_time")

    assert gate["passed"] is False
    assert "추적 중인 문턱 통과 4건" in gate["detail"]

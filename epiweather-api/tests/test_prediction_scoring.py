"""예측 채점 — 적중률·Brier·보정.

배경: 이 기능 이전에는 예측을 **기록만 하고 채점 가능한 형식이 아니었다.**
판정 기준이 예측 시점에 없어 결과를 본 뒤 기준을 만들 수 있었고, 신뢰도가 없어
"확신한 만큼 맞았나"(보정)를 잴 수 없었으며, 판정 기한이 없어 불리한 예측을
미판정으로 남기면 적중률이 저절로 올라갔다.

설계는 자매 프로젝트 I2OS(`app/predictions.py`)에서 가져왔다.
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms.prediction_scoring import (
    score, validate, is_scoreable, MIN_CRITERIA_LEN,
)

TODAY = dt.date(2026, 8, 9)
CRITERIA = "2026-11-07까지 WHO 발병공고 또는 해당국 보건당국의 공식 발병 선언이 확인되면 correct."


def _p(pid, confidence=0.7, outcome=None, resolves_by="2026-11-07",
       criteria=CRITERIA, verified=True, sources=("https://who.int/don/1",)):
    return {
        "id": pid,
        "predicted_at": "2026-08-09T00:00:00+00:00",
        "confidence": confidence,
        "resolution_criteria": criteria,
        "resolves_by": resolves_by,
        "outcome": outcome,
        "verified_at": "2026-08-10T00:00:00+00:00" if (outcome and verified) else None,
        "resolution_sources": list(sources) if (outcome and verified) else None,
    }


# ── 채점 가능 형식 판정 ───────────────────────────────────────────
def test_legacy_records_are_excluded_not_silently_counted():
    """★핵심★ 판정 기준·신뢰도가 없는 옛 기록을 억지로 채점하면 없는 실적이 생긴다.
    빼되 **몇 건을 뺐는지 반드시 보고**한다(조용히 사라지면 그것도 거짓말이다)."""
    legacy = {"id": 1, "predicted_at": "2026-01-01T00:00:00+00:00", "confidence": None,
              "resolution_criteria": None, "resolves_by": None, "outcome": None}
    assert is_scoreable(legacy) is False
    out = score([legacy], today=TODAY)
    assert out["total"] == 1
    assert out["scoreable"] == 0
    assert out["unscoreable_legacy"] == 1
    assert out["accuracy"] is None
    assert "소급 추가하지 않는다" in out["note"]


# ── 규칙 검증 ────────────────────────────────────────────────────
def test_confidence_must_be_strictly_between_zero_and_one():
    """0이나 1은 '절대'라는 뜻이라 Brier에서 사실상 무한 벌점이다.
    그건 예측이 아니라 단정이므로 허용하지 않는다."""
    assert any("0과 1 사이" in m for m in validate(_p(1, confidence=0.0)))
    assert any("0과 1 사이" in m for m in validate(_p(1, confidence=1.0)))
    assert validate(_p(1, confidence=0.5)) == []


def test_missing_confidence_is_rejected():
    assert any("신뢰도" in m for m in validate(_p(1, confidence=None)))


def test_short_resolution_criteria_is_rejected():
    """★ 한 줄짜리 기준은 나중에 해석 여지가 생겨 결국 합리화된다 ★"""
    assert any("너무 짧다" in m for m in validate(_p(1, criteria="맞으면 correct")))
    assert len("맞으면 correct") < MIN_CRITERIA_LEN


def test_resolve_deadline_must_be_after_prediction():
    assert any("뒤여야" in m for m in validate(_p(1, resolves_by="2026-08-01")))


def test_resolved_prediction_requires_sources():
    """판정했는데 근거가 없으면 그 판정이 옳았는지 나중에 못 되짚는다."""
    bad = _p(1, outcome="correct", sources=())
    assert any("근거 출처" in m for m in validate(bad))


def test_unknown_outcome_rejected():
    assert any("알 수 없는 판정" in m for m in validate(_p(1, outcome="맞음")))


# ── 채점 ─────────────────────────────────────────────────────────
def test_accuracy_and_brier():
    recs = [
        _p(1, 0.8, "correct"), _p(2, 0.8, "correct"),
        _p(3, 0.8, "correct"), _p(4, 0.8, "incorrect"),
    ]
    out = score(recs, today=TODAY)
    assert out["resolved"] == 4
    assert out["accuracy"] == 0.75
    # (0.2² × 3 + 0.8² × 1) / 4 = (0.12 + 0.64) / 4 = 0.19
    assert out["brier"] == pytest.approx(0.19, abs=1e-6)


def test_brier_punishes_overconfidence():
    """★이게 Brier를 쓰는 이유★ 적중률이 같아도 확신이 틀리면 점수가 나빠진다.
    쉬운 예측만 골라 담아 적중률을 부풀리는 것을 막는다."""
    humble = score([_p(1, 0.55, "incorrect")], today=TODAY)["brier"]
    cocky = score([_p(1, 0.95, "incorrect")], today=TODAY)["brier"]
    assert cocky > humble


def test_calibration_reports_stated_vs_actual():
    """"0.8이라고 말한 것들이 실제로 80% 맞았는가" — 재보험이 먼저 보는 지표."""
    recs = [_p(1, 0.8, "correct"), _p(2, 0.8, "correct"),
            _p(3, 0.8, "correct"), _p(4, 0.8, "incorrect")]
    bucket = score(recs, today=TODAY)["calibration"][0]
    assert bucket["range"] == "0.7~0.9"
    assert bucket["count"] == 4
    assert bucket["stated"] == 0.8
    assert bucket["actual"] == 0.75


def test_ambiguous_is_excluded_but_counted():
    """참/거짓으로 못 나누는 걸 억지로 밀어넣으면 채점이 오염된다.
    빼되 건수는 센다 — 많아지면 예측을 모호하게 쓰고 있다는 신호다."""
    out = score([_p(1, 0.7, "correct"), _p(2, 0.7, "ambiguous"),
                 _p(3, 0.7, "cancelled")], today=TODAY)
    assert out["resolved"] == 1
    assert out["excluded"] == 2
    assert out["accuracy"] == 1.0     # 판정된 1건만으로 계산


def test_overdue_unresolved_is_flagged():
    """★핵심 회귀★ 판정 기한이 지났는데 안 하면 **불리한 예측만 미판정으로 남아
    적중률이 부풀려진다.** 조용히 넘어가면 안 되는 자리다."""
    out = score([_p(9, 0.7, None, resolves_by="2026-07-01")], today=TODAY)
    assert out["overdue"] == [9]
    assert "부풀려진다" in out["note"]


def test_no_resolutions_says_so_plainly():
    """판정이 없으면 '성적이 없는 것이지 좋은 것이 아니다'라고 말해야 한다."""
    out = score([_p(1, 0.7, None)], today=TODAY)
    assert out["accuracy"] is None
    assert out["brier"] is None
    assert "성적이 없는 것이지 좋은 것이 아니다" in out["note"]


def test_small_sample_is_called_out():
    out = score([_p(1, 0.7, "correct"), _p(2, 0.7, "correct")], today=TODAY)
    assert out["accuracy"] == 1.0
    assert "통계적으로 이르다" in out["note"]   # 100%를 실적처럼 내보내지 않는다


# ── DB 연동 ──────────────────────────────────────────────────────
def test_db_roundtrip_records_and_scores(isolated_db):
    import db as dbmod
    by = (dt.date.today() + dt.timedelta(days=90)).isoformat()
    p = dbmod.create_prediction(
        "콩고민주공화국", "에볼라", 82.0, ["신호 근거"],
        confidence=0.65, resolution_criteria=CRITERIA, resolves_by=by,
    )
    assert p["confidence"] == 0.65
    assert is_scoreable(p)

    dbmod.verify_prediction(p["id"], "WHO 발병공고 확인", outcome="correct",
                            resolution_sources=["https://who.int/don/xyz"])
    stored = dbmod.get_prediction(p["id"])
    assert stored["outcome"] == "correct"
    assert stored["correct"] == 1          # 기존 통계와의 호환도 유지
    assert validate(stored) == []

    out = score(dbmod.list_predictions())
    assert out["resolved"] == 1 and out["accuracy"] == 1.0


def test_db_rejects_unknown_outcome(isolated_db):
    import db as dbmod
    p = dbmod.create_prediction("한국", "홍역", 71.0, ["근거"], confidence=0.5,
                                resolution_criteria=CRITERIA, resolves_by="2026-12-31")
    with pytest.raises(ValueError):
        dbmod.verify_prediction(p["id"], "결과", outcome="맞음")


def test_legacy_verify_signature_still_works(isolated_db):
    """호출부가 여럿이라 한 번에 못 바꾼다 — 예전 방식도 계속 받아야 한다."""
    import db as dbmod
    p = dbmod.create_prediction("일본", "독감", 72.0, ["근거"], confidence=0.5,
                                resolution_criteria=CRITERIA, resolves_by="2026-12-31")
    out = dbmod.verify_prediction(p["id"], "발생 확인", True, 3)
    assert out["outcome"] == "correct"
    assert out["lead_days"] == 3


def test_auto_logged_predictions_are_scoreable(isolated_db, monkeypatch):
    """★회귀★ 자동 기록이 판정 기준 없이 쌓이면 아무리 오래 돌려도 채점이 안 된다.
    실제로 이 기능 이전 기록은 전부 채점 불가였다."""
    from algorithms import country_risk as cr
    fake = [{
        "country": "COD", "name": "콩고민주공화국", "raw_score": 85.0, "risk_score": 60.0,
        "raw_score_components": {"direct_signal": None, "nlp_signal": 85.0, "nlp_signal_count": 7},
        "vulnerability_index": 0.64,
    }]
    logged = cr.log_notable_predictions(fake)
    assert len(logged) == 1
    p = logged[0]
    assert is_scoreable(p), "자동 기록이 채점 불가 형식으로 저장됐다"
    assert validate(p) == []
    assert 0 < p["confidence"] < 1

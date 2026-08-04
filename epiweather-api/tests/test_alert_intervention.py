"""경보 → NPI 반사실 브리핑 — 예측을 의사결정으로 승격 + OpenTimestamps 봉인.
정직성: 반사실은 '모델 시나리오'로 표시, 봉인 실패는 sealed=False로 정직 표시."""
from __future__ import annotations
from unittest.mock import patch

from algorithms import alert_intervention as ai


def test_assume_threat_maps_by_disease_and_tier():
    assert ai.assume_threat("에볼라", "critical")[0] == "severe"
    assert ai.assume_threat("신종 미상 폐렴", "high")[0] == "novel"
    assert ai.assume_threat("계절 인플루엔자", "high")[0] == "flu"
    # 질병 불명 → 등급으로 예방적 매핑
    assert ai.assume_threat(None, "critical")[0] == "novel"
    assert ai.assume_threat(None, "high")[0] == "flu"


def test_brief_has_three_scenarios_and_disclaimer():
    b = ai.intervention_brief("에볼라", "COD", "critical", 88)
    assert set(b["scenarios"]) == {"no_action", "mild", "strong"}
    assert b["is_modeled_scenario"] is True
    assert "모델" in b["disclaimer"]              # 방향성 참고임을 항상 명시
    assert b["recommended"] in ("mild", "strong")


def test_intervention_reduces_deaths_vs_no_action():
    """개입 시나리오는 무대응보다 사망이 적고 구할 생명이 양수여야(반사실 방향성)."""
    b = ai.intervention_brief("에볼라", "COD", "critical", 88)
    no_action = b["scenarios"]["no_action"]["total_deaths"]
    strong = b["scenarios"]["strong"]
    assert strong["total_deaths"] <= no_action
    assert strong["saved_lives"] > 0


def test_explicit_threat_overrides_disease_heuristic():
    b = ai.intervention_brief("알수없는병", "KOR", "high", 60, threat="severe")
    assert b["assumed_threat"] == "severe"
    assert "명시된" in b["threat_basis"]


def test_sealed_brief_digest_computed_even_without_network():
    """봉인 실패(네트워크 없음)여도 다이제스트는 계산되고 sealed=False로 정직 표시."""
    with patch("algorithms.prediction_timestamp.submit_timestamp", return_value=None):
        b = ai.sealed_brief("에볼라", "COD", "critical", 88, seal=True)
    ts = b["timestamp"]
    assert ts["sealed"] is False
    assert len(ts["digest_sha256"]) == 64          # SHA-256 hex
    assert ts["proof_hex"] is None


def test_sealed_brief_marks_sealed_when_proof_returned():
    with patch("algorithms.prediction_timestamp.submit_timestamp", return_value="deadbeef"):
        b = ai.sealed_brief("에볼라", "COD", "critical", 88, seal=True)
    assert b["timestamp"]["sealed"] is True
    assert b["timestamp"]["proof_hex"] == "deadbeef"


def test_seal_false_skips_network_but_keeps_digest():
    with patch("algorithms.prediction_timestamp.submit_timestamp") as m:
        b = ai.sealed_brief("에볼라", "COD", "critical", 88, seal=False)
    m.assert_not_called()
    assert b["timestamp"]["sealed"] is False
    assert len(b["timestamp"]["digest_sha256"]) == 64


def test_enrich_alerts_attaches_npi_summary():
    alerts = [{"tier": "critical", "label": "에볼라 COD", "score": 88,
               "disease": "에볼라", "country": "COD"}]
    out = ai.enrich_alerts_with_briefs(alerts)
    assert "npi_summary" in out[0]
    assert "개입 브리핑" in out[0]["npi_summary"]
    assert out[0]["npi_brief"]["assumed_threat"] == "severe"

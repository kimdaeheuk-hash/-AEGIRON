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


def test_known_disease_uses_measured_params():
    """등재 질병은 문헌 실측 R0/CFR로 캘리브레이션됨을 정직하게 표시."""
    b = ai.intervention_brief("에볼라", "COD", "critical", 88)
    assert b["calibration"] == "disease_measured"
    assert b["epidemic_params"]["cfr"] == 0.50        # 에볼라 실측 CFR
    assert b["epidemic_params"]["R0"] == 1.8
    assert "WHO" in b["epidemic_params"]["source"]


def test_unknown_disease_falls_back_to_generic():
    b = ai.intervention_brief("정체불명 신종 X", "KOR", "critical", 80)
    assert b["calibration"] == "generic_tier"
    assert "예시 상수" in b["epidemic_params"]["source"]


def test_low_r0_disease_shows_limited_spread():
    """니파(R0<1)는 SEIR상 대규모 확산이 안 나야 하고 그 사실이 노트로 붙어야 함."""
    b = ai.intervention_brief("니파바이러스", "IND", "critical", 85)
    assert b["limited_human_transmission"] is True
    assert b["spread_note"] and "제한" in b["spread_note"]
    # 무대응이어도 유행이 작다(사망 규모가 고전파 병원체보다 훨씬 작음)
    assert b["scenarios"]["no_action"]["total_deaths"] < 1000


def test_explicit_threat_skips_calibration():
    """위협을 명시하면 질병 캘리브레이션을 생략하고 generic tier를 존중."""
    b = ai.intervention_brief("에볼라", "COD", "critical", 88, threat="severe")
    assert b["calibration"] == "generic_tier"
    assert b["assumed_threat"] == "severe"


def test_disease_params_lookup_matches_aliases():
    from algorithms import disease_params as dp
    assert dp.lookup("mpox 의심")["key"] == "mpox"
    assert dp.lookup("계절 독감 유행")["key"] == "influenza_seasonal"
    assert dp.lookup("완전히 새로운 병") is None


def test_enrich_alerts_attaches_npi_summary():
    alerts = [{"tier": "critical", "label": "에볼라 COD", "score": 88,
               "disease": "에볼라", "country": "COD"}]
    out = ai.enrich_alerts_with_briefs(alerts)
    assert "npi_summary" in out[0]
    assert "개입 브리핑" in out[0]["npi_summary"]
    assert out[0]["npi_brief"]["assumed_threat"] == "severe"


# ── 발병률 상한(87배 과대추정 회귀) ──────────────────────────────
def test_ebola_no_action_stays_near_historical_scale():
    """★핵심 회귀★ 상한 없는 SEIR가 에볼라 무대응 사망을 989,509명으로 냈다 —
    역사상 최대 발병(서아프리카 2014~16, 11,325명)의 87배다. R0 1.8은 '초기·대응 전'
    값이라 인구 500만 전체 유행곡선에 그대로 쓰면 안 된다."""
    from algorithms.alert_intervention import intervention_brief
    b = intervention_brief("에볼라", "COD", "critical", 85.0)
    deaths = b["scenarios"]["no_action"]["total_deaths"]
    assert deaths < 100_000, f"에볼라 무대응 사망 {deaths:,} — 역사 규모를 크게 벗어남"
    assert b["plausibility"]["ratio_vs_historical"] < 5


def test_contact_limited_pathogens_do_not_burn_whole_population():
    """접촉 제한 병원체는 인구 전체를 태우면 안 된다 — 도달 가능 인구가 제한된다."""
    from algorithms.defense import simulate, N
    from algorithms.common import PRESETS
    from algorithms import disease_params as dp
    out = simulate(PRESETS["none"], "severe",
                   params=dp.as_threat_params(dp.lookup("에볼라")))
    assert out["attack_rate_capped"] is True
    assert out["population_modeled"] < N        # 전체 인구가 아니다


def test_sustained_transmission_pathogens_use_full_population():
    """홍역처럼 실제로 일반 유행을 만드는 병원체는 상한을 걸지 않는다 —
    그건 SEIR가 맞는 모델이다."""
    from algorithms.defense import simulate, N
    from algorithms.common import PRESETS
    from algorithms import disease_params as dp
    out = simulate(PRESETS["none"], "severe",
                   params=dp.as_threat_params(dp.lookup("홍역")))
    assert out["attack_rate_capped"] is False
    assert out["population_modeled"] == N


def test_all_registered_diseases_stay_within_plausible_range():
    """등재된 모든 질병이 역사 대조를 통과해야 한다 — 상한값이 판단치라
    하나를 고치다 다른 게 틀어질 수 있다."""
    from algorithms.alert_intervention import intervention_brief
    from algorithms.disease_params import DISEASE_PARAMS
    bad = []
    for key, p in DISEASE_PARAMS.items():
        b = intervention_brief(p["nm"], "COD", "critical", 85.0)
        pl = b["plausibility"]
        if pl.get("checked") and pl.get("implausible"):
            bad.append(f"{p['nm']}={pl['ratio_vs_historical']}x")
    assert not bad, f"역사 대조 실패: {', '.join(bad)}"


def test_plausibility_travels_in_the_payload():
    """경고가 docstring에만 있으면 숫자만 떨어져 나가 화면·자료에서 그대로 쓰인다."""
    from algorithms.alert_intervention import intervention_brief
    b = intervention_brief("에볼라", "COD", "critical", 85.0)
    pl = b["plausibility"]
    assert pl["checked"] is True
    assert pl["historical_max_deaths"] == 11325
    assert "역사상 최대" in pl["note"]


def test_plausibility_flags_implausible_output():
    """상한이 잘못 잡혀 모델값이 역사 최대의 10배를 넘으면 자동으로 잡아야 한다."""
    from algorithms.disease_params import plausibility
    out = plausibility("ebola", 989_509)          # 상한 적용 전 실측값
    assert out["implausible"] is True
    assert out["ratio_vs_historical"] > 80
    assert "대외 자료에 쓰지 말 것" in out["note"]


def test_plausibility_skips_unknown_disease():
    from algorithms.disease_params import plausibility
    assert plausibility(None, 1000)["checked"] is False

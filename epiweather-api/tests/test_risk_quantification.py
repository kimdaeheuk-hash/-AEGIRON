"""팬데믹 리스크 계량화(㉓) — 노출 지수가 실제 신호·취약성·확산에서 정직하게
합성되는지, 그리고 "절대 확률이 아님" 플래그가 항상 붙는지 확인. 이 플래그가
빠지면 보험·금융이 상대 지표를 절대 확률로 오해할 수 있어 회귀 방지가 중요."""
from __future__ import annotations
import pytest

from algorithms import country_risk as country_risk_mod
from algorithms.risk_quantification import (
    quantify_country_exposure, quantify_portfolio, W_SIGNAL, W_VULNERABILITY, W_SPREAD,
)


@pytest.fixture(autouse=True)
def no_real_country_data(monkeypatch):
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: {})


def test_curated_country_without_signal_uses_latent_exposure(isolated_db):
    """신호가 없으면 signal_pressure=0이라도 취약성·확산으로 잠재 노출은 계산됨."""
    result = quantify_country_exposure("KOR")
    assert result["has_active_signal"] is False
    assert result["components"]["signal_pressure"] == 0.0
    assert result["exposure_index"] > 0  # 취약성·확산분은 남음


def test_exposure_index_always_flags_not_a_probability(isolated_db):
    """★ 핵심 정직성 회귀 방지 — is_probability가 반드시 False여야 함."""
    result = quantify_country_exposure("KOR")
    assert result["is_probability"] is False
    assert result["weights_calibrated"] is False


def test_active_signal_raises_exposure(isolated_db):
    """실제 신호(country_iso3 매칭)가 들어오면 노출 지수가 무신호 대비 올라가야 함."""
    import db as dbmod
    before = quantify_country_exposure("COD")["exposure_index"]

    dbmod.create_extracted_signal(
        source="who", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=["spike"], symptom=None, transmission=None, source_trust=1.0,
        signal_date="2026-07-20", raw_text="t", country_iso3="COD",
    )
    after = quantify_country_exposure("COD")
    assert after["has_active_signal"] is True
    assert after["exposure_index"] > before


def test_exposure_index_matches_weighted_formula(isolated_db):
    result = quantify_country_exposure("KOR")
    c = result["components"]
    expected = round(
        100 * (W_SIGNAL * c["signal_pressure"] + W_VULNERABILITY * c["vulnerability"]
               + W_SPREAD * c["spread_potential"]),
        1,
    )
    assert result["exposure_index"] == expected


def test_tier2_country_without_signal_raises_keyerror(isolated_db):
    with pytest.raises(KeyError):
        quantify_country_exposure("IND")


def test_portfolio_ranks_and_adds_percentile_and_empirical_basis(isolated_db):
    result = quantify_portfolio()
    countries = result["countries"]
    # Tier-1 14개국 전부 포함(신호 없어도 잠재 노출로 랭킹됨)
    assert len(countries) == len(country_risk_mod.COUNTRIES)
    # 내림차순 정렬 + 백분위 존재
    scores = [c["exposure_index"] for c in countries]
    assert scores == sorted(scores, reverse=True)
    assert countries[0]["percentile"] == pytest.approx(100.0, abs=0.1)
    # 실증 근거·면책 고지가 항상 붙어야 함(정직성)
    assert "empirical_basis" in result
    assert "verified_lead_time_cases" in result["empirical_basis"]
    assert "disclaimer" in result


def test_portfolio_includes_auto_discovered_tier2(isolated_db):
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who", disease="뎅기열", location="인도", signal_type="급증",
        severity=["spike"], symptom=None, transmission=None, source_trust=0.9,
        signal_date="2026-07-20", raw_text="t", country_iso3="IND",
    )
    result = quantify_portfolio()
    ind = next((c for c in result["countries"] if c["country"] == "IND"), None)
    assert ind is not None
    assert ind["coverage_tier"] == "auto"


def test_measured_but_quiet_is_not_an_active_signal(isolated_db, monkeypatch):
    """★회귀★ '측정했는데 이상 없음'(anomaly=0.0)을 '활성신호 있음'으로 보고하면 안 된다.

    _anomaly_score는 None='판단할 데이터 부족', 0.0='데이터 있고 이상 없음'을 구분한다.
    `raw is not None`으로만 판정하면 실데이터가 쌓일수록 조용한 나라가 전부
    '활성신호 있음'으로 뒤집힌다 — 실제로 KDCA 데이터 유입 후 한국이 그렇게 됐다.
    감시 시스템에서 이 방향 오류는 '평시를 경보로 읽는' 쪽이라 특히 나쁘다."""
    from algorithms import risk_quantification as rq

    def quiet(country_id):
        return {"name": "조용한나라", "coverage_tier": "curated",
                "raw_score": 0.0,          # 측정됨 · 이상 없음
                "vulnerability_index": 0.4, "vulnerability_source": "real_data"}

    monkeypatch.setattr(rq, "compute_country_risk", quiet)
    r = rq.quantify_country_exposure("KOR")
    assert r["has_active_signal"] is False
    assert r["components"]["signal_pressure"] == 0.0
    assert r["exposure_index"] > 0        # 취약성·확산 기반 잠재 노출은 남는다


def test_nonzero_anomaly_is_an_active_signal(isolated_db, monkeypatch):
    """반대 방향도 고정 — 실제 이상도가 잡히면 활성신호로 봐야 한다."""
    from algorithms import risk_quantification as rq

    def noisy(country_id):
        return {"name": "시끄러운나라", "coverage_tier": "curated",
                "raw_score": 12.0, "vulnerability_index": 0.4,
                "vulnerability_source": "real_data"}

    monkeypatch.setattr(rq, "compute_country_risk", noisy)
    r = rq.quantify_country_exposure("KOR")
    assert r["has_active_signal"] is True
    assert r["components"]["signal_pressure"] == 0.12

"""국가별 위험지수 — 취약성지수가 실측인지 추정 시드값인지가 API 응답에서
항상 정확히 드러나는지 확인(감사에서 지적된 '겉보기엔 실측값처럼 보임' 문제의
회귀 방지). country_indicators 캐시는 monkeypatch로 통제해 테스트를 결정론적으로
만든다 — 실제 파일시스템 캐시 상태에 테스트 결과가 좌우되면 안 됨."""
from __future__ import annotations
import pytest

from algorithms import country_risk as country_risk_mod
from algorithms.country_risk import (
    compute_country_risk, vulnerability_index, COUNTRIES, DEFAULT_VULNERABILITY,
)


@pytest.fixture(autouse=True)
def no_real_country_data(monkeypatch):
    """기본값: 실데이터 캐시 없음 → 전부 seed_fallback. 개별 테스트가 필요하면 override."""
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: {})


@pytest.mark.parametrize("country_id", list(COUNTRIES))
def test_every_seed_country_flags_vulnerability_as_seed_fallback_without_cache(isolated_db, country_id):
    result = compute_country_risk(country_id)
    assert result["vulnerability_estimated"] is True
    assert result["vulnerability_source"] == "seed_fallback"


def test_country_with_full_real_data_cache_flags_as_real_data(isolated_db, monkeypatch):
    fake_cache = {
        "South Korea": {
            "healthcare_infra": 0.9, "population_density": 0.8, "airport_connectivity": 0.7,
        }
    }
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: fake_cache)
    result = compute_country_risk("South Korea")
    assert result["vulnerability_estimated"] is False
    assert result["vulnerability_source"] == "real_data"


def test_country_with_partial_real_data_still_flags_as_seed_fallback(isolated_db, monkeypatch):
    """3개 실데이터 필드 중 하나라도 빠지면(부분 캐시) 전체를 seed_fallback으로 취급."""
    fake_cache = {"South Korea": {"healthcare_infra": 0.9}}  # population_density·airport_connectivity 없음
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: fake_cache)
    result = compute_country_risk("South Korea")
    assert result["vulnerability_estimated"] is True
    assert result["vulnerability_source"] == "seed_fallback"


def test_unknown_country_raises_keyerror(isolated_db):
    with pytest.raises(KeyError):
        compute_country_risk("Atlantis")


def test_vulnerability_index_unknown_country_uses_neutral_default():
    assert vulnerability_index("Atlantis") == DEFAULT_VULNERABILITY


def test_vulnerability_index_is_deterministic_for_seed_country():
    assert vulnerability_index("South Korea") == vulnerability_index("South Korea")
    assert 0.0 <= vulnerability_index("South Korea") <= 1.0

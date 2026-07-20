"""국가별 위험지수 — 취약성지수가 실측이 아니라 추정 시드값이라는 사실이
API 응답에서 항상 드러나는지 확인(감사에서 지적된 '겉보기엔 실측값처럼 보임'
문제의 회귀 방지)."""
from __future__ import annotations
import pytest

from algorithms.country_risk import (
    compute_country_risk, vulnerability_index, COUNTRIES, DEFAULT_VULNERABILITY,
)


@pytest.mark.parametrize("country_id", list(COUNTRIES))
def test_every_seed_country_flags_vulnerability_as_estimated(isolated_db, country_id):
    result = compute_country_risk(country_id)
    assert result["vulnerability_estimated"] is True
    assert result["vulnerability_source"] == "seed"


def test_unknown_country_raises_keyerror(isolated_db):
    with pytest.raises(KeyError):
        compute_country_risk("Atlantis")


def test_vulnerability_index_unknown_country_uses_neutral_default():
    assert vulnerability_index("Atlantis") == DEFAULT_VULNERABILITY


def test_vulnerability_index_is_deterministic_for_seed_country():
    assert vulnerability_index("South Korea") == vulnerability_index("South Korea")
    assert 0.0 <= vulnerability_index("South Korea") <= 1.0

"""국가별 위험지수 — 취약성지수가 실측인지 추정 시드값인지가 API 응답에서
항상 정확히 드러나는지 확인(감사에서 지적된 '겉보기엔 실측값처럼 보임' 문제의
회귀 방지). country_indicators 캐시는 monkeypatch로 통제해 테스트를 결정론적으로
만든다 — 실제 파일시스템 캐시 상태에 테스트 결과가 좌우되면 안 됨."""
from __future__ import annotations
import pytest

import datetime as dt

from algorithms import country_risk as country_risk_mod
from algorithms.country_risk import (
    compute_country_risk, vulnerability_index, COUNTRIES, DEFAULT_VULNERABILITY,
    _record_matches_country, _nlp_raw_score, discovered_tier2_countries, rank_countries,
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
        "KOR": {
            "healthcare_infra": 0.9, "population_density": 0.8, "airport_connectivity": 0.7,
        }
    }
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: fake_cache)
    result = compute_country_risk("KOR")
    assert result["vulnerability_estimated"] is False
    assert result["vulnerability_source"] == "real_data"


def test_country_with_partial_real_data_still_flags_as_seed_fallback(isolated_db, monkeypatch):
    """3개 실데이터 필드 중 하나라도 빠지면(부분 캐시) 전체를 seed_fallback으로 취급."""
    fake_cache = {"KOR": {"healthcare_infra": 0.9}}  # population_density·airport_connectivity 없음
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: fake_cache)
    result = compute_country_risk("KOR")
    assert result["vulnerability_estimated"] is True
    assert result["vulnerability_source"] == "seed_fallback"


def test_unknown_country_raises_keyerror(isolated_db):
    with pytest.raises(KeyError):
        compute_country_risk("Atlantis")


def test_vulnerability_index_unknown_country_uses_neutral_default():
    assert vulnerability_index("Atlantis") == DEFAULT_VULNERABILITY


def test_vulnerability_index_is_deterministic_for_seed_country():
    assert vulnerability_index("KOR") == vulnerability_index("KOR")
    assert 0.0 <= vulnerability_index("KOR") <= 1.0


# ── ⑯⑰ country_iso3 정확매칭 vs 레거시 alias 폴백 ────────────────────


def test_record_with_country_iso3_matches_exactly_regardless_of_location_text():
    """country_iso3가 있으면 location 문구가 별칭 사전에 전혀 없어도 매칭돼야 함
    — 이게 바로 별칭사전 없이 전세계 커버리지가 열리는 지점."""
    record = {"country_iso3": "COD", "location": "그 어떤 별칭에도 없는 문구"}
    assert _record_matches_country(record, "COD", COUNTRIES["COD"]["aliases"]) is True
    assert _record_matches_country(record, "KOR", COUNTRIES["KOR"]["aliases"]) is False


def test_record_without_country_iso3_falls_back_to_alias_matching():
    """country_iso3가 없는 구형 레코드는 기존 alias substring 매칭으로 계속 동작 —
    ISO3 도입 전에 쌓인 데이터가 유실되지 않음(하위호환)."""
    record = {"country_iso3": None, "location": "콩고민주공화국에서 신규 발생"}
    assert _record_matches_country(record, "COD", COUNTRIES["COD"]["aliases"]) is True
    assert _record_matches_country(record, "KOR", COUNTRIES["KOR"]["aliases"]) is False


def test_record_missing_country_iso3_key_entirely_falls_back_to_alias():
    """dict.get 기본값 처리 확인 — country_iso3 키 자체가 없어도 안전하게 폴백."""
    record = {"location": "한국 질병관리청 발표"}
    assert _record_matches_country(record, "KOR", COUNTRIES["KOR"]["aliases"]) is True


def test_nlp_raw_score_uses_country_iso3_even_with_unrelated_location_text(isolated_db, monkeypatch):
    """실제 파이프라인 단위에서: country_iso3만 맞으면 location 표기가 들쭉날쭉해도
    _nlp_raw_score가 정확히 집계하는지 확인."""
    import db as dbmod

    dbmod.create_extracted_signal(
        source="test", disease="에볼라", location="Somewhere unusual phrasing",
        signal_type="신규발생", severity=["spike"], symptom=None, transmission=None,
        source_trust=1.0, signal_date="2026-07-01", raw_text="t", country_iso3="COD",
    )
    score, count = _nlp_raw_score("COD")
    assert count == 1
    assert score == 85.0  # 신규발생 severity(85) * trust(1.0)


# ── ⑱ Tier-2 전세계 국가 자동 커버리지 ────────────────────────────


def test_tier2_country_with_no_signal_raises_keyerror(isolated_db):
    """COUNTRIES(Tier-1)에도 없고 실제 신호도 없는 국가는 근거 없이 만들어지면
    안 됨 — 임의 ISO3 코드로 위험도가 조작되는 걸 막는 안전장치."""
    with pytest.raises(KeyError):
        compute_country_risk("IND")


def test_tier2_country_with_recent_signal_is_auto_covered(isolated_db):
    """country_iso3 신호가 실제로 있으면 COUNTRIES에 없어도(Tier-2) 자동으로
    위험도가 계산되고 coverage_tier로 정직하게 구분됨."""
    import db as dbmod

    dbmod.create_extracted_signal(
        source="test", disease="뎅기열", location="인도 델리에서 발생",
        signal_type="급증", severity=["spike"], symptom=None, transmission=None,
        source_trust=0.9, signal_date="2026-07-01", raw_text="t", country_iso3="IND",
    )
    result = compute_country_risk("IND")
    assert result["coverage_tier"] == "auto"
    assert result["has_signal"] is True


def test_discovered_tier2_countries_excludes_curated_and_old_signals(isolated_db):
    import db as dbmod

    # Tier-1(KOR)은 COUNTRIES에 이미 있으므로 discovered 목록에서 제외돼야 함
    dbmod.create_extracted_signal(
        source="test", disease="독감", location="한국", signal_type="진행중",
        severity=[], symptom=None, transmission=None, source_trust=0.8,
        signal_date="2026-07-01", raw_text="t", country_iso3="KOR",
    )
    # 최근 신호(IND) — 포함돼야 함
    dbmod.create_extracted_signal(
        source="test", disease="뎅기열", location="인도", signal_type="급증",
        severity=[], symptom=None, transmission=None, source_trust=0.9,
        signal_date="2026-07-01", raw_text="t", country_iso3="IND",
    )
    # 40일 전 신호(VNM) — 30일 발견 윈도우 밖이라 제외돼야 함
    old_at = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)).isoformat()
    with dbmod.get_connection() as conn:
        conn.execute(
            "INSERT INTO extracted_signals "
            "(extracted_at, source, disease, location, signal_type, severity, "
            " symptom, transmission, source_trust, signal_date, known_disease, raw_text, country_iso3) "
            "VALUES (?, 'test', '콜레라', '베트남', '진행중', '[]', NULL, NULL, 0.7, '2026-05-01', 1, 't', 'VNM')",
            (old_at,),
        )
        conn.commit()

    discovered = discovered_tier2_countries()
    assert discovered == {"IND"}


def test_rank_countries_includes_auto_discovered_tier2_country(isolated_db, monkeypatch):
    monkeypatch.setattr(country_risk_mod, "load_country_indicators", lambda: {})
    import db as dbmod

    dbmod.create_extracted_signal(
        source="test", disease="뎅기열", location="인도", signal_type="급증",
        severity=[], symptom=None, transmission=None, source_trust=0.9,
        signal_date="2026-07-01", raw_text="t", country_iso3="IND",
    )
    ranked = rank_countries()["countries"]
    ind = next((c for c in ranked if c["country"] == "IND"), None)
    assert ind is not None
    assert ind["coverage_tier"] == "auto"
    # Tier-1은 여전히 전부 포함돼야 함(회귀 방지)
    assert len(ranked) == len(COUNTRIES) + 1

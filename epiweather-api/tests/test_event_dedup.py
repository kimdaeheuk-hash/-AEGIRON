"""이벤트 중복제거 — 인수인계서 Part5 ⑩.
같은 질병을 보고한 여러 출처는 하나로 병합되고, 다른 질병은 안 섞이는지 확인."""
from __future__ import annotations

from algorithms.event_dedup import normalize_disease, dedupe_events


def test_normalize_disease_matches_known_aliases():
    assert normalize_disease("에볼라 바이러스(Bundibugyo)") == "에볼라"
    assert normalize_disease("Ebola outbreak in DRC") == "에볼라"
    assert normalize_disease("h5n1 case confirmed") == "조류인플루엔자"
    assert normalize_disease("COVID-19 variant") == "코로나19"


def test_normalize_disease_none_input_returns_none():
    assert normalize_disease(None) is None


def test_normalize_disease_unknown_disease_kept_verbatim():
    """사전에 없는 질병명은 병합하지 않고 원문 유지 — 잘못 합치는 것보다 안전."""
    assert normalize_disease("정체불명 신종질병 X") == "정체불명 신종질병 X"


def _make_signal(dbmod, source, disease, location, signal_type, trust, date):
    return dbmod.create_extracted_signal(
        source=source, disease=disease, location=location, signal_type=signal_type,
        severity=["unusual"], symptom=None, transmission=None,
        source_trust=trust, signal_date=date, raw_text=f"{source}: {disease}",
    )


def test_multiple_sources_reporting_same_disease_merge_into_one_event(isolated_db):
    _make_signal(isolated_db, "WHO", "에볼라", "DRC", "신규발생", 1.00, "2026-05-16")
    _make_signal(isolated_db, "Wikipedia", "ebola", "DRC", "급증", 0.90, "2026-05-17")
    _make_signal(isolated_db, "Perplexity", "MERS", "Saudi Arabia", "진행중", 0.65, "2026-06-01")

    events = dedupe_events()

    ebola = [e for e in events if e["disease"] == "에볼라"]
    assert len(ebola) == 1
    assert ebola[0]["source_count"] == 2
    assert set(ebola[0]["sources"]) == {"WHO", "Wikipedia"}

    mers = [e for e in events if e["disease"] == "MERS"]
    assert len(mers) == 1
    assert mers[0]["source_count"] == 1


def test_merged_score_is_trust_weighted_not_plain_average(isolated_db):
    """출처신뢰도가 다른 두 보고를 병합할 때 단순평균이 아니라 신뢰도가중 평균인지 확인."""
    _make_signal(isolated_db, "WHO", "콜레라", "Yemen", "신규발생", 1.00, "2026-01-01")   # severity 85
    _make_signal(isolated_db, "SNS", "콜레라", "Yemen", "감소", 0.20, "2026-01-02")        # severity 15

    events = dedupe_events()
    cholera = next(e for e in events if e["disease"] == "콜레라")
    # 신뢰도가중 평균이므로 단순평균((85+15)/2=50)보다 신뢰도 높은 WHO(85) 쪽에 훨씬 가까워야 함
    assert cholera["merged_score"] > 50

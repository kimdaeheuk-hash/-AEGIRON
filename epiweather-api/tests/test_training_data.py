"""학습 데이터 export(독자 모델 IP 1단계) — extracted_signals가 증류 학습쌍으로
정확히 변환되는지, 실버/골드 라벨 구분·빈 라벨 제외를 확인."""
from __future__ import annotations

from algorithms import training_data as td


def test_export_pairs_roundtrip(isolated_db):
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=["high"], symptom="출혈", transmission="접촉", source_trust=0.9,
        signal_date="2026-05-15", raw_text="DRC에서 에볼라 분디부조형 신규 발생", country_iso3="COD",
    )
    pairs = td.export_extraction_pairs()
    assert len(pairs) == 1
    p = pairs[0]
    assert p["input"] == "DRC에서 에볼라 분디부조형 신규 발생"
    assert p["output"]["disease"] == "에볼라"
    assert p["output"]["country_iso3"] == "COD"
    assert p["output"]["severity"] == ["high"]          # JSON 문자열 → 리스트 파싱
    assert p["label_quality"] == "silver_llm_distillation"  # 사람 검증 전


def test_empty_label_pair_excluded(isolated_db):
    """disease·signal_type·country_iso3가 전부 비면 학습쌍으로 부적합 — 제외(안 지어냄)."""
    import db as dbmod
    dbmod.create_extracted_signal(
        source="x", disease=None, location=None, signal_type=None, severity=[],
        symptom=None, transmission=None, source_trust=0.5, signal_date=None,
        raw_text="의미 없는 텍스트", country_iso3=None,
    )
    assert td.export_extraction_pairs() == []


def test_dataset_stats_counts_and_note(isolated_db):
    import db as dbmod
    for i in range(3):
        dbmod.create_extracted_signal(
            source="who", disease="뎅기열", location="태국", signal_type="급증",
            severity=["medium"], symptom=None, transmission="매개체", source_trust=0.7,
            signal_date="2026-07-01", raw_text=f"태국 뎅기 급증 {i}", country_iso3="THA",
        )
    s = td.dataset_stats()
    assert s["total_pairs"] == 3
    assert s["silver_llm_distillation"] == 3 and s["gold_human_verified"] == 0
    assert s["distinct_diseases"] == 1
    assert "운영=학습데이터" in s["note"] or "학습셋" in s["note"]


def test_to_jsonl_is_line_per_pair(isolated_db):
    import db as dbmod
    dbmod.create_extracted_signal(
        source="who", disease="MERS", location="사우디", signal_type="진행중",
        severity=["high"], symptom=None, transmission=None, source_trust=0.8,
        signal_date="2026-06-01", raw_text="사우디 MERS 진행", country_iso3="SAU",
    )
    jsonl = td.to_jsonl(td.export_extraction_pairs())
    assert len(jsonl.splitlines()) == 1
    import json
    assert json.loads(jsonl)["output"]["disease"] == "MERS"


# ── 교사 모델 분리(NIM 배선 이후) ────────────────────────────────
def _mk(dbmod, raw_text: str, ai_provider):
    dbmod.create_extracted_signal(
        source="who", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date=None, raw_text=raw_text, country_iso3="COD",
        ai_provider=ai_provider,
    )


def test_pair_carries_teacher(isolated_db):
    """어느 모델이 만든 라벨인지 학습쌍에 붙어 나와야 한다."""
    _mk(isolated_db, "NIM이 뽑은 것", "nvidia_nim_hosted")
    p = td.export_extraction_pairs()[0]
    assert p["teacher"] == "nim_hosted"


def test_legacy_rows_are_unrecorded_not_guessed(isolated_db):
    """ai_provider 기록 이전 행을 'claude'로 단정하지 않는다 — 기억이지 기록이 아니다."""
    _mk(isolated_db, "옛날 것", None)
    assert td.export_extraction_pairs()[0]["teacher"] == td.UNRECORDED_TEACHER


def test_mixed_teachers_raise_a_warning_in_the_payload(isolated_db):
    """★핵심★ 8B NIM 라벨과 Claude 라벨을 한 통에 담고 'Claude 증류'라고 부르면
    학습셋 품질 주장이 거짓이 된다. 섞였다는 사실이 숫자 옆에 실려 나가야 한다."""
    _mk(isolated_db, "클로드 것", "external_llm_fallback")
    _mk(isolated_db, "NIM 것", "nvidia_nim_hosted")
    s = td.dataset_stats()
    assert s["mixed_teachers"] is True
    assert s["teacher_distribution"] == {"claude": 1, "nim_hosted": 1}
    assert "교사 모델이 섞여" in s["teacher_warning"]


def test_single_teacher_has_no_warning(isolated_db):
    _mk(isolated_db, "클로드 것", "external_llm_fallback")
    s = td.dataset_stats()
    assert s["mixed_teachers"] is False
    assert s["teacher_warning"] is None

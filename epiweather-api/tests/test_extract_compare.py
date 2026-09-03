"""추출 모델 비교 — 8B NIM을 켜기로 한 이상, 품질 저하를 숫자로 잡을 장치.

추출은 실패해도 예외가 안 난다. 그럴듯한 JSON이 계속 나오기 때문에 '잘 도는 것
같다'로 몇 주가 지나갈 수 있다(NIM 배선이 정확히 그렇게 끊겨 있었다). 아래
테스트는 비교기가 실제로 차이를 잡아내는지, 그리고 잡아낸 것을 정확도로
과대포장하지 않는지 확인한다.
"""
from __future__ import annotations

from unittest.mock import patch

from algorithms import extract_compare as ec


def _base(**over):
    rec = {
        "source": "who_emro", "disease": "에볼라", "location": "DRC",
        "country_iso3": "COD", "signal_type": "신규발생", "symptom": None,
        "transmission": None, "signal_date": None, "known_disease": True,
        "raw_text": "DRC에서 출혈열 환자 발생", "ai_provider": "external_llm_fallback",
    }
    rec.update(over)
    return rec


# ── 필드 관계 ────────────────────────────────────────────────────
def test_overfill_is_the_failure_we_care_about():
    """기존이 '모른다(null)'로 둔 자리를 후보가 채우는 것 — 작은 모델의 전형적 실패.
    이 태스크에서 채우는 건 대개 지어내는 것이다."""
    assert ec.field_relation(None, "COD") == "overfill"
    assert ec.field_relation("COD", None) == "underfill"
    assert ec.field_relation("COD", "COD") == "agree"
    assert ec.field_relation("COD", "UGA") == "conflict"
    assert ec.field_relation(None, None) == "both_null"


def test_empty_string_counts_as_null():
    """모델마다 '모름'을 null로도 ""로도 낸다 — 표기 차이를 불일치로 세면 안 된다."""
    assert ec.field_relation(None, "") == "both_null"
    assert ec.field_relation("", "  ") == "both_null"


# ── 규칙 위반(사람 없이 판정 가능한 것만) ────────────────────────
def test_date_invented_when_text_has_no_year():
    """★핵심★ 프롬프트가 "연도 없이 나오면 절대 추측하지 말고 null"이라고 못박은
    지점. 원문에 연도가 없는데 날짜를 채웠으면 지어낸 것이다."""
    v = ec.rule_violations({"signal_date": "2026-05-15"}, {}, "지난달 발열 환자 12명")
    assert "date_invented" in v


def test_date_not_flagged_when_year_present_in_text():
    v = ec.rule_violations({"signal_date": "2026-05-15"}, {},
                           "2026년 5월 15일 DRC에서 발생")
    assert "date_invented" not in v


def test_null_date_is_never_a_violation():
    assert ec.rule_violations({"signal_date": None}, {}, "지난달 발열") == []


def test_schema_coercions_are_counted_as_violations():
    """방어 로직이 조용히 고쳐주는 바람에 '몇 번 어겼나'가 지워지던 자리."""
    notes = {"signal_type_coerced": True, "country_iso3_dropped": True}
    v = ec.rule_violations({"signal_date": None}, notes, "원문")
    assert "signal_type_invalid" in v and "country_iso3_malformed" in v


def test_parse_failure_counted():
    v = ec.rule_violations(None, {"json_parse_failed": True}, "원문")
    assert v == ["json_parse_failed"]


# ── 집계 ─────────────────────────────────────────────────────────
def test_summary_counts_overfill_and_violations():
    baseline = _base(country_iso3=None, signal_date=None)
    candidate = {**baseline, "country_iso3": "COD", "signal_date": "2026-05-15"}
    comps = [ec.compare_one("연도 없는 원문", baseline, candidate, {})]
    s = ec.summarize(comps)

    assert s["pairs_compared"] == 1
    assert s["field_relations"]["country_iso3"]["overfill"] == 1
    assert s["overfill_total"] == 2                 # country_iso3 + signal_date
    assert s["rule_violations"]["date_invented"] == 1


def test_summary_refuses_to_call_itself_accuracy():
    """기존 라벨은 검증된 정답이 아니다. 이 표가 '정확도'로 인용되면 안 된다."""
    s = ec.summarize([ec.compare_one("원문", _base(), _base(), {})])
    assert "agreement_where_baseline_filled" in s
    assert "accuracy" not in s
    assert "정답이 아니다" in s["not_an_accuracy_measure"]


def test_agreement_is_none_when_baseline_filled_nothing():
    """분모가 0이면 0.0이 아니라 None — 비율을 지어내지 않는다."""
    empty = {f: None for f in ec.COMPARE_FIELDS}
    empty["known_disease"] = None
    s = ec.summarize([ec.compare_one("원문", empty, empty, {})])
    assert s["agreement_where_baseline_filled"] is None


def test_failed_candidate_extraction_is_counted_not_dropped():
    c = ec.compare_one("원문", _base(), None, {"json_parse_failed": True})
    s = ec.summarize([c])
    assert s["candidate_extraction_failures"] == 1
    assert s["field_relations"]["disease"]["underfill"] == 1


# ── 실행 경로 ────────────────────────────────────────────────────
def test_run_comparison_refuses_when_nim_not_configured(isolated_db, monkeypatch):
    """후보 모델이 없으면 빈 표를 그럴듯하게 내놓지 않고 사유를 말한다."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    out = ec.run_comparison()
    assert out["available"] is False
    assert "NIM 미설정" in out["reason"]


def test_run_comparison_pairs_stored_rows_with_nim_output(isolated_db, monkeypatch):
    """★핵심★ 며칠 기다리지 않아도 비교가 된다 — 이미 쌓인 원문에는 기존 라벨이
    붙어 있으니 같은 원문을 후보 모델에 다시 넣으면 짝이 만들어진다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.delenv("AEGIRON_NIM_EXTRACT", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_BASE_URL", raising=False)
    monkeypatch.delenv("AEGIRON_NVIDIA_ONPREM_BASE", raising=False)

    isolated_db.create_extracted_signal(
        source="who_emro", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date=None, raw_text="지난달 DRC에서 출혈열 환자 발생",
        country_iso3=None, ai_provider="external_llm_fallback")

    # 후보(8B)가 연도 없는 원문에 날짜를 만들어 넣고, 국가도 채웠다.
    nim_out = ('{"disease":"에볼라","location":"DRC","country_iso3":"COD",'
               '"signal_type":"신규발생","severity":[],"symptom":null,'
               '"transmission":null,"date":"2026-05-15","known_disease":true}')
    with patch("algorithms.aegiron_model.nim_raw", return_value=nim_out):
        out = ec.run_comparison(limit=10)

    assert out["available"] is True
    assert out["pairs_compared"] == 1
    assert out["rule_violations"]["date_invented"] == 1
    assert out["field_relations"]["country_iso3"]["overfill"] == 1
    assert out["candidate_model"] == "meta/llama-3.1-8b-instruct"


def test_comparison_never_writes_to_extracted_signals(isolated_db, monkeypatch):
    """★회귀★ 측정용 라벨이 운영 신호로 섞이면 무엇이 관측이고 무엇이 실험인지
    영영 못 가린다."""
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.delenv("AEGIRON_NIM_EXTRACT", raising=False)
    isolated_db.create_extracted_signal(
        source="who_emro", disease="에볼라", location="DRC", signal_type="신규발생",
        severity=[], symptom=None, transmission=None, source_trust=0.65,
        signal_date=None, raw_text="원문", country_iso3="COD")
    before = len(isolated_db.list_extracted_signals(limit=100))

    with patch("algorithms.aegiron_model.nim_raw",
               return_value='{"disease":"에볼라","signal_type":"진행중"}'):
        ec.run_comparison(limit=10)

    assert len(isolated_db.list_extracted_signals(limit=100)) == before

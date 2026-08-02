"""보건 보고서 표 → 신호 정규화. 실제 WHO 표 모양으로 결정론적 검증.
지어내지 않는 규칙(헤더 미인식 열 폐기, 질병 추측 금지)을 특히 고정한다."""
from __future__ import annotations

from algorithms import bulletin_signals as bs


# 실측한 WHO AFRO 주간보고서의 두 가지 표 모양
DISEASE_TABLE = [
    ["Event", "Total Cases", "Confirmed cases", "Deaths", "Case Fatality Rate",
     "Case Contacts", "Counties", "Start of reporting period", "WHO Grade"],
    ["Mpox", "1,170", "1,170", "19", "1.6%", "1,376", "39", "31 July 2024", "Protracted 2"],
    ["Cholera", "40", "2", "1", "2.5%", "N/A", "2", "May 2026", "Protracted 3"],
    ["Measles", "480", "85", "5 Suspected", "0.2%", "N/A", "5", "Nov 2025", "Ungraded"],
]
COUNTRY_TABLE = [
    ["Country*", "Cumulative Confirmed", "Recovered", "Confirmed Deaths",
     "Contact Follow-up", "Active health zones"],
    ["DRC", "1,963", "331", "719", "81.5%", "33"],
    ["Uganda", "20", "17", "2", "100%", "0"],
]


def test_disease_table_produces_signals_with_numbers():
    signals = bs.rows_to_signals(DISEASE_TABLE)
    assert len(signals) == 3
    mpox = signals[0]
    assert mpox["disease"] == "Mpox" and mpox["location"] is None
    assert mpox["metrics"]["total_cases"] == 1170
    assert mpox["metrics"]["deaths"] == 19
    assert mpox["metrics"]["cfr"] == 0.016


def test_number_parsing_handles_suffix_text():
    """'5 Suspected' 같은 칸도 숫자를 건져야 한다."""
    signals = bs.rows_to_signals(DISEASE_TABLE)
    measles = [s for s in signals if s["disease"] == "Measles"][0]
    assert measles["metrics"]["deaths"] == 5


def test_na_cells_are_omitted_not_zeroed():
    """N/A를 0으로 바꾸면 '접촉자 0명'이라는 거짓 신호가 된다 — 아예 빼야 한다."""
    signals = bs.rows_to_signals(DISEASE_TABLE)
    cholera = [s for s in signals if s["disease"] == "Cholera"][0]
    assert "contacts" not in cholera["metrics"]


def test_country_table_leaves_disease_none():
    """★핵심★ 국가 축 표엔 질병 열이 없다 — 추측해 채우면 안 된다."""
    signals = bs.rows_to_signals(COUNTRY_TABLE)
    assert len(signals) == 2
    drc = signals[0]
    assert drc["location"] == "DRC" and drc["disease"] is None
    assert drc["metrics"]["confirmed"] == 1963
    assert drc["metrics"]["deaths"] == 719
    assert drc["metrics"]["recovered"] == 331


def test_percent_only_parsed_for_cfr_field():
    """81.5%는 접촉자 추적률이지 치명률이 아니다 — cfr로 잡히면 안 된다."""
    signals = bs.rows_to_signals(COUNTRY_TABLE)
    assert "cfr" not in signals[0]["metrics"]


def test_non_epi_table_yields_nothing():
    rows = [["0 New Events", "0 Ongoing Events", "4 Outbreaks"],
            ["0 Grade 3", "0 Grade 2", "2 Ungraded"]]
    assert bs.rows_to_signals(rows) == []


def test_rows_without_numbers_are_dropped():
    rows = [["Event", "Deaths"], ["Mpox", "N/A"], ["Cholera", "3"]]
    signals = bs.rows_to_signals(rows)
    assert [s["disease"] for s in signals] == ["Cholera"]


def test_numeric_label_row_is_skipped():
    """라벨 칸에 숫자가 오면 표가 밀린 것 — 신호로 만들지 않는다."""
    rows = [["Event", "Deaths"], ["1,170", "19"]]
    assert bs.rows_to_signals(rows) == []


def test_unmapped_columns_are_discarded_not_guessed():
    """헤더를 못 알아본 열은 위치로 추측하지 않고 버려야 한다."""
    rows = [["Event", "Zzz Unknown Column", "Deaths"], ["Mpox", "999", "19"]]
    metrics = bs.rows_to_signals(rows)[0]["metrics"]
    assert metrics == {"deaths": 19}       # 999는 버려짐


# ── 전체 파이프라인 ───────────────────────────────────────────────
def _parsed(tables: list[list[list[str]]], cross=None) -> dict:
    return {"ok": True, "pages": [{"page": 1, "ok": True, "table_count": len(tables),
                                   "tables": [{"rows": t, "cross_check": cross} for t in tables]}]}


def test_extract_signals_collects_across_tables():
    out = bs.extract_signals(_parsed([DISEASE_TABLE, COUNTRY_TABLE]))
    assert out["ok"] is True
    assert out["signal_count"] == 5 and out["epi_tables"] == 2
    assert all(s["page"] == 1 for s in out["signals"])


def test_extract_signals_tracks_unverified_tables():
    """교차검증에서 원문에 없던 숫자가 나온 표는 추적 가능해야 한다."""
    out = bs.extract_signals(_parsed([DISEASE_TABLE],
                                     cross={"checked": True, "numbers_unverified": 2}))
    assert out["signals_from_unverified_tables"] == 3


def test_extract_signals_propagates_failure():
    out = bs.extract_signals({"ok": False, "reason": "NVIDIA_API_KEY 없음"})
    assert out["ok"] is False and out["signals"] == []


def test_extract_signals_marks_machine_extracted():
    out = bs.extract_signals(_parsed([DISEASE_TABLE]))
    assert out["is_machine_extracted"] is True
    assert all(s["is_machine_extracted"] for s in out["signals"])


# ── WHO AFRO 감시 이벤트 표(헤더 없는 고정 레이아웃) ──────────────
# 실측 행(OEW12 10~13페이지). VLM이 큰 표를 조각내 헤더 없이 내보낸다.
AFRO_ROWS = [
    ["Guinea", "Lassa fever", "Ungraded", "10-Mar-26", "10-Mar-26", "22-Mar-26", "1", "1", "1", "100.00%"],
    ["Guinea", "Diphtheria", "Grade 2", "4-Jul-25", "1-Jan-25", "22-Mar-26", "873", "50", "158", "18.10%"],
    ["Kenya", "Mpox", "Protracted 2", "3-Aug-24", "31-Jul-24", "22-Mar-26", "1 087", "1 087", "19", "0.70%"],
    ["Kenya", "Measles", "Ungraded", "29-Jun-22", "1-Jan-26", "22-Mar-26", "364", "24", "", "0", "0.00%"],
]


def test_afro_layout_extracts_country_disease_and_metrics():
    signals = bs.rows_to_signals(AFRO_ROWS)
    assert len(signals) == 4
    lassa = signals[0]
    assert lassa["location"] == "Guinea" and lassa["disease"] == "Lassa fever"
    assert lassa["metrics"] == {"total_cases": 1, "cfr": 1.0, "deaths": 1}
    assert lassa["layout"] == "who_afro_events"


def test_afro_layout_handles_space_thousands_separator():
    """★핵심★ WHO는 천 단위에 공백을 쓴다 — '1 087'을 1로 읽으면 신호가 망가진다."""
    kenya = [s for s in bs.rows_to_signals(AFRO_ROWS) if s["disease"] == "Mpox"][0]
    assert kenya["metrics"]["total_cases"] == 1087
    assert kenya["metrics"]["deaths"] == 19


def test_afro_layout_handles_ragged_blank_columns():
    """빈 칸이 섞여 열이 밀려도 치명률을 기준으로 사망자를 제대로 잡아야 한다."""
    measles = [s for s in bs.rows_to_signals(AFRO_ROWS) if s["disease"] == "Measles"][0]
    assert measles["metrics"]["total_cases"] == 364
    assert measles["metrics"]["deaths"] == 0 and measles["metrics"]["cfr"] == 0.0


def test_afro_layout_omits_deaths_when_no_cfr_column():
    """사이클론 같은 비질병 이벤트는 치명률 칸이 없다 — 사망 위치가 모호하므로
    추측해 넣지 않는다(가짜 사망자 방지)."""
    row = [["Madagascar", "Cyclone Gezani", "Grade 2", "10-Feb-26", "10-Feb-26",
            "22-Mar-26", "430 000", "-", "62", "-"]]
    sig = bs.rows_to_signals(row)[0]
    assert sig["metrics"]["total_cases"] == 430000
    assert "deaths" not in sig["metrics"] and "cfr" not in sig["metrics"]


def test_afro_layout_rejects_rows_without_grade_signature():
    """등급 열이 없으면 이 레이아웃이 아니다 — 아무 표나 억지로 읽지 않는다."""
    assert bs.rows_to_signals([["Kenya", "Mpox", "아무거나", "a", "b", "c", "1", "2", "3", "4%"]]) == []


def test_afro_layout_rejects_numeric_country():
    assert bs.parse_afro_event_row(
        ["1 087", "Mpox", "Ungraded", "a", "b", "c", "1", "1", "1", "1%"]) is None


def test_afro_layout_requires_minimum_columns():
    assert bs.parse_afro_event_row(["Kenya", "Mpox", "Ungraded", "a", "b"]) is None


def test_afro_layout_flattens_wrapped_labels():
    """★회귀★ 표 셀은 폭에 맞춰 줄바꿈돼 온다 — 그대로 두면 질병명이
    "Impact of Sudan\ncris"처럼 쪼개져 하류 질병 매칭이 깨진다."""
    row = [["Chad", "Impact of Sudan\ncrisis", "Grade 3", "15-Apr-23", "15-Apr-23",
            "15-Feb-25", "918 000", "-", "-", "-"]]
    sig = bs.rows_to_signals(row)[0]
    assert sig["disease"] == "Impact of Sudan crisis"
    assert sig["metrics"]["total_cases"] == 918000


# ── 섹션 제목에서 병명 보강 ────────────────────────────────────────
BVD_HEADER = "## Bundibugyo Virus Disease (BVD) outbreak in the Democratic Republic of Congo and Uganda"


def test_disease_from_header_finds_known_disease():
    assert bs.disease_from_header(BVD_HEADER) == "Bundibugyo"
    assert bs.disease_from_header("Cholera situation update") == "Cholera"


def test_disease_from_header_ignores_unrelated_titles():
    """아무 제목이나 병명으로 삼으면 신호가 오염된다 — 사전에 있을 때만."""
    assert bs.disease_from_header("Summary of Ongoing Public Health Emergencies") is None
    assert bs.disease_from_header(None) is None


def test_country_table_gets_disease_from_section_header():
    """★핵심 회귀★ 국가 축 표는 병명이 표에 없고 위쪽 제목에만 있다. 이걸 못
    물려주면 DRC 719사망을 잡고도 무슨 병인지 몰라 질병별 경보가 안 뜬다
    (실제 WHO 28주차 분디부조 표에서 확인된 문제)."""
    signals = bs.rows_to_signals(COUNTRY_TABLE, context_header=BVD_HEADER)
    drc = signals[0]
    assert drc["location"] == "DRC"
    assert drc["disease"] == "Bundibugyo"
    assert drc["disease_source"] == "section_header"   # 어디서 온 이름인지 투명하게
    assert drc["metrics"]["deaths"] == 719


def test_table_column_disease_wins_over_header():
    """표에 병명 열이 있으면 그게 우선 — 제목으로 덮어쓰면 안 된다."""
    signals = bs.rows_to_signals(DISEASE_TABLE, context_header=BVD_HEADER)
    assert signals[0]["disease"] == "Mpox"
    assert signals[0]["disease_source"] == "table_column"


def test_country_table_without_header_still_leaves_disease_none():
    """제목이 없으면 여전히 비운다 — 추측 금지 원칙은 그대로."""
    signals = bs.rows_to_signals(COUNTRY_TABLE)
    assert signals[0]["disease"] is None and signals[0]["disease_source"] is None


def test_extract_signals_passes_context_header_through():
    parsed = {"ok": True, "pages": [{"page": 2, "ok": True, "table_count": 1, "tables": [
        {"rows": COUNTRY_TABLE, "cross_check": None, "context_header": BVD_HEADER}]}]}
    out = bs.extract_signals(parsed)
    assert out["signals"][0]["disease"] == "Bundibugyo"


def test_disease_header_found_by_looking_back_past_intervening_header():
    """★핵심 회귀★ 병명 제목과 표 사이에 다른 소제목이 끼어드는 실제 사례
    (BVD 제목 → "Kenya Preparedness and Readiness Actions" → 표). 바로 앞
    제목만 보면 분디부조를 놓쳐 719사망이 '미상'으로 남는다."""
    signals = bs.rows_to_signals(
        COUNTRY_TABLE,
        context_header="### Kenya Preparedness and Readiness Actions",
        context_headers=["## Overview", BVD_HEADER, "### Kenya Preparedness and Readiness Actions"])
    assert signals[0]["disease"] == "Bundibugyo"
    assert signals[0]["disease_source"] == "section_header"


def test_lookback_stops_when_no_disease_anywhere():
    signals = bs.rows_to_signals(COUNTRY_TABLE, context_header="### Actions",
                                 context_headers=["## Overview", "### Actions"])
    assert signals[0]["disease"] is None


def test_percent_cell_not_stored_as_count():
    """★회귀★ 'Contact Follow-up 81.5%'가 contacts=81.5(명)로 저장돼 접촉자
    81.5명처럼 읽히던 문제. 퍼센트 칸은 개수로 취하지 않는다."""
    signals = bs.rows_to_signals(COUNTRY_TABLE)
    drc = signals[0]
    assert "contacts" not in drc["metrics"]
    assert drc["metrics"]["confirmed"] == 1963 and drc["metrics"]["deaths"] == 719


def test_location_from_header_for_disease_axis_table():
    """질병 축 표엔 국가 열이 없다 — 국가별 보고서라 제목에만 있다."""
    header = "Summary of Ongoing Public Health Emergencies in Kenya, June 2026"
    signals = bs.rows_to_signals(DISEASE_TABLE, context_header=header)
    assert signals[0]["location"] == "Kenya"
    assert signals[0]["location_source"] == "section_header"


def test_table_column_location_wins_over_header():
    signals = bs.rows_to_signals(COUNTRY_TABLE, context_header="... in Kenya ...")
    assert signals[0]["location"] == "DRC"
    assert signals[0]["location_source"] == "table_column"


def test_location_stays_none_without_known_country_in_header():
    signals = bs.rows_to_signals(DISEASE_TABLE, context_header="Summary of ongoing events")
    assert signals[0]["location"] is None and signals[0]["location_source"] is None


# ── VLM 오독 병명 정규화 ──────────────────────────────────────────
def test_normalize_disease_fixes_observed_misreads():
    """★회귀★ 같은 페이지를 두 번 돌리면 결과가 흔들린다(실측: Cholera→Colera,
    Mpox→Mpx). 한 글자 틀리면 하류 질병 매칭이 통째로 안 걸린다."""
    assert bs.normalize_disease("Colera") == ("Cholera", "Colera")
    assert bs.normalize_disease("Mpx") == ("Mpox", "Mpx")


def test_normalize_disease_leaves_correct_names_untouched():
    assert bs.normalize_disease("Cholera") == ("Cholera", None)
    assert bs.normalize_disease("Lassa fever") == ("Lassa fever", None)
    assert bs.normalize_disease("Poliomyelitis (cVDPV2)") == ("Poliomyelitis (cVDPV2)", None)


def test_normalize_disease_does_not_overcorrect_unknown_labels():
    """모르는 라벨을 억지로 병명에 끼워맞추면 안 된다."""
    for label in ("Cyclone Gezani", "Complex Humanitarian crisis", "Landslide"):
        name, raw = bs.normalize_disease(label)
        assert name == label and raw is None


def test_normalized_disease_keeps_original_in_signal():
    """교정했으면 원본을 남겨 사람이 대조할 수 있어야 한다."""
    rows = [["Event", "Deaths"], ["Colera", "3"]]
    sig = bs.rows_to_signals(rows)[0]
    assert sig["disease"] == "Cholera" and sig["disease_raw"] == "Colera"


# ── 누적 vs 신규 열 구분 (실제 상황보고서 표) ─────────────────────
_BS = chr(92)   # 역슬래시 리터럴 — 소스에 직접 쓰면 따옴표를 이스케이프해버린다
SITREP_HEADER = ['Country', 'New Confirmed Cases (Last 7 days)',
                 'New Confirmed Deaths (Last 7 days)', 'Confirmed Cases (total)',
                 'Confirmed Deaths (total)', 'Probable Cases', 'Probable Deaths',
                 '**Total Cases (Confirmed ' + _BS, 'Probable)**',
                 '**Total Deaths (Confirmed ' + _BS, 'Probable)**',
                 '**CFR (%) Confirmed ' + _BS, 'Probable**']
SITREP_ROW = ['Democratic Republic of the Congo', '567', '296', '3 262', '1 437',
              '-', '-', '3 262', '1 437', '44.1%']


def test_wrapped_header_cells_are_merged():
    """★회귀★ 헤더가 줄바꿈으로 쪼개져 13칸인데 데이터는 10칸이었다 — 위치 정렬이
    통째로 깨진다."""
    merged = bs.merge_wrapped_header(SITREP_HEADER)
    assert len(merged) == len(SITREP_ROW) == 10
    assert merged[7] == "**Total Cases (Confirmed Probable)**"


def test_cumulative_column_preferred_over_recent():
    """★핵심 회귀★ '최근 7일 신규 사망 296'을 누적 사망으로 보고하던 문제.
    실제 누적은 1,437 — 5배 축소였다."""
    sig = bs.rows_to_signals([SITREP_HEADER, SITREP_ROW])[0]
    assert sig["metrics"]["deaths"] == 1437
    assert sig["metrics"]["confirmed"] == 3262
    assert sig["metrics"]["cfr"] == 0.441


def test_recent_columns_kept_separately_not_discarded():
    """주간 신규는 그 자체로 좋은 조기경보 신호 — 버리지 말고 따로 담는다."""
    sig = bs.rows_to_signals([SITREP_HEADER, SITREP_ROW])[0]
    assert sig["metrics"]["new_deaths"] == 296
    assert sig["metrics"]["new_confirmed"] == 567


def test_probable_column_does_not_become_total():
    """'Probable Cases'가 total_cases로 잡히면 추정 환자를 확진 총계로 보고하게 된다."""
    header = ["Country", "Probable Cases", "Confirmed Deaths (total)"]
    row = ["Uganda", "88", "2"]
    sig = bs.rows_to_signals([header, row])[0]
    assert sig["metrics"].get("probable_total_cases") == 88
    assert "total_cases" not in sig["metrics"]
    assert sig["metrics"]["deaths"] == 2


def test_combined_confirmed_plus_probable_is_not_treated_as_probable_only():
    """★회귀★ 'CFR (%) Confirmed + Probable'은 합산 열이지 추정 전용이 아니다 —
    추정으로 밀어내면 정상 CFR을 통째로 잃는다."""
    assert bs._column_priority("**CFR (%) Confirmed Probable**") == 0
    assert bs._column_priority("Probable Cases") == 3


def test_summary_total_row_is_not_a_location():
    """★회귀★ 표 합계 행이 국가로 잡혀 'Total'이라는 나라가 생겼다 —
    추이 분석에 유령 지역이 끼어든다(실제 상황보고서 적재에서 발생)."""
    rows = [["Country", "Confirmed Cases (total)", "Confirmed Deaths (total)"],
            ["DRC", "3 262", "1 437"],
            ["Total", "3 283", "1 439"]]
    got = bs.rows_to_signals(rows)
    assert [s["location"] for s in got] == ["DRC"]


def test_summary_label_variants_are_excluded():
    for label in ("Total", "TOTAL", "Grand Total", "Sub-total", "합계"):
        rows = [["Country", "Deaths"], [label, "5"]]
        assert bs.rows_to_signals(rows) == []

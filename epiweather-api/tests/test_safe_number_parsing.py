"""외부 데이터 숫자 파싱 전수점검 회귀 (2026-08-18).

2026-08-13 KDCA 사고의 진짜 원인은 쉼표가 아니라 **항목 하나의 실패가 배치 전체를
죽이는 구조**였다. 전수점검에서 같은 구조를 baseline_collector(기준선)와
behavioral_data(서울 응급실)에서도 찾았다. 기준선 쪽이 특히 위험한데, 조용히 짧은
목록을 돌려주면 이상 탐지가 틀린 기준과 비교하면서도 아무 에러를 안 내기 때문이다.

여기 테스트는 '한 항목이 깨져도 나머지가 살아남는지'를 고정한다."""
from __future__ import annotations
from unittest.mock import patch

from algorithms import baseline_collector as bc
from algorithms.common import safe_float, safe_int
from algorithms.kdca_anomaly import parse_kdca_count


def test_safe_int_absorbs_every_shape_the_real_apis_send():
    assert safe_int("1,296") == 1296          # KDCA가 실제로 보낸 값
    assert safe_int("12,345.6") == 12345
    assert safe_int("  42 ") == 42
    assert safe_int(7) == 7 and safe_int(2.9) == 2
    for missing in ("-", "", "   ", None, "미상", True):
        assert safe_int(missing) is None      # 0이 아니라 None


def test_safe_int_default_is_opt_in():
    """못 읽은 값을 0으로 적으면 없는 안전을 지어내는 것 — 호출측이 명시할 때만 0."""
    assert safe_int("-") is None
    assert safe_int("-", 0) == 0


def test_safe_float_keeps_precision_and_absorbs_commas():
    assert safe_float("1,234.5") == 1234.5
    assert safe_float(3) == 3.0
    for missing in ("-", "", None, "미상", False):
        assert safe_float(missing) is None


def test_parse_kdca_count_still_behaves_after_unification():
    """공용 파서로 통일했어도 KDCA 의미(0건 vs 못 읽음)는 그대로여야 한다."""
    assert parse_kdca_count("1,296") == 1296
    assert parse_kdca_count("0") == 0          # 0건 신고는 진짜 데이터
    assert parse_kdca_count("-") is None       # 못 읽음


def test_nwss_baseline_survives_one_broken_month():
    """★핵심★ 한 달치가 깨져도 24개월 기준선이 통째로 사라지면 안 된다."""
    rows = [
        {"month": "2026-06-01T00:00:00", "n": "1,296", "avg_conc": "5,000.5"},
        {"month": "2026-07-01T00:00:00", "n": "-", "avg_conc": None},
        {"month": "2026-08-01T00:00:00", "n": "812", "avg_conc": "4321.0"},
    ]
    with patch.object(bc, "fetch_cdc_nwss_historical", return_value=rows):
        records = bc.build_cdc_nwss_records()

    assert len(records) == 3                                   # 깨진 달도 레코드는 남는다
    assert records[0]["cdc_nwss"]["site_count"] == 1296         # 쉼표 정상 파싱
    assert records[0]["cdc_nwss"]["mean_concentration"] == 5000.5
    assert records[1]["cdc_nwss"]["site_count"] is None          # 못 읽은 건 None(0 아님)
    assert records[2]["cdc_nwss"]["site_count"] == 812           # 뒤 항목이 유실되지 않음


def test_wiki_baseline_skips_only_the_broken_month():
    rows = [
        {"timestamp": "20260601000000", "views": 3000},
        {"timestamp": "20260701000000", "views": "알수없음"},
        {"timestamp": "20260801000000", "views": "1,500"},
    ]
    with patch.object(bc, "fetch_wiki_monthly", return_value=rows), \
         patch.object(bc, "WIKI_DISEASES", {"Ebola": "wiki_ebola_daily"}):
        records = bc.build_wiki_records()

    dailies = [r["wiki_ebola_daily"] for r in records]
    assert dailies == [100.0, 50.0]        # 깨진 달만 빠지고 나머지는 살아남음


def test_infodengue_baseline_skips_non_numeric_week():
    rows = [
        {"label": "상파울루", "week": "202630", "casos": 10},
        {"label": "상파울루", "week": "2026-1", "casos": 20},   # 길이는 6, 숫자가 아님
    ]
    with patch.object(bc, "fetch_infodengue_historical", return_value=rows):
        records = bc.build_infodengue_records()

    assert len(records) == 1               # 예전엔 여기서 터져 104주치가 전부 사라졌다

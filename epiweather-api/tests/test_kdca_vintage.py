"""질병청 주간 값 성숙도 측정 — 한국 주간 예측(⑥)의 1단계 (2026-10-19).

고정하는 것: ① 값이 바뀐 순간만 남긴다 ② 성숙 판정은 MATURE_DAYS 지난 주만 ③ 처음·7일·14일
시점 합계를 마지막 값으로 나눈다(위험군만) ④ 합계 0 인 주는 비율을 내지 않는다
⑤ 판정 가능한 주가 없으면 '측정 중' ⑥ 수집기가 실제로 부른다.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib

from algorithms import kdca_vintage as kv

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 1, 1, tzinfo=UTC)
COLLECTOR_PY = pathlib.Path(__file__).resolve().parents[1] / "collector.py"
NOTABLE = {"레지오넬라증", "홍역"}


def test_only_changes_are_recorded(isolated_db):
    assert kv.record({"레지오넬라증": {"2026년 36주": 3}}, T0) == 1
    assert kv.record({"레지오넬라증": {"2026년 36주": 3}}, T0 + dt.timedelta(hours=1)) == 0
    assert kv.record({"레지오넬라증": {"2026년 36주": 5}, "홍역": {"2026년 36주": None}},
                     T0 + dt.timedelta(days=2)) == 1
    assert kv.record(None, T0) == 0


def test_maturity_ratios_at_first_seen_7_and_14_days(isolated_db):
    week = "2026년 36주"
    kv.record({"레지오넬라증": {week: 4}, "홍역": {week: 0}, "결핵": {week: 100}}, T0)       # 결핵은 위험군 아님(이 시험에서)
    kv.record({"레지오넬라증": {week: 6}, "홍역": {week: 1}}, T0 + dt.timedelta(days=3))
    kv.record({"레지오넬라증": {week: 8}, "홍역": {week: 2}}, T0 + dt.timedelta(days=10))
    kv.record({"레지오넬라증": {week: 8}, "홍역": {week: 2}}, T0 + dt.timedelta(days=20))   # 변화 없음
    rep = kv.maturity_report(T0 + dt.timedelta(days=30), notable=NOTABLE)
    assert rep["mature_periods"] == [week]
    assert rep["median_ratio"] == {0: 0.4, 7: 0.7, 14: 1.0}      # 4/10 · 7/10 · 10/10
    line = kv.report_line(rep)
    assert "성숙 판정 1주" in line and "40%" in line and "70%" in line and "100%" in line
    assert "수집 창(최근 4주) 밖 변동은 못 봄" in line


def test_young_weeks_and_zero_totals_are_not_judged(isolated_db):
    kv.record({"레지오넬라증": {"2026년 40주": 2}}, T0 + dt.timedelta(days=25))
    kv.record({"홍역": {"2026년 36주": 0}}, T0)
    rep = kv.maturity_report(T0 + dt.timedelta(days=30), notable=NOTABLE)
    assert rep["mature_periods"] == [] and rep["young_periods"] == 1 and rep["zero_total_periods"] == 1
    assert rep["median_ratio"][0] is None
    assert "측정 중" in kv.report_line(rep)


def test_collector_records_vintages_inside_the_kdca_block():
    tree = ast.parse(COLLECTOR_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    names = {c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert {"record", "maturity_report", "report_line"} <= names

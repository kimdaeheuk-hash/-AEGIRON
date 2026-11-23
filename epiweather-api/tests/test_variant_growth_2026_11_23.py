"""헤임달 성장 신호 — '커지고 있는 계통' (2026-11-23).

계산(구성비 로그 변화/주) · 문턱 미달은 판정 안 함 · 소표본 계통 제외 · 로그 줄 · API 저장본 ·
수집 주기 배선을 네트워크 없이 고정한다.
"""
from __future__ import annotations

import ast
import datetime as dt
import math
import pathlib

from fastapi.testclient import TestClient

from algorithms import genomic_variants as gv
from algorithms import response_cache

TODAY = dt.date(2026, 11, 23)


def _num_date(days_ago: float) -> float:
    d = TODAY - dt.timedelta(days=days_ago)
    y0 = dt.date(d.year, 1, 1)
    return d.year + (d - y0).days / (dt.date(d.year + 1, 1, 1) - y0).days


def _tips(prior: dict[str, int], recent: dict[str, int]) -> list[tuple[str, float]]:
    out = []
    for clade, n in prior.items():
        out += [(clade, _num_date(40))] * n          # 직전 구간(28~56일 전)
    for clade, n in recent.items():
        out += [(clade, _num_date(10))] * n          # 최근 구간(0~28일 전)
    return out


def test_growing_clade_gets_weekly_rate_and_doubling_days():
    tips = _tips({"A": 90, "B": 10}, {"A": 70, "B": 30})
    g = gv.growth_signal(tips, today=TODAY)
    assert g["determined"] is True and g["n_recent"] == 100 and g["n_prior"] == 100
    assert [r["clade"] for r in g["growing"]] == ["B"]            # A 는 줄었으니 목록에 없다
    b = g["growing"][0]
    expected = math.log(0.30 / (10.5 / 100.5)) / 4
    assert b["weekly_growth"] == round(expected, 3)
    assert b["share_recent"] == 0.3 and b["share_prior"] == 0.1
    assert b["share_doubling_days"] == round(math.log(2) / expected * 7, 1)
    assert b["new_in_window"] is False


def test_new_clade_uses_pseudocount_and_is_marked_new():
    tips = _tips({"A": 100}, {"A": 80, "N": 20})
    g = gv.growth_signal(tips, today=TODAY)
    n = g["growing"][0]
    assert n["clade"] == "N" and n["new_in_window"] is True and n["prior_count"] == 0


def test_small_samples_are_undetermined_not_empty():
    g = gv.growth_signal(_tips({"A": 30}, {"A": 20, "B": 20}), today=TODAY)
    assert g["determined"] is False and g["growing"] == []
    assert "표본 부족" in g["reason"]


def test_tiny_clades_are_not_listed():
    g = gv.growth_signal(_tips({"A": 100}, {"A": 95, "C": 5}), today=TODAY)
    assert g["determined"] is True and g["growing"] == []         # C 는 5건 — 소표본 튐


def test_growth_line_three_states():
    ok = {"label": "SARS-CoV-2", "growth": gv.growth_signal(_tips({"A": 90, "B": 10}, {"A": 70, "B": 30}),
                                                              today=TODAY)}
    assert gv.growth_line(ok).startswith("📈 성장 신호 SARS-CoV-2: B 주당 +")
    none = {"label": "X", "growth": gv.growth_signal(_tips({"A": 100}, {"A": 100}), today=TODAY)}
    assert "커지는 계통 없음" in gv.growth_line(none)
    und = {"label": "Y", "growth": gv.growth_signal([], today=TODAY)}
    assert "판정 안 함" in gv.growth_line(und)


def test_snapshot_keeps_failed_builds_visible():
    snap = gv.growth_snapshot({
        "ok": {"available": True, "label": "A", "growth": {"determined": True, "growing": []}},
        "bad": {"available": False, "label": "B", "reason": "Nextstrain API 응답 실패"},
    })
    by = {b["build"]: b for b in snap["builds"]}
    assert by["bad"]["determined"] is False and "응답 실패" in by["bad"]["reason"]
    assert by["ok"]["determined"] is True


def test_api_without_snapshot_is_undetermined_then_serves_snapshot():
    import main
    client = TestClient(main.app)
    response_cache.clear()
    body = client.get("/api/variant-growth").json()
    assert body["determined"] is False and body["builds"] == []
    response_cache.put(gv.GROWTH_CACHE_KEY, {"computed_at": "2026-11-23T00:00:00+00:00",
                                             "builds": [{"build": "x", "growing": []}]})
    body = client.get("/api/variant-growth").json()
    assert body["determined"] is True and body["builds"][0]["build"] == "x"


def test_collector_puts_growth_snapshot():
    src = (pathlib.Path(__file__).resolve().parents[1] / "collector.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "collect_free_sources")
    calls = {ast.unparse(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)}
    assert "response_cache.put" in calls and "growth_snapshot" in calls and "growth_line" in calls

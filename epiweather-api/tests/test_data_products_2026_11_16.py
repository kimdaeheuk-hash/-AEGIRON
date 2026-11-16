"""판매 준비 — 보유량 집계 · 카탈로그 · 상업 조건별 내보내기 · 실적표 · 배선 (2026-11-16)."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algorithms import data_inventory, data_products, track_record

MAIN = Path(__file__).resolve().parents[1] / "main.py"


@pytest.fixture
def seeded(isolated_db, tmp_path, monkeypatch):
    db = isolated_db
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO alerts (alert_date, source, tier, label, score, evidence, suppressed, created_at, updated_at) "
            "VALUES ('2099-01-01','gai:x','high','X',85,'[\"관측값 3\"]',0,'2099-01-01T00:00','2099-01-01T00:00')")
        conn.execute(
            "INSERT INTO extracted_signals (extracted_at, source, disease, location, signal_type, severity, "
            "source_trust, raw_text, country_iso3) VALUES ('2099-01-01T01:00','who_don','콜레라','킨샤사','급증',"
            "'[]',0.9,'원문 기사 전문 — 내보내면 안 됨','COD')")
        for layer in ("climate", "travel", "trade"):
            conn.execute(
                "INSERT INTO observations (layer, target, metric, status, measured, derived, source, value_hash, "
                "observed_at, confirmed_at) VALUES (?, 'KOR', '', 'ok', '{\"v\": 1}', '{\"d\": 2}', 's', 'h', "
                "'2099-01-01T00:00', '2099-01-01T00:00')", (layer,))
    monkeypatch.setattr(data_inventory, "DATA_DIR", tmp_path)
    (tmp_path / "signals_log.jsonl").write_text(
        json.dumps({"type": "free_sources", "timestamp": "2099-01-01T00:00:00"}) + "\n"
        + json.dumps({"type": "free_sources", "timestamp": "2099-01-02T00:00:00"}) + "\n", encoding="utf-8")
    # 표본은 '최근 7일' 이라 미래 날짜는 기간 안에 든다
    return db


def test_inventory_counts_tables_and_files_directly(seeded):
    inv = data_inventory.compute()
    a = inv["tables"]["alerts"]
    assert a["rows"] == 1 and a["first"] == "2099-01-01" and a["days"] == 1
    assert inv["tables"]["observations"]["rows"] == 3
    f = inv["files"]["signals_log.jsonl"]
    assert f["lines"] == 2 and f["first"].startswith("2099-01-01") and f["last"].startswith("2099-01-02")
    assert inv["files"]["baseline_signals.jsonl"] == {"label": data_inventory.FILES["baseline_signals.jsonl"],
                                                       "exists": False, "lines": 0}
    # 내부 호출 기록은 세지 않는다
    assert "api_key_usage" not in inv["tables"]
    line = data_inventory.summary_line(inv)
    assert line.startswith("📦 데이터 보유량") and "alerts 1행" in line and "signals_log 2줄" in line


def test_inventory_marks_unreadable_table_not_zero(seeded, monkeypatch):
    monkeypatch.setitem(data_inventory.TABLES, "no_such_table", ("t", "없는 표"))
    inv = data_inventory.compute()
    t = inv["tables"]["no_such_table"]
    assert t["rows"] is None and "error" in t
    assert "no_such_table" not in data_inventory.summary_line(inv) or "판정 안 함" in data_inventory.summary_line(inv)


def test_catalog_states_and_open_meteo_blocked():
    cat = data_products.catalog(None)
    by = {d["id"]: d for d in cat["datasets"]}
    assert set(by) == set(data_products.DATASETS)
    layers = {lay["layer"]: lay["license"] for lay in by["observations"]["layers"]}
    # 무료 API 는 비상업 전용 → 막힘. 무역은 Comtrade 재배포 제한 → 막힘
    assert layers["climate"] == layers["polar"] == layers["trade"] == "blocked"
    assert layers["travel"] == "allowed"
    assert by["predictions"]["license"] == "allowed"
    assert cat["pricing"].startswith("미정")


def test_sample_excludes_blocked_layers_and_raw_text(seeded):
    r = data_products.export_rows("observations", paid=False)
    got = {row["layer"] for row in r["rows"]}
    assert got == {"travel"}  # climate·trade 는 blocked
    assert any(e.startswith("observations/climate: blocked") for e in r["excluded"])
    assert r["row_cap"] == data_products.SAMPLE_ROWS
    o = data_products.export_rows("outbreak_reports", paid=False)
    assert o["count"] == 1 and "raw_text" not in o["rows"][0]


def test_paid_export_only_allowed(seeded):
    # alerts 는 review → 유료 내보내기에서 빠지고 이유가 남는다
    r = data_products.export_rows("alerts", paid=True)
    assert r["rows"] == [] and r["excluded"][0].startswith("alerts: review")
    # 표본에서는 review 도 보인다
    s = data_products.export_rows("alerts", paid=False)
    assert s["count"] == 1 and s["rows"][0]["evidence"] == ["관측값 3"]
    obs = data_products.export_rows("observations", paid=True, since="2098-12-31")
    assert {row["layer"] for row in obs["rows"]} == {"travel"}


def test_csv_serialises_json_columns(seeded):
    csv_text = data_products.to_csv(data_products.export_rows("observations", paid=False))
    header, first = csv_text.splitlines()[:2]
    assert header.startswith("layer,target") and '{""v"": 1}' in first
    empty = data_products.to_csv({"rows": [], "excluded": ["x: blocked"]})
    assert "# excluded: x: blocked" in empty


def test_data_keys_parse(monkeypatch):
    monkeypatch.setenv("EPIWEATHER_DATA_KEYS", "pilot_a:k1, bad ,pilot_b:k2")
    assert data_products.data_keys() == {"k1": "pilot_a", "k2": "pilot_b"}


def test_alerts_by_month(seeded):
    rows = track_record.alerts_by_month()
    assert rows == [{"month": "2099-01", "by_tier": {"high": 1}, "total": 1, "sent": 0, "suppressed": 0}]


def test_routes_and_daily_log_are_wired():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    routes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                    routes.add(dec.args[0].value)
    for r in ("/api/data-inventory", "/api/datasets", "/api/datasets/{dataset_id}/export", "/api/track-record"):
        assert r in routes
    src = MAIN.read_text(encoding="utf-8")
    after = src[src.index("def _after_cycle_bg"):src.index("def _log_inventory_daily")]
    assert "_log_inventory_daily()" in after
    assert "_log_inventory_daily(force=True)" in src

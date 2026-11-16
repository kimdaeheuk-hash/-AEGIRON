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


# ── 정제 상품(가공 2차 데이터) — 캡틴 "원본 그대로 팔라는 얘기가 아니잖아" ──────────────────────
from algorithms import refined_products


@pytest.fixture
def reports(isolated_db):
    db = isolated_db
    rows = [
        # 같은 질병(별칭 다름)·같은 나라·30일 안 → 한 사건, 출처 2곳
        ("2099-03-02T00:00", "who_don", "Cholera", "COD", "신규발생", 0.9, 1),
        ("2099-03-05T00:00", "africa_cdc", "콜레라", "COD", "급증", 0.8, 1),
        # 60일 뒤 → 새 사건
        ("2099-05-10T00:00", "who_don", "콜레라", "COD", "진행중", 0.9, 1),
        # 다른 나라 같은 주
        ("2099-03-03T00:00", "promed", "콜레라", "AGO", "신규발생", 0.6, 0),
        # 국가 미상 → 국가 패널 제외, 질병 패널엔 unlocated
        ("2099-03-04T00:00", "news", "콜레라", None, "불명", 0.5, 1),
    ]
    with db.get_connection() as conn:
        for at, src, dis, iso, typ, tr, known in rows:
            conn.execute(
                "INSERT INTO extracted_signals (extracted_at, source, disease, location, signal_type, severity, "
                "source_trust, raw_text, country_iso3, known_disease) VALUES (?,?,?,?,?,'[]',?,'원문',?,?)",
                (at, src, dis, "x", typ, tr, iso, known))
        conn.execute(
            "INSERT INTO lead_time_ledger (disease, country_iso3, crossed_at, severity, threshold, signal_ids, "
            "declared_on, lead_days, outcome) VALUES ('콜레라','COD','2099-03-02T00:00',0.8,0.5,'[]','2099-03-12',10,'declared')")
        conn.execute("INSERT INTO weekly_reports (week, generated_at, payload) VALUES (?,?,?)",
                     ("2099-W09", "2099-03-02T00:00",
                      json.dumps({"top_exposure": [{"country": "COD", "exposure_index": 33.3, "raw_score": 45.0}]})))
    return db


def test_events_dedupe_normalise_and_split_episodes(reports):
    ev = refined_products.outbreak_events()
    cod = sorted([e for e in ev if e["country_iso3"] == "COD"], key=lambda e: e["first_seen"])
    assert len(cod) == 2  # 공백 60일 → 사건 둘
    first = cod[0]
    assert first["disease"] == "콜레라" and first["report_count"] == 2 and first["source_count"] == 2
    # 확신도 = 1-(1-0.9)×0.5^(2-1) = 0.95
    assert first["confidence"] == 0.95
    assert first["declared_on"] == "2099-03-12" and first["lead_days_vs_declaration"] == 10
    assert first["surge_reports"] == 1 and first["new_reports"] == 1
    assert "raw_text" not in first and first["basis"].startswith("AI 구조화 추출")
    # 국가 미상 보도는 사건에 안 들어감
    assert all(e["country_iso3"] for e in ev)


def test_country_week_panel_ranks_and_joins_exposure(reports):
    rows = {(r["week"], r["country_iso3"]): r for r in refined_products.country_week_panel()}
    cod = rows[("2099-W10", "COD")]
    ago = rows[("2099-W10", "AGO")]
    assert cod["report_count"] == 2 and cod["surge_reports"] == 1 and cod["active_events"] == 1
    assert ago["unexplained_reports"] == 1
    assert cod["activity_percentile"] == 100 and ago["activity_percentile"] == 50
    assert all(k[1] for k in rows)  # 국가 미상 없음
    # 노출 지수는 보고서가 있던 주에만(W09) — W10 은 None(지어내지 않음)
    assert cod["korea_exposure_index"] is None


def test_disease_week_panel_new_countries(reports):
    rows = {(r["week"], r["disease"]): r for r in refined_products.disease_week_panel()}
    w10 = rows[("2099-W10", "콜레라")]
    assert w10["countries_affected"] == 2 and w10["new_countries"] == ["AGO", "COD"]
    assert w10["unlocated_reports"] == 1
    w19 = rows[("2099-W19", "콜레라")]
    assert w19["new_countries"] == []  # COD 는 이미 나왔던 나라


def test_refined_products_are_sold_paid_and_catalogued(reports):
    r = data_products.export_rows("outbreak_events", paid=True)
    assert r["license"] == "derived" and r["count"] == 3 and r["excluded"] == []  # COD 2 + AGO 1
    w = data_products.export_rows("country_week_panel", paid=True, since="2099-03-06")
    assert {x["week"] for x in w["rows"]} >= {"2099-W10"}
    cat = {d["id"]: d for d in data_products.catalog(None)["datasets"]}
    assert cat["outbreak_events"]["license"] == "derived" and cat["outbreak_events"]["coverage"]["rows"] == 3
    assert list(cat)[:3] == ["outbreak_events", "country_week_panel", "disease_week_panel"]


def test_every_table_dataset_columns_exist_in_schema(isolated_db):
    """카탈로그의 칸 이름이 실제 표와 다르면 내보내기가 운영에서 터진다(weekly_reports.report → payload 실수, 2026-11-16)."""
    with isolated_db.get_connection() as conn:
        for ds_id, d in data_products.DATASETS.items():
            if not d.get("table"):
                continue
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({d['table']})").fetchall()}
            missing = set(d["columns"]) - cols
            assert not missing, (ds_id, missing)
            assert d["time_column"] in cols, ds_id

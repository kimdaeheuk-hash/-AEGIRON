"""main.py 라우트 통합테스트 — 지금까지 87개(현재 115개+) 테스트가 전부
algorithms/·db.py 단위테스트였고, 실제 FastAPI 엔드포인트(인증이 진짜로
걸려있는지, 응답 스키마가 맞는지)를 직접 때리는 테스트가 하나도 없었다.
새 POST 엔드포인트를 추가하면서 dependencies=_auth를 빠뜨려도 그동안은
아무 테스트도 잡아주지 못했음 — 이 파일이 그 회귀를 방지한다.

TestClient로 실제 앱 인스턴스를 띄우되, 스케줄러(백그라운드 수집 루프)는
끄고(EPIWEATHER_SCHEDULER=off) DB는 isolated_db로 격리해 운영 데이터에
전혀 영향이 없게 한다."""
from __future__ import annotations
import os
import sqlite3

import pytest

os.environ.setdefault("EPIWEATHER_SCHEDULER", "off")

from fastapi.testclient import TestClient
import main


@pytest.fixture()
def client(isolated_db, monkeypatch):
    monkeypatch.setenv("EPIWEATHER_SCHEDULER", "off")
    monkeypatch.delenv("EPIWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("EPIWEATHER_API_KEYS", raising=False)
    return TestClient(main.app)


@pytest.fixture()
def client_with_key(client, monkeypatch):
    monkeypatch.setenv("EPIWEATHER_API_KEY", "test-key-123")
    return client, "test-key-123"


def test_health_check_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_endpoints_are_public_without_api_key(client):
    """읽기(GET)는 인증 없이 공개돼야 함 — Phase1 설계 원칙."""
    for path in ("/api/risk-index", "/api/status", "/api/threats", "/api/alerts?date=2026-07-21"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 실패: {resp.status_code} {resp.text}"


def test_post_endpoint_fails_closed_when_no_api_key_configured(client):
    """EPIWEATHER_API_KEY(및 EPIWEATHER_API_KEYS) 자체가 서버에 없으면
    503로 막혀야 함(fail-closed) — 키 없이도 조용히 열려버리면(fail-open) 안 됨."""
    resp = client.post("/api/timeline", json={
        "event_id": "t1", "event_name": "테스트", "event_date": "2026-07-21",
        "milestone": "first_report", "description": "d",
    })
    assert resp.status_code == 503


def test_post_endpoint_requires_valid_key_returns_401(client_with_key):
    client, _ = client_with_key
    resp = client.post(
        "/api/timeline",
        headers={"X-API-Key": "wrong-key"},
        json={
            "event_id": "t1", "event_name": "테스트", "event_date": "2026-07-21",
            "milestone": "first_report", "description": "d",
        },
    )
    assert resp.status_code == 401


def test_post_endpoint_missing_key_header_returns_401(client_with_key):
    client, _ = client_with_key
    resp = client.post("/api/timeline", json={
        "event_id": "t1", "event_name": "테스트", "event_date": "2026-07-21",
        "milestone": "first_report", "description": "d",
    })
    assert resp.status_code == 401


def test_post_endpoint_succeeds_with_valid_key(client_with_key):
    client, key = client_with_key
    resp = client.post(
        "/api/timeline",
        headers={"X-API-Key": key},
        json={
            "event_id": "t1", "event_name": "테스트 발병", "event_date": "2026-07-21",
            "milestone": "first_report", "description": "첫 보고",
        },
    )
    assert resp.status_code == 200

    check = client.get("/api/timeline/t1")
    assert check.status_code == 200
    assert check.json()["milestones"][0]["milestone"] == "first_report"


def test_risk_index_unknown_country_returns_404(client):
    resp = client.get("/api/risk-index/ZZZ")
    assert resp.status_code == 404


def test_risk_index_curated_country_returns_coverage_tier(client):
    resp = client.get("/api/risk-index/KOR")
    assert resp.status_code == 200
    assert resp.json()["coverage_tier"] == "curated"


def test_backtest_historical_endpoint_is_public_and_returns_summary(client):
    resp = client.get("/api/backtest/historical")
    assert resp.status_code == 200
    assert "summary" in resp.json()


def test_backtest_historical_event_endpoint_reports_unverified_for_unknown_event(client):
    resp = client.get("/api/backtest/historical/no_such_event")
    assert resp.status_code == 200
    assert resp.json()["verified"] is False


def test_risk_quantification_endpoint_is_public_and_flags_not_probability(client):
    resp = client.get("/api/risk-quantification")
    assert resp.status_code == 200
    body = resp.json()
    assert "countries" in body
    assert "disclaimer" in body
    assert body["countries"][0]["is_probability"] is False


def test_risk_quantification_country_endpoint_returns_components(client):
    resp = client.get("/api/risk-quantification/KOR")
    assert resp.status_code == 200
    assert set(resp.json()["components"]) == {"signal_pressure", "vulnerability", "spread_potential"}


def test_risk_quantification_unknown_country_returns_404(client):
    resp = client.get("/api/risk-quantification/ZZZ")
    assert resp.status_code == 404


def test_status_endpoint_reports_tier2_discovery_field(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "tier2_countries_discovered" in body
    assert body["tier2_countries_discovered"] == 0  # 신규 DB라 신호 없음


def test_climate_signals_endpoint_public_and_flags_leading_indicator(client):
    """기후 선행지표(㉛)는 공개 GET이고, 발병 측정치가 아니라 선행지표 추정임을
    disclaimer/note로 명시해야 함."""
    resp = client.get("/api/climate-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["countries"]) == 14
    assert "삼림파괴" in body["disclaimer"]  # 미구현 동인 정직하게 명시


def test_climate_signals_unknown_country_returns_404(client):
    resp = client.get("/api/climate-signals/ZZZ")
    assert resp.status_code == 404


def test_land_signals_endpoint_public_and_flags_proxy(client, monkeypatch):
    """토지이용 선행지표(㉜)는 공개 GET이고, 화재→삼림파괴가 프록시임을
    disclaimer로 명시해야 함. 키 없으면 configured=False."""
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    resp = client.get("/api/land-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["countries"]) == 13  # HKG 제외
    assert body["configured"] is False
    assert "GFW" in body["disclaimer"]


def test_land_signals_unknown_country_returns_404(client):
    resp = client.get("/api/land-signals/ZZZ")
    assert resp.status_code == 404


def test_threats_semantic_falls_back_without_api_key(client, monkeypatch):
    """ANTHROPIC_API_KEY 없으면 결정론적 폴백으로 동작하고 그 사실이 표시돼야 함(㉚)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.get("/api/threats/semantic")
    assert resp.status_code == 200
    body = resp.json()
    assert body["clustering_method"] == "disease_name_fallback"
    assert "ANTHROPIC_API_KEY" in body["note"]


def test_status_endpoint_includes_source_health(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    sh = resp.json()["source_health"]
    assert "degraded_sources" in sh
    assert "sources" in sh


def test_historical_backtest_includes_covid_bluedot_benchmark(client):
    """코로나 벤치마크가 자동 시드돼 블루닷 비교가 항상 나오는지(엔드포인트가
    _seed_known_timelines를 호출하므로) — 실측 없이도 목표 기준선은 표기."""
    resp = client.get("/api/backtest/historical/covid19_wuhan_2019")
    assert resp.status_code == 200
    body = resp.json()
    assert "bluedot_comparison" in body
    assert body["bluedot_comparison"]["bluedot_lead_days"] == 9


def test_db_backup_requires_auth(client):
    resp = client.get("/api/admin/db-backup")
    assert resp.status_code == 503  # 이 fixture는 키 미설정 상태


def test_db_backup_returns_valid_sqlite_snapshot(client_with_key, tmp_path):
    """⑲ — 백업 응답이 실제로 열어서 쿼리 가능한 온전한 SQLite 파일인지 확인."""
    client, key = client_with_key
    resp = client.get("/api/admin/db-backup", headers={"X-API-Key": key})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"

    out = tmp_path / "downloaded.db"
    out.write_bytes(resp.content)

    conn = sqlite3.connect(out)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "predictions" in tables
    assert "extracted_signals" in tables
    conn.close()

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
from unittest.mock import patch

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


def test_backtest_gdelt_endpoint_public_and_flags_reconstruction(client):
    """GDELT 과거 재구성 백테스트(㉟)는 공개 GET이고, 뉴스 커버리지 프록시·재구성임을
    note로 명시해야 함(라이브 신호와 안 섞음)."""
    resp = client.get("/api/backtest/gdelt")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "gdelt_coverage_volume" in body["note"] or "커버리지" in body["note"]
    assert "2017" in body["coverage_note"]


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


def test_travel_notices_endpoint_public_no_key_needed(client, monkeypatch):
    """CDC 여행경보(신규 각도, 2026-07-27)는 키 없이도 바로 응답해야 함."""
    monkeypatch.setattr(
        "algorithms.cdc_travel_notices.fetch_travel_notices",
        lambda: [{"level": 3, "headline": "Test Outbreak", "description": "",
                  "link": "https://example.com", "pub_date": ""}],
    )
    resp = client.get("/api/travel-notices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_available"] is True
    assert body["by_level"] == {"1": 0, "2": 0, "3": 1, "4": 0}
    assert set(body["level_meaning"]) == {"1", "2", "3", "4"}


def test_trade_signals_endpoint_public_and_flags_proxy(client, monkeypatch):
    """국제무역 선행지표(Phase 42)는 공개 GET이고, 신고지연을 disclaimer로
    명시해야 함. 키 없으면 configured=False."""
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    resp = client.get("/api/trade-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["countries"]) == 13  # HKG 제외
    assert body["configured"] is False
    assert "지연" in body["disclaimer"]


def test_trade_signals_unknown_country_returns_404(client):
    resp = client.get("/api/trade-signals/ZZZ")
    assert resp.status_code == 404


def test_deforestation_signals_endpoint_public_and_honest_about_verification(client, monkeypatch):
    """직접 산림손실 지표(㉝)는 공개 GET이고, 라이브 미검증을 disclaimer에
    정직하게 명시해야 함. 키 없으면 configured=False."""
    monkeypatch.delenv("GFW_API_KEY", raising=False)
    resp = client.get("/api/deforestation-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["countries"]) == 13  # HKG 제외
    assert body["configured"] is False
    assert "배포 환경에서 확인" in body["disclaimer"]


def test_deforestation_signals_unknown_country_returns_404(client):
    resp = client.get("/api/deforestation-signals/ZZZ")
    assert resp.status_code == 404


def test_polar_watch_endpoint_public_and_watch_grade_not_alert(client):
    """극지 관찰 층(㉞)은 공개 GET이고, '경보'가 아니라 watch 등급임을 명시해야 함."""
    resp = client.get("/api/polar-watch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["grade"] == "watch"
    assert "경보" in body["note"]
    assert len(body["regions"]) >= 5


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


def test_daily_brief_endpoint_public_and_flags_not_official(client, monkeypatch):
    """일일 브리핑(㊱)은 공개 GET이고, 공식 경보가 아님을 못박아야 함. 신규 DB라
    위협이 없으니 조용한 날로 나오고, 앵커 대본·자막·화면지시 3종을 갖춰야 함."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.get("/api/daily-brief")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_official_alert"] is False
    assert body["generation_method"] == "template_fallback"
    assert body["quiet_day"] is True  # 신규 DB — 신호 없음
    seg = body["segments"][0]
    assert seg["anchor_script"] and seg["lower_third"] and seg["visual_cue"]
    assert "공식 경보가 아니" in body["disclosure"]


def test_daily_brief_english_version(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.get("/api/daily-brief?lang=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["lang"] == "en"
    assert "AEGIRON" in body["program_name"]


def test_daily_brief_archive_empty_then_populated(client):
    """아카이브는 공개 GET. 신규 DB엔 비어있고, 저장하면 목록·상세로 조회됨."""
    empty = client.get("/api/daily-brief/archive")
    assert empty.status_code == 200
    assert empty.json()["briefs"] == []

    import db
    db.save_daily_brief("2026-07-25", "ko", {
        "headline": "테스트 브리핑", "quiet_day": True,
        "format": {"name": "속보 데스크"}, "segments": [],
    })
    lst = client.get("/api/daily-brief/archive")
    assert lst.json()["briefs"][0]["date"] == "2026-07-25"

    one = client.get("/api/daily-brief/archive/2026-07-25")
    assert one.status_code == 200
    assert one.json()["headline"] == "테스트 브리핑"


def test_daily_brief_archive_missing_date_returns_404(client):
    resp = client.get("/api/daily-brief/archive/1999-01-01")
    assert resp.status_code == 404


def test_genome_screen_requires_auth(client):
    """유전체 스크리닝은 POST라 쓰기 인증 필요(키 미설정 fixture → 503)."""
    resp = client.post("/api/synthetic-threat/genome-screen", json={"sequence": "ACGT" * 20})
    assert resp.status_code == 503


def test_genome_screen_computes_real_metrics(client_with_key):
    """Stage 0 실측 업그레이드: CAI·CpG·엔트로피를 실제로 계산해 반환하고,
    판정이 아니라 방어 스크리닝임을 명시."""
    client, key = client_with_key
    seq = "ATGGCCATTGTAATGGGCCGCTGCAAAGGGTGCCCGATAGTT"
    resp = client.post("/api/synthetic-threat/genome-screen",
                       headers={"X-API-Key": key}, json={"sequence": seq})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["shannon_entropy_bits"] is not None
    assert body["cpg_observed_expected"] is not None
    assert body["is_screening_only"] is True


def test_biodefense_readiness_requires_auth(client):
    """Stage 8(VALHALLA)은 최고 보안등급 — 인증 필수(키 미설정 fixture → 503)."""
    resp = client.post("/api/biodefense/readiness", json={})
    assert resp.status_code == 503


def test_biodefense_readiness_illustrative_with_key(client_with_key):
    client, key = client_with_key
    resp = client.post("/api/biodefense/readiness", headers={"X-API-Key": key}, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_illustrative"] is True
    assert "coverage" in body and "sovereignty" in body
    # 기밀 프로그램 메타데이터가 붙어야 함
    assert body["classification"]["program_code"] == "VALHALLA"
    assert "R&D 연구센터" in body["classification"]["owning_center_ko"]
    assert body["classification"]["designation_ko"] == "사내 R&D 프로그램"


def test_biodefense_readiness_computes_gaps_from_input(client_with_key):
    client, key = client_with_key
    resp = client.post("/api/biodefense/readiness", headers={"X-API-Key": key}, json={
        "countermeasures": [{"name": "국산항체", "type": "mAb", "targets": ["H5N1"],
                             "declared_efficacy": 0.6, "domestic_producible": True}],
        "threats": [{"pathogen": "H5N1"}, {"pathogen": "MERS"}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"]["covered"] == 1
    assert body["coverage"]["uncovered_threats"] == ["MERS"]


def test_genome_screen_attaches_heimdall_classification(client_with_key):
    """Stage 0(HEIMDALL)은 R&D 연구센터 관리·최고 보안등급 메타데이터가 붙어야 함."""
    client, key = client_with_key
    resp = client.post("/api/synthetic-threat/genome-screen",
                       headers={"X-API-Key": key}, json={"sequence": "ATGC" * 20})
    c = resp.json()["classification"]
    assert c["program_code"] == "HEIMDALL"
    assert "R&D 연구센터" in c["owning_center_ko"]
    assert c["classification_ko"].startswith("사내 최고 보안등급")
    assert c["audit_logged"] is True


def test_ai_provider_status_public_and_reports_fallback(client, monkeypatch):
    """독자 API 구조: 로컬 모델/NIM 없으면 외부 LLM 폴백임을 정직하게 표시."""
    monkeypatch.delenv("AEGIRON_LOCAL_MODEL", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    resp = client.get("/api/ai/provider-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_provider"] == "external_llm_fallback"
    assert "data_sovereignty" in body


def test_ai_training_data_stats_public(client):
    resp = client.get("/api/ai/training-data/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"] == "news_text_to_structured_signal"
    assert "total_pairs" in body


def test_ai_training_data_export_requires_auth(client):
    """학습셋 export는 독자 자산이라 인증 필수(키 미설정 fixture → 503)."""
    resp = client.get("/api/ai/training-data/export")
    assert resp.status_code == 503


def test_ai_nowcast_readiness_public_and_honest_when_insufficient(client):
    """Tier 2: 신규 DB엔 성과 라벨이 없어 sufficient_data=False가 정상(안 지어냄)."""
    resp = client.get("/api/ai/nowcast/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sufficient_data"] is False
    assert "feature_keys" in body


def test_ai_nowcast_train_requires_auth(client):
    resp = client.get("/api/ai/nowcast/train")
    assert resp.status_code == 503


def test_ai_nowcast_train_refuses_insufficient_with_key(client_with_key):
    client, key = client_with_key
    resp = client.get("/api/ai/nowcast/train", headers={"X-API-Key": key})
    assert resp.status_code == 200
    assert resp.json()["trained"] is False   # 데이터 부족 → 학습 거부(정직)


def test_genome_screen_accepts_reference_sequences(client_with_key):
    client, key = client_with_key
    seq = "ATGGCCATTGTAATGGGCCGCTGCAAAGGGTGCCCGATAGTT"
    resp = client.post("/api/synthetic-threat/genome-screen", headers={"X-API-Key": key}, json={
        "sequence": seq,
        "reference_sequences": [seq, seq[:-3] + "AAA", seq[:-6] + "AAAAAA"],
    })
    assert resp.status_code == 200
    assert "reference_comparison" in resp.json()


def test_patient_zero_origins_is_public_and_includes_auto_countries(client):
    # auto 국가는 런타임 캐시(world_countries_cache.json)에서 오는데 테스트/CI 환경엔
    # 없다 → 다른 origin_catalog 테스트와 동일하게 load_world_countries를 mock해
    # 결정론적으로 검증(캐시 유무에 흔들리지 않게).
    sample = {
        "VNM": {"name": "Viet Nam", "region": "East Asia & Pacific", "capital": "Hanoi",
                "iso2": "VN", "lat": 21.0069, "lng": 105.8194},
        "COD": {"name": "Congo, Dem. Rep.", "region": "Sub-Saharan Africa", "capital": "Kinshasa",
                "iso2": "CD", "lat": -4.4419, "lng": 15.2663},
    }
    with patch("algorithms.origin_catalog.load_world_countries", return_value=sample):
        resp = client.get("/api/patient-zero/origins")
    assert resp.status_code == 200
    origins = resp.json()["origins"]
    tiers = {o["tier"] for o in origins}
    assert "curated" in tiers
    assert "auto" in tiers               # auto 국가가 병합됐는지
    assert len(origins) > 8              # curated 8개 + auto 최소 1개 이상


def test_db_backup_requires_auth(client):
    resp = client.get("/api/admin/db-backup")
    assert resp.status_code == 503  # 이 fixture는 키 미설정 상태


# ── Stage 8 실제 재고 DB 연동 ─────────────────────────────────────
def test_stockpile_list_is_public(client):
    resp = client.get("/api/biodefense/stockpile")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_stockpile_create_requires_auth(client):
    resp = client.post("/api/biodefense/stockpile", json={
        "name": "테스트 항체", "targets": ["H5N1"], "domestic_producible": True,
    })
    assert resp.status_code == 503


def test_stockpile_create_and_list(client_with_key):
    client, key = client_with_key
    resp = client.post("/api/biodefense/stockpile", headers={"X-API-Key": key}, json={
        "name": "국산 항바이러스", "type": "antiviral", "targets": ["H5N1"],
        "declared_efficacy": 0.6, "domestic_producible": True,
    })
    assert resp.status_code == 200
    created = resp.json()
    assert created["name"] == "국산 항바이러스"
    assert created["domestic_producible"] is True

    listed = client.get("/api/biodefense/stockpile").json()["items"]
    assert len(listed) == 1
    assert listed[0]["targets"] == ["H5N1"]


def test_stockpile_delete(client_with_key):
    client, key = client_with_key
    created = client.post("/api/biodefense/stockpile", headers={"X-API-Key": key}, json={
        "name": "삭제될 항목", "targets": ["MERS"], "domestic_producible": False,
    }).json()
    resp = client.delete(f"/api/biodefense/stockpile/{created['id']}", headers={"X-API-Key": key})
    assert resp.status_code == 200
    assert client.get("/api/biodefense/stockpile").json()["items"] == []


def test_stockpile_delete_missing_returns_404(client_with_key):
    client, key = client_with_key
    resp = client.delete("/api/biodefense/stockpile/9999", headers={"X-API-Key": key})
    assert resp.status_code == 404


def test_readiness_uses_stored_stockpile_when_no_body(client_with_key):
    """등록된 실제 재고가 있으면 바디 없이 호출해도 예시 데이터가 아니라
    실제 재고로 계산해야 함(is_illustrative=False)."""
    client, key = client_with_key
    client.post("/api/biodefense/stockpile", headers={"X-API-Key": key}, json={
        "name": "국산 항바이러스", "targets": ["H5N1"],
        "declared_efficacy": 0.6, "domestic_producible": True,
    })
    resp = client.post("/api/biodefense/readiness", headers={"X-API-Key": key}, json={})
    body = resp.json()
    assert body["is_illustrative"] is False
    assert body["coverage"]["covered"] >= 1


def test_readiness_falls_back_to_illustrative_when_no_stockpile(client_with_key):
    client, key = client_with_key
    resp = client.post("/api/biodefense/readiness", headers={"X-API-Key": key}, json={})
    assert resp.json()["is_illustrative"] is True


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


def test_create_prediction_attaches_timestamp_proof_best_effort(client_with_key, monkeypatch):
    """Phase 44 — 예측 생성 시 존재증명을 best-effort로 제출·부착."""
    client, key = client_with_key
    monkeypatch.setattr(
        "algorithms.prediction_timestamp.submit_timestamp", lambda digest_hex: "aabbcc"
    )
    resp = client.post(
        "/api/predictions",
        json={"country": "KOR", "disease": "테스트", "risk_score": 50.0, "basis": ["근거1"]},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_hash"] is not None
    assert body["ots_proof_hex"] == "aabbcc"
    assert body["ots_submitted_at"] is not None


def test_create_prediction_succeeds_even_when_timestamp_submission_fails(client_with_key, monkeypatch):
    """캘린더 서버 전부 실패해도 예측 저장 자체는 절대 막히면 안 됨."""
    client, key = client_with_key
    monkeypatch.setattr(
        "algorithms.prediction_timestamp.submit_timestamp",
        lambda digest_hex: (_ for _ in ()).throw(Exception("network down")),
    )
    resp = client.post(
        "/api/predictions",
        json={"country": "KOR", "disease": "테스트", "risk_score": 50.0, "basis": ["근거1"]},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["ots_proof_hex"] is None


def test_timestamp_proof_endpoint_public_and_reports_unsubmitted(client_with_key, monkeypatch):
    """증명 조회는 공개 GET. 아직 제출 안 된 예측은 정직하게 unavailable."""
    client, key = client_with_key
    # 실제 캘린더 서버로 나가지 않게 명시적으로 실패시켜 '미제출' 경로를 검증.
    monkeypatch.setattr("algorithms.prediction_timestamp.submit_timestamp", lambda digest_hex: None)
    create_resp = client.post(
        "/api/predictions",
        json={"country": "KOR", "disease": "테스트", "risk_score": 50.0, "basis": ["근거1"]},
        headers={"X-API-Key": key},
    )
    pred_id = create_resp.json()["id"]

    resp = client.get(f"/api/predictions/{pred_id}/timestamp-proof")
    assert resp.status_code == 200
    assert resp.json()["data_available"] is False


def test_timestamp_proof_endpoint_unknown_prediction_returns_404(client):
    resp = client.get("/api/predictions/999999/timestamp-proof")
    assert resp.status_code == 404

def test_backtest_covers_drc_ebola_2026_bundibugyo(client):
    """① 2026 DRC 분디부조 에볼라가 실이력 백테스트 대상에 등록되고, 공식 선언
    마일스톤(5/15)이 잡힌다. (격리 테스트DB엔 신호가 없어 verified=False가 정상 —
    지어내지 않음. declaration_date가 잡히는 것으로 '대상 등록'을 확인.)"""
    resp = client.get("/api/backtest/historical/ebola_drc_2026")
    assert resp.status_code == 200
    body = resp.json()
    assert body["declaration_date"] == "2026-05-15"
    # 이벤트 자체는 인식됨(등록 안 됨이 아니라 '신호 없음'이 이유)
    assert "등록된 이벤트 없음" not in body.get("reason", "")

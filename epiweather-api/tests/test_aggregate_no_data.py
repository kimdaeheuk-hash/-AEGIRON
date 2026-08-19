"""집계 함수가 '자식 전멸'을 '이상 없음'으로 보고하지 않는지 (2026-08-19 전수점검).

source_health.py가 스스로 적어둔 문장이 이 테스트의 이유다:
  "조기경보 시스템에서 가장 위험한 결함은 소스가 죽었는데 시스템이 조용히 넘어가서
   '신호 없음 = 안전'으로 오해하는 것"

전수점검에서 그 결함이 집계 계층에 그대로 있었다. 자식 요청이 전부 실패해도 부모가
status:ok에 경보 0건을 돌려줘서, **전면 장애와 '전 세계 평온'이 글자 그대로 똑같이
보였다.** 어제 만든 no_data 상태를 여기까지 연결한 것을 고정한다."""
from __future__ import annotations
from unittest.mock import patch

from algorithms import behavioral_data as bd
from algorithms import supply_chain as sc


def test_supply_chain_total_failure_is_not_reported_as_calm(monkeypatch):
    """★핵심★ 네이버가 통째로 죽으면 '부족 없음'이 아니라 '모름'이어야 한다."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "x")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")
    all_failed = {"해열제": None, "마스크": None, "손소독제": None}

    with patch.object(sc, "fetch_supply_trends", return_value=all_failed):
        out = sc.get_supply_signal()

    assert out["status"] == "no_data"          # 예전엔 "ok"였다
    assert out["supply_alert_count"] is None   # 0이 아니다 — 0은 '없음'을 주장하는 것
    assert "모름" in out["note"]


def test_supply_chain_partial_failure_still_reports_what_it_has(monkeypatch):
    """일부만 실패하면 나머지는 살려야 한다 — 과잉 반응도 거짓이다."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "x")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")
    partial = {"해열제": 55.0, "마스크": None, "손소독제": 12.0}

    with patch.object(sc, "fetch_supply_trends", return_value=partial):
        out = sc.get_supply_signal()

    assert out["status"] == "ok"
    assert out["supply_items_ok"] == 2 and out["supply_items_total"] == 3
    assert out["supply_alert_items"] == ["해열제"]      # 30 이상만
    assert out["total_supply_ratio"] == 67.0


def test_supply_chain_zero_ratio_is_real_data_not_missing(monkeypatch):
    """실제로 0.0이 온 건 진짜 데이터다 — 결측으로 오인하면 안 된다."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "x")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")
    with patch.object(sc, "fetch_supply_trends", return_value={"해열제": 0.0}):
        out = sc.get_supply_signal()
    assert out["status"] == "ok" and out["supply_alert_count"] == 0


def test_hira_total_failure_is_not_reported_as_ok(monkeypatch):
    """HIRA가 한 건도 안 오면 '처방 급증 없음'이 아니라 '모름'."""
    monkeypatch.setenv("HIRA_API_KEY", "k")

    class _Resp:
        status_code = 500
        text = ""

    with patch.object(bd.requests, "get", return_value=_Resp()):
        out = bd.fetch_hira_drug_claims()

    assert out["status"] == "no_data"          # 예전엔 "ok"였다
    assert out["failed_codes"]                  # 무엇이 실패했는지 남는다


# ── db 마이그레이션이 조용히 실패하지 않는지 (2026-08-19) ────────────────
# 예전엔 sqlite3.OperationalError를 전부 삼켜서, '이미 있는 컬럼'(정상)과
# '없는 테이블'(진짜 실패)이 구분되지 않았다. 컬럼이 영영 안 생겨도 아무 소리가
# 안 나고, 한참 뒤 엉뚱한 INSERT 에러로만 드러난다.

def test_init_db_is_idempotent():
    """두 번 돌려도 조용히 성공해야 한다(이미 있는 컬럼은 정상)."""
    import db as db_mod
    db_mod.init_db()
    db_mod.init_db()          # 예외가 나면 실패


class _FakeConn:
    """ALTER TABLE만 실패시키는 가짜 연결. sqlite3.Connection은 불변이라 패치 불가."""

    def __init__(self, error: str):
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def executescript(self, sql):
        return None

    def execute(self, sql, *a, **kw):
        import sqlite3
        if sql.strip().upper().startswith("ALTER TABLE"):
            raise sqlite3.OperationalError(self.error)
        return None

    def commit(self):
        return None


def test_real_migration_failure_is_not_swallowed(monkeypatch):
    """★핵심★ 진짜 실패한 마이그레이션은 반드시 터져야 한다."""
    import sqlite3
    import pytest
    import db as db_mod

    monkeypatch.setattr(db_mod, "get_connection",
                        lambda: _FakeConn("no such table: sentinel_queue"))
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        db_mod.init_db()


def test_duplicate_column_is_still_treated_as_normal(monkeypatch):
    """'이미 있는 컬럼'은 정상 — 여기까지 터지면 재배포가 전부 실패한다."""
    import db as db_mod

    monkeypatch.setattr(db_mod, "get_connection",
                        lambda: _FakeConn("duplicate column name: confidence"))
    db_mod.init_db()          # 예외가 나면 실패

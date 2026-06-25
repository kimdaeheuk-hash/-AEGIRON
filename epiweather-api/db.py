"""예측 검증 DB — SQLite.

인수인계서 Part1 ⑧: "우리가 72% 맞췄다"를 증명하려면 예측 시점과
검증 시점을 분리해서 기록해야 함. predicted_at에 근거 3가지와 함께
기록하고, 나중에 실제 결과가 나오면 verify로 채점.
"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "data" / "epiweather.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    predicted_at  TEXT NOT NULL,
    country       TEXT NOT NULL,
    disease       TEXT NOT NULL,
    risk_score    REAL NOT NULL,
    basis         TEXT NOT NULL,
    verified_at   TEXT,
    actual_result TEXT,
    lead_days     INTEGER,
    correct       INTEGER
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_date  TEXT NOT NULL,   -- YYYY-MM-DD, 일일 캡 카운트 기준
    source      TEXT NOT NULL,   -- 같은 조건의 재발생을 식별하는 키 (예: gai:behavioral.naver_flu_ratio)
    tier        TEXT NOT NULL,   -- critical | high | medium | low
    label       TEXT NOT NULL,
    score       REAL NOT NULL,
    suppressed  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE(alert_date, source)
);

CREATE TABLE IF NOT EXISTS extracted_signals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    extracted_at   TEXT NOT NULL,
    source         TEXT NOT NULL,   -- global_watch.py의 slug (who_emro, africa_cdc 등)
    disease        TEXT,
    location       TEXT,
    signal_type    TEXT,            -- 급증 | 감소 | 신규발생 | 진행중 | 종료 | 불명
    severity       TEXT NOT NULL,   -- JSON 배열 문자열
    symptom        TEXT,
    transmission   TEXT,
    source_trust   REAL NOT NULL,
    signal_date    TEXT,            -- 텍스트가 언급한 기준일 (YYYY-MM-DD), 모르면 NULL
    known_disease  INTEGER NOT NULL DEFAULT 1,  -- 모델이 "기존에 알려진 질병 패턴과 일치"로 판단했는지
    raw_text       TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def create_prediction(country: str, disease: str, risk_score: float, basis: list[str]) -> dict:
    predicted_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO predictions (predicted_at, country, disease, risk_score, basis) "
            "VALUES (?, ?, ?, ?, ?)",
            (predicted_at, country, disease, risk_score, json.dumps(basis, ensure_ascii=False)),
        )
        conn.commit()
        return get_prediction(cur.lastrowid)


def get_prediction(prediction_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (prediction_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def list_predictions(country: str | None = None, verified_only: bool = False) -> list[dict]:
    query = "SELECT * FROM predictions"
    conditions = []
    params: list = []
    if country:
        conditions.append("country = ?")
        params.append(country)
    if verified_only:
        conditions.append("verified_at IS NOT NULL")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY predicted_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]


def verify_prediction(
    prediction_id: int, actual_result: str, correct: bool, lead_days: int | None = None
) -> dict | None:
    verified_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE predictions SET verified_at = ?, actual_result = ?, correct = ?, lead_days = ? "
            "WHERE id = ?",
            (verified_at, actual_result, int(correct), lead_days, prediction_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        return get_prediction(prediction_id)


def accuracy_stats(country: str | None = None) -> dict:
    """검증된 예측 중 정확도·평균 선행일수. '72% 맞췄다' 수치의 출처."""
    verified = list_predictions(country=country, verified_only=True)
    total = len(verified)
    correct = sum(1 for p in verified if p["correct"])
    leads = [p["lead_days"] for p in verified if p["lead_days"] is not None]
    return {
        "total_verified": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else None,
        "mean_lead_days": round(sum(leads) / len(leads), 1) if leads else None,
    }


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["basis"] = json.loads(d["basis"])
    d["correct"] = bool(d["correct"]) if d["correct"] is not None else None
    return d


# ── 경보 피로 방지 (alerts) ──────────────────────────────────
def upsert_alert(alert_date: str, source: str, tier: str, label: str, score: float) -> None:
    """같은 날 같은 source는 갱신만 함 — 매시간 재계산해도 캡 카운트가 부풀지 않게."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO alerts (alert_date, source, tier, label, score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alert_date, source) DO UPDATE SET
                tier = excluded.tier,
                label = excluded.label,
                score = excluded.score,
                updated_at = excluded.updated_at
            """,
            (alert_date, source, tier, label, score, now, now),
        )
        conn.commit()


def set_suppressed(alert_ids: list[int], suppressed: bool) -> None:
    if not alert_ids:
        return
    with get_connection() as conn:
        conn.executemany(
            "UPDATE alerts SET suppressed = ? WHERE id = ?",
            [(int(suppressed), aid) for aid in alert_ids],
        )
        conn.commit()


def list_alerts(alert_date: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE alert_date = ? ORDER BY score DESC", (alert_date,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── NLP 구조화 추출 (extracted_signals) ──────────────────────
def create_extracted_signal(
    source: str, disease: str | None, location: str | None, signal_type: str | None,
    severity: list[str], symptom: str | None, transmission: str | None,
    source_trust: float, signal_date: str | None, raw_text: str,
    known_disease: bool = True,
) -> dict:
    extracted_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO extracted_signals
                (extracted_at, source, disease, location, signal_type, severity,
                 symptom, transmission, source_trust, signal_date, known_disease, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (extracted_at, source, disease, location, signal_type,
             json.dumps(severity, ensure_ascii=False), symptom, transmission,
             source_trust, signal_date, int(known_disease), raw_text),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM extracted_signals WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return _extracted_row_to_dict(row)


def list_extracted_signals(disease: str | None = None, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM extracted_signals"
    params: list = []
    if disease:
        query += " WHERE disease = ?"
        params.append(disease)
    query += " ORDER BY extracted_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_extracted_row_to_dict(r) for r in rows]


def _extracted_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["severity"] = json.loads(d["severity"])
    d["known_disease"] = bool(d["known_disease"])
    return d

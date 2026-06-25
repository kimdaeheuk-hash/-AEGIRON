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
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA)


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

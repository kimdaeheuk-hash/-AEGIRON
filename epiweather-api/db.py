"""예측 검증 DB — SQLite.

인수인계서 Part1 ⑧: "우리가 72% 맞췄다"를 증명하려면 예측 시점과
검증 시점을 분리해서 기록해야 함. predicted_at에 근거 3가지와 함께
기록하고, 나중에 실제 결과가 나오면 verify로 채점.
"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

DB_PATH = Path(__file__).parent / "data" / "epiweather.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS outbreak_timeline (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id     TEXT NOT NULL,
    event_name   TEXT NOT NULL,
    event_date   TEXT NOT NULL,
    milestone    TEXT NOT NULL,
    description  TEXT NOT NULL,
    source       TEXT,
    source_type  TEXT,
    created_at   TEXT NOT NULL,
    UNIQUE(event_id, milestone)
);

CREATE TABLE IF NOT EXISTS sentinel_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at   TEXT NOT NULL,
    layer         TEXT NOT NULL,
    metric        TEXT NOT NULL,
    spike_ratio   REAL NOT NULL,
    latest_val    REAL NOT NULL,
    baseline_avg  REAL NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending | confirmed | dismissed
    evidence      TEXT,
    confidence    REAL,
    verified_at   TEXT,
    verified_by   TEXT,   -- ai | human — 이 판정을 누가 내렸는지
    ai_status     TEXT,   -- AI가 최초로 내린 판정(사람이 나중에 재검증해도 덮어쓰지 않음 — 일치율 비교용)
    ai_confidence REAL,
    UNIQUE(detected_at, layer, metric)
);

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

CREATE TABLE IF NOT EXISTS api_key_usage (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key_label  TEXT NOT NULL,   -- EPIWEATHER_API_KEYS의 라벨 (예: "internal_frontend", "airline_partner_a")
    endpoint   TEXT NOT NULL,
    called_at  TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    # WAL: 백그라운드 스케줄러와 API 요청이 동시에 읽고/쓸 때 서로 안 막게 함.
    # busy_timeout: 그래도 쓰기가 겹치면 즉시 실패 대신 5초까지 재시도 대기.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # sentinel_queue에 verified_by/ai_status/ai_confidence 컬럼 도입 전에
        # 이미 만들어진 DB(운영 중인 것 포함)에도 안전하게 추가.
        # CREATE TABLE IF NOT EXISTS는 기존 테이블에 컬럼을 추가해주지 않으므로
        # ALTER TABLE로 따로 처리 — 이미 있으면 OperationalError만 삼킴.
        for ddl in (
            "ALTER TABLE sentinel_queue ADD COLUMN verified_by TEXT",
            "ALTER TABLE sentinel_queue ADD COLUMN ai_status TEXT",
            "ALTER TABLE sentinel_queue ADD COLUMN ai_confidence REAL",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        conn.commit()


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


def list_recent_signals_by_source(source: str, days: int = 21, limit: int = 50) -> list[dict]:
    """최근 N일 이내 특정 source의 추출 신호 목록 — 같은 사건 재탐지 여부 판정용."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM extracted_signals WHERE source = ? AND extracted_at >= ? "
            "ORDER BY extracted_at DESC LIMIT ?",
            (source, cutoff, limit),
        ).fetchall()
        return [_extracted_row_to_dict(r) for r in rows]


def _extracted_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["severity"] = json.loads(d["severity"])
    d["known_disease"] = bool(d["known_disease"])
    return d


# ── Sentinel Queue ────────────────────────────────────────────
def upsert_timeline_event(
    event_id: str, event_name: str, event_date: str,
    milestone: str, description: str,
    source: str | None = None, source_type: str | None = None,
) -> dict:
    """발병 타임라인 이벤트 추가. 같은 milestone은 갱신."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO outbreak_timeline
                (event_id, event_name, event_date, milestone, description, source, source_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, milestone) DO UPDATE SET
                description = excluded.description,
                source = excluded.source
            """,
            (event_id, event_name, event_date, milestone, description, source, source_type, now),
        )
        conn.commit()
    return get_timeline(event_id)


def get_timeline(event_id: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM outbreak_timeline WHERE event_id = ? ORDER BY event_date",
            (event_id,),
        ).fetchall()
        if not rows:
            return {"event_id": event_id, "milestones": []}
        return {
            "event_id":   event_id,
            "event_name": rows[0]["event_name"],
            "milestones": [dict(r) for r in rows],
        }


def list_timeline_events() -> list[dict]:
    """진행 중인 발병 이벤트 목록 (event_id별 최신 마일스톤)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, event_name, MAX(event_date) as latest_date, COUNT(*) as milestone_count
            FROM outbreak_timeline GROUP BY event_id ORDER BY latest_date DESC
            """,
        ).fetchall()
        return [dict(r) for r in rows]


def upsert_sentinel(
    detected_at: str, layer: str, metric: str,
    spike_ratio: float, latest_val: float, baseline_avg: float,
) -> int:
    """같은 날 같은 metric은 갱신 — 매시간 재스캔해도 중복 안 쌓임."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO sentinel_queue
                (detected_at, layer, metric, spike_ratio, latest_val, baseline_avg)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(detected_at, layer, metric) DO UPDATE SET
                spike_ratio  = excluded.spike_ratio,
                latest_val   = excluded.latest_val,
                baseline_avg = excluded.baseline_avg
            """,
            (detected_at, layer, metric, spike_ratio, latest_val, baseline_avg),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM sentinel_queue WHERE detected_at=? AND layer=? AND metric=?",
            (detected_at, layer, metric),
        ).fetchone()
        return row["id"]


def update_sentinel_verification(
    sentinel_id: int, status: str, evidence: str | None, confidence: float | None,
    verified_by: str = "ai",
) -> None:
    """
    verified_by="ai" (verification.py의 자동검증)일 때만 ai_status/ai_confidence를
    같이 기록한다. verified_by="human"(수동 재검증, POST /api/sentinel/{id}/verify)이면
    기존 ai_status/ai_confidence는 그대로 두고 status/evidence만 갱신 —
    "AI가 처음에 뭐라고 판단했었는지"를 사람이 나중에 고쳐도 비교할 수 있게 보존.
    """
    verified_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if verified_by == "ai":
            conn.execute(
                "UPDATE sentinel_queue SET status=?, evidence=?, confidence=?, verified_at=?, "
                "verified_by=?, ai_status=?, ai_confidence=? WHERE id=?",
                (status, evidence, confidence, verified_at, verified_by, status, confidence, sentinel_id),
            )
        else:
            conn.execute(
                "UPDATE sentinel_queue SET status=?, evidence=?, confidence=?, verified_at=?, "
                "verified_by=? WHERE id=?",
                (status, evidence, confidence, verified_at, verified_by, sentinel_id),
            )
        conn.commit()


def sentinel_verification_accuracy() -> dict:
    """
    AI 자동검증(verification.py) 후 사람이 나중에 재검증한 사례들만 골라서
    AI 판정과 사람 판정이 얼마나 일치하는지 계산 — "AI 검증을 얼마나 믿을
    수 있는가"의 실측 근거. verified_by='human'이면서 ai_status가 남아있는
    (=AI가 먼저 판단했던) 항목만 대상으로 함.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, ai_status FROM sentinel_queue "
            "WHERE verified_by = 'human' AND ai_status IS NOT NULL"
        ).fetchall()
    total = len(rows)
    if total == 0:
        return {
            "total_compared": 0, "agreed": 0, "agreement_rate": None,
            "note": "AI 판정 후 사람이 재검증한 사례가 아직 없음 — 표본 쌓이면 계산됨",
        }
    agreed = sum(1 for r in rows if r["status"] == r["ai_status"])
    return {
        "total_compared": total,
        "agreed": agreed,
        "agreement_rate": round(agreed / total, 3),
    }


def metric_reliability_report(min_samples: int = 3) -> list[dict]:
    """
    (layer, metric)별로 Sentinel 검증 이력(confirmed/dismissed)을 집계해
    오탐율이 높은 지표를 자동으로 드러낸다.

    지금까지 negative_space.py의 UNRELIABLE_METRICS·SEASONAL_METRICS는
    사람이 로그를 보고 수동으로 찾아서 하드코딩한 것(git log 참고 — 실측
    오탐 사례가 쌓일 때마다 커밋으로 예외 목록을 늘려옴). 이 리포트는 같은
    판단을 검증 이력 데이터로 자동 계산해서, "이 지표는 못 믿는다"를 사람이
    매번 로그를 뒤져서 발견하지 않아도 시스템 스스로 계속 드러내게 한다 —
    실제로 UNRELIABLE_METRICS에 반영할지는 여전히 사람이 판단(자동 제외까지
    시키면 진짜 위협 신호를 스스로 꺼버릴 위험이 있어 최종 판단은 안 자동화).

    표본이 min_samples 미만인 지표는 통계적으로 의미가 없어 제외.
    false_positive_rate 내림차순(가장 못 믿을 지표가 먼저) 정렬.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT layer, metric, status FROM sentinel_queue WHERE status != 'pending'"
        ).fetchall()

    grouped: dict[tuple[str, str], dict[str, int]] = {}
    for r in rows:
        key = (r["layer"], r["metric"])
        counts = grouped.setdefault(key, {"confirmed": 0, "dismissed": 0})
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    report = []
    for (layer, metric), counts in grouped.items():
        confirmed = counts.get("confirmed", 0)
        dismissed = counts.get("dismissed", 0)
        total = confirmed + dismissed
        if total < min_samples:
            continue
        report.append({
            "layer": layer,
            "metric": metric,
            "total_flagged": total,
            "confirmed": confirmed,
            "dismissed": dismissed,
            "false_positive_rate": round(dismissed / total, 3),
        })
    report.sort(key=lambda r: -r["false_positive_rate"])
    return report


def list_sentinel_queue(status: str | None = None, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM sentinel_queue"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY detected_at DESC, spike_ratio DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ── 모니터링 (/api/status) ───────────────────────────────────
_STATUS_TABLES = (
    "predictions", "alerts", "extracted_signals",
    "sentinel_queue", "outbreak_timeline",
)


def table_counts() -> dict[str, int]:
    """/api/status용 — 주요 테이블 행 수 스냅샷."""
    with get_connection() as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            for table in _STATUS_TABLES
        }


# ── API 키 사용량 로깅 ────────────────────────────────────────
# 지금은 요율제한을 만들지 않는다 — 실제 고객사가 생기기 전에 임계값을
# 정하면 근거 없는 숫자가 됨. 우선 라벨별 호출 이력만 쌓아서, 나중에
# 실제 사용 패턴을 보고 요율제한 정책을 정할 수 있게 함.
def log_api_key_usage(key_label: str, endpoint: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO api_key_usage (key_label, endpoint, called_at) VALUES (?, ?, ?)",
            (key_label, endpoint, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def api_key_usage_summary(days: int = 30) -> list[dict]:
    """라벨별 최근 N일 호출 수·최근 호출 시각 — 요율제한 정책 설계용 근거 데이터."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key_label, COUNT(*) AS call_count, MAX(called_at) AS last_called_at "
            "FROM api_key_usage WHERE called_at >= ? GROUP BY key_label ORDER BY call_count DESC",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]

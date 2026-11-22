"""아이기론 DB — SQLite (Railway 볼륨).

2026-11-22 개편 뒤 남은 표: 헤임달 변이 원장(variant_ledger) · 발할라 대조 원장
(match_ledger) · 대응제 비축(countermeasure_stockpile) · 극지 관측값 시계열
(observations) · API 키 사용량(api_key_usage).

2026-11-22 오후: BAIKAL MOB 을 상태변화 엔진으로 다시 세웠다(baikal_mob_* 표).
옛 표(예측·경보·옛 BAIKAL·주간 예보 등)는 코드에서 지웠다. 운영 DB 파일에는 그 표가
그대로 남아 있지만 읽지도 쓰지도 않는다(복원 기준 커밋 83406e4).
FK 는 선언하지 않는다 — 남은 표끼리 참조가 없다. PRAGMA foreign_keys=ON 은 유지.
"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "data" / "epiweather.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_key_usage (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key_label  TEXT NOT NULL,   -- EPIWEATHER_API_KEYS의 라벨 (예: "internal_frontend", "airline_partner_a")
    endpoint   TEXT NOT NULL,
    called_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS countermeasure_stockpile (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    type                 TEXT,
    targets              TEXT NOT NULL,           -- JSON 배열 (대응 병원체 목록)
    declared_efficacy    REAL,
    domestic_producible  INTEGER NOT NULL DEFAULT 0,
    courses              INTEGER,                 -- 비축 인분(선택)
    population           INTEGER,                 -- 대상 인구(선택)
    attack_rate          REAL,                    -- 예상 발병률(선택)
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
-- ── 변이 상태원장 (2026-11-03) ─────────────────────────────────────
-- 매 수집 주기 Nextstrain 빌드별 (우세 계통, 구성비, 신규 계통) 한 행.
-- BAIKAL이 시스템 상태 전이를 적는다면, 여기는 병원체 자체의 상태 전이를
-- 적는다. available=False 주기는 적지 않는다(없는 관측을 "변화 없음"으로
-- 적으면 거짓말). 전이는 지우지 않는다(감사 기록).
CREATE TABLE IF NOT EXISTS variant_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at     TEXT NOT NULL,       -- UTC ISO, 수집 주기 시각
    build           TEXT NOT NULL,       -- Nextstrain 빌드 slug
    label           TEXT NOT NULL,       -- 표시명
    dominant_clade  TEXT,                -- 우세 계통
    dominant_share  REAL,                -- 우세 계통 구성비
    n_recent        INTEGER,             -- 최근 구간 시퀀스 수
    new_clades      TEXT NOT NULL,       -- JSON 배열 — 직전 구간 대비 신규
    prev_dominant   TEXT,                -- 직전 주기 우세 계통(NULL=첫 기록)
    transition      TEXT NOT NULL,       -- none / first_seen / dominant_changed / new_clade
    build_updated   TEXT                 -- Nextstrain 빌드 갱신일
);
CREATE INDEX IF NOT EXISTS idx_variant_ledger_build_observed ON variant_ledger(build, observed_at);
-- ── 대응제 매칭원장 (2026-11-03) ───────────────────────────────────
-- "오늘 이 비축이 이 변이를 막는가" — 위협×비축(선언 효능)×변이상태의
-- 일일 판정 1행/위협. 변이 전이는 수치 할인이 아니라 "재확인 필요" 플래그로만
-- 쓴다(분자 중화 예측 지어내기 금지). 실데이터로만 기록(예시 금지).
CREATE TABLE IF NOT EXISTS match_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    verdict_date    TEXT NOT NULL,       -- UTC 날짜(YYYY-MM-DD)
    pathogen        TEXT NOT NULL,
    coverage_status TEXT NOT NULL,       -- covered / uncovered / unrated
    best_efficacy   REAL,                -- 선언 효능 최댓값(covered만)
    covering        TEXT NOT NULL,       -- JSON 배열 — 커버 대응제명
    variant_build   TEXT,                -- 연결된 변이 감시 빌드(NULL=미연결)
    variant_flag    TEXT,                -- JSON — 최근 7일 전이(NULL=없음)
    verdict         TEXT NOT NULL,       -- holds / recheck / gap / unknown
    note            TEXT,
    UNIQUE(verdict_date, pathogen)
);
CREATE INDEX IF NOT EXISTS idx_match_ledger_date ON match_ledger(verdict_date);
-- 관측값 시계열(2026-11-15) — 요청 때 계산하고 버리던 층(극지·기후·토지·삼림·무역·재난·여행경보)을
-- 매시간 남긴다. 값이 그대로면 새 행 대신 confirmed_at·checks 만 갱신한다(같은 값을 매시간 복제하지 않음).
-- 실패한 시각은 status='undetermined' 행(이유 포함)으로 남긴다 — 빈칸을 0 으로 채우지 않는다.
CREATE TABLE IF NOT EXISTS observations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    layer         TEXT NOT NULL,             -- polar | climate | land | deforestation | trade | disaster | travel
    target        TEXT NOT NULL,             -- ISO3 · 극지 지역 id · 여행경보 id · 층 전체 실패면 '*'
    metric        TEXT NOT NULL DEFAULT '',  -- 같은 대상 안의 하위 계열(무역 품목 등), 없으면 ''
    status        TEXT NOT NULL,             -- ok | undetermined
    measured      TEXT,                      -- JSON: 출처가 준 측정값
    derived       TEXT,                      -- JSON: 우리가 계산한 해석값(추정·지수)
    reason        TEXT,                      -- undetermined 이유
    source        TEXT,
    value_hash    TEXT NOT NULL,
    observed_at   TEXT NOT NULL,             -- 이 값이 처음 계산된 시각(UTC)
    confirmed_at  TEXT NOT NULL,             -- 같은 값을 마지막으로 다시 확인한 시각(UTC)
    checks        INTEGER NOT NULL DEFAULT 1 -- 같은 값으로 확인된 횟수
);
CREATE INDEX IF NOT EXISTS idx_observations_key ON observations(layer, target, metric, id);
CREATE INDEX IF NOT EXISTS idx_observations_layer_time ON observations(layer, confirmed_at);
-- ── BAIKAL MOB 상태변화 엔진 (2026-11-22 재구현) ─────────────────────
-- 옛 baikal_snapshots/baikal_transitions 는 운영 DB 에 남아 있지만 옛 7개 시스템
-- (HUGINN…) 기록이라 섞지 않으려고 새 이름을 쓴다. 매 수집 주기 스냅숏 1행,
-- 전이는 상태가 **바뀐 순간만**(from_status NULL = 관측 시작). 지우지 않는다(감사 기록).
CREATE TABLE IF NOT EXISTS baikal_mob_snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at  TEXT NOT NULL,          -- UTC ISO
    payload      TEXT NOT NULL           -- JSON — baikal.observe() 결과 전체
);
CREATE INDEX IF NOT EXISTS idx_baikal_mob_snapshots_observed ON baikal_mob_snapshots(observed_at);
CREATE TABLE IF NOT EXISTS baikal_mob_transitions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at  TEXT NOT NULL,
    node         TEXT NOT NULL,          -- 온톨로지 노드 키(COLLECTOR · HEIMDALL_VARIANTS …)
    from_status  TEXT,                   -- NULL = 관측 시작
    to_status    TEXT NOT NULL,
    reason       TEXT,
    evidence     TEXT                    -- measured / estimated / proxy
);
CREATE INDEX IF NOT EXISTS idx_baikal_mob_transitions_observed ON baikal_mob_transitions(observed_at);
-- 스키마 버전(2026-11-02). init_db()가 매 호출마다 DDL 전문을 돌리지 않게
-- 1행짜리 버전표로 판정한다. 스키마를 바꾸면 SCHEMA_VERSION을 올릴 것.
CREATE TABLE IF NOT EXISTS _schema_version (
    id       INTEGER PRIMARY KEY CHECK (id = 1),
    version  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_api_usage_label_called ON api_key_usage(key_label, called_at);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    # WAL: 백그라운드 스케줄러와 API 요청이 동시에 읽고/쓸 때 서로 안 막게 함.
    # busy_timeout: 그래도 쓰기가 겹치면 즉시 실패 대신 5초까지 재시도 대기.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    # FK 강제: 지금 선언된 FK는 없지만(값 연결 테이블이라), 앞으로 추가되는
    # FK가 연결마다 반드시 강제되도록 기본 켜둔다. 기존 동작 변화 없음.
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# 스키마 버전 — SCHEMA 를 바꾸면 1 올린다. 안 올리면 운영 DB 에 새 표가 안 생긴다
# (init_db 가 버전이 맞으면 DDL 을 건너뛰므로 — 2026-11-03 /api/variant-ledger 500 실측).
# v6 이 개편 전 마지막 버전이다. v7(2026-11-22): BAIKAL MOB 표 두 개 추가.
SCHEMA_VERSION = 7


def _db_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT version FROM _schema_version WHERE id = 1").fetchone()
    except sqlite3.OperationalError:
        return 0  # 버전표 없음 = 구 DB
    return row[0] if row else 0


def _migrate(conn: sqlite3.Connection) -> None:
    """DDL 전문 + 버전 기록. 버전 판정은 init_db가 한다."""
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO _schema_version (id, version) VALUES (1, ?)",
                 (SCHEMA_VERSION,))
    conn.commit()


def init_db() -> None:
    """DB 준비. 버전이 맞으면 DDL을 건너뛴다(요청·수집마다 전문 실행 방지)."""
    with get_connection() as conn:
        if _db_version(conn) >= SCHEMA_VERSION:
            return
        _migrate(conn)
        conn.commit()


# ── 관측값 시계열 (2026-11-15) ─────────────────────────────────────────
def record_observation(
    *, layer: str, target: str, metric: str = "", status: str, measured: dict | None,
    derived: dict | None, reason: str | None, source: str | None, at: str,
) -> str:
    """관측 한 건을 남긴다. 직전 행과 값이 같으면 확인 시각만 갱신하고 'same', 다르면 새 행 'new'."""
    import hashlib

    payload = json.dumps([status, measured, derived, reason], ensure_ascii=False, sort_keys=True, default=str)
    h = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    with get_connection() as conn:
        last = conn.execute(
            "SELECT id, value_hash, confirmed_at FROM observations WHERE layer = ? AND target = ? AND metric = ? "
            "ORDER BY id DESC LIMIT 1",
            (layer, target, metric),
        ).fetchone()
        if last is not None and last["value_hash"] == h:
            conn.execute(
                "UPDATE observations SET confirmed_at = MAX(confirmed_at, ?), checks = checks + 1 WHERE id = ?",
                (at, last["id"]),
            )
            conn.commit()
            return "same"
        conn.execute(
            "INSERT INTO observations (layer, target, metric, status, measured, derived, reason, source, "
            "value_hash, observed_at, confirmed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                layer, target, metric, status,
                None if measured is None else json.dumps(measured, ensure_ascii=False, default=str),
                None if derived is None else json.dumps(derived, ensure_ascii=False, default=str),
                reason, source, h, at, at,
            ),
        )
        conn.commit()
        return "new"


def observation_history(
    layer: str, target: str | None = None, metric: str | None = None,
    since: str | None = None, limit: int = 2000,
) -> list[dict]:
    """관측 이력(오래된 것부터). since 는 confirmed_at 기준 — 그 뒤에도 유효했던 값까지 포함."""
    sql = "SELECT * FROM observations WHERE layer = ?"
    args: list = [layer]
    if target is not None:
        sql += " AND target = ?"
        args.append(target)
    if metric is not None:
        sql += " AND metric = ?"
        args.append(metric)
    if since is not None:
        sql += " AND confirmed_at >= ?"
        args.append(since)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, args).fetchall()
    out = []
    for r in reversed(rows):
        d = dict(r)
        d.pop("value_hash", None)
        for k in ("measured", "derived"):
            d[k] = json.loads(d[k]) if d[k] else None
        out.append(d)
    return out


# ── 모니터링 (/api/status) ───────────────────────────────────
_STATUS_TABLES = (
    "variant_ledger", "match_ledger", "countermeasure_stockpile", "observations",
    "baikal_mob_snapshots", "baikal_mob_transitions",
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


# ── Stage 8(VALHALLA) 실제 대응제 비축 목록 ──────────────────────
# 기존엔 /api/biodefense/readiness가 매 요청마다 비축 목록을 통째로 받아야
# 했고, 안 주면 항상 예시 데이터로 갔음. 실제 정부미팅용으로 쓰려면
# "한 번 등록해두면 계속 쓰는" 구조가 필요해서 영속 저장으로 옮김.
def create_countermeasure(
    name: str, type_: str | None, targets: list[str], declared_efficacy: float | None,
    domestic_producible: bool, courses: int | None = None,
    population: int | None = None, attack_rate: float | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO countermeasure_stockpile "
            "(name, type, targets, declared_efficacy, domestic_producible, courses, "
            "population, attack_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, type_, json.dumps(targets, ensure_ascii=False), declared_efficacy,
             int(domestic_producible), courses, population, attack_rate, now, now),
        )
        conn.commit()
        return get_countermeasure(cur.lastrowid)


def get_countermeasure(item_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM countermeasure_stockpile WHERE id = ?", (item_id,)
        ).fetchone()
        return _countermeasure_row_to_dict(row) if row else None


def list_countermeasures() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM countermeasure_stockpile ORDER BY created_at DESC"
        ).fetchall()
        return [_countermeasure_row_to_dict(r) for r in rows]


def delete_countermeasure(item_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM countermeasure_stockpile WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0


def _countermeasure_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["targets"] = json.loads(d["targets"])
    d["domestic_producible"] = bool(d["domestic_producible"])
    return d




# ── BAIKAL MOB (상태변화 엔진) ────────────────────────────────
def insert_baikal_snapshot(snapshot: dict) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("INSERT INTO baikal_mob_snapshots (observed_at, payload) VALUES (?, ?)",
                     (snapshot["observed_at"], json.dumps(snapshot, ensure_ascii=False)))


def latest_baikal_snapshot() -> dict | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT payload FROM baikal_mob_snapshots "
                           "ORDER BY observed_at DESC, id DESC LIMIT 1").fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except (TypeError, ValueError):
        return None


def insert_baikal_transition(observed_at: str, t: dict) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO baikal_mob_transitions "
            "(observed_at, node, from_status, to_status, reason, evidence) VALUES (?, ?, ?, ?, ?, ?)",
            (observed_at, t["node"], t.get("from_status"), t["to_status"], t.get("reason"),
             t.get("evidence")))


def list_baikal_transitions(limit: int = 50, node: str | None = None) -> list[dict]:
    init_db()
    limit = max(1, min(int(limit), 500))
    query = ("SELECT observed_at, node, from_status, to_status, reason, evidence "
             "FROM baikal_mob_transitions")
    params: list = []
    if node:
        query += " WHERE node = ?"
        params.append(node)
    query += " ORDER BY observed_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]

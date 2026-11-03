"""대응제 매칭원장 — "오늘 이 비축이 이 변이를 막는가" 일일 판정 (2026-11-03).

## 왜 만들었나

compute_readiness는 선언 효능 기준 커버리지를 계산하지만, 변이가 바뀌면
효능 전제가 흔들린다. 변이원장(variant_ledger)이 그 변화를 추적하므로,
둘을 매일 맞물려 판정한다:

- holds: 커버 + 연결된 변이 감시에 최근 전이 없음
- recheck: 커버 + 최근 7일 내 변이 전이 → 효능 재확인 필요(수치 할인은 안 함)
- gap: 미커버
- unknown: 판정 불가(unrated)

★ 수치 효능 할인을 하지 않는다 ★ 변이별 분자 중화 예측(escape)은
BioNeMo·CEPI 연동 Phase 2이며, 여기서 계수를 지어내면 '가짜 정밀도'가 된다.
변이 전이는 "재확인 필요"라는 정성 플래그로만 쓴다.

위협→변이빌드 연결이 없으면 variant_flag=None + note에 명시(감시 사각을
숨기지 않는다). 하루 1행/(위협) — 같은 날 중복 기록 안 함.
"""
from __future__ import annotations

import datetime as dt
import json

import db
from .biodefense_readiness import compute_readiness

VERDICT_HOLDS = "holds"
VERDICT_RECHECK = "recheck"
VERDICT_GAP = "gap"
VERDICT_UNKNOWN = "unknown"

# 변이 전이를 "최근"으로 보는 창. 이 안에 dominant_changed/new_clade가
# 있으면 covered여도 recheck.
RECENT_TRANSITION_DAYS = 7

# 위협명(소문자 정규화) → variant_ledger.build. 없는 위협은 변이 감시 미연결.
THREAT_BUILD_MAP = {
    "sars-cov-2": "ncov_open_global_6m",
    "sarscov2": "ncov_open_global_6m",
    "covid": "ncov_open_global_6m",
    "covid-19": "ncov_open_global_6m",
    "mpox": "mpox",
    "엠폭스": "mpox",
    "rsv": "rsv_a_genome",
    "rsv-a": "rsv_a_genome",
}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _recent_transition(build: str, now: dt.datetime) -> dict | None:
    """연결된 빌드의 최근 7일 내 전이(우세변경·신규출현) 최신 1건."""
    floor = (now - dt.timedelta(days=RECENT_TRANSITION_DAYS)).isoformat()
    with db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM variant_ledger
             WHERE build = ? AND transition IN ('dominant_changed', 'new_clade')
               AND observed_at >= ?
             ORDER BY observed_at DESC, id DESC LIMIT 1
            """,
            (build, floor),
        ).fetchone()
    return dict(row) if row else None


def record_daily_verdict(countermeasures: list[dict], threats: list[dict],
                         now: dt.datetime | None = None) -> list[dict]:
    """오늘의 매칭 판정을 위협별로 기록. 같은 날 이미 있으면 건너뛴다.

    countermeasures/threats는 compute_readiness와 같은 입력. 실데이터만
    기록한다(예시 데이터로 원장을 채우지 않음 — 호출자가 보장).
    """
    now = now or _now()
    today = now.date().isoformat()
    readiness = compute_readiness(countermeasures, threats)
    recorded: list[dict] = []
    for row in readiness["matrix"]:
        pathogen = row["pathogen"]
        status = row["coverage_status"]
        build = THREAT_BUILD_MAP.get((pathogen or "").strip().lower())
        flag = _recent_transition(build, now) if build else None
        if status == "uncovered":
            verdict = VERDICT_GAP
        elif status == "unrated":
            verdict = VERDICT_UNKNOWN
        elif flag:
            verdict = VERDICT_RECHECK
        else:
            verdict = VERDICT_HOLDS
        note = None
        if build is None:
            note = "연결된 변이 감시 없음"
        elif flag:
            note = (f"{flag['transition']}({flag['observed_at'][:10]}) — "
                    f"선언 효능 재확인 필요")
        with db.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO match_ledger
                    (verdict_date, pathogen, coverage_status, best_efficacy,
                     covering, variant_build, variant_flag, verdict, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (today, pathogen, status, row.get("best_declared_efficacy"),
                 json.dumps(row.get("covering_countermeasures", []),
                            ensure_ascii=False),
                 build,
                 json.dumps({"transition": flag["transition"],
                             "observed_at": flag["observed_at"],
                             "dominant_clade": flag.get("dominant_clade")},
                            ensure_ascii=False) if flag else None,
                 verdict, note),
            )
            conn.commit()
            if cur.rowcount != 1:
                continue
            rec = conn.execute("SELECT * FROM match_ledger WHERE id = ?",
                               (cur.lastrowid,)).fetchone()
        recorded.append(dict(rec))
    return recorded


def list_verdicts(days: int = 30, pathogen: str | None = None,
                  verdict: str | None = None, limit: int = 500) -> list[dict]:
    """최근 N일 판정 최신순."""
    floor = (_now().date() - dt.timedelta(days=days)).isoformat()
    query = "SELECT * FROM match_ledger WHERE verdict_date >= ?"
    params: list = [floor]
    if pathogen:
        query += " AND pathogen = ?"
        params.append(pathogen)
    if verdict:
        query += " AND verdict = ?"
        params.append(verdict)
    query += " ORDER BY verdict_date DESC, id DESC LIMIT ?"
    params.append(limit)
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


def latest_verdicts() -> list[dict]:
    """가장 최근 판정일의 전 위협 행 — 화면 '오늘의 판정'용."""
    with db.get_connection() as conn:
        day = conn.execute("SELECT MAX(verdict_date) AS d FROM match_ledger").fetchone()
    if not day or not day["d"]:
        return []
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM match_ledger WHERE verdict_date = ? ORDER BY pathogen",
            (day["d"],),
        )]

"""변이 상태원장 — 병원체 자체의 상태 전이를 1급 기록으로 남긴다 (2026-11-03).

## 왜 만들었나

BAIKAL-MOB은 7개 시스템의 **시스템 상태** 전이를 기록하고, lead-time-ledger는
예측의 전이를 기록한다. 그런데 정작 병원체 자체의 상태 전이 — 우세 계통이
바뀌고, 새 계통이 출현하는 순간 — 는 수집 주기 기록 속에 점(point)으로만
흩어져 있었다. "Nextstrain은 나무를 보여주고, 아이기론은 변이의 상태변화를
추적·채점한다" — 그 추적의 첫 장부다(최소형: 기록+전이 판정까지, VAR식
선언 대조 채점은 다음 단계).

## 무엇을 적나

매 수집 주기, Nextstrain 빌드마다 (우세 계통, 구성비, 신규 계통)을 한 행으로
적는다. 직전 주기와 비교해 전이를 판정한다:

- first_seen: 이 빌드의 첫 기록 (이전 상태를 지어내지 않는다)
- none: 우세 계통 동일 + 신규 계통 없음
- dominant_changed: 우세 계통이 바뀜
- new_clade: 우세는 같지만 신규 계통 출현

available=False(빌드 실패·갱신 정지) 주기는 적지 않는다 — 없는 관측을
"변화 없음"으로 적으면 거짓말이 된다. 대신 행이 비어 gap으로 보인다.
"""
from __future__ import annotations

import datetime as dt
import json

import db

TRANSITION_NONE = "none"
TRANSITION_FIRST_SEEN = "first_seen"
TRANSITION_DOMINANT_CHANGED = "dominant_changed"
TRANSITION_NEW_CLADE = "new_clade"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _last(build: str) -> dict | None:
    with db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM variant_ledger
             WHERE build = ?
             ORDER BY observed_at DESC, id DESC LIMIT 1
            """,
            (build,),
        ).fetchone()
    return dict(row) if row else None


def record_cycle(signals: dict, now: dt.datetime | None = None) -> list[dict]:
    """이번 수집 주기의 변이 스냅샷을 빌드별로 적고 전이를 판정한다.

    signals는 get_genomic_variant_signals()의 반환(빌드 slug → 분석 dict).
    관측 없는 빌드(available=False·우세 없음)는 건너뛴다. 반환은 이번 주기에
    적은 행들(new_clades는 파싱된 리스트) — 수집기 로그용.
    """
    now = now or _now()
    stamp = now.isoformat()
    recorded: list[dict] = []
    for build, v in (signals or {}).items():
        if not isinstance(v, dict) or not v.get("available"):
            continue
        dominant = v.get("dominant_clade")
        if dominant is None:
            continue
        new_clades = list(v.get("new_clades") or [])
        prev = _last(build)
        if prev is None:
            transition = TRANSITION_FIRST_SEEN
            prev_dominant = None
        elif prev.get("dominant_clade") != dominant:
            transition = TRANSITION_DOMINANT_CHANGED
            prev_dominant = prev.get("dominant_clade")
        elif new_clades:
            transition = TRANSITION_NEW_CLADE
            prev_dominant = prev.get("dominant_clade")
        else:
            transition = TRANSITION_NONE
            prev_dominant = prev.get("dominant_clade")
        with db.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO variant_ledger
                    (observed_at, build, label, dominant_clade,
                     dominant_share, n_recent, new_clades, prev_dominant,
                     transition, build_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (stamp, build, v.get("label") or build, dominant,
                 v.get("dominant_share"), v.get("n_recent_sequences"),
                 json.dumps(new_clades, ensure_ascii=False),
                 prev_dominant, transition, v.get("build_updated")),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM variant_ledger WHERE id = ?",
                               (cur.lastrowid,)).fetchone()
        entry = dict(row)
        entry["new_clades"] = new_clades
        recorded.append(entry)
    return recorded


def list_entries(build: str | None = None, limit: int = 200) -> list[dict]:
    """원장 행 최신순. new_clades는 JSON 문자열 그대로(호출자가 파싱)."""
    query = "SELECT * FROM variant_ledger"
    params: list = []
    if build:
        query += " WHERE build = ?"
        params.append(build)
    query += " ORDER BY observed_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


def list_transitions(limit: int = 200) -> list[dict]:
    """전이가 있었던 주기만(none 제외) 최신순."""
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(
            """
            SELECT * FROM variant_ledger
             WHERE transition != ?
             ORDER BY observed_at DESC, id DESC LIMIT ?
            """,
            (TRANSITION_NONE, limit),
        )]

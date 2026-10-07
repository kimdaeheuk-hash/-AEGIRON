"""시험용: 정답 경로가 '보고 있었다'는 상태를 만든다.

실제 침묵 채점은 정답 경로가 그 기간을 보고 있었을 때만 닫힌다(`ground_truth_channel.blind_reason`).
그 전제를 갖춘 상태에서 옛 계약(기한 내 선언 없음 → 닫음)을 시험하려면 어느 질병·나라와도 안 겹치는
실시간 선언 한 건을 판정 구간 안에 두면 된다.
"""
from __future__ import annotations

import datetime as dt

import db

SEED_EVENT_ID = "seed_atlantis_live"


def seed_live_channel(first_seen: dt.date, event_date: dt.date) -> None:
    """`first_seen` 에 처음 적재됐고 `event_date` 날짜를 가진 who_don 선언 한 건."""
    db.upsert_timeline_event(SEED_EVENT_ID, "Seed Atlantis 1999", event_date.isoformat(),
                             "who_statement", "시험용 시드", "WHO DON seed", "who_don")
    with db.get_connection() as conn:
        conn.execute("UPDATE outbreak_timeline SET created_at = ? WHERE event_id = ?",
                     (f"{first_seen.isoformat()}T00:00:00+00:00", SEED_EVENT_ID))
        conn.commit()

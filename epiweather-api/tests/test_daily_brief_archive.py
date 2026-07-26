"""일일 브리핑 자동 아카이브(㊲) — DB 저장/조회 왕복, 텔레그램 요약 포맷,
그리고 아카이브 조회 엔드포인트. 실제 네트워크·스케줄러는 안 돈다."""
from __future__ import annotations
from unittest.mock import patch

import db
from algorithms.notifier import format_daily_brief_message, notify_daily_brief


_BRIEF = {
    "date": "2026-07-25", "lang": "ko",
    "headline": "아이기론 역병예보 브리핑 · 속보 데스크: 브라질 뎅기 신호 주시",
    "summary": "오늘 총 2건의 위협 신호를 추적 중입니다.",
    "quiet_day": False,
    "format": {"name": "속보 데스크"},
    "segments": [
        {"kind": "threat", "lower_third": "뎅기열 · 브라질 · 경계"},
        {"kind": "promo", "lower_third": "아이기론 소개"},
    ],
}


def test_save_and_get_daily_brief_roundtrip(isolated_db):
    db.save_daily_brief("2026-07-25", "ko", _BRIEF)
    got = db.get_daily_brief("2026-07-25", "ko")
    assert got["headline"] == _BRIEF["headline"]
    assert db.get_daily_brief("2026-07-25", "en") is None  # 언어별로 분리 보관


def test_save_daily_brief_is_upsert(isolated_db):
    db.save_daily_brief("2026-07-25", "ko", _BRIEF)
    db.save_daily_brief("2026-07-25", "ko", {**_BRIEF, "headline": "갱신됨"})
    assert db.get_daily_brief("2026-07-25", "ko")["headline"] == "갱신됨"
    assert len(db.list_daily_briefs("ko")) == 1  # 같은 날짜는 1건만


def test_list_daily_briefs_desc_and_light(isolated_db):
    db.save_daily_brief("2026-07-24", "ko", {**_BRIEF, "date": "2026-07-24"})
    db.save_daily_brief("2026-07-25", "ko", _BRIEF)
    rows = db.list_daily_briefs("ko")
    assert [r["date"] for r in rows] == ["2026-07-25", "2026-07-24"]  # 최신순
    assert "headline" in rows[0] and "segments" not in rows[0]  # 가벼운 메타만


def test_format_daily_brief_message_includes_disclosure():
    msg = format_daily_brief_message(_BRIEF)
    assert "뎅기열 · 브라질 · 경계" in msg
    assert "공식 경보 아님" in msg


def test_notify_daily_brief_off_without_telegram(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notify_daily_brief(_BRIEF) is False


def test_notify_daily_brief_sends_when_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    with patch("algorithms.notifier.send_telegram_message", return_value=True) as m:
        assert notify_daily_brief(_BRIEF) is True
        m.assert_called_once()

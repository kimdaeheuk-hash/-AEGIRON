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


# ── 스케줄러가 지원 언어를 빠짐없이 만드는지 (2026-08-23) ─────────────────
# 발견: SUPPORTED_LANGS에 fr이 있고 홈페이지도 3개 언어로 나가는데, 스케줄러가
# "ko", "en"을 손으로 나열하고 있어 **fr 아카이브만 계속 0건**이었다. 프랑스어
# 방문자에게는 브리핑 아카이브가 영원히 비어 있는 페이지였다.

def _run(job, today="2026-08-23"):
    import asyncio
    asyncio.run(job(today))


def test_scheduler_generates_every_supported_language(isolated_db, monkeypatch):
    """★핵심★ 언어 목록을 손으로 적지 않고 SUPPORTED_LANGS를 따라야 한다."""
    import main
    from algorithms.daily_brief import SUPPORTED_LANGS

    monkeypatch.setattr(
        "algorithms.daily_brief.generate_daily_brief",
        lambda lang, api_key=None, today=None, **kw: {**_BRIEF, "lang": lang},
    )
    monkeypatch.setattr("algorithms.notifier.notify_daily_brief", lambda b: True)
    _run(main._run_daily_brief_job)

    for lang in SUPPORTED_LANGS:
        assert db.get_daily_brief("2026-08-23", lang) is not None, f"{lang} 브리핑이 없다"
    assert "fr" in SUPPORTED_LANGS      # 회귀 방지 — fr이 목록에서 빠지면 여기서 걸린다


def test_one_language_failure_does_not_kill_the_others(isolated_db, monkeypatch):
    """en이 터져도 ko·fr은 남아야 한다 — try 하나가 전부를 삼키면 안 된다."""
    import main

    def flaky(lang, api_key=None, today=None, **kw):
        if lang == "en":
            raise RuntimeError("Claude 429")
        return {**_BRIEF, "lang": lang}

    monkeypatch.setattr("algorithms.daily_brief.generate_daily_brief", flaky)
    monkeypatch.setattr("algorithms.notifier.notify_daily_brief", lambda b: True)
    _run(main._run_daily_brief_job)

    assert db.get_daily_brief("2026-08-23", "ko") is not None
    assert db.get_daily_brief("2026-08-23", "fr") is not None   # en 뒤에 오는데도 살아남음
    assert db.get_daily_brief("2026-08-23", "en") is None


def test_telegram_skipped_when_korean_failed(isolated_db, monkeypatch):
    """한국어가 실패하면 발송을 건너뛴다 — 캡틴이 못 읽는 알림을 보내면 안 된다."""
    import main

    def no_korean(lang, api_key=None, today=None, **kw):
        if lang == "ko":
            raise RuntimeError("실패")
        return {**_BRIEF, "lang": lang}

    sent = []
    monkeypatch.setattr("algorithms.daily_brief.generate_daily_brief", no_korean)
    monkeypatch.setattr("algorithms.notifier.notify_daily_brief",
                        lambda b: sent.append(b) or True)
    _run(main._run_daily_brief_job)

    assert sent == []                                    # 다른 언어로 대신 보내지 않는다
    assert db.get_daily_brief("2026-08-23", "fr") is not None   # 저장은 계속됨


def test_missing_language_is_retried_on_next_tick(isolated_db, monkeypatch):
    """ko만 보고 '오늘 끝'으로 치면 빠진 언어는 영영 안 채워진다."""
    import main

    db.save_daily_brief("2026-08-23", "ko", _BRIEF)      # ko만 있는 상태
    ran = []
    monkeypatch.setattr(main, "_run_daily_brief_job",
                        lambda today: _noop(ran, today))
    monkeypatch.setattr(main.dt, "datetime", _FixedUtc)
    import asyncio
    asyncio.run(main._maybe_run_daily_brief())

    assert ran == ["2026-08-23"], "fr·en이 없는데도 재시도하지 않았다"


async def _noop(ran, today):
    ran.append(today)


class _FixedUtc(__import__("datetime").datetime):
    @classmethod
    def utcnow(cls):
        return cls(2026, 8, 23, 23, 0, 0)      # UTC 23시 = 생성 시각 이후

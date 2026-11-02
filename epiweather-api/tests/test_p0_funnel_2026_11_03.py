"""P0 — 스캔 깔때기 진단(scan_funnel).

원장에 아무것도 안 열리면, 그게 '신호 없음'인지 '신뢰도 없음'인지
'문턱 미달'인지가 안 보였다. 단계별 개수를 낸다. 읽기만 하고 안 쓴다.
"""
from __future__ import annotations

import datetime as dt
import os

os.environ.setdefault("EPIWEATHER_SCHEDULER", "off")

import main
from algorithms.lead_time_ledger import list_entries, scan_funnel

UTC = dt.timezone.utc


def _at(y, m, d):
    return dt.datetime(y, m, d, tzinfo=UTC)


def _signal(dbmod, disease, iso3, day, signal_type="급증", trust=0.9):
    return dbmod.create_extracted_signal(
        source="msf", disease=disease, location=iso3, signal_type=signal_type,
        severity=["spike"], symptom=None, transmission=None, source_trust=trust,
        signal_date=day, raw_text="t", country_iso3=iso3)


def test_funnel_counts_each_stage(isolated_db, monkeypatch):
    """주사위→날짜→질병→신뢰도 단계별 개수가 맞는다."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")                    # 통과
    _signal(dbmod, "에볼라", "COD", "2019-06-10")                    # 날짜 밖
    _signal(dbmod, "에볼라", "COD", "2026-09-01", trust=0.0)         # 신뢰도 0
    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY",
                        {"급증": 95})

    out = scan_funnel(now=_at(2026, 9, 3))

    assert out["scanned"] == 3
    assert out["no_date"] == 1 and out["no_trust"] == 1
    assert out["groups"] == 1
    assert out["groups_above_threshold"] == 1
    assert out["top_groups"][0]["score"] == 95.0
    assert out["threshold"] == 80


def test_funnel_shows_near_miss(isolated_db, monkeypatch):
    """문턱 미달이어도 최고 그룹 점수가 보인다 — '왜 0건인지'의 답."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")
    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY",
                        {"급증": 10})

    out = scan_funnel(now=_at(2026, 9, 3))

    assert out["groups"] == 1 and out["groups_above_threshold"] == 0
    assert out["top_groups"][0]["score"] == 10.0
    assert out["top_groups"][0]["above_threshold"] is False


def test_funnel_writes_nothing(isolated_db):
    """진단은 읽기 전용 — 원장에 흔적을 남기지 않는다."""
    dbmod = isolated_db
    _signal(dbmod, "에볼라", "COD", "2026-09-01")

    scan_funnel(now=_at(2026, 9, 3))

    assert list_entries() == []


def test_funnel_empty_db(isolated_db):
    """신호가 없어도 깨지지 않고 0으로 말한다."""
    out = scan_funnel(now=_at(2026, 9, 3))
    assert out["scanned"] == 0 and out["groups"] == 0
    assert out["top_groups"] == []


# ── 첫 실측 알림 ──────────────────────────────────────────────────
def test_notify_quiet_when_unconfigured(monkeypatch):
    """채널 없으면 조용히 False — 크래시·스팸 없음."""
    from algorithms.notifier import notify_lead_time_hit

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_OPS_CHAT_ID", raising=False)
    hit = {"disease": "에볼라", "lead_days": 5, "event_id": "ebola_cod"}
    assert notify_lead_time_hit(hit) is False
    assert notify_lead_time_hit(hit, first_ever=True) is False


def test_notify_sends_to_ops_chat(monkeypatch):
    """설정되면 운영 대화로, 첫 건은 '첫 실측'으로."""
    from algorithms import notifier

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_OPS_CHAT_ID", "ops-1")
    sent: dict = {}

    class _R:
        status_code = 200

    def fake_post(url, json=None, timeout=None):
        sent["url"] = url
        sent["chat"] = json["chat_id"]
        sent["text"] = json["text"]
        return _R()

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    monkeypatch.setattr(notifier, "_record_alert_attempt",
                        lambda *a, **k: None)
    hit = {"disease": "에볼라", "lead_days": 5, "event_id": "ebola_cod"}
    assert notifier.notify_lead_time_hit(hit, first_ever=True) is True
    assert sent["chat"] == "ops-1"
    assert "첫 실측" in sent["text"] and "+5일" in sent["text"]
    assert notifier.notify_lead_time_hit(hit) is True
    assert "첫 실측" not in sent["text"]


def test_notify_escapes_values(monkeypatch):
    """질병명에 HTML이 섞여도 경보가 통째로 안 가지 않는다."""
    from algorithms import notifier

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    sent: dict = {}

    class _R:
        status_code = 200

    def fake_post(url, json=None, timeout=None):
        sent["text"] = json["text"]
        return _R()

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    monkeypatch.setattr(notifier, "_record_alert_attempt",
                        lambda *a, **k: None)
    hit = {"disease": "<b>에볼라</b>", "lead_days": 3, "event_id": "x"}
    assert notifier.notify_lead_time_hit(hit) is True
    assert "<b>에볼라</b>" not in sent["text"]


def test_collector_wires_first_hit_notice():
    """수집기가 실측→알림을 잇는다."""
    import inspect

    import collector

    src = inspect.getsource(collector)
    assert "notify_lead_time_hit" in src
    assert "first_ever" in src


def test_endpoint_returns_summary_entries_and_funnel(isolated_db, monkeypatch):
    """GET /api/lead-time-ledger 응답에 세 키가 다 있다(소켓 없이 직접 호출)."""
    from algorithms.lead_time_ledger import open_crossing

    dbmod = isolated_db
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    _signal(dbmod, "에볼라", "COD", today)
    monkeypatch.setattr("algorithms.country_risk.SIGNAL_TYPE_SEVERITY",
                        {"급증": 95})
    open_crossing("에볼라", "COD", 95.0, 80.0, [1], now=_at(2026, 9, 1))

    body = main.lead_time_ledger()

    assert body["summary"]["measured_events"] == 0
    assert body["summary"]["open_crossings"] == 1
    assert body["entries"][0]["disease"] == "에볼라"
    assert body["funnel"]["scanned"] == 1
    assert body["funnel"]["groups_above_threshold"] == 1
    assert body["funnel"]["threshold"] == 80

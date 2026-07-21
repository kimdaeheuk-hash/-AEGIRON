"""Telegram 실시간 알림 — 토큰 미설정 시 안전하게 꺼지는지, 메시지 포맷이
맞는지 확인. 실제 Telegram API 호출은 하지 않음(네트워크 mock)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.notifier import (
    telegram_configured, send_telegram_message, format_alert_message, notify_new_alerts,
)


def test_telegram_not_configured_without_env_vars(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert telegram_configured() is False


def test_telegram_configured_when_both_env_vars_present(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    assert telegram_configured() is True


def test_send_telegram_message_returns_false_without_config(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert send_telegram_message("test") is False


def test_send_telegram_message_returns_true_on_200(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    with patch("algorithms.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        assert send_telegram_message("test") is True


def test_send_telegram_message_returns_false_on_network_error(monkeypatch):
    import requests
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    with patch("algorithms.notifier.requests.post", side_effect=requests.RequestException("boom")):
        assert send_telegram_message("test") is False


def test_format_alert_message_includes_tier_icons_and_scores():
    alerts = [
        {"tier": "critical", "label": "종합 위험도 급상승", "score": 92.0},
        {"tier": "high", "label": "행동신호 급증", "score": 82.0},
    ]
    msg = format_alert_message(alerts)
    assert "🔴" in msg
    assert "🟠" in msg
    assert "종합 위험도 급상승" in msg
    assert "92.0" in msg


def test_notify_new_alerts_noop_when_empty_list(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    with patch("algorithms.notifier.requests.post") as mock_post:
        assert notify_new_alerts([]) is False
        mock_post.assert_not_called()


def test_notify_new_alerts_noop_when_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("algorithms.notifier.requests.post") as mock_post:
        result = notify_new_alerts([{"tier": "critical", "label": "x", "score": 95.0}])
        assert result is False
        mock_post.assert_not_called()

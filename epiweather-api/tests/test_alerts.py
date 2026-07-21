"""경보 파이프라인 — 같은 경보가 매시간 재계산돼도 Telegram 알림은 "오늘
이 source로 처음 잡힌" critical/high 건에만 나가는지 확인(반복 재통보 방지)."""
from __future__ import annotations
from unittest.mock import patch

from algorithms.alerts import refresh_alerts


def _fake_candidates(score: float):
    return [{
        "source": "gai:overall", "label": "종합 위험도", "score": score,
        "evidence": ["근거1"],
    }]


def test_new_critical_alert_triggers_notification(isolated_db):
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=_fake_candidates(95.0)), \
         patch("algorithms.alerts.notify_new_alerts") as mock_notify:
        refresh_alerts("2026-07-21")

    assert mock_notify.call_count == 1
    sent = mock_notify.call_args[0][0]
    assert len(sent) == 1
    assert sent[0]["source"] == "gai:overall"
    assert sent[0]["tier"] == "critical"


def test_same_ongoing_alert_does_not_renotify_on_second_refresh(isolated_db):
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=_fake_candidates(95.0)), \
         patch("algorithms.alerts.notify_new_alerts") as mock_notify:
        refresh_alerts("2026-07-21")  # 1차: 신규 → 알림
        refresh_alerts("2026-07-21")  # 2차: 같은 날 같은 source 재계산 → 알림 없어야 함

    assert mock_notify.call_count == 2
    assert len(mock_notify.call_args_list[0][0][0]) == 1  # 1차: 신규 1건
    assert len(mock_notify.call_args_list[1][0][0]) == 0  # 2차: 신규 0건


def test_medium_tier_alert_does_not_trigger_notification(isolated_db):
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=_fake_candidates(72.0)), \
         patch("algorithms.alerts.notify_new_alerts") as mock_notify:
        refresh_alerts("2026-07-21")

    assert mock_notify.call_args[0][0] == []  # medium은 신규여도 알림 대상 아님

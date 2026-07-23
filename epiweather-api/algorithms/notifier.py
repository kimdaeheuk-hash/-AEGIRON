"""실시간 사람 알림 — Telegram Bot API.

경보가 DB에만 쌓이고 대시보드를 열어야만 보이면, "빨리 알린다"는 역병예보의
핵심 가치가 실제로는 안 지켜진다. 채널 선택 기준(2026-07 조사):
  - 이메일: 확인 지연이 큼(대시보드 pull 방식과 다를 바 없음)
  - Slack/Discord: 팀 워크스페이스 가입이 필요해 일반 대중 알림엔 무거움
  - WhatsApp Business API: 대화 1건당 과금(월 수만 원~수십만 원), 승인 절차 필요
  - Telegram Bot API: 완전 무료·@BotFather로 30초 발급·승인 없음, 채널 하나에
    최대 20만 명 구독 가능, 중앙아시아·중동·구소련권 등 아이기론이 닿아야 하는
    지역에서 이미 실사용률이 높음 — 그래서 이걸 1순위로 채택.

TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID 둘 다 없으면 조용히 꺼진 상태로 동작한다
(KDCA_API_KEY 등 다른 선택적 연동과 동일한 패턴) — 알림 미설정이 경보
파이프라인 자체를 막으면 안 되므로, 전송 실패도 예외를 밖으로 던지지 않는다.

향후 확장: 🔴 critical 등급만 SMS(Twilio 등)로 이중발송하면 데이터망이 약한
지역까지 닿을 수 있음 — 유료 계정·전화번호 등록이 필요해 이번 스코프에서는
제외하고 설계만 이 구조를 따르면 되도록 남겨둠(notify_new_alerts 시그니처가
채널 추가에 열려있음).
"""
from __future__ import annotations
import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = 10

TIER_ICON = {"critical": "🔴", "high": "🟠"}


def telegram_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_telegram_message(text: str) -> bool:
    """설정 안 됐으면 조용히 False. 네트워크 실패도 예외 없이 False로 흡수."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        resp = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def format_alert_message(new_alerts: list[dict]) -> str:
    lines = [f"🚨 <b>아이기론 신규 경보 {len(new_alerts)}건</b>"]
    for a in new_alerts:
        icon = TIER_ICON.get(a["tier"], "🟡")
        lines.append(f"{icon} {a['label']} — {a['score']}점")
    return "\n".join(lines)


def notify_new_alerts(new_alerts: list[dict]) -> bool:
    """critical/high 신규 경보를 한 번에 정리해서 Telegram으로 전송.
    new_alerts가 비어있거나 채널 미설정이면 아무 것도 안 하고 False."""
    if not new_alerts or not telegram_configured():
        return False
    return send_telegram_message(format_alert_message(new_alerts))


def notify_source_degradation(failing_sources: list[str]) -> bool:
    """데이터 소스가 연속 실패로 죽었을 때 운영자에게 즉시 통보(㉔) — '조기경보
    시스템이 조용히 눈이 머는' 상황을 사람에게 알리는 게 목적. 소스 장애를
    조용히 넘기지 않고 실제로 경보를 낸다."""
    if not failing_sources or not telegram_configured():
        return False
    lines = ["⚠️ <b>아이기론 데이터 소스 장애 감지</b>",
             f"다음 소스가 연속 실패로 중단됨(신호 유실 위험): {', '.join(failing_sources)}"]
    return send_telegram_message("\n".join(lines))

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


# 경보 채널의 능력 장부 키. 조기경보 시스템에서 '알림이 조용히 안 나가는 것'은
# 소스가 죽는 것보다 위험하다 — 소스는 /api/status에 degraded로 뜨지만, 알림
# 실패는 알림으로 알려줄 수가 없다(알림이 고장난 거니까). 그래서 기록해 둔다.
ALERT_CAPABILITY = "telegram_alerting"


def _record_alert_attempt(ok: bool, detail: str | None = None) -> None:
    try:
        from .capability_ledger import record
        record(ALERT_CAPABILITY, ok=ok, detail=detail,
               endpoint="api.telegram.org")
    except Exception:
        pass      # 기록 실패가 알림 전송을 막지 않는다


def send_telegram_message(text: str) -> bool:
    """설정 안 됐으면 조용히 False. 네트워크 실패도 예외 없이 False로 흡수.

    다만 '조용히'가 영원하면 안 된다 — 토큰만 꽂혀 있고 전송은 매번 실패하는
    상태를 아무도 모르게 된다. 시도 결과를 능력 장부에 남겨 /api/status에서
    '설정됨'과 '실제로 보내진 적 있음'이 구분되게 한다."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False      # 설정 자체가 없는 건 실패로 세지 않는다(안 켠 것뿐)
    try:
        resp = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        _record_alert_attempt(False, f"{type(e).__name__}: {e}")
        return False
    ok = resp.status_code == 200
    _record_alert_attempt(ok, None if ok else f"HTTP {resp.status_code}")
    return ok


def format_alert_message(new_alerts: list[dict]) -> str:
    lines = [f"🚨 <b>아이기론 신규 경보 {len(new_alerts)}건</b>"]
    for a in new_alerts:
        icon = TIER_ICON.get(a["tier"], "🟡")
        lines.append(f"{icon} {a['label']} — {a['score']}점")
        # 경보에 NPI 반사실 브리핑이 붙어 있으면(자동연결) 한 줄로 노출 —
        # "그래서 뭘 하라고?"에 답하는 의사결정 라인.
        if a.get("npi_summary"):
            lines.append(f"   {a['npi_summary']}")
    return "\n".join(lines)


def notify_new_alerts(new_alerts: list[dict]) -> bool:
    """critical/high 신규 경보를 한 번에 정리해서 Telegram으로 전송.
    new_alerts가 비어있거나 채널 미설정이면 아무 것도 안 하고 False."""
    if not new_alerts or not telegram_configured():
        return False
    return send_telegram_message(format_alert_message(new_alerts))


def _fmt_num(v, *, whole: bool = False) -> str:
    """숫자를 사람이 읽게. 없으면 '—' — 0으로 채우지 않는다.

    whole=True 는 **사람 수처럼 쪼갤 수 없는 값**에 쓴다. 예보 엔진은 외삽이라
    4885.5 같은 값을 내는데, 그대로 "4,885.5명" 으로 쓰면 말이 안 된다.
    """
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        if whole:
            return f"{round(v):,}"
        if isinstance(v, float):
            return f"{v:,.1f}".rstrip("0").rstrip(".")
        return f"{v:,}"
    return str(v)


def _special_lines(brief: dict) -> list[str]:
    """특수 섹션을 텔레그램 한 덩어리로. **매일 값이 달라지는 부분이다.**

    예전 메시지는 헤드라인·요약·위협목록만 보냈는데, 그 셋이 전부 순위표에서
    나오는 값이라 순위가 안 바뀌면 **7일 내내 같은 문장**이 나갔다.
    (2026-08-26 실측: 연속한 날 헤드라인 유사도 88~89%)
    """
    out: list[str] = []
    for sec in brief.get("special_sections") or []:
        rows = sec.get("rows") or []
        head = f"\n{sec.get('icon', '•')} <b>{sec.get('title', '')}</b>"
        body = [sec.get("lead")] if sec.get("lead") else []

        if sec.get("id") == "silence":
            for r in rows[:2]:
                body.append(
                    f"· {r.get('label') or r.get('metric')}: {_fmt_num(r.get('latest'))}"
                    f" (평소 {_fmt_num(r.get('history_avg'))})")
        elif sec.get("id") == "polar":
            for r in rows[:2]:
                body.append(
                    f"· {r.get('name')} 해빙 {r.get('thaw_days_30d')}/30일"
                    f" · 압력 {_fmt_num(r.get('pressure'))}")
            for c in (sec.get("citations") or [])[:2]:
                body.append(f"· “{c}”")
        elif sec.get("id") == "forecast":
            # 사람 수를 세는 지표를 앞세운다 — 우리 순위가 아니라 사람 이야기여야 한다
            for r in [x for x in rows if x.get("counts_people")][:2]:
                body.append(
                    f"· {r.get('label') or r.get('metric')}: {_fmt_num(r.get('current'), whole=True)}명"
                    f" → 14일 후 {_fmt_num(r.get('in_14d'), whole=True)}명")
        elif sec.get("id") == "unexplained":
            for r in rows[:2]:
                where = r.get("location") or r.get("source") or "?"
                when = r.get("signal_date")
                body.append(f"· {when} {where}" if when else f"· {where}")

        if body:
            out.append(head)
            out.extend(body)
    return out


def format_daily_brief_message(brief: dict) -> str:
    """일일 브리핑을 텔레그램용 짧은 뉴스로 요약. 정직성 고지 포함."""
    lines = [f"📰 <b>{brief.get('headline', '아이기론 역병예보')}</b>"]
    summary = brief.get("summary")
    if summary:
        lines.append(summary)
    # 위협 목록은 순위표라 순위가 안 바뀌면 매일 똑같다. 텔레그램에는 상위 2건만
    # 싣고 나머지 수만 알린다 — 같은 줄이 다섯 개씩 반복되면 아래 특수 섹션이 묻힌다.
    threats = [s["lower_third"] for s in brief.get("segments", [])
               if s.get("kind") == "threat" and s.get("lower_third")]
    for t in threats[:2]:
        lines.append(f"• {t}")
    if len(threats) > 2:
        lines.append(f"• 외 {len(threats) - 2}건 추적 중")

    lines.extend(_special_lines(brief))

    lines.append("\n<i>공식 경보 아님 · AI 자동생성 · 관찰 등급은 경보가 아닙니다</i>")
    return "\n".join(lines)


def notify_daily_brief(brief: dict) -> bool:
    """스케줄러가 매일 만든 브리핑을 텔레그램으로 발송. 채널 미설정이면 False.
    조용한 날도 '오늘은 조용함'으로 그대로 보낸다(가짜 위기 X)."""
    if not brief or not telegram_configured():
        return False
    return send_telegram_message(format_daily_brief_message(brief))


def notify_source_degradation(failing_sources: list[str]) -> bool:
    """데이터 소스가 연속 실패로 죽었을 때 운영자에게 즉시 통보(㉔) — '조기경보
    시스템이 조용히 눈이 머는' 상황을 사람에게 알리는 게 목적. 소스 장애를
    조용히 넘기지 않고 실제로 경보를 낸다."""
    if not failing_sources or not telegram_configured():
        return False
    lines = ["⚠️ <b>아이기론 데이터 소스 장애 감지</b>",
             f"다음 소스가 연속 실패로 중단됨(신호 유실 위험): {', '.join(failing_sources)}"]
    return send_telegram_message("\n".join(lines))


def format_source_health_message(pending: dict) -> str:
    """죽은 소스는 '며칠째 몇 시간째'까지 적는다 — 한 줄짜리 '장애 감지'는
    이틀 뒤에 다시 봐도 그게 아직 진행 중인지 알 수가 없었다."""
    lines: list[str] = []
    degraded = pending.get("degraded") or []
    recovered = pending.get("recovered") or []
    if degraded:
        lines.append(f"⚠️ <b>아이기론 데이터 소스 {len(degraded)}개 중단</b>")
        for d in degraded:
            stale = d.get("staleness_hours")
            if stale is None:
                age = "마지막 성공 기록 없음"
            elif stale >= 24:
                age = f"{stale / 24:.1f}일째 데이터 없음"
            else:
                age = f"{stale:.0f}시간째 데이터 없음"
            fails = d.get("consecutive_failures") or 0
            lines.append(f"🔴 {d['source']} — {age} (연속 실패 {fails}회)")
        lines.append("\n<i>이 소스가 담당하는 지역·질병은 지금 '조용한 게 아니라 안 보이는' 상태입니다.</i>")
    if recovered:
        if lines:
            lines.append("")
        lines.append(f"✅ <b>복구됨</b>: {', '.join(recovered)}")
    return "\n".join(lines)


def notify_source_health(pending: dict) -> bool:
    """소스 중단/복구를 한 통으로 통보. 보낼 게 없거나 채널 미설정이면 False.
    반환값이 곧 '전송 성공' — 호출부는 True일 때만 통보 도장을 찍어야 한다
    (실패했는데 도장을 찍으면 다음 주기에 조용해져 알림을 잃는다)."""
    if not telegram_configured():
        return False
    if not (pending.get("degraded") or pending.get("recovered")):
        return False
    return send_telegram_message(format_source_health_message(pending))

# -*- coding: utf-8 -*-
"""서버 밖에서 하는 생존 감시 (2026-10-19, 캡틴 승인 ①).

## 왜

BAIKAL 운영 알림(⑤)은 Railway 서버 **안에서** 보낸다. 서버가 죽거나 매시 주기가 멈추면
알림도 같이 멈춘다 — 가장 큰 고장이 가장 조용하다. 이 스크립트는 GitHub Actions 에서
매시간 돌아 서버를 바깥에서 본다(.github/workflows/liveness.yml).

## 무엇을 보는가

- `/health` 가 200 · status ok 인가                   → 아니면 '서버 응답 없음'
- `/api/baikal` 의 마지막 관측이 오래되지 않았는가(stale) → 오래됐으면 '매시 주기 멈춤 의심'
- 웹사이트 첫 화면이 200 인가                          → 아니면 '웹사이트 응답 없음'

## 언제 보내는가 — 바뀐 순간만

GitHub 워크플로는 상태를 기억하지 못해서, 직전 실행들의 결과(성공/실패)를 인자로 받는다.
- 이번에 실패 · 직전 성공(또는 기록 없음) → 🔴 한 통
- 계속 실패 → RENOTIFY_EVERY 회마다 한 통(몇 시간째인지 적어서)
- 이번에 성공 · 직전 실패 → 🟢 복구 한 통
값은 HTML 이스케이프한다. 이 알림은 시스템 운영 상태이지 감염병 경보가 아니다.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request

RENOTIFY_EVERY = 6          # 매시 실행 기준 6시간마다 '아직 멈춤'
TIMEOUT = 30


def _get(url: str, attempts: int = 3, wait: float = 20.0) -> tuple[int | None, str]:
    """(HTTP 상태, 본문). 연결 자체가 안 되면 (None, 사유). 일시 오류는 몇 번 다시 묻는다."""
    last = (None, "")
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "aegiron-liveness"}),
                                        timeout=TIMEOUT) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = (e.code, "")
        except Exception as e:                      # 연결 실패·타임아웃
            last = (None, type(e).__name__)
        if i < attempts - 1:
            time.sleep(wait)
    return last


def evaluate(health: tuple[int | None, str], baikal: tuple[int | None, str],
             site: tuple[int | None, str] | None) -> list[str]:
    """문제 목록(사람이 읽는 문장). 비어 있으면 정상."""
    problems: list[str] = []
    code, body = health
    ok = False
    if code == 200:
        try:
            ok = json.loads(body).get("status") == "ok"
        except ValueError:
            ok = False
    if not ok:
        problems.append(f"운영 서버 응답 없음 (/health {'HTTP ' + str(code) if code else body or '연결 실패'})")
    else:
        code, body = baikal
        try:
            data = json.loads(body) if code == 200 else None
        except ValueError:
            data = None
        if data is None:
            problems.append(f"BAIKAL 상태를 못 읽음 (/api/baikal {'HTTP ' + str(code) if code else body or '연결 실패'})")
        elif data.get("available") and data.get("stale"):
            age = data.get("snapshot_age_minutes")
            problems.append("매시 주기 멈춤 의심 — BAIKAL 마지막 관측 "
                            + (f"{age}분 전" if age is not None else "시각 모름"))
        # available=False(첫 관측 전)는 배포 직후 정상 상태라 문제로 세지 않는다.
    if site is not None:
        code, body = site
        if code != 200:
            problems.append(f"웹사이트 응답 없음 ({'HTTP ' + str(code) if code else body or '연결 실패'})")
    return problems


def decide(problems: list[str], prior_failures: int) -> str | None:
    """보낼 텔레그램 본문, 보낼 게 없으면 None. prior_failures = 직전까지 연속 실패 횟수."""
    foot = "\n\n<i>서버 밖(GitHub Actions)에서 본 운영 상태 — 감염병 경보가 아님 · 상세: /baikal</i>"
    if problems:
        if prior_failures == 0:
            head = "🔴 <b>외부 생존 감시: 이상</b>"
        elif (prior_failures + 1) % RENOTIFY_EVERY == 0:
            head = f"🔴 <b>외부 생존 감시: {prior_failures + 1}회 연속 이상</b>"
        else:
            return None
        return head + "\n" + "\n".join(f"· {html.escape(p, quote=False)}" for p in problems) + foot
    if prior_failures > 0:
        return f"🟢 <b>외부 생존 감시: 복구</b>\n· {prior_failures}회 연속 이상 뒤 정상 응답" + foot
    return None


def send(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_OPS_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("::warning::텔레그램 시크릿 없음 — 알림 없이 작업 상태(빨간불)로만 남김")
        return False
    data = json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML",
                       "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status == 200
    except Exception as e:
        print(f"::warning::텔레그램 전송 실패: {type(e).__name__}")
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--site")
    ap.add_argument("--prior-failures", type=int, default=0)
    args = ap.parse_args(argv)
    api = args.api.rstrip("/")
    problems = evaluate(_get(f"{api}/health"), _get(f"{api}/api/baikal?transitions=1"),
                        _get(args.site) if args.site else None)
    print("문제 없음" if not problems else "\n".join(problems))
    text = decide(problems, args.prior_failures)
    if text:
        print("텔레그램:", "전송됨" if send(text) else "전송 안 됨")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

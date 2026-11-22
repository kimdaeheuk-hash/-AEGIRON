# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""서버 밖에서 하는 생존 감시.

## 왜

서버가 죽거나 매시 주기가 멈추면 서버 안에서 보내는 로그·알림도 같이 멈춘다 —
가장 큰 고장이 가장 조용하다. 이 스크립트는 GitHub Actions 에서 매시간 돌아
서버를 바깥에서 본다(.github/workflows/liveness.yml).

## 무엇을 보는가

- `/health` 가 200 · status ok 인가                   → 아니면 '서버 응답 없음'
- `/api/status` 의 collector_silent_hours 가 STALL_HOURS 를 넘었는가 → 넘으면 '매시 주기 멈춤 의심'
- 웹사이트 첫 화면이 200 인가                          → 아니면 '웹사이트 응답 없음'

## 어떻게 알리는가 (2026-11-22: 텔레그램 제거)

문제가 있으면 문장으로 찍고 **종료 코드 1**로 끝낸다 — GitHub Actions 작업이 빨간불이
되고, GitHub 자체 알림이 저장소 소유자에게 간다. 별도 전송 채널을 두지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 30
# 수집은 매시 정각. 두 주기를 연달아 못 돌았을 때만 멈춤으로 본다(한 번 늦는 것은 배포·재시작에도 난다).
STALL_HOURS = 2.0


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


def evaluate(health: tuple[int | None, str], status: tuple[int | None, str],
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
        code, body = status
        try:
            data = json.loads(body) if code == 200 else None
        except ValueError:
            data = None
        if not isinstance(data, dict):
            problems.append(f"운영 상태를 못 읽음 (/api/status {'HTTP ' + str(code) if code else body or '연결 실패'})")
        else:
            silent = (data.get("source_health") or {}).get("collector_silent_hours")
            if isinstance(silent, (int, float)) and silent > STALL_HOURS:
                problems.append(f"매시 주기 멈춤 의심 — 수집 마지막 기록 {silent}시간 전")
            # None(첫 주기 전·기록 없음)은 배포 직후 정상 상태라 문제로 세지 않는다.
    if site is not None:
        code, body = site
        if code != 200:
            problems.append(f"웹사이트 응답 없음 ({'HTTP ' + str(code) if code else body or '연결 실패'})")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--site")
    args = ap.parse_args(argv)
    api = args.api.rstrip("/")
    problems = evaluate(_get(f"{api}/health"), _get(f"{api}/api/status"),
                        _get(args.site) if args.site else None)
    if problems:
        print("\n".join(problems))
        return 1
    print("문제 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())

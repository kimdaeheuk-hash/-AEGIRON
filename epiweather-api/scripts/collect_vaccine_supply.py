# -*- coding: utf-8 -*-
"""WHO 사전적격성(PQ) 백신 목록 스냅샷을 손으로 갱신한다.

## 이 파일은 이제 껍데기다 (2026-09-04)

수집·검증·저장 로직은 운영에서도 부를 수 있어야 해서 옮겼다:

    algorithms/reference_fetch.py       원본에서 받아 payload 를 만든다
    algorithms/reference_snapshots.py   검증하고 원자적으로 저장한다

옮긴 이유: 이 스크립트가 **아무도 안 부르는 CLI 였다.** 그래서 두 기준 파일이
2026-09-02 에 멈춘 채 발할라의 두 축을 떠받치고 있었다. 이제 주간작업이
`refresh_due()` 로 묵은 것만 새로 받는다. 이 스크립트는 그걸 지금 당장
돌리고 싶을 때 쓴다.

## 자료 — WHO Prequalified Vaccines

UN 기관이 조달하려면 통과해야 하는 목록이다. 백신마다 제조사와 감독 규제기관이
붙어 있어서 "어느 나라가 이 백신을 만들 수 있는가" 를 볼 수 있다.
실측(2026-09-02): 284건 · 56종 · 제조사 51곳 · 규제기관 20곳.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.reference_snapshots import refresh, snapshot_status  # noqa: E402


def main() -> None:
    before = snapshot_status("vaccine_supply")
    print(f"현재: {before['record_count']}건 · {before['snapshot_date']} "
          f"({before['age_days']}일 전)" if before["present"] else "현재: 파일 없음")

    result = refresh("vaccine_supply")
    if not result["refreshed"]:
        # 검증에 걸려 거부된 것도 실패다. 기존 파일은 그대로 남는다.
        raise SystemExit(f"갱신 안 됨 — {result['reason']}")

    print(f"갱신 완료: {result['record_count']}건 · {result['snapshot_date']}")


if __name__ == "__main__":
    main()

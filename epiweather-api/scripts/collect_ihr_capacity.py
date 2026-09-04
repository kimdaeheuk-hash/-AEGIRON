# -*- coding: utf-8 -*-
"""WHO 국제보건규칙(IHR) 자가평가 15개 역량 스냅샷을 손으로 갱신한다.

## 왜 스냅샷인가

이 자료는 **1년에 한 번** 갱신된다. 매 호출마다 WHO 를 15번 때리는 건 낭비이고,
WHO 가 잠깐 안 되는 날 국가 비교가 통째로 사라진다. 항공노선(`flight_routes_
by_country.json`)과 같은 방식으로 파일에 떠 놓고 쓴다.

    python scripts/collect_ihr_capacity.py

## ★ 240행 중 국가는 193개다 ★

WHO OData 는 국가 행 사이에 지역·전세계 집계행을 섞어 준다(UNREGION 40 ·
REGION 6 · GLOBAL 1). `SpatialDimType == "COUNTRY"` 로 거르지 않으면 국가 수를
240 으로 잘못 세고, "아프리카 지역" 을 한 나라처럼 순위에 넣게 된다.
(이 거르기는 algorithms/reference_fetch.py 로 옮겼다.)

## 이 파일은 이제 껍데기다 (2026-09-04)

수집·검증·저장은 운영에서도 부를 수 있어야 해서 옮겼다:

    algorithms/reference_fetch.py       원본에서 받아 payload 를 만든다
    algorithms/reference_snapshots.py   검증하고 원자적으로 저장한다

옮긴 이유: 이 스크립트가 **아무도 안 부르는 CLI 였다.** 그래서 파일이
2026-09-02 에 멈춘 채 발할라의 국가 역량 축을 떠받치고 있었다. 이제 주간작업이
묵은 것만 새로 받는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.reference_snapshots import refresh, snapshot_status  # noqa: E402


def main() -> None:
    before = snapshot_status("ihr_capacity")
    print(f"현재: {before['record_count']}개국 · {before['snapshot_date']} "
          f"({before['age_days']}일 전)" if before["present"] else "현재: 파일 없음")

    result = refresh("ihr_capacity")
    if not result["refreshed"]:
        raise SystemExit(f"갱신 안 됨 — {result['reason']}")

    print(f"갱신 완료: {result['record_count']}개국 · {result['snapshot_date']}")


if __name__ == "__main__":
    main()

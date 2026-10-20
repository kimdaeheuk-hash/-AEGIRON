"""국가별 대비 역량 — "이 나라는 스스로를 몇 점이라 했는가" (2026-09-02).

## 왜 만들었나

캡틴: *"발할라 더 크게 확장할 수 있는 방법 있어?"*

발할라의 계산기는 튼튼한데 **국가 축이 없었다.** 위협 8종이 코드에 박혀 있고
나라는 한국 하나뿐이라, "다른 나라 대비 우리가 어디쯤인가" 를 못 냈다. 국가
바이오안보 기획 문서는 그 비교 없이는 쓰이지 않는다.

## 자료 — WHO 국제보건규칙 자가평가(SPAR)

194개국 × 15개 역량 × 2021~2023. 무료·키 불필요를 실측 확인(2026-09-02).
연 1회 갱신이라 `scripts/collect_ihr_capacity.py` 로 떠 놓고 파일에서 읽는다.

실측한 2023년 분포(0~100):

    실험실        한국 100 · 세계 중앙값 71 · 40점 이하 16개국
    감시          한국 100 · 세계 중앙값 80 · 40점 이하 10개국
    감염예방관리    한국 100 · 세계 중앙값 60 · 40점 이하 53개국
    인수공통감염병  한국 100 · 세계 중앙값 60 · 40점 이하 57개국

## ★★ 이 숫자는 자가평가다 ★★

**나라가 자기 점수를 스스로 매긴다.** WHO 가 검증한 값이 아니다. 인도는 감시를
100점, 네팔은 50점이라고 **스스로 적어냈다.**

그래서 이 모듈은 점수를 "역량" 이라고 부르지 않고 **"신고한 점수"** 라고 부른다.
`is_self_assessed=True` 를 모든 응답에 넣는다. 이 한 줄을 빼면 자가평가를 측정치로
파는 것이 되고, 그건 정부 문서에서 가장 먼저 지적당하는 종류의 잘못이다.

## ★ 합산 점수를 만들지 않는다 ★

15개를 평균 내면 "한국 99.5점" 같은 게 나오고, 그 숫자가 문서에 실린다. 그런데
실험실 100점과 방사선 비상 100점을 더해서 나누는 근거가 우리에게 없다. 대신
**세계 중앙값보다 낮은 역량이 몇 개인가** 를 센다 — 이건 셀 수 있는 사실이다.
"""
from __future__ import annotations

import json
import statistics
from functools import lru_cache
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent / "reference" / "ihr_capacity.json"

# 세계 중앙값보다 이만큼 낮으면 "뒤처진다" 고 부른다. 중앙값보다 1점 낮은 걸
# 격차라고 하면 절반의 나라가 매년 격차가 된다.
BEHIND_MARGIN = 10


def _current_path() -> Path:
    """주간작업이 볼륨에 받은 새 사본이 있으면 그쪽(reference_snapshots.newest)."""
    from .reference_snapshots import newest
    return newest(REFERENCE)


@lru_cache(maxsize=1)
def _snapshot() -> dict | None:
    try:
        return json.loads(_current_path().read_text(encoding="utf-8"))
    except Exception:                                # noqa: BLE001
        return None


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason, "is_self_assessed": True}


@lru_cache(maxsize=16)
def world_medians(year: int | None = None) -> dict[str, float] | None:
    """역량별 세계 중앙값. 평균이 아니라 중앙값이다 — 0점 몇 나라에 끌려가지 않는다."""
    snap = _snapshot()
    if not snap:
        return None
    year = str(year or snap["latest_year"])
    buckets: dict[str, list[int]] = {}
    for scores in snap["scores"].values():
        for code, value in (scores.get(year) or {}).items():
            buckets.setdefault(code, []).append(value)
    return {code: statistics.median(vals) for code, vals in buckets.items() if vals}


def country_capacity(iso3: str, year: int | None = None) -> dict:
    """한 나라가 **스스로 신고한** 15개 역량. 수록이 없으면 0이 아니라 모름이다."""
    snap = _snapshot()
    if not snap:
        return _unavailable(
            f"기준 파일이 없다: {REFERENCE.name} "
            "(scripts/collect_ihr_capacity.py 로 만든다)")

    iso3 = (iso3 or "").strip().upper()
    year = year or snap["latest_year"]
    scores = (snap["scores"].get(iso3) or {}).get(str(year))
    if not scores:
        # ★ 수록이 없는 것을 0점으로 접지 않는다 ★ 그러면 신고를 안 한 나라가
        # 세계 최악으로 보고된다. 실제로 신고를 거른 나라가 매년 있다.
        return _unavailable(f"{iso3} 의 {year}년 신고 기록이 없다")

    medians = world_medians(year) or {}
    names = snap["capacities"]
    rows, behind = [], []
    for code in sorted(names):
        if code not in scores:
            continue
        value, median = scores[code], medians.get(code)
        is_behind = median is not None and value < median - BEHIND_MARGIN
        if is_behind:
            behind.append(names[code])
        rows.append({
            "code": code, "name_ko": names[code],
            "reported_score": value,
            "world_median": median,
            "behind_world": is_behind,
        })

    return {
        "available": True,
        "iso3": iso3,
        "year": year,
        "capacities": rows,
        # ★ 합산 점수를 만들지 않는다 ★ 셀 수 있는 사실만 낸다.
        "behind_world_count": len(behind),
        "behind_world": behind,
        "capacity_count": len(rows),
        "is_self_assessed": True,
        "source": snap["source"],
        "snapshot_date": snap["snapshot_date"],
        "limits": [
            "각국이 스스로 매긴 점수다. WHO 가 검증한 값이 아니다.",
            "100점이 무결점이라는 뜻이 아니다 — 자기 기준을 다 채웠다는 신고일 뿐이다.",
            "15개를 합쳐 하나의 국가 점수를 만들지 않는다. 실험실과 방사선 비상을 "
            "더해서 나눌 근거가 없다.",
            "신고가 없는 나라는 0점이 아니라 '모름' 이다.",
            "연 1회 갱신 자료다. 지금 그 나라의 상태가 아니라 신고 시점의 상태다.",
        ],
    }


def weakest_countries(code: str, limit: int = 10, year: int | None = None) -> dict:
    """한 역량에서 낮게 신고한 나라들. **위험 순위가 아니다.**"""
    snap = _snapshot()
    if not snap:
        return _unavailable(f"기준 파일이 없다: {REFERENCE.name}")
    code = (code or "").strip().upper()
    if code not in snap["capacities"]:
        return _unavailable(f"없는 역량 코드: {code}")

    year = year or snap["latest_year"]
    rows = [{"iso3": iso3, "reported_score": s[str(year)][code]}
            for iso3, s in snap["scores"].items()
            if str(year) in s and code in s[str(year)]]
    rows.sort(key=lambda r: (r["reported_score"], r["iso3"]))
    return {
        "available": True,
        "code": code, "name_ko": snap["capacities"][code], "year": year,
        "countries": rows[:limit],
        "reporting_country_count": len(rows),
        "world_median": (world_medians(year) or {}).get(code),
        "is_self_assessed": True,
        "is_risk_ranking": False,
        "limits": [
            "스스로 낮게 적은 나라 목록이다. 정직하게 신고한 나라가 불리하게 보인다.",
            "위험 순위가 아니다 — 여기 없는 나라가 안전하다는 뜻이 아니고, "
            "신고를 아예 안 한 나라는 애초에 목록에 오르지 않는다.",
        ],
    }

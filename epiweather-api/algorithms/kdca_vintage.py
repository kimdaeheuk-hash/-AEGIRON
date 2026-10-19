"""질병청 주간 값의 성숙도 측정 — 한국 주간 예측(⑥)의 1단계 (2026-10-19).

## 왜 예측보다 측정이 먼저인가

주간 추세 예측(weekly_forecast)은 일본 표본감시만 쓴다. 질병청 주간 신고를 뺀 이유가 그
모듈에 적혀 있다 — **새 주가 일부만 채워져 들어오고 나중에 늘어난다.** 그러면 '다음 주에
늘었나'의 정답이 언제 보느냐에 따라 달라진다. 성숙 기간을 모르는 채로 예측을 시작하면
채점 기록이 신고 지연을 재는 숫자가 된다(일찍 본 주는 늘 '감소'로 보인다).

그래서 먼저 잰다. 매시 수집기가 받는 최근 4주 × 질병별 값을 **값이 바뀐 순간만**
`kdca_vintages` 에 남기고, 충분히 지난 주(MATURE_DAYS 이상)에 대해:

    처음 본 합계 · 처음 본 뒤 7일 · 14일 시점 합계  ÷  지금 합계

를 낸다. 이 비율이 언제 1 에 붙는지가 '정답으로 써도 되는 나이'다. 그 값을 보고 나서
한국 계열 예측을 켠다(캡틴 결정).

## 정직성 경계선

- 합계는 위험군(KDCA_NOTABLE)만 — 지수 kdca_weekly_total 과 같은 정의.
- 지금 합계가 0 인 주는 비율을 내지 않는다(나눌 수 없음 — 0 으로 쓰지 않는다).
- 성숙 판정이 가능한 주가 없으면 '측정 중'이라고 쓴다. 수집기 최근 4주 창 밖으로 나간 주는
  더 늘어나도 못 본다 — 그래서 '지금 합계'는 '우리가 마지막으로 본 값'이다(로그에 적는다).
"""
from __future__ import annotations

import datetime as dt
import statistics

MATURE_DAYS = 21          # 처음 본 뒤 이만큼 지난 주만 성숙도 계산에 넣는다
CHECKPOINTS = (0, 7, 14)  # 처음 본 시점 기준 며칠 뒤 값을 볼지


def record(kdca_weekly: dict | None, now: dt.datetime) -> int:
    """이번 주기 값 중 (질병, 주) 마지막 기록과 다른 것만 남긴다. 남긴 행 수."""
    import db

    if not kdca_weekly:
        return 0
    added = 0
    with db.get_connection() as conn:
        for disease, by_period in kdca_weekly.items():
            for period, value in (by_period or {}).items():
                if value is None:
                    continue
                row = conn.execute(
                    "SELECT value FROM kdca_vintages WHERE disease=? AND period=? "
                    "ORDER BY seen_at DESC LIMIT 1", (disease, period)).fetchone()
                if row is not None and row["value"] == int(value):
                    continue
                conn.execute("INSERT OR IGNORE INTO kdca_vintages (disease, period, value, seen_at) "
                             "VALUES (?, ?, ?, ?)", (disease, period, int(value), now.isoformat()))
                added += 1
        conn.commit()
    return added


def _total_at(rows: list[dict], when: dt.datetime, notable: set[str]) -> int:
    """when 시점에 우리가 알던 위험군 합계 — 질병마다 그 시각 이전의 마지막 값."""
    latest: dict[str, int] = {}
    for r in rows:
        if r["disease"] in notable and dt.datetime.fromisoformat(r["seen_at"]) <= when:
            latest[r["disease"]] = r["value"]
    return sum(latest.values())


def maturity_report(now: dt.datetime, notable: set[str] | None = None) -> dict:
    import db
    from .kdca_anomaly import KDCA_NOTABLE

    notable = notable if notable is not None else set(KDCA_NOTABLE)
    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT disease, period, value, seen_at FROM kdca_vintages ORDER BY seen_at")]
    by_period: dict[str, list[dict]] = {}
    for r in rows:
        by_period.setdefault(r["period"], []).append(r)

    ratios = {d: [] for d in CHECKPOINTS}
    mature, young, zero = [], 0, 0
    for period, prow in sorted(by_period.items()):
        first = min(dt.datetime.fromisoformat(r["seen_at"]) for r in prow)
        if (now - first).days < MATURE_DAYS:
            young += 1
            continue
        final = _total_at(prow, now, notable)
        if final <= 0:
            zero += 1
            continue
        mature.append(period)
        for d in CHECKPOINTS:
            ratios[d].append(_total_at(prow, first + dt.timedelta(days=d), notable) / final)
    return {
        "mature_periods": mature, "young_periods": young, "zero_total_periods": zero,
        "median_ratio": {d: (round(statistics.median(v), 3) if v else None) for d, v in ratios.items()},
        "mature_days": MATURE_DAYS,
    }


def report_line(rep: dict) -> str:
    n = len(rep["mature_periods"])
    if not n:
        return (f"🇰🇷 질병청 주간 값 성숙도: 측정 중 — {rep['mature_days']}일 지난 주 0개"
                f"(쌓이는 중 {rep['young_periods']}개) · 한국 주간 예측은 이 값을 보고 켠다")
    m = rep["median_ratio"]
    pct = lambda v: "—" if v is None else f"{v:.0%}"
    return (f"🇰🇷 질병청 주간 값 성숙도: 성숙 판정 {n}주 — 처음 본 합계는 마지막으로 본 값의 "
            f"{pct(m[0])}(중앙) · 7일 뒤 {pct(m[7])} · 14일 뒤 {pct(m[14])} · "
            f"수집 창(최근 4주) 밖 변동은 못 봄")

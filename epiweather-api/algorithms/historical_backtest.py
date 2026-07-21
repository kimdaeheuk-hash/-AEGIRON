"""실제 발병 이력 기반 백테스트 — 인수인계서 Part5 확장(⑳).

기존 POST /api/backtest(Stage 5)는 make_season()이 만든 합성 데이터로
Farrington/z-score/EWMA "탐지 방법론" 자체의 성능을 비교한다 — 방법 비교에는
유효하지만, "아이기론이 실제로 며칠 먼저 알았는가"는 증명하지 못한다(가짜
계절 데이터라서).

이 모듈은 main.py._seed_known_timelines()가 심어둔 실제 발병 milestone(WHO
PHEIC 선언 등 진짜 날짜, knowledge_graph.py Phase14가 이미 같은 데이터로
지식그래프의 lead_days 추정치를 검증하는 데 씀)을 기준점 삼아, 같은 기간
extracted_signals(⑦, NLP 구조화 추출로 실제 수집된 신호)가 공식 선언보다
며칠 먼저(또는 늦게) critical/high 임계치를 넘었는지 계산한다.

합성 데이터가 아니라 실제 수집 파이프라인이 쌓은 기록을 그대로 쓰는 게
핵심 — extracted_signals에 매칭되는 신호가 없으면(수집 전이거나 아직
미수집) 억지로 채우지 않고 "검증 불가"로 정직하게 표시한다.
"""
from __future__ import annotations
import datetime as dt

import db
from .event_dedup import normalize_disease
from .country_risk import SIGNAL_TYPE_SEVERITY
from .alerts import classify_tier
from .knowledge_graph import _DECLARATION_MILESTONE_KEYS

LOOKBACK_DAYS_BEFORE_DECLARATION = 60  # 선언일 이전 이만큼까지만 신호를 훑는다
LOOKAHEAD_DAYS_AFTER_DECLARATION = 7   # 선언 직후 신호(사후 확인용)도 소폭 포함


def _daily_severity_series(disease_key: str, start: dt.date, end: dt.date) -> dict[str, float]:
    """disease_key(normalize_disease 정규화명)에 매칭되는 실제 extracted_signals를
    날짜별로 묶어 신뢰도가중 평균 심각도를 계산 — event_dedup.dedupe_events()와
    같은 산식(신뢰도가중 평균)을 날짜 단위로 쪼갠 것."""
    records = db.list_extracted_signals(limit=2000)
    by_day: dict[str, list[tuple[float, float]]] = {}
    for r in records:
        if normalize_disease(r.get("disease")) != disease_key:
            continue
        day = r.get("signal_date") or (r.get("extracted_at") or "")[:10]
        if not day:
            continue
        try:
            d = dt.date.fromisoformat(day)
        except ValueError:
            continue
        if not (start <= d <= end):
            continue
        severity = SIGNAL_TYPE_SEVERITY.get(r["signal_type"], 40)
        by_day.setdefault(day, []).append((severity, r["source_trust"]))

    result: dict[str, float] = {}
    for day, pairs in by_day.items():
        weight_sum = sum(t for _, t in pairs)
        if weight_sum:
            result[day] = round(sum(s * t for s, t in pairs) / weight_sum, 1)
    return result


def backtest_event(event_id: str) -> dict:
    """특정 발병 이벤트에 대해 '실제 신호가 임계치를 넘은 날' vs '실제 공식
    선언일'을 비교. 근거 데이터가 없는 단계마다 이유를 명시하고 verified=False."""
    timeline = db.get_timeline(event_id)
    milestones = timeline.get("milestones", [])
    if not milestones:
        return {"event_id": event_id, "verified": False, "reason": "outbreak_timeline에 등록된 이벤트 없음"}

    declaration = next(
        (m for m in milestones if m["milestone"] in _DECLARATION_MILESTONE_KEYS), None,
    )
    if declaration is None:
        return {
            "event_id": event_id, "verified": False,
            "reason": "공식 선언급 마일스톤이 없음(status_update·year_start 같은 정기 갱신만 있음)",
        }

    declaration_date = dt.date.fromisoformat(declaration["event_date"])
    start = declaration_date - dt.timedelta(days=LOOKBACK_DAYS_BEFORE_DECLARATION)
    end = declaration_date + dt.timedelta(days=LOOKAHEAD_DAYS_AFTER_DECLARATION)
    disease_key = normalize_disease(timeline["event_name"])

    severity_by_day = _daily_severity_series(disease_key, start, end)
    if not severity_by_day:
        return {
            "event_id": event_id, "verified": False,
            "reason": "이 기간 extracted_signals에 매칭되는 실제 신호가 없음(수집 전이거나 아직 미수집)",
            "declaration_date": declaration_date.isoformat(),
        }

    first_high_day = next(
        (day for day in sorted(severity_by_day)
         if classify_tier(severity_by_day[day]) in ("critical", "high")),
        None,
    )

    if first_high_day is None:
        return {
            "event_id": event_id, "verified": True, "would_have_alerted": False,
            "declaration_date": declaration_date.isoformat(),
            "signal_days_checked": len(severity_by_day),
            "reason": "이 기간 신호는 있었지만 critical/high 임계치를 넘은 날이 없음",
        }

    detected_date = dt.date.fromisoformat(first_high_day)
    lead_days = (declaration_date - detected_date).days  # 양수 = 선언보다 먼저 감지

    return {
        "event_id": event_id,
        "event_name": timeline["event_name"],
        "verified": True,
        "would_have_alerted": True,
        "declaration_date": declaration_date.isoformat(),
        "declaration_milestone": declaration["milestone"],
        "first_high_severity_signal_date": first_high_day,
        "lead_days": lead_days,
        "signal_days_checked": len(severity_by_day),
    }


def backtest_all_known_events() -> dict:
    """outbreak_timeline에 등록된 모든 이벤트를 백테스트하고 요약 통계를 낸다."""
    event_ids = [e["event_id"] for e in db.list_timeline_events()]
    results = [backtest_event(eid) for eid in event_ids]
    verified = [r for r in results if r.get("verified") and r.get("would_have_alerted")]
    lead_days_list = [r["lead_days"] for r in verified]

    return {
        "results": results,
        "summary": {
            "events_checked": len(results),
            "events_with_verified_lead_time": len(verified),
            "mean_lead_days": round(sum(lead_days_list) / len(lead_days_list), 1) if lead_days_list else None,
        },
    }

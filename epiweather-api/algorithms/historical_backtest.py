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
from .alerts import MEDIUM, HIGH, CRITICAL
from .knowledge_graph import _DECLARATION_MILESTONE_KEYS
from .benchmark_baselines import compare_to_bluedot

LOOKBACK_DAYS_BEFORE_DECLARATION = 60  # 선언일 이전 이만큼까지만 신호를 훑는다

# ── 백테스트가 '경보로 넘어갔다'를 판정하는 기준선(로컬 코드리뷰 후속 ㉗) ──
# lead_days는 이 기준선 위에서만 의미가 있으므로, 숫자를 낼 때 항상 기준선을
# 함께 명시한다. 주 판정은 high(≥80). anomaly_engine의 z-score 임계값과는
# 무관 — 백테스트는 extracted_signals의 '사건 유형'(급증/신규발생 등, 범주형)에
# 매긴 SIGNAL_TYPE_SEVERITY를 신뢰도가중 평균한 점수에 classify_tier를 쓴다.
# 사건 유형은 수치 시계열이 아니라 z-score(평균/표준편차)를 적용할 대상이
# 아니다 — 그래서 여기선 '단일 임계값이 정답인 척'하는 대신, 여러 임계값에서의
# lead_days를 함께 보여주는 민감도 분석으로 '숫자가 임계값에 얼마나 흔들리는지'를
# 정직하게 드러낸다.
PRIMARY_THRESHOLD_TIER = "high"
PRIMARY_THRESHOLD_SCORE = HIGH  # 80
SEVERITY_MODEL = "SIGNAL_TYPE_SEVERITY(사건유형 범주형 심각도) 신뢰도가중 평균"


def _first_day_crossing(severity_by_day: dict[str, float], min_score: float) -> str | None:
    """severity가 min_score 이상으로 처음 올라간 날(오름차순 첫 날). 없으면 None."""
    return next(
        (day for day in sorted(severity_by_day) if severity_by_day[day] >= min_score),
        None,
    )


def _threshold_sensitivity(severity_by_day: dict[str, float], declaration_date) -> dict:
    """medium/high/critical 세 임계값 각각에서 lead_days를 계산 — '3일 빨랐다'가
    임계값을 바꿔도 안 흔들리는지(robust) 심사자가 직접 볼 수 있게 한다."""
    out = {}
    for name, score in (("medium", MEDIUM), ("high", HIGH), ("critical", CRITICAL)):
        day = _first_day_crossing(severity_by_day, score)
        if day is None:
            out[name] = {"threshold_score": score, "detected": False, "lead_days": None}
        else:
            lead = (declaration_date - dt.date.fromisoformat(day)).days
            out[name] = {
                "threshold_score": score, "detected": True,
                "first_signal_date": day, "lead_days": lead,
            }
    return out


def _detection_baseline() -> dict:
    """모든 lead_days 출력에 부착 — 이 숫자가 '어느 기준선 위에서' 나왔는지 명시.
    기준선 없이 lead_days를 인용하지 못하게 하는 게 목적."""
    return {
        "severity_model": SEVERITY_MODEL,
        "primary_threshold_tier": PRIMARY_THRESHOLD_TIER,
        "primary_threshold_score": PRIMARY_THRESHOLD_SCORE,
        "note": "lead_days는 이 기준선 위에서만 유효. 임계값 민감도는 "
                "threshold_sensitivity 참고(단일 임계값이 정답이 아님을 명시).",
    }
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
    """특정 발병 이벤트를 백테스트하고, 벤치마크(㉕)가 있으면 블루닷 대비 비교를
    붙인다. 아이기론 실측 선행일수가 없으면(그 시점 데이터 부재) 블루닷 비교는
    '실측 없음, 목표 기준선만 표기'로 정직하게 나온다."""
    result = _backtest_event_core(event_id)
    aegiron_lead = result.get("lead_days") if result.get("would_have_alerted") else None
    comparison = compare_to_bluedot(event_id, aegiron_lead)
    if comparison is not None:
        result["bluedot_comparison"] = comparison
    return result


def _backtest_event_core(event_id: str) -> dict:
    """'실제 신호가 임계치를 넘은 날' vs '실제 공식 선언일'을 비교.
    근거 데이터가 없는 단계마다 이유를 명시하고 verified=False."""
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

    sensitivity = _threshold_sensitivity(severity_by_day, declaration_date)
    first_high_day = _first_day_crossing(severity_by_day, PRIMARY_THRESHOLD_SCORE)

    if first_high_day is None:
        return {
            "event_id": event_id, "verified": True, "would_have_alerted": False,
            "declaration_date": declaration_date.isoformat(),
            "signal_days_checked": len(severity_by_day),
            "detection_baseline": _detection_baseline(),
            "threshold_sensitivity": sensitivity,
            "reason": f"이 기간 신호는 있었지만 주 임계값(high≥{PRIMARY_THRESHOLD_SCORE})을 넘은 날이 없음 "
                      "— 더 낮은 임계값 결과는 threshold_sensitivity 참고",
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
        # lead_days를 기준선 없이 인용하지 못하게 항상 부착(㉗)
        "detection_baseline": _detection_baseline(),
        "threshold_sensitivity": sensitivity,
    }


def backtest_all_known_events() -> dict:
    """outbreak_timeline에 등록된 모든 이벤트를 백테스트하고 요약 통계를 낸다.
    벤치마크(㉕)가 있는 이벤트는 블루닷 대비 비교도 요약에 모은다."""
    event_ids = [e["event_id"] for e in db.list_timeline_events()]
    results = [backtest_event(eid) for eid in event_ids]
    verified = [r for r in results if r.get("verified") and r.get("would_have_alerted")]
    lead_days_list = [r["lead_days"] for r in verified]

    benchmarked = [r["bluedot_comparison"] for r in results if "bluedot_comparison" in r]
    measured_head_to_head = [c for c in benchmarked if c["aegiron_lead_days"] is not None]

    return {
        "results": results,
        "summary": {
            "events_checked": len(results),
            "events_with_verified_lead_time": len(verified),
            "mean_lead_days": round(sum(lead_days_list) / len(lead_days_list), 1) if lead_days_list else None,
            "bluedot_benchmarked_events": len(benchmarked),
            "bluedot_head_to_head_measured": len(measured_head_to_head),
            "bluedot_note": "블루닷 비교 중 aegiron_lead_days가 실측된 건만 실제 head-to-head. "
                            "코로나 등 아이기론 부재 시점 사건은 '목표 기준선'으로만 표기(실측 없음).",
        },
    }

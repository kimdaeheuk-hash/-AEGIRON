"""경보 피로 방지 엔진 — 인수인계서 Part5 ⑥.

경보 500개 = 아무도 안 봄. GAI(①)·부정적 공간 감시(⑤)가 만들어내는 후보들을
등급별로 분류하고 일일 캡을 적용해, 정말 봐야 할 것만 상위에 남긴다.

  Critical (90점↑) → 즉시 알림, 최대 3개/일
  High     (80점↑) → 일 1회 요약, 최대 5개
  Medium   (70점↑) → 주간 리포트(캡 없음 — 그냥 쌓아둠)
  Low      (70점↓) → 로그만 저장 (후보로도 만들지 않음)

캡 초과분은 버리지 않고 suppressed=1로 표시해 DB에 남긴다(나중에 "오늘 몇 건이
억제됐는지" 확인 가능). 같은 source가 같은 날 반복되면 갱신만 하므로, 수집기가
매시간 돌아도 캡 카운트가 부풀지 않는다.
"""
from __future__ import annotations
import datetime as dt

import db
from .gai import compute_gai
from .negative_space import scan_negative_space
from .unexplained import scan_unexplained

CRITICAL = 90
HIGH = 80
MEDIUM = 70

DAILY_CAPS = {"critical": 3, "high": 5}  # medium·low는 캡 없음
CANDIDATE_FLOOR = 50  # 이보다 낮은 점수는 후보로도 안 올림 (잡음 방지)
DASHBOARD_TOP_N = 5


def classify_tier(score: float) -> str:
    if score >= CRITICAL:
        return "critical"
    if score >= HIGH:
        return "high"
    if score >= MEDIUM:
        return "medium"
    return "low"


def _gai_overall_evidence(gai_result: dict) -> list[str]:
    """GAI 종합 점수의 근거 — 가장 크게 기여한 계층·지표를 실제 수치로 나열.
    "근거 없는 숫자는 기관이 사용 못 함"(인수인계서 Part5 ⑫) — 결재 올릴 수
    있는 형태를 목표로 함."""
    all_metrics = []
    for layer_key, layer in gai_result["layers"].items():
        for m in layer["metrics"]:
            all_metrics.append((layer["label"], m))
    all_metrics.sort(key=lambda x: -x[1]["trusted_score"])

    evidence = []
    for label, m in all_metrics[:3]:
        evidence.append(
            f"{label} · {m['metric']} — 원시 이상도 {m['raw_score']}점 "
            f"(출처신뢰도 {m['trust']} 반영 후 {m['trusted_score']}점)"
        )
    n_free = gai_result.get("sample_size", {}).get("free_sources")
    if n_free is not None:
        evidence.append(f"누적 표본 {n_free}건 기준")
    return evidence


def collect_candidate_alerts(today: str) -> list[dict]:
    """GAI 층별 신호원 + 부정적 공간 감시 + 설명불가 신호를 경보 후보로 변환."""
    candidates = []

    gai_result = compute_gai()
    if gai_result["gai"] is not None and gai_result["gai"] >= CANDIDATE_FLOOR:
        candidates.append({
            "source": "gai:overall",
            "label": "Global Anomaly Index 종합",
            "score": gai_result["gai"],
            "evidence": _gai_overall_evidence(gai_result),
        })
    for layer_key, layer in gai_result["layers"].items():
        for m in layer["metrics"]:
            if m["trusted_score"] >= CANDIDATE_FLOOR:
                candidates.append({
                    "source": f"gai:{layer_key}.{m['metric']}",
                    "label": f"{layer['label']} · {m['metric']}",
                    "score": m["trusted_score"],
                    "evidence": [
                        f"원시 이상도(과거 대비 z-score 환산) {m['raw_score']}점",
                        f"출처신뢰도 {m['trust']} 반영 후 최종 {m['trusted_score']}점",
                        f"{layer['label']} 계층 가중치 {layer['weight']}",
                    ],
                })

    for a in scan_negative_space()["alerts"]:
        severity = round((1 - a["drop_ratio"]) * 100, 1) if a.get("drop_ratio") is not None else 70.0
        if severity >= CANDIDATE_FLOOR:
            candidates.append({
                "source": f"negative_space:{a['layer']}.{a['metric']}",
                "label": f"{a['label']} · {a['metric']} 보고 급감",
                "score": severity,
                "evidence": [
                    f"최신값 {a['latest']} (과거 평균 {a['history_avg']}의 {a.get('drop_ratio', '—')}배)",
                    "2014년 기니 에볼라 사례 — 보고 급감이 실제론 의료체계 붕괴 신호였음",
                    "신호 증가가 아니라 '보고가 끊긴 것' 자체를 경보 대상으로 봄",
                ],
            })

    # 설명불가 신호는 문서 요구사항대로 무조건 critical(100점)으로 즉시 올림 —
    # 단, 능동 검색(unexplained_cluster)만 대상으로 함. who_wpro 같은 일반
    # 지역동향 요약은 질병명이 없는 게 흔해서, 전체 source를 다 포함하면
    # "원인불명 클러스터"가 아니라 그냥 막연한 요약문까지 critical로 오탐함.
    # 오늘 추출된 것만 후보로 올림(아니면 과거 발견이 매일 영원히 재후보로 뜸).
    for a in scan_unexplained()["alerts"]:
        if a["source"] != "unexplained_cluster":
            continue
        if (a["extracted_at"] or "")[:10] != today:
            continue
        key = a["location"] or a["raw_disease_text"] or a["source"]
        candidates.append({
            "source": f"unexplained:{key}",
            "evidence": [
                f"위치: {a['location'] or '불명'}",
                f"모델이 추출한 원문 질병명: {a['raw_disease_text'] or '불명'} — 기존 알려진 패턴과 불일치 판정",
                f"원문 발췌: {(a['raw_text'] or '')[:120]}",
            ],
            "label": f"설명불가 신호 · {a['location'] or '지역불명'} ({a['raw_disease_text'] or '질병불명'})",
            "score": 100.0,
        })

    return candidates


def refresh_alerts(today: str | None = None) -> dict:
    """후보를 분류·저장하고, 등급별 일일 캡을 적용해 오늘자 경보 상태를 반환."""
    today = today or dt.date.today().isoformat()

    for c in collect_candidate_alerts(today):
        tier = classify_tier(c["score"])
        db.upsert_alert(today, c["source"], tier, c["label"], c["score"], evidence=c.get("evidence"))

    rows = db.list_alerts(today)  # score 내림차순

    by_tier: dict[str, list[dict]] = {"critical": [], "high": [], "medium": [], "low": []}
    for r in rows:
        by_tier[r["tier"]].append(r)

    visible_ids: list[int] = []
    suppressed_ids: list[int] = []
    tier_summary = {}
    for tier, items in by_tier.items():
        cap = DAILY_CAPS.get(tier)
        shown = items if cap is None else items[:cap]
        hidden = [] if cap is None else items[cap:]
        visible_ids += [i["id"] for i in shown]
        suppressed_ids += [i["id"] for i in hidden]
        tier_summary[tier] = {"cap": cap, "total": len(items), "suppressed": len(hidden)}

    db.set_suppressed(visible_ids, False)
    db.set_suppressed(suppressed_ids, True)

    visible_rows = [r for r in rows if r["id"] in visible_ids]
    dashboard_top = visible_rows[:DASHBOARD_TOP_N]
    hidden_count = len(visible_rows) - len(dashboard_top)

    return {
        "date": today,
        "dashboard": {
            "top": [
                {
                    "label": r["label"], "tier": r["tier"], "score": r["score"],
                    "source": r["source"], "evidence": r.get("evidence", []),
                }
                for r in dashboard_top
            ],
            "hidden_count": hidden_count,
        },
        "tier_summary": tier_summary,
    }

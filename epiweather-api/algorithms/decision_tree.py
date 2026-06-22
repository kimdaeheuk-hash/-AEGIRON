"""
위험 수준별 자동 대응 권고 의사결정 트리.

LLM 호출 전에 규칙 기반으로 즉시 권고를 생성.
Rt, 유입일, 민간 선행일, 병상 초과일 등을 입력으로 받아
KDCA 위기경보 단계와 대응 우선순위를 결정.
"""
from __future__ import annotations


def classify_alert_level(rt: float, arrival_day: int, hosp_overflow_days: int) -> str:
    """
    KDCA 위기경보 4단계 분류.
    실효재생산수(Rt) + 유입일 + 병상초과 복합 판단.
    """
    if hosp_overflow_days > 30 or rt >= 2.0:
        return "심각(Red)"
    if hosp_overflow_days > 0 or rt >= 1.5:
        return "경계(Orange)"
    if rt >= 1.0 or arrival_day <= 7:
        return "주의(Yellow)"
    return "관심(Blue)"


def get_priority_actions(
    rt: float,
    alert_level: str,
    civic_lead_days: int,
    arrival_day: int,
    saved_lives: int,
    threat: str,
) -> dict:
    """
    위험 수준별 즉시 대응 우선순위 3가지 자동 생성.
    규칙 기반 → LLM 호출 전 빠른 참조용.
    """
    actions: list[dict] = []
    reasoning: list[str] = []

    # ── 1순위: 전파 차단 여부 ────────────────────────────────
    if rt >= 1.5:
        actions.append({
            "priority": 1,
            "category": "전파차단",
            "action": "즉시 사회적 거리두기 격상 + 대규모 집회 금지",
            "rationale": f"Rt={rt:.2f} > 1.5: 전파 가속 구간. 지금 개입하지 않으면 2주 후 환자 수 {round(rt**2, 1)}배.",
            "urgency": "즉시(24시간 내)",
        })
        reasoning.append(f"Rt {rt:.2f}로 전파 가속 중")
    elif rt >= 1.0:
        actions.append({
            "priority": 1,
            "category": "전파억제",
            "action": "검역·접촉자 추적 강화, 마스크 착용 의무화 검토",
            "rationale": f"Rt={rt:.2f}: 1 이상으로 지속 확산. 선제 억제로 Rt<1 목표.",
            "urgency": "3일 내",
        })
        reasoning.append(f"Rt {rt:.2f}로 완만한 확산 중")
    else:
        actions.append({
            "priority": 1,
            "category": "조기탐지 유지",
            "action": "민간 신호 모니터링 지속, 검역 현행 유지",
            "rationale": f"Rt={rt:.2f} < 1: 현재 차단 성공. 재확산 징후 조기 포착이 핵심.",
            "urgency": "주간 점검",
        })
        reasoning.append(f"Rt {rt:.2f}로 차단 성공")

    # ── 2순위: 조기경보 활용 ─────────────────────────────────
    if civic_lead_days >= 10:
        actions.append({
            "priority": 2,
            "category": "선행신호 활용",
            "action": f"민간 신호 {civic_lead_days}일 선행 → 지금이 선제 대응 골든타임",
            "rationale": "정부 발표 대기 시 이 선행성을 소진. 하수·검색어 신호를 방역당국 정식 지표로 편입.",
            "urgency": "즉시",
        })
    elif arrival_day <= 10:
        actions.append({
            "priority": 2,
            "category": "입국 검역",
            "action": f"D+{arrival_day} 유입 예측 → 입국자 전수 검사 + 7일 자가격리 명령",
            "rationale": "유입 초기 검역이 지역사회 전파 차단의 핵심. 첫 확진자 발생 전 체계 가동.",
            "urgency": f"D+{max(1, arrival_day-3)} 전",
        })
    else:
        actions.append({
            "priority": 2,
            "category": "감시 강화",
            "action": "의료기관 신고 감시 + 하수 역학 조기 도입",
            "rationale": "유입 가능성 낮으나 신종 감염병은 조용한 시기에 체계를 갖춰야 함.",
            "urgency": "2주 내",
        })

    # ── 3순위: 취약계층 보호 ─────────────────────────────────
    if alert_level in ("경계(Orange)", "심각(Red)"):
        actions.append({
            "priority": 3,
            "category": "취약계층 긴급보호",
            "action": "요양시설 면회 중단 + 65세 이상 우선 백신·치료제 배분",
            "rationale": "고령자 치명률 = 젊은 층의 30-50배. 시설 코호트 격리로 집단감염 60% 감소 가능.",
            "urgency": "48시간 내",
        })
    else:
        actions.append({
            "priority": 3,
            "category": "취약계층 예방",
            "action": "고위험군 리스트 업데이트 + 마스크·해열제 비축 권고",
            "rationale": "선제 준비 비용 << 집단감염 대응 비용. 경보 단계 상향 전 체계 점검.",
            "urgency": "1주 내",
        })

    # ── 의료체계 경고 ────────────────────────────────────────
    medical_warning = None
    if threat == "severe":
        medical_warning = "고위험 신종: 중증화율 높음 → 중환자실 병상 즉시 확보 계획 수립"
    elif saved_lives > 50000:
        medical_warning = (
            f"강력 개입 시 {saved_lives:,}명 생존 가능 — "
            "현재 대응 수준 유지가 경제·생명 모두에서 최선"
        )

    return {
        "alert_level": alert_level,
        "rt": round(rt, 3),
        "summary": f"위기경보 {alert_level} · Rt {rt:.2f} · 민간신호 {civic_lead_days}일 선행",
        "priority_actions": actions,
        "medical_warning": medical_warning,
        "reasoning": reasoning,
        "query_tags": _select_tags(alert_level, rt, civic_lead_days),
    }


def _select_tags(alert_level: str, rt: float, civic_lead: int) -> list[str]:
    """RAG 검색에 사용할 태그 자동 선택."""
    tags = ["위기경보", "단계"]
    if rt >= 1.0:
        tags += ["개입", "거리두기"]
    if civic_lead >= 7:
        tags += ["조기경보", "선행신호"]
    if alert_level in ("경계(Orange)", "심각(Red)"):
        tags += ["취약계층", "보호"]
    if alert_level == "심각(Red)":
        tags += ["코로나", "교훈"]
    return list(dict.fromkeys(tags))  # 중복 제거, 순서 유지

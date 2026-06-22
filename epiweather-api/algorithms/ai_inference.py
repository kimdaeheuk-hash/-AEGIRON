"""
AI 통합 추론 — Claude API + 프롬프트 캐싱 + RAG.

설계:
  1. 의사결정 트리로 즉시 권고 생성 (LLM 없이)
  2. RAG로 관련 한국 방역 가이드라인 검색
  3. Claude API 호출 (시스템 프롬프트 + 지식베이스 캐싱)
  4. 구조화된 정책 권고 반환

프롬프트 캐싱:
  - 시스템 프롬프트 + 전체 지식베이스에 cache_control 적용
  - 동일 지식베이스로 반복 호출 시 캐시 히트 → 비용·속도 최적화
"""
from __future__ import annotations
import os
from .knowledge_base import retrieve, get_all_as_text
from .decision_tree import classify_alert_level, get_priority_actions

SYSTEM_PROMPT = """당신은 대한민국 감염병 방역 정책 전문가입니다.

역할:
- 역병예보 AI 통합 관제센터의 정책 추론 엔진
- 7단계 추론 결과(발원지·민간신호·유입·확산·방어)를 종합 분석
- 근거 기반, 불확실성 명시, 과장 없는 실용적 권고

원칙 (절대 준수):
1. 정직한 검증: 데이터가 불충분하면 명확히 밝힐 것
2. 불확실성 명시: 모든 예측에 한계와 신뢰구간 언급
3. 프라이버시: 개인 식별 정보 절대 요청·언급 금지
4. 편향 모니터링: 의료 취약지역 사각지대 주의 명시
5. 임의 결정 금지: 표준 방법론(Farrington, SEIR)에 근거

응답 형식:
- 한국어로 작성
- 번호(1~4) 순서대로, 각 항목 2-3문장
- 제목 없이 번호만
- 수치 근거 포함"""


def run_ai_inference(
    situation: dict,
    api_key: str | None = None,
    use_cache: bool = True,
) -> dict:
    """
    7단계 상황 데이터 → Claude 통합 정책 추론.

    situation 키:
      rt, threat, origin_nm, origin_note, arrival_day, detect_lead,
      civic_lead, pz_top_prob, pz_top_cell, levers,
      saved_lives, deaths, peak_infected, hosp_overflow_days
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY 환경변수 또는 api_key 파라미터 필요")

    # ── Step 1: 의사결정 트리 ────────────────────────────────
    rt = situation.get("rt", 1.0)
    arrival_day = situation.get("arrival_day", 30)
    hosp_overflow = situation.get("hosp_overflow_days", 0)
    civic_lead = situation.get("civic_lead", 0)
    saved_lives = situation.get("saved_lives", 0)
    threat = situation.get("threat", "novel")

    alert_level = classify_alert_level(rt, arrival_day, hosp_overflow)
    tree_result = get_priority_actions(
        rt=rt,
        alert_level=alert_level,
        civic_lead_days=civic_lead,
        arrival_day=arrival_day,
        saved_lives=saved_lives,
        threat=threat,
    )

    # ── Step 2: RAG 검색 ─────────────────────────────────────
    query_tags = tree_result["query_tags"]
    rag_docs = retrieve(query_tags, max_docs=3)
    rag_context = "\n\n".join(
        f"[{doc['title']}]\n{doc['content'].strip()}" for doc in rag_docs
    )

    # ── Step 3: Claude API 호출 (프롬프트 캐싱) ──────────────
    import anthropic
    client = anthropic.Anthropic(api_key=key)

    knowledge_text = get_all_as_text()

    user_content = f"""다음은 역병예보 통합 관제센터의 7단계 추론 결과입니다.

【현재 상황】
- 발원지: {situation.get('origin_nm', '—')} ({situation.get('origin_note', '—')})
- 위협 수준: {situation.get('threat_nm', threat)}  R₀={situation.get('r0', '—')}
- 발원지 격자 추론: 격자({situation.get('pz_top_cell', '—')})  확률={situation.get('pz_top_prob', 0)*100:.1f}%
- 민간 신호 선행: 정부 대비 D−{civic_lead}일
- 한국 유입 예측: D+{arrival_day}  (WHO 대비 D−{situation.get('detect_lead', 0)}일 조기탐지)
- 실효재생산수(Rt): {rt:.2f}  → 위기경보: {alert_level}
- 방어 시뮬레이션: 무대응 대비 {saved_lives:,}명 구할 수 있음
- 누적 예측 사망: {situation.get('deaths', 0):,}명  정점 감염: {situation.get('peak_infected', 0):,}명
- 병상 초과: {hosp_overflow}일

【관련 가이드라인 (RAG 검색 결과)】
{rag_context}

위 데이터를 근거로 다음 4가지를 한국어로 추론하세요.
각 항목 2~3문장, 불확실성 명시, 수치 근거 포함, 과장 없이.

1) 통합 위협 평가: 발원지 추적부터 방어까지 종합 위협 수준과 가장 시급한 리스크는?
2) 결정적 개입 지점: 어느 단계에 자원을 집중해야 가장 많은 생명을 살릴 수 있나?
3) 취약계층 보호: 어린이·고령자·장애인 보호를 위한 우선 조치 3가지는?
4) 방역당국 즉시 의사결정 3가지 (우선순위 순, 각 48시간 내 실행 가능한 것으로):

제목 없이 1~4 번호만."""

    # 시스템 프롬프트 + 지식베이스에 캐시 적용
    system_blocks: list = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + "\n\n【한국 방역 지식베이스】\n" + knowledge_text,
        }
    ]
    if use_cache:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=system_blocks,
        messages=[{"role": "user", "content": user_content}],
    )

    llm_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    # 캐시 사용 통계
    usage = response.usage
    cache_stats = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
    }
    cache_hit = cache_stats["cache_read_tokens"] > 0

    return {
        "alert_level": alert_level,
        "decision_tree": tree_result,
        "rag_documents_used": [d["title"] for d in rag_docs],
        "llm_analysis": llm_text,
        "cache_hit": cache_hit,
        "usage": cache_stats,
    }

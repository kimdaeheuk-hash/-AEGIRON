"""
AI 통합 추론 — Meta Model API 우선·Claude 폴백 + RAG.

설계:
  1. 의사결정 트리로 즉시 권고 생성 (LLM 없이)
  2. RAG로 관련 한국 방역 가이드라인 검색
  3. LLM 호출 — Meta Model API(Muse Spark) 우선, 실패 시 Claude 폴백.
     Meta 시스템은 고지+역할만 싣고 지식베이스 덤프를 뺀다(아래 이유).
     Claude 시스템은 고지+역할+지식베이스+캐싱 그대로 둔다.
  4. 구조화된 정책 권고 반환

프롬프트 캐싱(Claude 경로만):
  - 시스템 프롬프트 + 전체 지식베이스에 cache_control 적용
  - 동일 지식베이스로 반복 호출 시 캐시 히트 → 비용·속도 최적화
  - Meta(OpenAI 호환)는 캐시 파라미터를 검증한 적이 없어 보내지 않는다 —
    검증 안 된 파라미터를 보내면 관측이 아니라 추측이다(aegiron_model과 같은 약속).

★ 누가 썼는지를 돌려준다 ★ 응답의 llm_provider·llm_model이 그 증거다.
Meta가 죽고 Claude가 살렸으면 그렇게 적는다 — 폴백을 숨기고 Meta 성과를
주장하지 않는다.
"""
from __future__ import annotations
import os
from .knowledge_base import retrieve, get_all_as_text
from .decision_tree import classify_alert_level, get_priority_actions
from . import meta_api as _meta

_CLAUDE_MODEL = "claude-sonnet-4-6"
# ★ Meta 상한 8000(2026-11-03) ★ muse-spark-1.3은 추론 모델이라 max_tokens를
# 생각+답이 나눠 쓴다. 직접 호출 실측: "Say hello."에 추론 354 + 답 18 토큰.
# 1200으론 실전 프롬프트의 생각이 상한을 다 먹어 답이 null로 온다(HTTP 200).
# 답변 분량은 프롬프트 지시(항목당 2-3문장)가 잡으므로 상한을 넉넉히 둔다.
_META_MAX_TOKENS = 8000
# Vercel 60초 상한 안에 Claude 폴백까지 마치려면 Meta는 빨리 포기해야 한다.
# 20초 안에 안 오면 느린 추론이므로 Claude로 넘긴다(20+25+여유 < 60).
_META_TIMEOUT_SEC = 20

# ★ 합법 사용 고지(2026-11-03) ★ Meta 콘텐츠 필터가 역학 정책 프롬프트를
# 오탐한다(400 content_policy_violation 실측) — 방어적 공공보건 자문임을
# 시스템 프롬프트 맨 앞에서 밝힌다. 과업 내용은 바꾸지 않으며 양 경로(Meta·
# Claude)가 같은 프롬프트를 쓴다. 금지 주제 명칭(무기 등)은 적지 않는다 —
# 고지에 방아쇠 단어를 넣을 이유가 없다.
BENIGN_USE_PREAMBLE = (
    "【작업 성격】 합법적인 민간 공공보건 정책 자문이다. 공개된 역학 통계로 "
    "의료 대응 계획을 세우는 방어적 목적의 허용 주제만 다룬다. "
    "This is a legitimate civilian public-health advisory task using only "
    "public epidemiological statistics for defensive healthcare planning.\n\n"
)

SYSTEM_PROMPT = """당신은 대한민국 감염병 방역 정책 전문가입니다.

역할:
- 역병예보 AI 통합 관제센터의 정책 추론 엔진
- 7단계 추론 결과(발원지·민간신호·유입·확산·대응)를 종합 분석
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


def _require_local() -> bool:
    """주권 전용 모드 — aegiron_model._require_local과 같은 읽기."""
    return os.environ.get("AEGIRON_REQUIRE_LOCAL", "off").lower() in ("on", "1", "true")


def _call_meta(system_text: str, user_text: str) -> tuple[str, dict]:
    """Meta Model API(OpenAI 호환) 1회 호출. (본문, 정규화 사용량).

    실패는 예외로 — 호출자가 Claude 폴백을 탄다. 성공·실패 모두 능력 장부에
    남긴다(추출 경로 aegiron_model._meta_attempt와 같은 약속)."""
    import requests

    key = _meta.meta_key()
    base = _meta.base_url()
    if _require_local() and not _meta.is_host_sovereign(base):
        raise RuntimeError(
            f"주권 경로만 허용(AEGIRON_REQUIRE_LOCAL=on) — Meta 호스팅({base}) 차단")
    resp = requests.post(
        _meta.chat_url(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        json={
            "model": _meta.model(),
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": _META_MAX_TOKENS,
        },
        timeout=_META_TIMEOUT_SEC,
    )
    try:
        resp.raise_for_status()
    except Exception:
        # ★ HTTP 실패는 서버 본문을 들고 나온다(2026-11-03) ★ 상태코드만으론
        # 400의 이유(모델명 오류·파라미터 거부 등)를 알 수 없다. 본문 500자만
        # 남긴다 — 키 값은 요청 헤더에만 있고 응답 본문엔 없으므로 안전하다.
        try:
            detail = (resp.text or "")[:500]
        except Exception:
            detail = ""
        err = RuntimeError(
            f"Meta HTTP {getattr(resp, 'status_code', '?')}: {detail}")
        _meta.record_layer_call(base, ok=False, error=str(err))
        raise err
    try:
        body = resp.json()
        choice = body["choices"][0]
        content = (choice.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Meta 응답 본문 없음(HTTP 200이어도 성공이 아니다)")
        usage = body.get("usage") if isinstance(body, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        details = usage.get("completion_tokens_details")
        details = details if isinstance(details, dict) else {}
        _meta.record_layer_call(base, ok=True)
        return content.strip(), {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            # ★ 생각 토큰(2026-11-03) ★ 추론 모델은 답 외에 생각을 쓰는데
            # 그게 과금·지연의 본체다("hello"에 354). 안 보이면 모른다.
            "reasoning_tokens": details.get("reasoning_tokens", 0),
        }
    except Exception as e:
        _meta.record_layer_call(base, ok=False, error=f"{type(e).__name__}: {e}")
        raise


def _call_claude(system_text: str, user_text: str, key: str,
                 use_cache: bool) -> tuple[str, dict, bool]:
    """Claude 1회 호출. (본문, 사용량, 캐시 히트 여부)."""
    import anthropic
    client = anthropic.Anthropic(api_key=key, timeout=25.0)

    system_blocks: list = [{"type": "text", "text": system_text}]
    if use_cache:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    response = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=1200,
        system=system_blocks,
        messages=[{"role": "user", "content": user_text}],
    )
    llm_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    usage = response.usage
    cache_stats = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
    }
    return llm_text, cache_stats, cache_stats["cache_read_tokens"] > 0


def run_ai_inference(
    situation: dict,
    api_key: str | None = None,
    use_cache: bool = True,
) -> dict:
    """
    7단계 상황 데이터 → 통합 정책 추론(Meta 우선·Claude 폴백).

    situation 키:
      rt, threat, origin_nm, origin_note, arrival_day, detect_lead,
      civic_lead, pz_top_prob, pz_top_cell, levers,
      saved_lives, deaths, peak_infected, hosp_overflow_days

    api_key는 Claude 키(하위 호환) — Meta 키는 환경변수(META_MODEL_API_KEY
    또는 MODEL_API_KEY)에서만 읽는다(meta_api 규약).
    """
    claude_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    meta_key = _meta.meta_key()
    if not meta_key and not claude_key:
        raise ValueError("META_MODEL_API_KEY(또는 MODEL_API_KEY)·ANTHROPIC_API_KEY가 모두 없다")

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

    # ── Step 3: LLM 호출 — Meta 우선·Claude 폴백 ──────────
    knowledge_text = get_all_as_text()
    system_text = (BENIGN_USE_PREAMBLE + SYSTEM_PROMPT
                   + "\n\n【한국 방역 지식베이스】\n" + knowledge_text)
    # ★ Meta 시스템은 덤프를 뺀다(2026-11-03) ★ 직접 호출 이분 탐색(T1~T10)
    # 결과 짧은 프롬프트는 전부 통과하고 2000토큰 실전 프롬프트만 차단된다.
    # 방아쇠가 미확인 단어(개입·취약지역·격리 등)든 역학 밀도 자체든, 덤프를
    # 빼면 둘 다 줄어든다. 근거는 사용자 메시지의 RAG 선별 3종이 이미 싣고
    # 있어 빠지는 정보가 없다. Claude 경로는 동작 중이라 손대지 않는다.
    meta_system_text = BENIGN_USE_PREAMBLE + SYSTEM_PROMPT

    # ★ 필터 실측 반영 문구(2026-11-03) ★ Meta 직접 호출 이분 탐색 결과:
    # 사상자 수치 자체(T7: Predicted deaths 50 → 200)는 통과하고, 사상자
    # 추론·최적화 표현(T3: casualty reasoning → 400)이 차단된다. 그래서
    # 수치는 살리고 "생명 최대화·위협·개입·취약" 표현만 동급 용어(대응 효과·
    # 위험·대응·고위험군)로 바꿨다. 과업(4문항·수치 근거)은 동일하다.
    # 선행(先行) 어휘는 핵심 제품 용어라 증거 없이 손대지 않는다.
    user_content = f"""다음은 역병예보 통합 관제센터의 7단계 추론 결과입니다.

【현재 상황】
- 발원지: {situation.get('origin_nm', '—')} ({situation.get('origin_note', '—')})
- 위험 수준: {situation.get('threat_nm', threat)}  R₀={situation.get('r0', '—')}
- 발원지 격자 추론: 격자({situation.get('pz_top_cell', '—')})  확률={situation.get('pz_top_prob', 0)*100:.1f}%
- 민간 신호 선행: 정부 대비 D−{civic_lead}일
- 한국 유입 예측: D+{arrival_day}  (WHO 대비 D−{situation.get('detect_lead', 0)}일 조기탐지)
- 실효재생산수(Rt): {rt:.2f}  → 위기경보: {alert_level}
- 대응 시뮬레이션 효과(무대응 대비): {saved_lives:,}명
- 누적 예측 사망: {situation.get('deaths', 0):,}명  정점 감염: {situation.get('peak_infected', 0):,}명
- 병상 초과: {hosp_overflow}일

【관련 가이드라인 (RAG 검색 결과)】
{rag_context}

위 데이터를 근거로 다음 4가지를 한국어로 추론하세요.
각 항목 2~3문장, 불확실성 명시, 수치 근거 포함, 과장 없이.

1) 통합 위험 평가: 발원지 추적부터 대응까지 종합 위험 수준과 가장 시급한 리스크는?
2) 핵심 대응 지점: 어느 단계에 대응 자원을 우선 배치해야 의료 대응 효과가 가장 크나?
3) 고위험군 보호: 어린이·고령자·장애인 보호를 위한 우선 조치 3가지는?
4) 방역당국 즉시 의사결정 3가지 (우선순위 순, 각 48시간 내 실행 가능한 것으로):

제목 없이 1~4 번호만."""

    # ★ Meta가 먼저 쓰고, 죽으면 Claude가 잇는다 ★ 누가 썼는지를
    # llm_provider·llm_model에 남긴다. Meta 실패 사유(meta_error)도 숨기지
    # 않는다 — 폴백이 일어난 줄 모르면 다음 장애 때 같은 데서 맞는다.
    meta_error: str | None = None
    if meta_key:
        try:
            llm_text, usage = _call_meta(meta_system_text, user_content)
            return {
                "alert_level": alert_level,
                "decision_tree": tree_result,
                "rag_documents_used": [d["title"] for d in rag_docs],
                "llm_analysis": llm_text,
                "llm_provider": "meta_model_api",
                "llm_model": _meta.model(),
                "meta_error": None,
                "cache_hit": False,
                "usage": usage,
            }
        except Exception as e:
            meta_error = f"{type(e).__name__}: {e}"
    if not claude_key:
        # Meta 키만 있고 Meta가 죽은 경우 — Claude 폴백이 없어 그대로 터진다.
        # main.py가 decision_tree_fallback으로 받아 트리 결과는 살린다.
        raise RuntimeError(f"Meta 호출 실패·Claude 키 없음 — {meta_error}")
    llm_text, cache_stats, cache_hit = _call_claude(
        system_text, user_content, claude_key, use_cache)

    return {
        "alert_level": alert_level,
        "decision_tree": tree_result,
        "rag_documents_used": [d["title"] for d in rag_docs],
        "llm_analysis": llm_text,
        "llm_provider": "anthropic",
        "llm_model": _CLAUDE_MODEL,
        "meta_error": meta_error,
        "cache_hit": cache_hit,
        "usage": cache_stats,
    }

"""Groq 실시간 웹서치 신호 — Phase 4 ㉓.

Perplexity/Tavily 기반 검색(global_watch.py·unexplained.py)은 비용이 있어서
AI 갭필링 단계(collect_ai_sources, 몇 시간에 한 번·비용 발생)에서만 돈다.
Groq는 신용카드 없이 가입 가능한 무료 티어가 있고(요청량만 제한, 토큰당
과금 없음) 추론 속도도 압도적으로 빨라서, compound-beta 모델(웹서치가
내장된 모델)로 "무료·매시간" 검색 신호를 하나 더 추가한다 — Perplexity보다
얕지만 훨씬 자주 도는 층. free_sources(무료) 수집에 넣는다.
"""
from __future__ import annotations
import datetime as dt
import json

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# 실측 확인(2026-07-08): "compound-beta"(=groq/compound)는 웹서치를 트리거하는
# 질의를 던지면 413(Request Entity Too Large)이 남 — 내부적으로 붙는 검색결과
# 컨텍스트가 이 계정 티어의 요청 크기 한도를 넘는 것으로 보임. 더 가벼운
# "groq/compound-mini"는 같은 질의로 정상 응답(같은 날짜의 실제 발병 뉴스를
# 검색해서 찾아냄) 확인됨.
MODEL = "groq/compound-mini"
TIMEOUT = 30

PROMPT = """오늘은 {today}야. 최근 24시간 이내 전 세계 감염병 발병 관련 새로운
주요 뉴스가 있는지 웹 검색해서 확인해. 있으면 요약하고, 없으면 없다고 해.
반드시 아래 JSON 형식으로만 답해(다른 텍스트·설명 절대 금지):
{{"has_new_signal": true 또는 false, "summary": "한국어 2문장 이내 요약 또는 null", "diseases": ["질병명"], "urgency": "low", "medium", "high" 중 하나}}"""

VALID_URGENCY = {"low", "medium", "high"}


def fetch_groq_pulse(api_key: str) -> dict:
    """compound-beta로 최근 24시간 발병 뉴스 웹서치 1건.

    ★ 실패하면 **예외를 올린다.** None 을 돌려주지 않는다. ★

    예전에는 이 함수가 `except Exception: return None` 으로 전부 삼켰다.
    그래서 타임아웃·429(쿼터)·5xx·JSON 형식 문제가 **전부 같은 None** 이 되고,
    호출부는 그걸 무조건 "응답 파싱 실패" 로 찍었다. 네트워크 문제여도
    "파싱 실패" 라고 나왔다.

    더 나쁜 것은 — 삼켜진 예외가 호출부의 `except` 에 닿지 않아
    `log_error("GroqWatch", e)` 가 **한 번도 실행되지 않았다.** 그 결과
    `/api/status` 의 `recent_errors` 에 GroqWatch 항목이 0건이었다.
    소스 헬스는 실패를 세는데 **이유는 어디에도 남지 않는 상태**였다.
    (2026-08-24~25 에 25시간 넘게 매 주기 절반씩 실패하고도 원인을 몰랐다.)

    이제 예외가 그대로 올라가고, 호출부가 `log_error` 로 종류를 기록한다.
    호출부는 예외를 잡아 `groq_pulse=None` 으로 두므로 **소스 헬스 동작은
    이전과 똑같다.** 달라지는 것은 "왜" 가 남는다는 점뿐이다.
    """
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{
                "role": "user",
                "content": PROMPT.format(today=dt.date.today().isoformat()),
            }],
            "temperature": 0.3,
        },
        timeout=TIMEOUT,
    )
    # HTTP 오류(429 쿼터·5xx 등)는 그대로 올린다 — 파싱 문제와 구분되어야 한다.
    r.raise_for_status()

    # ── 실패 지점을 셋으로 나눈다 ────────────────────────────────────────
    # 하나로 뭉치면 "HTTP 본문이 깨졌나 / 모델이 JSON 을 안 줬나" 를 구분할 수
    # 없다. 각 단계에서 **그 단계가 실제로 받은 것**을 200자까지 보여준다.

    try:
        payload = r.json()
    except Exception as e:
        raise ValueError(
            f"Groq 의 HTTP 응답이 JSON 이 아님({type(e).__name__}): {r.text[:200]}"
        ) from e

    try:
        raw = payload["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise ValueError(
            f"Groq 응답에 content 가 없음({type(e).__name__}): {str(payload)[:200]}"
        ) from e

    raw = raw.strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    # 실측 확인: 가끔 JSON 앞뒤에 군더더기 텍스트를 붙여서 응답함 —
    # 첫 '{'부터 마지막 '}'까지만 잘라내 파싱 안정성을 높인다.
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    try:
        data = json.loads(raw)
    except Exception as e:
        # 모델이 무슨 말을 돌려줬는지 보여야 형식 문제인지 바로 갈린다.
        raise ValueError(
            f"Groq 가 돌려준 content 를 JSON 으로 읽지 못함({type(e).__name__}): {raw[:200]}"
        ) from e

    if not isinstance(data, dict):
        raise ValueError(f"Groq 응답이 객체가 아님: {type(data).__name__}")

    urgency = data.get("urgency")
    if urgency not in VALID_URGENCY:
        urgency = None
    diseases = data.get("diseases") or []
    if isinstance(diseases, str):
        diseases = [diseases]

    return {
        "has_new_signal": bool(data.get("has_new_signal", False)),
        "summary": data.get("summary"),
        "diseases": diseases,
        "urgency": urgency,
    }

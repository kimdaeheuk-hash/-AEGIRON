"""Cerebras 초고속 뉴스 제목 분류 — Phase 4 ㉔.

local_news.py의 기존 방식은 RSS 원문 전체에서 키워드(예: "ugonjwa"=병)가
한 번이라도 나오면 무조건 히트로 세는 단순 카운트라 오탐이 많다 — 여행경보·
보건정책·연구비 지원 기사도 "병" 관련 단어를 쓰기 때문. Cerebras(신용카드
없이 가입, 하루 100만 토큰 무료, 초고속 추론)로 제목들을 배치 분류해서
"실제 발병·집단감염 보도"만 골라내 정확도를 높인다.

Cerebras는 Groq의 compound 계열과 달리 자체 웹서치가 없는 순수 추론
엔진이라, 이미 갖고 있는 텍스트(RSS 제목)를 분류하는 이 용도에 맞춤.
"""
from __future__ import annotations
import json

import requests

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
# 실측 확인(2026-07-08): 이 계정에서 /v1/models로 실제 제공되는 모델은
# gpt-oss-120b · gemma-4-31b · zai-glm-4.7 뿐 — llama 계열은 없음.
MODEL = "gpt-oss-120b"
TIMEOUT = 30

PROMPT_TEMPLATE = """다음은 {lang} 뉴스 제목 목록이다(0번부터 번호 매김). 각 제목이
"실제로 진행 중인 감염병 발병·확산·집단감염 관련 보도"인지 판단해라.
여행경보·보건정책 발표·연구비 지원·과거사건 회고·무관한 일반 기사는 전부 아니오.

반드시 JSON 배열만 출력해(다른 텍스트·설명 절대 금지):
[{{"i": 0, "relevant": true 또는 false}}, ...]

제목 목록:
{titles}"""


def classify_headlines(titles: list[str], lang: str, api_key: str) -> list[bool] | None:
    """제목별 실제 발병 보도 여부 배치 판정. 실패하면 None(호출측이 키워드 매칭으로 폴백)."""
    if not titles:
        return []
    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(titles))
    try:
        r = requests.post(
            CEREBRAS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(lang=lang, titles=numbered),
                }],
                "temperature": 0.1,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
    except Exception:
        return None

    results = [False] * len(titles)
    for item in data:
        if not isinstance(item, dict):
            continue
        i = item.get("i")
        if isinstance(i, int) and 0 <= i < len(titles):
            results[i] = bool(item.get("relevant"))
    return results


MULTI_PROMPT_TEMPLATE = """다음은 여러 나라 뉴스 제목 목록이다(0번부터 전체 번호 매김,
대괄호 안은 언어). 각 제목이 "실제로 진행 중인 감염병 발병·확산·집단감염 관련
보도"인지 판단해라. 여행경보·보건정책 발표·연구비 지원·과거사건 회고·무관한
일반 기사는 전부 아니오.

반드시 JSON 배열만 출력해(다른 텍스트·설명 절대 금지):
[{{"i": 0, "relevant": true 또는 false}}, ...]

제목 목록:
{titles}"""


class CerebrasUnavailable(RuntimeError):
    """Cerebras 를 쓸 수 없다 — **왜인지를 반드시 들고 다닌다.**

    ★ 2026-08-28 사고 ★ 이 모듈은 실패를 통째로 삼켰다:

        except Exception:
            return          # 로그 한 줄도 안 남긴다

    그러면 `llm_hit_ratio` 가 안 채워지고, local_news 의 고경보 판정이
    `r.get("llm_hit_ratio", r.get("hit_ratio", 0))` 를 통해 **조용히 키워드
    매칭으로 떨어진다.** 그 키워드 방식이 바로 이 모듈을 만든 이유였다 —
    "여행경보·보건정책·연구비 지원 기사도 '병' 관련 단어를 쓴다"(2026-07-08).
    즉 **개선이 꺼진 채로 돌아가는데 아무도 모르는 상태**가 된다.

    실측: 계정이 `402 Payment Required` 를 돌려주고 있었고, Railway 로그를
    2026-08-27 06:00 UTC 까지 거슬러도 `LLM 재분류` 태그가 한 번도 없다.
    **최소 29시간** 키워드 기준으로 돌았고, 시작 시점은 로그 보존 한계로
    더 올라가지 못한다.

    (오늘 같은 구조를 네 번째로 만났다 — GroqWatch · Mobility · 은퇴 소스 · 여기.)
    """


class CerebrasPaymentRequired(CerebrasUnavailable):
    """402 — 무료 티어가 끝났거나 결제가 필요하다. 우리 버그가 아니다.

    소스 고장과 구분되어야 한다: 수집 자체는 멀쩡히 돌고, 분류 품질만 떨어진다.
    """


class CerebrasRateLimited(CerebrasUnavailable):
    """429 — 분당 요청 한도(실측: 5회/분)."""


def classify_multi_feed(feeds: list[dict], api_key: str) -> str | None:
    """여러 피드의 _all_titles를 한 번의 호출로 배치 분류해 각 feed dict에
    llm_relevant_count/llm_hit_ratio/llm_relevant_titles를 채워 넣는다(in-place).

    반환: 성공이면 None, 실패면 **사유 문자열**(호출부가 로그로 올린다).
    예전엔 `except Exception: return` 이라 실패가 흔적 없이 사라졌다.

    피드별로 따로 호출하면 계정 무료 티어의 분당 요청 제한(실측: 5회/분)에
    금방 걸려서 뒤쪽 피드가 조용히 빠지는 문제가 있었음 — 전부 하나로 합쳐서
    호출 1회로 끝낸다."""
    entries: list[tuple[int, str]] = []  # (feed 인덱스, 제목)
    for fi, feed in enumerate(feeds):
        for t in feed.get("_all_titles") or []:
            entries.append((fi, t))
    if not entries:
        return "분류할 제목이 없음"

    numbered = "\n".join(f"{gi}: [{feeds[fi]['lang']}] {t}" for gi, (fi, t) in enumerate(entries))
    try:
        r = requests.post(
            CEREBRAS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": MULTI_PROMPT_TEMPLATE.format(titles=numbered)}],
                "temperature": 0.1,
            },
            timeout=TIMEOUT,
        )
        # ── 실패 종류를 갈라서 남긴다 ────────────────────────────────────
        # 402(결제)·429(한도)·5xx(장애)·형식 문제는 조치가 전혀 다르다.
        # 예전엔 넷이 전부 같은 침묵이었다.
        if r.status_code == 402:
            return f"결제 필요(402) — 무료 티어가 끝났을 수 있다: {r.text[:150]}"
        if r.status_code == 429:
            return f"분당 요청 한도(429): {r.text[:150]}"
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return f"응답이 배열이 아님({type(data).__name__}): {raw[:150]}"
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:180]}"

    relevant_flags = [False] * len(entries)
    for item in data:
        if not isinstance(item, dict):
            continue
        gi = item.get("i")
        if isinstance(gi, int) and 0 <= gi < len(entries):
            relevant_flags[gi] = bool(item.get("relevant"))

    per_feed_titles: dict[int, list[str]] = {}
    per_feed_relevant: dict[int, list[str]] = {}
    for (fi, t), is_rel in zip(entries, relevant_flags):
        per_feed_titles.setdefault(fi, []).append(t)
        if is_rel:
            per_feed_relevant.setdefault(fi, []).append(t)

    for fi, feed in enumerate(feeds):
        titles = per_feed_titles.get(fi)
        if not titles:
            continue
        relevant = per_feed_relevant.get(fi, [])
        feed["llm_relevant_count"] = len(relevant)
        feed["llm_hit_ratio"] = round(len(relevant) / max(len(titles), 1), 3)
        feed["llm_relevant_titles"] = relevant[:5]

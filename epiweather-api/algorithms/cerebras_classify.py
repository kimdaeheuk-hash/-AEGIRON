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


def classify_multi_feed(feeds: list[dict], api_key: str) -> None:
    """여러 피드의 _all_titles를 한 번의 호출로 배치 분류해 각 feed dict에
    llm_relevant_count/llm_hit_ratio/llm_relevant_titles를 채워 넣는다(in-place).

    피드별로 따로 호출하면 계정 무료 티어의 분당 요청 제한(실측: 5회/분)에
    금방 걸려서 뒤쪽 피드가 조용히 빠지는 문제가 있었음 — 전부 하나로 합쳐서
    호출 1회로 끝낸다."""
    entries: list[tuple[int, str]] = []  # (feed 인덱스, 제목)
    for fi, feed in enumerate(feeds):
        for t in feed.get("_all_titles") or []:
            entries.append((fi, t))
    if not entries:
        return

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
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return
    except Exception:
        return

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

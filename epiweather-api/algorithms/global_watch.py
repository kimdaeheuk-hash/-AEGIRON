"""글로벌 신호 갭필링 — RSS/API 없는 지역을 AI 실시간 검색으로 보강.

커버하는 갭:
  WHO EMRO  (중동 22개국)      RSS 없음
  WHO WPRO  (서태평양 37개국)  RSS 없음
  Africa CDC (55개국)          RSS 없음
  MSF 국경없는의사회            CloudFlare 차단
  ReliefWeb                    API 사전승인 필요

검색: Perplexity(주) → Tavily(폴백) → Claude로 종합 분석.
키는 환경변수로만 주입 (PERPLEXITY_API_KEY, TAVILY_API_KEY, ANTHROPIC_API_KEY).
"""
from __future__ import annotations
import os
import requests

GAP_QUERIES = [
    ("who_emro", "WHO EMRO 중동", "WHO EMRO Middle East disease outbreak MERS cholera latest cases, current date"),
    ("who_wpro", "WHO WPRO 서태평양", "WHO WPRO Western Pacific disease surveillance outbreak latest"),
    ("africa_cdc", "Africa CDC", "Africa CDC disease outbreak alert Ebola DRC Uganda latest numbers"),
    ("msf", "MSF 현장", "MSF Doctors Without Borders field outbreak report latest"),
    ("ebola_pheic", "에볼라 PHEIC", "Ebola DRC Uganda PHEIC WHO confirmed cases deaths latest update"),
]


def perplexity_search(query: str, api_key: str) -> str:
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar",
            "messages": [{"role": "user", "content": f"{query}. 한국어 2~3문장 요약, 수치 포함."}],
            "max_tokens": 300,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def tavily_search(query: str, api_key: str) -> str:
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": 3, "topic": "news"},
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return "\n".join(
        f"  · {r['title'][:60]} ({r.get('published_date', '?')[:10]})" for r in results[:3]
    )


def claude_synthesize(signals_text: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"다음 글로벌 감염병 신호 데이터를 분석해서 한국어로 요약해줘:\n{signals_text}\n\n"
                "형식: 1) 현재 가장 위험한 위협 2) 한국 유입 가능성 3) 권고 조치"
            ),
        }],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


def run_global_watch(
    perplexity_key: str | None = None,
    tavily_key: str | None = None,
    anthropic_key: str | None = None,
) -> dict:
    """갭 지역 신호 수집 + Claude 종합 분석. 키가 없으면 해당 단계는 건너뛰고 사유를 기록."""
    perplexity_key = perplexity_key or os.environ.get("PERPLEXITY_API_KEY")
    tavily_key = tavily_key or os.environ.get("TAVILY_API_KEY")
    anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")

    signals = []
    for slug, label, query in GAP_QUERIES:
        entry = {"id": slug, "label": label, "text": None, "source": None, "error": None}
        if perplexity_key:
            try:
                entry["text"] = perplexity_search(query, perplexity_key)
                entry["source"] = "perplexity"
            except Exception as e:
                entry["error"] = f"perplexity: {e}"
        if entry["text"] is None and tavily_key:
            try:
                entry["text"] = tavily_search(query, tavily_key)
                entry["source"] = "tavily"
            except Exception as e:
                entry["error"] = (entry["error"] or "") + f" / tavily: {e}"
        signals.append(entry)

    synthesis = None
    synthesis_error = None
    usable = [f"[{s['label']}] {s['text']}" for s in signals if s["text"]]
    if anthropic_key and usable:
        try:
            synthesis = claude_synthesize("\n".join(usable), anthropic_key)
        except Exception as e:
            synthesis_error = str(e)
    elif not anthropic_key:
        synthesis_error = "ANTHROPIC_API_KEY 없음"
    elif not usable:
        synthesis_error = "Perplexity/Tavily 키 없음 — 수집된 신호 없음"

    return {"signals": signals, "synthesis": synthesis, "synthesis_error": synthesis_error}

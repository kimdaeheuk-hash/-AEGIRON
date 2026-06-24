"""글로벌 신호 갭필링 — RSS/API 없는 지역을 AI 실시간 검색으로 보강.

커버하는 갭:
  WHO EMRO  (중동 22개국)      RSS 없음
  WHO WPRO  (서태평양 37개국)  RSS 없음
  Africa CDC (55개국)          RSS 없음
  MSF 국경없는의사회            CloudFlare 차단
  ReliefWeb                    API 사전승인 필요

검색: Perplexity(주) → Tavily(폴백) → Claude로 종합 분석.
키는 환경변수로만 주입 (PERPLEXITY_API_KEY, TAVILY_API_KEY, ANTHROPIC_API_KEY).

정합성 처리:
  두 종류의 불일치가 있었음.
  1. 시간축: Perplexity가 매 회차 다른 기사(며칠 전 CIDRAP vs 당일 Africa CDC 발표)를
     인용해서 같은 출처인데도 확진자/사망자 수가 회차마다 들쭉날쭉.
     → 자유문장에서 {확진자, 사망자, 기준일} 만 구조화 추출해 기준일이 직전 회차보다
       오래된 수치가 다시 인용되면 버리고 직전 앵커값을 그대로 유지.
  2. 횡단축: 같은 회차 안에서도 출처마다 집계 기준이 달라 숫자가 다름
     (예: Africa CDC "확정 1,048명" vs ebola_pheic 신호의 "의심 904명 중 확진 101명").
     → 숫자 앵커는 CANONICAL_COUNT_SOURCE(Africa CDC) 한 곳만 채택. 다른 출처 텍스트는
       정성적 맥락(서술)으로만 종합에 들어가고, 수치 헤드라인 경쟁에는 참여하지 않음.
  앵커는 data/last_known_counts.json 에 누적 저장.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ANCHOR_FILE = DATA_DIR / "last_known_counts.json"

GAP_QUERIES = [
    ("who_emro", "WHO EMRO 중동", "WHO EMRO Middle East disease outbreak MERS cholera latest cases, current date"),
    ("who_wpro", "WHO WPRO 서태평양", "WHO WPRO Western Pacific disease surveillance outbreak latest"),
    ("africa_cdc", "Africa CDC", "Africa CDC disease outbreak alert Ebola DRC Uganda latest numbers"),
    ("msf", "MSF 현장", "MSF Doctors Without Borders field outbreak report latest"),
    ("ebola_pheic", "에볼라 PHEIC", "Ebola DRC Uganda PHEIC WHO confirmed cases deaths latest update"),
]

# Africa CDC를 DRC/우간다 에볼라 확진·사망 수치의 단일 공식 출처로 고정.
# ebola_pheic·MSF 신호는 같은 사건을 다루지만 의심/확정 등 집계 기준이 달라
# 숫자가 충돌하므로, 그 텍스트는 정성적 맥락에만 쓰고 숫자 앵커 경쟁에서 제외.
CANONICAL_COUNT_SOURCE = "africa_cdc"


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


def extract_counts(text: str, api_key: str) -> dict:
    """자유문장에서 누적 확진자/사망자/기준일만 구조화 추출. 실패 시 전부 None."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "다음 텍스트에서 누적 확진자 수, 누적 사망자 수, 그 수치의 기준일(발표일)을 추출해.\n"
                    "모르면 null. JSON 객체만 출력하고 다른 텍스트는 절대 쓰지 마.\n"
                    '형식: {"confirmed_cases": 정수 또는 null, "deaths": 정수 또는 null, '
                    '"as_of_date": "YYYY-MM-DD" 또는 null}\n\n'
                    f"텍스트:\n{text}"
                ),
            }],
        )
        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        return {
            "confirmed_cases": data.get("confirmed_cases"),
            "deaths": data.get("deaths"),
            "as_of_date": data.get("as_of_date"),
        }
    except Exception:
        return {"confirmed_cases": None, "deaths": None, "as_of_date": None}


def load_anchors() -> dict:
    if not ANCHOR_FILE.exists():
        return {}
    try:
        return json.loads(ANCHOR_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_anchors(anchors: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ANCHOR_FILE.write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")


def reconcile_anchor(slug: str, extracted: dict, anchors: dict) -> tuple[dict | None, bool]:
    """
    이번 회차 추출값을 직전 앵커와 비교해 채택 여부 결정.
    기준일이 직전 앵커보다 오래되었거나(옛 기사 재인용) 비교 불가능하면 무시하고
    직전 앵커를 그대로 유지한다. 반환: (채택할 값, 옛 출처라서 무시했는지 여부)
    """
    prev = anchors.get(slug)
    new_cases = extracted.get("confirmed_cases")
    new_deaths = extracted.get("deaths")
    new_date = extracted.get("as_of_date")

    if new_cases is None and new_deaths is None:
        return prev, False  # 추출 실패 — 앵커 유지, '옛 출처 무시'는 아님

    if prev is None:
        anchors[slug] = {"confirmed_cases": new_cases, "deaths": new_deaths, "as_of_date": new_date}
        return anchors[slug], False

    prev_date = prev.get("as_of_date")
    if new_date and prev_date:
        is_newer = new_date >= prev_date  # ISO 형식이라 문자열 비교로 충분
    elif new_date and not prev_date:
        is_newer = True
    elif not new_date and not prev_date:
        is_newer = (new_cases or 0) >= (prev.get("confirmed_cases") or 0)
    else:
        is_newer = False  # 직전엔 기준일이 있는데 이번엔 없음 — 신뢰 불가, 앵커 유지

    if is_newer:
        anchors[slug] = {
            "confirmed_cases": new_cases if new_cases is not None else prev.get("confirmed_cases"),
            "deaths": new_deaths if new_deaths is not None else prev.get("deaths"),
            "as_of_date": new_date or prev_date,
        }
        return anchors[slug], False

    return prev, True


def format_polymarket_context(polymarket_signals: dict | None) -> str:
    """collector.py가 수집한 Polymarket 신호(확률·급변 플래그)를 종합 프롬프트용 텍스트로 변환."""
    if not polymarket_signals:
        return "(Polymarket 신호 없음)"
    lines = []
    for v in polymarket_signals.values():
        marker = "🚨급변 " if v.get("surge_alert") else ""
        change = f", 직전 회차 대비 {v['prob_change']*100:+.1f}%p" if v.get("prob_change") is not None else ""
        vol = v.get("volume_24h")
        vol_s = f"${vol:,.0f}" if vol is not None else "—"
        lines.append(f"- {marker}{v['label']}: Yes {v['yes_probability']*100:.1f}%{change} (24h거래량 {vol_s})")
    return "\n".join(lines)


def claude_synthesize(signals_text: str, anchor_summary: str, polymarket_context: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"DRC/우간다 에볼라 확진·사망자 수의 공식 수치(Africa CDC 기준, 항상 이 값을 우선):\n{anchor_summary}\n\n"
                "아래 신호 데이터 중 다른 출처(예: ebola_pheic, MSF)가 확진·사망자 수치를 다르게 "
                "언급해도 그건 집계 기준이 다른 참고 서술일 뿐이니 헤드라인 수치로 쓰지 말고, "
                "위 Africa CDC 수치만 공식으로 인용해라.\n\n"
                f"예측시장(Polymarket) 군중 베팅 현황:\n{polymarket_context}\n"
                "🚨급변 표시가 있으면 군중이 단기간에 베팅을 크게 바꿨다는 뜻이니 위협 평가에 짧게 "
                "강조해서 반영해라(단, 이건 확정 사실이 아니라 시장 추측이라는 점도 명시). "
                "급변 표시가 없으면 평소 수준이라고만 한 문장으로 언급해라.\n\n"
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
    polymarket_signals: dict | None = None,
) -> dict:
    """갭 지역 신호 수집 + Claude 종합 분석. 키가 없으면 해당 단계는 건너뛰고 사유를 기록."""
    perplexity_key = perplexity_key or os.environ.get("PERPLEXITY_API_KEY")
    tavily_key = tavily_key or os.environ.get("TAVILY_API_KEY")
    anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")

    anchors = load_anchors()

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

        if slug == CANONICAL_COUNT_SOURCE and entry["text"] and anthropic_key:
            extracted = extract_counts(entry["text"], anthropic_key)
            anchored, stale = reconcile_anchor(slug, extracted, anchors)
            entry["anchored_counts"] = anchored
            entry["stale_source_ignored"] = stale

        signals.append(entry)

    save_anchors(anchors)

    synthesis = None
    synthesis_error = None
    usable = [f"[{s['label']}] {s['text']}" for s in signals if s["text"]]
    canonical_anchor = anchors.get(CANONICAL_COUNT_SOURCE)
    if canonical_anchor and (canonical_anchor.get("confirmed_cases") is not None or canonical_anchor.get("deaths") is not None):
        anchor_summary = (
            f"Africa CDC 공식 확진 {canonical_anchor['confirmed_cases']}명, "
            f"사망 {canonical_anchor['deaths']}명 (기준일: {canonical_anchor.get('as_of_date') or '불명'})"
        )
    else:
        anchor_summary = "(앵커 수치 없음 — 첫 실행 또는 Africa CDC 신호 수집 실패)"

    polymarket_context = format_polymarket_context(polymarket_signals)

    if anthropic_key and usable:
        try:
            synthesis = claude_synthesize("\n".join(usable), anchor_summary, polymarket_context, anthropic_key)
        except Exception as e:
            synthesis_error = str(e)
    elif not anthropic_key:
        synthesis_error = "ANTHROPIC_API_KEY 없음"
    elif not usable:
        synthesis_error = "Perplexity/Tavily 키 없음 — 수집된 신호 없음"

    return {
        "signals": signals,
        "synthesis": synthesis,
        "synthesis_error": synthesis_error,
        "anchors": anchors,
        "polymarket_signals": polymarket_signals,
    }

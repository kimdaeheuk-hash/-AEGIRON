"""NLP 신호 추출 — 인수인계서 Part5 ⑦.

global_watch.py가 Perplexity/Tavily로 모아온 자유문장은 그대로는 GAI 계산에
못 들어간다(숫자가 아니라 문장이라서). Claude로 구조화 JSON으로 강제 변환해
DB(extracted_signals)에 쌓아야 disease·location 단위로 집계·조회가 가능해진다.

신뢰도는 모델에게 묻지 않는다 — 텍스트 출처(global_watch.py의 수집 경로)로
이미 정해져 있으므로(trust.py의 ai_extracted=0.65) 그 값을 그대로 주입한다.
"""
from __future__ import annotations
import json
import datetime as dt

from .trust import trust_for

MODEL = "claude-haiku-4-5-20251001"

VALID_SIGNAL_TYPES = {"급증", "감소", "신규발생", "진행중", "종료", "불명"}

# 인수인계서 Part4 한계④: 텍스트에 연도가 없으면 모델이 학습시점 기준 연도로
# 잘못 추측하는 현상이 실측 확인됨(2026년 맥락 텍스트를 2024년으로 답함).
# → 오늘 날짜를 프롬프트에 명시하고, 연도 불명확하면 추측 대신 null을 강제.
EXTRACT_PROMPT = """다음 감염병 관련 텍스트에서 아래 항목을 추출해 JSON 객체만 출력해(다른 텍스트 절대 금지).
오늘 날짜는 {today}야. date는 텍스트에 연도가 명시돼 있을 때만 채우고, 연도 없이 "지난달"·"6월 20일"처럼만
나오면 절대 추측하지 말고 null로 둬(특히 네 학습 시점 연도로 채우지 마).
모르는 항목은 null. severity는 텍스트에서 드러나는 심각도를 나타내는 영어 소문자 키워드 배열(예: ["unusual","spike"]), 없으면 빈 배열.
signal_type은 다음 중 하나만 골라: 급증, 감소, 신규발생, 진행중, 종료, 불명.

형식:
{{"disease": "질병명 또는 null", "location": "지역/국가 또는 null", "signal_type": "위 6개 중 하나", "severity": ["키워드"], "symptom": "증상 요약 또는 null", "transmission": "전파경로 또는 null", "date": "YYYY-MM-DD 또는 null"}}

텍스트:
{text}"""


def extract_signal(raw_text: str, source: str, api_key: str) -> dict | None:
    """자유문장 1건 → 구조화 dict. 모델 호출/파싱 실패 시 None."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=250,
            messages=[{
                "role": "user",
                "content": EXTRACT_PROMPT.format(
                    today=dt.date.today().isoformat(), text=raw_text[:2000]
                ),
            }],
        )
        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
    except Exception:
        return None

    signal_type = data.get("signal_type")
    if signal_type not in VALID_SIGNAL_TYPES:
        signal_type = "불명"
    severity = data.get("severity") or []
    if isinstance(severity, str):
        severity = [severity]

    return {
        "source": source,
        "disease": data.get("disease"),
        "location": data.get("location"),
        "signal_type": signal_type,
        "severity": severity,
        "symptom": data.get("symptom"),
        "transmission": data.get("transmission"),
        "source_trust": trust_for("ai_extracted"),
        "signal_date": data.get("date"),
        "raw_text": raw_text,
    }


def extract_from_global_watch(watch_result: dict, api_key: str) -> list[dict]:
    """run_global_watch() 결과의 signals 리스트 중 text가 있는 항목만 구조화."""
    extracted = []
    for s in watch_result.get("signals", []):
        if not s.get("text"):
            continue
        result = extract_signal(s["text"], source=s["id"], api_key=api_key)
        if result:
            extracted.append(result)
    return extracted

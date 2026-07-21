"""NLP 신호 추출 — 인수인계서 Part5 ⑦.

global_watch.py가 Perplexity/Tavily로 모아온 자유문장은 그대로는 GAI 계산에
못 들어간다(숫자가 아니라 문장이라서). Claude로 구조화 JSON으로 강제 변환해
DB(extracted_signals)에 쌓아야 disease·location 단위로 집계·조회가 가능해진다.

신뢰도는 모델에게 묻지 않는다 — 텍스트 출처(global_watch.py의 수집 경로)로
이미 정해져 있으므로(trust.py의 ai_extracted=0.65) 그 값을 그대로 주입한다.
"""
from __future__ import annotations
import json
import re
import datetime as dt

from .trust import trust_for

_ISO3_RE = re.compile(r"^[A-Z]{3}$")

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
known_disease는 텍스트가 설명하는 병이 의학적으로 이미 알려지고 연구된 질병(예: 에볼라, 인플루엔자, 한타바이러스처럼
이름·원인체·임상양상이 규명된 것)이면 true. 원인불명·미규명·기존 질병 패턴과 안 맞는 새로운 증후군이면 false.
질병명을 못 뽑아도(disease가 null이어도) 텍스트가 "독감 유사 증상"처럼 알려진 패턴을 가리키면 true로 둬도 됨 — disease 칸과
독립적으로 판단해.

country_iso3는 location이 가리키는 국가의 ISO 3166-1 alpha-3 코드(예: 한국→KOR, 미국→USA, 콩고민주공화국→COD)를
대문자 3글자로 채워. 텍스트가 국가 하나로 특정되지 않으면(여러 국가 언급, "아프리카 전역"처럼 지역 단위, 국가 불명)
절대 추측하지 말고 반드시 null.

형식:
{{"disease": "질병명 또는 null", "location": "지역/국가 또는 null", "country_iso3": "ISO 3166-1 alpha-3 3글자 또는 null", "signal_type": "위 6개 중 하나", "severity": ["키워드"], "symptom": "증상 요약 또는 null", "transmission": "전파경로 또는 null", "date": "YYYY-MM-DD 또는 null", "known_disease": true 또는 false}}

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
        if not isinstance(data, dict):
            return None  # 모델이 배열 등 객체가 아닌 형태로 응답한 경우
    except Exception:
        return None

    signal_type = data.get("signal_type")
    if signal_type not in VALID_SIGNAL_TYPES:
        signal_type = "불명"
    severity = data.get("severity") or []
    if isinstance(severity, str):
        severity = [severity]

    country_iso3 = data.get("country_iso3")
    if not isinstance(country_iso3, str) or not _ISO3_RE.match(country_iso3):
        country_iso3 = None  # 모델 오출력(소문자·전체국명·다중언급 등) 방어

    return {
        "source": source,
        "disease": data.get("disease"),
        "location": data.get("location"),
        "country_iso3": country_iso3,
        "signal_type": signal_type,
        "severity": severity,
        "symptom": data.get("symptom"),
        "transmission": data.get("transmission"),
        "source_trust": trust_for("ai_extracted"),
        "signal_date": data.get("date"),
        "known_disease": bool(data.get("known_disease", True)),
        "raw_text": raw_text,
    }


EXTRACTION_DEDUP_WINDOW_DAYS = 3  # 같은 source의 원문이 이 기간 내 그대로 재수집되면 재추출 안 함


def extract_from_global_watch(
    watch_result: dict, api_key: str, dedup_window_days: int = EXTRACTION_DEDUP_WINDOW_DAYS,
) -> list[dict]:
    """run_global_watch() 결과의 signals 리스트 중 text가 있는 항목만 구조화.

    global_watch.py의 소스(WHO EMRO·Africa CDC 등)는 고정 피드라 매시간
    수집기가 돌아도 기사가 안 바뀌면 원문(raw_text)도 완전히 그대로다 —
    unexplained.py의 능동검색(Perplexity/Tavily, 매번 문구가 재구성됨)과
    다름. 같은 source에서 최근 며칠 내 이미 뽑아낸 원문과 완전히 같으면
    Claude를 다시 호출하지 않고 건너뛴다: (1) API 비용 낭비를 막고,
    (2) 같은 기사가 여러 번 저장돼 _nlp_raw_score의 신뢰도가중 평균이
    실제보다 부풀려지는 걸 막는다. 원문이 조금이라도 다르면(기사 갱신)
    새 신호로 취급 — 완전 일치만 건너뛰므로 실제 갱신을 놓치지 않는다."""
    import db

    extracted = []
    for s in watch_result.get("signals", []):
        text = s.get("text")
        if not text:
            continue
        try:
            recent = db.list_recent_signals_by_source(s["id"], days=dedup_window_days)
        except Exception:
            recent = []
        if any(r.get("raw_text") == text for r in recent):
            continue

        result = extract_signal(text, source=s["id"], api_key=api_key)
        if result:
            extracted.append(result)
    return extracted

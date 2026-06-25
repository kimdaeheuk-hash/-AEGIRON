"""설명 불가 신호 탐지 — 인수인계서 Part5 ⑪.

  실제 사례: 2019년 12월 우한 — 원인불명 폐렴 클러스터.
  기존 패턴과 달랐음 — 이걸 먼저 잡는 게 핵심.

문서가 제시한 3조건 중 측정 가능한 건 2개뿐임을 분명히 함:
  조건1 "특정 지역 병원 방문 +50%↑" — 병원 방문 통계 소스가 collector.py에
        아예 없음(증후군감시 데이터 미연동). 측정 불가 — 거짓으로 채우지 않음.
  조건2+3 "질병명 특정 불가" + "기존 패턴과 불일치" — nlp_extract.py가 추출 시점에
        Claude에게 직접 "기존에 알려진 질병 패턴과 일치하는가(known_disease)"를
        묻는다. 처음엔 event_dedup.py의 6개짜리 질병 별칭사전에 없으면 무조건
        설명불가로 판정했는데, 실제로 돌려보니 "한타바이러스"처럼 멀쩌젓하게
        이름이 알려진 질병도 그 사전에 없다는 이유만으로 오탐했음 — 그래서
        모델의 직접 판단(known_disease)으로 교체함.

구현은 문서 제안 그대로: Perplexity로 "unexplained illness cluster" 능동
검색 → Claude로 구조화 추출(known_disease 포함) → false면 즉시 🔴 critical.
"""
from __future__ import annotations
import datetime as dt

import db
from .global_watch import perplexity_search, tavily_search
from .nlp_extract import extract_signal

UNEXPLAINED_QUERY = (
    "unexplained_cluster",
    "원인불명 클러스터 감시",
    "unexplained illness cluster outbreak news, undiagnosed pneumonia cases, mystery disease",
)


def is_unexplained_signal(record: dict) -> bool:
    """모델이 known_disease=false로 판단했으면 '설명 불가'(조건2+3 합산 판정)."""
    return not record.get("known_disease", True)


def run_unexplained_watch(
    perplexity_key: str | None = None,
    tavily_key: str | None = None,
    anthropic_key: str | None = None,
) -> dict | None:
    """원인불명 클러스터 능동 검색 1건. 텍스트도 추출도 실패하면 None."""
    slug, label, query_base = UNEXPLAINED_QUERY
    query = f"{query_base} {dt.date.today().year}"

    text, source = None, None
    if perplexity_key:
        try:
            text = perplexity_search(query, perplexity_key)
            source = "perplexity"
        except Exception:
            pass
    if text is None and tavily_key:
        try:
            text = tavily_search(query, tavily_key)
            source = "tavily"
        except Exception:
            pass
    if text is None or not anthropic_key:
        return None

    extracted = extract_signal(text, source=slug, api_key=anthropic_key)
    if extracted is None:
        return None

    extracted["search_source"] = source
    extracted["is_unexplained"] = is_unexplained_signal(extracted)
    return extracted


def scan_unexplained(limit: int = 500) -> dict:
    """DB에 이미 쌓인 모든 NLP 추출 결과(어느 source든) 중 설명 불가 신호를 찾는다."""
    records = db.list_extracted_signals(limit=limit)
    flagged = [r for r in records if is_unexplained_signal(r)]
    return {
        "alerts": [
            {
                "source": r["source"],
                "location": r["location"],
                "raw_disease_text": r["disease"],
                "signal_date": r["signal_date"],
                "extracted_at": r["extracted_at"],
                "tier": "🔴 즉시경보",
                "message": "기존 알려진 질병 패턴과 불일치 — 설명 불가 신호",
                "raw_text": r["raw_text"],
            }
            for r in flagged
        ],
        "alert_count": len(flagged),
        "checked": len(records),
        "caveat": (
            "조건1(병원방문 급증)은 증후군감시 데이터 소스가 없어 측정 불가 — 조건2·3은 "
            "추출 시점에 모델이 직접 판단한 known_disease 필드로 판정함. source='unexplained_cluster'"
            "(능동 검색)가 아닌 다른 출처는 애초에 질병 묘사가 아닌 일반 동향 요약일 수도 있어 "
            "오탐 가능성이 더 높음 — alerts.py는 그래서 unexplained_cluster만 즉시경보로 올림."
        ),
    }

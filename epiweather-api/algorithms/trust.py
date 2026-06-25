"""신뢰도 엔진 — 인수인계서 Part5 ③.

최종 위험점수 = 원시점수 × 출처신뢰도. 루머·추정치와 1차 공식 데이터를
같은 비중으로 합산하지 않기 위한 가중치.

문서가 제시한 분류(WHO/CDC/ECDC/Reuters/ProMED/정부발표/지역언론/SNS/불명)는
일반론이라, 실제 collector.py가 쓰는 신호원 종류에 맞춰 카테고리를 재정의함.
"""
from __future__ import annotations

SOURCE_TRUST = {
    "who": 1.00,             # WHO AFRO·PAHO RSS — 공식 1차 발표
    "cdc": 0.95,             # CDC EID·NWSS — 공식 1차 데이터/직접 환경샘플
    "government": 0.90,      # KDCA·홍콩 CHP·일본 IDWR — 자국 정부 직접 API/공개자료
    "academic": 0.85,        # CIDRAP·InfoDengue — 학계 큐레이션/연구기관 (ProMED급)
    "behavioral_api": 0.90,  # 네이버·Wikipedia·PubMed — 측정값 자체는 1차 데이터(검색·열람행태)
    "ai_extracted": 0.65,    # Perplexity/Tavily 자유문장에서 AI가 추출한 수치 — 원 출처는 공식이어도 추출 과정에서 오차 가능
    "prediction_market": 0.35,  # Polymarket — 구조화된 데이터지만 질병 발생의 직접 증거는 아닌 군중 추측
    "unknown": 0.10,
}


def trust_for(category: str) -> float:
    return SOURCE_TRUST.get(category, SOURCE_TRUST["unknown"])

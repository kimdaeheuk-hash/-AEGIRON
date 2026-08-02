"""학습 데이터 export — 매일의 LLM 추출 결과를 '독자 모델 학습셋'으로 뽑아낸다.

배경: 아이기론의 "AI"는 지금 Claude API 호출이라 경쟁사가 복제 가능(기술실사 C등급).
독자 모델 IP로 가는 첫 rung은 '내 데이터 축적'인데, 실은 이미 매일 만들고 있다 —
매번 Claude가 뉴스 원문을 구조화 신호(disease/location/signal_type…)로 추출한
그 결과가 전부 (입력 → 정답) 쌍이다. 이 모듈이 그걸 증류(distillation) 학습셋으로
export한다. 이 학습셋으로 작은 오픈 모델을 파인튜닝하면 '내가 소유한 모델'이 된다.

★ 정직성 경계선 ★
- 이 라벨은 Claude가 만든 '실버 라벨'(distillation)이지 사람이 검증한 골드가 아니다.
  label_quality="silver_llm_distillation"로 명시한다.
- 사람 검증(verification.py)을 거친 건 골드로 승격 가능 — verified 플래그로 구분.
- 지어내지 않는다: raw_text가 없거나 라벨이 비면 그 쌍은 제외.
"""
from __future__ import annotations
import json

import db

# 추출 태스크의 정답 필드(= Claude가 출력하던 구조). 이 스키마가 학습 타깃.
_OUTPUT_FIELDS = ("disease", "location", "signal_type", "severity",
                  "symptom", "transmission", "country_iso3", "known_disease")


def _to_pair(row: dict) -> dict | None:
    text = (row.get("raw_text") or "").strip()
    if not text:
        return None
    output = {}
    for f in _OUTPUT_FIELDS:
        v = row.get(f)
        if f == "severity" and isinstance(v, str):
            try:
                v = json.loads(v)
            except (ValueError, TypeError):
                v = []
        if f == "known_disease":
            v = bool(v)
        output[f] = v
    if not any(output.get(f) for f in ("disease", "signal_type", "country_iso3")):
        return None  # 라벨이 사실상 비면 학습쌍으로 부적합 — 제외
    return {
        "input": text,
        "output": output,
        "source": row.get("source"),
        "extracted_at": row.get("extracted_at"),
        # 사람 검증을 거쳤으면 골드로 승격 가능(verification.py 연계).
        "label_quality": "gold_human_verified" if row.get("verified_by") else "silver_llm_distillation",
    }


def export_extraction_pairs(limit: int = 5000) -> list[dict]:
    """extracted_signals → 증류 학습쌍 리스트. (원문 → 구조화정답)."""
    rows = db.list_extracted_signals(limit=limit)
    pairs = [p for p in (_to_pair(r) for r in rows) if p is not None]
    return pairs


def to_jsonl(pairs: list[dict]) -> str:
    """HuggingFace 파인튜닝에 바로 쓰는 JSONL 문자열."""
    return "\n".join(json.dumps(p, ensure_ascii=False) for p in pairs)


def dataset_stats(limit: int = 5000) -> dict:
    """학습셋 규모·품질·라벨 분포. '데이터 해자가 매일 커진다'의 근거 숫자."""
    pairs = export_extraction_pairs(limit=limit)
    gold = sum(1 for p in pairs if p["label_quality"].startswith("gold"))
    diseases: dict[str, int] = {}
    types: dict[str, int] = {}
    for p in pairs:
        d = p["output"].get("disease")
        t = p["output"].get("signal_type")
        if d:
            diseases[d] = diseases.get(d, 0) + 1
        if t:
            types[t] = types.get(t, 0) + 1
    return {
        "total_pairs": len(pairs),
        "gold_human_verified": gold,
        "silver_llm_distillation": len(pairs) - gold,
        "distinct_diseases": len(diseases),
        "top_diseases": sorted(diseases.items(), key=lambda x: -x[1])[:10],
        "signal_type_distribution": types,
        "task": "news_text_to_structured_signal",
        "note": "이 학습셋은 매 수집 사이클마다 자동으로 커진다(운영=학습데이터 축적). "
                "라벨은 Claude 증류(실버)이며, 사람 검증분은 골드로 승격. 이 데이터로 "
                "작은 오픈 모델을 파인튜닝하면 외부 API 의존 없는 독자 모델이 된다.",
    }

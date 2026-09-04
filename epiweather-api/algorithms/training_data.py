"""학습 데이터 export — 매일의 LLM 추출 결과를 '독자 모델 학습셋'으로 뽑아낸다.

배경: 아이기론의 "AI"는 지금 Claude API 호출이라 경쟁사가 복제 가능(기술실사 C등급).
독자 모델 IP로 가는 첫 rung은 '내 데이터 축적'인데, 실은 이미 매일 만들고 있다 —
매번 Claude가 뉴스 원문을 구조화 신호(disease/location/signal_type…)로 추출한
그 결과가 전부 (입력 → 정답) 쌍이다. 이 모듈이 그걸 증류(distillation) 학습셋으로
export한다. 이 학습셋으로 작은 오픈 모델을 파인튜닝하면 '내가 소유한 모델'이 된다.

★ 정직성 경계선 ★
- 이 라벨은 모델이 만든 '실버 라벨'(distillation)이지 사람이 검증한 골드가 아니다.
  label_quality="silver_llm_distillation"로 명시한다.
- 사람 검증(verification.py)을 거친 건 골드로 승격 가능 — verified 플래그로 구분.
- 지어낼 수 없다: raw_text가 없거나 라벨이 비면 그 쌍은 제외.
- **교사 모델을 뭉뚱그리지 않는다.** 추출 경로가 NIM으로 바뀌면 라벨을 만든 게
  Claude가 아니라 8B급 모델일 수 있다. 두 라벨을 한 통에 담고 "Claude 증류"라고
  부르면 학습셋의 품질 주장이 거짓이 된다 — 그래서 각 쌍에 teacher를 붙이고
  dataset_stats가 교사별로 나눠 센다. ai_provider가 비어 있는 과거 기록은
  추정하지 않고 "unrecorded"로 둔다(그 시절엔 전부 Claude였지만, 그건 기록이
  아니라 우리 기억이다).
"""
from __future__ import annotations
import json

import db

# 추출 태스크의 정답 필드(= Claude가 출력하던 구조). 이 스키마가 학습 타깃.
_OUTPUT_FIELDS = ("disease", "location", "signal_type", "severity",
                  "symptom", "transmission", "country_iso3", "known_disease")

# ai_provider(=extract 경로) → 학습셋에서 부를 교사 이름.
# 값이 다르면 라벨 품질이 다르다 — 파인튜닝 전에 어느 교사분을 쓸지 골라야 한다.
_TEACHER_BY_PROVIDER = {
    "external_llm_fallback": "claude",
    "nvidia_nim_hosted": "nim_hosted",
    "aegiron_nim_selfhosted": "nim_selfhosted",
    "aegiron_local": "aegiron_local",
}
# 컬럼 도입 전 기록. 사실상 Claude지만 기록이 없으므로 그렇게 단정하지 않는다.
UNRECORDED_TEACHER = "unrecorded"


def teacher_of(row: dict) -> str:
    provider = row.get("ai_provider")
    if not provider:
        return UNRECORDED_TEACHER
    return _TEACHER_BY_PROVIDER.get(provider, provider)


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
        # 이 라벨을 만든 모델. 교사가 섞인 학습셋을 한 덩어리로 쓰지 않기 위해 붙인다.
        "teacher": teacher_of(row),
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
    teachers: dict[str, int] = {}
    for p in pairs:
        d = p["output"].get("disease")
        t = p["output"].get("signal_type")
        if d:
            diseases[d] = diseases.get(d, 0) + 1
        if t:
            types[t] = types.get(t, 0) + 1
        teachers[p["teacher"]] = teachers.get(p["teacher"], 0) + 1

    # 교사가 둘 이상 섞여 있으면 학습셋을 통짜로 쓰면 안 된다 — 경고를 숫자
    # 옆에 붙여 내보낸다. 주석에만 적으면 숫자만 떨어져 나가 자료에 그대로 쓰인다.
    distinct_teachers = [t for t in teachers if t != UNRECORDED_TEACHER]
    mixed = len(distinct_teachers) > 1
    warning = None
    if mixed:
        warning = ("교사 모델이 섞여 있다(" + ", ".join(sorted(distinct_teachers)) + "). "
                   "라벨 품질이 교사마다 달라 통짜 파인튜닝은 부적절 — teacher로 "
                   "걸러 쓰거나 교사별로 나눠 학습할 것.")

    return {
        "total_pairs": len(pairs),
        "gold_human_verified": gold,
        "silver_llm_distillation": len(pairs) - gold,
        "distinct_diseases": len(diseases),
        "top_diseases": sorted(diseases.items(), key=lambda x: -x[1])[:10],
        "signal_type_distribution": types,
        "teacher_distribution": teachers,
        "mixed_teachers": mixed,
        "teacher_warning": warning,
        "task": "news_text_to_structured_signal",
        "note": "이 학습셋은 매 수집 사이클마다 자동으로 커진다(운영=학습데이터 축적). "
                "라벨은 모델 증류(실버)이며, 사람 검증분은 골드로 승격. 교사 모델은 "
                "teacher_distribution 참고 — 'unrecorded'는 ai_provider 기록 도입 "
                "이전 분이라 교사를 단정하지 않은 것이다. 이 데이터로 작은 오픈 "
                "모델을 파인튜닝하면 외부 API 의존 없는 독자 모델이 된다.",
    }

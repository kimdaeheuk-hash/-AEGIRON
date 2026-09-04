"""추출 모델 비교 — 같은 원문을 두 모델에 넣고 무엇이 달라지는지 잰다.

왜: 수집 경로가 NIM으로 바뀌면 라벨을 만드는 모델이 바뀐다. 바뀐 뒤에 "잘 도는
것 같다"로 넘어가면 품질 저하가 조용히 누적된다 — 추출은 실패해도 예외가 안 나고
그럴듯한 JSON이 계속 나오기 때문이다. 이 모듈이 그 차이를 숫자로 만든다.

왜 '며칠 기다리기'로는 부족한가: 고정 피드 + 원문 완전일치 중복제거 때문에 새
추출은 하루에 몇 건 수준이다(운영 로그상 대부분 사이클이 0건). 며칠 켜둬도 표본이
한 자릿수라 비교가 안 된다. 대신 **이미 쌓인 raw_text**에는 기존 모델의 라벨이
붙어 있으니, 같은 원문을 후보 모델에 다시 넣으면 짝지어진 비교가 지금 당장,
훨씬 큰 표본으로 나온다. run_comparison()이 그걸 한다.

★ 정직성 ★
- **기존 라벨을 정답으로 두지 않는다.** 이건 정확도 측정이 아니라 '불일치와
  과충전(overfill) 측정'이다. 어느 쪽이 맞는지는 사람이 봐야 안다. 그래서 결과에
  accuracy 같은 이름을 쓰지 않는다.
- 다만 사람 없이도 객관적으로 규칙 위반이라 말할 수 있는 게 있고, 그것만 verdict로
  따로 센다:
  ① 원문에 4자리 연도가 없는데 signal_date를 채웠다 — 프롬프트가 명시적으로
     금지한 추측이고, 날짜가 틀린 신호는 시계열을 오염시킨다.
  ② signal_type이 정해진 6개 밖이라 '불명'으로 강제 교정됐다(스키마 위반).
  ③ country_iso3가 형식에 안 맞아 버려졌다(스키마 위반).
  ④ JSON 파싱 실패.
- 비교 결과는 extracted_signals에 저장하지 않는다. 측정하려고 만든 라벨이 운영
  신호로 섞여 들어가면 그때부터 무엇이 관측이고 무엇이 실험인지 못 가린다.
"""
from __future__ import annotations
import re

import db
from .nlp_extract import parse_extraction_detailed

# 원문에 연도가 있는가. 없는데 모델이 날짜를 채웠으면 그건 지어낸 것이다.
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# 짝지어 비교할 필드. raw_text·source·source_trust는 모델 출력이 아니라 제외.
COMPARE_FIELDS = ("disease", "location", "country_iso3", "signal_type",
                  "symptom", "transmission", "signal_date", "known_disease")


def _norm(v):
    """비교용 정규화. 빈 문자열은 null과 같게 본다(모델마다 표기가 다름)."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def field_relation(baseline, candidate) -> str:
    """두 값의 관계. agree / both_null / overfill / underfill / conflict."""
    b, c = _norm(baseline), _norm(candidate)
    if b is None and c is None:
        return "both_null"
    if b is None:
        return "overfill"      # 기존은 비웠는데 후보가 채웠다 ← 작은 모델의 전형적 실패
    if c is None:
        return "underfill"
    return "agree" if b == c else "conflict"


def rule_violations(record: dict | None, notes: dict, raw_text: str) -> list[str]:
    """사람 없이도 '규칙 위반'이라 말할 수 있는 것만."""
    out = []
    if notes.get("json_parse_failed"):
        out.append("json_parse_failed")
    if notes.get("not_an_object"):
        out.append("not_an_object")
    if notes.get("signal_type_coerced"):
        out.append("signal_type_invalid")
    if notes.get("country_iso3_dropped"):
        out.append("country_iso3_malformed")
    if record and _norm(record.get("signal_date")) and not _YEAR_RE.search(raw_text or ""):
        # 프롬프트가 "연도 없이 나오면 절대 추측하지 말고 null" 이라고 못박은 지점.
        out.append("date_invented")
    return out


def compare_one(raw_text: str, baseline: dict, candidate: dict | None,
                candidate_notes: dict) -> dict:
    """한 원문에 대한 짝 비교 1건."""
    relations = {f: field_relation(baseline.get(f), (candidate or {}).get(f))
                 for f in COMPARE_FIELDS}
    return {
        "raw_text": raw_text,
        "source": baseline.get("source"),
        "baseline_provider": baseline.get("ai_provider") or "unrecorded",
        "candidate_extracted": candidate is not None,
        "relations": relations,
        "candidate_violations": rule_violations(candidate, candidate_notes, raw_text),
        "baseline": {f: baseline.get(f) for f in COMPARE_FIELDS},
        "candidate": {f: (candidate or {}).get(f) for f in COMPARE_FIELDS},
    }


def summarize(comparisons: list[dict]) -> dict:
    """건별 비교 → 집계. 필드별 관계 분포 + 규칙 위반 건수."""
    n = len(comparisons)
    by_field: dict[str, dict[str, int]] = {f: {} for f in COMPARE_FIELDS}
    violations: dict[str, int] = {}
    failed = 0
    for c in comparisons:
        if not c["candidate_extracted"]:
            failed += 1
        for f, rel in c["relations"].items():
            by_field[f][rel] = by_field[f].get(rel, 0) + 1
        for v in c["candidate_violations"]:
            violations[v] = violations.get(v, 0) + 1

    overfill_total = sum(by_field[f].get("overfill", 0) for f in COMPARE_FIELDS)
    conflict_total = sum(by_field[f].get("conflict", 0) for f in COMPARE_FIELDS)
    filled_baseline = sum(
        by_field[f].get("agree", 0) + by_field[f].get("conflict", 0) + by_field[f].get("underfill", 0)
        for f in COMPARE_FIELDS)
    agree_total = sum(by_field[f].get("agree", 0) for f in COMPARE_FIELDS)

    return {
        "pairs_compared": n,
        "candidate_extraction_failures": failed,
        "field_relations": by_field,
        "overfill_total": overfill_total,
        "conflict_total": conflict_total,
        # 기존이 값을 채운 자리에서 후보가 같은 값을 낸 비율. '정확도'가 아니라
        # 일치율이다 — 기존 라벨도 검증된 정답이 아니기 때문.
        "agreement_where_baseline_filled": (
            round(agree_total / filled_baseline, 3) if filled_baseline else None),
        "rule_violations": violations,
        "interpretation": (
            "overfill은 기존 모델이 '모른다(null)'로 둔 자리를 후보 모델이 채운 "
            "횟수다. 이 태스크에서 채우는 건 대개 지어내는 것이라 높을수록 나쁘다. "
            "rule_violations의 date_invented는 원문에 연도가 아예 없는데 날짜를 "
            "만들어낸 것이라 사람 확인 없이도 오류로 셀 수 있다."),
        "not_an_accuracy_measure": (
            "기존 라벨은 검증된 정답이 아니다. 이 표는 두 모델이 어디서 갈리는지 "
            "보여줄 뿐, 어느 쪽이 옳은지는 말하지 않는다 — conflict 건은 사람이 "
            "직접 봐야 판정된다."),
    }


def run_comparison(limit: int = 50, source: str | None = None) -> dict:
    """이미 쌓인 추출 결과의 원문을 현재 NIM 설정으로 다시 뽑아 짝 비교.

    NIM이 설정 안 돼 있으면 비교 자체가 성립 안 하므로 지어내지 않고 사유만 낸다."""
    from . import aegiron_model as am

    conf = am._nim_config()
    if conf is None:
        return {"available": False,
                "reason": "NIM 미설정(NVIDIA_API_KEY 없음 또는 AEGIRON_NIM_EXTRACT=off) "
                          "— 비교할 후보 모델이 없다.",
                "pairs_compared": 0}

    rows = db.list_extracted_signals(limit=limit)
    if source:
        rows = [r for r in rows if r.get("source") == source]

    comparisons = []
    for r in rows:
        raw_text = (r.get("raw_text") or "").strip()
        if not raw_text:
            continue
        content = am.nim_raw(raw_text, conf)
        if content is None:
            comparisons.append(compare_one(raw_text, r, None, {"json_parse_failed": False}))
            continue
        candidate, notes = parse_extraction_detailed(content, raw_text, r.get("source") or "compare")
        comparisons.append(compare_one(raw_text, r, candidate, notes))

    summary = summarize(comparisons)
    return {
        "available": True,
        "candidate_model": conf["model"],
        "candidate_provider": conf["provider"],
        "candidate_sovereign": conf["sovereign"],
        **summary,
        "comparisons": comparisons,
    }

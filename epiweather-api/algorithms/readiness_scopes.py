"""준비태세를 '범위별로' 답한다 — 정의를 고르는 대신 셋으로 나눈다.

## 왜 만들었나 (2026-09-04, A안)

발할라 준비태세 축은 8시간 내내 `대응제 5건 · 판정불가 2` 로 굳어 있었다.
그 5건은 사람이 손으로 넣은 국가 비축이고, 그것으로 위협 8종의 커버리지율을
계산해 내보내고 있었다.

늘리려고 보니 갈림길이 있었다 — **"대응제"를 무엇으로 볼 것인가.** 국내 비축
가능 품목이냐, 세계에 존재하는 대응 수단이냐. 어느 쪽을 고르든 다른 쪽 질문에는
답을 못 한다.

그래서 **고르지 않는다.** 범위를 셋으로 나누고 각각 제 출처로 답한다. 이 리포가
다른 데서 계속 해온 방식이다(교사 모델, claim_basis, evidence_class — 합치지
않고 쪼갠다).

## ★ 진짜 발견 — 둘은 이미 수집하고 있었다 ★

    국가 비축      DB 수기 5건            → readiness 가 이것만 본다
    국제 비축      WHO ICG 5종            → 수집 중인데 readiness 에 안 들어감
    임상 파이프라인  ClinicalTrials 17종    → 수집 중인데 readiness 에 안 들어감

새 API 를 붙일 필요가 없었다. `compute_readiness` 가 `db.list_countermeasures()`
만 보기 때문에, 이미 매일 받아오는 두 축이 준비태세 판정에 한 번도 반영되지
않았을 뿐이다.

## ★ 임상 단계를 '커버'라고 부르지 않는다 ★

이 파일에서 가장 조심하는 지점이다. 3상 진행 중인 백신은 **지금 쓸 수 있는
물량이 아니다.** 그래서 임상 범위에는 coverage_rate 를 내지 않는다 — 단계
분포만 낸다. 셋을 합친 하나의 "준비도 점수" 도 내지 않는다. 합치는 순간
"임상 중이니까 대비됨" 이 되어버린다.
"""
from __future__ import annotations

# 범위 정의. 각 칸이 무엇을 말하고 **무엇을 말하지 않는지**를 함께 싣는다 —
# 숫자만 떼어 자료에 옮겨도 경계선이 따라가게.
SCOPES = {
    "national_stockpile": {
        "label": "국가 비축",
        "source": "직접 등록(비공개 자료라 자동 수집 불가)",
        "means": "우리가 실제로 들고 있다고 등록된 대응제.",
        "does_not_mean": "등록이 없다고 나라에 없는 것이 아니다 — 국가 비축량은 "
                         "안보 사안이라 공개 API 가 없고, 알아내려 해서도 안 된다.",
    },
    "international_stockpile": {
        "label": "국제 비상 비축",
        "source": "WHO ICG (International Coordinating Group), Gavi 자금",
        "means": "발병 시 국제 체계에서 즉시 요청할 물량이 있다.",
        "does_not_mean": "충분하다는 뜻이 아니다 — ICG 비축도 대형 발병에서 "
                         "모자란 적이 여러 번 있었다.",
    },
    "clinical_pipeline": {
        "label": "임상 파이프라인",
        "source": "ClinicalTrials.gov API v2 (미국 NIH)",
        "means": "대응제 후보가 임상 어디까지 와 있는가.",
        "does_not_mean": "★ 커버리지가 아니다 ★ 3상 진행 중은 지금 쓸 수 있는 "
                         "물량이 아니다. 그래서 이 범위에는 커버리지율을 내지 않는다.",
    },
}

# 임상 단계 → 이 범위에서 쓰는 칸. countermeasure_pipeline 의 stage 키를 받는다.
_PIPELINE_BUCKET = {
    "approved_path": "advanced",        # 3상 이상 완료
    "late_trial": "advanced",
    "early_trial": "early",
    "research_only": "early",
    "no_registered_trial": "none",
    "stockpiled": "advanced",           # 비축된 것은 임상도 끝난 것으로 본다
    "unknown": "unknown",
}


def _resolve_ko(pathogen: str | None) -> str | None:
    """위협 이름(영문 표기 포함) → 우리 한글 표준명. 못 알아보면 None.

    ★ 못 알아본 것을 '없음'으로 접지 않는다 ★ DEFAULT_THREATS 는 영문(H5N1,
    Anthrax)이고 파이프라인 키는 한글(인플루엔자, 탄저)이다. 이 다리를 안 놓으면
    전부 미커버로 잡혀 없는 위기를 만들어낸다."""
    from .countermeasure_stockpile import stockpile_status
    status = stockpile_status(pathogen)
    return status.get("name_ko") if status.get("known") else None


def national_scope(countermeasures: list[dict], threats: list[dict]) -> dict:
    """등록된 국가 비축 기준. 판정은 compute_readiness 가 한다(중복 구현 금지)."""
    from .biodefense_readiness import compute_readiness

    if not countermeasures:
        # 시연 데이터로 채우지 않는다. 비어 있으면 비어 있다고 말한다.
        return {"scope": "national_stockpile", **SCOPES["national_stockpile"],
                "available": False,
                "reason": "등록된 대응제가 없다 — 시연값을 쓰지 않는다",
                "countermeasure_count": 0}

    r = compute_readiness(countermeasures, threats)
    cov = r["coverage"]
    return {
        "scope": "national_stockpile", **SCOPES["national_stockpile"],
        "available": True,
        "countermeasure_count": len(countermeasures),
        "covered": cov["covered"],
        "uncovered": cov["uncovered"],
        "unrated": cov["unrated"],
        "coverage_rate": cov["coverage_rate"],
        "threat_count": len(threats),
    }


def international_scope(threats: list[dict]) -> dict:
    """WHO ICG 국제 비상 비축 기준. 있다/없다/모른다 세 갈래."""
    from .countermeasure_stockpile import stockpile_status

    covered, uncovered, unknown = [], [], []
    for th in threats:
        pathogen = th.get("pathogen")
        status = stockpile_status(pathogen)
        if not status.get("known"):
            unknown.append(pathogen)            # 표에 없는 이름 — 격차가 아니다
        elif status.get("has_global_stockpile"):
            covered.append(status["name_ko"])
        else:
            uncovered.append(status["name_ko"])

    rated = len(covered) + len(uncovered)
    return {
        "scope": "international_stockpile", **SCOPES["international_stockpile"],
        "available": True,
        "covered": len(covered),
        "uncovered": len(uncovered),
        # ★ 판정 못 한 것을 격차로 세지 않는다 ★ 분모에서도 뺀다.
        "unknown": len(unknown),
        "covered_names": sorted(covered),
        "uncovered_names": sorted(uncovered),
        "unknown_names": [p for p in unknown if p],
        "coverage_rate": round(len(covered) / rated, 3) if rated else None,
        "threat_count": len(threats),
    }


def clinical_scope(threats: list[dict], pipeline_value: dict | None) -> dict:
    """임상 파이프라인 기준. **커버리지율을 내지 않는다.**"""
    if not pipeline_value or not pipeline_value.get("stages"):
        return {"scope": "clinical_pipeline", **SCOPES["clinical_pipeline"],
                "available": False,
                "reason": "임상 파이프라인 값이 아직 없다(24시간 주기)"}

    stages = pipeline_value["stages"]
    buckets: dict[str, list[str]] = {"advanced": [], "early": [], "none": [], "unknown": []}
    for th in threats:
        pathogen = th.get("pathogen")
        name_ko = _resolve_ko(pathogen)
        stage = stages.get(name_ko) if name_ko else None
        if stage is None:
            # 파이프라인이 안 물어본 병원체다. '개발 없음'과 완전히 다르다.
            buckets["unknown"].append(pathogen)
            continue
        buckets[_PIPELINE_BUCKET.get(stage, "unknown")].append(name_ko)

    return {
        "scope": "clinical_pipeline", **SCOPES["clinical_pipeline"],
        "available": True,
        "advanced": len(buckets["advanced"]),
        "early": len(buckets["early"]),
        "no_registered_trial": len(buckets["none"]),
        "unknown": len(buckets["unknown"]),
        "advanced_names": sorted(buckets["advanced"]),
        "no_registered_trial_names": sorted(buckets["none"]),
        "unknown_names": [p for p in buckets["unknown"] if p],
        "threat_count": len(threats),
        # 이 칸이 없으면 누군가 advanced/threat_count 로 비율을 만들어 쓴다.
        "coverage_rate": None,
        "why_no_coverage_rate": "임상 단계는 보유 물량이 아니다. 비율을 내면 "
                                "'임상 중이니까 대비됨'으로 읽힌다.",
    }


def readiness_by_scope(countermeasures: list[dict], threats: list[dict],
                       pipeline_value: dict | None = None) -> dict:
    """세 범위를 나란히. **합친 점수를 내지 않는다.**

    합치는 순간 서로 다른 종류의 사실이 한 숫자가 된다 — 창고에 있는 것,
    국제 체계가 들고 있는 것, 아직 임상 중인 것은 대비 수준이 전혀 다르다."""
    return {
        "scopes": {
            "national_stockpile": national_scope(countermeasures, threats),
            "international_stockpile": international_scope(threats),
            "clinical_pipeline": clinical_scope(threats, pipeline_value),
        },
        "threat_count": len(threats),
        "combined_score": None,
        "why_no_combined_score": (
            "범위마다 사실의 종류가 다르다 — 창고에 있는 것, 국제 체계가 들고 "
            "있는 것, 아직 임상 중인 것. 하나의 준비도 점수로 합치면 '임상 중이니까 "
            "대비됨'이 되어버린다. 범위별로 읽어야 뜻이 생긴다."
        ),
    }


def scope_summary(by_scope: dict | None) -> str | None:
    """로그 한 줄. 값이 없으면 None(빈 줄을 흘리지 않는다)."""
    if not by_scope or not by_scope.get("scopes"):
        return None
    s = by_scope["scopes"]
    parts = []

    nat = s["national_stockpile"]
    parts.append(f"국가비축 {nat['covered']}/{nat['threat_count']}종"
                 + (f"(판정불가 {nat['unrated']})" if nat.get("unrated") else "")
                 if nat.get("available") else "국가비축 등록없음")

    intl = s["international_stockpile"]
    parts.append(f"국제비축 {intl['covered']}/{intl['covered'] + intl['uncovered']}종"
                 + (f"(미상 {intl['unknown']})" if intl["unknown"] else ""))

    cli = s["clinical_pipeline"]
    if cli.get("available"):
        parts.append(f"임상 진전 {cli['advanced']}종·초기 {cli['early']}종"
                     + (f"·등록없음 {cli['no_registered_trial']}종"
                        if cli["no_registered_trial"] else ""))
    return " · ".join(parts)

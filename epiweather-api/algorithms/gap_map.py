"""발할라 대응제 공백 지도 — 우선 병원체 × (백신 · 치료제 · FDA 승인 · 진단 · 국내 허가) (2026-11-23).

캡틴: "치료제나 백신 같은 게 없는 항목들이 많을 거야" → 그 빈칸이 상품이다.
국제 100일 미션 보고(2025)는 코로나 외 우선 병원체 치료제 임상 후보가 11종에 27개뿐이고 진단이
가장 약한 고리라고 했다. 이 지도는 그 빈칸을 병원체별로 한 장에 보인다.

## 감시 대상 — WHO 2024 우선 병원체 체계 기반

WHO 'Pathogens prioritization: a scientific framework for epidemic and pandemic research
preparedness'(2024)는 계열(family) 단위로 우선 병원체·원형 병원체를 정했다. **원문 표는 이 작업
환경에서 직접 대조하지 못했다**(who.int 접속 불가). 그래서 항목마다 `basis` 에 근거 수준을 적는다:
2차 문헌(PMC11627490 · infezmed 2024 해설 · PMC11881517 등) 확인 / 2차 문헌 간 불일치 /
아이기론 기존 감시(생물테러 A군). 원문 대조 뒤 고칠 자리는 이 REGISTRY 하나다.

## 칸과 상태 — 모르면 모른다고 한다

상태는 다섯: approved(승인) · clinical(임상, 단계 포함) · none(없음 — '이 출처 기준') ·
undetermined(판정 안 함) · unsearchable(정의상 검색 불가, 병원체 X).
- 백신: WHO 사전적격(PQ) 목록에 있으면 approved. 없으면 ClinicalTrials.gov 백신 연구의 최고 단계.
- 치료제: ClinicalTrials.gov 치료제(항바이러스·항체·항생제) 연구의 최고 단계. 4상(시판 후)은
  어딘가에서 쓰이는 약이 있다는 뜻이라 approved 로 센다.
- FDA 승인: openFDA 라벨 적응증 검색(백신·치료제 섞임 — 종류 미구분). 주간 스냅숏.
- 진단: 손으로 든 표(DIAGNOSTICS) — 출처가 있는 것만. 나머지는 판정 안 함.
- 국내 허가: 식약처 의약품 제품 허가정보 품목명 검색(주간 스냅숏, 2026-11-23 연결). 국산·수입은 가르지
  않는다. 키(MFDS_API_KEY)가 없거나 수집 전이면 판정 안 함.
'없음'은 '그 등록부에 없다'이지 '세상에 없다'가 아니다(군사·기밀 프로그램은 미등재).
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt

# key, 한국어, 영어, 계열, 근거, ClinicalTrials 검색어, WHO PQ 백신 이름 일치어, openFDA 키
REGISTRY: list[dict] = [
    {"key": "ebola", "ko": "에볼라", "en": "Ebola", "family": "Filoviridae",
     "basis": "who2024_secondary", "ct": "Ebola", "pq": ["ebola"], "fda": "Ebola"},
    {"key": "marburg", "ko": "마버그", "en": "Marburg", "family": "Filoviridae",
     "basis": "who2024_secondary", "ct": "Marburg", "pq": [], "fda": "Marburg"},
    {"key": "lassa", "ko": "라싸열", "en": "Lassa fever", "family": "Arenaviridae",
     "basis": "who2024_secondary", "ct": "Lassa Fever", "pq": [], "fda": "Lassa"},
    {"key": "cchf", "ko": "크리미안콩고출혈열", "en": "Crimean-Congo haemorrhagic fever",
     "family": "Nairoviridae", "basis": "who2024_secondary",
     "ct": "Crimean-Congo Hemorrhagic Fever", "pq": [], "fda": "CCHF"},
    {"key": "sfts", "ko": "중증열성혈소판감소증후군(SFTS)", "en": "SFTS", "family": "Phenuiviridae",
     "basis": "who2024_secondary", "ct": "Severe Fever with Thrombocytopenia Syndrome", "pq": [],
     "fda": "SFTS"},
    {"key": "rvf", "ko": "리프트밸리열", "en": "Rift Valley fever", "family": "Phenuiviridae",
     "basis": "who2024_prototype", "ct": "Rift Valley Fever", "pq": [], "fda": "Rift Valley fever"},
    {"key": "hanta", "ko": "한타바이러스", "en": "Hantavirus", "family": "Hantaviridae",
     "basis": "who2024_secondary_conflict", "ct": "Hantavirus", "pq": [], "fda": "Hantavirus"},
    {"key": "nipah", "ko": "니파", "en": "Nipah", "family": "Paramyxoviridae",
     "basis": "who2024_secondary", "ct": "Nipah Virus", "pq": [], "fda": "Nipah"},
    {"key": "flu_pandemic", "ko": "범유행 인플루엔자 A(H1–3·H5–7·H10)", "en": "Pandemic influenza A",
     "family": "Orthomyxoviridae", "basis": "who2024_secondary", "ct": "Avian Influenza",
     "pq": ["influenza, pandemic"], "fda": "H5N1"},
    {"key": "mers", "ko": "메르스", "en": "MERS", "family": "Coronaviridae",
     "basis": "who2024_family", "ct": "MERS-CoV", "pq": [], "fda": "MERS"},
    {"key": "sars2", "ko": "SARS-CoV-2", "en": "SARS-CoV-2", "family": "Coronaviridae",
     "basis": "who2024_family", "ct": "COVID-19", "pq": ["covid-19"], "fda": "COVID-19"},
    {"key": "mpox", "ko": "엠폭스", "en": "Mpox", "family": "Poxviridae",
     "basis": "who2024_secondary", "ct": "Mpox", "pq": ["mpox"], "fda": "Mpox"},
    {"key": "smallpox", "ko": "두창", "en": "Smallpox", "family": "Poxviridae",
     "basis": "who2024_secondary", "ct": "Smallpox", "pq": ["smallpox"], "fda": "Smallpox"},
    {"key": "yellow_fever", "ko": "황열", "en": "Yellow fever", "family": "Flaviviridae",
     "basis": "who2024_secondary", "ct": "Yellow Fever", "pq": ["yellow fever"], "fda": "Yellow fever"},
    {"key": "dengue", "ko": "뎅기", "en": "Dengue", "family": "Flaviviridae",
     "basis": "aegiron_existing", "ct": "Dengue", "pq": ["dengue"], "fda": "Dengue"},
    {"key": "zika", "ko": "지카", "en": "Zika", "family": "Flaviviridae",
     "basis": "who2024_secondary_conflict", "ct": "Zika", "pq": [], "fda": "Zika"},
    {"key": "chikungunya", "ko": "치쿤구니야", "en": "Chikungunya", "family": "Togaviridae",
     "basis": "who2024_secondary", "ct": "Chikungunya", "pq": [], "fda": "Chikungunya"},
    {"key": "veev", "ko": "베네수엘라말뇌염", "en": "Venezuelan equine encephalitis",
     "family": "Togaviridae", "basis": "who2024_secondary",
     "ct": "Venezuelan Equine Encephalitis", "pq": [], "fda": "VEEV"},
    {"key": "enterovirus", "ko": "엔테로바이러스(EV-D68·EV-A71)", "en": "Enterovirus",
     "family": "Picornaviridae", "basis": "who2024_secondary_conflict", "ct": "Enterovirus",
     "pq": [], "fda": "Enterovirus"},
    {"key": "plague", "ko": "페스트", "en": "Plague", "family": "세균",
     "basis": "who2024_secondary", "ct": "Plague", "pq": [], "fda": "Plague"},
    {"key": "cholera", "ko": "콜레라", "en": "Cholera", "family": "세균",
     "basis": "who2024_secondary", "ct": "Cholera", "pq": ["cholera"], "fda": "Cholera"},
    {"key": "shigella", "ko": "이질(S. dysenteriae 1형)", "en": "Shigella", "family": "세균",
     "basis": "who2024_secondary", "ct": "Shigella", "pq": [], "fda": "Shigella"},
    {"key": "klebsiella", "ko": "폐렴막대균", "en": "Klebsiella pneumoniae", "family": "세균",
     "basis": "who2024_secondary_conflict", "ct": "Klebsiella pneumoniae", "pq": [],
     "fda": "Klebsiella"},
    {"key": "salmonella_nts", "ko": "비장티푸스 살모넬라", "en": "Non-typhoidal Salmonella",
     "family": "세균", "basis": "who2024_secondary_conflict", "ct": "Salmonella Infections",
     "pq": [], "fda": "Salmonella"},
    {"key": "anthrax", "ko": "탄저", "en": "Anthrax", "family": "세균",
     "basis": "aegiron_existing", "ct": "Anthrax", "pq": [], "fda": "Anthrax"},
    {"key": "tularemia", "ko": "야토병", "en": "Tularemia", "family": "세균",
     "basis": "aegiron_existing", "ct": "Tularemia", "pq": [], "fda": "Tularemia"},
    {"key": "pathogen_x", "ko": "병원체 X(미지)", "en": "Pathogen X", "family": "—",
     "basis": "who2024_placeholder", "ct": None, "pq": [], "fda": "Novel"},
]

BASIS_KO = {
    "who2024_secondary": "WHO 2024 우선 병원체 — 2차 문헌 확인(원문 미대조)",
    "who2024_prototype": "WHO 2024 원형 병원체 — 2차 문헌 확인(원문 미대조)",
    "who2024_family": "WHO 2024 우선 계열(코로나바이러스과) — 개별 병원체 지정은 원문 미대조",
    "who2024_secondary_conflict": "WHO 2024 — 2차 문헌 간 등급·포함 여부 불일치(원문 대조 필요)",
    "who2024_placeholder": "WHO 2024 '병원체 X' — 아직 모르는 위협의 자리",
    "aegiron_existing": "아이기론 기존 감시(WHO 2024 원문 포함 여부 미대조)",
}

# openFDA 라벨 적응증 검색어 — approved_products.THREAT_SEARCH_TERMS 에 합쳐 주간 스냅숏이 조회한다.
FDA_TERMS: dict[str, list[str]] = {
    "Marburg": ["marburg"], "Lassa": ["lassa"], "CCHF": ["crimean-congo"],
    "SFTS": ["severe fever with thrombocytopenia"], "Rift Valley fever": ["rift valley"],
    "Hantavirus": ["hantavirus"], "Nipah": ["nipah"], "COVID-19": ["covid-19"],
    "Mpox": ["mpox", "monkeypox"], "Smallpox": ["smallpox"], "Yellow fever": ["yellow fever"],
    "Zika": ["zika"], "Chikungunya": ["chikungunya"], "VEEV": ["venezuelan equine encephalitis"],
    "Enterovirus": ["enterovirus"], "Cholera": ["cholera"], "Shigella": ["shigella"],
    "Klebsiella": ["klebsiella pneumoniae"], "Salmonella": ["salmonella"],
}

# 식약처 품목명 검색어(국내 허가 분기 — 키 집합은 openFDA 표와 같아야 한다).
DOMESTIC_TERMS: dict[str, list[str]] = {
    "Marburg": ["마버그"], "Lassa": ["라싸"], "CCHF": ["크리미안콩고"], "SFTS": ["중증열성혈소판감소"],
    "Rift Valley fever": ["리프트밸리"], "Hantavirus": ["한타", "신증후군출혈열"], "Nipah": ["니파"],
    "COVID-19": ["코로나19", "COVID-19"], "Mpox": ["엠폭스", "원숭이두창"], "Smallpox": ["두창"],
    "Yellow fever": ["황열"], "Zika": ["지카"], "Chikungunya": ["치쿤구니야"],
    "VEEV": ["베네수엘라"], "Enterovirus": ["엔테로바이러스"], "Cholera": ["콜레라"],
    "Shigella": ["이질"], "Klebsiella": ["폐렴막대균", "클렙시엘라"], "Salmonella": ["살모넬라"],
}

# 진단 — 출처가 있는 것만. 없으면 판정 안 함(빈칸을 '없음'으로 채우지 않는다).
# status: approved = 미국 FDA 허가(510(k)/De Novo) 진단이 있음 · limited = 실험실 분자검사는 있으나
# 검증된 신속진단이 없다는 문헌.
DIAGNOSTICS: dict[str, dict] = {
    "ebola": {"status": "approved", "note": "FDA De Novo 신속항원검사(OraQuick Ebola, 2019)",
              "source": "https://www.fda.gov/emergency-preparedness-and-response/medical-countermeasure-mcm-issues/ebola"},
    "mpox": {"status": "approved", "note": "FDA 510(k) 비두창 오르토폭스바이러스 PCR(CDC, 2018·2022)",
             "source": "https://www.fda.gov/medical-devices/emergency-situations-medical-devices/monkeypox-mpox-and-medical-devices"},
    "zika": {"status": "approved", "note": "FDA 허가 IgM 검사(DPP Zika IgM 2020, ADVIA Centaur Zika 2019)",
             "source": "https://www.fda.gov/emergency-preparedness-and-response/medical-countermeasure-mcm-issues/zika-virus"},
    "dengue": {"status": "approved", "note": "FDA 510(k) NS1 ELISA(InBios DENV Detect, K181473)",
               "source": "https://www.accessdata.fda.gov/cdrh_docs/reviews/K181473.pdf"},
    "nipah": {"status": "limited", "note": "검증된 고감도 신속진단 없음(2024 문헌) — 실험실 분자검사만",
              "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11085978"},
    "lassa": {"status": "limited", "note": "검증된 고감도 신속진단 없음(2024 문헌) — 실험실 분자검사만",
              "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11085978"},
    "mers": {"status": "limited", "note": "검증된 고감도 신속진단 없음(2024 문헌) — 실험실 분자검사만",
             "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11085978"},
}
DIAGNOSTICS_CHECKED = "2026-11-23"

STATUSES = ("approved", "clinical", "none", "undetermined", "unsearchable")
_PHASE4 = 6  # countermeasure_pipeline._PHASE_RANK 의 4상(시판 후)

# ClinicalTrials.gov 개입 검색어 — 백신과 치료제를 따로 묻는다(countermeasure_pipeline 과 같은 API).
VACCINE_INTR = "vaccine"
THERAPEUTIC_INTR = "antiviral OR monoclonal antibody OR antibiotic OR antitoxin"
FETCH_WORKERS = 6
FETCH_TIMEOUT = 20


def _cell(status: str, label: str, **extra) -> dict:
    assert status in STATUSES, status
    return {"status": status, "label": label, **extra}


def fetch_trials(fetch=None) -> dict:
    """병원체마다 백신·치료제 임상 최고 단계를 ClinicalTrials.gov 에서. 하루 한 번(발할라 무거운 조각).

    병원체 하나가 실패해도 나머지는 계속한다 — 실패는 그 칸만 판정 안 함."""
    if fetch is None:
        from .countermeasure_pipeline import fetch_pipeline

        def fetch(query: str, intr: str) -> dict:
            return fetch_pipeline(query, timeout=FETCH_TIMEOUT, intr=intr)
    jobs = [(r["key"], kind, r["ct"], intr) for r in REGISTRY if r["ct"]
            for kind, intr in (("vaccine", VACCINE_INTR), ("therapeutic", THERAPEUTIC_INTR))]
    out: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        futs = {ex.submit(fetch, q, intr): (key, kind) for key, kind, q, intr in jobs}
        for fut in concurrent.futures.as_completed(futs):
            key, kind = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:                      # noqa: BLE001
                res = {"available": False, "reason": f"조회 실패: {type(exc).__name__}"}
            out.setdefault(key, {})[kind] = res
    return {"by_pathogen": out, "fetched": len(jobs)}


def _trial_cell(res: dict | None) -> dict:
    if not res:
        return _cell("undetermined", "임상 조회 전")
    if not res.get("available"):
        return _cell("undetermined", res.get("reason") or "조회 실패")
    if not res.get("study_count"):
        return _cell("none", "등록 연구 없음")
    rank = res.get("furthest_phase") or 0
    phase = res.get("furthest_phase_ko") or "단계 미표기"
    if rank >= _PHASE4:
        return _cell("approved", f"시판 후 연구({phase})", studies=res.get("study_count"))
    return _cell("clinical", phase, studies=res.get("study_count"), phase_rank=rank)


def _pq_match(entry: dict, pq_snapshot: dict | None) -> list[str] | None:
    """WHO 사전적격 백신 목록에서 이름이 맞는 백신 종류. 스냅숏이 없으면 None(모름)."""
    if not pq_snapshot:
        return None
    names = {r.get("vaccine_type", "") for r in pq_snapshot.get("records") or []}
    hits = sorted(n for n in names if any(t in n.lower() for t in entry["pq"]))
    return hits


def _vaccine_cell(entry: dict, pq_snapshot: dict | None, trials: dict | None) -> dict:
    hits = _pq_match(entry, pq_snapshot)
    if hits:
        return _cell("approved", "WHO 사전적격", products=hits[:3])
    cell = _trial_cell((trials or {}).get("vaccine"))
    if hits is None and cell["status"] in ("none", "undetermined"):
        # PQ 목록을 못 읽었으면 '없음'이라 말하지 않는다.
        return _cell("undetermined", "WHO 사전적격 목록을 못 읽음")
    return cell


def _fda_cell(entry: dict, approved_snapshot: dict | None) -> dict:
    from .approved_products import products_for
    res = products_for(entry["fda"], approved_snapshot)
    st = res.get("status")
    if st == "approved":
        return _cell("approved", f"승인 제품 {res.get('product_count')}종",
                     products=res.get("examples") or [])
    if st == "none":
        return _cell("none", "FDA 라벨에 이 적응증 없음")
    if st == "unsearchable":
        return _cell("unsearchable", res.get("reason") or "검색 불가")
    return _cell("undetermined", res.get("reason") or "모름")


def _domestic_cell(entry: dict, domestic_snapshot: dict | None) -> dict:
    if domestic_snapshot is None:
        return _cell("undetermined", "식약처 자료 없음(키 미설정 또는 수집 전)")
    from .approved_products import domestic_products_for
    res = domestic_products_for(entry["fda"], domestic_snapshot)
    st = res.get("status")
    if st == "approved":
        return _cell("approved", f"국내 허가 {res.get('product_count')}품목",
                     products=res.get("examples") or [])
    if st == "none":
        return _cell("none", "품목명 검색 0건(허가 없음 단정 아님)")
    if st == "unsearchable":
        return _cell("unsearchable", res.get("reason") or "검색 불가")
    return _cell("undetermined", res.get("reason") or "모름")


def _diag_cell(entry: dict) -> dict:
    d = DIAGNOSTICS.get(entry["key"])
    if not d:
        return _cell("undetermined", "출처 확인 전")
    status = "approved" if d["status"] == "approved" else "clinical"
    return _cell(status, d["note"], source=d["source"], checked=DIAGNOSTICS_CHECKED)


def build(pq_snapshot: dict | None, approved_snapshot: dict | None, trials: dict | None,
          trials_age_hours: float | None = None, domestic_snapshot: dict | None = None) -> dict:
    """공백 지도 한 장. 네트워크를 쓰지 않는다(스냅숏·저장본만 읽는다)."""
    by = (trials or {}).get("by_pathogen") or {}
    rows = []
    for e in REGISTRY:
        if e["key"] == "pathogen_x":
            unknown = _cell("unsearchable", "정의상 검색 불가 — 아직 이름이 없는 병원체")
            cells = {"vaccine": unknown, "therapeutic": unknown, "fda": unknown,
                     "diagnostic": unknown}
        else:
            t = by.get(e["key"]) if trials is not None else None
            cells = {
                "vaccine": _vaccine_cell(e, pq_snapshot, t),
                "therapeutic": _trial_cell((t or {}).get("therapeutic")) if trials is not None
                else _cell("undetermined", "임상 조회 전"),
                "fda": _fda_cell(e, approved_snapshot),
                "diagnostic": _diag_cell(e),
            }
        cells["domestic"] = (_cell("unsearchable", "정의상 검색 불가 — 아직 이름이 없는 병원체")
                             if e["key"] == "pathogen_x" else _domestic_cell(e, domestic_snapshot))
        no_countermeasure = all(cells[k]["status"] in ("none", "clinical")
                                for k in ("vaccine", "therapeutic", "fda"))
        rows.append({"key": e["key"], "ko": e["ko"], "en": e["en"], "family": e["family"],
                     "basis": e["basis"], "basis_ko": BASIS_KO[e["basis"]],
                     "cells": cells, "countermeasure_gap": no_countermeasure})
    gaps = [r["ko"] for r in rows if r["countermeasure_gap"]]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pathogen_count": len(rows),
        "gap_count": len(gaps),
        "gap_pathogens": gaps,
        "gap_rule_ko": "백신·치료제·FDA 승인 세 칸이 모두 '없음' 또는 '임상 중'이면 대응제 공백"
                       "(판정 안 함 칸이 하나라도 있으면 공백으로 세지 않는다)",
        "trials_age_hours": trials_age_hours,
        "sources": {
            "vaccine": "WHO 사전적격 백신 목록(주간 스냅숏) → 없으면 ClinicalTrials.gov 백신 연구",
            "therapeutic": "ClinicalTrials.gov 치료제(항바이러스·항체·항생제·항독소) 연구, 하루 1회",
            "fda": "openFDA 라벨 적응증 검색(백신·치료제 섞임), 주간 스냅숏",
            "diagnostic": f"손으로 든 표 — 출처 있는 항목만({DIAGNOSTICS_CHECKED} 확인)",
            "domestic": ("식약처 의약품 제품 허가정보 품목명 검색(주간 스냅숏) — 국산·수입 미구분, "
                         "품목명에 질병명이 없으면 안 걸림" if domestic_snapshot is not None
                         else "식약처 자료 없음(키 미설정 또는 수집 전) — 전부 판정 안 함"),
            "registry": "WHO 2024 병원체 우선순위 체계 — 2차 문헌 기반(원문 표 미대조)",
        },
        "rows": rows,
    }


def current() -> dict:
    """저장본·스냅숏으로 지금 공백 지도를 만든다(네트워크 없음). API·수집 로그가 같이 쓴다."""
    from . import valhalla_watch, vaccine_supply
    from .reference_snapshots import _load
    state = valhalla_watch._load_state().get("gap_trials") or {}
    age = valhalla_watch._age_hours(state.get("fetched_at"), valhalla_watch._now())
    try:
        approved = _load("approved_products")
    except Exception:                                     # noqa: BLE001
        approved = None
    try:
        domestic = _load("domestic_products")
    except Exception:                                     # noqa: BLE001
        domestic = None
    return build(vaccine_supply._snapshot(), approved, state.get("value"), age, domestic)


def summary_line(m: dict) -> str:
    """로그 한 줄: 🗺 공백 지도: 27개 중 공백 4개(니파·…) · 판정 안 함 칸 12"""
    undetermined = sum(1 for r in m["rows"] for c in r["cells"].values()
                       if c["status"] == "undetermined")
    names = "·".join(m["gap_pathogens"][:6]) + ("…" if len(m["gap_pathogens"]) > 6 else "")
    age = m.get("trials_age_hours")
    age_txt = f" · 임상 {age}시간 전 값" if age is not None else " · 임상 조회 전"
    return (f"🗺 공백 지도: {m['pathogen_count']}개 중 공백 {m['gap_count']}개"
            + (f"({names})" if names else "") + f" · 판정 안 함 칸 {undetermined}{age_txt}")

"""규제 승인 제품 — "쓸 수 있게 허가된 물건이 세상에 있는가" (2026-09-04, A-2).

## 왜 네 번째 범위인가

A안에서 준비태세를 셋으로 나눴다. 그런데 그 셋 사이에 큰 구멍이 있었다.

    국가 비축      1/8종   ← 우리가 들고 있는 것
    국제 비축      1/5종   ← ICG 가 들고 있는 것
    임상 파이프라인  진전 4종  ← 아직 개발 중인 것

    ??? 이미 허가가 끝났는데 아무도 안 비축한 것은 어디에 잡히나?

탄저(BioThrax·raxibacumab), 에볼라(ERVEBO·Inmazeb), 야토병(독시사이클린) 처럼
**승인은 끝났는데 우리 비축 목록엔 없는** 것들이 어느 칸에도 안 들어갔다.
비축 축은 "없음", 임상 축은 "이미 끝남" 이라 조용하다.

이 구분이 대비 우선순위를 완전히 바꾼다:

    승인 제품 없음 → 개발부터. 몇 년 단위.
    승인 제품 있음 → 조달·계약부터. 몇 달 단위.

## ★ 이것을 '국가 비축' 에 부으면 안 된다 ★

openFDA 를 국가 비축 축에 넣고 싶은 유혹이 있는데, 그건 범주 오류다.
**미국에서 허가됐다는 것과 한국이 비축했다는 것은 아무 관계가 없다.**
섞으면 "국가비축 6/8종" 같은 숫자가 나오고, 그건 거짓이다.
국가 비축량은 비공개이고 알아내려 해서도 안 된다(readiness_scopes 참고).

## ★ 이 파일이 말하지 않는 것 ★

- **물량을 말하지 않는다.** 허가된 제품이 있다는 것이지 살 수 있다는 뜻이 아니다.
  생산량·재고·수출통제는 이 자료에 없다.
- **한국에서 쓸 수 있다는 뜻이 아니다.** openFDA 는 미국 허가다. 국내 허가는
  식약처 자료가 필요한데, 공공데이터포털 활용신청이 아직 안 돼 있다(2026-09-02
  실측: "등록되지 않은 서비스키"). 그래서 국내 허가 여부는 **모른다고 말한다.**
- **효능을 말하지 않는다.** 허가는 그 적응증에 대해 심사를 통과했다는 뜻이지
  변이 회피나 실전 효과를 보장하지 않는다.
- **없다고 개발이 없는 것도 아니다.** 군사·기밀 프로그램은 이 목록에 없다.
"""
from __future__ import annotations

# 위협 → openFDA 적응증 검색어. **우리 표기가 아니라 라벨 표기로 물어야 한다.**
# ★ 검색어를 빼면 안 된다 ★ 빼면 "안 찾아봤다"가 "없다"로 접힌다. 그 둘은 다르다.
THREAT_SEARCH_TERMS: dict[str, list[str]] = {
    "Anthrax": ["anthrax"],
    "Ebola": ["ebola", "zaire ebolavirus"],
    "Plague": ["plague", "yersinia pestis"],
    "Tularemia": ["tularemia", "francisella tularensis"],
    "H5N1": ["influenza a virus h5n1", "h5n1", "pandemic influenza"],
    "Dengue": ["dengue"],
    "MERS": ["middle east respiratory syndrome", "mers-cov"],
    # ★ Novel 은 정의상 검색이 불가능하다 ★ 아직 이름이 없는 병원체라 적응증에
    # 걸릴 낱말이 없다. '없음'이 아니라 '정의상 불가'로 따로 센다 — 이걸 0으로
    # 접으면 신종 위협이 "승인 제품 없는 병" 목록에 섞여 우선순위를 흐린다.
    "Novel": [],
}

# 검색어가 비어 있는 위협의 사유. 값 옆에 실어 보낸다.
UNSEARCHABLE_REASON = {
    "Novel": "정의상 검색 불가 — 아직 이름이 없는 병원체에는 적응증 낱말이 없다",
}


def searchable(pathogen: str | None) -> bool:
    return bool(THREAT_SEARCH_TERMS.get(pathogen or ""))


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def products_for(pathogen: str | None, snapshot: dict | None) -> dict:
    """그 위협에 대해 승인된 제품이 스냅샷에 있는가. **모르면 모른다고 한다.**"""
    if snapshot is None:
        return {"status": "unknown", "reason": "승인 제품 스냅샷이 없다"}

    terms = THREAT_SEARCH_TERMS.get(pathogen or "")
    if terms is None:
        # 검색어 표에 아예 없는 위협 — 안 찾아본 것이다.
        return {"status": "unknown",
                "reason": f"검색어 표에 없는 위협: {pathogen}"}
    if not terms:
        return {"status": "unsearchable",
                "reason": UNSEARCHABLE_REASON.get(pathogen, "검색 불가")}

    by_threat = snapshot.get("by_threat") or {}
    entry = by_threat.get(pathogen)
    if entry is None:
        # 스냅샷을 뜰 때 이 위협을 안 물어봤다. 없는 것과 다르다.
        return {"status": "unknown",
                "reason": "이 스냅샷이 조회하지 않은 위협"}

    count = entry.get("product_count") or 0
    if count <= 0:
        return {"status": "none", "product_count": 0,
                "note": "이 등록부에 승인 제품이 없다. 개발이 없다는 뜻이 아니라 "
                        "미국 FDA 라벨에 이 적응증이 없다는 뜻이다."}
    return {
        "status": "approved",
        "product_count": count,
        "examples": (entry.get("examples") or [])[:3],
    }


def approved_scope(threats: list[dict], snapshot: dict | None) -> dict:
    """승인 제품 범위. 있다 / 없다 / 모른다 / 검색불가 네 갈래."""
    from .readiness_scopes import SCOPES

    approved, none, unknown, unsearchable_list = [], [], [], []
    examples: dict[str, list[str]] = {}
    for th in threats:
        pathogen = th.get("pathogen")
        result = products_for(pathogen, snapshot)
        status = result["status"]
        if status == "approved":
            approved.append(pathogen)
            examples[pathogen] = result.get("examples") or []
        elif status == "none":
            none.append(pathogen)
        elif status == "unsearchable":
            unsearchable_list.append(pathogen)
        else:
            unknown.append(pathogen)

    if snapshot is None:
        return {"scope": "approved_products", **SCOPES["approved_products"],
                "available": False,
                "reason": "승인 제품 스냅샷이 아직 없다(주간 갱신 대상)"}

    # ★ 분모에서 '모른다'와 '검색불가'를 뺀다 ★ 넣으면 안 찾아본 것 때문에
    # 승인률이 낮아져 없는 격차를 만든다.
    rated = len(approved) + len(none)
    return {
        "scope": "approved_products", **SCOPES["approved_products"],
        "available": True,
        "approved": len(approved),
        "none": len(none),
        "unknown": len(unknown),
        "unsearchable": len(unsearchable_list),
        "approved_names": sorted(approved),
        "none_names": sorted(none),
        "unknown_names": sorted(n for n in unknown if n),
        "unsearchable_names": sorted(n for n in unsearchable_list if n),
        "examples": examples,
        "approval_rate": round(len(approved) / rated, 3) if rated else None,
        "snapshot_date": snapshot.get("snapshot_date"),
        # 국내 허가는 별개의 사실이고 아직 못 본다. 모른다고 말한다.
        "domestic_approval": "unknown",
        "domestic_reason": (
            "식약처 의약품 허가 자료는 공공데이터포털 활용신청이 안 돼 있다"
            "(2026-09-02 실측: 등록되지 않은 서비스키). 신청이 되면 붙인다."
        ),
    }


def approved_summary(scope: dict | None) -> str | None:
    """로그 한 줄. 값이 없으면 None."""
    if not scope or not scope.get("available"):
        return None
    parts = [f"승인 {scope['approved']}종", f"없음 {scope['none']}종"]
    if scope.get("unknown"):
        parts.append(f"미조회 {scope['unknown']}종")
    if scope.get("unsearchable"):
        parts.append(f"검색불가 {scope['unsearchable']}종")
    line = " · ".join(parts)
    # 비축은 없는데 승인은 있는 것 — 조달부터 시작하면 되는 칸이다.
    if scope.get("approved_names"):
        line += f" [승인: {'·'.join(scope['approved_names'])}]"
    return line

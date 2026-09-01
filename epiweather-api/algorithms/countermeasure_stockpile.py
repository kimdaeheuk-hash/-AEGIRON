"""대응제 비축 격차 — "막을 물량이 세상에 있는가" (2026-09-01).

## 왜 만들었나

캡틴 지적: *"그래서 우리가 어떻게 대비를 해야 하는지 찾아봐! 아이기론은
국가 안보 분야도 다뤄야 해!"*

아이기론엔 이미 대비를 다루는 층이 있다 — 8단계 VALHALLA(`biodefense_readiness`).
그런데 그건 **계산기**다. 비축 목록을 입력받아야 돌아가는데 아무도 안 넣고
있어서, 지금 도는 것은 `illustrative`(시연용 예시)뿐이었다.

## 그래서 조사했다 — 국가 비축은 못 본다

    질병관리청 공공데이터   접종 통계는 공개, **비축 재고는 비공개**
    WHO ICG               비축을 운영하지만 재고 수준 공개 API 없음

당연하다. 국가 비축량은 안보 사안이다. **그걸 알아내려 해서도 안 된다.**

## 대신 공개되는 것이 하나 있다

**어떤 질병에 국제 비상 비축이 존재하는가** 는 공개돼 있다.

    WHO ICG (International Coordinating Group), Gavi 자금:
      황열 · 수막구균 · 콜레라 · 에볼라  (기존 4종)
      엠폭스                            (2025-11 신설)

이게 VALHALLA 가 묻는 커버리지 격차와 같은 질문이다. "우리 창고에 뭐가 있나"
는 못 봐도, **"이 병에 세계가 즉시 꺼낼 물량이 있는가"** 는 볼 수 있다.

## ★ 이 파일이 말하지 않는 것 ★

- **재고량을 말하지 않는다.** 비축이 "있다" 는 것이지 "충분하다" 가 아니다.
  ICG 비축도 대형 발병에서는 모자란 적이 여러 번 있었다.
- **한국 비축을 말하지 않는다.** 비공개이고, 모르는 것을 추정하지 않는다.
- **효능을 예측하지 않는다.** 변이별 회피는 구조·면역 모델링의 영역이고,
  파이썬 수식으로 흉내내면 가짜 정밀도가 된다(VALHALLA docstring 의 원칙).

여기서 내는 것은 **"국제 비상 비축 체계 안에 있는가 없는가"** 라는 이분법뿐이다.
그리고 그 이분법만으로도 쓸모가 있다 — 없는 쪽은 발병하면 조달부터 시작해야
한다는 뜻이기 때문이다.
"""
from __future__ import annotations

# ── WHO ICG 국제 비상 비축 (공개 정보) ──────────────────────────────────────
# 근거: WHO ICG on Vaccine Provision(1997년 설립) · Gavi 자금 지원.
# 확인일 2026-09-01. 비축 종류가 늘면 여기에 추가한다.
ICG_STOCKPILES: dict[str, dict] = {
    "yellow_fever": {
        "name_ko": "황열", "since": 1997,
        "aliases": ["yellow fever", "황열", "황열병"],
    },
    "meningitis": {
        "name_ko": "수막구균 수막염", "since": 1997,
        "aliases": ["meningitis", "meningococcal", "수막염", "수막구균", "뇌수막염"],
    },
    "cholera": {
        "name_ko": "콜레라", "since": 2013,
        "aliases": ["cholera", "콜레라"],
    },
    "ebola": {
        "name_ko": "에볼라", "since": 2021,
        "aliases": ["ebola", "에볼라", "ebola virus disease", "evd"],
    },
    "mpox": {
        "name_ko": "엠폭스", "since": 2025,
        "aliases": ["mpox", "monkeypox", "엠폭스", "원숭이두창"],
    },
}

# ── 비축은 없지만 아이기론이 실제로 신호를 잡는 위협 ────────────────────────
# ★ 이 목록은 "위험 순위" 가 아니다 ★ 아이기론 신호에 자주 나오는데 ICG 비축
# 체계에 없는 것들이고, 그 사실 자체가 격차다. 여기 없는 병이 안전한 것도 아니다.
KNOWN_GAP_ALIASES: dict[str, list[str]] = {
    "인플루엔자(조류·계절)": ["influenza", "flu", "h5n1", "h1n1", "h7n9", "h5n2",
                            "인플루엔자", "독감", "조류인플루엔자", "조류독감"],
    "뎅기열": ["dengue", "뎅기", "덴기", "덴그", "덴게"],
    "말라리아": ["malaria", "말라리아"],
    "홍역": ["measles", "홍역"],
    "MERS": ["mers", "메르스", "middle east respiratory"],
    "한타바이러스": ["hantavirus", "한타", "안데스바이러스", "andes virus"],
    "니파": ["nipah", "니파"],
    "라싸열": ["lassa", "라싸"],
    "마버그": ["marburg", "마버그", "마르부르크"],
    "치쿤구니야": ["chikungunya", "치쿤구니야"],
    "지카": ["zika", "지카"],
    "탄저": ["anthrax", "탄저"],
}


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def stockpile_status(disease: str | None) -> dict:
    """그 질병에 국제 비상 비축이 있는가.

    ★ 세 가지 답이 있다 ★ 있다 / 없다 / **모른다**.
    모르는 것을 "없다" 로 접으면, 이름을 못 알아본 병이 전부 격차로 잡혀
    없는 위기를 만들어낸다.
    """
    key = _norm(disease)
    if not key:
        return {"known": False, "reason": "질병명이 비어 있음"}

    for sid, entry in ICG_STOCKPILES.items():
        if any(a in key for a in entry["aliases"]):
            return {
                "known": True, "has_global_stockpile": True,
                "stockpile_id": sid, "name_ko": entry["name_ko"],
                "since": entry["since"], "mechanism": "WHO ICG",
            }

    for name, aliases in KNOWN_GAP_ALIASES.items():
        if any(a in key for a in aliases):
            return {
                "known": True, "has_global_stockpile": False,
                "name_ko": name, "mechanism": None,
            }

    # 표에 없는 이름. "비축 없음" 이 아니라 "모른다" 이다.
    return {"known": False, "reason": f"표에 없는 질병명: {disease}"}


def gap_report(diseases: list[str | None]) -> dict:
    """감시 중인 질병 목록 → 비축 격차. 모르는 것은 모른다고 센다."""
    covered, gaps, unknown = [], [], []
    for d in diseases:
        s = stockpile_status(d)
        if not s["known"]:
            unknown.append(d)
        elif s["has_global_stockpile"]:
            covered.append(s["name_ko"])
        else:
            gaps.append(s["name_ko"])

    return {
        "covered": sorted(set(covered)),
        "gaps": sorted(set(gaps)),
        # ★ 판정 못 한 것을 격차로 넣지 않는다 ★ 따로 센다.
        "unclassified": [d for d in unknown if d],
        "unclassified_count": len(unknown),
        "stockpile_mechanism": "WHO ICG (International Coordinating Group), Gavi 자금",
        "stockpile_list": [v["name_ko"] for v in ICG_STOCKPILES.values()],
        "limits": [
            "비축이 '있다'는 것이지 '충분하다'가 아니다 — ICG 비축도 대형 발병에서 "
            "모자란 적이 있다.",
            "한국 국가 비축은 비공개다. 이 보고는 국제 비상 비축 체계만 본다.",
            "효능·변이 회피를 예측하지 않는다. 그건 구조·면역 모델링의 영역이다.",
            "격차 목록은 위험 순위가 아니다. 여기 없는 병이 안전한 것도 아니다.",
        ],
    }

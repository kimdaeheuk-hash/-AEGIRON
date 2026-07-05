"""국가별 위험지수 — 인수인계서 Part5 ⑨.

최종 국가위험도 = 원시위험도 × 국가취약성지수.

원시위험도는 두 갈래를 합쳐 만든다:
  1) collector.py 직접수치 — KDCA(한국)·InfoDengue(브라질)·IDWR(일본)·CHP(홍콩)처럼
     국가 단위로 떨어지는 신호는 gai.py와 같은 z-score 이상도를 재사용.
  2) NLP 구조화 추출(⑦, extracted_signals) — location 필드에 해당 국가명이 매칭되는
     기록들의 출처신뢰도 가중 심각도 평균.
  둘 다 있으면 평균, 하나만 있으면 그것만, 둘 다 없으면 None(랭킹 하단으로).

국가취약성지수 4요소(의료인프라·인구밀도·공항연결성·국경이동량, 0~1)는
WHO Global Health Observatory·World Bank·OpenFlights·UNWTO 실연동 전까지
직접 추정한 시드값이다 — 인수인계서 Part2가 이 4개 소스를 전부 "추가 필요"로
분류해놓아서 아직 연결된 API가 없음. 실제 API 연동 전까지의 근사치라는 점을
명확히 하고, 시드 테이블에 없는 국가는 중립값(0.5)을 씀.
"""
from __future__ import annotations
import statistics

import db
from .gai import _anomaly_score, _tier
from .signal_metrics import (
    load_records, _kdca_latest_total, _japan_idwr_total, _hk_chp_total, _infodengue_total,
)

# (국가ID: 한국어명·매칭별칭·취약성 4요소[0~1, 추정 시드값])
COUNTRIES = {
    "DRC": {
        "name": "콩고민주공화국", "aliases": ["DRC", "콩고민주공화국", "콩고", "Congo"],
        "healthcare_infra": 0.25, "population_density": 0.55,
        "airport_connectivity": 0.15, "border_mobility": 0.55,
    },
    "Uganda": {
        "name": "우간다", "aliases": ["우간다", "Uganda"],
        "healthcare_infra": 0.30, "population_density": 0.50,
        "airport_connectivity": 0.20, "border_mobility": 0.50,
    },
    "Saudi Arabia": {
        "name": "사우디아라비아", "aliases": ["사우디", "사우디아라비아", "Saudi"],
        "healthcare_infra": 0.70, "population_density": 0.20,
        "airport_connectivity": 0.55, "border_mobility": 0.75,  # 하지 순례 — 단기 대규모 국경이동
    },
    "Thailand": {
        "name": "태국", "aliases": ["태국", "Thailand", "방콕", "Bangkok"],
        "healthcare_infra": 0.60, "population_density": 0.45,
        "airport_connectivity": 0.75, "border_mobility": 0.70,
    },
    "South Korea": {
        "name": "한국", "aliases": ["한국", "대한민국", "Korea", "South Korea"],
        "healthcare_infra": 0.88, "population_density": 0.85,
        "airport_connectivity": 0.75, "border_mobility": 0.45,
    },
    "Japan": {
        "name": "일본", "aliases": ["일본", "Japan"],
        "healthcare_infra": 0.85, "population_density": 0.70,
        "airport_connectivity": 0.75, "border_mobility": 0.40,
    },
    "Hong Kong": {
        "name": "홍콩", "aliases": ["홍콩", "Hong Kong"],
        "healthcare_infra": 0.82, "population_density": 0.95,
        "airport_connectivity": 0.85, "border_mobility": 0.60,
    },
    "Brazil": {
        "name": "브라질", "aliases": ["브라질", "Brazil", "상파울루", "Sao Paulo", "리우데자네이루", "Rio"],
        "healthcare_infra": 0.55, "population_density": 0.30,
        "airport_connectivity": 0.45, "border_mobility": 0.35,
    },
    "USA": {
        "name": "미국", "aliases": ["미국", "USA", "United States", "US"],
        "healthcare_infra": 0.82, "population_density": 0.20,
        "airport_connectivity": 0.85, "border_mobility": 0.40,
    },
}

DEFAULT_VULNERABILITY = 0.5  # 시드 데이터 없는 국가용 중립값

SIGNAL_TYPE_SEVERITY = {
    "신규발생": 85, "급증": 80, "진행중": 60, "불명": 40, "감소": 15, "종료": 10,
}

# 국가 단위로 떨어지는 collector.py 직접수치 — 이 4개만 국가에 1:1로 귀속 가능
DIRECT_METRICS = {
    "South Korea": _kdca_latest_total,
    "Japan": _japan_idwr_total,
    "Hong Kong": _hk_chp_total,
    "Brazil": _infodengue_total,
}


def vulnerability_index(country_id: str) -> float:
    c = COUNTRIES.get(country_id)
    if not c:
        return DEFAULT_VULNERABILITY
    return round(
        (1 - c["healthcare_infra"]) * 0.30
        + c["population_density"] * 0.25
        + c["airport_connectivity"] * 0.25
        + c["border_mobility"] * 0.20,
        3,
    )


def _matches(location: str | None, aliases: list[str]) -> bool:
    return bool(location) and any(alias in location for alias in aliases)


def _nlp_raw_score(country_id: str) -> tuple[float | None, int]:
    """extracted_signals 중 이 국가에 매칭되는 기록들의 신뢰도가중 평균 심각도."""
    aliases = COUNTRIES[country_id]["aliases"]
    matched = [r for r in db.list_extracted_signals(limit=500) if _matches(r["location"], aliases)]
    if not matched:
        return None, 0
    scores = [SIGNAL_TYPE_SEVERITY.get(r["signal_type"], 40) * r["source_trust"] for r in matched]
    return round(statistics.mean(scores), 1), len(matched)


def compute_country_risk(country_id: str) -> dict:
    if country_id not in COUNTRIES:
        raise KeyError(country_id)

    direct_score = None
    extractor = DIRECT_METRICS.get(country_id)
    if extractor:
        records = load_records()
        series = [extractor(r) for r in records if r.get("type") == "free_sources"]
        direct_score = _anomaly_score(series)

    nlp_score, nlp_count = _nlp_raw_score(country_id)

    components = [s for s in (direct_score, nlp_score) if s is not None]
    raw_score = round(statistics.mean(components), 1) if components else None
    vuln = vulnerability_index(country_id)

    if raw_score is not None:
        risk_score = round(raw_score * vuln, 1)
    else:
        # 실신호 없을 때 취약성 지수로 기준선 제공 (표시는 되되 낮은 값)
        risk_score = round(vuln * 35, 1)

    return {
        "country": country_id,
        "name": COUNTRIES[country_id]["name"],
        "raw_score": raw_score,
        "raw_score_components": {
            "direct_signal": direct_score,
            "nlp_signal": nlp_score,
            "nlp_signal_count": nlp_count,
        },
        "vulnerability_index": vuln,
        "risk_score": risk_score,
        "has_signal": raw_score is not None,
        "tier": _tier(risk_score),
    }


def rank_countries() -> dict:
    results = [compute_country_risk(cid) for cid in COUNTRIES]
    results.sort(key=lambda r: -r["risk_score"])
    return {"countries": results}

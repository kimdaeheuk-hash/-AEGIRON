"""국가별 위험지수 — 인수인계서 Part5 ⑨.

최종 국가위험도 = 원시위험도 × 국가취약성지수.

원시위험도는 두 갈래를 합쳐 만든다:
  1) collector.py 직접수치 — KDCA(한국)·InfoDengue(브라질)·IDWR(일본)·CHP(홍콩)처럼
     국가 단위로 떨어지는 신호는 gai.py와 같은 z-score 이상도를 재사용.
  2) NLP 구조화 추출(⑦, extracted_signals) — location 필드에 해당 국가명이 매칭되는
     기록들의 출처신뢰도 가중 심각도 평균.
  둘 다 있으면 평균, 하나만 있으면 그것만, 둘 다 없으면 None(랭킹 하단으로).

국가취약성지수 4요소(의료인프라·인구밀도·공항연결성·국경이동량, 0~1) 중
의료인프라·인구밀도는 World Bank Open Data, 공항연결성은 OpenFlights 공개
데이터로 실연동됨(country_indicators.py, 주간 스케줄러가 갱신). 국경이동량은
근거로 쓸 만한 무료 API가 없어(UNWTO는 유료) 계속 COUNTRIES의 추정 시드값을
씀. 실데이터 캐시가 없거나(수집 전, 갱신 실패) 시드 테이블에 없는 국가는
COUNTRIES의 추정 시드값 → 그마저 없으면 중립값(0.5)으로 폴백.
"""
from __future__ import annotations
import datetime as dt
import statistics

import db
from .gai import _anomaly_score, _tier
from .country_indicators import load_country_indicators
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
    # 기존 9개국이 동아시아·중동·남미·미국 위주라 실제 감염병 고위험·저인프라
    # 지역(아프리카 상당수·분쟁지역·태평양 오지)이 안 보이는 문제가 있었음 —
    # 5개국 추가. 4요소는 다른 국가들과 동일하게 손으로 추정한 시드값이고,
    # country_indicators.py의 World Bank·OpenFlights 실데이터로 갱신됨.
    "Nigeria": {
        "name": "나이지리아", "aliases": ["나이지리아", "Nigeria", "라고스", "Lagos", "아부자", "Abuja"],
        "healthcare_infra": 0.25, "population_density": 0.45,
        "airport_connectivity": 0.45, "border_mobility": 0.55,  # 라싸열 풍토병 + 아프리카 최다인구
    },
    "Ethiopia": {
        "name": "에티오피아", "aliases": ["에티오피아", "Ethiopia", "아디스아바바", "Addis Ababa"],
        "healthcare_infra": 0.20, "population_density": 0.40,
        "airport_connectivity": 0.50, "border_mobility": 0.45,  # 에티오피아항공 = 아프리카 최대 허브
    },
    "Yemen": {
        "name": "예멘", "aliases": ["예멘", "Yemen", "사나", "Sanaa"],
        "healthcare_infra": 0.10, "population_density": 0.35,
        "airport_connectivity": 0.10, "border_mobility": 0.40,  # 분쟁으로 의료체계 붕괴, 콜레라 상시유행
    },
    "Madagascar": {
        "name": "마다가스카르", "aliases": ["마다가스카르", "Madagascar", "안타나나리보", "Antananarivo"],
        "healthcare_infra": 0.20, "population_density": 0.30,
        "airport_connectivity": 0.20, "border_mobility": 0.15,  # 전세계 유일 상시 페스트(흑사병) 발생국
    },
    "Papua New Guinea": {
        "name": "파푸아뉴기니", "aliases": ["파푸아뉴기니", "Papua New Guinea", "PNG", "포트모르즈비", "Port Moresby"],
        "healthcare_infra": 0.15, "population_density": 0.15,
        "airport_connectivity": 0.10, "border_mobility": 0.20,  # 태평양 오지 — 산악지형 의료접근성 최하위권
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


def _vulnerability_components(country_id: str) -> tuple[dict, bool]:
    """
    healthcare_infra·population_density·airport_connectivity는 country_indicators
    캐시(World Bank·OpenFlights 실데이터)가 있으면 그걸 쓰고, 없으면 COUNTRIES
    시드값으로 폴백. border_mobility는 항상 시드값(실데이터 소스 없음).
    반환값 두 번째 요소: 3개 실데이터 필드가 전부 캐시에서 채워졌는지 여부.
    """
    seed = COUNTRIES.get(country_id, {})
    real = load_country_indicators().get(country_id, {})

    fields = {}
    all_real = True
    for key in ("healthcare_infra", "population_density", "airport_connectivity"):
        if key in real:
            fields[key] = real[key]
        else:
            fields[key] = seed.get(key, 0.5)
            all_real = False
    fields["border_mobility"] = seed.get("border_mobility", 0.5)
    return fields, all_real and bool(real)


def vulnerability_index(country_id: str) -> float:
    if country_id not in COUNTRIES and country_id not in load_country_indicators():
        return DEFAULT_VULNERABILITY
    c, _ = _vulnerability_components(country_id)
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
    _, vuln_all_real = _vulnerability_components(country_id)

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
        # healthcare_infra·population_density·airport_connectivity 3개 전부
        # World Bank·OpenFlights 실데이터 캐시에서 채워졌으면 real_data,
        # 하나라도 COUNTRIES 시드값으로 폴백됐으면 seed_fallback. border_mobility는
        # 항상 시드값이라 real_data여도 100% 실측은 아니라는 점은 유의.
        "vulnerability_estimated": not vuln_all_real,
        "vulnerability_source": "real_data" if vuln_all_real else "seed_fallback",
        "risk_score": risk_score,
        "has_signal": raw_score is not None,
        "tier": _tier(risk_score),
    }


def rank_countries() -> dict:
    results = [compute_country_risk(cid) for cid in COUNTRIES]
    results.sort(key=lambda r: -r["risk_score"])
    return {"countries": results}


# risk_score(= raw_score × 취약성지수, 취약성이 대개 0.4~0.6대)에는 gai.py의
# _tier() 절대 기준(70/80/90)을 그대로 못 씀 — 실측 확인 결과 raw_score가
# 100(최대 이상치)이어도 risk_score가 70을 못 넘는 나라가 대부분이라, tier로
# 걸면 사실상 영원히 안 울림. 그래서 취약성 배율 이전의 raw_score(순수 이상도,
# GAI와 동일 척도)를 기준으로 삼는다 — raw_score 70은 z-score 2σ 이상에 해당.
RAW_SCORE_THRESHOLD = 70
PREDICTION_COOLDOWN_DAYS = 14  # 같은 국가를 이 기간 내 중복으로 다시 기록하지 않음


def log_notable_predictions(ranked: list[dict] | None = None) -> list[dict]:
    """
    '적중률을 실제로 증명하려면 예측 시점과 검증 시점을 분리해서 기록해야 한다'
    (db.py 상단 설계 원칙)를 실제로 실행에 옮기는 부분 — country_risk가 통계적으로
    유의미한 이상치(raw_score >= RAW_SCORE_THRESHOLD)를 감지할 때마다 predictions
    테이블에 자동 기록한다. 지금까지는 이 테이블에 기록하는 함수
    (db.create_prediction)가 API로만 노출되고 아무도 호출한 적이 없어 0건이었음.

    같은 국가를 매시간 반복 기록하면 의미가 없어서, 최근 PREDICTION_COOLDOWN_DAYS
    이내 미검증 기록이 이미 있으면 건너뛴다(alerts.py의 '같은 날 갱신만' 방지
    패턴과 같은 취지 — 여기선 국가 단위로 더 길게 잡음).
    """
    ranked = ranked or rank_countries()["countries"]
    logged: list[dict] = []

    for c in ranked:
        raw = c.get("raw_score")
        if raw is None or raw < RAW_SCORE_THRESHOLD:
            continue

        existing = db.list_predictions(country=c["name"])
        unverified = [p for p in existing if p["verified_at"] is None]
        if unverified:
            latest_predicted_at = dt.datetime.fromisoformat(unverified[0]["predicted_at"])
            age_days = (dt.datetime.now(dt.timezone.utc) - latest_predicted_at).days
            if age_days < PREDICTION_COOLDOWN_DAYS:
                continue

        comp = c["raw_score_components"]
        basis = []
        if comp.get("direct_signal") is not None:
            basis.append(f"정부/공식 통계 기반 이상도 {comp['direct_signal']}점")
        if comp.get("nlp_signal") is not None:
            basis.append(f"뉴스·검색 기반 신호 {comp['nlp_signal']}점({comp['nlp_signal_count']}건 언급)")
        basis.append(f"국가 취약성 지수 {c['vulnerability_index']}(의료인프라·인구밀도·공항연결성·국경이동량 종합)")

        pred = db.create_prediction(
            country=c["name"], disease="종합 위험도(GAI 기반)",
            risk_score=c["risk_score"], basis=basis,
        )
        logged.append(pred)

    return logged

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

Tier-1(COUNTRIES, 14개국)은 사람이 손으로 취약성 지수를 다듬고 직접수치까지
연결한 큐레이션 국가. Tier-2는 nlp_extract.py(⑯)가 country_iso3를 뽑아낸
그 외 전세계 국가 중 최근 실제 신호가 있었던 곳만 자동으로 랭킹에 편입된다
(discovered_tier2_countries) — 별칭사전 없이 ISO3 정확매칭만으로 커버리지가
열리는 지점. API 응답의 coverage_tier로 "curated"(정교)/"auto"(자동편입,
아직 손으로 다듬지 않음)를 항상 구분해서 노출한다(정직성 원칙).
"""
from __future__ import annotations
import datetime as dt
import math
import statistics

import db
from .gai import _anomaly_score, _tier
from .country_indicators import load_country_indicators
from .world_countries import load_world_countries
from .signal_metrics import (
    collapse_repeats, load_records, _kdca_latest_total, _japan_idwr_total, _hk_chp_total, _infodengue_total,
)

TIER2_DISCOVERY_WINDOW_DAYS = 30  # 이 기간 내 country_iso3 신호가 있어야 Tier-2로 편입

# (국가ID = ISO 3166-1 alpha-3: 한국어명·매칭별칭[레거시 location 텍스트 매칭용]·
#  취약성 4요소[0~1, 추정 시드값]). 키가 ISO3라 nlp_extract.py가 뽑아내는
# country_iso3와 별칭사전 없이 바로 매칭된다(⑯). aliases는 country_iso3가
# 없는 구형 레코드의 free-text location 매칭 폴백용으로만 남겨둠.
COUNTRIES = {
    "COD": {
        "name": "콩고민주공화국", "aliases": ["DRC", "콩고민주공화국", "콩고", "Congo"],
        "healthcare_infra": 0.25, "population_density": 0.55,
        "airport_connectivity": 0.15, "border_mobility": 0.55,
    },
    "UGA": {
        "name": "우간다", "aliases": ["우간다", "Uganda"],
        "healthcare_infra": 0.30, "population_density": 0.50,
        "airport_connectivity": 0.20, "border_mobility": 0.50,
    },
    "SAU": {
        "name": "사우디아라비아", "aliases": ["사우디", "사우디아라비아", "Saudi"],
        "healthcare_infra": 0.70, "population_density": 0.20,
        "airport_connectivity": 0.55, "border_mobility": 0.75,  # 하지 순례 — 단기 대규모 국경이동
    },
    "THA": {
        "name": "태국", "aliases": ["태국", "Thailand", "방콕", "Bangkok"],
        "healthcare_infra": 0.60, "population_density": 0.45,
        "airport_connectivity": 0.75, "border_mobility": 0.70,
    },
    "KOR": {
        "name": "한국", "aliases": ["한국", "대한민국", "Korea", "South Korea"],
        "healthcare_infra": 0.88, "population_density": 0.85,
        "airport_connectivity": 0.75, "border_mobility": 0.45,
    },
    "JPN": {
        "name": "일본", "aliases": ["일본", "Japan"],
        "healthcare_infra": 0.85, "population_density": 0.70,
        "airport_connectivity": 0.75, "border_mobility": 0.40,
    },
    "HKG": {
        "name": "홍콩", "aliases": ["홍콩", "Hong Kong"],
        "healthcare_infra": 0.82, "population_density": 0.95,
        "airport_connectivity": 0.85, "border_mobility": 0.60,
    },
    "BRA": {
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
    "NGA": {
        "name": "나이지리아", "aliases": ["나이지리아", "Nigeria", "라고스", "Lagos", "아부자", "Abuja"],
        "healthcare_infra": 0.25, "population_density": 0.45,
        "airport_connectivity": 0.45, "border_mobility": 0.55,  # 라싸열 풍토병 + 아프리카 최다인구
    },
    "ETH": {
        "name": "에티오피아", "aliases": ["에티오피아", "Ethiopia", "아디스아바바", "Addis Ababa"],
        "healthcare_infra": 0.20, "population_density": 0.40,
        "airport_connectivity": 0.50, "border_mobility": 0.45,  # 에티오피아항공 = 아프리카 최대 허브
    },
    "YEM": {
        "name": "예멘", "aliases": ["예멘", "Yemen", "사나", "Sanaa"],
        "healthcare_infra": 0.10, "population_density": 0.35,
        "airport_connectivity": 0.10, "border_mobility": 0.40,  # 분쟁으로 의료체계 붕괴, 콜레라 상시유행
    },
    "MDG": {
        "name": "마다가스카르", "aliases": ["마다가스카르", "Madagascar", "안타나나리보", "Antananarivo"],
        "healthcare_infra": 0.20, "population_density": 0.30,
        "airport_connectivity": 0.20, "border_mobility": 0.15,  # 전세계 유일 상시 페스트(흑사병) 발생국
    },
    "PNG": {
        "name": "파푸아뉴기니", "aliases": ["파푸아뉴기니", "Papua New Guinea", "PNG", "포트모르즈비", "Port Moresby"],
        "healthcare_infra": 0.15, "population_density": 0.15,
        "airport_connectivity": 0.10, "border_mobility": 0.20,  # 태평양 오지 — 산악지형 의료접근성 최하위권
    },
    # 2026-08-28 추가. 계기: 네팔 홍수 보도를 보고 이 시스템이 네팔을 어디까지
    # 아는지 확인했더니 — 현지어 뉴스 피드(gn_np)와 국가명 해석(NPL)은 있는데
    # Tier-1 국가표와 기후 좌표에는 없었다. 즉 **발병 보도가 시작되기 전까지는
    # 네팔이 위험 랭킹에 아예 등장하지 않는 상태**였다.
    "NPL": {
        "name": "네팔", "aliases": ["네팔", "Nepal", "카트만두", "Kathmandu"],
        "healthcare_infra": 0.25, "population_density": 0.40,
        "airport_connectivity": 0.20,   # 국제선 관문이 사실상 카트만두 1곳
        # ★ 0.85 는 이 표에서 가장 높다 — 근거를 남긴다 ★
        # 인도-네팔 국경은 비자도 여권도 없이 건너는 개방국경이다(1950년 평화우호조약).
        # 사우디(0.75)의 하지는 연 1회 단기 집중이지만, 이쪽은 상시 왕래다.
        # 이 값만은 실데이터 소스가 없어 country_indicators 로 갱신되지 않는다 —
        # 즉 여기 적은 추정이 그대로 계산에 쓰인다.
        "border_mobility": 0.85,
    },
}

DEFAULT_VULNERABILITY = 0.5  # 시드 데이터 없는 국가용 중립값

SIGNAL_TYPE_SEVERITY = {
    "신규발생": 85, "급증": 80, "진행중": 60, "불명": 40, "감소": 15, "종료": 10,
}

# 국가 단위로 떨어지는 collector.py 직접수치 — 이 4개만 국가에 1:1로 귀속 가능
DIRECT_METRICS = {
    "KOR": _kdca_latest_total,
    "JPN": _japan_idwr_total,
    "HKG": _hk_chp_total,
    "BRA": _infodengue_total,
}
# 위 중 원천이 주 단위인 것(홍콩 CHP 는 RSS 항목 수라 매시 바뀔 수 있어 뺀다).
DIRECT_SLOW_CADENCE = frozenset({"KOR", "JPN", "BRA"})


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


def _record_matches_country(record: dict, country_id: str, aliases: list[str]) -> bool:
    """country_iso3(⑯, Claude가 직접 추출한 표준코드)가 있으면 정확일치로 판정.
    country_iso3가 없는 구형 레코드만 기존 alias substring 매칭으로 폴백 —
    별칭사전에 없는 신규 국가도 country_iso3만 있으면 매칭되게 하는 게 핵심."""
    iso3 = record.get("country_iso3")
    if iso3:
        return iso3 == country_id
    return _matches(record.get("location"), aliases)


# 신호는 시간이 지나면 현재 위험에 대한 정보가치가 줄어든다 — 조기경보 엔진이라
# 오래된(이미 잦아든) 발병이 오늘 위험을 계속 부풀리면 안 된다. 반감기 지수감쇠로
# 최근 신호가 지배하게 한다(역학 nowcasting의 EWMA 철학). 반감기 14일: 2주 전
# 신호는 절반 가중치. 같은 시점 신호들끼리면 기존 단순평균과 동일(하위호환).
NLP_SIGNAL_HALFLIFE_DAYS = 14.0


def _signal_age_days(record: dict) -> float:
    """신호의 나이(일). 텍스트 기준일(signal_date) 우선, 없으면 추출시각(extracted_at)."""
    now = dt.datetime.now(dt.timezone.utc)
    for key in ("signal_date", "extracted_at"):
        v = record.get(key)
        if not v:
            continue
        try:
            d = dt.datetime.fromisoformat(v)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return max(0.0, (now - d).total_seconds() / 86400.0)
        except ValueError:
            try:
                d0 = dt.date.fromisoformat(str(v)[:10])
                return max(0.0, float((now.date() - d0).days))
            except ValueError:
                continue
    return 0.0


def _recency_weight(age_days: float) -> float:
    return 0.5 ** (age_days / NLP_SIGNAL_HALFLIFE_DAYS)


# 지목한 질병이 점수의 이만큼은 책임져야 한다. 못 넘으면 이름을 안 붙인다 —
# 여러 질병이 고르게 섞인 위험도에 하나를 골라 붙이면 없는 정밀도를 지어내는 것이고,
# 그 이름으로 채점까지 하면 틀린 근거로 틀린 성적표가 나온다.
DOMINANT_DISEASE_MIN_SHARE = 0.5


def _matched_signals(country_id: str) -> list[dict]:
    """이 국가에 매칭되는 extracted_signals. country_id가 COUNTRIES(Tier-1)에
    없으면(Tier-2) aliases가 비어있어 country_iso3 정확매칭만 동작한다."""
    aliases = COUNTRIES.get(country_id, {}).get("aliases", [])
    return [
        r for r in db.list_extracted_signals(limit=500)
        if _record_matches_country(r, country_id, aliases)
    ]


def _signal_weight(record: dict) -> float:
    """★ 점수와 질병 지목이 같은 저울을 쓴다 ★

    가중치 식을 두 벌 두면 '점수를 만든 질병'과 '이름 붙인 질병'이 갈라진다.
    이 리포가 반복해서 잡아온 고장이 정확히 그 모양이다(같은 개념의 정의가 둘).
    """
    return (_recency_weight(_signal_age_days(record))
            * SIGNAL_TYPE_SEVERITY.get(record.get("signal_type"), 40)
            * (record.get("source_trust") or 0))


def dominant_disease(country_id: str, matched: list[dict] | None = None) -> tuple[str | None, float]:
    """이 나라 위험도를 실제로 끌어올린 질병과 그 비중. 없으면 (None, 0.0).

    ★ 왜 이게 필요한가 ★ (2026-09-21, 캡틴 지시 B)

    예측이 `disease="종합 위험도(GAI 기반)"` 로 기록되고 있었다. 채점기는 예측의
    질병이 발병 사건 이름에 들어있는지를 보는데, 그 글자는 어떤 사건 이름에도
    안 나온다 — **적중이 영원히 불가능**했고 90일 뒤 전부 incorrect 로 떨어졌다.

    고치는 방법은 번역표를 만드는 게 아니라 **같은 어휘를 쓰는 것**이다. 여기서
    돌려주는 질병명은 extracted_signals.disease 이고, 정답 테이블에 올라가는
    이름도 같은 필드에서 온다(declaration_ingest.event_name_for). 둘이 같은
    출처를 쓰므로 표기가 어긋날 자리가 없다 — 제일 싼 온톨로지는 사전이 아니라
    하나의 어휘다.
    """
    matched = _matched_signals(country_id) if matched is None else matched
    by_disease: dict[str, float] = {}
    total = 0.0
    for r in matched:
        w = _signal_weight(r)
        if w <= 0:
            continue
        total += w
        name = (r.get("disease") or "").strip()
        if name:
            by_disease[name] = by_disease.get(name, 0.0) + w
    if not by_disease or total <= 0:
        return None, 0.0
    ranked = sorted(by_disease.items(), key=lambda kv: kv[1], reverse=True)
    name, weight = ranked[0]
    share = round(weight / total, 3)

    # 동점이면 지목하지 않는다. 반반이면 산술적으로는 문턱(50%)을 넘지만,
    # 그 '1등'은 dict 순서가 정한 것이지 신호가 정한 게 아니다 — 들어온 순서가
    # 바뀌면 예측의 질병이 바뀐다. 그건 측정이 아니라 우연이다.
    if len(ranked) > 1 and math.isclose(ranked[0][1], ranked[1][1]):
        return None, share

    return (name, share) if share >= DOMINANT_DISEASE_MIN_SHARE else (None, share)


def _nlp_raw_score(country_id: str, matched: list[dict] | None = None) -> tuple[float | None, int]:
    """extracted_signals 중 이 국가에 매칭되는 기록들의 '최근성·신뢰도 가중' 심각도.
    가중치 = 신뢰도(source_trust) × 반감기 감쇠(_recency_weight). 오래된 신호일수록
    현재 위험 기여가 줄어든다."""
    matched = _matched_signals(country_id) if matched is None else matched
    if not matched:
        return None, 0
    # 기존 값(심각도×신뢰도)의 '최근성 가중 평균' — 같은 시점 신호끼리면 단순평균과 동일.
    #
    # 분자 항은 _signal_weight() 를 **그대로** 쓴다. 여기에 같은 식을 한 벌 더 적어두면
    # 점수 쪽만 고치고 질병 지목 쪽은 안 고치는 날이 오고, 그러면 '점수를 만든 질병'과
    # '이름 붙인 질병'이 말없이 갈라진다.
    num = 0.0
    den = 0.0
    for r in matched:
        decay = _recency_weight(_signal_age_days(r))
        num += _signal_weight(r)
        den += decay
    if den == 0:
        return None, len(matched)
    return round(num / den, 1), len(matched)


def discovered_tier2_countries(days: int = TIER2_DISCOVERY_WINDOW_DAYS, limit: int = 1000) -> set[str]:
    """최근 N일 이내 extracted_signals에 country_iso3로 등장했지만 COUNTRIES(Tier-1)에는
    없는 국가 — 실제 신호가 있는 국가만 자동으로 랭킹에 편입시켜(근거 없는 국가를
    억지로 채우지 않음) Tier-2 전세계 커버리지를 연다."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    found: set[str] = set()
    for r in db.list_extracted_signals(limit=limit):
        iso3 = r.get("country_iso3")
        if not iso3 or iso3 in COUNTRIES:
            continue
        try:
            extracted_at = dt.datetime.fromisoformat(r["extracted_at"])
        except (KeyError, ValueError, TypeError):
            continue
        if extracted_at >= cutoff:
            found.add(iso3)
    return found


def _country_display(country_id: str) -> str:
    """Tier-1은 손으로 다듬은 한국어명, Tier-2는 world_countries 캐시의 영문명
    (world_countries.py, 주간 갱신) → 캐시가 아직 없으면 ISO3 코드 그대로."""
    curated = COUNTRIES.get(country_id)
    if curated:
        return curated["name"]
    ref = load_world_countries().get(country_id)
    return ref["name"] if ref else country_id


def _country_coords(country_id: str) -> tuple[float | None, float | None]:
    ref = load_world_countries().get(country_id)
    if not ref or "lat" not in ref or "lng" not in ref:
        return None, None
    return ref["lat"], ref["lng"]


def compute_country_risk(country_id: str) -> dict:
    curated = country_id in COUNTRIES

    direct_score = None
    extractor = DIRECT_METRICS.get(country_id)
    if extractor:
        records = load_records()
        series = [extractor(r) for r in records if r.get("type") == "free_sources"]
        if country_id in DIRECT_SLOW_CADENCE:
            # 주간 원천 — 매시간 다시 기록된 같은 값을 한 관측으로 접는다(signal_metrics.SLOW_CADENCE_METRICS 주석).
            series = collapse_repeats(series)
        direct_score = _anomaly_score(series)

    matched = _matched_signals(country_id)
    nlp_score, nlp_count = _nlp_raw_score(country_id, matched)
    top_disease, disease_share = dominant_disease(country_id, matched)

    # Tier-1(COUNTRIES)이 아니면 실제 신호(country_iso3 매칭)가 있을 때만 유효한
    # Tier-2 국가로 인정 — 근거 없는 임의 ISO3 코드로 위험도가 만들어지지 않게 함.
    if not curated and nlp_count == 0:
        raise KeyError(country_id)

    components = [s for s in (direct_score, nlp_score) if s is not None]
    raw_score = round(statistics.mean(components), 1) if components else None
    vuln = vulnerability_index(country_id)
    _, vuln_all_real = _vulnerability_components(country_id)
    lat, lng = _country_coords(country_id)

    if raw_score is not None:
        risk_score = round(raw_score * vuln, 1)
    else:
        # 실신호 없을 때 취약성 지수로 기준선 제공 (표시는 되되 낮은 값)
        risk_score = round(vuln * 35, 1)

    return {
        "country": country_id,
        "name": _country_display(country_id),
        "coverage_tier": "curated" if curated else "auto",
        "lat": lat,
        "lng": lng,
        "raw_score": raw_score,
        # 위험도를 끌어올린 질병과 그 비중. 못 고르면 None — 지어내지 않는다.
        # 예측이 이 이름으로 기록되고, 채점기가 이 이름으로 정답과 대조한다.
        "dominant_disease": top_disease,
        "dominant_disease_share": disease_share,
        "raw_score_components": {
            "direct_signal": direct_score,
            "nlp_signal": nlp_score,
            "nlp_signal_count": nlp_count,
        },
        "vulnerability_index": vuln,
        # healthcare_infra·population_density·airport_connectivity 3개 전부
        # World Bank·OpenFlights 실데이터 캐시에서 채워졌으면 real_data,
        # 하나라도 COUNTRIES 시드값(또는 Tier-2 중립값)으로 폴백됐으면 seed_fallback.
        # border_mobility는 항상 시드값이라 real_data여도 100% 실측은 아니라는 점은 유의.
        "vulnerability_estimated": not vuln_all_real,
        "vulnerability_source": "real_data" if vuln_all_real else "seed_fallback",
        "risk_score": risk_score,
        "has_signal": raw_score is not None,
        "tier": _tier(risk_score),
    }


def rank_countries() -> dict:
    ids = set(COUNTRIES) | discovered_tier2_countries()
    results = [compute_country_risk(cid) for cid in ids]
    results.sort(key=lambda r: -r["risk_score"])
    return {"countries": results}


# risk_score(= raw_score × 취약성지수, 취약성이 대개 0.4~0.6대)에는 gai.py의
# _tier() 절대 기준(70/80/90)을 그대로 못 씀 — 실측 확인 결과 raw_score가
# 100(최대 이상치)이어도 risk_score가 70을 못 넘는 나라가 대부분이라, tier로
# 걸면 사실상 영원히 안 울림. 그래서 취약성 배율 이전의 raw_score(순수 이상도,
# GAI와 동일 척도)를 기준으로 삼는다 — raw_score 70은 z-score 2σ 이상에 해당.
RAW_SCORE_THRESHOLD = 70
PREDICTION_COOLDOWN_DAYS = 14  # 같은 국가를 이 기간 내 중복으로 다시 기록하지 않음

# ★★ 정기 보정 기록 — 캡틴이 바꿀 수 있는 손잡이 ★★
# 매 주기 상위 몇 개국을 '경보가 없어도' 기록할지. 0으로 두면 이 기능이 꺼지고
# 예전처럼 경보(2σ 이상)일 때만 기록한다.
#
# 왜 필요한가 (2026-08-18 실측):
#   RAW_SCORE_THRESHOLD가 70인데 그날 전 세계 최고점이 52점(캄보디아)이었다. 전 국가가
#   '정상'이라 예측이 한 건도 안 쌓였다 — 8/9에 Brier 채점을 도입하고 9일이 지나도
#   scoreable 0건, accuracy null. 즉 '검증 가능하게 만든다'는 약속의 결과물이 계속
#   비어 있었다. 문턱이 틀린 게 아니라, **경보가 울릴 때만 기록하는 구조**가 문제였다.
#
# 왜 이게 '가짜 경보 만들기'가 아닌가:
#   보정곡선(Brier)은 확신했을 때뿐 아니라 **조용하다고 판단했을 때도** 채점해야
#   만들어진다. "여기는 90일 안에 아무 일 없다"고 낮은 확률로 말하고 실제로 아무 일도
#   없으면, 그건 맞힌 것이고 성적에 들어가야 한다. 경보일 때만 기록하는 예보관은
#   영원히 자기 보정을 증명할 수 없다. 이 경로는 알람을 늘리지 않는다 —
#   경보 등급도 안 올리고, 텔레그램도 안 울린다. 기록만 남긴다.
ROUTINE_PREDICTION_COUNT = 5
# 예측의 판정 기한. 이 안에 공식 발병 선언이 나오는지로 채점한다.
# 90일인 이유: 너무 짧으면 실제 발병이 기한 뒤에 나와 부당하게 틀린 것이 되고,
# 너무 길면 판정이 계속 미뤄져 성적이 안 쌓인다. 실제 판정이 쌓이면 재조정한다.
PREDICTION_HORIZON_DAYS = 90


# 지목 못 한 예측의 질병 칸에 들어가는 문자열. _record_prediction 과 로그 줄이
# 같은 상수를 봐야 한다 — 글자를 두 군데 적으면 한쪽만 바뀌는 날이 온다.
UNNAMED_DISEASE = "종합 위험도(GAI 기반)"


def prediction_line(pred: dict) -> str:
    """예측 한 건의 로그 줄. 문자열은 시험 가능한 자리에 둔다.

    ★ 왜 질병을 적나 ★ (2026-09-27, 캡틴이 '루프가 도는지 확인해봐' 라고 물었을 때)

    예전 줄은 `- 콩고민주공화국: 위험도 78.5점` 이었다. #42 가 예측에 질병 이름을
    붙이게 만들었는데, **그게 실제로 붙었는지 로그로 확인할 방법이 없었다.**
    코드와 시험으로는 붙지만 프로덕션 관측으로는 미확인이었다 — #40 에서 경보에
    이름을 넣어 진단이 가능해진 것과 똑같은 자리다.

    지목 못 한 예측은 그렇다고 적는다(`질병 미지목`). 숨기면 '전부 지목되고 있다'
    로 읽힌다.
    """
    disease = (pred.get("disease") or "").strip()
    head = f"{pred.get('country')}: 위험도 {pred.get('risk_score')}점"
    named = "질병 미지목" if (not disease or disease == UNNAMED_DISEASE) else disease
    conf = pred.get("confidence")
    tail = f" · 신뢰도 {conf}" if conf is not None else ""
    return f"{head} · {named}{tail}"


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

    기록 경로는 두 가지다:
      ① 경보 — raw_score >= RAW_SCORE_THRESHOLD(2σ). 원래 있던 동작.
      ② 정기 보정 — 경보가 없어도 상위 ROUTINE_PREDICTION_COUNT개국을 낮은 신뢰도로
         기록한다. ①만 있으면 조용한 시기에 성적표가 영원히 비기 때문이다(상수부의
         ROUTINE_PREDICTION_COUNT 주석에 실측 근거와 논리를 적어뒀다).
    ②는 경보 등급을 올리지도, 알림을 울리지도 않는다 — 기록만 남긴다.
    """
    ranked = ranked or rank_countries()["countries"]
    logged: list[dict] = []
    recorded: set[str] = set()

    # ① 경보 경로 — 통계적 이상치(2σ 이상). 원래 있던 동작, 그대로 둔다.
    for c in ranked:
        raw = c.get("raw_score")
        if raw is None or raw < RAW_SCORE_THRESHOLD:
            continue
        pred = _record_prediction(c, raw, routine=False)
        if pred:
            logged.append(pred)
            recorded.add(c["name"])

    # ② 정기 보정 경로 — 경보가 없어도 상위 국가를 주기적으로 기록한다.
    if ROUTINE_PREDICTION_COUNT > 0:
        scored = [c for c in ranked if c.get("raw_score") is not None]
        scored.sort(key=lambda c: c["raw_score"], reverse=True)
        for c in scored[:ROUTINE_PREDICTION_COUNT]:
            if c["name"] in recorded:
                continue
            pred = _record_prediction(c, c["raw_score"], routine=True)
            if pred:
                logged.append(pred)

    return logged


def _record_prediction(c: dict, raw: float, routine: bool) -> dict | None:
    """국가 1건을 predictions에 기록. 쿨다운에 걸리면 None."""
    existing = db.list_predictions(country=c["name"])
    unverified = [p for p in existing if p["verified_at"] is None]
    if unverified:
        latest_predicted_at = dt.datetime.fromisoformat(unverified[0]["predicted_at"])
        age_days = (dt.datetime.now(dt.timezone.utc) - latest_predicted_at).days
        if age_days < PREDICTION_COOLDOWN_DAYS:
            return None

    comp = c["raw_score_components"]
    basis = []
    if routine:
        basis.append(
            f"정기 보정 기록 — 경보 아님(이상도 {raw}점, 경보 기준 {RAW_SCORE_THRESHOLD}점 미만). "
            "조용한 판단도 채점해 보정곡선을 만들기 위한 기록이다."
        )
    if comp.get("direct_signal") is not None:
        basis.append(f"정부/공식 통계 기반 이상도 {comp['direct_signal']}점")
    if comp.get("nlp_signal") is not None:
        basis.append(f"뉴스·검색 기반 신호 {comp['nlp_signal']}점({comp['nlp_signal_count']}건 언급)")
    basis.append(f"국가 취약성 지수 {c['vulnerability_index']}(의료인프라·인구밀도·공항연결성·국경이동량 종합)")

    # ★ 판정 기준·기한·신뢰도를 예측과 **동시에** 적는다 ★
    # 이게 없으면 기록은 쌓여도 채점이 안 된다. 실제로 이 기능 이전에 쌓인
    # 기록은 전부 채점 불가였다. 기준을 나중에 쓰면 결과를 보고 맞추게 되므로
    # 사후 보완도 하지 않는다.
    resolves_by = (dt.date.today() + dt.timedelta(days=PREDICTION_HORIZON_DAYS)).isoformat()

    # ★ 질병을 지목할 수 있으면 지목한다 ★ (2026-09-21, 캡틴 지시 B)
    #
    # 예전엔 무조건 "종합 위험도(GAI 기반)" 으로 적었다. 채점기는 예측의 질병이
    # 발병 사건 이름에 들어있는지를 보는데 그 글자는 어떤 사건 이름에도 안 나온다
    # — **적중이 영원히 불가능**했고, 90일 뒤 전부 incorrect 로 떨어져
    # '측정된 것처럼 보이는 적중률 0%' 가 만들어지는 중이었다.
    #
    # 이름은 dominant_disease() 가 준다. 점수를 만든 것과 **같은 저울**로 고른
    # 질병이고, extracted_signals.disease 를 그대로 쓴다 — 정답 테이블에 올라가는
    # 이름도 같은 필드에서 오므로(declaration_ingest) 표기가 어긋날 자리가 없다.
    #
    # 못 고르면 예전 이름을 그대로 쓴다. 지어내지 않는다 — 그 경우는 채점기가
    # ambiguous 로 판정한다(국가는 맞고 질병은 확인 불가). 거짓 오답보다 낫다.
    top_disease = c.get("dominant_disease")
    share = c.get("dominant_disease_share") or 0.0
    disease = top_disease or UNNAMED_DISEASE

    if top_disease:
        basis.append(
            f"이 위험도를 끌어올린 신호의 {round(share * 100)}%가 '{top_disease}' — "
            f"채점은 이 질병 기준으로 한다(같은 가중치로 고름)")
        criteria = (
            f"{resolves_by}까지 {c['name']}에서 {top_disease} 관련 WHO 발병공고·"
            f"상황보고서 또는 해당국 보건당국의 공식 발병 선언이 확인되면 correct. "
            f"확인되지 않으면 incorrect. 발병은 확인됐으나 다른 질병이면 ambiguous."
        )
    else:
        basis.append(
            "신호가 여러 질병에 흩어져 있어 하나를 지목하지 않는다"
            f"(최대 비중 {round(share * 100)}% < {round(DOMINANT_DISEASE_MIN_SHARE * 100)}%) — "
            "발병이 확인돼도 질병 대조가 안 되므로 ambiguous 로 판정된다")
        criteria = (
            f"{resolves_by}까지 {c['name']}에서 WHO 발병공고·상황보고서 또는 해당국 "
            f"보건당국의 공식 발병 선언이 확인되면 correct. 확인되지 않으면 incorrect. "
            f"발병은 확인됐으나 이 신호와 다른 질병이면 ambiguous."
        )

    return db.create_prediction(
        country=c["name"], disease=disease,
        risk_score=c["risk_score"], basis=basis,
        confidence=_confidence_for(raw),
        resolution_criteria=criteria,
        resolves_by=resolves_by,
    )


def _confidence_for(raw_score: float) -> float:
    """이상도 → 신뢰도(0~1).

    위험도와 신뢰도는 다르다 — 위험도는 '그 나라가 위험한 정도', 신뢰도는 '이
    판단이 맞을 확률'이다. 지금은 검증된 이력이 없어 둘의 관계를 실측할 수 없으므로,
    **보수적인 구간(0.05~0.65)만 쓴다.**

    0이나 1에 가까운 값을 쓰지 않는 이유: Brier 점수에서 확신은 틀렸을 때 큰 벌점을
    받는다. 근거 없이 확신을 높게 잡으면 성적이 나빠질 뿐 아니라 보정이 무너진다.

    ★ 이 매핑은 잠정값이다 ★
    실측 근거가 없다. 그래서 두 구간으로 나눠 보수적으로 잡았다:
      - 경보 구간(70~100): 0.35 → 0.65 선형. 원래 값 그대로 유지.
      - 보정 구간(0~70):   0.05 → 0.35, 이차곡선. 선형이 아니라 이차인 이유는
        2σ 미만 점수는 실제로 발병으로 이어질 확률이 낮아야 정직하기 때문이다.
        70에서 두 구간이 정확히 0.35로 이어져 불연속이 없다.
    첫 90일치 판정이 나오면 이 함수를 실측 보정곡선으로 갈아끼운다. 그게 이 기록을
    쌓는 목적이고, 잠정값이 틀렸다면 Brier 점수가 그걸 먼저 알려줄 것이다.
    """
    raw = max(0.0, min(float(raw_score), 100.0))
    if raw >= RAW_SCORE_THRESHOLD:
        span = max(1.0, 100.0 - RAW_SCORE_THRESHOLD)
        ratio = (raw - RAW_SCORE_THRESHOLD) / span
        return round(0.35 + ratio * 0.30, 2)
    ratio = raw / max(1.0, float(RAW_SCORE_THRESHOLD))
    return round(0.05 + (ratio ** 2) * 0.30, 2)

"""GDELT 과거 뉴스 커버리지 백테스트 — 인수인계서 확장(㉟).

전략적 배경: EIOS/BlueDot의 진짜 자산은 '데이터'가 아니라 그 데이터로 검증된
트랙레코드다(공개 뉴스는 누구나 씀). 아이기론은 시작이 늦어 '0에서 출발'처럼
보이지만, GDELT Project가 전 세계 뉴스 커버리지를 무료 공개하므로 과거 발병에
대한 '우리가 그때 있었다면 며칠 빨랐나'를 실데이터로 재구성할 수 있다.

이 모듈은 GDELT DOC 2.0 API(무료·키 불필요)의 커버리지 볼륨 타임라인을 받아,
발병별로 '뉴스 커버리지가 급증한 날' vs '공식 선언일'의 선행일수를 계산한다.
Phase 21 실이력 백테스트(extracted_signals 기반)의 '과거 재구성판'.

★ 정직성 경계선 ★
- GDELT 볼륨은 '뉴스 커버리지 강도'다 — 확진자 수도, 아이기론의 자체
  extracted_signals도 아니다. signal_source="gdelt_coverage_volume"로 명시하고,
  live 백테스트와 절대 같은 숫자인 척하지 않는다(reconstruction=True).
- 급증 탐지는 anomaly_engine과 동일한 z-score(기준선 평균+kσ) 철학을 쓴다 —
  임의 임계값이 아니라 커버리지 자체 변동폭 대비.
- GDELT DOC 2.0은 2017년 이후만 커버한다(그 이전은 BigQuery Events 필요 —
  미구현). 그래서 코로나(2019.12)·최근 에볼라는 되지만 더 옛날 사건은 안 됨을
  정직하게 표시한다.
- 샌드박스는 외부 API 정책 차단이라 라이브 검증 불가 — mock 단위테스트,
  Railway 운영환경에서 실제 조회.
"""
from __future__ import annotations
import datetime as dt
import statistics

import requests

USER_AGENT = {"User-Agent": "EpiWeather-GDELT/1.0 (epiweather.kr)"}
TIMEOUT = 30
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT DOC 2.0은 2017-01-01 이후만 커버.
GDELT_MIN_DATE = dt.date(2017, 1, 1)

# 커버리지 급증 판정: 기준선 평균 + Z_THRESHOLD·표준편차 이상인 첫 날.
COVERAGE_Z_THRESHOLD = 2.0
BASELINE_FRACTION = 0.4     # 창의 앞쪽 이만큼을 '조용한 기준선'으로 사용
LOOKBACK_DAYS = 60          # 선언일 기준 이만큼 이전부터 커버리지를 훑음
LOOKAHEAD_DAYS = 7

# outbreak_timeline event_id → GDELT 검색 쿼리(질병+지역).
EVENT_QUERIES = {
    "covid19_wuhan_2019": "coronavirus wuhan",
    "ebola_drc_2026": "ebola congo",
    "mers_saudi_2026": "mers saudi arabia",
    "dengue_2026": "dengue outbreak",
}


def _parse_gdelt_date(s: str) -> dt.date | None:
    digits = "".join(c for c in str(s) if c.isdigit())
    if len(digits) >= 8:
        try:
            return dt.date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        except ValueError:
            return None
    return None


def fetch_coverage_timeline(query: str, start: dt.date, end: dt.date) -> list[tuple[dt.date, float]] | None:
    """GDELT DOC 2.0 커버리지 볼륨 타임라인. (날짜, 볼륨) 리스트. 실패 시 None."""
    params = {
        "query": query, "mode": "timelinevol", "format": "json",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    try:
        resp = requests.get(GDELT_DOC_URL, params=params, headers=USER_AGENT, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        timeline = data.get("timeline")
        if not isinstance(timeline, list) or not timeline:
            return None
        series = timeline[0].get("data")
        if not isinstance(series, list):
            return None
        points = []
        for pt in series:
            d = _parse_gdelt_date(pt.get("date", ""))
            v = pt.get("value")
            if d is not None and isinstance(v, (int, float)):
                points.append((d, float(v)))
        points.sort(key=lambda p: p[0])
        return points or None
    except Exception:
        return None


def detect_coverage_spike(points: list[tuple[dt.date, float]]) -> dt.date | None:
    """커버리지가 처음으로 기준선 평균+2σ를 넘은 날. 기준선은 창 앞쪽 40%.
    급증이 없으면 None. anomaly_engine과 동일한 z-score 철학."""
    if len(points) < 5:
        return None
    n_base = max(3, int(len(points) * BASELINE_FRACTION))
    baseline = [v for _, v in points[:n_base]]
    rest = points[n_base:]
    if not rest:
        return None
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline) if len(baseline) > 1 else 0.0
    if stdev > 0:
        threshold = mean + COVERAGE_Z_THRESHOLD * stdev
    else:
        threshold = mean * 2 if mean > 0 else 0.0  # 분산 0이면 '2배 급증'을 급증으로
    for d, v in rest:
        if v > threshold:
            return d
    return None


def gdelt_reconstruct_event(event_id: str, declaration_date: dt.date) -> dict:
    """한 발병에 대해 GDELT 커버리지 급증일 vs 공식 선언일의 선행일수를 재구성.
    쿼리 매핑/데이터 없으면 available=False로 정직하게 표시."""
    query = EVENT_QUERIES.get(event_id)
    if not query:
        return {"event_id": event_id, "available": False, "reason": "GDELT 쿼리 매핑 없음"}
    if declaration_date < GDELT_MIN_DATE:
        return {
            "event_id": event_id, "available": False,
            "reason": f"GDELT DOC는 2017년 이후만 커버(선언일 {declaration_date}) — BigQuery Events 필요(미구현)",
        }

    start = declaration_date - dt.timedelta(days=LOOKBACK_DAYS)
    end = declaration_date + dt.timedelta(days=LOOKAHEAD_DAYS)
    points = fetch_coverage_timeline(query, start, end)
    if points is None:
        return {"event_id": event_id, "available": False,
                "reason": "GDELT 조회 실패(네트워크·정책 차단 등)", "query": query}

    spike = detect_coverage_spike(points)
    if spike is None:
        return {
            "event_id": event_id, "available": True, "coverage_spiked": False,
            "query": query, "declaration_date": declaration_date.isoformat(),
            "points_checked": len(points),
            "reason": "이 기간 커버리지 급증(기준선+2σ)이 없었음",
            "signal_source": "gdelt_coverage_volume", "reconstruction": True,
        }

    lead_days = (declaration_date - spike).days
    return {
        "event_id": event_id, "available": True, "coverage_spiked": True,
        "query": query,
        "declaration_date": declaration_date.isoformat(),
        "coverage_spike_date": spike.isoformat(),
        "gdelt_lead_days": lead_days,          # 양수 = 뉴스 커버리지가 공식 선언보다 먼저 급증
        "points_checked": len(points),
        "signal_source": "gdelt_coverage_volume",
        "reconstruction": True,
    }


def backtest_all_gdelt() -> dict:
    """GDELT 쿼리 매핑이 있는 모든 발병을 재구성 백테스트. 선언일은 db의
    outbreak_timeline에서 가져온다(㉑과 동일한 공식 선언 마일스톤 기준)."""
    import db
    from .knowledge_graph import _DECLARATION_MILESTONE_KEYS
    from .benchmark_baselines import compare_to_bluedot

    results = []
    for event_id in EVENT_QUERIES:
        timeline = db.get_timeline(event_id)
        milestones = timeline.get("milestones", [])
        declaration = next((m for m in milestones if m["milestone"] in _DECLARATION_MILESTONE_KEYS), None)
        if declaration is None:
            results.append({"event_id": event_id, "available": False,
                            "reason": "outbreak_timeline에 공식 선언 마일스톤 없음"})
            continue
        decl_date = dt.date.fromisoformat(declaration["event_date"])
        recon = gdelt_reconstruct_event(event_id, decl_date)
        # 벤치마크(㉕)가 있으면 GDELT 재구성 선행일수를 블루닷과 나란히
        lead = recon.get("gdelt_lead_days") if recon.get("coverage_spiked") else None
        comparison = compare_to_bluedot(event_id, lead)
        if comparison is not None:
            recon["bluedot_comparison"] = comparison
        results.append(recon)

    verified = [r for r in results if r.get("coverage_spiked")]
    leads = [r["gdelt_lead_days"] for r in verified]
    return {
        "results": results,
        "summary": {
            "events_checked": len(results),
            "events_with_coverage_spike": len(verified),
            "mean_gdelt_lead_days": round(sum(leads) / len(leads), 1) if leads else None,
        },
        "note": "GDELT 볼륨은 '뉴스 커버리지 강도' 프록시로, 확진자 수도 아이기론 자체 신호도 아님. "
                "라이브 extracted_signals 백테스트(/api/backtest/historical)와는 별개의 과거 재구성.",
        "coverage_note": "GDELT DOC 2.0은 2017년 이후만 커버 — 그 이전 사건은 재구성 불가(BigQuery Events 필요, 미구현).",
    }

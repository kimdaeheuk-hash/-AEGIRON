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
import re
import statistics
import time

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


# GDELT는 "5초에 1회"를 명시적으로 요구하고, 어기면 429 + 안내문을 돌려준다.
# 백필처럼 여러 사건을 연달아 긁으면 대부분 429가 나는데 실패가 조용해서(None 반환)
# '수집됐다'고 착각하기 쉽다 — 실측에서 16건 중 14건이 그렇게 비었다.
# 그래서 호출 간격을 강제하고 429는 물러났다 재시도한다.
_GDELT_MIN_INTERVAL_SEC = 5.5
_GDELT_MAX_RETRIES = 3
_gdelt_last_call = 0.0


def _gdelt_throttle() -> None:
    """직전 호출로부터 최소 간격을 보장(프로세스 내 전역)."""
    global _gdelt_last_call
    wait = _GDELT_MIN_INTERVAL_SEC - (time.monotonic() - _gdelt_last_call)
    if wait > 0:
        time.sleep(wait)
    _gdelt_last_call = time.monotonic()


# GDELT가 거부하는 질의문 규칙 — 네트워크를 안 타고 미리 걸러낸다.
# 이 규칙들은 전부 실측으로 확인한 것이며, 어길 때 GDELT는 **HTTP 200에 평문 오류**를
# 돌려주므로(예외도, 에러코드도 아님) 사전 점검이 없으면 조용히 '자료 없음'이 된다.
_GDELT_MIN_PHRASE_LEN = 5      # "The specified phrase is too short." — `"mpox"`(4)가 걸렸다
_QUOTED = re.compile(r'"([^"]*)"')
_PAREN = re.compile(r"\(([^()]*)\)")


def lint_gdelt_query(query: str) -> list[str]:
    """질의문을 보내기 전에 GDELT 문법 위반을 찾아낸다. 문제없으면 빈 목록.

    실측 근거: 백필 16건 중 2건이 질의문 오류로 통째로 비어 있었는데, GDELT가
    200 + 평문으로 답하는 바람에 '뉴스가 없던 사건'으로 몇 시간 오해했다.
      · `"Marburg" (Equatorial Guinea)` → Parentheses may only be used around OR'd statements
      · `"mpox" OR "monkeypox" (Congo OR DRC)` → The specified phrase is too short
    질의문은 사람이 손으로 적는 상수라 오타가 반드시 또 생긴다. 그때 네트워크
    왕복 없이 즉시 잡히게 한다."""
    problems = []
    for phrase in _QUOTED.findall(query):
        if len(phrase.strip()) < _GDELT_MIN_PHRASE_LEN:
            problems.append(f'따옴표 구문 "{phrase}"가 {_GDELT_MIN_PHRASE_LEN}글자 미만 — GDELT가 거부한다')
    for grp in _PAREN.findall(query):
        if " OR " not in grp.upper():
            problems.append(f"괄호 '({grp})'에 OR이 없다 — GDELT는 OR 묶음에만 괄호를 허용한다")
    # `A OR B (지역)`은 문법은 통과하지만 A가 지역 제한을 안 받는다(조용한 의미 오류).
    if re.search(r"\bOR\b", query, re.I) and "(" in query:
        head = query[:query.index("(")]
        if re.search(r"\bOR\b", head, re.I):
            problems.append("괄호 앞에 OR이 있다 — 앞쪽 항이 뒤 조건의 제한을 안 받는다"
                            "(병명 묶음을 먼저 괄호로 닫을 것)")
    return problems


def fetch_coverage_detailed(query: str, start: dt.date, end: dt.date) -> dict:
    """GDELT 커버리지 조회 — **왜 실패했는지까지** 돌려준다.

    {"points": [(날짜, 볼륨)...] | None, "error": None | "rate_limited" |
     "bad_query" | "http_<코드>" | "no_data" | "unparseable", "detail": str|None}

    왜 필요한가(실측): GDELT는 **질의문이 틀려도 HTTP 200**에 평문 안내를 돌려준다.
    실제로 `"Marburg" (Equatorial Guinea)`가 200 + `Parentheses may only be used
    around OR'd statements.`를 받았는데, 예전 구현은 `resp.json()`이 던지는 예외를
    통째로 삼켜 **'자료 없음'과 똑같이 None**을 반환했다. 그래서 백필이 "이 사건은
    뉴스가 없었다"로 조용히 넘어갔고, 원인이 속도제한인 줄로 몇 시간 오해했다.
    호출측이 '고칠 수 있는 실패(질의문 오류)'와 '기다리면 되는 실패(429)'와
    '진짜 자료 없음'을 구분하지 못하면 잘못된 곳을 고치게 된다."""
    bad = lint_gdelt_query(query)
    if bad:
        # 네트워크를 안 태운다 — 어차피 GDELT가 거부할 질의문이고, 여기서 잡아야
        # 원인이 '자료 없음'이 아니라 '질의문 오류'로 정확히 보고된다.
        return {"points": None, "error": "bad_query", "detail": "; ".join(bad)}
    params = {
        "query": query, "mode": "timelinevol", "format": "json",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    resp = None
    try:
        for attempt in range(_GDELT_MAX_RETRIES):
            _gdelt_throttle()
            resp = requests.get(GDELT_DOC_URL, params=params, headers=USER_AGENT, timeout=TIMEOUT)
            if resp.status_code != 429:
                break
            time.sleep(_GDELT_MIN_INTERVAL_SEC * (attempt + 2))   # 물러나며 재시도
    except Exception as e:
        return {"points": None, "error": "network", "detail": e.__class__.__name__}

    if resp is None:
        return {"points": None, "error": "network", "detail": "응답 없음"}
    if resp.status_code == 429:
        return {"points": None, "error": "rate_limited",
                "detail": f"재시도 {_GDELT_MAX_RETRIES}회 후에도 429 — 시간을 두고 재실행"}
    if resp.status_code != 200:
        return {"points": None, "error": f"http_{resp.status_code}", "detail": resp.text[:200]}

    try:
        data = resp.json()
    except ValueError:
        # ★ 200인데 JSON이 아니다 = 질의문을 GDELT가 거부한 것. 절대 '자료 없음'이 아니다.
        # 성공 시엔 항상 JSON이므로 평문 본문은 그 자체로 질의문 문제다 — 키워드로
        # 좁히면 새 오류 문구가 나올 때마다 'unparseable'로 흘러가 원인이 가려진다
        # (실제로 "The specified phrase is too short."가 그렇게 묻혔다. GDELT는
        # 5글자 미만 구문을 거부하는데 `"mpox"`가 4글자였다).
        body = resp.text.strip().strip('"')
        return {"points": None, "error": "bad_query", "detail": body[:200]}

    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        return {"points": None, "error": "no_data", "detail": "timeline 비어 있음"}
    series = timeline[0].get("data")
    if not isinstance(series, list):
        return {"points": None, "error": "no_data", "detail": "data 배열 없음"}
    points = []
    for pt in series:
        d = _parse_gdelt_date(pt.get("date", ""))
        v = pt.get("value")
        if d is not None and isinstance(v, (int, float)):
            points.append((d, float(v)))
    points.sort(key=lambda p: p[0])
    if not points:
        return {"points": None, "error": "no_data", "detail": "유효 포인트 0개"}
    return {"points": points, "error": None, "detail": None}


def fetch_coverage_timeline(query: str, start: dt.date, end: dt.date) -> list[tuple[dt.date, float]] | None:
    """GDELT DOC 2.0 커버리지 볼륨 타임라인. (날짜, 볼륨) 리스트. 실패 시 None.
    실패 이유가 필요하면 fetch_coverage_detailed를 쓸 것(하위호환용 얇은 껍데기)."""
    return fetch_coverage_detailed(query, start, end)["points"]


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

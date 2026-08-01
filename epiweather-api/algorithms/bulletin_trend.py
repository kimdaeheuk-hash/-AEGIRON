"""적재된 보고서 신호로 '추이'를 낸다 — 점 신호를 시계열로 바꾸는 층.

배경: bulletin_ingest는 회차별 수치를 한 건씩 넣는다. 그런데 조기경보에서 정말
필요한 건 "지금 몇 명"이 아니라 "**늘고 있느냐**"다. 회차가 여러 개 쌓이면
그 비교가 가능해진다 — 그래서 적재 때는 쓰지 않았던 급증·감소 판정을 여기서 한다
(bulletin_ingest.signal_type_for는 비교 대상이 없어 '진행중/불명'만 쓴다).

★ 정직성 규칙 ★
- 같은 지표끼리만 비교한다(누적 확진 vs 누적 확진). new_ 접두어가 붙은 주간 신규는
  누적과 절대 섞지 않는다.
- **누적 수치가 줄어드는 것을 '호전'으로 읽지 않는다.** WHO는 사례 재분류로 누적을
  하향 조정하는 일이 있다(확진→추정 재분류 등). 실제 환자가 사라진 게 아니므로
  '재조정(revised)'으로 따로 표시한다.
- 회차가 2개 미만이면 추이를 말하지 않는다(assessed=False).
- 값은 문서가 보고한 수치이고 기계 추출이라는 표시를 그대로 달고 다닌다.
"""
from __future__ import annotations

import re

# bulletin_ingest가 raw_text 끝에 "[confirmed=3262 deaths=1437 ...]"로 붙여둔 수치.
# 스키마에 metrics 열이 없어서 이렇게 실어 나른다 — 형식은 우리가 쓰는 쪽을 통제한다.
_METRIC_BLOCK = re.compile(r"\[([^\[\]]*=[^\[\]]*)\]\s*$")
_METRIC_PAIR = re.compile(r"([a-z_]+)=([-\d.eE+]+)")

# 주간 증가율이 이 이상이면 '급증'으로 본다. 발병 초기 주간 배가(倍加)를 잡되
# 소규모 표본의 흔들림에 반응하지 않도록 최소 증가분도 함께 건다.
SURGE_RATE = 0.20
SURGE_MIN_DELTA = 5


def metrics_from_raw(raw_text: str | None) -> dict[str, float]:
    """적재할 때 raw_text에 실어둔 수치를 다시 꺼낸다."""
    if not raw_text:
        return {}
    block = _METRIC_BLOCK.search(raw_text)
    if not block:
        return {}
    out: dict[str, float] = {}
    for key, value in _METRIC_PAIR.findall(block.group(1)):
        try:
            out[key] = float(value)
        except ValueError:
            continue
    return out


def build_series(rows: list[dict], disease: str | None = None) -> dict[str, list[dict]]:
    """적재 행들 → {지역: [회차별 관측치(날짜순)]}."""
    series: dict[str, list[dict]] = {}
    for row in rows:
        if disease and (row.get("disease") or "").lower() != disease.lower():
            continue
        location = row.get("location") or row.get("country_iso3")
        if not location:
            continue
        metrics = metrics_from_raw(row.get("raw_text"))
        if not metrics:
            continue
        series.setdefault(location, []).append({
            "date": row.get("signal_date") or row.get("extracted_at", "")[:10],
            "disease": row.get("disease"),
            "country_iso3": row.get("country_iso3"),
            "metrics": metrics,
        })
    for points in series.values():
        points.sort(key=lambda p: p["date"] or "")
    return series


def _direction(previous: float, latest: float) -> tuple[str, float | None]:
    """두 관측치의 방향과 증가율. 누적이 줄면 '재조정'으로 본다(호전이 아니다)."""
    delta = latest - previous
    rate = (delta / previous) if previous else None
    if delta < 0:
        return "재조정", rate            # 사례 재분류 등 — 환자가 사라진 게 아니다
    if delta == 0:
        return "정체", rate
    if rate is not None and rate >= SURGE_RATE and delta >= SURGE_MIN_DELTA:
        return "급증", rate
    return "증가", rate


def assess(rows: list[dict], disease: str | None = None,
           metric: str = "confirmed") -> dict:
    """지역별 추이 판정. 회차 2개 미만이면 판정하지 않는다."""
    series = build_series(rows, disease=disease)
    results = []
    for location, points in sorted(series.items()):
        usable = [p for p in points if metric in p["metrics"]]
        if len(usable) < 2:
            results.append({
                "location": location, "assessed": False,
                "observations": len(usable),
                "reason": f"'{metric}' 관측치가 {len(usable)}회 — 비교하려면 2회 이상 필요",
            })
            continue
        first, previous, latest = usable[0], usable[-2], usable[-1]
        direction, rate = _direction(previous["metrics"][metric], latest["metrics"][metric])
        span_total = latest["metrics"][metric] - first["metrics"][metric]
        results.append({
            "location": location,
            "country_iso3": latest.get("country_iso3"),
            "disease": latest.get("disease"),
            "assessed": True,
            "observations": len(usable),
            "metric": metric,
            "first": {"date": first["date"], "value": first["metrics"][metric]},
            "previous": {"date": previous["date"], "value": previous["metrics"][metric]},
            "latest": {"date": latest["date"], "value": latest["metrics"][metric]},
            "delta": round(latest["metrics"][metric] - previous["metrics"][metric], 4),
            "rate": round(rate, 4) if rate is not None else None,
            "direction": direction,
            "span_delta": round(span_total, 4),
            "series": [{"date": p["date"], "value": p["metrics"][metric]} for p in usable],
        })
    surging = [r for r in results if r.get("direction") == "급증"]
    return {
        "ok": True,
        "metric": metric,
        "disease": disease,
        "locations_assessed": sum(1 for r in results if r["assessed"]),
        "surging": [r["location"] for r in surging],
        "results": results,
        "is_machine_extracted": True,
        "note": (
            "같은 지표끼리만 비교한다(누적 vs 누적). 누적이 줄어든 경우는 '재조정'으로 "
            "표시한다 — WHO가 사례 재분류로 누적을 하향 조정하는 일이 있어 호전으로 "
            "읽으면 안 된다. 회차 2개 미만은 판정하지 않는다."
        ),
    }

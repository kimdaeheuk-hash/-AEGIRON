"""정제 데이터 상품 — 원본이 아니라 아이기론이 가공한 2차 데이터 (2026-11-16).

캡틴: "수집한 정보들을 가공하고 정제해서 판매할 수 있게 해야지! 원본 그대로 팔라는 얘기가 아니잖아".

원문·원값을 그대로 넘기지 않는다. 여러 출처의 보도를 **중복 제거·질병명 정규화·국가 코드화·사건 단위 묶기·
주 단위 집계·순위화**해서, 아이기론이 만든 지표만 판다. 세 가지:

1. ``outbreak_events``      정제 발생 사건 — (정규화 질병, 국가) 묶음을 공백 30일 기준 '사건(episode)'으로 자르고
                              처음/마지막 확인일·보도 수·출처 수·최고 신뢰도·최근 상태·확신도(공식 공개)를 붙인다.
                              선행성 원장에 같은 질병·국가의 공식 선언이 있으면 선언일과 선행일수를 잇는다.
2. ``country_week_panel``   국가 × ISO 주 패널 — 보도 수·질병 수·대표 질병·신규/급증/설명불가 보도 수·평균 신뢰도·
                              진행 중 사건 수, 그 주 국가 간 활동 백분위, 한국 유입 노출 지수(주간 보고서가 있던 주).
3. ``disease_week_panel``   질병 × ISO 주 패널 — 영향 국가 수·보도 수·그 주 새로 나타난 국가 수·급증 보도 수.

## 정직성

- 모두 **AI 구조화 추출(확인 필요 신호)을 집계한 추정 지표**다. 확진 건수가 아니다(각 행에 basis 로 적음).
- 확신도 공식: ``1 - (1 - 최고신뢰도) × 0.5^(출처 수 - 1)`` — 출처가 늘수록 1 에 다가간다. 학습한 값이 아니라 정한 규칙.
- 활동 백분위는 '그 주 보도가 있었던 나라들 사이의 순위'다. 보도가 없는 나라는 패널에 없다(0 이 아니라 미관측).
- 국가를 하나로 특정 못 한 보도(country_iso3 없음)는 국가 패널에서 빼고 수를 따로 센다.
- 질병명 정규화는 event_dedup.normalize_disease(별칭 사전) — 사전에 없는 이름은 원문 이름 그대로 남는다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter, defaultdict

EPISODE_GAP_DAYS = 30
CONF_BASIS = "1 - (1 - max_source_trust) × 0.5^(source_count - 1)"
BASIS = "AI 구조화 추출(확인 필요 신호)을 집계한 추정 지표 — 확진 건수 아님"


def _date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _load_reports(since: dt.date | None = None) -> list[dict]:
    import db
    from algorithms.event_dedup import normalize_disease

    q = ("SELECT id, extracted_at, source, disease, location, signal_type, source_trust, signal_date, "
         "known_disease, country_iso3 FROM extracted_signals")
    params: list = []
    if since:
        q += " WHERE extracted_at >= ?"
        params.append(since.isoformat())
    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(q + " ORDER BY extracted_at", params).fetchall()]
    out = []
    for r in rows:
        d = _date(r.get("signal_date")) or _date(r.get("extracted_at"))
        if d is None:
            continue
        r["day"] = d
        r["disease_norm"] = normalize_disease(r.get("disease"))
        r["iso3"] = (r.get("country_iso3") or "").upper() or None
        out.append(r)
    return out


def _declarations() -> dict[tuple[str, str], list[dict]]:
    """선행성 원장의 공식 선언 — (질병, ISO3) → [{declared_on, crossed_at, lead_days}]."""
    import db
    from algorithms.event_dedup import normalize_disease

    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    try:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT disease, country_iso3, crossed_at, declared_on, lead_days FROM lead_time_ledger "
                "WHERE outcome = 'declared' AND declared_on IS NOT NULL").fetchall()
    except Exception:  # noqa: BLE001 — 원장이 없으면 선언 연결만 생략
        return by
    for r in rows:
        key = (normalize_disease(r["disease"]) or r["disease"], (r["country_iso3"] or "").upper())
        by[key].append({"declared_on": r["declared_on"], "crossed_at": r["crossed_at"], "lead_days": r["lead_days"]})
    return by


def outbreak_events(since: dt.date | None = None) -> list[dict]:
    reports = _load_reports()
    decl = _declarations()
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in reports:
        if r["disease_norm"] and r["iso3"]:
            groups[(r["disease_norm"], r["iso3"])].append(r)
    events: list[dict] = []
    for (disease, iso3), rs in groups.items():
        rs.sort(key=lambda x: x["day"])
        episode: list[dict] = []
        for r in rs + [None]:  # 끝 표시
            if r is not None and (not episode or (r["day"] - episode[-1]["day"]).days <= EPISODE_GAP_DAYS):
                episode.append(r)
                continue
            if episode:
                events.append(_event_row(disease, iso3, episode, decl.get((disease, iso3), [])))
            episode = [r] if r is not None else []
    events.sort(key=lambda e: e["last_seen"], reverse=True)
    if since:
        events = [e for e in events if e["last_seen"] >= since.isoformat()]
    return events


def _event_row(disease: str, iso3: str, rs: list[dict], decls: list[dict]) -> dict:
    first, last = rs[0]["day"], rs[-1]["day"]
    sources = sorted({str(r.get("source") or "") for r in rs if r.get("source")})
    trust = [float(r["source_trust"]) for r in rs if isinstance(r.get("source_trust"), (int, float))]
    max_trust = max(trust) if trust else 0.0
    conf = 1 - (1 - max_trust) * (0.5 ** max(len(sources) - 1, 0))
    types = Counter(str(r.get("signal_type") or "불명") for r in rs)
    unexplained = sum(1 for r in rs if r.get("known_disease") == 0)
    # 이 사건 기간(앞뒤 30일 여유) 안의 공식 선언
    window_lo = first - dt.timedelta(days=EPISODE_GAP_DAYS)
    window_hi = last + dt.timedelta(days=EPISODE_GAP_DAYS)
    match = next((d for d in decls if (dd := _date(d["declared_on"])) and window_lo <= dd <= window_hi), None)
    eid = hashlib.sha1(f"{disease}|{iso3}|{first.isoformat()}".encode()).hexdigest()[:12]
    return {
        "event_id": eid,
        "disease": disease,
        "country_iso3": iso3,
        "first_seen": first.isoformat(),
        "last_seen": last.isoformat(),
        "duration_days": (last - first).days + 1,
        "report_count": len(rs),
        "source_count": len(sources),
        "sources": sources,
        "max_source_trust": round(max_trust, 3),
        "confidence": round(conf, 3),
        "latest_status": str(rs[-1].get("signal_type") or "불명"),
        "surge_reports": types.get("급증", 0),
        "new_reports": types.get("신규발생", 0),
        "unexplained_share": round(unexplained / len(rs), 3),
        "declared_on": match["declared_on"] if match else None,
        "lead_days_vs_declaration": match["lead_days"] if match else None,
        "basis": BASIS,
    }


def _weekly_exposure() -> dict[tuple[str, str], dict]:
    """주간 보고서의 (주, ISO3) → 노출 지수·이상도. 보고서가 없던 주는 비어 있다."""
    import db

    out: dict[tuple[str, str], dict] = {}
    try:
        with db.get_connection() as conn:
            rows = conn.execute("SELECT week, payload FROM weekly_reports").fetchall()
    except Exception:  # noqa: BLE001
        return out
    for r in rows:
        try:
            rep = json.loads(r["payload"])
        except (TypeError, ValueError):
            continue
        for e in (rep.get("top_exposure") or []) + (rep.get("no_direct_route_high") or []):
            iso = str(e.get("country") or "").upper()
            if iso:
                out[(r["week"], iso)] = {"korea_exposure_index": e.get("exposure_index"), "anomaly_score": e.get("raw_score")}
    return out


def country_week_panel(since: dt.date | None = None) -> list[dict]:
    reports = _load_reports(since - dt.timedelta(days=EPISODE_GAP_DAYS) if since else None)
    events = outbreak_events()
    exposure = _weekly_exposure()
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in reports:
        if r["iso3"]:
            cells[(_iso_week(r["day"]), r["iso3"])].append(r)
    rows = []
    for (week, iso3), rs in cells.items():
        diseases = Counter(r["disease_norm"] for r in rs if r["disease_norm"])
        trust = [float(r["source_trust"]) for r in rs if isinstance(r.get("source_trust"), (int, float))]
        y, w = int(week[:4]), int(week[-2:])
        wk_start = dt.date.fromisocalendar(y, w, 1)
        wk_end = wk_start + dt.timedelta(days=6)
        active = sum(1 for e in events if e["country_iso3"] == iso3
                     and e["first_seen"] <= wk_end.isoformat() and e["last_seen"] >= wk_start.isoformat())
        weighted = sum(trust) * (1 + sum(1 for r in rs if r.get("signal_type") == "급증"))
        rows.append({
            "week": week,
            "country_iso3": iso3,
            "report_count": len(rs),
            "distinct_diseases": len(diseases),
            "top_disease": diseases.most_common(1)[0][0] if diseases else None,
            "new_reports": sum(1 for r in rs if r.get("signal_type") == "신규발생"),
            "surge_reports": sum(1 for r in rs if r.get("signal_type") == "급증"),
            "unexplained_reports": sum(1 for r in rs if r.get("known_disease") == 0),
            "mean_source_trust": round(sum(trust) / len(trust), 3) if trust else None,
            "active_events": active,
            "_weighted": weighted,
            **exposure.get((week, iso3), {"korea_exposure_index": None, "anomaly_score": None}),
        })
    # 그 주 국가 간 활동 백분위(신뢰도 가중 보도량, 급증 가중) — 보도가 있던 나라들 사이의 순위
    by_week: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_week[r["week"]].append(r)
    for wk_rows in by_week.values():
        wk_rows.sort(key=lambda r: r["_weighted"])
        n = len(wk_rows)
        for i, r in enumerate(wk_rows):
            r["activity_percentile"] = round(100 * (i + 1) / n) if n else None
    for r in rows:
        r.pop("_weighted", None)
        r["basis"] = BASIS
    rows.sort(key=lambda r: (r["week"], -(r["activity_percentile"] or 0)), reverse=True)
    if since:
        rows = [r for r in rows if r["week"] >= _iso_week(since)]
    return rows


def disease_week_panel(since: dt.date | None = None) -> list[dict]:
    reports = _load_reports()
    seen_countries: dict[str, set[str]] = defaultdict(set)
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in sorted(reports, key=lambda x: x["day"]):
        if r["disease_norm"]:
            cells[(_iso_week(r["day"]), r["disease_norm"])].append(r)
    rows = []
    for (week, disease) in sorted(cells):
        rs = cells[(week, disease)]
        countries = {r["iso3"] for r in rs if r["iso3"]}
        new = countries - seen_countries[disease]
        seen_countries[disease] |= countries
        rows.append({
            "week": week,
            "disease": disease,
            "countries_affected": len(countries),
            "countries": sorted(countries),
            "new_countries": sorted(new),
            "report_count": len(rs),
            "surge_reports": sum(1 for r in rs if r.get("signal_type") == "급증"),
            "unlocated_reports": sum(1 for r in rs if not r["iso3"]),
            "basis": BASIS,
        })
    rows.sort(key=lambda r: (r["week"], r["report_count"]), reverse=True)
    if since:
        rows = [r for r in rows if r["week"] >= _iso_week(since)]
    return rows


BUILDERS = {
    "outbreak_events": outbreak_events,
    "country_week_panel": country_week_panel,
    "disease_week_panel": disease_week_panel,
}

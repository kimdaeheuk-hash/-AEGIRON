"""관측값 시계열 저장 — 요청 때 계산하고 버리던 층을 매시간 남긴다 (2026-11-15).

캡틴: "지금까지 아이기론에서 받은 모든 정보도 실측이야 — 홈페이지나 대시보드에서 볼 수 있게" →
"남은 거 시작해야지". 관측 데이터 활용 계획(docs/관측데이터_활용계획_2026-11.md) 권장 순서 1번.

## 왜

극지·기후·토지·삼림·무역·재난·여행경보는 요청할 때 계산해서 돌려주고 끝났다. 그래서
"지난달 대비"를 보여 줄 수 없고, 과거 재현(백테스트)도, 팔 수 있는 이력 데이터도 없었다.

## 어떻게

- 층마다 대상(ISO3·극지 지역·여행경보) 한 개당 한 행. 칸은 **측정값(measured)** 과 **해석값(derived)** 을 나눈다:
  측정값 = 출처가 준 숫자(기온·해빙일수·화재 수·수입액·경보 등급…), 해석값 = 우리가 계산한 지수·추정
  (이상도·압력·점수·급증 배수…). 둘을 섞지 않는다.
- 값이 직전과 같으면 새 행 대신 확인 시각(confirmed_at)·확인 횟수만 갱신한다(db.record_observation).
  observed_at 은 그 값이 **처음 계산된 시각**이다 — 응답 캐시 저장본이면 저장본의 계산 시각을 쓴다(지금 시각이 아님).
- 층을 못 읽었으면(예외·data_available False) 대상 '*' 의 status='undetermined' 행을 이유와 함께 남긴다.
  대상별로 값이 없으면 그 대상의 undetermined 행. **빈칸을 0 으로 채우지 않는다.**
- 무역은 Comtrade 상위 급증(품목별 상위 10개국)만 저장한다 — 전 세계 전수가 아니다(coverage 에 적음).

## 누가 부르나

main._after_cycle_bg — 매시 경보 주기 직후 응답 캐시 예열 다음. 끄기: EPIWEATHER_OBSERVATION_STORE=off.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from collections.abc import Callable
from typing import Any

LAYERS = ("polar", "climate", "land", "deforestation", "trade", "disaster", "travel")

Row = dict[str, Any]


def enabled() -> bool:
    return os.environ.get("EPIWEATHER_OBSERVATION_STORE", "on").lower() != "off"


def _row(target: str, *, metric: str = "", measured: dict | None = None, derived: dict | None = None,
         status: str = "ok", reason: str | None = None) -> Row:
    return {"target": target, "metric": metric, "status": status,
            "measured": measured, "derived": derived, "reason": reason}


def _undetermined(target: str, reason: str | None, metric: str = "") -> Row:
    return _row(target, metric=metric, status="undetermined", reason=reason or "이유 미상 — 값 없음")


def _pick(d: dict, *keys: str) -> dict:
    """있는 키만 — 없는 값을 None/0 으로 만들지 않는다."""
    return {k: d[k] for k in keys if k in d and d[k] is not None}


# ── 층별 추출 (입력은 각 API 응답 dict, 네트워크 없음) ─────────────────────────

def rows_polar(d: dict) -> list[Row]:
    out = []
    for r in d.get("regions") or []:
        rid = r.get("region")
        if not rid:
            continue
        thaw = r.get("thaw") or {}
        base = r.get("baseline") or {}
        news = r.get("news") or {}
        if thaw.get("data_available") is False:
            out.append(_undetermined(rid, thaw.get("reason") or "극지 기상 조회 실패 — 값 없음"))
            continue
        measured = {
            **_pick(base, "mean_max_c_current", "current_days_counted", "reference_period"),
            **_pick(thaw, "thaw_days_30d"),
        }
        if news.get("status") == "ok":
            measured.update(_pick(news, "keyword_hits", "item_count"))
        derived = {
            **_pick(base, "anomaly_c", "mean_max_c_baseline", "baseline_years"),
            **_pick(thaw, "permafrost_thaw_pressure"),
            **_pick(r, "polar_watch_score", "watch_grade"),
        }
        yi = r.get("yamal_index") or {}
        if "score" in yi:
            derived["yamal_index_score"] = yi["score"]
        out.append(_row(rid, measured=measured, derived=derived))
    return out


def _country_rows(d: dict, measured_keys: tuple[str, ...], derived_keys: tuple[str, ...]) -> list[Row]:
    out = []
    for c in d.get("countries") or []:
        iso = c.get("country")
        if not iso:
            continue
        if c.get("data_available") is False:
            out.append(_undetermined(iso, c.get("reason")))
            continue
        out.append(_row(iso, measured=_pick(c, *measured_keys), derived=_pick(c, *derived_keys)))
    return out


def rows_climate(d: dict) -> list[Row]:
    return _country_rows(d, ("mean_recent_temp_c", "precip_recent_14d_mm"),
                         ("heat_trend_c", "vector_suitability", "spillover_pressure", "method"))


def rows_land(d: dict) -> list[Row]:
    return _country_rows(d, ("fire_count_recent", "day_range"), ("land_clearing_pressure", "method"))


def rows_deforestation(d: dict) -> list[Row]:
    return _country_rows(d, ("deforestation_alerts_recent", "day_range"), ("deforestation_pressure", "method"))


def rows_trade(d: dict) -> list[Row]:
    if d.get("data_available") is False:
        return [_undetermined("*", d.get("reason"))]
    out = []
    for product, p in (d.get("products") or {}).items():
        if not isinstance(p, dict):
            continue
        fetch = p.get("fetch") or {}
        if p.get("data_available") is False:
            out.append(_undetermined("*", p.get("reason") or "품목 조회 실패 — 값 없음", metric=product))
            continue
        for s in p.get("top_surges") or []:
            iso = s.get("country_iso3")
            if not iso:
                continue
            measured = _pick(s, "monthly_import_usd")
            if fetch.get("latest_period"):
                measured["latest_period"] = fetch["latest_period"]
            out.append(_row(iso, metric=product, measured=measured, derived=_pick(s, "surge_ratio")))
    return out


def rows_disaster(d: dict) -> list[Row]:
    out = []
    for c in d.get("countries") or []:
        iso = c.get("country_iso3")
        if not iso:
            continue
        events, seen = [], set()
        for w in c.get("open_windows") or []:
            key = (w.get("disaster_type"), w.get("disaster_date"), w.get("title"))
            if key in seen:
                continue
            seen.add(key)
            events.append(_pick(w, "disaster_type", "alert_level", "disaster_date", "title"))
        diseases = sorted({w.get("disease") for w in c.get("open_windows") or [] if w.get("disease")})
        out.append(_row(iso, measured={"events": events},
                        derived={"open_windows": c.get("window_count", len(c.get("open_windows") or [])),
                                 "window_diseases": diseases}))
    return out


def _notice_id(link: str | None, headline: str) -> str:
    if link:
        m = re.search(r"/notices/(?:level\d/)?([^/?#]+)", link)
        if m:
            return m.group(1)
    return re.sub(r"[^a-z0-9]+", "-", headline.lower()).strip("-")[:80]


def rows_travel(d: dict) -> list[Row]:
    if d.get("data_available") is False:
        return [_undetermined("*", d.get("reason"))]
    from .country_cards import _travel_isos

    out = []
    for n in d.get("all_notices") or []:
        head = n.get("headline")
        if not head:
            continue
        out.append(_row(_notice_id(n.get("link"), head),
                        measured=_pick(n, "level", "headline", "pub_date", "link"),
                        derived={"countries_read": _travel_isos(head)}))
    return out


EXTRACTORS: dict[str, Callable[[dict], list[Row]]] = {
    "polar": rows_polar, "climate": rows_climate, "land": rows_land, "deforestation": rows_deforestation,
    "trade": rows_trade, "disaster": rows_disaster, "travel": rows_travel,
}

SOURCES = {
    "polar": "Open-Meteo 기상 + Google News(극지)",
    "climate": "Open-Meteo",
    "land": "NASA FIRMS VIIRS",
    "deforestation": "Global Forest Watch",
    "trade": "UN Comtrade(공개 전세계 스캔 상위 급증)",
    "disaster": "GDACS",
    "travel": "CDC Travelers' Health",
}


def _computed_at(d: dict) -> str:
    rc = d.get("response_cache") if isinstance(d, dict) else None
    if isinstance(rc, dict) and rc.get("computed_at"):
        return rc["computed_at"]
    return dt.datetime.now(dt.timezone.utc).isoformat()


def store(fetchers: dict[str, Callable[[], dict]]) -> dict[str, dict[str, int]]:
    """층별로 응답을 받아 저장한다. 반환: {층: {new, same, undetermined}}. 한 층의 실패가 다른 층을 막지 않는다."""
    import db

    summary: dict[str, dict[str, int]] = {}
    for layer, fetch in fetchers.items():
        counts = {"new": 0, "same": 0, "undetermined": 0}
        try:
            data = fetch()
            if not isinstance(data, dict):
                raise TypeError(f"응답이 dict 가 아님: {type(data).__name__}")
            at = _computed_at(data)
            rows = EXTRACTORS[layer](data)
        except Exception as e:  # noqa: BLE001 — 층을 못 읽은 것 자체를 기록한다
            at = dt.datetime.now(dt.timezone.utc).isoformat()
            rows = [_undetermined("*", f"층 조회 실패: {type(e).__name__}: {str(e)[:160]}")]
        for r in rows:
            result = db.record_observation(layer=layer, source=SOURCES.get(layer), at=at, **r)
            counts[result] += 1
            if r["status"] == "undetermined":
                counts["undetermined"] += 1
        summary[layer] = counts
    return summary


def summary_line(summary: dict[str, dict[str, int]]) -> str:
    names = {"polar": "극지", "climate": "기후", "land": "토지", "deforestation": "삼림",
             "trade": "무역", "disaster": "재난", "travel": "여행경보"}
    parts = []
    for layer, c in summary.items():
        total = c["new"] + c["same"]
        part = f"{names.get(layer, layer)} {total}(새 {c['new']}·같음 {c['same']}"
        if c["undetermined"]:
            part += f"·판정 안 함 {c['undetermined']}"
        parts.append(part + ")")
    return "🗄 관측 저장: " + " · ".join(parts)

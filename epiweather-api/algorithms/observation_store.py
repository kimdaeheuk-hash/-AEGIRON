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

from collections.abc import Callable
from typing import Any

# 개편(2026-11-22): 극지만 남겼다. 다른 층(기후·토지·삼림·무역·재난·여행경보)의 추출기는 커밋 83406e4 에 있다.
LAYERS = ("polar",)

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


EXTRACTORS: dict[str, Callable[[dict], list[Row]]] = {"polar": rows_polar}

SOURCES = {"polar": "Open-Meteo 기상 + Google News(극지)"}


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
    names = {"polar": "극지"}
    parts = []
    for layer, c in summary.items():
        total = c["new"] + c["same"]
        part = f"{names.get(layer, layer)} {total}(새 {c['new']}·같음 {c['same']}"
        if c["undetermined"]:
            part += f"·판정 안 함 {c['undetermined']}"
        parts.append(part + ")")
    return "🗄 관측 저장: " + " · ".join(parts)

"""나라별 위험 카드 — 흩어진 관측 층을 나라 한 장으로 융합한다 (2026-11-15).

캡틴: "이대로 가면 데이터를 활용 못하고 사업화가 안 돼" → "진행해".

한 나라에 대해 다음을 모은다:
  발생 보도(AI 구조화 추출) · 설명 불가 신호 · 재난 감시창(GDACS) · 의료물자 수입 급증(UN Comtrade) ·
  CDC 여행경보 최고 등급 · 위험지수(country_risk) · 한국 연결(주간 유입 보고서의 직항 노선·인천 여객).

이 카드는 웹 지구본의 클릭 화면이자 판매 단위다: `/api/country-cards`(API·구독),
매일 텔레그램 요약(notifier.notify_country_cards), 나라별 기관 브리핑.

★ 정직성 ★
- `intensity`(관측 강도)는 측정값이 아니라 우리가 정한 가중합(추정)이다. 가중치는 실측으로 보정하지
  않았다(`weights_calibrated: False`). 발병 확률이 아니라 "이번에 받은 관측이 얼마나 많고 무거운가"다.
- 한국 연결은 주간 유입 보고서가 준 값만 쓴다. 보고서가 없으면 `korea_available: False` 로 말한다.
- 여행경보 나라는 CDC 제목 속 나라 이름을 읽은 것이다(못 읽으면 붙이지 않음).
- 위치를 못 읽은 기록은 카드에 넣지 않고 `unlocated` 로 센다.
- 웹(epiweather-web/src/lib/countryCards.ts)과 같은 가중치·등급 문턱을 쓴다 — 한쪽만 바꾸지 말 것.
"""
from __future__ import annotations

import math
import re
from typing import Any

# 웹 lib/countryCards.ts INTENSITY_WEIGHTS 와 같은 값(판단 상수, 미보정)
INTENSITY_WEIGHTS = {"event": 20, "unexplained": 15, "disaster": 15, "trade": 10, "travel_per_level": 8}
GRADE_HIGH = 60
GRADE_ELEVATED = 30
EVIDENCE_MAX = 12
EXTRACTED_LIMIT = 200

LAYERS = ("event", "unexplained", "disaster", "trade")


def intensity_of(counts: dict[str, int], travel_level: int | None) -> int:
    w = INTENSITY_WEIGHTS
    v = (
        w["event"] * math.log2(1 + counts.get("event", 0))
        + w["unexplained"] * math.log2(1 + counts.get("unexplained", 0))
        + w["disaster"] * math.log2(1 + counts.get("disaster", 0))
        + w["trade"] * math.log2(1 + counts.get("trade", 0))
        + w["travel_per_level"] * (travel_level or 0)
    )
    return min(100, round(v))


def grade_of(intensity: int) -> str:
    return "high" if intensity >= GRADE_HIGH else "elevated" if intensity >= GRADE_ELEVATED else "watch"


def _travel_isos(headline: str) -> list[str]:
    """'Yellow Fever in Burkina Faso, Côte d'Ivoire, and Ghana' → 나라 ISO3 목록. 'in' 뒤만 읽는다."""
    from .country_resolve import countries_in_text

    m = re.search(r"\bin (?:the )?(.+)$", headline, re.IGNORECASE)
    return countries_in_text(m.group(1)) if m else []


def build_cards(
    *,
    extracted: list[dict],
    unexplained: dict | None,
    disaster: dict | None,
    trade: dict | None,
    travel: dict | None,
    risk: dict | None,
    korea: dict | None,
    lang: str = "ko",
) -> dict[str, Any]:
    """각 층의 응답(이미 계산된 dict)을 받아 카드 목록을 만든다 — 네트워크·DB 를 직접 부르지 않는다(시험 가능)."""
    from .country_resolve import resolve_countries, signal_countries
    from .name_i18n import country_name, disease_name

    cards: dict[str, dict] = {}
    unlocated = 0

    def card(iso3: str) -> dict:
        c = cards.get(iso3)
        if c is None:
            c = cards[iso3] = {
                "iso3": iso3,
                "name": country_name(iso3, lang),
                "counts": {k: 0 for k in LAYERS},
                "travel_level": None,
                "travel_titles": [],
                "risk_score": None,
                "dominant_disease": None,
                "lat": None,
                "lng": None,
                "korea": {"routes": None, "passengers": None},
                "evidence": [],
            }
        return c

    def add(iso3: str, layer: str, line: str | None) -> None:
        c = card(iso3)
        c["counts"][layer] += 1
        if line and len(c["evidence"]) < EVIDENCE_MAX:
            item = {"layer": layer, "line": line}
            if item not in c["evidence"]:
                c["evidence"].append(item)

    # 발생 보도 — 같은 질병·장소·출처의 반복 보도는 최신 1건(웹 보드와 같은 규칙)
    seen: set[tuple] = set()
    for r in extracted:
        key = (r.get("disease"), r.get("location"), r.get("source"))
        if key in seen:
            continue
        seen.add(key)
        isos = signal_countries(r)
        if not isos:
            unlocated += 1
            continue
        line = " · ".join(
            x for x in (
                disease_name(r.get("disease"), lang) or r.get("disease"),
                r.get("signal_type"),
                r.get("source"),
                (r.get("extracted_at") or "")[:10] or None,
            ) if x
        )
        for iso in isos:
            add(iso, "event", line)

    for a in (unexplained or {}).get("alerts") or []:
        isos = resolve_countries(a.get("location"))
        if not isos:
            unlocated += 1
            continue
        line = " · ".join(x for x in (a.get("location"), a.get("source"), a.get("signal_date")) if x)
        for iso in isos:
            add(iso, "unexplained", line)

    for c in (disaster or {}).get("countries") or []:
        iso = c.get("country_iso3")
        if not iso:
            unlocated += 1
            continue
        first = (c.get("open_windows") or [{}])[0]
        add(iso, "disaster", (first.get("title") or "")[:120] or None)

    for s in (trade or {}).get("top_surges") or []:
        iso = s.get("country_iso3")
        if not iso:
            continue
        ratio = s.get("surge_ratio")
        add(iso, "trade", f"{s.get('product')} ×{ratio:.2f}" if isinstance(ratio, (int, float)) else s.get("product"))

    for n in (travel or {}).get("all_notices") or []:
        head, level = n.get("headline"), n.get("level")
        if not head or not isinstance(level, int):
            continue
        for iso in _travel_isos(head):
            c = card(iso)
            c["travel_level"] = max(c["travel_level"] or 0, level)
            if len(c["travel_titles"]) < 3:
                c["travel_titles"].append(f"Level {level} · {head}")

    # 위험지수 — 신호가 있는 나라에만 붙인다(없는 나라를 새로 만들지 않음)
    for r in (risk or {}).get("countries") or []:
        iso = r.get("country")
        if iso in cards:
            c = cards[iso]
            c["risk_score"] = r.get("risk_score")
            c["dominant_disease"] = r.get("dominant_disease")
            c["lat"], c["lng"] = r.get("lat"), r.get("lng")

    for e in [*((korea or {}).get("top_exposure") or []), *((korea or {}).get("no_direct_route_high") or [])]:
        iso = e.get("country")
        if iso in cards:
            cards[iso]["korea"] = {"routes": e.get("direct_routes_to_kor"), "passengers": e.get("kor_passengers")}

    out = []
    for c in cards.values():
        c["intensity"] = intensity_of(c["counts"], c["travel_level"])
        c["grade"] = grade_of(c["intensity"])
        out.append(c)
    out.sort(key=lambda c: -c["intensity"])

    return {
        "cards": out,
        "unlocated": unlocated,
        "korea_available": korea is not None,
        "korea_week": (korea or {}).get("week"),
        "intensity_formula": "Σ 가중치×log2(1+건수) + CDC 경보 등급×8 (최대 100)",
        "weights": INTENSITY_WEIGHTS,
        "grade_thresholds": {"high": GRADE_HIGH, "elevated": GRADE_ELEVATED},
        "weights_calibrated": False,
        "is_probability": False,
        "note": "관측 강도는 받은 관측의 양·무게를 합친 추정이며 발병 확률이 아님 · 가중치 미보정",
    }


def collect_inputs() -> dict[str, Any]:
    """운영에서 각 층을 모은다. 무거운 층은 응답 캐시 저장본을 그대로 쓴다(같은 키 → 재계산 없음)."""
    import db
    from main import (  # main 의 캐시된 빌더를 그대로 써서 같은 저장본을 공유
        rank_countries,
        scan_unexplained,
    )

    from . import response_cache
    from .cdc_travel_notices import travel_notices_summary
    from .comtrade_signals import trade_signals_all
    from .disaster_watch import disaster_watch_report
    from .korea_import_report import get_report

    def safe(fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001 — 한 층의 실패가 카드 전체를 죽이지 않게(그 층은 None)
            return None

    return {
        "extracted": safe(lambda: db.list_extracted_signals(limit=EXTRACTED_LIMIT)) or [],
        "unexplained": safe(lambda: response_cache.swr("unexplained", 600, scan_unexplained)),
        "disaster": safe(disaster_watch_report),
        "trade": safe(trade_signals_all),
        "travel": safe(travel_notices_summary),
        "risk": safe(lambda: response_cache.swr("risk-index", 600, rank_countries)),
        "korea": safe(get_report),
    }


def country_cards(lang: str = "ko") -> dict[str, Any]:
    return build_cards(**collect_inputs(), lang=lang)


def telegram_text(result: dict, top: int = 5, site_url: str | None = None) -> str:
    """매일 텔레그램 요약 — 관측 강도 상위 나라. HTML parse_mode 라 값은 이스케이프한다."""
    import html

    grade_ko = {"high": "높음", "elevated": "주의", "watch": "관찰"}
    lines = ["🌍 <b>오늘의 나라별 관측 카드</b> (관측 강도 상위)"]
    for c in result.get("cards", [])[:top]:
        n = c["counts"]
        parts = [
            f"보도 {n['event']}", f"설명불가 {n['unexplained']}", f"재난 {n['disaster']}", f"무역 {n['trade']}",
        ]
        if c.get("travel_level"):
            parts.append(f"CDC L{c['travel_level']}")
        k = c.get("korea") or {}
        if k.get("routes") or k.get("passengers"):
            parts.append(f"한국 직항 {k.get('routes') or 0}")
        lines.append(
            f"• <b>{html.escape(str(c['name']))}</b> {c['intensity']}/100 ({grade_ko.get(c['grade'], c['grade'])}) — "
            + html.escape(" · ".join(parts))
        )
    if not result.get("cards"):
        lines.append("• 오늘은 카드로 묶일 관측이 없음")
    lines.append("<i>관측 강도 = 받은 관측의 양·무게 가중합(추정, 가중치 미보정) · 발병 확률 아님</i>")
    if site_url:
        lines.append(html.escape(f"{site_url.rstrip('/')}/ko/observations"))
    return "\n".join(lines)

"""대한민국 해외 유입 위험 주간 보고서 (2026-10-19, 캡틴 승인 ③).

## 왜

기능은 많은데 기관이 손에 쥘 결과물이 없었다. 질병청·검역소가 매주 받아 볼 한 장짜리
보고서를 이미 있는 부품으로 묶는다 — 새 수집·새 계산 없이:

    국가별 이상도(country_risk.rank_countries)  ×  한국 직항 연결(OpenFlights 노선 수)
    + 이웃 나라 주간 추세(weekly_forecast) + 이번 주 경보(alerts)

ISO 주마다 한 번 만들어 DB 에 보관한다(지난 보고서를 다시 볼 수 있게).

## 정직성 경계선

- **유입 노출 지수는 확률이 아니다.** 이상도(0~100)와 직항 노선 수(로그 정규화)를 곱한
  순위용 지수다. "유입될 확률 N%"로 쓰지 않는다.
- **노선 수는 승객 수가 아니다.** OpenFlights 2014 기준 '노선 개수'다(digital_twin 과
  같은 캐시). 편수·좌석은 반영되지 않는다.
- 이상도가 없는 나라(신호 없음)는 순위에 넣지 않는다 — 취약성만으로 만든 기준선 점수를
  위험처럼 보이게 하지 않는다.
- 직항이 없어도 이상도가 높은 나라는 따로 적는다 — 경유 유입은 이 지수가 못 본다.
- 이상 신호는 '확인이 필요한 신호'이지 발병 확정이 아니다.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from typing import Any

from .country_resolve import korean_name

KOR = "KOR"
TOP_N = 10
NO_ROUTE_RAW_MIN = 70          # 직항 없는 나라를 따로 적는 이상도 문턱(country_risk 와 같은 2σ 선)
CAVEATS = (
    "유입 노출 지수는 순위용 지수이며 확률이 아님",
    "직항 노선 수는 OpenFlights 2014 기준 '노선 개수' — 승객·편수 아님",
    "이상 신호 = 확인이 필요한 신호 · 발병 확정 아님",
    "경유 유입은 지수에 반영되지 않음 — 직항 없는 고이상도 국가를 별도 기재",
    "이웃 나라 주간 추세의 확률은 표본 8건 미만이면 성적 판정 전 값",
)


def week_key(now: dt.datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def routes_to_korea(routes: dict[tuple[str, str], int], country: str) -> int:
    return routes.get(tuple(sorted((country, KOR))), 0) or 0


def build_report(ranked: list[dict], routes: dict[tuple[str, str], int],
                 alerts: list[dict], weekly_rows: list[dict], now: dt.datetime,
                 routes_error: str | None = None) -> dict:
    """순수 함수 — 입력만으로 보고서를 만든다(시험 가능)."""
    # 정규화 기준은 '한국 노선 전체 중 최대'다 — 순위에 든 나라 중 최대로 잡으면 주마다
    # 어떤 나라가 들어오느냐에 따라 같은 나라의 지수가 말없이 바뀐다.
    max_routes = max((n for pair, n in routes.items() if KOR in pair), default=0)

    exposed, no_route, domestic = [], [], None
    for c in ranked:
        if c.get("raw_score") is None:
            continue                                   # 신호 없음 — 순위에 넣지 않는다
        if c["country"] == KOR:
            domestic = c
            continue
        n_routes = routes_to_korea(routes, c["country"])
        row = {
            # 표시명은 한글로 통일한다(표에 없으면 원래 이름 그대로 — 지어내지 않는다).
            "country": c["country"], "name": korean_name(c["country"]) or c.get("name"),
            "raw_score": c["raw_score"], "tier": c.get("tier"),
            "dominant_disease": c.get("dominant_disease"),
            "dominant_disease_share": c.get("dominant_disease_share"),
            "direct_routes_to_kor": n_routes,
        }
        if n_routes and max_routes:
            conn = math.log1p(n_routes) / math.log1p(max_routes)
            row["exposure_index"] = round(c["raw_score"] * conn, 1)
            exposed.append(row)
        elif c["raw_score"] >= NO_ROUTE_RAW_MIN:
            no_route.append(row)

    exposed.sort(key=lambda r: -r["exposure_index"])
    no_route.sort(key=lambda r: -r["raw_score"])

    # 이웃 나라 주간 추세 — 계열마다 가장 최근 예측 1건과 가장 최근 채점 1건
    from .weekly_forecast import SERIES_BY_KEY
    trends = []
    by_series: dict[str, list[dict]] = {}
    for r in sorted(weekly_rows, key=lambda r: r["id"], reverse=True):
        by_series.setdefault(r["series"], []).append(r)
    for key, rows in sorted(by_series.items()):
        latest = rows[0]
        last_scored = next((r for r in rows if r.get("outcome") in ("up", "down")), None)
        trends.append({
            "series": key,
            "label_ko": SERIES_BY_KEY.get(key, {}).get("label_ko", key),
            "base_week": f"{latest['base_year']}-W{latest['base_week']:02d}",
            "base_value": latest["base_value"],
            "target_week": f"{latest['target_year']}-W{latest['target_week']:02d}",
            "prob_up": latest["prob_up"],
            "last_scored": None if last_scored is None else {
                "target_week": f"{last_scored['target_year']}-W{last_scored['target_week']:02d}",
                "prob_up": last_scored["prob_up"], "outcome": last_scored["outcome"],
            },
        })

    active_alerts = [
        {"tier": a.get("tier"), "label": a.get("label"), "score": a.get("score")}
        for a in alerts if not a.get("suppressed")
    ]

    return {
        "week": week_key(now),
        "generated_at": now.isoformat(),
        "summary": {
            "countries_with_signal": sum(1 for c in ranked if c.get("raw_score") is not None),
            "exposed_countries": len(exposed),
            "no_direct_route_high": len(no_route),
            "active_alerts": len(active_alerts),
        },
        "top_exposure": exposed[:TOP_N],
        "no_direct_route_high": no_route,
        "domestic": None if domestic is None else {
            "raw_score": domestic["raw_score"], "tier": domestic.get("tier"),
            "dominant_disease": domestic.get("dominant_disease"),
        },
        "neighbor_trends": trends,
        "alerts": active_alerts,
        "routes_source": "OpenFlights routes.dat(2014 기준) · OurAirports",
        "routes_error": routes_error,
        "caveats": list(CAVEATS),
        "is_probability": False,
    }


def to_markdown(rep: dict) -> str:
    """보고서 한 장(보고체). 기관에 그대로 붙일 수 있는 형태."""
    s = rep["summary"]
    lines = [
        f"# 대한민국 해외 유입 위험 주간 보고서 — {rep['week']}",
        "",
        f"생성 {rep['generated_at'][:16].replace('T', ' ')} UTC · 아이기론(AEGIRON)",
        "",
        f"- 이상 신호 국가 {s['countries_with_signal']}곳 · 한국 직항 연결 {s['exposed_countries']}곳 · "
        f"직항 없는 고이상도 {s['no_direct_route_high']}곳 · 이번 주 활성 경보 {s['active_alerts']}건",
        "",
        "## 1. 유입 노출 상위 국가",
        "",
    ]
    if rep["top_exposure"]:
        lines += ["| 순위 | 국가 | 이상도 | 주요 질병 | 한국 직항 노선 | 노출 지수 |",
                  "|---|---|---|---|---|---|"]
        for i, r in enumerate(rep["top_exposure"], 1):
            disease = r["dominant_disease"] or "질병 미지목"
            lines.append(f"| {i} | {r['name'] or r['country']} | {r['raw_score']} | {disease} | "
                         f"{r['direct_routes_to_kor']} | {r['exposure_index']} |")
    else:
        lines.append("- 한국 직항 연결 국가 중 이상 신호 국가 없음")
    lines += ["", "## 2. 직항 없는 고이상도 국가 (경유 유입 주의)", ""]
    if rep["no_direct_route_high"]:
        for r in rep["no_direct_route_high"]:
            lines.append(f"- {r['name'] or r['country']} — 이상도 {r['raw_score']} · "
                         f"{r['dominant_disease'] or '질병 미지목'}")
    else:
        lines.append("- 해당 없음")
    lines += ["", "## 3. 이웃 나라 주간 추세 (일본 공식 표본감시)", ""]
    if rep["neighbor_trends"]:
        for t in rep["neighbor_trends"]:
            tail = ""
            if t["last_scored"]:
                ls = t["last_scored"]
                tail = (f" · 직전 채점 {ls['target_week']}: 예측 증가확률 {ls['prob_up']} → "
                        f"실제 {'증가' if ls['outcome'] == 'up' else '감소'}")
            lines.append(f"- {t['label_ko']}: {t['base_week']} {t['base_value']:,.0f}건 → "
                         f"{t['target_week']} 증가 확률 {t['prob_up']}{tail}")
    else:
        lines.append("- 주간 추세 예측 기록 없음")
    lines += ["", "## 4. 이번 주 활성 경보", ""]
    if rep["alerts"]:
        for a in rep["alerts"]:
            lines.append(f"- [{a['tier']}] {a['label']} ({a['score']}점)")
    else:
        lines.append("- 활성 경보 없음")
    lines += ["", "## 고지", ""] + [f"- {c}" for c in rep["caveats"]]
    if rep.get("routes_error"):
        lines.append(f"- ⚠ 항공 노선 캐시 문제: {rep['routes_error']} — 노출 지수 산출 불가")
    return "\n".join(lines) + "\n"


# ── 보관 ─────────────────────────────────────────────────────────────

def save_report(rep: dict) -> bool:
    import db

    with db.get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO weekly_reports (week, generated_at, payload) VALUES (?, ?, ?)",
            (rep["week"], rep["generated_at"], json.dumps(rep, ensure_ascii=False)))
        return cur.rowcount > 0


def get_report(week: str | None = None) -> dict | None:
    import db

    with db.get_connection() as conn:
        if week:
            row = conn.execute("SELECT payload FROM weekly_reports WHERE week=?", (week,)).fetchone()
        else:
            row = conn.execute(
                "SELECT payload FROM weekly_reports ORDER BY week DESC LIMIT 1").fetchone()
    return json.loads(row["payload"]) if row else None


def list_weeks(limit: int = 52) -> list[str]:
    import db

    with db.get_connection() as conn:
        return [r["week"] for r in conn.execute(
            "SELECT week FROM weekly_reports ORDER BY week DESC LIMIT ?", (limit,))]


def generate_if_due(now: dt.datetime | None = None) -> dict | None:
    """이번 ISO 주 보고서가 없으면 만든다. 이미 있으면 None(주당 1회)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if get_report(week_key(now)) is not None:
        return None
    import db
    from .country_risk import rank_countries
    from .digital_twin import load_flight_routes
    from .weekly_forecast import all_forecasts

    routes, routes_error = load_flight_routes()
    rep = build_report(
        ranked=rank_countries()["countries"],
        routes=routes,
        alerts=db.list_alerts(now.date().isoformat()),
        weekly_rows=all_forecasts(),
        now=now,
        routes_error=routes_error,
    )
    save_report(rep)
    return rep


SITE_URL_DEFAULT = "https://epiweather-web.vercel.app"


def telegram_text(rep: dict, site_url: str | None = None) -> str:
    """주간 보고서 텔레그램 요약(2026-10-19 — 만들어만 두고 받는 사람이 없던 결과물).

    값은 HTML 이스케이프한다(parse_mode=HTML). 노출 지수가 확률이 아니라는 고지를 본문에 싣는다."""
    import html
    import os

    site = (site_url or os.environ.get("EPIWEATHER_SITE_URL") or SITE_URL_DEFAULT).rstrip("/")
    s = rep["summary"]
    esc = lambda v: html.escape(str(v), quote=False)
    lines = [
        f"🇰🇷 <b>대한민국 해외 유입 위험 주간 보고서 {esc(rep['week'])}</b>",
        f"이상 신호 국가 {s['countries_with_signal']}곳 · 한국 직항 연결 {s['exposed_countries']}곳 · "
        f"직항 없는 고이상도 {s['no_direct_route_high']}곳 · 활성 경보 {s['active_alerts']}건",
    ]
    top = rep.get("top_exposure") or []
    if top:
        lines.append("노출 상위: " + " · ".join(
            f"{esc(r['name'] or r['country'])} {r['exposure_index']}" for r in top[:5]))
    else:
        lines.append("한국 직항 연결 국가 중 이상 신호 국가 없음")
    if rep.get("no_direct_route_high"):
        lines.append("직항 없는 고이상도: " + " · ".join(
            esc(r["name"] or r["country"]) for r in rep["no_direct_route_high"][:5]))
    if rep.get("routes_error"):
        lines.append("⚠ 항공 노선 캐시 문제 — 이번 주 노출 지수 산출 불가")
    lines += [
        "",
        "<i>노출 지수는 순위용 지수이며 확률이 아님 · 이상 신호 = 확인이 필요한 신호, 발병 확정 아님</i>",
        f"전문: {site}/ko/record",
    ]
    return "\n".join(lines)


def notify_new_report(rep: dict) -> str:
    """새로 만든 보고서를 텔레그램으로 보낸다. 상태 문구를 돌려준다(로그용).

    EPIWEATHER_WEEKLY_REPORT_NOTIFY=off 면 보내지 않는다. 전송 실패는 재시도하지 않는다 —
    보고서는 이미 저장돼 /record 와 API 에 게시돼 있다."""
    import os

    from .notifier import send_telegram_message, telegram_configured

    if os.environ.get("EPIWEATHER_WEEKLY_REPORT_NOTIFY", "on").strip().lower() in ("off", "0", "false"):
        return "꺼 둠"
    if not telegram_configured():
        return "채널 미설정"
    if send_telegram_message(telegram_text(rep)):
        return "전송됨"
    return "전송 실패(재시도 없음 — /record·API 에 게시됨)"


def report_line(rep: dict) -> str:
    s = rep["summary"]
    top = ", ".join(f"{r['name'] or r['country']}({r['exposure_index']})" for r in rep["top_exposure"][:3])
    return (f"🇰🇷 유입 주간 보고서 {rep['week']} 생성 — 이상 신호 국가 {s['countries_with_signal']}곳 · "
            f"직항 연결 {s['exposed_countries']}곳" + (f" · 상위 {top}" if top else "") +
            f" · 직항 없는 고이상도 {s['no_direct_route_high']}곳")

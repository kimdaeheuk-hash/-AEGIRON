"""판매용 데이터셋 카탈로그 + 내보내기 (2026-11-16).

캡틴: "보고해서 데이터로 집계해 판매할 수 있게 전부 셋팅해야 해". 데이터 활용 계획 ④.

## 무엇을 파나

이미 운영 DB 에 쌓인 것 중 **사람이 사서 쓸 수 있는 모양**으로 정리할 수 있는 여섯 묶음:
경보 이력 · 발생 보도(구조화) · 관측값 시계열 · 예측 원장 · 선행성 원장 · 한국 해외유입 주간 보고서.

## 상업 이용 조건(라이선스) — 지어내지 않는다

데이터셋(관측값은 층)마다 원천과 상업 이용 상태를 적는다. 상태는 셋 중 하나:

- ``allowed``  — 우리 자체 산출이거나 원천이 상업 재배포를 허용(출처 표기 조건 포함).
- ``derived``  — 아이기론 가공 지표(정제 상품): 원문·원값을 넘기지 않고 중복 제거·정규화·집계·순위만 판다.
  사실과 우리 계산만 담는다는 내부 판단 — 계약 전 법률 확인을 권한다(문서에 적음). 유료 내보내기에 포함.
- ``review``   — 원천 조건을 아직 확정 못 했거나 법률 검토가 필요. 표본은 보여 주되 **유료 내보내기에서 뺀다**.
- ``blocked``  — 원천 조건이 지금 방식의 상업 이용을 막는다(예: Open-Meteo 무료 API 는 비상업 전용).
  유료 계약·허가를 받기 전까지 **표본·유료 내보내기 모두에서 뺀다**.

근거는 docs/데이터판매_준비_2026-11.md(2026-11-16 웹 검색으로 확인한 원천 약관 요약)에 있다.
상태를 바꾸려면 그 문서를 먼저 고치고 여기 표를 맞춘다.

## 접근

- 키 없이: 무료 표본 — 최근 7일·최대 100행, allowed+review 만.
- 고객 키(EPIWEATHER_DATA_KEYS="라벨:키,…", X-Data-Key 헤더): 기간 지정·최대 50,000행, allowed 만.
  호출은 db.api_key_usage 에 라벨별로 남는다(요율·과금 정책은 고객이 생긴 뒤 실제 사용량을 보고 정한다).
- 원문 보호: 발생 보도의 원문(raw_text)은 내보내지 않는다 — 구조화된 사실 칸 + 출처 이름만.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone

ALLOWED, DERIVED, REVIEW, BLOCKED = "allowed", "derived", "review", "blocked"

# 관측값 층별 원천·상태
OBS_LAYER_LICENSE: dict[str, tuple[str, str, str]] = {
    # layer: (원천, 상태, 근거 한 줄)
    "polar": ("Open-Meteo(+Google News 제목 수)", BLOCKED, "Open-Meteo 무료 API 는 비상업 전용 — 상업 구독 필요"),
    "climate": ("Open-Meteo", BLOCKED, "Open-Meteo 무료 API 는 비상업 전용 — 상업 구독 필요"),
    "land": ("NASA FIRMS", REVIEW, "NASA 자료는 대체로 자유 이용이나 FIRMS 조건 미확인"),
    "deforestation": ("Global Forest Watch", REVIEW, "GFW 데이터셋별 라이선스 미확인"),
    "trade": ("UN Comtrade", BLOCKED, "Comtrade 라이선스는 상업적 재배포를 제한 — 허가(comtrade@un.org) 필요"),
    "disaster": ("GDACS", REVIEW, "EC 재사용 정책(CC BY 계열) 추정 — 2025-03 약관 원문 확인 필요"),
    "travel": ("CDC Travelers' Health", ALLOWED, "CDC 웹 자료는 별도 표기 없으면 공공 영역 — 출처 표기"),
}

DATASETS: dict[str, dict] = {
    # ── 정제 상품(가공 2차 데이터) — 판매의 중심 (2026-11-16 캡틴 "가공하고 정제해서") ──
    "outbreak_events": {
        "title": "정제 발생 사건",
        "description": "여러 출처 보도를 질병명 정규화·국가 코드화·중복 제거해 (질병, 국가) 사건 단위로 묶은 표 — 처음/마지막 확인일, 보도·출처 수, 확신도, 최근 상태, 공식 선언일·선행일수.",
        "builder": "outbreak_events",
        "time_column": "last_seen",
        "columns": ["event_id", "disease", "country_iso3", "first_seen", "last_seen", "duration_days", "report_count",
                    "source_count", "sources", "max_source_trust", "confidence", "latest_status", "surge_reports",
                    "new_reports", "unexplained_share", "declared_on", "lead_days_vs_declaration", "basis"],
        "measured_vs_derived": "전부 아이기론 가공 지표(AI 추출 집계·추정). 확신도 = 1-(1-최고신뢰도)×0.5^(출처수-1). 확진 건수 아님.",
        "sources": "아이기론 가공(원천: WHO·지역 보건기구·언론 보도의 사실 정보 — 원문 미포함)",
        "license": DERIVED,
        "license_note": "원문·원값 없이 사건 단위 집계·지표만. 법률 확인 권장.",
    },
    "country_week_panel": {
        "title": "국가 × 주 위험 활동 패널",
        "description": "ISO 주마다 나라별 보도 수·질병 수·대표 질병·신규/급증/설명불가 보도·평균 신뢰도·진행 중 사건 수, 그 주 국가 간 활동 백분위, 한국 유입 노출 지수.",
        "builder": "country_week_panel",
        "time_column": "week",
        "columns": ["week", "country_iso3", "report_count", "distinct_diseases", "top_disease", "new_reports",
                    "surge_reports", "unexplained_reports", "mean_source_trust", "active_events",
                    "activity_percentile", "korea_exposure_index", "anomaly_score", "basis"],
        "measured_vs_derived": "전부 아이기론 가공 지표. 활동 백분위 = 그 주 보도가 있던 나라들 사이 순위(보도 없는 나라는 미관측).",
        "sources": "아이기론 가공(보도 사실 정보 + 주간 유입 보고서)",
        "license": DERIVED,
        "license_note": "집계·순위·지수만. 법률 확인 권장.",
    },
    "disease_week_panel": {
        "title": "질병 × 주 확산 패널",
        "description": "ISO 주마다 정규화 질병별 영향 국가 수·국가 목록·그 주 새로 나타난 국가·보도 수·급증 보도 수.",
        "builder": "disease_week_panel",
        "time_column": "week",
        "columns": ["week", "disease", "countries_affected", "countries", "new_countries", "report_count",
                    "surge_reports", "unlocated_reports", "basis"],
        "measured_vs_derived": "전부 아이기론 가공 지표(AI 추출 집계).",
        "sources": "아이기론 가공(보도 사실 정보)",
        "license": DERIVED,
        "license_note": "집계만. 법률 확인 권장.",
    },
    # ── 원자료 성격의 기록(참고·검증용) ──
    "alerts": {
        "title": "경보 이력",
        "description": "매시 경보 주기가 만든 경보 — 등급·점수·근거(원시값·기준선·신뢰도). 우리 산출.",
        "table": "alerts",
        "time_column": "alert_date",
        "columns": ["alert_date", "source", "tier", "label", "score", "evidence", "suppressed", "updated_at"],
        "measured_vs_derived": "점수·등급 = 우리 계산(추정). 근거 안의 관측값 = 출처 측정값.",
        "sources": "자체 산출(근거에 공개 원천 값 포함)",
        "license": REVIEW,
        "license_note": "점수·등급은 자체 산출. 근거 문장에 WHO 등 원천 값이 섞여 있어 원천별 검토 전까지 review.",
    },
    "outbreak_reports": {
        "title": "발생 보도(구조화)",
        "description": "WHO·지역 보건기구·언론 보도를 AI 로 구조화한 사실 칸(질병·장소·국가·유형·기준일). 원문은 빼고 출처 이름만.",
        "table": "extracted_signals",
        "time_column": "extracted_at",
        "columns": [
            "extracted_at", "source", "disease", "location", "country_iso3", "signal_type",
            "signal_date", "known_disease", "source_trust", "ai_provider",
        ],
        "measured_vs_derived": "모든 칸 = AI 추출(확진 아님, 원문 확인 필요).",
        "sources": "WHO DON·지역 보건기구·언론(출처별)",
        "license": REVIEW,
        "license_note": "사실 정보만 내보내지만 WHO 자료는 상업 이용에 허가가 필요(CC BY-NC-SA 3.0 IGO) — 법률 검토 전 review.",
    },
    "observations": {
        "title": "관측값 시계열",
        "description": "극지·기후·토지·삼림·무역·재난·여행경보의 측정값/해석값 시계열(2026-11-15~). 층마다 상업 조건이 다르다.",
        "table": "observations",
        "time_column": "observed_at",
        "columns": [
            "layer", "target", "metric", "status", "measured", "derived", "reason",
            "source", "observed_at", "confirmed_at", "checks",
        ],
        "measured_vs_derived": "measured = 출처 측정값, derived = 우리 계산(추정). status=undetermined = 그 시각 판정 안 함.",
        "sources": "층별 원천(layers 참고)",
        "license": "by_layer",
        "license_note": "층별 상태를 따른다 — blocked 층은 표본·유료 모두 제외.",
    },
    "predictions": {
        "title": "예측 원장",
        "description": "질병 지목 예측과 판정(맞음·틀림·선행일수). 내용 해시로 사후 수정 방지.",
        "table": "predictions",
        "time_column": "predicted_at",
        "columns": [
            "predicted_at", "country", "disease", "risk_score", "basis", "verified_at",
            "actual_result", "lead_days", "correct", "content_hash",
        ],
        "measured_vs_derived": "risk_score = 우리 예측(추정). 판정 칸 = 사후 확인 결과.",
        "sources": "자체 산출",
        "license": ALLOWED,
        "license_note": "자체 산출.",
    },
    "lead_time": {
        "title": "선행성 원장",
        "description": "우리 신호가 문턱을 넘은 시각 → 공식 선언일. 오경보(선언 없음)도 지우지 않는다.",
        "table": "lead_time_ledger",
        "time_column": "crossed_at",
        "columns": [
            "disease", "country_iso3", "crossed_at", "severity", "threshold",
            "resolved_at", "declared_on", "lead_days", "outcome",
        ],
        "measured_vs_derived": "crossed_at·severity = 우리 기록. declared_on = 공식 선언(외부).",
        "sources": "자체 산출 + 공식 선언일",
        "license": ALLOWED,
        "license_note": "자체 기록. 선언일은 사실 정보.",
    },
    "weekly_import_reports": {
        "title": "한국 해외유입 위험 주간 보고서",
        "description": "ISO 주마다 1건 — 나라별 이상도 × 한국 항공 연결, 이웃 나라 주간 추세, 유의사항.",
        "table": "weekly_reports",
        "time_column": "generated_at",
        "columns": ["week", "generated_at", "payload"],
        "measured_vs_derived": "노출 지수 = 우리 계산(순위용, 확률 아님). 여객 수 = 공공데이터 측정값.",
        "sources": "자체 산출 + 인천공항 운송실적(공공데이터, 이용허락 제한 없음) + OpenFlights(ODbL) + 일본 IDWR",
        "license": REVIEW,
        "license_note": "OpenFlights 는 ODbL(출처·동일조건), 일본 IDWR 재이용 조건 미확인 — 확인 전 review.",
    },
}

SAMPLE_DAYS = 7
SAMPLE_ROWS = 100
MAX_ROWS = 50_000


def data_keys() -> dict[str, str]:
    """키 → 라벨. 비어 있으면 유료 내보내기는 꺼져 있다(표본만)."""
    out: dict[str, str] = {}
    for pair in os.environ.get("EPIWEATHER_DATA_KEYS", "").split(","):
        if ":" in pair:
            label, key = pair.split(":", 1)
            if label.strip() and key.strip():
                out[key.strip()] = label.strip()
    return out


def catalog(inventory: dict | None = None) -> dict:
    """카탈로그 — 데이터셋 정의 + 보유량(있으면) + 층별 상태."""
    tables = (inventory or {}).get("tables", {})
    items = []
    for ds_id, d in DATASETS.items():
        inv = tables.get(d["table"], {}) if d.get("table") else (built_coverage(ds_id) or {})
        item = {
            "id": ds_id,
            **{k: d[k] for k in ("title", "description", "columns", "measured_vs_derived", "sources", "license", "license_note")},
            "coverage": {k: inv.get(k) for k in ("rows", "first", "last", "days")} if inv else None,
        }
        if ds_id == "observations":
            item["layers"] = [
                {"layer": layer, "source": src, "license": st, "note": note}
                for layer, (src, st, note) in OBS_LAYER_LICENSE.items()
            ]
        items.append(item)
    return {
        "datasets": items,
        "access": {
            "sample": f"키 없이 최근 {SAMPLE_DAYS}일·최대 {SAMPLE_ROWS}행 (allowed·derived·review)",
            "paid": f"고객 키(X-Data-Key)로 기간 지정·최대 {MAX_ROWS}행 (allowed·derived)",
            "paid_enabled": bool(data_keys()),
            "formats": ["json", "csv"],
        },
        "license_states": {
            ALLOWED: "상업 이용 가능(출처 표기 조건 포함)",
            DERIVED: "아이기론 가공 지표 — 원문·원값 없이 집계·지표만, 유료 판매 포함(법률 확인 권장)",
            REVIEW: "원천 조건 확인·법률 검토 중 — 표본만, 유료 내보내기 제외",
            BLOCKED: "원천 조건상 지금 방식의 상업 이용 불가 — 표본·유료 모두 제외",
        },
        "pricing": "미정 — 문의(파일럿 협약)",
        "basis": "상업 조건은 2026-11-16 원천 약관 확인 결과(docs/데이터판매_준비_2026-11.md). 법률 자문 전 단계.",
    }


def _allowed_states(paid: bool) -> set[str]:
    return {ALLOWED, DERIVED} if paid else {ALLOWED, DERIVED, REVIEW}


def export_rows(ds_id: str, *, paid: bool, since: str | None = None, until: str | None = None,
                limit: int | None = None) -> dict:
    """데이터셋 행을 꺼낸다. 상태가 막힌 데이터셋·층은 빼고, 뺀 이유를 excluded 에 적는다."""
    import db

    d = DATASETS.get(ds_id)
    if d is None:
        raise KeyError(ds_id)
    states = _allowed_states(paid)
    excluded: list[str] = []
    where: list[str] = []
    params: list = []

    if d["license"] != "by_layer" and d["license"] not in states:
        return {
            "dataset": ds_id, "rows": [], "excluded": [f"{ds_id}: {d['license']} — {d['license_note']}"],
            "paid": paid, "license": d["license"],
        }
    if d["license"] == "by_layer":
        ok_layers = [lay for lay, (_s, st, _n) in OBS_LAYER_LICENSE.items() if st in states]
        excluded += [f"observations/{lay}: {st} — {note}" for lay, (_s, st, note) in OBS_LAYER_LICENSE.items()
                     if st not in states]
        if not ok_layers:
            return {"dataset": ds_id, "rows": [], "excluded": excluded, "paid": paid, "license": "by_layer"}
        where.append(f"layer IN ({','.join('?' * len(ok_layers))})")
        params += ok_layers

    tc = d["time_column"]
    now = datetime.now(timezone.utc)
    if not paid:
        since = (now - timedelta(days=SAMPLE_DAYS)).date().isoformat()
        until = None
    if d.get("builder"):
        return _export_built(ds_id, d, paid=paid, since=since, until=until, limit=limit)
    if since:
        where.append(f"{tc} >= ?")
        params.append(since)
    if until:
        where.append(f"{tc} <= ?")
        params.append(until)
    cap = SAMPLE_ROWS if not paid else min(int(limit or MAX_ROWS), MAX_ROWS)
    sql = f"SELECT {', '.join(d['columns'])} FROM {d['table']}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {tc} DESC LIMIT ?"
    params.append(cap)
    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    # JSON 문자열 칸은 풀어서 준다(CSV 에서는 다시 문자열)
    for r in rows:
        for k in ("evidence", "measured", "derived", "payload"):
            if isinstance(r.get(k), str):
                try:
                    r[k] = json.loads(r[k])
                except ValueError:
                    pass
    return {
        "dataset": ds_id,
        "title": d["title"],
        "paid": paid,
        "license": d["license"],
        "measured_vs_derived": d["measured_vs_derived"],
        "since": since,
        "until": until,
        "row_cap": cap,
        "count": len(rows),
        "truncated": len(rows) >= cap,
        "excluded": excluded,
        "attribution": d["sources"],
        "rows": rows,
    }


def _week_or_date(v: str | None) -> str | None:
    """since/until(YYYY-MM-DD) 를 주 칸('2026-W46')과 비교할 수 있게 바꾼다."""
    if not v:
        return None
    try:
        y, w, _ = datetime.fromisoformat(v[:10]).date().isocalendar()
        return f"{y}-W{w:02d}"
    except ValueError:
        return v


def _export_built(ds_id: str, d: dict, *, paid: bool, since: str | None, until: str | None,
                  limit: int | None) -> dict:
    from algorithms.refined_products import BUILDERS

    rows = BUILDERS[d["builder"]]()
    tc = d["time_column"]
    lo = _week_or_date(since) if tc == "week" else since
    hi = _week_or_date(until) if tc == "week" else until
    if lo:
        rows = [r for r in rows if str(r.get(tc) or "") >= lo]
    if hi:
        rows = [r for r in rows if str(r.get(tc) or "") <= hi + ("" if tc == "week" else "\uffff")]
    cap = SAMPLE_ROWS if not paid else min(int(limit or MAX_ROWS), MAX_ROWS)
    rows = [{c: r.get(c) for c in d["columns"]} for r in rows[:cap]]
    return {
        "dataset": ds_id, "title": d["title"], "paid": paid, "license": d["license"],
        "measured_vs_derived": d["measured_vs_derived"], "since": since, "until": until,
        "row_cap": cap, "count": len(rows), "truncated": len(rows) >= cap, "excluded": [],
        "attribution": d["sources"], "rows": rows,
    }


def built_coverage(ds_id: str) -> dict | None:
    """정제 상품의 보유량 — 행 수·처음/마지막(시간 칸 기준). 계산 실패는 None."""
    d = DATASETS.get(ds_id)
    if not d or not d.get("builder"):
        return None
    try:
        from algorithms.refined_products import BUILDERS

        rows = BUILDERS[d["builder"]]()
    except Exception:  # noqa: BLE001
        return None
    vals = sorted(str(r.get(d["time_column"]) or "") for r in rows if r.get(d["time_column"]))
    return {"rows": len(rows), "first": vals[0] if vals else None, "last": vals[-1] if vals else None,
            "days": None}


def to_csv(result: dict) -> str:
    rows = result.get("rows") or []
    buf = io.StringIO()
    if not rows:
        buf.write("# no rows\n")
        for e in result.get("excluded") or []:
            buf.write(f"# excluded: {e}\n")
        return buf.getvalue()
    cols = list(rows[0].keys())
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for v in
                    (r.get(c) for c in cols)])
    return buf.getvalue()

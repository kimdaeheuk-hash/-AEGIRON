"""선행성 원장 — "우리가 언제 알았나" 를 **선언 전에** 못 박는다 (2026-09-03).

## 왜 만들었나

캡틴: *"지금까지 한 번밖에 실측을 못한 거야? 이유가 뭐야?"*

파보니 **한 번도 못 했다.** 유일한 실측이라던 에볼라 DRC 2026 을 열어보니:

    공식 선언일        2026-05-15
    신호일 2026-05-15  →  우리가 기록한 날 2026-06-26   (+42일)
    신호일 2026-05-17  →  우리가 기록한 날 2026-08-10   (+85일)

**선언이 끝나고 두 달 뒤에 넣은 신호로 "선언보다 5일 먼저" 를 재고 있었다.**

원인은 방식 자체에 있었다. 지금까지는 **선언이 난 뒤에** `extracted_signals` 를
거꾸로 뒤져서 "그때 갖고 있었나" 를 따졌다. 그 방식은 사후에 적재된 것과 그때
손에 있던 것을 가리기 어렵고, 한 번 틀리면 제품의 핵심 주장이 통째로 거짓이 된다.

## 이 원장이 하는 일 — 순서를 뒤집는다

**매 수집 주기에 선제적으로 쓴다.** 어떤 (질병, 국가) 가 경보 문턱을 처음 넘는
순간, 그 자리에서 기록한다. 선언은 그 **뒤에** 온다.

    수집 주기  →  문턱 넘음 → 원장에 crossed_at 기록   ← 선언은 아직 없다
       ...
    며칠 뒤    →  공식 선언 → 원장을 찾아 lead_days 계산

그러므로 `crossed_at` 은 선언보다 앞설 수밖에 없다. **그 순서 자체가 증거다.**
나중에 무엇을 적재하든 이미 적힌 시각은 바뀌지 않는다.

## ★ 이 원장이 지키는 것 ★

- **빗나간 것도 남긴다.** 문턱을 넘었는데 끝내 선언이 안 나면 `no_declaration`
  으로 닫는다. 맞은 것만 세면 정밀도만 남고 재현율이 사라진다. 오경보율을 낼 수
  있어야 감시역학에서 말이 통한다.
- **한 번 적힌 crossed_at 을 고치지 않는다.** 같은 (질병, 국가) 가 계속 문턱
  위에 있어도 **첫 진입만** 기록한다. 매 주기 갱신하면 선행일수가 0 에 수렴한다.
- **선언 뒤에 생긴 진입은 선행이 아니다.** `lead_days <= 0` 이어도 그대로 적는다 —
  늦은 것도 기록이다. 다만 `outcome` 은 `declared` 이되 음수 선행일수로 남는다.
- **문턱 값을 함께 적는다.** 나중에 문턱을 바꾸면 옛 기록의 의미가 달라지는데,
  그때 어떤 문턱이었는지 모르면 되짚을 수 없다.
"""
from __future__ import annotations

import datetime as dt
import json
import re

import db

# 문턱을 넘은 뒤 이 기간 안에 공식 선언이 없으면 오경보로 닫는다.
# 되짚기(historical_backtest)의 관찰 창과 같은 90일을 쓴다 — 예측 판정 기한
# (country_risk.PREDICTION_HORIZON_DAYS)과 맞춰야 두 성적표가 같은 말을 한다.
RESOLUTION_HORIZON_DAYS = 90

OUTCOME_OPEN = "open"
OUTCOME_DECLARED = "declared"
OUTCOME_NO_DECLARATION = "no_declaration"
# 같은 선언에 걸린 두 번째 이후의 통과. 실측으로도, 오경보로도 세지 않는다.
OUTCOME_DUPLICATE = "duplicate"
# 문턱을 넘기 전에 같은 질병의 선언이 이미 있었다 — 이미 공개된 발병을 뒤따라 넘은 것이라 선행이 아니다
# (2026-10-25, 예측 채점기와 같은 구멍 — prediction_resolver 머리말 5). 실측으로도, 오경보로도 세지 않는다.
OUTCOME_ALREADY_DECLARED = "already_declared"
ALREADY_DECLARED_LOOKBACK_DAYS = 365


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _as_date(stamp: str | None) -> dt.date | None:
    if not stamp:
        return None
    try:
        return dt.date.fromisoformat(stamp[:10])
    except ValueError:
        return None


# ── 기록 ──────────────────────────────────────────────────────────────────

def open_crossing(disease: str, country_iso3: str | None, severity: float,
                  threshold: float, signal_ids: list[int],
                  now: dt.datetime | None = None) -> dict | None:
    """문턱을 넘은 것을 원장에 적는다. **이미 열려 있으면 아무것도 안 한다.**

    같은 (질병, 국가) 가 계속 문턱 위에 있어도 첫 진입만 남긴다 — 매 주기
    갱신하면 선행일수가 0 으로 수렴해 원장이 무의미해진다.
    """
    now = now or _now()
    if _open_entry(disease, country_iso3):
        return None

    stamp = now.isoformat()
    with db.get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO lead_time_ledger
                (disease, country_iso3, crossed_at, severity, threshold,
                 signal_ids, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (disease, country_iso3, stamp, float(severity), float(threshold),
             json.dumps(sorted(signal_ids)), OUTCOME_OPEN),
        )
        conn.commit()
        # ★ lastrowid 를 믿지 않는다 ★ INSERT OR IGNORE 가 무시되면 lastrowid 는
        # 0 이 아니라 **직전 값**이 남아, 안 넣은 행을 넣었다고 착각하게 된다.
        if cur.rowcount != 1:
            return None
        row = conn.execute("SELECT * FROM lead_time_ledger WHERE id = ?",
                           (cur.lastrowid,)).fetchone()
    return dict(row) if row else None


def _open_entry(disease: str, country_iso3: str | None) -> dict | None:
    with db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM lead_time_ledger
             WHERE disease = ? AND outcome = ?
               AND (country_iso3 IS ? OR country_iso3 = ?)
             ORDER BY crossed_at ASC LIMIT 1
            """,
            (disease, OUTCOME_OPEN, country_iso3, country_iso3),
        ).fetchone()
    return dict(row) if row else None


def list_entries(outcome: str | None = None, limit: int = 200) -> list[dict]:
    query = "SELECT * FROM lead_time_ledger"
    params: list = []
    if outcome:
        query += " WHERE outcome = ?"
        params.append(outcome)
    query += " ORDER BY crossed_at DESC LIMIT ?"
    params.append(limit)
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


# ── 해소 ──────────────────────────────────────────────────────────────────

def _close(entry_id: int, outcome: str, now: dt.datetime,
           event_id: str | None = None, declared_on: str | None = None,
           lead_days: int | None = None) -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            UPDATE lead_time_ledger
               SET outcome = ?, resolved_at = ?, event_id = ?,
                   declared_on = ?, lead_days = ?
             WHERE id = ?
            """,
            (outcome, now.isoformat(), event_id, declared_on, lead_days, entry_id),
        )
        conn.commit()


def _event_isos(event_id: str | None, event_name: str | None) -> set[str]:
    """선언 사건이 가리키는 나라들 — 사건 키의 `_iso3_연도` 꼬리와 이름에서 읽힌 나라."""
    from .country_resolve import resolve_countries
    isos = set(resolve_countries(event_name or ""))
    tail = re.search(r"_([a-z]{3})_\d{4}$", event_id or "")
    if tail:
        isos.add(tail.group(1).upper())
    return isos


def resolve_ledger(now: dt.datetime | None = None) -> dict:
    """열린 항목을 공식 선언과 맞춰 닫는다. 기한이 지나도 선언이 없으면 오경보.

    ★ 선언은 우리가 만드는 것이 아니다 ★ `outbreak_timeline` 에 실제로 적재된
    선언급 마일스톤만 정답으로 쓴다. 우리 신호로 우리를 채점하면 순환이 된다.
    """
    from .event_dedup import normalize_disease
    from .knowledge_graph import _DECLARATION_MILESTONE_KEYS

    now = now or _now()
    today = now.date()

    declarations = []
    for event in db.list_timeline_events():
        timeline = db.get_timeline(event["event_id"])
        for milestone in timeline.get("milestones", []):
            if milestone["milestone"] in _DECLARATION_MILESTONE_KEYS:
                declarations.append({
                    "event_id": event["event_id"],
                    "disease": normalize_disease(timeline["event_name"]),
                    "date": _as_date(milestone["event_date"]),
                    "isos": _event_isos(event["event_id"], timeline.get("event_name")),
                })
                break

    # ★★ 한 선언은 한 번만 센다 ★★
    # 같은 병이 (질병, 국가) 조합별로 여러 건 열려 있을 수 있다 — 실측에서
    # `에볼라/COD` 와 `에볼라/국가미상` 이 동시에 열렸다. 각각을 따로 채점하면
    # **선언 하나가 실측 두 건이 되어 우리 성적표를 우리가 부풀린다.**
    # 이미 채점된 선언도 세어둔다(지난 주기에 닫힌 것).
    credited: set[str] = {
        row["event_id"] for row in list_entries(outcome=OUTCOME_DECLARED, limit=1000)
        if row.get("event_id")
    }

    closed_declared, closed_silent, duplicates, already, still_open = [], [], [], [], 0
    blind = 0
    blind_reasons: dict[str, int] = {}
    # 먼저 넘은 것부터 본다 — 가장 이른 기록이 그 사건의 선행일수다.
    for entry in sorted(list_entries(outcome=OUTCOME_OPEN, limit=1000),
                        key=lambda e: e["crossed_at"]):
        crossed = _as_date(entry["crossed_at"])
        if crossed is None:
            continue

        prior = next(
            (d for d in sorted(declarations, key=lambda d: d["date"] or dt.date.max)
             if d["disease"] == entry["disease"] and d["date"]
             and crossed - dt.timedelta(days=ALREADY_DECLARED_LOOKBACK_DAYS) <= d["date"] < crossed
             # 나라를 아는 통과는 같은 나라의 선언만 본다 — 다른 나라에서 선언된 병은 이 나라의 선행을 막지 않는다.
             and (not entry.get("country_iso3") or entry["country_iso3"] in d["isos"])),
            None,
        )
        if prior:
            _close(entry["id"], OUTCOME_ALREADY_DECLARED, now,
                   event_id=prior["event_id"], declared_on=prior["date"].isoformat())
            already.append(entry)
            continue

        # ★ 우리가 먼저 적은 뒤에 나온 선언만 찾는다 ★ 원장 기록보다 앞선
        # 선언은 이 진입이 설명하는 사건이 아니다(이미 공개된 뒤에 넘은 것).
        match = next(
            (d for d in declarations
             if d["disease"] == entry["disease"] and d["date"]
             and crossed <= d["date"] <= crossed + dt.timedelta(days=RESOLUTION_HORIZON_DAYS)),
            None,
        )
        if match:
            if match["event_id"] in credited:
                # 같은 선언에 이미 다른 통과가 걸렸다 — 중복으로 닫는다.
                # 실측으로도 오경보로도 세지 않는다.
                _close(entry["id"], OUTCOME_DUPLICATE, now,
                       event_id=match["event_id"],
                       declared_on=match["date"].isoformat())
                duplicates.append(entry)
                continue
            lead = (match["date"] - crossed).days
            _close(entry["id"], OUTCOME_DECLARED, now,
                   event_id=match["event_id"], declared_on=match["date"].isoformat(),
                   lead_days=lead)
            credited.add(match["event_id"])
            closed_declared.append({**entry, "lead_days": lead,
                                    "event_id": match["event_id"]})
            continue

        if today > crossed + dt.timedelta(days=RESOLUTION_HORIZON_DAYS):
            # 기한이 지났는데 선언이 없다 — 오경보다. 지우지 않고 남긴다.
            # ★ 단, 정답 경로가 그 기간을 보고 있었을 때만 ★ 눈이 먼 채 지나간 침묵은 오경보가
            # 아니라 '못 봤다'다. 닫지 않고 열어 둔다(판정 안 함).
            from .ground_truth_channel import blind_reason, unread_reason
            window_end = crossed + dt.timedelta(days=RESOLUTION_HORIZON_DAYS)
            # 받았지만 못 읽은 발표가 구간에 있어도 '선언 없음'이라 말할 수 없다(ground_truth_channel 머리말).
            reason = blind_reason(crossed, window_end) or unread_reason(crossed, window_end)
            if reason:
                blind += 1
                blind_reasons[reason] = blind_reasons.get(reason, 0) + 1
                continue
            _close(entry["id"], OUTCOME_NO_DECLARATION, now)
            closed_silent.append(entry)
        else:
            still_open += 1

    return {
        "closed_declared": closed_declared,
        "closed_no_declaration": len(closed_silent),
        "closed_duplicate": len(duplicates),
        "closed_already_declared": len(already),
        "still_open": still_open,
        "blind": blind,
        "blind_reasons": blind_reasons,
        "horizon_days": RESOLUTION_HORIZON_DAYS,
    }


# ── 매 주기 훑기 ──────────────────────────────────────────────────────────

# 최근 이 기간의 신호만 본다. **오래된 자료를 오늘 적재해도 오늘의 통과로 세지
# 않기 위한 방어**다 — 2019년 자료를 오늘 백필하면 signal_date 가 2019년이므로
# 이 창에 안 들어온다. 이 한 줄이 없으면 백필 한 번이 가짜 선행 기록을 만든다.
SCAN_WINDOW_DAYS = 14


def scan_and_record(now: dt.datetime | None = None,
                    window_days: int = SCAN_WINDOW_DAYS) -> list[dict]:
    """지금 우리가 가진 신호로 (질병, 국가)별 심각도를 재고, 문턱을 넘으면 적는다.

    ★ 되짚기와 같은 문턱·같은 산식을 쓴다 ★ 그래야 두 성적표가 같은 말을 한다
    (`historical_backtest.PRIMARY_THRESHOLD_SCORE`, 신뢰도가중 평균).
    """
    from .country_risk import SIGNAL_TYPE_SEVERITY
    from .event_dedup import normalize_disease
    from .historical_backtest import PRIMARY_THRESHOLD_SCORE

    now = now or _now()
    floor = now.date() - dt.timedelta(days=window_days)

    groups: dict[tuple, list[tuple[float, float, int]]] = {}
    for record in db.list_extracted_signals(limit=2000):
        day = _as_date(record.get("signal_date") or record.get("extracted_at"))
        if day is None or day < floor:
            continue
        disease = normalize_disease(record.get("disease"))
        if not disease:
            continue
        severity = SIGNAL_TYPE_SEVERITY.get(record.get("signal_type"), 40)
        trust = record.get("source_trust") or 0.0
        if trust <= 0:
            continue
        key = (disease, record.get("country_iso3"))
        groups.setdefault(key, []).append((severity, trust, record["id"]))

    opened = []
    for (disease, iso3), rows in groups.items():
        weight = sum(t for _, t, _ in rows)
        if not weight:
            continue
        score = round(sum(s * t for s, t, _ in rows) / weight, 1)
        if score < PRIMARY_THRESHOLD_SCORE:
            continue
        entry = open_crossing(disease, iso3, score, PRIMARY_THRESHOLD_SCORE,
                              [i for _, _, i in rows], now=now)
        if entry:
            opened.append(entry)
    return opened


# ── 성적표 ────────────────────────────────────────────────────────────────

def ledger_record() -> dict:
    """원장 기반 선행일수 성적표. **0건이면 0건이라고 말한다.**"""
    declared = [e for e in list_entries(outcome=OUTCOME_DECLARED, limit=1000)
                if e.get("lead_days") is not None]
    silent = list_entries(outcome=OUTCOME_NO_DECLARATION, limit=1000)
    open_now = list_entries(outcome=OUTCOME_OPEN, limit=1000)

    ahead = [e["lead_days"] for e in declared if e["lead_days"] > 0]
    leads = [e["lead_days"] for e in declared]

    return {
        "measured_events": len(declared),
        "ahead_of_declaration": len(ahead),
        "mean_lead_days": round(sum(leads) / len(leads), 1) if leads else None,
        "median_lead_days": (sorted(leads)[len(leads) // 2] if leads else None),
        "best_lead_days": max(leads) if leads else None,
        # ★ 오경보를 숨기지 않는다 ★ 이게 없으면 정밀도만 있는 성적표가 된다.
        "false_alarms": len(silent),
        "open_crossings": len(open_now),
        # 같은 선언에 걸린 중복 통과. 실측에도 오경보에도 안 들어가지만 숨기지도 않는다.
        "duplicates": len(list_entries(outcome=OUTCOME_DUPLICATE, limit=1000)),
        # 이미 선언된 발병을 뒤따라 넘은 것. 실측에도 오경보에도 안 들어가지만 숨기지도 않는다.
        "already_declared": len(list_entries(outcome=OUTCOME_ALREADY_DECLARED, limit=1000)),
        "precision": (round(len(declared) / (len(declared) + len(silent)), 3)
                      if (declared or silent) else None),
        "horizon_days": RESOLUTION_HORIZON_DAYS,
        "is_prospective": True,
        "note": (
            "이 성적표는 **선언 전에 기록된** 문턱 통과만 센다. 사후에 적재한 "
            "신호로는 한 건도 만들 수 없다 — crossed_at 이 선언일보다 앞선다는 "
            "사실 자체가 증거다."
            if declared else
            "아직 선언과 맞춰진 기록이 없다. 이 값이 0인 동안에는 선행성 주장을 "
            "할 근거가 없다. 원장은 매 수집 주기에 쌓이고 있고, 다음 공식 선언이 "
            "나오면 그 자리에서 채점된다."
        ),
    }

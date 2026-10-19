"""주간 추세 예측 — 공식 주간 표본감시의 '다음 주 증감'을 봉인하고 채점한다 (2026-10-19).

## 왜 만드는가

90일 발병 예측(predictions)은 기한이 길어 피드백 루프가 '측정 대기'에 묶여 있다 —
첫 성적표가 몇 달 뒤다. 사업계획서의 가장 큰 약점이 "채점 0건"이었다(캡틴 승인 ②).
공식 기관이 **매주** 게시하는 값의 다음 주 증감을 예측하면 몇 주 안에 실제 채점 기록이
생긴다. 판정 기준이 공식 숫자 하나라 해석의 여지가 없다.

## 무엇을 예측하나

일본 IDWR 주간 표본감시 전국 합계(인플루엔자·코로나19·RSV). 주차가 명시되고, 주마다
공식 CSV 로 게시된다. 브라질 InfoDengue 는 최신 주 값이 나중에 계속 고쳐지고, KDCA 는
새 주가 일부만 채워져 들어온다 — 무엇을 정답으로 볼지가 흔들려 v1 에서 뺐다.

    예측: P(대상 주 값 > 기준 주 값)        대상 주 = 기준 주 다음 주(아직 미게시)
    정답: 대상 주의 공식 값(우리가 처음 본 값 — 나중에 고쳐진 값으로 바꾸지 않는다)

일본은 약 2주 늦게 게시하므로 대상 주의 날짜가 이미 지났을 수 있다. 예측 대상은
'날짜'가 아니라 **아직 게시되지 않은 공식 값**이다. 매시 수집기가 그 시각의 최신 게시
주를 돌려주고, 기록은 **그 주기에 확인한 최신 게시 주를 기준으로만** 한다 — 그래서
기준 주의 다음 주는 기록 시점에 미게시다. 수집이 실패한 주기에는 기록하지 않는다.

## 정직성 경계선

- **90일 발병 예측과 섞지 않는다.** 표·채점표·로그가 따로다. 맞히기 쉬운 방향 예측이
  발병 예측의 적중률을 부풀리면 그 숫자는 거짓이 된다.
- **기준선과 나란히 본다.** 동전 던지기(Brier 0.25)와 '지난주 방향 그대로'. 기준선을
  못 이기면 못 이긴다고 쓴다. 모델(momentum-v1)은 일부러 단순하다 — 이 층의 가치는
  모델이 아니라 **봉인된 채로 쌓이는 채점 기록**이고, 모델은 그 기록으로 개선한다.
- **판정 8건(MIN_SCORED) 미만이면 성적을 말하지 않는다** — '측정 중(표본 부족)'.
- 정답이 오지 않으면 오답이 아니라 **판정 안 함(void)** 으로 닫는다. 값이 그대로면
  증가도 감소도 아니므로 역시 void.
- 봉인은 생성 즉시 시도하고(OpenTimestamps), 실패하면 다음 주기가 다시 시도한다.
  봉인 시각은 그대로 남는다 — 늦은 봉인을 제때 한 것처럼 보이게 하지 않는다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from typing import Any, Callable

from .common import brief_reason

# ── 예측 대상 ─────────────────────────────────────────────────────────
# include: 질병 이름(CSV 머리글, 소문자)에 들어 있어야 하는 말. 정확히 한 열만 맞아야
# 쓴다 — 0개거나 여러 개면 그 주는 그 계열을 판정하지 않는다(이름이 바뀐 걸 다른 질병
# 값으로 채우지 않기 위해). 운영 CSV 머리글은 샌드박스에서 못 봤다 — 첫 운영 로그가 검증.
SERIES: tuple[dict, ...] = (
    {"key": "jp_influenza", "label_ko": "일본 인플루엔자 표본감시(전국·주간)",
     "source": "japan_idwr", "include": ("influenza",)},
    {"key": "jp_covid", "label_ko": "일본 코로나19 표본감시(전국·주간)",
     "source": "japan_idwr", "include": ("covid",)},
    {"key": "jp_rsv", "label_ko": "일본 RSV 감염증 표본감시(전국·주간)",
     "source": "japan_idwr", "include": ("respiratory syncytial", "rs virus", "rsv")},
)
SERIES_BY_KEY = {s["key"]: s for s in SERIES}

METHOD = "momentum-v1"
# 최근 두 주의 로그 변화율을 0.7/0.3 으로 섞어 로지스틱에 넣는다. SLOPE 6 이면 한 주에
# 10% 늘었을 때 약 0.6. 채점 기록이 쌓이기 전이라 맞춘(fit) 값이 아니라 정한 값이다.
SLOPE = 6.0
P_MIN, P_MAX = 0.1, 0.9          # 근거가 세 점뿐이라 확신을 0.9 위로 올리지 않는다
MIN_SCORED = 8                   # 이 건수 미만이면 성적을 말하지 않는다
VOID_AFTER_DAYS = 35             # 대상 주 시작 + 35일까지 정답이 없으면 판정 안 함으로 닫음
SYNC_EVERY_HOURS = 24            # 지난 주 게시분 동기화 주기
SYNC_WEEKS_BACK = 8              # 동기화 범위 — 첫 배포 때 기록이 바로 쌓이게 하는 몫도 겸함
SEAL_PER_CYCLE = 5


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ── 주(ISO) 계산 ───────────────────────────────────────────────────────

def week_start(year: int, week: int) -> dt.date:
    return dt.date.fromisocalendar(year, week, 1)


def next_week(year: int, week: int) -> tuple[int, int]:
    y, w, _ = (week_start(year, week) + dt.timedelta(days=7)).isocalendar()
    return y, w


def weeks_back(today: dt.date, n: int) -> list[tuple[int, int]]:
    """오늘 이전 n 개 ISO 주(오래된 순). 이번 주는 넣지 않는다 — 아직 끝나지 않은 주다."""
    out = []
    for k in range(n, 0, -1):
        y, w, _ = (today - dt.timedelta(days=7 * k)).isocalendar()
        out.append((y, w))
    return out


# ── 값 고르기 ─────────────────────────────────────────────────────────

def match_value(totals: dict | None, include: tuple[str, ...]) -> tuple[float | None, str | None]:
    """질병별 합계에서 한 계열의 값을 고른다. 반환: (값, 못 고른 사유)."""
    if not totals:
        return None, "합계 없음"
    hits = [name for name in totals
            if any(word in str(name).lower() for word in include)]
    if not hits:
        return None, "해당 열 없음"
    if len(hits) > 1:
        return None, f"열 {len(hits)}개 일치"
    value = totals[hits[0]]
    if value is None:
        return None, "값 없음"
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, "숫자 아님"


# ── 저장 ─────────────────────────────────────────────────────────────

def _store_observation(conn, series: str, year: int, week: int, value: float,
                       now: dt.datetime) -> bool:
    """처음 본 값만 남긴다(INSERT OR IGNORE). 채점은 '그 주에 게시된 값'으로 한다 —
    나중에 고쳐진 값으로 바꾸면 과거 채점이 말없이 달라진다."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO weekly_observations (series, year, week, value, observed_at) "
        "VALUES (?, ?, ?, ?, ?)", (series, year, week, value, now.isoformat()))
    return cur.rowcount > 0


def observe_record(rec: dict | None, now: dt.datetime) -> dict:
    """japan_idwr 한 주치 결과({year, week, national_totals})를 계열별로 저장한다."""
    import db

    stored, skipped = [], {}
    if not rec or rec.get("year") is None or rec.get("week") is None:
        return {"stored": stored, "skipped": {"*": "결과 없음"}}
    with db.get_connection() as conn:
        for s in SERIES:
            value, why = match_value(rec.get("national_totals"), s["include"])
            if value is None:
                skipped[s["key"]] = why
                continue
            if _store_observation(conn, s["key"], int(rec["year"]), int(rec["week"]), value, now):
                stored.append(s["key"])
    return {"stored": stored, "skipped": skipped}


def sync_history(fetch_week: Callable[[int, int], dict | None], now: dt.datetime) -> dict | None:
    """지난 주 게시분을 하루 한 번 채운다. 첫 배포 때 이력을 만드는 몫도 겸한다.

    매시 수집기는 '가장 최근 게시 주' 하나만 돌려주므로, 한 주를 건너뛰면 그 주 정답이
    영영 안 들어온다. 그래서 하루 한 번 최근 8주 중 비어 있는 주를 직접 받는다.
    반환 None = 이번 주기는 동기화 차례가 아님."""
    import db

    with db.get_connection() as conn:
        row = conn.execute("SELECT synced_at FROM weekly_sync WHERE source = 'japan_idwr'").fetchone()
        if row:
            last = dt.datetime.fromisoformat(row["synced_at"])
            if (now - last).total_seconds() < SYNC_EVERY_HOURS * 3600:
                return None
        have = {(r["year"], r["week"]) for r in conn.execute(
            "SELECT DISTINCT year, week FROM weekly_observations WHERE series LIKE 'jp_%'")}
        conn.execute("INSERT OR REPLACE INTO weekly_sync (source, synced_at) VALUES ('japan_idwr', ?)",
                     (now.isoformat(),))

    out = {"fetched": 0, "stored": 0, "unpublished": 0, "errors": {}}
    for y, w in weeks_back(now.date(), SYNC_WEEKS_BACK):
        if (y, w) in have:
            continue
        try:
            rec = fetch_week(y, w)
        except Exception as e:  # 한 주 실패가 나머지 주를 막지 않는다 — 사유는 센다
            reason = brief_reason(e)
            out["errors"][reason] = out["errors"].get(reason, 0) + 1
            continue
        if rec is None:
            out["unpublished"] += 1
            continue
        out["fetched"] += 1
        out["stored"] += len(observe_record(rec, now)["stored"])
    return out


# ── 예측 ─────────────────────────────────────────────────────────────

def forecast_prob(values: list[float]) -> tuple[float, int] | None:
    """연속 세 주 값 → (증가 확률, 지난주 방향 기준선 1/0). 0 이하가 섞이면 None."""
    if len(values) < 3 or any(v is None or v <= 0 for v in values[-3:]):
        return None
    v3, v2, v1 = values[-3:]
    d1 = math.log(v1 / v2)
    d2 = math.log(v2 / v3)
    m = 0.7 * d1 + 0.3 * d2
    p = 1.0 / (1.0 + math.exp(-SLOPE * m))
    p = round(min(P_MAX, max(P_MIN, p)), 3)
    return p, (1 if d1 > 0 else 0)


def _history(conn, series: str) -> list[tuple[int, int, float]]:
    rows = conn.execute(
        "SELECT year, week, value FROM weekly_observations WHERE series = ? "
        "ORDER BY year, week", (series,)).fetchall()
    return [(r["year"], r["week"], r["value"]) for r in rows]


def _consecutive_tail(hist: list[tuple[int, int, float]], n: int = 3) -> list[float] | None:
    """마지막 n 주가 빈 주 없이 이어져 있을 때만 값을 돌려준다."""
    if len(hist) < n:
        return None
    tail = hist[-n:]
    for (y0, w0, _), (y1, w1, _) in zip(tail, tail[1:]):
        if next_week(y0, w0) != (y1, w1):
            return None
    return [v for _, _, v in tail]


def canonical_hash(f: dict) -> str:
    """봉인 대상 — 예측 시점에 알던 것만. 정답·채점 필드는 넣지 않는다."""
    core = {k: f.get(k) for k in (
        "id", "series", "base_year", "base_week", "base_value",
        "target_year", "target_week", "prob_up", "naive_up", "method", "created_at")}
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_due(now: dt.datetime, latest_published: tuple[int, int] | None) -> dict:
    """계열마다 '최신 게시 주의 다음 주' 예측이 없으면 하나 남긴다(대상 주당 1건).

    ★ latest_published = 이번 주기 수집기가 **실제로 확인한** 최신 게시 주 ★
    저장된 마지막 주만 보고 기록하면, 이번 주기 수집이 실패한 날 이미 게시된 주를
    '예측'하게 된다(값을 보지는 않았어도 '미게시 값을 예측한다'는 약속이 깨진다).
    그래서 이번 주기에 최신 게시 주를 확인하지 못했으면 기록하지 않는다."""
    import db

    made, skipped = [], {}
    if latest_published is None:
        return {"made": made, "skipped": {"*": "이번 주기 최신 게시 주 확인 못 함 — 기록 안 함"}}
    with db.get_connection() as conn:
        for s in SERIES:
            hist = _history(conn, s["key"])
            if not hist:
                skipped[s["key"]] = "관측 없음"
                continue
            by, bw, bv = hist[-1]
            if (by, bw) != tuple(latest_published):
                skipped[s["key"]] = "최신 게시 주 값 없음"
                continue
            ty, tw = next_week(by, bw)
            exists = conn.execute(
                "SELECT 1 FROM weekly_forecasts WHERE series=? AND target_year=? AND target_week=?",
                (s["key"], ty, tw)).fetchone()
            if exists:
                continue
            tail = _consecutive_tail(hist)
            if tail is None:
                skipped[s["key"]] = "연속 3주 이력 부족"
                continue
            fp = forecast_prob(tail)
            if fp is None:
                skipped[s["key"]] = "0 이하 값 포함"
                continue
            prob, naive = fp
            created = now.isoformat()
            cur = conn.execute(
                "INSERT INTO weekly_forecasts (series, base_year, base_week, base_value, "
                "target_year, target_week, prob_up, naive_up, method, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (s["key"], by, bw, bv, ty, tw, prob, naive, METHOD, created))
            made.append({"id": cur.lastrowid, "series": s["key"], "target": f"{ty}-W{tw:02d}",
                         "prob_up": prob})
    return {"made": made, "skipped": skipped}


def seal_pending(submit: Callable[[str], str | None] | None = None,
                 limit: int = SEAL_PER_CYCLE) -> dict:
    """미봉인 주간 예측을 봉인한다. 캘린더 서버가 응답하지 않으면 거기서 멈춘다
    (prediction_timestamp.seal_pending_predictions 와 같은 판단)."""
    import db

    if submit is None:
        from .prediction_timestamp import submit_timestamp as submit
    sealed = failed = 0
    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM weekly_forecasts WHERE ots_proof_hex IS NULL ORDER BY id LIMIT ?",
            (limit,))]
    for f in rows:
        digest = canonical_hash(f)
        proof = submit(digest)
        if not proof:
            failed += 1
            break
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE weekly_forecasts SET content_hash=?, ots_proof_hex=?, ots_submitted_at=? "
                "WHERE id=?", (digest, proof, _now().isoformat(), f["id"]))
        sealed += 1
    with db.get_connection() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM weekly_forecasts WHERE ots_proof_hex IS NULL").fetchone()[0]
    return {"sealed": sealed, "failed": failed, "remaining": remaining}


# ── 채점 ─────────────────────────────────────────────────────────────

def resolve_due(now: dt.datetime) -> dict:
    """대상 주 값이 들어온 미결 예측을 채점한다."""
    import db

    resolved, voided = [], []
    with db.get_connection() as conn:
        open_rows = [dict(r) for r in conn.execute(
            "SELECT * FROM weekly_forecasts WHERE outcome IS NULL ORDER BY id")]
        for f in open_rows:
            obs = conn.execute(
                "SELECT value FROM weekly_observations WHERE series=? AND year=? AND week=?",
                (f["series"], f["target_year"], f["target_week"])).fetchone()
            if obs is None:
                deadline = week_start(f["target_year"], f["target_week"]) + dt.timedelta(days=VOID_AFTER_DAYS)
                if now.date() > deadline:
                    # 정답을 못 받은 것은 오답이 아니다.
                    conn.execute(
                        "UPDATE weekly_forecasts SET outcome='void', outcome_note=?, resolved_at=? "
                        "WHERE id=?", ("정답 미수신 — 기한 내 공식 값 게시 확인 못 함",
                                      now.isoformat(), f["id"]))
                    voided.append(f["id"])
                continue
            actual = obs["value"]
            if actual > f["base_value"]:
                outcome, note = "up", None
            elif actual < f["base_value"]:
                outcome, note = "down", None
            else:
                outcome, note = "void", "변화 없음 — 증가도 감소도 아님"
            conn.execute(
                "UPDATE weekly_forecasts SET actual_value=?, outcome=?, outcome_note=?, resolved_at=? "
                "WHERE id=?", (actual, outcome, note, now.isoformat(), f["id"]))
            (voided if outcome == "void" else resolved).append(f["id"])
    return {"resolved": resolved, "voided": voided}


def scorecard(rows: list[dict]) -> dict:
    """채점표. 판정 MIN_SCORED 건 미만이면 enough=False — 성적을 말하지 않는다."""
    scored = [r for r in rows if r.get("outcome") in ("up", "down")]
    n = len(scored)
    out: dict[str, Any] = {
        "scored": n,
        "void": sum(1 for r in rows if r.get("outcome") == "void"),
        "open": sum(1 for r in rows if r.get("outcome") is None),
        "min_scored": MIN_SCORED,
        "enough": n >= MIN_SCORED,
        "brier_coin": 0.25,
        "brier_model": None, "hits_model": None, "calls_model": None,
        "hits_naive": None, "calls_naive": None,
    }
    if not n:
        return out
    ys = [1 if r["outcome"] == "up" else 0 for r in scored]
    ps = [float(r["prob_up"]) for r in scored]
    out["brier_model"] = round(sum((p - y) ** 2 for p, y in zip(ps, ys)) / n, 4)
    calls = [(p > 0.5, y) for p, y in zip(ps, ys) if p != 0.5]   # 0.5 는 방향을 말하지 않은 것
    out["calls_model"] = len(calls)
    out["hits_model"] = sum(1 for up, y in calls if up == bool(y))
    naive = [(r.get("naive_up"), y) for r, y in zip(scored, ys) if r.get("naive_up") is not None]
    out["calls_naive"] = len(naive)
    out["hits_naive"] = sum(1 for nu, y in naive if int(nu) == y)
    return out


def list_forecasts(limit: int = 200) -> list[dict]:
    import db

    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM weekly_forecasts ORDER BY id DESC LIMIT ?", (limit,))]
    for r in rows:
        r["series_label_ko"] = SERIES_BY_KEY.get(r["series"], {}).get("label_ko")
    return rows


def all_forecasts() -> list[dict]:
    import db

    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM weekly_forecasts")]


# ── 매시 주기 ─────────────────────────────────────────────────────────

def run_cycle(japan_idwr: dict | None, fetch_week: Callable[[int, int], dict | None],
              now: dt.datetime | None = None,
              submit: Callable[[str], str | None] | None = None) -> dict:
    """수집 결과 저장 → (하루 한 번) 지난 주 동기화 → 채점 → 새 예측 → 봉인.
    채점을 기록보다 먼저 한다 — 같은 주기에 들어온 정답을 먼저 반영한다."""
    now = now or _now()
    observed = observe_record(japan_idwr, now)
    synced = sync_history(fetch_week, now)
    resolved = resolve_due(now)
    latest = ((int(japan_idwr["year"]), int(japan_idwr["week"]))
              if japan_idwr and japan_idwr.get("year") is not None
              and japan_idwr.get("week") is not None else None)
    recorded = record_due(now, latest)
    sealed = seal_pending(submit)
    return {"observed": observed, "synced": synced, "resolved": resolved,
            "recorded": recorded, "sealed": sealed, "card": scorecard(all_forecasts())}


def cycle_line(summary: dict) -> str:
    """로그 한 줄. 표본이 모자라면 성적 대신 그 사실을 쓴다."""
    card = summary["card"]
    parts = [f"새 예측 {len(summary['recorded']['made'])}건",
             f"채점 {len(summary['resolved']['resolved'])}건"]
    if summary["resolved"]["voided"]:
        parts.append(f"판정 안 함 {len(summary['resolved']['voided'])}건")
    if card["enough"]:
        parts.append(
            f"누적 판정 {card['scored']}건 · Brier {card['brier_model']} (동전 0.25) · "
            f"방향 적중 {card['hits_model']}/{card['calls_model']} "
            f"(지난주 방향 {card['hits_naive']}/{card['calls_naive']})")
    else:
        parts.append(f"누적 판정 {card['scored']}건 — {MIN_SCORED}건 미만이라 성적 판정 안 함")
    parts.append(f"미결 {card['open']}건")
    sealed = summary["sealed"]
    if sealed["remaining"]:
        parts.append(f"미봉인 {sealed['remaining']}건")
    skipped = {**summary["observed"]["skipped"], **summary["recorded"]["skipped"]}
    if skipped:
        parts.append("건너뜀 " + ", ".join(f"{k}({v})" for k, v in sorted(skipped.items())))
    synced = summary.get("synced")
    if synced and synced["errors"]:
        parts.append("동기화 실패 " + ", ".join(f"{k}×{v}" for k, v in synced["errors"].items()))
    return "📈 주간 예측: " + " · ".join(parts)

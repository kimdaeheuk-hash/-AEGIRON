"""조달 선행지표 — 입찰 속도의 변화율 (2026-11-03).

정부가 무엇을 사려는지는 태세 변화의 선행 신호다(나라장터 6시간·TED 주기
수집). 이번 7일 vs 직전 7일 공고 건수 배율로 급변을 본다(social_signal의
SURGE_RATIO=2.0과 같은 방식). KOR/TED 소스별 분리 — 합쳐서 한 숫자로
내면 어느 쪽인지 안 보인다(valhalla_watch 규칙).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "procurement_velocity.json"

SURGE_RATIO = 2.0
WINDOW_DAYS = 7
MAX_ENTRIES = 120  # 6시간 주기 × 30일


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load() -> list:
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:                                # noqa: BLE001
        return []


def _save(entries: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


def record(kor_count: int | None, ted_count: int | None = None,
           now: dt.datetime | None = None) -> None:
    """이번 주기 공고 건수 기록. 수집 주기(6시간)에서만 부른다."""
    try:
        entries = _load()
        entries.append({"ts": (now or _now()).isoformat(),
                        "kor": kor_count, "ted": ted_count})
        _save(entries[-MAX_ENTRIES:])
    except Exception:                                # noqa: BLE001
        pass  # 기록 실패가 수집을 깨면 안 된다


def _window_mean(entries: list, key: str, start: dt.datetime,
                 end: dt.datetime) -> float | None:
    vals = []
    for e in entries:
        try:
            ts = dt.datetime.fromisoformat(e["ts"])
        except (KeyError, ValueError):
            continue
        if start <= ts < end and isinstance(e.get(key), (int, float)):
            vals.append(e[key])
    if not vals:
        return None
    return sum(vals) / len(vals)


def velocity(now: dt.datetime | None = None) -> dict:
    """소스별 입찰 속도(7일 평균)와 직전 7일 대비 배율."""
    now = now or _now()
    entries = _load()
    recent_start = now - dt.timedelta(days=WINDOW_DAYS)
    prior_start = now - dt.timedelta(days=2 * WINDOW_DAYS)
    out = {}
    for key in ("kor", "ted"):
        recent = _window_mean(entries, key, recent_start, now)
        prior = _window_mean(entries, key, prior_start, recent_start)
        if recent is None or prior is None:
            out[key] = {"assessed": False,
                        "reason": "비교 구간(직전 7일) 기록 없음 — 2주기 쌓이면 판정"}
            continue
        ratio = round(recent / prior, 2) if prior > 0 else None
        out[key] = {"assessed": True, "recent_7d_mean": round(recent, 1),
                    "prior_7d_mean": round(prior, 1), "ratio": ratio,
                    "surge": ratio is not None and ratio >= SURGE_RATIO}
    out["window_days"] = WINDOW_DAYS
    out["surge_ratio"] = SURGE_RATIO
    return out

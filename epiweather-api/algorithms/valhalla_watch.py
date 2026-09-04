"""발할라 감시층 — 부를 때만 계산하던 것을 **쌓는다** (2026-09-03).

## 왜 만들었나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해!"* → 점검해보니 **아무것도 안
쌓이고 있었다.**

    수집기가 발할라를 도나?   0회
    브리핑에 발할라가 있나?   0회

발할라는 누가 엔드포인트를 부를 때만 계산했다. 그래서 어제 백신 공급이 어땠는지
오늘 비교할 수 없었다. 극지 관찰층이 2026-09-01 에 겪은 것과 똑같은 문제다 —
*"기능은 있는데 감시는 안 하고 있었다."*

## ★ 왜 다 매시간 돌리지 않는가 ★

이 층의 조각들은 **변하는 속도가 다르다.**

    준비태세·백신 공급   로컬 파일·DB — 네트워크 0회, 즉시
    조달 공고            나라장터 66회 호출 · 47초 — 하루 단위로 바뀐다
    임상 파이프라인       ClinicalTrials 17회 호출 — 달 단위로 바뀐다

임상시험 등록부를 매시간 긁는 건 낭비다. 그렇다고 무거운 것을 하루 한 번만
돌리면 **나머지 23주기가 값없음으로 쌓여 소스 헬스에 거짓 경보가 뜬다**
(극지층 주석에 적힌 그 함정).

그래서 이렇게 나눈다: **가벼운 조각은 매 주기 채운다** — 그러면 `valhalla` 키가
항상 있어서 헬스가 정상으로 돈다. **무거운 조각은 주기가 지났을 때만 새로
받고**, 아니면 지난번 성공분을 그대로 들고 간다. 그때 몇 시간 된 값인지
(`age_hours`) 를 함께 낸다 — 오래된 값을 새 값인 척하지 않는다.

## ★ 실패를 성공처럼 보이게 하지 않는다 ★

무거운 조각을 못 받으면 지난 값을 쓰되 `refreshed=False` 와 사유를 남긴다.
계속 실패하면 `age_hours` 가 자라므로, 조용히 굳은 값을 보고 있는 상황이
숫자로 드러난다.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "valhalla_state.json"

# 무거운 조각의 갱신 주기. 값이 바뀌는 속도에 맞춘다.
PROCUREMENT_EVERY_HOURS = 6      # 입찰공고는 하루 단위로 바뀐다
PIPELINE_EVERY_HOURS = 24        # 임상 단계는 달 단위로 바뀐다
PROCUREMENT_WINDOW_DAYS = 7


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # 파일이 깨졌다고 층을 죽이지 않는다. 다음 주기에 다시 쌓인다.
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _age_hours(stamp, now):
    if not stamp:
        return None
    try:
        then = dt.datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=dt.timezone.utc)
    return round((now - then).total_seconds() / 3600, 1)


def _due(stamp, every_hours: int, now) -> bool:
    age = _age_hours(stamp, now)
    return age is None or age >= every_hours


def _refresh_heavy(key: str, every_hours: int, fetch, state: dict, now) -> dict:
    """주기가 됐으면 새로 받고, 아니면 지난 값을 **나이와 함께** 들고 간다."""
    saved = state.get(key) or {}
    if not _due(saved.get("fetched_at"), every_hours, now):
        return {"refreshed": False, "reason": "갱신 주기 전",
                "age_hours": _age_hours(saved.get("fetched_at"), now),
                "value": saved.get("value")}
    try:
        value = fetch()
    except Exception as exc:                              # noqa: BLE001
        # 실패했는데 지난 값을 새 값처럼 내지 않는다. 사유와 나이를 남긴다.
        return {"refreshed": False,
                "reason": "%s: %s" % (FAILURE_PREFIX, type(exc).__name__),
                "age_hours": _age_hours(saved.get("fetched_at"), now),
                "value": saved.get("value")}
    state[key] = {"fetched_at": now.isoformat(), "value": value}
    return {"refreshed": True, "reason": None, "age_hours": 0.0, "value": value}


def _light_layers() -> dict:
    """네트워크를 쓰지 않는 조각들. **매 주기 채운다.**"""
    out = {}

    try:
        from .vaccine_supply import chokepoints
        choke = chokepoints()
        out["vaccine_chokepoints"] = (
            {"single_source_count": choke.get("single_source_count"),
             "vaccine_type_count": choke.get("vaccine_type_count"),
             "snapshot_date": choke.get("snapshot_date")}
            if choke.get("available") else {"error": choke.get("reason")}
        )
    except Exception as exc:                              # noqa: BLE001
        out["vaccine_chokepoints"] = {"error": type(exc).__name__}

    # ★ 정적 축의 나이 ★ 이 층의 두 축(백신 공급·국가 역량)은 파일에 얹혀 있다.
    # 예전엔 나이를 재는 곳이 없어서, 파일이 몇 달 묵어도 조달 숫자 옆에 나란히
    # 최신인 척 실렸다. 굳은 값을 새 값처럼 내지 않는다 — 무거운 조각에 age_hours
    # 를 붙인 것과 같은 이유다.
    try:
        from .reference_snapshots import report as _snapshot_report
        snap = _snapshot_report()
        out["reference_snapshots"] = {
            "stale": snap["stale_snapshots"],
            "ages_days": {r["name"]: r["age_days"] for r in snap["snapshots"]},
        }
    except Exception as exc:                              # noqa: BLE001
        out["reference_snapshots"] = {"error": type(exc).__name__}

    try:
        import db as _db
        from .biodefense_readiness import DEFAULT_THREATS, compute_readiness
        stored = _db.list_countermeasures()
        if stored:
            r = compute_readiness(stored, DEFAULT_THREATS)
            out["readiness"] = {
                "countermeasure_count": len(stored),
                "covered": r["coverage"]["covered"],
                "uncovered": r["coverage"]["uncovered"],
                # 판정 불가를 미커버와 섞지 않는다 (2026-09-03 결함 수정분).
                "unrated": r["coverage"]["unrated"],
                "coverage_rate": r["coverage"]["coverage_rate"],
                "sovereignty_rate": r["sovereignty"]["sovereignty_rate"],
                "domestic_but_unrated": r["sovereignty"]["domestic_but_unrated_threats"],
                "is_illustrative": False,
            }
        else:
            # 시연 데이터로 채우면 시계열에 가짜 값이 섞인다. 비워 둔다.
            out["readiness"] = {"error": "등록된 대응제가 없다 — 시연값을 쌓지 않는다"}
    except Exception as exc:                              # noqa: BLE001
        out["readiness"] = {"error": type(exc).__name__}

    return out


def _fetch_procurement() -> dict:
    from .procurement_watch import watch_bids
    bids = watch_bids(days=PROCUREMENT_WINDOW_DAYS)
    if not bids.get("available"):
        raise RuntimeError(bids.get("reason") or "조달 조회 불가")
    return {"bid_count": bids["bid_count"],
            "excluded_count": bids["excluded_count"],
            "categories": sorted({b["category"] for b in bids["bids"]}),
            "notice_nos": [b["notice_no"] for b in bids["bids"]]}


def _fetch_pipeline() -> dict:
    from .countermeasure_pipeline import (
        PATHOGEN_QUERIES, fetch_pipeline, readiness_stage,
    )
    from .countermeasure_stockpile import stockpile_status
    stages, failed = {}, 0
    for name_ko, query in PATHOGEN_QUERIES.items():
        pipeline = fetch_pipeline(query)
        if not pipeline.get("available"):
            failed += 1
        has = bool(stockpile_status(name_ko).get("has_global_stockpile"))
        stages[name_ko] = readiness_stage(pipeline, has)["stage"]
    if failed == len(PATHOGEN_QUERIES):
        raise RuntimeError("모든 병원체 조회 실패")
    return {"stages": stages, "lookup_failed": failed}


# 갱신에 실패한 조각의 사유 앞머리. 로그·경고가 이 낱말로 구분한다.
FAILURE_PREFIX = "갱신 실패"


def stale_parts(snapshot: dict) -> list[tuple[str, dict]]:
    """갱신에 **실패해서** 굳은 조각들. 주기 전이라 안 받은 것은 실패가 아니다.

    ★ 왜 함수로 뺐나 ★ 수집기에서 `part.get("reason", "")` 로 짜다가 터졌다
    (2026-09-03 운영). 키가 **있는데 값이 None** 이면 `.get` 의 기본값은 안
    먹는다. 성공했을 때 reason 이 None 이라 첫 성공 주기에서 바로 AttributeError
    가 났고, 발할라 층 전체가 실패로 기록됐다. 판정을 한 곳에 모으고 시험한다.
    """
    out = []
    for name in ("procurement", "pipeline"):
        part = snapshot.get(name)
        if not isinstance(part, dict):
            continue
        reason = part.get("reason") or ""          # None 도 빈 문자열로 받는다
        if reason.startswith(FAILURE_PREFIX):
            out.append((name, part))
    return out


def valhalla_snapshot(now=None) -> dict:
    """이번 주기의 발할라 상태. 가벼운 건 매번, 무거운 건 주기대로."""
    now = now or _now()
    state = _load_state()
    out = _light_layers()

    out["procurement"] = _refresh_heavy(
        "procurement", PROCUREMENT_EVERY_HOURS, _fetch_procurement, state, now)
    out["pipeline"] = _refresh_heavy(
        "pipeline", PIPELINE_EVERY_HOURS, _fetch_pipeline, state, now)

    _save_state(state)
    out["collected_at"] = now.isoformat()
    # 관찰층이지 경보층이 아니다 — 여기서 경보를 울리지 않는다.
    out["watch_grade"] = True
    return out

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
            # ★ 왜 묵었는지를 같이 들고 간다 ★ 파일이 아예 없는 것과 오래된 것은
            # 다른 상태고 손댈 곳도 다르다. 이걸 버렸더니 수집기가 나이를 대신
            # 찍었고, 파일이 없을 때 age가 None이라 "(None일 전)"으로 나갔다.
            "reasons": {r["name"]: r["reason"] for r in snap["snapshots"] if r["reason"]},
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
    """조달 공고 현황. **제목과 마감일을 버리지 않는다.**

    예전엔 건수·공고번호·분류만 들고 왔다. 그래서 "정부가 지금 무엇을 사려는지
    본다" 는 이 층의 목적이 로그·스냅샷 어디에도 안 남았고, 공고번호만 봐서는
    사람이 아무것도 판단할 수 없었다(파이프라인 층과 같은 '결과를 버린다' 문제).

    마감도 같이 본다 — 이미 닫힌 공고를 열린 것과 같은 숫자로 세면 그 숫자는
    기회의 크기를 말하지 못한다."""
    from .procurement_watch import summarize_bids, watch_bids
    bids = watch_bids(days=PROCUREMENT_WINDOW_DAYS)
    if not bids.get("available"):
        raise RuntimeError(bids.get("reason") or "조달 조회 불가")

    value = {"bid_count": bids["bid_count"],
             "excluded_count": bids["excluded_count"],
             "categories": sorted({b["category"] for b in bids["bids"]}),
             "notice_nos": [b["notice_no"] for b in bids["bids"]],
             "deadline": summarize_bids(bids["bids"]),
             "source": bids.get("source"),
             # 범위를 값에 담는다 — "국가 조달 감시" 라는 이름이 실제 범위를
             # 넘어 읽히지 않게. 소스가 붙으면 여기가 늘어난다.
             "coverage": ["KOR/나라장터"]}

    # ── EU(TED) 추가 (2026-09-04, C-2) ────────────────────────────
    # ★ 소스별로 따로 담는다 ★ 합쳐서 한 숫자로 내면 '31건' 이 어느 나라 것인지
    # 알 수 없고, 한쪽이 죽어도 총계가 줄기만 해서 안 보인다. 그리고 TED 는
    # 아직 실측되지 않은 층이라, 국내 숫자와 섞이면 검증 안 된 값이 검증된
    # 값처럼 읽힌다.
    try:
        from .procurement_ted import watch_ted
        ted = watch_ted(days=PROCUREMENT_WINDOW_DAYS)
        if ted.get("available"):
            value["ted"] = {
                "bid_count": ted["bid_count"],
                "deadline": summarize_bids(ted["bids"]),
                "dropped_unconfirmed": ted["dropped_unconfirmed"],
                "lookup_failures": len(ted["lookup_failures"]),
                "is_verified": ted["is_verified"],
                "unverified_note": ted["unverified_note"],
                # 이 배선은 키를 손으로 골라 옮긴다 — 여기 안 적으면 watch_ted 가
                # 아무리 잘 담아도 요약 줄까지 **영영 안 온다**(2026-09-15 에
                # 실제로 그럴 뻔했다). 버림 수와 확인 범위는 같이 다녀야 한다.
                "description_checked": ted.get("description_checked", True),
            }
            value["coverage"].append("EU/TED(미검증)")
        else:
            # 실패를 '0건'으로 접지 않는다. 사유를 그대로 남긴다.
            value["ted"] = {"available": False, "reason": ted.get("reason"),
                            "is_verified": ted.get("is_verified", False)}
    except Exception as exc:                              # noqa: BLE001
        value["ted"] = {"available": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "is_verified": False}
    return value


def _fetch_pipeline() -> dict:
    """병원체별 대비 단계. **단계 키만 남기지 않는다.**

    예전엔 `stages`(키 문자열)와 실패 수만 들고 왔다. 그래서 24시간마다 17개
    병원체를 조회해놓고 **로그에도 요약에도 아무 값이 안 실렸다** — 돌고는 있는데
    무엇이 나오는지 아무도 모르는 층이었다. 조회 수·한글 단계를 같이 들고 온다.
    """
    from .countermeasure_pipeline import (
        PATHOGEN_QUERIES, fetch_pipeline, readiness_stage,
    )
    from .countermeasure_stockpile import stockpile_status

    stages, stage_ko, study_counts = {}, {}, {}
    failed_pathogens = []
    for name_ko, query in PATHOGEN_QUERIES.items():
        pipeline = fetch_pipeline(query)
        if not pipeline.get("available"):
            # ★ 조회 실패를 '등록 연구 없음'과 섞지 않는다 ★ 전자는 우리가 못 본
            # 것이고 후자는 보고 없다고 확인한 것이다. 준비태세 축에서 '판정불가를
            # 미커버와 섞지 않는다'고 고친 것과 같은 구분이다.
            failed_pathogens.append(name_ko)
        has = bool(stockpile_status(name_ko).get("has_global_stockpile"))
        stage = readiness_stage(pipeline, has)
        stages[name_ko] = stage["stage"]
        stage_ko[name_ko] = stage["stage_ko"]
        study_counts[name_ko] = pipeline.get("study_count")

    if len(failed_pathogens) == len(PATHOGEN_QUERIES):
        raise RuntimeError("모든 병원체 조회 실패")

    counts: dict[str, int] = {}
    for key in stages.values():
        counts[key] = counts.get(key, 0) + 1
    return {
        "stages": stages,
        "stage_ko": stage_ko,
        "study_counts": study_counts,
        "stage_counts": counts,
        "lookup_failed": len(failed_pathogens),
        "failed_pathogens": failed_pathogens,
        # ★ 이 목록의 뜻을 오해하면 안 된다 ★ '등록 연구 없음'은 개발이 없다는
        # 뜻이 아니라 이 등록부에 없다는 뜻이다(군사·기밀 프로그램은 미등재).
        "no_registered_trial": sorted(
            n for n, s in stages.items() if s == "no_registered_trial"),
        "pathogen_count": len(PATHOGEN_QUERIES),
    }


# 로그에 찍을 단계 순서. 시장에서 먼 쪽이 뒤로 가서 눈에 띄게 둔다.
_STAGE_LOG_ORDER = (
    ("stockpiled", "비축"),
    ("approved_path", "후기임상완료"),
    ("late_trial", "후기임상"),
    ("early_trial", "초기임상"),
    ("research_only", "연구단계"),
    ("no_registered_trial", "등록없음"),
    ("unknown", "판정불가"),
)


def pipeline_summary(value: dict | None) -> str | None:
    """파이프라인 값 → 로그 한 줄. 값이 없으면 None(없는 걸 지어내지 않는다).

    ★ '등록없음'과 '판정불가'를 반드시 따로 센다 ★ 앞은 보고 없다고 확인한
    것이고 뒤는 우리가 못 본 것이다. 합치면 "17종 중 3종 미대비"처럼 조회
    실패가 발견으로 둔갑한다."""
    if not value:
        return None

    # ★ 옛 모양 값도 읽는다 ★ 파이프라인은 24시간 주기라, 이 코드를 배포해도
    # 볼륨에 남아 있는 값은 한동안 stage_counts 가 없는 옛 모양이다. 그걸 못
    # 읽으면 **최대 하루, 갱신이 계속 실패하면 영영 로그가 조용하다** — 이 층을
    # 보이게 하려고 만든 함수가 정확히 그 이유로 침묵하는 셈이다(2026-09-04 실측:
    # 배포 후 두 주기 연속 아무 줄도 안 찍혔다). stages 만 있으면 거기서 센다.
    stages = value.get("stages") or {}
    counts = value.get("stage_counts")
    if not counts and stages:
        counts = {}
        for key in stages.values():
            counts[key] = counts.get(key, 0) + 1
    counts = counts or {}

    parts = [f"{label} {counts[key]}종"
             for key, label in _STAGE_LOG_ORDER if counts.get(key)]
    if not parts:
        return None
    line = " · ".join(parts)

    bare = value.get("no_registered_trial")
    if bare is None and stages:
        bare = sorted(n for n, s in stages.items() if s == "no_registered_trial")
    if bare:
        line += f" [등록없음: {'·'.join(bare)}]"
    return line


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


def _readiness_scopes(pipeline_part: dict | None) -> dict:
    """국가 비축 · 국제 비축 · 임상 파이프라인을 나란히. 합친 점수는 내지 않는다."""
    try:
        import db as _db
        from .biodefense_readiness import DEFAULT_THREATS
        from .readiness_scopes import readiness_by_scope

        # 승인 제품은 기준 스냅샷(주간 갱신)에서 읽는다 — 매 주기 openFDA 를
        # 때리지 않는다. 파일이 없으면 approved_scope 가 available=False 로
        # 정직하게 답한다(0%로 내지 않는다).
        approved = None
        try:
            from .reference_snapshots import _load
            approved = _load("approved_products")
        except Exception:                                 # noqa: BLE001
            approved = None

        return readiness_by_scope(
            _db.list_countermeasures(), DEFAULT_THREATS,
            (pipeline_part or {}).get("value"), approved)
    except Exception as exc:                              # noqa: BLE001
        return {"error": type(exc).__name__}


def valhalla_snapshot(now=None) -> dict:
    """이번 주기의 발할라 상태. 가벼운 건 매번, 무거운 건 주기대로."""
    now = now or _now()
    state = _load_state()
    out = _light_layers()

    out["procurement"] = _refresh_heavy(
        "procurement", PROCUREMENT_EVERY_HOURS, _fetch_procurement, state, now)
    out["pipeline"] = _refresh_heavy(
        "pipeline", PIPELINE_EVERY_HOURS, _fetch_pipeline, state, now)

    # ★ 준비태세를 범위별로 ★ 여기서 계산하는 이유: 임상 범위는 위 무거운 조각의
    # 값이 있어야 하고, 그건 _light_layers 시점엔 아직 없다.
    #
    # 점검(2026-09-04)에서 나온 것: 국제 비축(ICG 5종)과 임상 파이프라인(17종)을
    # **이미 매일 받아오면서도** 준비태세 판정에는 한 번도 안 넣고 있었다.
    # compute_readiness 가 db.list_countermeasures()(수기 5건)만 보기 때문이다.
    out["readiness_by_scope"] = _readiness_scopes(out.get("pipeline"))

    _save_state(state)
    out["collected_at"] = now.isoformat()
    # 관찰층이지 경보층이 아니다 — 여기서 경보를 울리지 않는다.
    out["watch_grade"] = True
    return out

"""기준 스냅샷의 나이·갱신 — "파일이 있다"와 "데이터가 최신이다"를 가른다.

## 왜 만들었나 (2026-09-04, 발할라 점검)

발할라 5개 축 중 둘이 정적 파일이다.

    WHO 사전적격성 백신   284건 · snapshot_date 2026-09-02
    WHO IHR 국가 역량     194개국 · snapshot_date 2026-09-02 (원데이터는 2023년)

그런데 코드베이스 전체에 **snapshot_date를 나이로 환산하는 곳이 하나도 없었다.**
갱신 스크립트는 있는데 주간작업이 안 불렀다. 즉 두 파일은 사람이 손으로 돌릴
때만 새로워지고, 몇 달이 지나도 `available: true`로 답한다.

이건 어제 고친 것(`capability_ledger`)과 같은 종류의 거짓말이다 — 그때는 설정을
근거로 능력을 주장했고, 여기서는 파일의 존재를 근거로 신선도를 주장한다.

## ★ 좋은 스냅샷을 나쁜 것으로 덮지 않는다 ★

원본은 우리 것이 아니다. WHO가 HTML 표 구조를 바꾸면 파서가 0건을 뱉는데, 그걸
그대로 쓰면 **멀쩡하던 284건이 사라진다.** 8월 KDCA 쉼표 사고가 정확히 그
모양이었다(파서가 깨지자 나흘치가 통째로 날아갔다).

그래서 쓰기 전에 두 관문을 둔다:
  ① 절대 하한 — 최소 건수에 못 미치면 거부
  ② 상대 하한 — 기존 스냅샷보다 SHRINK_LIMIT 이상 줄면 거부

거부는 조용하지 않다. 능력 장부에 실패로 남아 /api/status 에 드러난다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
# 실행 중에 받은 스냅샷은 볼륨(epiweather-api/data, Railway 볼륨 마운트)에 쓴다 (2026-10-20).
# ★ 왜 ★ 예전엔 저장소 디렉터리(REFERENCE_DIR)에 썼는데, 그곳은 컨테이너 파일이라 **재배포마다 지워졌다.**
# 저장소에 없는 `approved_products.json` 은 10-19 하루에만 배포 네 번마다 '기준 파일이 없다'가 찍히고
# 2~10분 뒤 다시 받았다 — 그 사이 발할라 준비태세 줄에서 승인제품 축이 빠졌다. 저장소에 있는 스냅샷도
# 주간작업이 갱신한 값이 배포 때 커밋된 옛 값으로 되돌아갔다.
# 읽을 때는 볼륨 사본과 저장소 사본 중 snapshot_date 가 늦은 쪽을 쓴다(커밋으로 더 새 값을 넣으면 그쪽이 이긴다).
RUNTIME_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"

# 새 수집이 기존보다 이 비율 밑으로 줄면 파서가 깨진 것으로 보고 거부한다.
SHRINK_LIMIT = 0.8


def _vaccine_count(payload: dict) -> int:
    return len(payload.get("records") or [])


def _ihr_count(payload: dict) -> int:
    return len(payload.get("scores") or {})


def _approved_count(payload: dict) -> int:
    return len(payload.get("by_threat") or {})


def _kor_route_count(payload: dict) -> int:
    return len(payload.get("by_country") or {})


# 스냅샷 등록부. max_age_days는 '원본이 얼마나 자주 바뀌는가'에 맞춘다.
SNAPSHOTS: dict[str, dict] = {
    "vaccine_supply": {
        "label": "WHO 사전적격성 백신",
        "filename": "who_prequalified_vaccines.json",
        # 사전적격성 목록은 수시로 추가된다. 분기보다 짧게 본다.
        "max_age_days": 90,
        "min_records": 100,
        "count": _vaccine_count,
        "fetch": "fetch_vaccine_supply",
        "owner": "VALHALLA",
    },
    "ihr_capacity": {
        "label": "WHO IHR 국가 역량(SPAR)",
        "filename": "ihr_capacity.json",
        # SPAR는 연 1회 보고다. 반년이면 충분하고, 더 짧게 잡으면 안 바뀐 걸
        # 계속 받으러 가느라 낭비만 한다.
        "max_age_days": 180,
        "min_records": 150,
        "count": _ihr_count,
        "fetch": "fetch_ihr_capacity",
        "owner": "VALHALLA",
    },
    "approved_products": {
        "label": "규제 승인 제품(openFDA)",
        "filename": "approved_products.json",
        # 신규 허가는 드물지만, 하나 나면 대비 우선순위가 바뀐다(개발 → 조달).
        "max_age_days": 60,
        # ★ 하한이 낮다 ★ 위협 8종 중 검색 가능한 것이 7종뿐이고(Novel 은 정의상
        # 불가), 일부 조회가 실패해도 나머지는 쓸모가 있다. 대신 급감 관문이
        # 파서 붕괴를 잡는다.
        "min_records": 3,
        "count": _approved_count,
        "fetch": "fetch_approved_products",
        "owner": "VALHALLA",
    },
    "kor_route_stats": {
        "label": "한국 국제선 국가별 운송 실적(공공데이터포털 파일)",
        "filename": "kor_route_stats.json",
        # 원본이 반기(1월 20일 무렵·7월 초) 갱신이다. 첫 스냅샷(10-19, 캡틴이 받아 준 7월 등록본)에서
        # 100일 뒤면 1월 등록 직후라, 그 주의 주간작업이 처음으로 자동 내려받기를 시도한다.
        "max_age_days": 100,
        # 인천 취항국은 수십 개국이다. 이보다 적으면 열·국가 매핑이 깨진 것으로 본다.
        "min_records": 30,
        "count": _kor_route_count,
        "fetch": "fetch_kor_route_stats",
        # 유입 보고서·확산 모델(SKULD)이 쓴다 — 발할라 대응제 축이 아니다. 발할라 로그에 섞이지 않게.
        "owner": "SKULD",
    },
}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _snapshot_date(path: Path) -> str:
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("snapshot_date") or "")
    except Exception:                                   # noqa: BLE001
        return ""


def newest(seed: Path) -> Path:
    """저장소 사본(seed)과 같은 이름의 볼륨 사본 중 snapshot_date 가 늦은 쪽. 같으면 볼륨 쪽.
    둘 다 없으면 seed 를 돌려준다(읽는 쪽이 '없다'를 말한다)."""
    runtime = RUNTIME_DIR / seed.name
    if not runtime.exists():
        return seed
    if not seed.exists():
        return runtime
    return seed if _snapshot_date(seed) > _snapshot_date(runtime) else runtime


def path_for(name: str) -> Path:
    """읽을 파일 — 볼륨 사본과 저장소 사본 중 새것."""
    return newest(REFERENCE_DIR / SNAPSHOTS[name]["filename"])


def write_path_for(name: str) -> Path:
    """갱신을 쓸 파일 — 항상 볼륨. 재배포에 살아남는다."""
    return RUNTIME_DIR / SNAPSHOTS[name]["filename"]


def _load(name: str) -> dict | None:
    try:
        return json.loads(path_for(name).read_text(encoding="utf-8"))
    except Exception:                                   # noqa: BLE001
        return None


def age_days(snapshot_date: str | None, now=None) -> float | None:
    """스냅샷을 뜬 날로부터 며칠. 날짜를 못 읽으면 None — 0으로 두지 않는다."""
    if not snapshot_date:
        return None
    try:
        taken = dt.date.fromisoformat(snapshot_date)
    except (TypeError, ValueError):
        return None
    today = (now or _now()).date()
    return round((today - taken).days, 1)


def snapshot_status(name: str, now=None) -> dict:
    """이 스냅샷이 얼마나 묵었나. **없는 것과 묵은 것을 구분한다.**"""
    cfg = SNAPSHOTS[name]
    payload = _load(name)
    if payload is None:
        return {
            "name": name, "label": cfg["label"], "present": False,
            "snapshot_date": None, "age_days": None,
            "max_age_days": cfg["max_age_days"], "stale": True,
            "record_count": 0,
            "reason": "기준 파일이 없다",
        }

    age = age_days(payload.get("snapshot_date"), now)
    # 날짜를 못 읽으면 신선하다고 우기지 않는다 — 모르면 stale로 본다.
    stale = age is None or age > cfg["max_age_days"]
    return {
        "name": name,
        "label": cfg["label"],
        "present": True,
        "snapshot_date": payload.get("snapshot_date"),
        "age_days": age,
        "max_age_days": cfg["max_age_days"],
        "stale": stale,
        "record_count": cfg["count"](payload),
        "source": payload.get("source"),
        "reason": None if not stale else (
            "snapshot_date를 읽을 수 없다" if age is None
            else f"{age:.0f}일 묵음(기준 {cfg['max_age_days']}일)"),
    }


def report(now=None, owner: str | None = None) -> dict:
    """전 스냅샷의 신선도 — /api/status가 노출.

    stale_snapshots가 비어 있지 않으면 '조용히 굳은 기준 데이터'가 눈에 보이는 것.
    발할라의 백신 공급·국가 역량 축이 여기에 달려 있다. owner 를 주면 그 시스템 몫만
    (발할라 관찰이 유입 보고서용 노선 실적까지 '발할라 스냅샷 묵음'으로 찍지 않게)."""
    rows = [snapshot_status(n, now) for n in sorted(SNAPSHOTS)
            if owner is None or SNAPSHOTS[n].get("owner") == owner]
    return {
        "snapshots": rows,
        "stale_snapshots": [r["name"] for r in rows if r["stale"]],
        "fresh_count": sum(1 for r in rows if not r["stale"]),
        "total_tracked": len(rows),
        "note": (
            "age_days는 스냅샷을 뜬 날로부터의 경과일이지, 원본 데이터가 만들어진 "
            "시점이 아니다. 예: IHR은 오늘 받아도 원데이터는 latest_year(연 1회 보고) "
            "기준이다. 파일이 있다는 것과 데이터가 최신이라는 것은 다른 말이다."
        ),
    }


def stale_lines(refs: dict | None) -> list[str]:
    """묵은 스냅샷마다 로그 한 줄. 발할라가 저장해 둔 조각(reference_snapshots)을
    그대로 받는다.

    ★ 왜 사유를 쓰는가 ★ 예전엔 수집기가 나이만 찍었는데, 파일이 아예 없으면
    age_days가 None이라 운영 로그에 이렇게 나갔다:

        ⚠ 발할라 기준 스냅샷 'approved_products' 묵음 (None일 전)

    '한 번도 안 떠졌다'와 '오래됐다'는 다른 상태고 손댈 곳도 다른데 같은 문장이
    됐다. 사유는 snapshot_status가 이미 만들고 있었고 버려지기만 했다.

    ★ 옛 모양을 견딘다 ★ reasons 키가 없던 시절 값에도 안 터지고, 나이로라도
    말한다 — 못 말하면 '사유 미상'이라고 하지 조용해지지 않는다."""
    refs = refs or {}
    reasons = refs.get("reasons") or {}
    ages = refs.get("ages_days") or {}
    lines = []
    for name in refs.get("stale") or []:
        why = reasons.get(name)
        if not why:
            age = ages.get(name)
            why = (f"{age:.0f}일 묵음" if isinstance(age, (int, float))
                   else "사유 미상(갱신 대기)")
        lines.append(f"기준 스냅샷 '{name}' — {why}")
    return lines


def _write_atomic(target: Path, payload: dict) -> None:
    """같은 디렉터리에 임시로 쓴 뒤 옮긴다. 쓰다 죽어도 기존 파일이 안 깨진다."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        os.replace(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def validate(name: str, payload: dict) -> tuple[bool, str | None]:
    """새 payload를 써도 되는가. (통과, 거부 사유).

    ★ 이 함수가 이 모듈의 요점이다 ★ 원본은 우리 것이 아니라서 언제든 모양이
    바뀐다. 검증 없이 덮으면 파서가 깨진 날 좋은 데이터가 사라진다."""
    cfg = SNAPSHOTS[name]
    count = cfg["count"](payload)
    if count < cfg["min_records"]:
        return False, (f"수집이 너무 적다({count}건 < 하한 {cfg['min_records']}건) "
                       "— 원본 구조가 바뀐 것으로 본다")

    current = _load(name)
    if current:
        before = cfg["count"](current)
        if before and count < before * SHRINK_LIMIT:
            return False, (f"기존({before}건)보다 {count}건으로 급감 "
                           f"— {SHRINK_LIMIT:.0%} 미만이라 덮어쓰지 않는다")
    return True, None


def refresh(name: str, now=None) -> dict:
    """원본에서 새로 받아 검증 후 저장. 실패해도 기존 파일은 그대로 둔다.

    성공·실패를 능력 장부에 남긴다 — 갱신이 매번 조용히 실패하는 상태를
    /api/status에서 볼 수 있게."""
    from . import reference_fetch
    from .capability_ledger import record

    capability = f"snapshot_{name}"
    cfg = SNAPSHOTS[name]
    try:
        payload = getattr(reference_fetch, cfg["fetch"])()
    except Exception as exc:                            # noqa: BLE001
        detail = f"{type(exc).__name__}: {exc}"
        record(capability, ok=False, detail=detail)
        return {"name": name, "refreshed": False, "reason": f"수집 실패 — {detail}"}

    ok, why = validate(name, payload)
    if not ok:
        # 받아오긴 했는데 못 믿을 값이다. 이건 성공이 아니다.
        record(capability, ok=False, detail=why)
        return {"name": name, "refreshed": False, "reason": f"검증 거부 — {why}"}

    try:
        _write_atomic(write_path_for(name), payload)
    except Exception as exc:                            # noqa: BLE001
        detail = f"저장 실패 {type(exc).__name__}: {exc}"
        record(capability, ok=False, detail=detail)
        return {"name": name, "refreshed": False, "reason": detail}

    # 읽기 캐시를 비운다 — 안 비우면 갱신해놓고 옛 값을 계속 본다.
    _clear_consumer_caches(name)
    count = cfg["count"](payload)
    record(capability, ok=True, detail=f"{count}건", endpoint=payload.get("source_url"))
    return {"name": name, "refreshed": True, "record_count": count,
            "snapshot_date": payload.get("snapshot_date"), "reason": None}


# 스냅샷을 읽는 소비자 모듈. 갱신 뒤 이 모듈들의 캐시를 전부 비운다.
CONSUMER_MODULES = {
    "vaccine_supply": "vaccine_supply",
    "ihr_capacity": "ihr_capacity",
}


def _clear_consumer_caches(name: str) -> None:
    """스냅샷을 lru_cache로 들고 있는 소비자의 캐시를 비운다.

    ★ 이걸 빼먹으면 갱신이 무의미해진다 ★ 소비자들은 파일을 lru_cache로 읽는다.
    파일을 새로 써도 같은 프로세스는 옛 값을 계속 보고, 수집기는 재배포 전까지
    안 죽으므로 몇 주가 그대로 갈 수 있다 — 갱신했다고 로그만 찍히고 실제로는
    안 바뀌는, 이 리포가 반복해 겪은 바로 그 모양이다.

    이름을 하나씩 적지 않고 모듈을 훑는다. ihr_capacity에는 _snapshot 말고
    world_medians도 캐시라, 하나만 비우면 **파생값이 옛것으로 남는다.**"""
    module_name = CONSUMER_MODULES.get(name)
    if not module_name:
        return
    try:
        import importlib
        module = importlib.import_module(f".{module_name}", __package__)
        for attr in vars(module).values():
            clear = getattr(attr, "cache_clear", None)
            if callable(clear):
                clear()
    except Exception:                                   # noqa: BLE001
        pass        # 캐시 비우기 실패가 갱신 자체를 실패로 만들진 않는다


def refresh_due(now=None) -> dict:
    """묵은 것만 새로 받는다. 주간작업이 부른다.

    안 묵은 것은 원본을 부르지도 않는다 — 안 바뀐 걸 매주 긁을 이유가 없다."""
    results, skipped = [], []
    for name in sorted(SNAPSHOTS):
        status = snapshot_status(name, now)
        if not status["stale"]:
            skipped.append({"name": name, "age_days": status["age_days"]})
            continue
        results.append(refresh(name, now))
    return {"refreshed": results, "skipped_fresh": skipped}


def refresh_missing(now=None) -> dict:
    """**파일이 아예 없는** 스냅샷만 새로 받는다. 주간 타이머와 무관하게 부른다.

    ★ 왜 필요한가 ★ (2026-10-04 관측)

    `approved_products.json` 은 저장소에 없고 주간작업이 런타임에 만든다. 로그는
    `기준 파일이 없다. 주간작업이 갱신 시도` 를 최소 10-01 16시부터 **매시간** 찍었는데,
    같은 기간 로그에서 갱신 성공·실패 줄은 한 줄도 못 찾았다. 주간작업은 마지막 실행 시각이
    남아 있으면 7일을 기다리고, 파일은 재배포로 사라질 수 있다(저장소 밖에 쓰는 파일) — 이
    둘이 겹치면 '없다'는 경고만 일주일 내내 반복된다(추정 — 확인된 원인이 아니다).

    묵은 것(`refresh_due`)과 없는 것을 가른다: 없는 것은 기다릴 이유가 없다. 안 바뀐 걸
    긁지 않는다는 `refresh_due` 의 원칙은 그대로고, 여기서는 **없는 것만** 부른다.
    """
    results = []
    for name in sorted(SNAPSHOTS):
        if snapshot_status(name, now)["present"]:
            continue
        results.append(refresh(name, now))
    return {"refreshed": results}


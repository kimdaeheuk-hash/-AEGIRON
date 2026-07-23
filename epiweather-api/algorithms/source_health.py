"""소스별 헬스·신선도 추적 — 인수인계서 확장(㉔, "조용한 실패" 제거).

조기경보 시스템에서 가장 위험한 결함은 소스가 죽었는데 시스템이 조용히
넘어가서 "신호 없음 = 안전"으로 오해하는 것(= 놓친 경보의 근본 원인).
기존엔 collector.log_error()가 error_log.txt에 한 줄 남기고 다음 소스로
넘어갈 뿐이라, "어느 소스가 며칠째 죽었는지"가 어디에도 안 보였다.

이 모듈은 매 수집 주기마다 소스별 성공/실패를 구조화해서 남긴다:
  - last_success_at / last_failure_at
  - consecutive_failures (연속 실패 횟수 — 이게 쌓이면 소스가 죽은 것)
  - staleness_hours (마지막 성공 이후 경과 — "얼마나 신선한가"의 정직한 프록시)

★ 정직성 경계선 ★
staleness_hours는 "마지막 성공 수집 이후 경과 시간"이지, "실제 사건 발생
→ DB 반영"까지의 역학적 지연(latency)이 아니다. 진짜 event→ingest 지연은
소스가 자기 데이터에 기준일(data date)을 실어줄 때만 계산 가능한데(KDCA
주간·InfoDengue 등 일부만 해당), 대부분의 무료 소스(WHO item 수·네이버
검색비율)는 기준일이 없어서 계산 불가 — 그래서 보편적으로 측정 가능한
"신선도(staleness)"만 정직하게 제공하고, 이름으로 그 한계를 명시한다.
"""
from __future__ import annotations
import json
import datetime as dt
from pathlib import Path

HEALTH_FILE = Path(__file__).resolve().parent.parent / "data" / "source_health.json"

# 연속 실패가 이 횟수 이상이면 "failing"(죽은 것으로 간주).
FAILING_STREAK = 3
# 마지막 성공이 이 시간(h)을 넘으면 "stale"(신선하지 않음). 무료 소스가
# 1시간 주기 수집이므로 넉넉히 6시간(6회 연속 놓침) 기준.
STALE_HOURS = 6.0


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load_raw() -> dict:
    if not HEALTH_FILE.exists():
        return {}
    try:
        with open(HEALTH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict) -> None:
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_source_result(source: str, ok: bool, error: str | None = None) -> None:
    """소스 1건의 이번 주기 결과를 기록. ok=True면 연속실패 카운터를 리셋."""
    data = _load_raw()
    now = _now().isoformat()
    entry = data.get(source, {
        "last_success_at": None, "last_failure_at": None,
        "consecutive_failures": 0, "total_successes": 0, "total_failures": 0,
        "last_error": None,
    })
    if ok:
        entry["last_success_at"] = now
        entry["consecutive_failures"] = 0
        entry["total_successes"] = entry.get("total_successes", 0) + 1
    else:
        entry["last_failure_at"] = now
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        entry["total_failures"] = entry.get("total_failures", 0) + 1
        if error:
            entry["last_error"] = error[:200]
    data[source] = entry
    _save_raw(data)


def record_cycle(result: dict, source_key_map: dict[str, str]) -> list[str]:
    """한 수집 주기 결과(result dict)를 소스별로 한 번씩 기록.
    source_key_map: {소스이름: result에서 그 소스가 채우는 키}. 값이 None이면
    실패/건너뜀(수집 실패), non-None이면 성공으로 판정 — 주기당 소스별 정확히
    1회만 기록해 연속실패 카운트가 중복 증가하지 않게 한다.

    반환: 이번 주기에 '새로' failing 상태로 넘어간 소스 목록(연속실패가 딱
    FAILING_STREAK에 도달한 것). 매 주기 반복 통보를 막으려고 '경계를 넘는
    순간'만 잡아서, collector가 이때 한 번 Telegram 경보를 낼 수 있게 한다."""
    newly_failing = []
    for source, key in source_key_map.items():
        ok = result.get(key) is not None
        if not ok:
            before = _load_raw().get(source, {}).get("consecutive_failures", 0)
            record_source_result(source, ok=False)
            if before + 1 == FAILING_STREAK:
                newly_failing.append(source)
        else:
            record_source_result(source, ok=True)
    return newly_failing


def _status_for(entry: dict) -> tuple[str, float | None]:
    """(status, staleness_hours) 계산. status = ok | stale | failing | unknown."""
    last_success = entry.get("last_success_at")
    staleness_hours = None
    if last_success:
        try:
            delta = _now() - dt.datetime.fromisoformat(last_success)
            staleness_hours = round(delta.total_seconds() / 3600, 1)
        except ValueError:
            staleness_hours = None

    if entry.get("consecutive_failures", 0) >= FAILING_STREAK:
        return "failing", staleness_hours
    if last_success is None:
        return "unknown", None
    if staleness_hours is not None and staleness_hours > STALE_HOURS:
        return "stale", staleness_hours
    return "ok", staleness_hours


def source_health_report() -> dict:
    """소스별 헬스 요약 — /api/status가 노출. degraded_sources가 비어있지
    않으면 '조용히 죽은 소스'가 실제로 눈에 보이게 되는 것."""
    data = _load_raw()
    sources = []
    degraded = []
    for source, entry in sorted(data.items()):
        status, staleness = _status_for(entry)
        row = {
            "source": source,
            "status": status,
            "staleness_hours": staleness,
            "consecutive_failures": entry.get("consecutive_failures", 0),
            "last_success_at": entry.get("last_success_at"),
            "last_failure_at": entry.get("last_failure_at"),
            "last_error": entry.get("last_error"),
        }
        sources.append(row)
        if status in ("failing", "stale"):
            degraded.append(source)

    return {
        "sources": sources,
        "degraded_sources": degraded,
        "healthy_count": sum(1 for s in sources if s["status"] == "ok"),
        "total_tracked": len(sources),
        "note": "staleness_hours는 마지막 성공 수집 이후 경과시간(신선도)이며, "
                "실제 사건→DB 반영 역학적 지연이 아님(대부분 무료 소스가 기준일을 "
                "제공하지 않아 후자는 측정 불가).",
    }

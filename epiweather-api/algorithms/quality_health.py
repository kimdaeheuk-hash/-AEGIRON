"""품질 헬스 — **소스가 살아있는 것과 값이 온전한 것은 다르다.**

## 왜 이 층이 따로 필요한가

`source_health` 는 "소스가 값을 돌려줬는가"(liveness)를 본다. 그런데 2026-08 한 달의
사고 6건은 **전부 그 검사를 통과하면서** 일어났다:

| 날짜 | 사고 | 그때 소스 헬스 |
|---|---|---|
| 08-13 | KDCA 파싱 버그로 국내 데이터 4일 공백 | 정상 (테스트 660개도 통과) |
| 08-22 | 배포가 스케줄러 틱을 죽여 하루치 누락 | 정상 (에러 0줄) |
| 08-25 | GroqWatch 25시간 실패, 원인 불명 | 값없음만 표시 |
| 08-28 | Mobility 245시간(10.2일) 무응답 | `정상 20/21` |
| 08-28 | 현지어 뉴스 LLM 재분류 29시간+ 꺼짐 | `정상 20/20 · 문제 없음` |
| 08-30 | LLM 재분류 24주기 중 14주기 실패 | `정상 20/21` |

마지막 두 개가 이 모듈의 존재 이유다. `local_news` 는 **정상적으로 값을 돌려준다** —
다만 그 값이 LLM 재분류를 거친 게 아니라 오탐 많은 키워드 매칭 결과일 뿐이다.
소스 헬스가 볼 수 있는 게 아니다. 구조적으로 못 본다.

    소스 헬스 = 값이 왔는가            (liveness)
    품질 헬스 = 그 값을 만든 방식이 온전한가  (integrity)

## 설계 — 불변식(invariant) 레지스트리

사고마다 새 경보를 손으로 붙이면 다음 사고는 또 못 잡는다. 그래서 "매 주기 참이어야
하는 명제" 를 등록하는 자리를 만든다. 각 불변식은:

- 무엇이 참이어야 하는가 (`check`)
- **왜 중요한가** (`why`) — 경보를 받은 사람이 판단할 수 있어야 한다
- 몇 주기 연속 깨지면 울리는가 (`alarm_after`)

`check` 가 `None` 을 돌려주면 **판정 불가**다(그 층이 이번 주기에 아예 안 돌았거나
입력이 없음). 판정 불가를 위반으로 세지 않는다 — 그러면 첫 배포마다 거짓 경보가 난다.

## 왜 연속 주기로 세는가

한 주기 실패는 흔하다(외부 API 순간 장애). 이 시스템을 다치게 한 건 **지속**이었다.
그래서 단발은 기록만 하고, 연속으로 이어질 때 울린다. `source_health.FAILING_STREAK`
와 같은 사고방식이다.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Callable

QUALITY_FILE = Path(__file__).resolve().parent.parent / "data" / "quality_health.json"

# 같은 저하를 다시 알리는 주기(h). source_health 와 같은 값을 쓴다 — 한 번 울리고
# 마는 알림은 스크롤에 묻힌다(2026-08-13 KDCA 가 정확히 그랬다).
RENOTIFY_HOURS = 24.0


class Invariant:
    """매 주기 참이어야 하는 명제 하나."""

    def __init__(self, key: str, label: str, why: str,
                 check: Callable[[dict], bool | None], alarm_after: int = 3):
        self.key = key
        self.label = label
        self.why = why
        self.check = check
        self.alarm_after = alarm_after


# ── 개별 검사 ────────────────────────────────────────────────────────
# 각 함수는 collector 의 result dict 를 받아 True/False/None 을 돌려준다.
# None = 판정 불가(이번 주기에 그 층이 안 돌았거나 입력이 없음).

def _check_llm_reclassify(result: dict) -> bool | None:
    """고경보가 LLM 기준으로 나왔는가(키워드 폴백이 아닌가).

    ★ 08-28·08-30 사고가 이것이다 ★ `high_alert_basis` 는 이미 계산되고 있었는데,
    아무도 그걸 **누적해서** 보지 않았다. 한 주기 로그에는 찍혔지만 "14주기째" 라는
    사실은 사람이 로그를 세어야만 나왔다.
    """
    news = result.get("local_news")
    if not isinstance(news, dict):
        return None
    basis = news.get("high_alert_basis")
    if basis is None:
        return None
    return basis == "llm"


def _check_llm_coverage(result: dict) -> bool | None:
    """LLM 응답이 잘리지 않고 보낸 제목을 전부 답받았는가.

    08-30 수리로 잘려도 부분 분류는 되게 했다. 그건 좋은 일이지만, **부분 성공이
    몇 주씩 이어지는 걸 성공으로만 세면** 커버가 반토막 난 채 도는 걸 아무도 모른다.
    """
    news = result.get("local_news")
    if not isinstance(news, dict):
        return None
    answered, sent = news.get("llm_answered_titles"), news.get("llm_sent_titles")
    if answered is None or not sent:
        return None
    return answered >= sent


def _check_disaster_watch(result: dict) -> bool | None:
    """재난 감시창이 GDACS 를 실제로 받아왔는가.

    이 층이 죽으면 현지어 뉴스 문턱이 **평시로 조용히 돌아간다**(0.08 → 0.15).
    고경보 수는 그럴듯하게 유지되므로 겉으로는 아무 일도 없어 보인다.
    `fetched == 0` 은 '재난이 없다' 가 아니라 파서가 형식과 안 맞는다는 뜻이다.
    """
    watch = result.get("disaster_watch")
    if watch is None:
        return None
    if not isinstance(watch, dict):
        return None
    fetched = watch.get("fetched")
    if fetched is None:
        return None
    return fetched > 0


def _check_local_feed_coverage(result: dict) -> bool | None:
    """현지어 피드가 대부분 살아있는가(90% 이상).

    179개 중 몇 개가 죽는 건 흔하다. 대량으로 죽으면 신호가 통째로 얇아지는데,
    `active_feeds` 가 0 이 아닌 한 소스 헬스는 정상으로 본다.
    """
    news = result.get("local_news")
    if not isinstance(news, dict):
        return None
    total, active = news.get("total_feeds"), news.get("active_feeds")
    if not total or active is None:
        return None
    return active / total >= 0.90


def _check_llm_provider_present(result: dict) -> bool | None:
    """LLM 재분류를 실제로 답해준 제공자가 있었는가.

    Cerebras 가 402(무료 쿼터 소진)로 죽은 뒤 **Groq 하나에 매달려 있다.** 그 하나가
    흔들리면 재분류가 통째로 멈춘다. 단일 의존 자체는 코드로 못 고치지만, 그 상태로
    돌고 있다는 사실은 보여야 한다.
    """
    news = result.get("local_news")
    if not isinstance(news, dict):
        return None
    if news.get("high_alert_basis") is None:
        return None
    return bool(news.get("llm_provider"))


INVARIANTS: list[Invariant] = [
    Invariant(
        "llm_reclassify", "LLM 재분류",
        "고경보가 키워드 기준으로 떨어졌다 — 오탐이 많다. 이 층을 만든 이유가 "
        "'여행경보·보건정책 기사도 병 단어를 쓴다'였다(2026-07-08).",
        _check_llm_reclassify, alarm_after=3,
    ),
    Invariant(
        "llm_coverage", "LLM 응답 커버리지",
        "응답이 잘려 보낸 제목의 일부만 분류됐다. 나머지는 키워드 값이 쓰인다.",
        _check_llm_coverage, alarm_after=6,
    ),
    Invariant(
        "disaster_watch", "재난 감시창",
        "GDACS 수신이 0건이다 — 재난이 없는 게 아니라 파서가 형식과 안 맞는 것이다. "
        "현지어 뉴스 문턱이 평시(0.15)로 조용히 돌아간다.",
        _check_disaster_watch, alarm_after=3,
    ),
    Invariant(
        "local_feeds", "현지어 피드 커버리지",
        "현지어 피드의 10% 이상이 죽었다 — 신호가 얇아지는데 소스 헬스는 정상으로 본다.",
        _check_local_feed_coverage, alarm_after=3,
    ),
    Invariant(
        "llm_provider", "LLM 제공자",
        "재분류에 답해준 제공자가 없다. Cerebras 402 이후 Groq 단일 의존 상태다.",
        _check_llm_provider_present, alarm_after=3,
    ),
]


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load_raw() -> dict:
    if not QUALITY_FILE.exists():
        return {}
    try:
        with open(QUALITY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict) -> None:
    QUALITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def record_cycle(result: dict) -> dict:
    """이번 주기의 불변식들을 평가하고 상태를 갱신한다. 반환: {key: entry}.

    판정 불가(None)는 연속 카운터를 **건드리지 않는다** — 위반도 회복도 아니다.
    그렇게 안 하면 그 층이 잠깐 안 돈 주기에 회복으로 오인돼 경보가 리셋된다.
    """
    data = _load_raw()
    now_iso = _now().isoformat()

    for inv in INVARIANTS:
        try:
            ok = inv.check(result)
        except Exception:
            # 검사 자체가 터지는 건 위반이 아니라 판정 불가로 본다 — 검사기의
            # 버그로 진짜 경보를 만들어내면 경보 전체를 못 믿게 된다.
            ok = None

        entry = data.get(inv.key) or {}
        entry["label"] = inv.label
        entry["last_checked_at"] = now_iso

        if ok is None:
            entry["last_result"] = "unknown"
        elif ok:
            entry["last_result"] = "ok"
            entry["consecutive_violations"] = 0
            entry["first_violated_at"] = None
            entry["last_ok_at"] = now_iso
        else:
            entry["last_result"] = "violated"
            entry["consecutive_violations"] = int(entry.get("consecutive_violations") or 0) + 1
            if not entry.get("first_violated_at"):
                entry["first_violated_at"] = now_iso
        data[inv.key] = entry

    _save_raw(data)
    return data


def _degraded_keys(data: dict) -> list[str]:
    out = []
    for inv in INVARIANTS:
        entry = data.get(inv.key) or {}
        if int(entry.get("consecutive_violations") or 0) >= inv.alarm_after:
            out.append(inv.key)
    return out


def quality_report() -> dict:
    """/api/status 에 실을 품질 상태.

    `degraded` 가 비어 있어도 `violating` 은 볼 가치가 있다 — 아직 문턱에 못 미친
    저하가 쌓이는 중일 수 있고, 그게 사고가 되기 전의 모습이다.
    """
    data = _load_raw()
    invariants = []
    for inv in INVARIANTS:
        entry = data.get(inv.key) or {}
        streak = int(entry.get("consecutive_violations") or 0)
        first = _parse_iso(entry.get("first_violated_at"))
        invariants.append({
            "key": inv.key,
            "label": inv.label,
            "last_result": entry.get("last_result", "unknown"),
            "consecutive_violations": streak,
            "alarm_after": inv.alarm_after,
            "alarming": streak >= inv.alarm_after,
            "first_violated_at": entry.get("first_violated_at"),
            "violated_hours": (
                round((_now() - first).total_seconds() / 3600, 1) if first else None
            ),
            "why": inv.why,
        })
    degraded = [i for i in invariants if i["alarming"]]
    return {
        "invariants": invariants,
        "degraded_count": len(degraded),
        "degraded": [i["key"] for i in degraded],
        "healthy_count": sum(1 for i in invariants if i["last_result"] == "ok"),
        "total_invariants": len(invariants),
        # 판정 불가를 정상으로 세지 않는다 — '모른다'와 '괜찮다'는 다르다.
        "unknown_count": sum(1 for i in invariants if i["last_result"] == "unknown"),
    }


def summary_line() -> str:
    """수집 로그 한 줄. 소스 건강 줄과 나란히 찍힌다."""
    report = quality_report()
    if report["degraded"]:
        parts = []
        for item in report["invariants"]:
            if not item["alarming"]:
                continue
            hours = item["violated_hours"]
            span = f"{item['consecutive_violations']}주기째"
            if hours is not None:
                span += f"/{hours:.0f}시간"
            parts.append(f"{item['label']} {span}")
        return "⚠️ 품질 저하: " + " · ".join(parts)
    unknown = report["unknown_count"]
    tail = f" · 판정불가 {unknown}" if unknown else ""
    return f"🔎 품질 불변식: 정상 {report['healthy_count']}/{report['total_invariants']}{tail}"


def pending_notifications() -> dict:
    """지금 사람에게 알려야 할 품질 저하 — source_health 와 같은 모양·같은 스로틀."""
    data = _load_raw()
    now = _now()
    degraded, recovered = [], []
    for inv in INVARIANTS:
        entry = data.get(inv.key)
        if entry is None:
            continue
        streak = int(entry.get("consecutive_violations") or 0)
        notified = entry.get("notified_state")
        if streak >= inv.alarm_after:
            last_notified = _parse_iso(entry.get("last_notified_at"))
            due = (
                notified != "degraded"
                or last_notified is None
                or (now - last_notified).total_seconds() / 3600 >= RENOTIFY_HOURS
            )
            if due:
                first = _parse_iso(entry.get("first_violated_at"))
                degraded.append({
                    "key": inv.key,
                    "label": inv.label,
                    "why": inv.why,
                    "consecutive_violations": streak,
                    "violated_hours": (
                        round((now - first).total_seconds() / 3600, 1) if first else None
                    ),
                })
        elif entry.get("last_result") == "ok" and notified == "degraded":
            recovered.append(inv.label)
    return {"degraded": degraded, "recovered": recovered}


def mark_notified(keys: list[str]) -> None:
    """통보 **성공 후에만** 호출할 것. 전송 실패에 도장을 찍으면 알림을 잃는다."""
    if not keys:
        return
    data = _load_raw()
    now_iso = _now().isoformat()
    for inv in INVARIANTS:
        if inv.key not in keys and inv.label not in keys:
            continue
        entry = data.get(inv.key)
        if entry is None:
            continue
        streak = int(entry.get("consecutive_violations") or 0)
        entry["notified_state"] = "degraded" if streak >= inv.alarm_after else "ok"
        entry["last_notified_at"] = now_iso
    _save_raw(data)

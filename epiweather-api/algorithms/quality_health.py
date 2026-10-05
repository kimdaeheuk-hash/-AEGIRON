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
| 09-05 | NLP 구조화 추출 나흘 내리 0건 | `정상 23/23` · **품질도 `5/5`** |

마지막 줄은 이 모듈이 만들어진 뒤에 난 사고다. 다섯 불변식이 전부
`local_news`·`disaster_watch` 만 보고 있어서 **추출층은 이 그물에도 없었다** —
새 그물을 쳐도 그물이 안 닿는 자리는 남는다는 뜻이라, 불변식을 늘릴 때 "이 층은
누가 보나"를 먼저 묻는다(2026-09-06 에 여섯 번째로 추가).

08-28·08-30 두 개가 이 모듈의 존재 이유다. `local_news` 는 **정상적으로 값을 돌려준다** —
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
                 check: Callable[[dict], bool | None], alarm_after: int = 3,
                 detail: Callable[[], str | None] | None = None):
        self.key = key
        self.label = label
        self.why = why
        self.check = check
        self.alarm_after = alarm_after
        # ★ 왜 이게 필요한가 ★ 경보 줄의 'N주기째/M시간'은 **연속 위반이 시작된
        # 시점**부터 잰다. 매 주기 도는 층에서는 그게 곧 경과지만, 하루 1회 도는
        # 층에서는 아니다 — 나흘째 죽은 추출층이 문턱을 넘은 직후엔 '3주기째/0시간'
        # 으로 찍힌다. 32배를 축소해서 말하는 셈이라, 이 리포가 반복해서 데인
        # 모양(값 하나가 사고를 작아 보이게 하는 것)이 경보 자리에서 되풀이된다.
        # detail 은 그 불변식만 아는 진짜 숫자를 경보에 실어 보내는 통로다.
        self.detail = detail


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


# ── 추출층 — 하루 한 번 도는 층을 매 주기 그물로 재는 법 ──────────────
#
# ★ 2026-09-06 점검에서 드러난 빈칸 ★
# NLP 구조화 추출이 09-02~09-05 **나흘 내리 0건 저장**이었는데, 그동안 소스
# 건강은 `정상 23/23`, 품질 불변식은 `정상 5/5` 였다. **두 그물을 다 통과했다** —
# 위 다섯 불변식이 전부 `local_news`·`disaster_watch` 만 보고 있어서 추출층은
# 애초에 아무도 안 보는 자리였다. 09-05 21:01 운영 로그가 이유까지 말해줬다:
#
#     NLP 구조화 추출: 0건 저장 · 추출실패 5 · 경로별:
#       nvidia_nim_hosted: HTTPError 410×5 · external_llm_fallback: BadRequestError 400×5
#
# 추출이 멎으면 `설명불가 신호 감시` 도 같이 멎는다 — 같은 게이트를 쓴다.
# 이 모듈을 만든 이유(8/28·8/30)와 정확히 같은 모양이 한 층 옆에서 반복됐다.
#
# ★ 왜 재는 방식이 다른가 ★
# 나머지 다섯은 매 주기 도는 층이라 그 주기의 result dict 만 보면 판정이 끝난다.
# 추출층은 **AI 갭필링 슬롯(UTC 21시)에서 하루 한 번**만 돌아 무료 주기의
# result 에는 아예 안 들어온다. 그대로 끼우면 둘 중 하나가 된다:
#
#   - 매 주기 판정불가 → 24주기 중 23주기가 판정불가라 그 표시가 무의미해진다
#   - 매 주기 위반    → 하루치 실패가 '24주기째'로 부풀려진다
#
# 그래서 슬롯이 결과를 남기고(record_extraction_outcome), 불변식은 그 값의
# **신선도**를 본다. source_health 의 staleness 와 같은 사고방식이다.
EXTRACTION_STATE_KEY = "_extraction_layer"

# 마지막 성공이 이 시간을 넘으면 위반. 슬롯이 하루 1회라 48시간은 '이틀 연속
# 빈손'을 뜻한다. 하루치 실패로는 울리지 않는다 — 단발은 흔하고, 이 시스템을
# 다치게 한 건 언제나 지속이었다.
EXTRACTION_STALE_HOURS = 48.0


def record_extraction_outcome(out: dict | None, available: bool = True) -> dict:
    """AI 갭필링 슬롯의 추출 결과를 남긴다. 수집기가 하루 한 번 부른다.

    ★ 세 상태를 뭉개지 않는다 ★

        저장 1건 이상        → 성공.  last_success_at 갱신
        시도했는데 전부 실패  → 실패.  last_attempt_at 만 갱신
        시도할 게 없었다      → 둘 다 안 건드린다(중복 건너뜀만 있던 날)

    마지막 경우를 실패로 세면 '오늘은 새 기사가 없었다' 가 고장으로 둔갑하고,
    성공으로 세면 죽은 층이 살아있는 걸로 둔갑한다. #30 의 'TED 열림 0건' 이
    정확히 이 모양이었다 — 값 하나가 서로 다른 두 상태를 감췄다.

    `available=False` 는 추출 백엔드가 아예 설정되지 않은 갈래다(수집기의
    '⏭ 추출 백엔드 없음'). 실패가 아니라 **안 돌린 것**이라 판정불가로 남긴다 —
    capability_ledger 가 not_configured 와 observed_failure 를 가르는 것과 같은
    이유다. 숨는 건 아니다: 판정불가는 summary_line 에 숫자로 찍힌다.

    ★ blocked(주권차단)는 시도로 세지 않는다 ★ 운영자가 고른 정책이지 고장이
    아니다. 다만 상태에는 남겨서 '왜 아무것도 안 나왔나' 를 짚을 수 있게 한다.
    """
    data = _load_raw()
    state = data.get(EXTRACTION_STATE_KEY)
    if not isinstance(state, dict):
        state = {}
    now_iso = _now().isoformat()

    state["last_checked_at"] = now_iso
    state["backend_available"] = bool(available)

    if not available:
        state["last_outcome"] = "no_backend"
        data[EXTRACTION_STATE_KEY] = state
        _save_raw(data)
        return state

    out = out or {}
    saved = len(out.get("records") or [])
    failed = int(out.get("failed") or 0)
    state["last_saved"] = saved
    state["last_failed"] = failed
    state["last_blocked"] = int(out.get("blocked") or 0)
    # 실패 사유를 그대로 들고 간다 — 경보를 받은 사람이 로그를 뒤지지 않아도
    # 어느 경로가 왜 죽었는지 /api/status 에서 바로 읽힌다. #27 이 애써 살려낸
    # 계측을 여기서 다시 버리면 '몇 번'만 남고 '왜'가 또 사라진다.
    state["last_failure_reasons"] = dict(out.get("failure_reasons") or {})

    if saved + failed == 0:
        state["last_outcome"] = "no_attempt"
    elif saved > 0:
        state["last_outcome"] = "ok"
        state["last_success_at"] = now_iso
        state["last_attempt_at"] = now_iso
        state.setdefault("first_attempt_at", now_iso)
    else:
        state["last_outcome"] = "failed"
        state["last_attempt_at"] = now_iso
        state.setdefault("first_attempt_at", now_iso)

    data[EXTRACTION_STATE_KEY] = state
    _save_raw(data)
    return state


def _check_extraction_layer(result: dict) -> bool | None:
    """추출층이 최근에 실제로 결과를 냈는가.

    `result` 를 안 쓴다 — 이 층은 무료 주기에 돌지 않기 때문이다. 슬롯이 남긴
    상태의 신선도를 본다(위 EXTRACTION_STATE_KEY 주석).

    ★ 두 가지 고장을 같은 그물로 잡는다 ★
      (a) 슬롯은 도는데 전부 실패한다      ← 2026-09-05 의 모양
      (b) 슬롯 자체가 안 돈다              ← 2026-08-22 사고 ②의 모양
    (b)를 판정불가로 빼면 '안 도는 층' 이 영영 안 울린다. Mobility 190시간과
    GroqWatch 간헐이 정확히 그 함정이었다 — 값이 안 오는 게 경보를 막아줬다.
    """
    state = _load_raw().get(EXTRACTION_STATE_KEY)
    if not isinstance(state, dict):
        return None                       # 한 번도 안 돌았다(첫 배포·빈 볼륨)
    if not state.get("backend_available", True):
        return None                       # 설정이 없어 안 돌린 것 — 고장이 아니다

    now = _now()
    last_success = _parse_iso(state.get("last_success_at"))
    if last_success is not None:
        return (now - last_success).total_seconds() / 3600 < EXTRACTION_STALE_HOURS

    # 여기부터는 '성공한 적이 한 번도 없다'.
    first_attempt = _parse_iso(state.get("first_attempt_at"))
    if first_attempt is None:
        return None                       # 시도 자체가 아직 없었다
    if (now - first_attempt).total_seconds() / 3600 < EXTRACTION_STALE_HOURS:
        # ★ 여기서 True 를 돌려주면 안 된다 ★ 아직 판정할 만큼 지켜보지 않은
        # 것이지 온전한 게 아니다. 배포 직후 한 번 실패했다고 울리는 거짓 경보와,
        # 한 번도 성공 못 한 층을 정상으로 세는 것 사이에서 판정을 미룬다.
        return None
    return False


def _extraction_detail_line() -> str | None:
    """추출층 경보에 붙는 진짜 숫자 — '3주기째/0시간' 뒤에 오는 말.

    (INVARIANTS 가 이 이름을 module 레벨에서 참조하므로 레지스트리보다 위에 둔다.)
    """
    detail = _extraction_detail(_load_raw())
    if not detail:
        return None
    if detail["success_age_hours"] is not None:
        head = f"마지막 성공 {detail['success_age_hours']:.0f}시간 전"
    elif detail["attempt_age_hours"] is not None:
        head = "성공 기록 없음"
    else:
        return None
    reasons = detail.get("last_failure_reasons") or {}
    if reasons:
        # 사유가 여럿이면 앞의 둘만. 경로가 갈렸다는 사실이 중요하지 전부 나열할
        # 필요는 없다 — 전체는 /api/status 에 있다.
        top = ", ".join(f"{k}×{v}" for k, v in list(reasons.items())[:2])
        return f"{head} · {top}"
    return head


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
    Invariant(
        "extraction", "구조화 추출",
        "AI 슬롯의 NLP 구조화 추출이 48시간 넘게 한 건도 저장하지 못했다 — "
        "extracted_signals 가 비고 '설명불가 신호 감시'도 같은 게이트라 함께 멎는다. "
        "연속 주기 수는 무료 주기 기준이라 실제 경과가 아니다. 마지막 성공 시각과 "
        "실패 경로별 사유는 /api/status 의 quality_health.extraction 에 있다.",
        _check_extraction_layer, alarm_after=3, detail=_extraction_detail_line,
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


def _safe_detail(inv: Invariant) -> str | None:
    if inv.detail is None:
        return None
    try:
        return inv.detail()
    except Exception:                                     # noqa: BLE001
        return None


def _degraded_keys(data: dict) -> list[str]:
    out = []
    for inv in INVARIANTS:
        entry = data.get(inv.key) or {}
        if int(entry.get("consecutive_violations") or 0) >= inv.alarm_after:
            out.append(inv.key)
    return out


def _extraction_detail(data: dict) -> dict | None:
    """추출층 원자료 — 경보의 '며칠째'가 여기서 나온다.

    ★ 왜 따로 싣는가 ★ 불변식의 `consecutive_violations` 는 **무료 주기** 수다.
    하루 1회 도는 이 층에서는 그 숫자가 '몇 시간째 빈손인가' 를 말해주지 못한다 —
    나흘째 죽은 층이 문턱을 넘은 직후엔 '3주기째/3시간' 으로 보인다. 그 숫자만
    떼어 읽으면 사고가 작아 보이므로 진짜 시각을 나란히 둔다.
    """
    state = data.get(EXTRACTION_STATE_KEY)
    if not isinstance(state, dict):
        return None

    now = _now()

    def _age(key: str) -> float | None:
        parsed = _parse_iso(state.get(key))
        return round((now - parsed).total_seconds() / 3600, 1) if parsed else None

    return {
        "last_outcome": state.get("last_outcome"),
        "backend_available": state.get("backend_available", True),
        "last_saved": state.get("last_saved"),
        "last_failed": state.get("last_failed"),
        "last_blocked": state.get("last_blocked"),
        # 어느 경로가 왜 죽었는지. 비어 있으면 실패가 없었다는 뜻이다.
        "last_failure_reasons": state.get("last_failure_reasons") or {},
        "last_success_at": state.get("last_success_at"),
        "success_age_hours": _age("last_success_at"),
        "last_attempt_at": state.get("last_attempt_at"),
        "attempt_age_hours": _age("last_attempt_at"),
        "stale_after_hours": EXTRACTION_STALE_HOURS,
    }


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
            # detail 이 터져도 보고 전체가 죽으면 안 된다 — 부가 정보 하나 때문에
            # 상태 응답을 잃는 건 남는 장사가 아니다.
            "detail": _safe_detail(inv),
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
        # 위반 중이지만 아직 문턱(alarm_after)에 못 닿은 층. 정상도 판정불가도 아니고
        # 경보도 아니라서, 이 숫자가 없으면 정상+판정불가+경보 가 총계에 못 미친다.
        "pre_alarm_count": sum(1 for i in invariants
                               if i["last_result"] == "violated" and not i["alarming"]),
        # 추출층은 하루 1회라 주기 수로는 경과를 못 읽는다(_extraction_detail 참고).
        "extraction": _extraction_detail(data),
    }


def _span_text(item: dict) -> str:
    span = f"{item['consecutive_violations']}주기째"
    hours = item["violated_hours"]
    if hours is not None:
        span += f"/{hours:.0f}시간"
    return span


def _pre_alarm_items(report: dict) -> list[dict]:
    return [i for i in report["invariants"]
            if i["last_result"] == "violated" and not i["alarming"]]


def summary_line() -> str:
    """수집 로그 한 줄. 소스 건강 줄과 나란히 찍힌다."""
    report = quality_report()
    pre_alarm = _pre_alarm_items(report)
    if report["degraded"]:
        parts = []
        for item in report["invariants"]:
            if not item["alarming"]:
                continue
            piece = f"{item['label']} {_span_text(item)}"
            # 그 층만 아는 진짜 숫자가 있으면 같이 싣는다(Invariant.detail 주석).
            if item.get("detail"):
                piece += f"({item['detail']})"
            parts.append(piece)
        # ★ 저하 중에도 나머지 층의 상태를 말한다 (2026-09-15) ★
        # 예전엔 두 갈래가 배타적이라, 위반이 하나라도 있으면 `정상 n/6` 줄이
        # **아예 안 찍혔다.** 그래서 09-13·09-15 점검이 "구조화 추출 하나가
        # 위반인 건 알겠는데, 나머지 다섯 중 판정불가가 있는지는 알 수 없다"로
        # 끝났다 — 이 층을 만든 이유가 "판정 불가를 정상으로 세지 않는다"인데,
        # 정작 저하 중에는 그 숫자가 보이지 않았다.
        # 위반이 있을 때야말로 다른 층이 조용히 사라졌는지가 중요하다.
        line = f"⚠️ 품질 저하: {' · '.join(parts)}"
        if pre_alarm:
            line += " · 경보 전 위반: " + " · ".join(
                f"{i['label']} {_span_text(i)}" for i in pre_alarm)
        return f"{line} · 나머지 {_healthy_tail(report)}"
    if pre_alarm:
        # ★ 경보 전 위반을 '정상' 줄에 묻지 않는다 (2026-10-05) ★
        # 10-04 11·12시 UTC 의 `정상 2/6 · 판정불가 1` 은 6층 중 3층이 줄에
        # 없었다. 현지어 뉴스 503 블록이 매일 정확히 2주기라 alarm_after(3)에
        # 영영 못 닿았고, 위반 층은 정상·판정불가·저하 어느 쪽에도 안 세어졌다.
        return ("⚠️ 품질 주의(경보 전): "
                + " · ".join(f"{i['label']} {_span_text(i)}" for i in pre_alarm)
                + f" · {_healthy_tail(report)}")
    # _healthy_tail 이 이미 '정상' 으로 시작한다(예전엔 '정상 정상 6/6' 으로 찍혔다).
    return f"🔎 품질 불변식: {_healthy_tail(report)}"


def _healthy_tail(report: dict) -> str:
    """"정상 4/6 · 판정불가 1 · 경보 전 위반 1" — 두 갈래가 같은 셈법을 쓰게 한 곳에 둔다.

    정상 + 판정불가 + 경보 전 위반 (+ 저하로 이름이 따로 찍힌 층) == 총계.
    """
    tail = f" · 판정불가 {report['unknown_count']}" if report["unknown_count"] else ""
    if report["pre_alarm_count"]:
        tail += f" · 경보 전 위반 {report['pre_alarm_count']}"
    return f"정상 {report['healthy_count']}/{report['total_invariants']}{tail}"


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
                    "detail": _safe_detail(inv),
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

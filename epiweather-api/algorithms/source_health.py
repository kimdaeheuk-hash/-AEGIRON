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
# 아직 죽어있는 소스를 다시 알리는 주기(h). 한 번 울리고 마는 알림은 스크롤에
# 묻혀 사라진다 — 2026-08-13 KDCA 장애 때 실제로 3회째에 딱 한 번 울리고
# 그 뒤 90회 실패는 완전히 침묵해서, 나흘간 국내 데이터 공백을 아무도 몰랐다.
RENOTIFY_HOURS = 24.0

# 값없음(no_data)이 이만큼 이어지면 "아는 조건"이 아니라 **그냥 죽은 것**으로 본다.
# no_data 는 원래 경보에서 뺐다 — 위키 404 지연·OpenSky 차단처럼 정상이거나
# 이미 아는 조건이 대부분이라 매일 울리면 경보 피로만 쌓이기 때문이다.
# 그런데 그 예외가 구멍이 됐다. 2026-08-25 실측: **Mobility 가 190시간(8일)째
# 값이 없는데 degraded_sources 는 비어 있었고, healthy_count 는 no_data 를 아예
# 세지 않아 "정상 20/21" 로 보였다.** 조용히 죽으면 영영 안 보이는 상태였다.
# → 사흘이 넘으면 그건 지연이 아니다. 그때는 울린다.
NO_DATA_ALARM_HOURS = 72.0

# ── 간헐적으로만 성공하는 소스 (2026-08-30) ──────────────────────────
# ★ 위의 두 장치를 **동시에** 빠져나가는 구멍이 있었다 ★
#
# `no_data` 는 연속실패 카운터를 리셋하고(정상 동작 — 함수는 멀쩡히 돌았으니까),
# `long_no_data` 경보는 마지막 성공이 72시간을 넘어야 울린다. 그래서 **가끔 한 번씩
# 성공하는 소스**는 두 그물을 다 통과한다:
#
#   - 성공할 때마다 last_success_at 이 갱신돼 staleness 가 72시간에 영영 못 닿고
#   - no_data 라 consecutive_failures 는 계속 0 이고
#   - healthy_count 는 no_data 를 아예 안 세므로 `정상 20/21` 로 보인다
#
# 실측(2026-08-30, GroqWatch): 14주기 중 성공 1회(7%) — 12주기가
# SearchContextTooLarge 였는데 **경보가 하나도 울리지 않았다.** 8/29 도 22주기 중
# 20주기 값없음(9%)이었다. 사실상 죽은 소스가 몇 주째 정상으로 집계된 것이다.
#
# 연속 카운팅으로는 이 모양을 잡을 수 없다. 그래서 **최근 N주기의 성공률**을 본다.
FLAKY_WINDOW = 24          # 시간당 1주기 → 하루치
FLAKY_SUCCESS_RATE = 0.5   # 하루의 절반도 성공 못 하면 그건 살아있는 게 아니다
# 창이 다 차기 전에는 판정하지 않는다 — 배포 직후 몇 주기로 울리면 거짓 경보가 된다.

# ── 추적에서 정식으로 제외한 소스 ──────────────────────────────────
# {소스이름: 뺀 이유}. 여기 있는 소스는 record_cycle 이 기록하지 않고, 리포트의
# 집계(healthy_count·total_tracked)와 경보에서 빠진다.
#
# ★ 숨기는 게 아니다 ★ `retired_sources` 로 이유와 함께 /api/status 에 그대로
# 실린다. 이 시스템에서 가장 위험한 건 "조용히 사라진 것" 이므로, 뺀 것은 뺐다고
# 보이게 둔다. 되살리려면 아래에서 한 줄을 지우면 된다 — 코드는 그대로 있다.
#
# ⚠️ 왜 이 장치가 필요한가(안 만들고 그냥 지웠을 때의 함정):
# total_tracked 는 FREE_SOURCE_HEALTH_KEYS 가 아니라 **source_health.json 파일의
# 항목 수**다(`len(sources)`). 그 파일은 Railway 볼륨에 있어 배포해도 남는다.
# 그래서 수집 맵에서 이름만 지우면 record_cycle 이 갱신을 멈추고 **last_success_at
# 이 영원히 멈춘 채 staleness_hours 만 계속 증가한다** → long_no_data 경보가
# 영영 울리는데 회복될 수조차 없다. 지금보다 나빠진다.
RETIRED_SOURCES: dict[str, str] = {
    "GroqWatch": (
        "2026-09-01 — NewsWatch 로 교대. 최근 24주기 성공률 0.0%, 마지막 성공은 "
        "2026-08-30 03:00 이었다. 원인은 2026-08-28 에 규명됐고 우리 손 밖이다: "
        "프롬프트 3,831~4,993 토큰 중 우리 지시문은 150 남짓이고 나머지 96% 는 "
        "compound-mini 가 서버 쪽에서 붙이는 검색결과라, 질의 축소·재시도·주기 "
        "조정이 전부 실패했다(주입량이 통제 밖). "
        "★ 게다가 죽은 채로 살아있는 소스의 예산을 먹고 있었다 ★ NewsWatch 가 "
        "같은 GROQ_API_KEY 로 도는데(Cerebras 쿼터 소진), GroqWatch 가 매시간 "
        "4,000 토큰씩 분당 한도 8,000 에서 태우고 실패했다. 그래서 추적에서 빼는 "
        "데 그치지 않고 호출 자체를 막는다(collector 가 is_retired 를 본다). "
        "대체한 NewsWatch 는 같은 기간 16주기 연속 성공, 토큰 1,031~1,766 이고 "
        "무엇보다 검색과 요약을 분리해 **주입량을 우리가 통제한다**. "
        "되살리려면 이 줄을 지워라 — 코드는 그대로 있고 /api/groq-watch 도 산다."
    ),
    "Mobility": (
        "2026-08-28 — Railway(SFO)에서 OpenSky 로 TCP 연결이 성립하지 않는다. "
        "연결 타임아웃을 3초→10초로 올려도 동일하게 ConnectTimeout 이 났다"
        "(auth.opensky-network.org:443). 403 이 아니라 무응답이므로 정책적 "
        "IP 차단이 아니라 경로/방화벽 문제이고, 우리 쪽에서 고칠 수 없다. "
        "2026-08-17부터 257시간(10.7일) 무응답. 되살리려면 서비스 리전을 "
        "옮기거나 Railway 아웃바운드가 뚫린 뒤 이 줄을 지워라. "
        "확인 방법은 /api/mobility 를 직접 부르는 것 — 엔드포인트는 살려뒀다."
    ),
}


def is_retired(source: str) -> bool:
    return source in RETIRED_SOURCES


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


def record_source_result(source: str, ok: bool, error: str | None = None,
                         no_data: bool = False) -> None:
    """소스 1건의 이번 주기 결과를 기록. ok=True면 연속실패 카운터를 리셋.

    no_data=True는 '수집은 정상인데 이번 주기에 쓸 값이 없다'는 제3의 상태다.
    실패로 세지 않는다(연속실패도 리셋한다) — 함수가 멀쩡히 돈 건 소스가 안 깨졌다는
    증거이기 때문이다. 그렇다고 성공으로도 세지 않는다. 값이 안 왔으니까.

    이 상태가 왜 필요한가: 위키미디어 페이지뷰는 전날치가 다음날 정오쯤 올라와서
    그 전 404는 '정상 지연'이다. collector는 그걸 알고 에러 기록조차 안 하는데,
    여기서 None을 무조건 실패로 세는 바람에 성공 90 대 실패 139로 집계돼 상시
    degraded에 앉아 있었다. 정상인 걸 계속 경보로 울리면 사람이 경보를 무시하게 되고,
    그러면 진짜 사고를 놓친다.
    """
    data = _load_raw()
    now = _now().isoformat()
    entry = data.get(source, {
        "last_success_at": None, "last_failure_at": None,
        "consecutive_failures": 0, "total_successes": 0, "total_failures": 0,
        "last_error": None,
    })
    if no_data:
        entry["last_no_data_at"] = now
        entry["last_outcome"] = "no_data"
        entry["consecutive_failures"] = 0
        entry["total_no_data"] = entry.get("total_no_data", 0) + 1
    elif ok:
        entry["last_success_at"] = now
        entry["last_outcome"] = "ok"
        entry["consecutive_failures"] = 0
        entry["total_successes"] = entry.get("total_successes", 0) + 1
    else:
        entry["last_failure_at"] = now
        entry["last_outcome"] = "fail"
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        entry["total_failures"] = entry.get("total_failures", 0) + 1
        if error:
            entry["last_error"] = error[:200]

    # 최근 결과를 창 크기만큼만 들고 다닌다 — 누적 총계(total_*)로는 "지금
    # 살아있나"를 알 수 없다. 한 달 전에 잘 돌던 이력이 오늘의 고장을 가린다.
    recent = list(entry.get("recent_outcomes") or [])
    recent.append(entry["last_outcome"])
    entry["recent_outcomes"] = recent[-FLAKY_WINDOW:]

    data[source] = entry
    _save_raw(data)


def _recent_success_rate(entry: dict) -> tuple[float | None, int]:
    """(최근 성공률, 표본 수). 창이 다 안 찼으면 성공률은 None."""
    recent = entry.get("recent_outcomes") or []
    if len(recent) < FLAKY_WINDOW:
        return None, len(recent)
    ok = sum(1 for outcome in recent if outcome == "ok")
    return ok / len(recent), len(recent)


def is_flaky(entry: dict) -> bool:
    """가끔만 성공하는 소스인가 — 연속 카운팅이 못 잡는 모양.

    `no_data` 와 `ok` 를 오가며 두 그물을 다 빠져나가는 소스를 잡는다.
    창이 다 차기 전에는 False 다(배포 직후 거짓 경보 방지).
    """
    rate, _ = _recent_success_rate(entry)
    return rate is not None and rate < FLAKY_SUCCESS_RATE


def record_cycle(result: dict, source_key_map: dict[str, str]) -> list[str]:
    """한 수집 주기 결과(result dict)를 소스별로 한 번씩 기록.
    source_key_map: {소스이름: result에서 그 소스가 채우는 키}. 값이 None이면
    실패/건너뜀(수집 실패), non-None이면 성공으로 판정 — 주기당 소스별 정확히
    1회만 기록해 연속실패 카운트가 중복 증가하지 않게 한다.

    반환: 이번 주기에 '새로' failing 상태로 넘어간 소스 목록(연속실패가 딱
    FAILING_STREAK에 도달한 것). 지금은 통보를 pending_notifications가 맡으므로
    이 반환값은 로그·호환용이다.

    ★ 값이 왔는지까지 본다 ★
    예전엔 `result[key] is not None` 하나로만 판정해서, 함수가 예외 없이 돌기만 하면
    성공으로 셌다. 그래서 OpenSky 이동성이 '공항 0개·항공편 None'을 담은 dict를
    돌려주는데도 229회 연속 성공으로 기록됐고, "21/21 정상"이라는 숫자가 실제보다
    부풀려져 있었다. 죽은 소스가 살아있다고 보고되는 건 조기경보 시스템에서
    가장 위험한 종류의 거짓말이다.
    """
    no_data_keys = set(result.get("_no_data_keys") or ())
    newly_failing = []
    for source, key in source_key_map.items():
        if is_retired(source):
            # 추적에서 뺀 소스는 기록하지 않는다 — 기록하면 값이 안 오는 게
            # 당연한데도 실패/값없음으로 계속 쌓여 경보가 울린다.
            continue
        value = result.get(key)
        if key in no_data_keys:
            # collector가 '정상인데 값 없음'이라고 명시한 것(위키 404 지연 등)
            record_source_result(source, ok=False, no_data=True)
        elif value is None:
            before = _load_raw().get(source, {}).get("consecutive_failures", 0)
            record_source_result(source, ok=False)
            if before + 1 == FAILING_STREAK:
                newly_failing.append(source)
        elif _is_empty(value):
            # 예외는 안 났지만 알맹이가 비었다 — 성공으로 세면 거짓이 된다.
            record_source_result(source, ok=False, no_data=True)
        else:
            record_source_result(source, ok=True)
    return newly_failing


def _is_empty(value) -> bool:
    """'왔지만 알맹이가 없는' 값인가. 보수적으로만 판정한다.

    0이나 False는 비었다고 보지 않는다 — 감염병 데이터에서 '0건'은 진짜 정보이고,
    그걸 결측으로 취급하면 조용한 시기를 장애로 오인한다. 빈 컨테이너와, 모든
    값이 None인 dict만 결측으로 본다(후자가 OpenSky처럼 껍데기만 오는 경우다)."""
    if isinstance(value, (dict, list, tuple, set, str)) and len(value) == 0:
        return True
    if isinstance(value, dict) and value and all(v is None for v in value.values()):
        return True
    return False


def _status_for(entry: dict) -> tuple[str, float | None]:
    """(status, staleness_hours) 계산. status = ok | no_data | stale | failing | unknown.

    no_data를 stale보다 먼저 판정한다. 위키처럼 '정상 지연'이 잦은 소스는 마지막
    성공이 6시간을 넘기 쉬운데, 그걸 stale로 올려 경보를 내면 정상 상태를 매일
    울리게 된다(경보 피로 → 진짜 사고를 놓침).
    """
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
    # ★ no_data 보다 먼저 판정한다 ★ 간헐 소스는 대부분의 주기가 no_data 라,
    # no_data 를 먼저 보면 이 상태에 영영 도달하지 못한다 — 그게 GroqWatch 가
    # 몇 주째 `정상 20/21` 에 묻혀 있던 이유다.
    if is_flaky(entry):
        return "flaky", staleness_hours
    if entry.get("last_outcome") == "no_data":
        return "no_data", staleness_hours
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
    no_data = []
    long_no_data = []
    flaky = []
    for source, entry in sorted(data.items()):
        if is_retired(source):
            # 집계·경보에서 뺀다. 파일에 남은 옛 항목이 여기로 새어 들어오면
            # staleness 만 계속 늘어 영영 울린다(위 RETIRED_SOURCES 주석 참고).
            continue
        status, staleness = _status_for(entry)
        rate, samples = _recent_success_rate(entry)
        row = {
            "source": source,
            "status": status,
            "staleness_hours": staleness,
            "consecutive_failures": entry.get("consecutive_failures", 0),
            "last_success_at": entry.get("last_success_at"),
            "last_failure_at": entry.get("last_failure_at"),
            "last_no_data_at": entry.get("last_no_data_at"),
            "last_error": entry.get("last_error"),
            # 최근 창의 성공률 — 누적 총계는 옛 이력이 오늘의 고장을 가린다.
            "recent_success_rate": round(rate, 3) if rate is not None else None,
            "recent_samples": samples,
        }
        sources.append(row)
        if status == "flaky":
            degraded.append(source)
            flaky.append({
                "source": source,
                "recent_success_rate": round(rate, 3) if rate is not None else None,
                "window": samples,
            })
        elif status in ("failing", "stale"):
            degraded.append(source)
        elif status == "no_data":
            no_data.append(source)
            # 며칠째 값이 없으면 따로 세운다 — 상시 목록에 묻히면 안 보인다.
            if staleness is not None and staleness >= NO_DATA_ALARM_HOURS:
                long_no_data.append({"source": source, "staleness_hours": staleness})

    return {
        "sources": sources,
        "degraded_sources": degraded,
        # ★ healthy_count는 '진짜 값이 온' 소스만 센다 ★ no_data는 여기 안 들어간다.
        # 예전엔 함수가 돌기만 하면 다 셌기 때문에 "21/21 정상"이 부풀려져 있었다.
        "no_data_sources": no_data,
        # ★ 값없음이 NO_DATA_ALARM_HOURS 를 넘긴 것 ★ 이건 경보 대상이다.
        "long_no_data_sources": long_no_data,
        # ★ 가끔만 성공하는 소스 ★ 연속 카운팅도 장기 값없음도 못 잡는 모양이다.
        # 성공할 때마다 staleness 가 리셋되고 no_data 라 연속실패도 0 이라,
        # 실측 7~9% 성공률의 GroqWatch 가 몇 주째 `정상 20/21` 에 묻혀 있었다.
        "flaky_sources": flaky,
        # ★ 추적에서 뺀 소스 — 숨기지 않고 이유와 함께 드러낸다 ★
        # 집계에는 안 들어가지만 목록에는 남는다. 조용히 사라진 소스가 이
        # 시스템에서 가장 위험한 실패 방식이라, 뺀 것도 보이게 둔다.
        "retired_sources": [
            {"source": s, "reason": r} for s, r in sorted(RETIRED_SOURCES.items())
        ],
        "collector_silent_hours": collector_silent_hours(),
        "healthy_count": sum(1 for s in sources if s["status"] == "ok"),
        "total_tracked": len(sources),
        "note": "staleness_hours는 마지막 성공 수집 이후 경과시간(신선도)이며, "
                "실제 사건→DB 반영 역학적 지연이 아님(대부분 무료 소스가 기준일을 "
                "제공하지 않아 후자는 측정 불가). healthy_count는 실제 값이 온 소스만 "
                "세며, no_data_sources(수집은 정상이나 값이 안 옴)는 제외한다. "
                f"long_no_data_sources는 값없음이 {NO_DATA_ALARM_HOURS:.0f}시간을 넘긴 "
                "소스이며, 이건 '아는 조건'이 아니라 죽은 것으로 보고 경보를 낸다.",
    }


# ── 지속 통보 (㉔-b) ────────────────────────────────────────────────
# record_cycle의 newly_failing은 '경계를 넘는 순간' 딱 1회만 잡는다. 그건 중복
# 알림을 막으려던 의도였지만, 실제로는 반대 방향으로 실패했다 — 소스가 나흘을
# 죽어 있어도 알림은 나흘 전 1건뿐이라 대화창에 묻혀 사라졌다(KDCA, 2026-08-13).
# 그래서 "아직 죽어있음"을 RENOTIFY_HOURS마다 다시 알리고, 살아나면 복구도 알린다.
# 복구 통보가 있어야 캡틴이 '조치가 먹혔는지'를 알림만 보고 판단할 수 있다.

def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def pending_notifications() -> dict:
    """지금 사람에게 알려야 할 것 — {"degraded": [...], "recovered": [...]}.

    degraded 항목: {"source", "status", "staleness_hours", "consecutive_failures"}
    - 처음 degraded가 됐거나, 마지막 통보 후 RENOTIFY_HOURS가 지났으면 포함.
    recovered 항목: 직전에 degraded로 통보했는데 지금 ok로 돌아온 소스 이름.
    """
    data = _load_raw()
    now = _now()
    degraded, recovered = [], []
    for source, entry in sorted(data.items()):
        if is_retired(source):
            continue      # 뺀 소스는 울리지도, 복구 통보를 내지도 않는다
        status, staleness = _status_for(entry)
        notified = entry.get("notified_status")
        # no_data는 텔레그램으로 울리지 않는다. 위키 404 지연·OpenSky 차단처럼
        # '정상이거나 이미 아는 조건'이 대부분이라 매일 울리면 경보 피로만 쌓인다.
        # 대신 /api/status의 no_data_sources에 그대로 노출되고, 매일 아침 점검
        # 루틴이 읽는다 — 안 보이게 숨기는 게 아니라, 밀도를 낮춰 보이게 한다.
        # flaky 도 degraded 다 — 이걸 빼면 '보이기는 하는데 안 울리는' 상태가 되고,
        # 그건 지금까지와 똑같이 아무도 모르는 것이다.
        is_degraded = status in ("failing", "stale", "flaky")
        # 값없음이 사흘을 넘기면 그것도 울린다. 짧은 no_data 는 여전히 조용하다 —
        # 경보 피로를 피하면서, 조용히 죽은 소스는 놓치지 않기 위한 선이다.
        long_no_data = (
            status == "no_data"
            and staleness is not None
            and staleness >= NO_DATA_ALARM_HOURS
        )
        if is_degraded or long_no_data:
            last_notified = _parse_iso(entry.get("last_notified_at"))
            state_changed = (
                notified not in ("failing", "stale", "flaky") if is_degraded
                else notified != "no_data"
            )
            due = (
                state_changed                                # 새로 죽음
                or last_notified is None
                or (now - last_notified).total_seconds() / 3600 >= RENOTIFY_HOURS
            )
            if due:
                degraded.append({
                    "source": source,
                    "status": status,
                    "staleness_hours": staleness,
                    "consecutive_failures": entry.get("consecutive_failures", 0),
                })
        elif status == "ok" and notified in ("failing", "stale", "no_data", "flaky"):
            recovered.append(source)
    return {"degraded": degraded, "recovered": recovered}


def mark_notified(sources: list[str]) -> None:
    """통보한 소스에 현재 상태·시각을 도장 찍는다. 통보 '성공' 후에만 호출할 것 —
    전송이 실패했는데 도장을 찍으면 다음 주기에 조용해져서 알림을 잃는다."""
    if not sources:
        return
    data = _load_raw()
    now = _now().isoformat()
    for source in sources:
        entry = data.get(source)
        if entry is None:
            continue
        entry["notified_status"], entry["last_notified_at"] = _status_for(entry)[0], now
    _save_raw(data)


def collector_silent_hours() -> float | None:
    """수집기가 마지막으로 '무엇이든' 기록한 뒤 흐른 시간. None이면 기록 없음.

    데드맨 스위치용 — 위의 소스별 알림은 전부 collector가 돌아야 울린다.
    collector 자체가 죽으면(스케줄러 중단·배포 실패) record_cycle이 아예 안 돌아
    누구도 아무 말을 안 하게 된다. 그게 가장 조용하고 가장 위험한 실패다.
    이 값은 collector가 아니라 /api/status를 보는 쪽에서 판정한다."""
    data = _load_raw()
    stamps = []
    for entry in data.values():
        for key in ("last_success_at", "last_failure_at"):
            parsed = _parse_iso(entry.get(key))
            if parsed:
                stamps.append(parsed)
    if not stamps:
        return None
    return round((_now() - max(stamps)).total_seconds() / 3600, 1)

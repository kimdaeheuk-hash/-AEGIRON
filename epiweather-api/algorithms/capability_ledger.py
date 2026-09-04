"""능력 장부 — "설정됐나"가 아니라 "최근에 실제로 동작했나"를 기록한다.

왜 이게 필요한가(전부 실측 사고다):

  "실측 18일"            → 실제 선행 관측은 0건. 사후 조립분을 섞어 세고 있었다.
  "sovereignty=full_onprem" → 문서 층은 그대로 NVIDIA 클라우드로 나가고 있었다.
  "accuracy 0.988"       → 다수 클래스만 찍은 값. recall은 0.056이었다.
  "nim_configured=true"  → 키만 있었고 수집기는 몇 주째 Claude를 불렀다.

네 번 다 같은 모양이다. **상태 필드가 설정을 근거로 능력을 주장했다.** 코드가
죽으면 로그가 나지만 상태 필드가 부풀면 아무 소리도 안 난다 — 그래서 몇 주씩
간다. 정직성을 파는 제품에서 이건 기능 하나가 아니라 신뢰 전체를 깎는다.

source_health.py가 **데이터 소스**에 대해 이미 이 일을 한다(마지막 성공 시각,
연속 실패, 신선도). 없던 건 **능력**에 대한 같은 장부다. 소스 쪽 파일에 섞지
않는 이유: healthy_count·total_tracked·텔레그램 경보가 전부 그 파일을 세므로,
능력을 끼워 넣으면 "정상 23/23" 숫자가 오염되고 경보가 시끄러워진다.

★ 정직성 ★
- verified는 "관측했다"는 뜻이지 "지금 이 순간 동작한다"가 아니다. 마지막 성공
  이후 VERIFY_WINDOW_HOURS가 지나면 stale로 내려간다 — 옛 성공이 오늘의 고장을
  가리지 않게.
- 한 번도 안 불려봤으면 실패가 아니라 unverified다. 둘을 구분한다: 안 돌려본
  것과 돌렸는데 실패한 것은 전혀 다른 상태다.
- claim_basis가 항상 따라다닌다. 설정만 보고 하는 주장에는 configuration_only가
  붙어 나가므로, 숫자만 떼어 자료에 옮겨도 근거가 같이 간다.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path

LEDGER_FILE = Path(__file__).resolve().parent.parent / "data" / "capability_health.json"

# 마지막 성공이 이 시간을 넘으면 '검증됨'을 유지하지 않는다.
# NVIDIA 층은 하루 1회 슬롯(AI 갭필링·불리틴)에서만 불리는 것도 있어서 넉넉히 잡는다.
VERIFY_WINDOW_HOURS = 72.0

# 최근 결과를 이만큼만 들고 다닌다. 누적 총계로는 '지금 살아있나'를 알 수 없다.
RECENT_WINDOW = 20

# claim_basis 값 — 상태 필드가 무엇을 근거로 말하는지.
BASIS_VERIFIED = "verified_run"        # 실제 성공을 관측함
BASIS_STALE = "verified_but_stale"     # 성공한 적 있으나 오래됨
BASIS_FAILED = "observed_failure"      # 돌렸는데 실패함
BASIS_CONFIG = "configuration_only"    # 설정만 있고 관측 없음
BASIS_ABSENT = "not_configured"        # 설정도 없음


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _load() -> dict:
    if not LEDGER_FILE.exists():
        return {}
    try:
        with open(LEDGER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    try:
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        # 장부 저장 실패가 실제 기능을 막으면 안 된다. 다만 조용히 넘어가면
        # verified가 영영 안 올라가므로, 그건 아래 status()가 unverified로
        # 정직하게 보고한다 — 없는 성공을 있다고 하지는 않는다.
        pass


def record(capability: str, ok: bool, detail: str | None = None,
           endpoint: str | None = None, sovereign: bool | None = None) -> None:
    """능력 1건의 실제 실행 결과를 남긴다. 호출 '시도' 직후에만 부를 것 —
    설정을 읽은 시점이 아니라 응답을 받은 시점이다(그 구분이 이 모듈의 전부다).

    endpoint/sovereign은 '어디로 나갔는가'다. 주권 주장은 설정이 아니라 이
    관측으로만 검증된다 — 온프렘으로 설정해두고 한 번도 안 불렀으면 그건
    검증된 주권이 아니라 의도일 뿐이다."""
    data = _load()
    now = _now().isoformat()
    entry = data.get(capability) or {
        "last_success_at": None, "last_failure_at": None,
        "total_successes": 0, "total_failures": 0,
        "consecutive_failures": 0, "last_error": None,
        "last_endpoint": None, "last_sovereign": None,
        "recent_outcomes": [],
    }
    if ok:
        entry["last_success_at"] = now
        entry["total_successes"] = entry.get("total_successes", 0) + 1
        entry["consecutive_failures"] = 0
    else:
        entry["last_failure_at"] = now
        entry["total_failures"] = entry.get("total_failures", 0) + 1
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        if detail:
            entry["last_error"] = detail[:200]
    if endpoint is not None:
        entry["last_endpoint"] = endpoint
    if sovereign is not None:
        entry["last_sovereign"] = bool(sovereign)
    if detail and ok:
        entry["last_detail"] = detail[:200]

    recent = list(entry.get("recent_outcomes") or [])
    recent.append("ok" if ok else "fail")
    entry["recent_outcomes"] = recent[-RECENT_WINDOW:]

    data[capability] = entry
    _save(data)


def status(capability: str, configured: bool | None = None) -> dict:
    """이 능력이 실제로 동작한 적 있는가.

    configured를 주면 claim_basis가 '설정은 됐는데 관측이 없다'(configuration_only)와
    '설정도 없다'(not_configured)를 구분한다 — 전자가 바로 NIM이 몇 주 갇혀 있던
    상태이고, 상태 필드에서 가장 위험한 칸이다."""
    entry = _load().get(capability)
    if not entry:
        basis = BASIS_ABSENT if configured is False else (
            BASIS_CONFIG if configured else BASIS_ABSENT)
        return {
            "capability": capability,
            "verified": False,
            "claim_basis": basis,
            "last_success_at": None,
            "last_failure_at": None,
            "staleness_hours": None,
            "consecutive_failures": 0,
            "last_endpoint": None,
            "last_sovereign": None,
            "last_error": None,
            "observations": 0,
        }

    last_success = _parse_iso(entry.get("last_success_at"))
    staleness = None
    if last_success:
        staleness = round((_now() - last_success).total_seconds() / 3600, 1)

    if last_success is None:
        basis = BASIS_FAILED if entry.get("total_failures") else (
            BASIS_CONFIG if configured else BASIS_ABSENT)
        verified = False
    elif staleness is not None and staleness > VERIFY_WINDOW_HOURS:
        basis, verified = BASIS_STALE, False
    elif entry.get("consecutive_failures", 0) > 0:
        # 마지막 성공은 창 안이지만 그 뒤로 계속 실패 중 — 지금은 검증됨이 아니다.
        basis, verified = BASIS_FAILED, False
    else:
        basis, verified = BASIS_VERIFIED, True

    return {
        "capability": capability,
        "verified": verified,
        "claim_basis": basis,
        "last_success_at": entry.get("last_success_at"),
        "last_failure_at": entry.get("last_failure_at"),
        "staleness_hours": staleness,
        "consecutive_failures": entry.get("consecutive_failures", 0),
        "last_endpoint": entry.get("last_endpoint"),
        "last_sovereign": entry.get("last_sovereign"),
        "last_error": entry.get("last_error"),
        "observations": entry.get("total_successes", 0) + entry.get("total_failures", 0),
    }


def report(configured: dict[str, bool] | None = None) -> dict:
    """장부 전체 — /api/status가 노출.

    ★ configured를 반드시 넘길 것 ★ 장부에 기록된 것만 나열하면, 이 모듈이
    잡으려는 바로 그 상태('설정은 됐는데 한 번도 안 불림')가 **목록에 아예 안
    뜬다** — 기록이 없으니까. 그러면 없는 게 안 보이는 옛날로 돌아간다.
    아는 능력을 전부 넘겨서, 안 돌아본 것이 빈칸이 아니라 한 줄로 보이게 한다.

    configured는 {능력이름: 설정됐나}. 소유 모듈이 답해야 하는 질문이라
    여기서 알아내지 않는다(그렇게 하면 이 모듈이 전 모듈을 임포트하게 된다)."""
    data = _load()
    names = sorted(set(data) | set(configured or {}))
    rows = [status(n, configured=(configured or {}).get(n)) for n in names]
    return {
        "capabilities": rows,
        "verified_count": sum(1 for r in rows if r["verified"]),
        "total_tracked": len(rows),
        "unverified": [r["capability"] for r in rows if not r["verified"]],
        # ★ 가장 위험한 칸 ★ 설정은 됐는데 한 번도 안 돌아본 능력. 실패보다
        # 조용해서 몇 주씩 간다 — NIM이 정확히 이 상태였다.
        "configured_but_never_run": [
            r["capability"] for r in rows if r["claim_basis"] == BASIS_CONFIG
        ],
        "verify_window_hours": VERIFY_WINDOW_HOURS,
        "note": (
            "verified는 최근 "
            f"{VERIFY_WINDOW_HOURS:.0f}시간 안에 실제 성공을 관측했다는 뜻이며, "
            "'설정돼 있다'와 다르다. 한 번도 안 불린 능력은 실패가 아니라 "
            "claim_basis=configuration_only로 표시된다 — 설정만 보고 능력을 주장하던 "
            "버릇(실측 사고 4건)을 막기 위한 구분이다."
        ),
    }

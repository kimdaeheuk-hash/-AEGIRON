"""공통 상수·데이터 — 원본 HTML 프로토타입과 동일한 값을 Python으로 이식."""
from __future__ import annotations
import math

# ── LCG 랜덤 (seed 기반 결정론적) ───────────────────────────
class LCG:
    def __init__(self, seed: int = 42):
        self.state = seed

    def next(self) -> float:
        self.state = (self.state * 1103515245 + 12345) & 0x7fffffff
        return self.state / 0x7fffffff

    def gauss(self) -> float:
        u = max(self.next(), 1e-9)
        return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * self.next())


# ── 외부 데이터 숫자 파싱 (2026-08-18 전수점검) ─────────────────────────
# 2026-08-13, KDCA가 건수를 "1,296"으로 주는데 int()가 쉼표에서 터져 그 주 국내
# 데이터가 통째로 사라졌다. 나흘간 아무도 몰랐다. 원인은 쉼표 자체가 아니라
# **항목 하나의 실패가 배치 전체를 죽이는 구조**였다 — 57종을 도는 루프 한가운데서
# 예외가 나면 앞서 읽은 56종까지 같이 버려진다.
#
# 전수점검 결과 같은 구조가 baseline_collector(기준선)·behavioral_data(응급실)에도
# 있었다. 기준선 쪽이 특히 위험한데, 조용히 짧은 목록을 돌려주면 이상 탐지가
# 틀린 기준과 비교하면서도 아무 에러를 안 내기 때문이다.
#
# 반대로 gdelt_signals는 처음부터 항목별로 타입을 확인하고 넘어간다 — 올바른
# 패턴은 이미 이 코드베이스 안에 있었고, 균일하게 안 쓰였을 뿐이다. 이 함수들이
# 그 기준이다.

# ── 예외를 로그에 실을 짧은 사유로 (2026-09-05) ────────────────────
# 여기 둔 이유: 이걸 nlp_extract 에만 뒀더니, 몇 시간 뒤 조달(TED) 층이 첫 실호출에
# 전부 실패했는데 로그가 "HTTPErro" 라고만 말했다 — 잘린 데다 상태코드가 없어서
# 401(키)·404(경로)·400(쿼리 형식) 중 무엇인지 알 수 없었고, 고칠 수가 없었다.
# 실패 사유를 만드는 자리는 한 곳이어야 한다.
def http_status(exc: BaseException) -> int | None:
    """예외에서 HTTP 상태코드만. 없으면 None.

    `brief_reason` 이 사유 문자열을 만들 때 쓰던 계산을 꺼내 둔 것이다 —
    **사유 문자열에서 코드를 다시 긁어 읽는 호출부가 생겼기 때문**이다
    (NIM 의 400 물러섬, 2026-10-10). 문자열은 앞에 예외 클래스 이름이 붙고
    공급자 메시지가 뒤에 붙는 자리라, 거기서 `400` 을 찾으면 메시지에 섞인
    숫자까지 걸린다. 코드로 판단하는 곳은 코드를 보게 한다."""
    return getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None)


def brief_reason(exc: BaseException) -> str:
    """예외 → 짧은 사유. 종류와 상태코드까지만 담는다.

    본문을 안 넣는 이유: 응답 본문에 요청 URL·헤더 조각이 섞여 나올 수 있고,
    진단에 실제로 필요한 건 '어떤 종류가 몇 번'이다(401=키, 404=경로·모델명,
    400=요청 형식, 402/429=한도, Timeout=네트워크). 전문이 필요하면 능력 장부의
    last_error 처럼 서버 안에 남기고, 요약 줄에는 이 값만 싣는다."""
    status = http_status(exc)
    return f"{type(exc).__name__} {status}" if status else type(exc).__name__


# ── 공급자가 스스로 말한 이유를 로그까지 가져온다 (2026-09-15) ──────
# ★ 왜 brief_reason 만으로는 부족했나 ★
# 위 docstring 의 판단("전문이 필요하면 능력 장부에 남기고 요약 줄에는 종류·상태
# 코드만")은 옳다 — 응답 본문에는 요청 URL·헤더 조각이 섞여 나올 수 있다. 그런데
# 그 결론에 딸린 전제가 틀렸다: **능력 장부는 /api/status 뒤에 있고, 매일 아침
# 점검 루틴은 거기에 닿지 못한다**(외부 접속이 허용목록이라 railway.app 이 막힌다).
#
# 그래서 실제로 이런 일이 벌어졌다. 추출층이 2026-09-02 부터 매일 같은 줄을 찍었다:
#
#     external_llm_fallback: BadRequestError 400×5
#
# 400 은 **본문에만 이유가 있는** 상태코드다(401=키, 404=경로처럼 코드 자체가
# 말해주지 않는다). 09-06 점검이 "전문을 읽는 게 다음 한 수"라고 적어뒀지만 그
# 세션도 curl 이 막혀 못 읽었고, 09-13·09-15 점검도 같은 벽에 막혔다.
# **14일 동안 이유가 서버 안에 멀쩡히 적혀 있는데 아무도 못 봤다.**
#
# 고치는 방향은 "본문을 다 싣자"가 아니다(그건 원래 판단을 뒤집는 것이다).
# **공급자가 채운 message 필드 하나만** 꺼낸다 — 그게 진단이고, URL·헤더·요청
# 본문은 애초에 손대지 않는다.
_DETAIL_KEYS = ("message", "detail", "title", "error_description")


def _message_from_body(body) -> str | None:
    """구조화된 오류 본문 → 사람이 읽는 메시지 한 줄. 못 찾으면 None.

    본문 전체를 문자열로 만들지 않는다 — 알려진 메시지 키만 본다. 그래야
    자격증명이나 요청 조각이 실려 나갈 길이 없다."""
    if isinstance(body, str):
        return body
    if not isinstance(body, dict):
        return None
    for key in _DETAIL_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value
    # Anthropic·OpenAI 호환 API 는 {"error": {"message": ...}} 로 한 겹 감싼다.
    nested = body.get("error")
    if isinstance(nested, (dict, str)):
        return _message_from_body(nested)
    return None



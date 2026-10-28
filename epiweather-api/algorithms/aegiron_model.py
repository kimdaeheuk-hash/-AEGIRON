"""아이기론 모델 추상화 계층 — '독자 API'로 가는 구조.

배경: 처음엔 추출을 Claude API로만 했지만(외부 의존 = 기술실사 약점, 그리고 국가
바이오안보 주권 포지셔닝과 상충 — 민감 데이터가 해외 API로 나감), 이제 자체
NIM(NVIDIA Inference Microservice) 추출 경로를 두어 '한 곳만 바꿔' 독자 모델로
전환되게 한다.

배선(2026-09-03): 이 모듈은 한동안 '만들어만 두고 아무도 안 부르는' 상태였다.
운영 환경변수에 NVIDIA_API_KEY가 있는데도 수집기는 매시간 Claude를 직접 불렀고,
provider_status는 nim_configured=true를 보고했다 — 설정은 됐지만 쓰이진 않았다.
지금은 collector.py의 AI 갭필링과 unexplained.py가 전부 여기를 거친다. 저장
경로는 extract_record()를 쓴다(차단·실패 응답을 DB로 흘리지 않기 위해).

호출 흐름(우선순위):
  aegiron_model.extract_signal(text)
    → ① NIM 추출(자체 GPU/온프렘 = 완전 주권 / NVIDIA 호스팅 = 준주권)
    → ② Meta Model API 추출(Muse Spark, Meta 호스팅 = 준주권)
    → ③ transformers 로컬 모델(설정+로딩 가능 시)
    → ④ 외부 LLM(nlp_extract, Claude)으로 폴백
    → AEGIRON_META_FIRST=on이면 ②가 ①보다 먼저 간다(해커톤 데모 등 Meta
       경로를 강제할 때 — 기본 off라 키 없는 기존 배포의 동작은 그대로다).
    → sensitive=True + AEGIRON_REQUIRE_LOCAL=on 이면 '주권 경로'가 아닌 처리는
       모두 '차단'(fail-closed) — 민감 텍스트를 외부로 '보내기 전에' 막는다.

★ 정직성 ★
- NIM에도 두 종류가 있다: (a) NVIDIA 호스팅(integrate.api.nvidia.com) — 데이터가
  NVIDIA 클라우드로 나가므로 '완전 주권 아님'(data_sovereign=False), (b) 자체 호스팅
  (온프렘/사설 엔드포인트) — 데이터가 국경을 안 넘음(data_sovereign=True).
  이 둘을 절대 뭉뚱그리지 않고 ai_provider로 구분해 표시한다.
- 민감 데이터 게이팅은 '완전 주권' 경로만 통과시킨다 — 호스팅 NIM은 외부 클라우드로
  간주해 REQUIRE_LOCAL 시 차단한다(호출 전에).
- 여전히 로컬/NIM 미설정이면 외부 폴백임을 정직하게 표시한다("독자 AI"로 과장 금지).
"""
from __future__ import annotations
import os
import re

# 로컬(자체) 모델 경로. 설정돼 있고 로딩 가능하면 자체 모델 사용.
LOCAL_MODEL_PATH_ENV = "AEGIRON_LOCAL_MODEL"
# 민감 데이터는 로컬 전용으로 강제(국외 유출 차단). 정부·국방 조달 요건 대비.
REQUIRE_LOCAL_ENV = "AEGIRON_REQUIRE_LOCAL"

# ── NVIDIA NIM(OpenAI 호환) 설정 ──
# 키 규약은 algorithms/nvidia.py(단일 소스)에 정의 — 여기서 재노출만 한다.
# 텍스트 추출은 AEGIRON_NIM_API_KEY(전용 오버라이드) → NVIDIA_API_KEY(공유) 순.
from . import nvidia as _nvidia
from . import meta_api as _meta

NIM_API_KEY_ENVS = (_nvidia.TEXT_KEY_OVERRIDE_ENV, _nvidia.SHARED_KEY_ENV)
NIM_BASE_URL_ENV = "AEGIRON_NIM_BASE_URL"      # 자체 호스팅이면 여기에 온프렘 URL
NIM_MODEL_ENV = "AEGIRON_NIM_MODEL"
# NVIDIA 호스팅 기본 엔드포인트(설정 없으면 여기 — 준주권으로 표시).
NIM_HOSTED_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"

# ★ 추론형 모델이 본문 전에 잘리고 있었다 (2026-10-10) ★
#
# 10-07·08·09 세 AI 슬롯 모두 5/5 가 같은 사유였다(프로덕션 실측):
#     빈응답(content=null, finish_reason=length,
#            응답키=annotations·audio·content·function_call·reasoning·
#                  reasoning_content·refusal·role·tool_calls)
#
# 두 신호가 같은 곳을 가리킨다 — `finish_reason=length` 는 한도에 걸려 잘렸다는
# 뜻이고, `reasoning_content` 키는 추론형 모델이라는 뜻이다. 추론형은 답 본문
# 전에 추론 토큰을 먼저 쓰는데, 옛 한도 300 은 **추론을 안 하는 8B**
# (`meta/llama-3.1-8b-instruct`)에 맞춰 잡은 값이었다. 09-18 에 모델만
# `AEGIRON_NIM_MODEL` 로 갈고 한도는 그대로 둬서, 추론이 300 을 다 쓰고 본문
# 차례에서 끊겼다. 그게 '본문 없는 200' 이다.
#
# 그래서 둘을 같이 손본다: ① 한도를 올린다 ② 추론 노력을 'low' 로 요청해
# 추론이 예산을 덜 먹게 한다. ②는 서버가 거부할 수 있어 스스로 물러선다(아래).
#
# ⚠️ 라이브 검증 못 함 — 이 샌드박스는 `integrate.api.nvidia.com` 에 못 나간다
# (허용목록 403). 판정은 다음 AI 슬롯(UTC 21시대) 로그 한 줄이다.
NIM_MAX_TOKENS = 1500
# 추론 노력을 낮춰 달라는 요청. NVIDIA 의 gpt-oss NIM 이 받는 꼴이
# `chat_template_kwargs` 라고 문서는 말하지만 **우리가 불러본 적은 없다** —
# 그래서 거부당하면 물러선다(_REASONING_EFFORT_REJECTED).
NIM_REASONING_EFFORT = "low"
# 한도를 5배로 올리면 생성이 길어진다. 30초는 300토큰에 맞춰 잡은 값이라
# 그대로 두면 ReadTimeout 으로 슬롯을 잃는다(사유는 보이지만 결과는 같다).
NIM_TIMEOUT_SEC = 60

# ── Meta Model API(OpenAI 호환) 설정 ──
# 키·베이스·모델 규약은 algorithms/meta_api.py(단일 소스)에 정의 — 여기서 재노출만 한다.
# Meta 호스팅(api.meta.ai)은 외부 클라우드라 준주권. REQUIRE_LOCAL 시 차단된다.
META_FIRST_ENV = "AEGIRON_META_FIRST"      # on이면 Meta를 NIM보다 먼저 시도
META_EXTRACT_ENV = "AEGIRON_META_EXTRACT"  # 텍스트 추출만 Meta에서 빼는 스위치(on/off, 기본 on)
# NIM과 같은 한도·타임아웃 — 같은 프롬프트·같은 스키마라 토큰 분포가 같다.
META_MAX_TOKENS = 1500
META_TIMEOUT_SEC = 60

_LOCAL_MODEL = None
_LOCAL_TRIED = False


def _load_local_model():
    """로컬 모델 로딩 시도(선택적). transformers 등은 설치돼 있을 때만. 실패 시 None."""
    global _LOCAL_MODEL, _LOCAL_TRIED
    if _LOCAL_TRIED:
        return _LOCAL_MODEL
    _LOCAL_TRIED = True
    path = os.environ.get(LOCAL_MODEL_PATH_ENV)
    if not path:
        return None
    try:
        # 실제 자체 모델이 준비되면 여기서 로드(예: transformers/ONNX 분류기).
        # 지금은 인터페이스만 — 무거운 의존성을 기본 설치에 넣지 않는다.
        from transformers import pipeline  # type: ignore
        _LOCAL_MODEL = pipeline("text-generation", model=path)
    except Exception:
        _LOCAL_MODEL = None
    return _LOCAL_MODEL


def _local_extract(text: str) -> dict | None:
    """자체 모델로 추출. 모델 없으면 None(→ 폴백). 실제 추론은 모델 준비 후 구현."""
    model = _load_local_model()
    if model is None:
        return None
    try:
        # TODO: 자체 모델 출력 파싱(학습셋 스키마와 동일). 준비되면 채운다.
        return None
    except Exception:
        return None


def _require_local() -> bool:
    return os.environ.get(REQUIRE_LOCAL_ENV, "off").lower() in ("on", "1", "true")


def _nim_key() -> str | None:
    return _nvidia.text_nim_key()


def _nim_base_url() -> str:
    # 텍스트 전용 URL → 온프렘 공통(AEGIRON_NVIDIA_ONPREM_BASE) → NVIDIA 호스팅.
    return _nvidia.text_base_url()


def _nim_is_sovereign(base_url: str) -> bool:
    """자체 호스팅(온프렘/사설)이면 완전 주권. NVIDIA 호스팅 클라우드면 준주권(False).
    integrate.api.nvidia.com 계열(공용 클라우드)만 비주권으로 본다."""
    return "integrate.api.nvidia.com" not in base_url and "api.nvidia.com" not in base_url


# 텍스트 추출만 NIM에서 빼는 스위치.
# NVIDIA_API_KEY는 유전체(Evo2)·MSA·문서 파싱까지 4개 층이 공유하는 키다. 그래서
# '키가 있으니 텍스트도 NIM' 이 자동으로 성립하면, 유전체 때문에 키를 넣은 사람이
# 자기도 모르게 추출 모델까지 갈아치우게 된다. 그 되돌리기를 재배포 없이 하려고
# 둔다 — off면 텍스트만 기존 경로로 돌아가고 나머지 층은 그대로 NIM을 쓴다.
NIM_EXTRACT_ENV = "AEGIRON_NIM_EXTRACT"


def _nim_extract_enabled() -> bool:
    return os.environ.get(NIM_EXTRACT_ENV, "on").lower() not in ("off", "0", "false")


def _nim_config() -> dict | None:
    """NIM 설정이 갖춰졌으면 dict, 아니면 None(→ NIM 경로 비활성)."""
    if not _nim_extract_enabled():
        return None
    key = _nim_key()
    if not key:
        return None
    base = _nim_base_url()
    return {
        "key": key,
        "base_url": base,
        "model": os.environ.get(NIM_MODEL_ENV) or NIM_DEFAULT_MODEL,
        "sovereign": _nim_is_sovereign(base),
        "provider": "aegiron_nim_selfhosted" if _nim_is_sovereign(base) else "nvidia_nim_hosted",
    }


def _meta_first() -> bool:
    return os.environ.get(META_FIRST_ENV, "off").lower() in ("on", "1", "true")


def _meta_extract_enabled() -> bool:
    return os.environ.get(META_EXTRACT_ENV, "on").lower() not in ("off", "0", "false")


def _meta_config() -> dict | None:
    """Meta 설정이 갖춰졌으면 dict, 아니면 None(→ Meta 경로 비활성)."""
    if not _meta_extract_enabled():
        return None
    key = _meta.meta_key()
    if not key:
        return None
    base = _meta.base_url()
    sovereign = _meta.is_host_sovereign(base)
    return {
        "key": key,
        "base_url": base,
        "model": _meta.model(),
        "sovereign": sovereign,
        "provider": "meta_model_api",
    }


# 추론 노력 지정이 거부됐는지 — 프로세스 수명 동안 기억한다. 슬롯마다 5번
# 부르는데 낱말마다 다시 시험하면 거부된 뒤에도 매번 두 번씩 나간다. TED 의
# 설명 식별자(#30)와 같은 판단이다 — 판정은 한 번이면 족하다.
# (환경변수로 모델을 갈면 컨테이너가 다시 뜨므로 이 기억도 같이 비워진다.)
_REASONING_EFFORT_REJECTED = False

_EFFORT_REJECTED_NOTE = " (추론 노력 지정 거부됨 — 기본 설정으로 호출)"


def _with_effort_note(reason: str | None) -> str | None:
    """거부가 확정된 뒤의 실패 사유에는 그 사실을 붙인다.

    ★ 왜 장부로 안 끝내나 (09-15 의 교훈) ★ 거부는 능력 장부에도 남는다. 그런데
    장부는 `/api/status` 뒤에 있고 **아침 점검은 거기 닿지 못한다**(허용목록). 거부된
    뒤 두 번째 호출부터는 그 필드를 아예 안 보내니, 사유에 안 적으면 "추론 노력을
    낮춰 달라고 했는데 거부당한 상태로 돌고 있다"가 로그 어디에도 없게 된다 —
    그러면 다음 점검이 `출력토큰` 숫자를 'low 로 돌린 결과'로 잘못 읽는다.

    사유가 만들어지는 자리마다 붙이지 않고 **나가는 한 곳**에서만 붙인다 —
    그래서 같은 원인이면 같은 문자열이고(`tally()` 가 5번 호출을 한 줄로 묶는다)
    두 번 붙을 길이 없다. (붙이는 자리를 늘리면 `endswith` 같은 방어가 필요해지고,
    그 방어는 시험으로 못 재는 가지가 된다.)"""
    if reason is None or not _REASONING_EFFORT_REJECTED:
        return reason
    return reason + _EFFORT_REJECTED_NOTE


REQUEST_REJECTED_CODES = (400, 422)


def _is_request_rejected(status: int | None) -> bool:
    """400·422 = 요청 본문 거부. 우리가 더한 건 `chat_template_kwargs` 하나뿐이니
    이 둘이면 그 후보가 원인이라고 보고 한 번 물러선다.
    401(키)·404(모델명)·410(철수)·429(한도)·5xx·타임아웃은 해당 없다 —
    물러서도 안 고쳐지고, 매 호출이 두 번씩 나가기만 한다.

    ★ 사유 문자열이 아니라 상태코드를 본다 ★ 사유는 `HTTPError 400: <공급자 문장>`
    꼴이라 앞에 예외 클래스 이름이 붙고(테스트 더블에서는 그 이름이 다르다) 뒤에
    공급자 메시지가 붙는다. 거기서 `400` 을 찾으면 메시지에 섞인 숫자도 걸린다."""
    return status in REQUEST_REJECTED_CODES


def _nim_attempt(text: str, conf: dict, *, reasoning_effort: bool
                 ) -> tuple[dict | None, dict, str | None, int | None]:
    """한 번의 NIM 호출. (choice, usage, 실패 사유, HTTP 상태코드).
    예외는 사유+코드로 접어 돌려준다.

    예외를 올리지 않는 이유: 호출부가 '물러서서 한 번 더' 를 판단해야 하고, 예외를
    올리면 그 판단이 호출부에서 또 `except` 로 갈라져 같은 처리가 두 곳에 흩어진다."""
    import requests

    from .common import http_status
    from .nlp_extract import build_prompt, reason_with_detail

    payload = {
        "model": conf["model"],
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.0,
        "max_tokens": NIM_MAX_TOKENS,
    }
    if reasoning_effort:
        payload["chat_template_kwargs"] = {"reasoning_effort": NIM_REASONING_EFFORT}
    try:
        resp = requests.post(
            f"{conf['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {conf['key']}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=NIM_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        body = resp.json()
        usage = body.get("usage") if isinstance(body, dict) else None
        return body["choices"][0], (usage if isinstance(usage, dict) else {}), None, None
    except Exception as e:
        # 실패해도 None을 돌려 폴백시키되(기존 동작), '시도했고 실패했다'는 사실은
        # 남긴다. 이게 없으면 NIM이 매번 죽는데도 상태 필드는 계속
        # nim_configured=true로 좋게 말한다 — 몇 주 갇혀 있던 그 상태다.
        #
        # ★ 장부와 사유는 일부러 다른 문자열이다 ★ 장부(`last_error`)는 서버 안에
        # 남는 자리라 예외 전문을 싣고, 돌려주는 사유는 로그·`/api/status` 로 나가는
        # 자리라 모양만 싣는다(#28). 물러섬 때문에 호출이 두 번이면 두 번 다 적힌다 —
        # 실제로 두 번 불렀으니 그게 맞고, 장부의 최종 상태는 두 번째가 말한다.
        _nvidia.record_layer_call("text", conf["base_url"], ok=False,
                                  error=f"{type(e).__name__}: {e}")
        # ★ 410 이 무엇인지 서버가 대답하게 한다 (2026-09-15) ★
        # 09-02 부터 이 경로는 매 슬롯 `HTTPError 410×5` 였다. 410 은 "여기 있던
        # 게 없어졌다"는 **대답**이라 카탈로그 철수가 유력하지만, 그건 추정이었고
        # 확정할 방법이 로그에 없었다 — 본문이 장부로만 갔기 때문이다.
        # 이제 NVIDIA 가 본문에 적어 보내는 사유가 요약 줄에 같이 실린다.
        return None, {}, reason_with_detail(e), http_status(e)


def nim_raw_detailed(text: str, conf: dict) -> tuple[str | None, str | None]:
    """(NIM 원시 응답, 실패 사유). 실패해도 '왜'를 들고 나온다.

    예전엔 실패가 전부 None 하나로 접혀서, 폴백이 조용히 받아 갔고 로그에는
    아무것도 안 남았다. 키가 죽은 것과 모델명이 틀린 것과 응답이 늦은 것을
    구분하지 못하면 고칠 수가 없다."""
    global _REASONING_EFFORT_REJECTED

    ask_effort = not _REASONING_EFFORT_REJECTED
    choice, usage, reason, status = _nim_attempt(text, conf, reasoning_effort=ask_effort)
    if ask_effort and _is_request_rejected(status):
        # 우리가 더한 건 `chat_template_kwargs` 하나뿐이다 — 물러서서 같은 원문을
        # 한 번만 다시. 거부가 확정이면 한도 상향만으로 돌고, 그 사실을 사유에
        # 남긴다(다음 점검이 "요청해봤고 거부됐다"를 로그만 보고 알 수 있게).
        _REASONING_EFFORT_REJECTED = True
        choice, usage, reason, _ = _nim_attempt(text, conf, reasoning_effort=False)
    reason = _with_effort_note(reason)
    if choice is None:
        # 장부는 `_nim_attempt` 가 이미 남겼다(전문까지). 여기서 또 적으면 한 번의
        # 실패가 두 줄이 되고, 두 번째 줄은 전문이 빠진 짧은 사유라 장부가 가진
        # 정보를 덮어쓴다 — 10-10 에 실제로 `502` 가 그렇게 사라졌다.
        return None, reason
    content = choice.get("message") if isinstance(choice, dict) else None
    content = content.get("content") if isinstance(content, dict) else None
    # ★ HTTP 200 이어도 쓸 본문이 없으면 성공이 아니다 (2026-10-07) ★
    # 10-01~06 매 슬롯 `nvidia_nim_hosted: 실패×5` 에 사유가 한 줄도 없었다. 예외는
    # 위에서 반드시 종류를 달고 나가므로, 사유 없는 실패는 "200 인데 content 가
    # null" 한 길뿐이다. 그 길이 아래 줄에서 ok=True 로 장부에 적혀, 장부는 NIM 이
    # 멀쩡하다고 말하는 중이었다 — 전멸을 성공으로 기록한 것이다.
    if not isinstance(content, str) or not content.strip():
        reason = _with_effort_note(_empty_content_reason(choice, content, usage))
        _nvidia.record_layer_call("text", conf["base_url"], ok=False, error=reason)
        return None, reason
    _nvidia.record_layer_call("text", conf["base_url"], ok=True)
    return content, None


_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")


def _empty_content_reason(choice: dict, content, usage: dict | None = None,
                         cap: int = NIM_MAX_TOKENS) -> str:
    """본문 없는 200 응답의 사유. **응답의 모양만** 싣는다 — finish_reason 과
    message 의 키 이름, 그리고 토큰 숫자. 본문·URL·헤더는 안 싣는다(#28 판단 유지).

    왜 이 둘인가: finish_reason=length 이면 토큰 한도(max_tokens)에 걸려 본문 전에
    잘린 것이고, `reasoning_content` 같은 키가 content 대신 채워져 있으면 추론형
    모델이 본문을 다른 칸에 둔 것이다. 처방이 전혀 다르다(한도 상향 / 모델 교체).

    ★ 토큰 숫자를 같이 싣는 이유 (2026-10-10) ★ 사흘 동안 사유가 글자 하나 안
    변했는데도 '한도가 모자란 것'과 '다른 이유로 비어 온 것'을 가를 수가 없었다.
    `출력토큰 1500/1500` 이면 한도를 또 올릴 근거이고, `300/1500` 이면 한도가
    아니라 다른 데 있다는 뜻이다 — 다음 점검이 추측 없이 갈라 읽는다."""
    finish = choice.get("finish_reason") if isinstance(choice, dict) else None
    finish = finish if isinstance(finish, str) and _SAFE_TOKEN.match(finish) else "없음"
    message = choice.get("message") if isinstance(choice, dict) else None
    keys = sorted(k for k in (message or {}) if isinstance(k, str) and _SAFE_TOKEN.match(k))
    kind = "null" if content is None else "빈문자열"
    return (f"빈응답(content={kind}, finish_reason={finish}, "
            f"{_token_note(usage, cap)}응답키={'·'.join(keys) or '없음'})")


def _token_note(usage: dict | None, cap: int = NIM_MAX_TOKENS) -> str:
    """`출력토큰 1500/1500(추론 1480) · ` 또는 서버가 안 줬으면 빈 문자열.

    cap은 분모(해당 경로의 max_tokens) — NIM이 아니면 그 경로의 한도를 넘긴다.
    기본값이 NIM 한도라 기존 NIM 호출부의 출력은 글자 하나 안 바뀐다.

    **정수만 싣는다.** usage 는 서버가 채우는 칸이라 무엇이든 올 수 있다 —
    숫자가 아니면 그 조각을 버린다(사유가 로그·`/api/status` 로 나가는 자리라
    문자열을 그대로 실으면 #28 이 막은 길이 다시 열린다)."""
    if not isinstance(usage, dict):
        return ""
    out = usage.get("completion_tokens")
    if not isinstance(out, int) or isinstance(out, bool):
        return ""
    detail = usage.get("completion_tokens_details")
    thinking = detail.get("reasoning_tokens") if isinstance(detail, dict) else None
    tail = (f"(추론 {thinking})"
            if isinstance(thinking, int) and not isinstance(thinking, bool) else "")
    return f"출력토큰 {out}/{cap}{tail} · "


def nim_raw(text: str, conf: dict) -> str | None:
    """NIM 원시 응답 문자열. 파싱 전 단계라 '모델이 스키마를 얼마나 지켰나'를
    재는 비교 도구(extract_compare)가 여기를 쓴다. 실패 시 None."""
    return nim_raw_detailed(text, conf)[0]


def _nim_extract_detailed(text: str, source: str,
                          conf: dict) -> tuple[dict | None, str | None]:
    """NIM(OpenAI 호환 chat/completions)으로 추출. (레코드 | None, 실패 사유 | None).
    프롬프트·파싱은 nlp_extract와 동일 헬퍼를 재사용해 스키마 일관성을 보장한다.

    호출 실패와 파싱 실패를 가른다 — 8B가 스키마를 못 지키는 것(파싱실패)과
    엔드포인트가 안 되는 것(HTTPError)은 손댈 곳이 다르다. 앞은 모델 상향,
    뒤는 키·모델명·URL 문제다."""
    from .nlp_extract import PARSE_FAILED, parse_extraction

    content, reason = nim_raw_detailed(text, conf)
    if content is None:
        return None, reason
    record = parse_extraction(content, text, source)
    return record, None if record is not None else PARSE_FAILED


def _nim_extract(text: str, source: str, conf: dict) -> dict | None:
    return _nim_extract_detailed(text, source, conf)[0]


def _meta_attempt(text: str, conf: dict) -> tuple[dict | None, dict, str | None, int | None]:
    """한 번의 Meta Model API 호출. (choice, usage, 실패 사유, HTTP 상태코드).
    예외는 사유+코드로 접어 돌려준다(_nim_attempt와 같은 약속).

    ★ NIM과 달리 chat_template_kwargs를 안 보낸다 ★ 그건 NVIDIA NIM 문서에만
    있는 꼴이고 Meta가 받는지는 우리가 불러본 적이 없다 — 검증 안 된 파라미터를
    보내면 400 물러섬 같은 분기를 타게 되는데, 그건 관측이 아니라 추측이다."""
    import requests

    from .common import http_status
    from .nlp_extract import build_prompt, reason_with_detail

    payload = {
        "model": conf["model"],
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.0,
        "max_tokens": META_MAX_TOKENS,
    }
    try:
        resp = requests.post(
            f"{conf['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {conf['key']}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=META_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        body = resp.json()
        usage = body.get("usage") if isinstance(body, dict) else None
        return body["choices"][0], (usage if isinstance(usage, dict) else {}), None, None
    except Exception as e:
        _meta.record_layer_call(conf["base_url"], ok=False,
                                error=f"{type(e).__name__}: {e}")
        return None, {}, reason_with_detail(e), http_status(e)


def meta_raw_detailed(text: str, conf: dict) -> tuple[str | None, str | None]:
    """(Meta 원시 응답, 실패 사유). 실패해도 '왜'를 들고 나온다."""
    choice, usage, reason, _ = _meta_attempt(text, conf)
    if choice is None:
        return None, reason
    content = choice.get("message") if isinstance(choice, dict) else None
    content = content.get("content") if isinstance(content, dict) else None
    # ★ HTTP 200이어도 쓸 본문이 없으면 성공이 아니다 (NIM 2026-10-07과 같은 판단) ★
    if not isinstance(content, str) or not content.strip():
        reason = _empty_content_reason(choice, content, usage, cap=META_MAX_TOKENS)
        _meta.record_layer_call(conf["base_url"], ok=False, error=reason)
        return None, reason
    _meta.record_layer_call(conf["base_url"], ok=True)
    return content, None


def meta_raw(text: str, conf: dict) -> str | None:
    """Meta 원시 응답 문자열. 실패 시 None."""
    return meta_raw_detailed(text, conf)[0]


def _meta_extract_detailed(text: str, source: str,
                           conf: dict) -> tuple[dict | None, str | None]:
    """Meta Model API(OpenAI 호환 chat/completions)로 추출. (레코드 | None, 실패 사유 | None).
    프롬프트·파싱은 nlp_extract와 동일 헬퍼를 재사용해 스키마 일관성을 보장한다."""
    from .nlp_extract import PARSE_FAILED, parse_extraction

    content, reason = meta_raw_detailed(text, conf)
    if content is None:
        return None, reason
    record = parse_extraction(content, text, source)
    return record, None if record is not None else PARSE_FAILED


def _meta_extract(text: str, source: str, conf: dict) -> dict | None:
    return _meta_extract_detailed(text, source, conf)[0]


def _blocked_sovereign(via: str) -> dict:
    return {
        "ai_provider": "local_required_unavailable",
        "blocked": True,
        "reason": f"완전 주권 모드(AEGIRON_REQUIRE_LOCAL=on) — 주권 경로만 허용. {via} 차단.",
    }


def extract_signal_detailed(
    text: str, source: str = "aegiron_model", api_key: str | None = None,
    sensitive: bool = False,
) -> tuple[dict | None, list[str]]:
    """(결과, 시도 자취). 결과는 extract_signal과 같고, 자취는 **실패한 경로마다
    "provider: 사유"** 한 줄이다(성공한 경로는 안 담는다 — 결과가 이미 말한다).

    ★ 왜 자취가 필요한가 ★ 실패 하나에 경로가 둘 이상 얽혀 있다. NIM이 죽어
    폴백으로 넘어갔는데 폴백도 죽으면, 예전엔 그냥 None 하나였다. 그러면
    "8B가 문제니 모델을 올려라" 같은 잘못된 처방이 나온다 — 실제로는 폴백 쪽
    키가 죽은 것일 수도 있다. 어디까지 갔다가 무엇 때문에 멈췄는지를 남긴다."""
    require_local = _require_local()
    attempts: list[str] = []

    # ① NIM 경로(자체 GPU/온프렘 = 완전 주권, NVIDIA 호스팅 = 준주권).
    # ② Meta Model API 경로(Meta 호스팅 = 준주권, 사설 베이스 = 완전 주권).
    # AEGIRON_META_FIRST=on이면 ②가 ①보다 먼저 간다. 키 없는 경로는 통째로
    # 건너뛰므로 기존 배포(키 없음)의 동작은 그대로다.
    _order = ("meta", "nim") if _meta_first() else ("nim", "meta")
    _confs = {"nim": _nim_config(), "meta": _meta_config()}
    _extract_fns = {"nim": _nim_extract_detailed, "meta": _meta_extract_detailed}
    for _hop in _order:
        conf = _confs[_hop]
        if conf is None:
            continue
        # 주권 전용 모드인데 비주권(호스팅)이면 그 홉만 건너뛴다(국외유출 방지).
        # 예전엔 여기서 바로 차단을 돌려줬는데, 그러면 뒤에 주권 로컬이 설정돼
        # 있어도 못 쓰고 끝난다 — fail-closed는 '외부로 안 보낸다'지 '주권
        # 경로까지 안 써본다'가 아니다. 아래 ④ 게이트가 주권 경로 전멸 시
        # 최종 차단을 맡는다.
        # ★ 건너뜀을 자취에 안 남긴다 ★ 차단은 고장이 아니라 정책이 동작한
        # 것이다 — 자취에 섞으면 '고쳐야 할 것'과 '의도한 것'이 같은 목록에
        # 들어간다(test_sovereign_block_is_not_counted_as_a_failed_path).
        if require_local and not conf["sovereign"]:
            continue
        result, reason = _extract_fns[_hop](text, source, conf)
        if result is not None:
            result["ai_provider"] = conf["provider"]
            result["data_sovereign"] = conf["sovereign"]
            return result, attempts
        # 호출 실패 → 아래 경로로 폴백(단, 아래 게이팅 그대로 적용).
        attempts.append(f"{conf['provider']}: {reason or '실패'}")

    # ③ transformers 로컬 모델(완전 주권).
    local = _local_extract(text)
    if local is not None:
        return {**local, "ai_provider": "aegiron_local", "data_sovereign": True}, attempts

    # ④ 주권 경로가 하나도 안 됐음: 주권 전용 모드면 외부 폴백 차단(fail-closed).
    #    공개 뉴스라도 미국 API로 안 나가게 — "완전 주권"의 실질 보장.
    if require_local:
        return _blocked_sovereign("외부 LLM 폴백"), attempts

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        attempts.append("external_llm_fallback: 키없음")
        return {"ai_provider": "unavailable",
                "reason": "NIM/Meta/로컬 없음 + ANTHROPIC_API_KEY 없음"}, attempts

    from .nlp_extract import extract_signal_detailed as llm_extract
    result, reason = llm_extract(text, source, key)
    if result is not None:
        result["ai_provider"] = "external_llm_fallback"
        result["data_sovereign"] = False
    else:
        attempts.append(f"external_llm_fallback: {reason or '실패'}")
    return result, attempts


def extract_signal(text: str, source: str = "aegiron_model",
                   api_key: str | None = None, sensitive: bool = False) -> dict | None:
    """추출 단일 진입점. NIM → Meta → 로컬 우선 → 외부 LLM 폴백.
    AEGIRON_REQUIRE_LOCAL=on이면 '주권 전용 모드' — 비주권 경로(호스팅 NIM·Meta·
    외부 LLM)는 데이터를 보내기 전에 모두 fail-closed 차단(민감 여부 무관).
    sensitive는 감사·표시용으로만 유지. 반환 dict의 ai_provider로 처리 경로를
    항상 표시한다. 실패 사유까지 필요하면 extract_signal_detailed를 쓸 것."""
    return extract_signal_detailed(text, source, api_key, sensitive)[0]


# ── 저장 경로용 진입점 ────────────────────────────────────────
# extract_signal은 '추출 레코드' 말고도 차단·불가 응답({"blocked": True, ...})을
# 돌려준다. 그걸 그대로 db.create_extracted_signal(**result)에 넘기면 TypeError로
# 터지거나(운이 좋으면) 라벨 없는 껍데기가 DB에 들어간다. 저장 경로는 반드시
# 아래 두 함수를 거치게 해서, '추출된 것'과 '못 한 이유'를 분리한다.

# DB 컬럼이 아닌 부가정보 — 레코드에서 떼어내 provenance로만 남긴다.
# (ai_provider는 실제 컬럼이라 레코드에 남긴다 — 교사 모델 추적용.)
NON_RECORD_KEYS = ("data_sovereign", "blocked", "reason")


def is_extraction(result: dict | None) -> bool:
    """실제 추출 레코드인지(차단·불가 응답이 아닌지). raw_text 유무로 판정 —
    차단/불가 응답에는 원문이 없다."""
    return bool(result) and "raw_text" in result


def extraction_available(api_key: str | None = None) -> bool:
    """추출을 시도할 백엔드가 하나라도 있는지. 수집기 게이트용.
    예전엔 ANTHROPIC_API_KEY만 봐서, NIM 키만 있으면 추출 자체를 건너뛰었다."""
    if _nim_config() is not None:
        return True
    if _meta_config() is not None:
        return True
    if os.environ.get(LOCAL_MODEL_PATH_ENV):
        return True
    return bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))


def extract_record(text: str, source: str, api_key: str | None = None,
                   sensitive: bool = False) -> tuple[dict | None, dict]:
    """(DB 저장 가능한 레코드 | None, 처리경로 정보).

    추출에 성공하면 레코드에 ai_provider가 남아 어느 모델이 만든 라벨인지
    DB에서 되짚을 수 있다. 실패·차단이면 레코드는 None이고 사유만 돌려준다 —
    '못 했다'를 '했다'로 바꾸지 않는다.

    attempts에는 실패한 경로가 "provider: 사유"로 담긴다. 성공했더라도 비어 있지
    않을 수 있다(NIM이 죽고 폴백이 살린 경우) — 그건 숨길 게 아니라 봐야 할
    사실이다. 폴백이 매번 구해주고 있으면 NIM은 사실상 꺼져 있는 것이다."""
    result, attempts = extract_signal_detailed(
        text, source=source, api_key=api_key, sensitive=sensitive)
    provider = (result or {}).get("ai_provider") or "none"
    if not is_extraction(result):
        return None, {
            "ai_provider": provider,
            "blocked": bool((result or {}).get("blocked")),
            "reason": (result or {}).get("reason"),
            "attempts": attempts,
        }
    provenance = {
        "ai_provider": provider,
        "data_sovereign": result.get("data_sovereign"),
        "blocked": False,
        "reason": None,
        "attempts": attempts,
    }
    record = {k: v for k, v in result.items() if k not in NON_RECORD_KEYS}
    return record, provenance


def provider_status() -> dict:
    """현재 어느 AI 제공자가 활성인지 + 주권 태세. 심사에서 '주권 대비 설계' 근거."""
    local_configured = bool(os.environ.get(LOCAL_MODEL_PATH_ENV))
    local_loaded = _load_local_model() is not None
    conf = _nim_config()
    nim_active = conf is not None
    meta_conf = _meta_config()
    meta_active = meta_conf is not None

    # ★ '활성'을 설정으로 정하지 않는다 ★ 아래 active_provider는 여전히 '설정상
    # 우선 경로'다. 그게 실제로 돌았는지는 장부(capability_ledger)만 안다.
    from .capability_ledger import status as _cap_status
    text_layer = _cap_status(_nvidia.LAYER_CAPABILITIES["text"], configured=nim_active)
    meta_layer = _cap_status(_meta.LAYER_CAPABILITY, configured=meta_active)

    if meta_active and _meta_first():
        active_provider = "meta_model_api"
    elif nim_active:
        active_provider = conf["provider"]
    elif meta_active:
        active_provider = "meta_model_api"
    elif local_loaded:
        active_provider = "aegiron_local"
    else:
        active_provider = "external_llm_fallback"

    if nim_active and conf["sovereign"]:
        nim_posture = "자체 호스팅 NIM 활성 — 민감 데이터가 국경을 넘지 않음(완전 주권)"
    elif nim_active:
        nim_posture = ("NVIDIA 호스팅 NIM 활성 — 추론은 자체 모델이나 데이터는 NVIDIA "
                       "클라우드를 경유(준주권). 완전 주권은 AEGIRON_NIM_BASE_URL을 온프렘으로.")
    else:
        nim_posture = None
    if meta_active and meta_conf["sovereign"]:
        meta_posture = "사설 베이스 Meta 활성 — 민감 데이터가 국경을 넘지 않음(완전 주권)"
    elif meta_active:
        meta_posture = ("Meta 호스팅 API 활성 — 데이터는 Meta 클라우드를 경유(준주권). "
                        "완전 주권은 META_MODEL_API_BASE_URL을 온프렘으로.")
    else:
        meta_posture = None
    _postures = [p for p in
                 ((meta_posture, nim_posture) if _meta_first()
                  else (nim_posture, meta_posture))
                 if p]
    if _postures:
        sovereignty = _postures[0]
    elif local_loaded:
        sovereignty = "로컬 모델 활성 — 민감 데이터가 국외로 나가지 않음"
    else:
        sovereignty = ("현재 외부 LLM 폴백 — 민감 데이터는 sensitive=True + "
                       "AEGIRON_REQUIRE_LOCAL로 차단 가능")

    return {
        "active_provider": active_provider,
        "nim_configured": nim_active,
        "nim_sovereign": bool(conf["sovereign"]) if nim_active else False,
        "nim_model": conf["model"] if nim_active else None,
        "meta_configured": meta_active,
        "meta_sovereign": bool(meta_conf["sovereign"]) if meta_active else False,
        "meta_model": meta_conf["model"] if meta_active else None,
        "meta_first": "on" if _meta_first() else "off",
        "local_model_configured": local_configured,
        "local_model_loaded": local_loaded,
        "require_local_for_sensitive": _require_local(),
        # 이 경로가 실제 수집기에 물려 있는지. 예전엔 여기가 nim_configured=true여도
        # 수집기는 Claude를 부르고 있었다 — '설정됨'과 '쓰임'은 다른 말이다.
        "extraction_wired_to_collector": True,
        "nim_extract_switch": "on" if _nim_extract_enabled() else "off",
        # ★ 관측 ★ nim_configured가 '설정'이면 이쪽이 '실제로 돌았나'다.
        # 대외 자료·심사 답변에는 이 칸을 쓸 것.
        "nim_verified": text_layer["verified"],
        "nim_claim_basis": text_layer["claim_basis"],
        "nim_last_success_at": text_layer["last_success_at"],
        "nim_last_error": text_layer["last_error"],
        "meta_extract_switch": "on" if _meta_extract_enabled() else "off",
        "meta_verified": meta_layer["verified"],
        "meta_claim_basis": meta_layer["claim_basis"],
        "meta_last_success_at": meta_layer["last_success_at"],
        "meta_last_error": meta_layer["last_error"],
        "active_provider_basis": (
            "설정상 우선 경로다. 실제로 이 경로가 최근에 성공했는지는 "
            f"nim_verified={text_layer['verified']} / "
            f"nim_claim_basis={text_layer['claim_basis']}, "
            f"meta_verified={meta_layer['verified']} / "
            f"meta_claim_basis={meta_layer['claim_basis']} 를 볼 것."
        ),
        "data_sovereignty": sovereignty,
        # 유전체(Evo2/MSA)·문서·텍스트 NIM을 같은 키 규약으로 묶어 보여줌(단일 소스).
        "nvidia": _nvidia.nvidia_status(),
        "meta": _meta.meta_status(),
        "note": "NIM(NVIDIA_API_KEY/AEGIRON_NIM_API_KEY) 설정 시 수집기의 추출이 NIM으로 "
                "전환된다(collector.py → nlp_extract → 이 모듈). Meta 키(META_MODEL_API_KEY)가 "
                "있으면 NIM 다음으로 Meta Model API(Muse Spark)를 시도한다. 자체 호스팅 URL이면 "
                "완전 주권, NVIDIA·Meta 호스팅이면 준주권. 각 신호가 어느 경로로 뽑혔는지는 "
                "extracted_signals.ai_provider에 건별로 남는다. 텍스트만 되돌리려면 "
                "AEGIRON_NIM_EXTRACT=off / AEGIRON_META_EXTRACT=off.",
    }

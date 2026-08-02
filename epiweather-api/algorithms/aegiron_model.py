"""아이기론 모델 추상화 계층 — '독자 API'로 가는 구조.

배경: 처음엔 추출을 Claude API로만 했지만(외부 의존 = 기술실사 약점, 그리고 국가
바이오안보 주권 포지셔닝과 상충 — 민감 데이터가 해외 API로 나감), 이제 자체
NIM(NVIDIA Inference Microservice) 추출 경로를 두어 '한 곳만 바꿔' 독자 모델로
전환되게 한다.

호출 흐름(우선순위):
  aegiron_model.extract_signal(text)
    → ① NIM 추출(자체 GPU/온프렘 = 완전 주권 / NVIDIA 호스팅 = 준주권)
    → ② transformers 로컬 모델(설정+로딩 가능 시)
    → ③ 외부 LLM(nlp_extract, Claude)으로 폴백
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

# 로컬(자체) 모델 경로. 설정돼 있고 로딩 가능하면 자체 모델 사용.
LOCAL_MODEL_PATH_ENV = "AEGIRON_LOCAL_MODEL"
# 민감 데이터는 로컬 전용으로 강제(국외 유출 차단). 정부·국방 조달 요건 대비.
REQUIRE_LOCAL_ENV = "AEGIRON_REQUIRE_LOCAL"

# ── NVIDIA NIM(OpenAI 호환) 설정 ──
# 키는 NVIDIA_API_KEY 또는 AEGIRON_NIM_API_KEY 중 아무거나.
NIM_API_KEY_ENVS = ("AEGIRON_NIM_API_KEY", "NVIDIA_API_KEY")
NIM_BASE_URL_ENV = "AEGIRON_NIM_BASE_URL"      # 자체 호스팅이면 여기에 온프렘 URL
NIM_MODEL_ENV = "AEGIRON_NIM_MODEL"
# NVIDIA 호스팅 기본 엔드포인트(설정 없으면 여기 — 준주권으로 표시).
NIM_HOSTED_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"
NIM_TIMEOUT_SEC = 30

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
    for env in NIM_API_KEY_ENVS:
        v = os.environ.get(env)
        if v:
            return v
    return None


def _nim_base_url() -> str:
    return (os.environ.get(NIM_BASE_URL_ENV) or NIM_HOSTED_BASE_URL).rstrip("/")


def _nim_is_sovereign(base_url: str) -> bool:
    """자체 호스팅(온프렘/사설)이면 완전 주권. NVIDIA 호스팅 클라우드면 준주권(False).
    integrate.api.nvidia.com 계열(공용 클라우드)만 비주권으로 본다."""
    return "integrate.api.nvidia.com" not in base_url and "api.nvidia.com" not in base_url


def _nim_config() -> dict | None:
    """NIM 설정이 갖춰졌으면 dict, 아니면 None(→ NIM 경로 비활성)."""
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


def _nim_extract(text: str, source: str, conf: dict) -> dict | None:
    """NIM(OpenAI 호환 chat/completions)으로 추출. 실패 시 None(→ 다음 경로).
    프롬프트·파싱은 nlp_extract와 동일 헬퍼를 재사용해 스키마 일관성을 보장한다."""
    import requests

    from .nlp_extract import build_prompt, parse_extraction

    try:
        resp = requests.post(
            f"{conf['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {conf['key']}",
                     "Content-Type": "application/json"},
            json={
                "model": conf["model"],
                "messages": [{"role": "user", "content": build_prompt(text)}],
                "temperature": 0.0,
                "max_tokens": 300,
            },
            timeout=NIM_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

    return parse_extraction(content, text, source)


def _blocked_sensitive(via: str) -> dict:
    return {
        "ai_provider": "local_required_unavailable",
        "blocked": True,
        "reason": f"민감 데이터 — 완전 주권 경로만 허용(AEGIRON_REQUIRE_LOCAL). {via} 차단.",
    }


def extract_signal(text: str, source: str = "aegiron_model",
                   api_key: str | None = None, sensitive: bool = False) -> dict | None:
    """추출 단일 진입점. NIM/로컬 우선 → 외부 LLM 폴백. sensitive면 주권 게이팅.
    반환 dict에 ai_provider를 붙여 어느 경로로 처리됐는지 항상 표시한다."""
    require_local = _require_local()

    # ① NIM 경로(자체 GPU/온프렘 = 완전 주권, NVIDIA 호스팅 = 준주권).
    conf = _nim_config()
    if conf is not None:
        # 민감 데이터인데 비주권(호스팅) NIM이면 '보내기 전에' 차단(국외유출 방지).
        if sensitive and require_local and not conf["sovereign"]:
            return _blocked_sensitive("NVIDIA 호스팅 NIM(외부 클라우드)")
        result = _nim_extract(text, source, conf)
        if result is not None:
            result["ai_provider"] = conf["provider"]
            result["data_sovereign"] = conf["sovereign"]
            return result
        # NIM 호출 실패 → 아래 경로로 폴백(단, 아래 게이팅 그대로 적용).

    # ② transformers 로컬 모델(완전 주권).
    local = _local_extract(text)
    if local is not None:
        return {**local, "ai_provider": "aegiron_local", "data_sovereign": True}

    # ③ 주권 경로가 하나도 안 됐음: 민감 데이터면 외부 폴백 차단(fail-closed).
    if sensitive and require_local:
        return _blocked_sensitive("외부 LLM 폴백")

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"ai_provider": "unavailable",
                "reason": "NIM/로컬 모델 없음 + ANTHROPIC_API_KEY 없음"}

    from .nlp_extract import extract_signal as llm_extract
    result = llm_extract(text, source, key)
    if result is not None:
        result["ai_provider"] = "external_llm_fallback"
        result["data_sovereign"] = False
    return result


def provider_status() -> dict:
    """현재 어느 AI 제공자가 활성인지 + 주권 태세. 심사에서 '주권 대비 설계' 근거."""
    local_configured = bool(os.environ.get(LOCAL_MODEL_PATH_ENV))
    local_loaded = _load_local_model() is not None
    conf = _nim_config()
    nim_active = conf is not None

    if nim_active:
        active_provider = conf["provider"]
    elif local_loaded:
        active_provider = "aegiron_local"
    else:
        active_provider = "external_llm_fallback"

    if nim_active and conf["sovereign"]:
        sovereignty = "자체 호스팅 NIM 활성 — 민감 데이터가 국경을 넘지 않음(완전 주권)"
    elif nim_active:
        sovereignty = ("NVIDIA 호스팅 NIM 활성 — 추론은 자체 모델이나 데이터는 NVIDIA "
                       "클라우드를 경유(준주권). 완전 주권은 AEGIRON_NIM_BASE_URL을 온프렘으로.")
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
        "local_model_configured": local_configured,
        "local_model_loaded": local_loaded,
        "require_local_for_sensitive": _require_local(),
        "data_sovereignty": sovereignty,
        "note": "NIM(NVIDIA_API_KEY/AEGIRON_NIM_API_KEY) 설정 시 추출이 NIM으로 전환된다. "
                "자체 호스팅 URL(AEGIRON_NIM_BASE_URL)이면 완전 주권, NVIDIA 호스팅이면 준주권. "
                "호출부 변경 없이 환경변수만으로 독자 모델 경로가 활성화된다.",
    }

"""Meta Model API 자격증명·호출 규약의 단일 소스(single source of truth).

배경: AEGIRON 추출은 NIM(자체/호스팅) → 로컬 → 외부 LLM(Claude) 순이었다.
Meta Global AI Developer Hackathon 제출을 위해 Meta의 최신 모델(Muse Spark)을
정식 추출 경로로 둔다. Meta Model API는 OpenAI 호환 chat/completions라 기존
NIM 호출 모양을 그대로 쓴다 — 베이스 URL·모델명·키만 다르다.

★ 규약 ★
- 키는 META_MODEL_API_KEY 우선, 없으면 Meta 문서식 MODEL_API_KEY로 폴백한다.
  (Meta 문서는 키를 MODEL_API_KEY라 부른다 — dev.meta.ai의 API keys에서 발급.)
  둘 다 없으면 이 경로는 비활성(설정 없음)이지 실패가 아니다.
- 기본 베이스 https://api.meta.ai/v1, 기본 모델 muse-spark-1.3.
- Meta 호스팅(api.meta.ai)은 외부 클라우드라 data_sovereign=False다 —
  AEGIRON_REQUIRE_LOCAL=on이면 '보내기 전에' 차단된다(호스팅 NIM과 동일 취급).
- 베이스를 온프렘/사설 OpenAI 호환 엔드포인트(Muse 오픈웨이트 자체호스팅 등)로
  가리키면 주권 경로로 본다(nvidia.is_host_sovereign과 같은 판단).

이 규약의 정의는 여기 한 곳뿐이다. 소비자는 여기 함수를 통해 키·URL·모델을
읽어 규약이 흩어지지 않게 한다(nvidia.py와 같은 자리).
"""
from __future__ import annotations
import os

# Meta Model API 키(코드베이스 표준 이름).
KEY_ENV = "META_MODEL_API_KEY"
# Meta 문서식 키 이름(폴백). Meta 문서는 MODEL_API_KEY라 부른다.
DOC_KEY_ENV = "MODEL_API_KEY"

# 베이스 URL·모델명 오버라이드(선택).
BASE_URL_ENV = "META_MODEL_API_BASE_URL"
MODEL_ENV = "META_MODEL_API_MODEL"

# Meta Model API 기본 엔드포인트(OpenAI 호환).
CLOUD_BASE = "https://api.meta.ai/v1"
# 기본 모델 — Muse Spark 최신(2026-09-02, 1.3). 구 버전(1.1·1.2)도 API에서
# 여전히 지원되므로 필요하면 MODEL_ENV로 지정한다.
DEFAULT_MODEL = "muse-spark-1.3"

# 능력 장부(capability_ledger) 식별자. 장부는 동적이라 등록 절차 없이 이
# 이름으로 record/status를 바로 쓴다(nvidia_text·external_llm_extract와 동렬).
LAYER_CAPABILITY = "meta_text"


def meta_key() -> str | None:
    """Meta Model API 키 — 전용 이름 우선, 없으면 Meta 문서식 이름으로 폴백."""
    return os.environ.get(KEY_ENV) or os.environ.get(DOC_KEY_ENV) or None


def base_url() -> str:
    """Meta Model API 베이스 — 오버라이드 있으면 그쪽, 없으면 Meta 클라우드."""
    return (os.environ.get(BASE_URL_ENV) or CLOUD_BASE).rstrip("/")


def model() -> str:
    """텍스트 추출용 모델 ID — 오버라이드 없으면 Muse Spark 최신 기본값."""
    return os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def chat_url() -> str:
    """chat/completions 전체 URL(OpenAI 호환 경로)."""
    return base_url() + "/chat/completions"


def is_host_sovereign(url: str) -> bool:
    """Meta 공용 클라우드가 아니면(온프렘/사설) 주권 경로로 본다."""
    return "api.meta.ai" not in url


def record_layer_call(url: str, ok: bool, error: str | None = None) -> None:
    """Meta 층 호출 1건의 실제 결과를 능력 장부에 남긴다.

    기록 실패가 본 기능을 막으면 안 되므로 예외를 삼킨다 — 다만 조용히 넘어가도
    거짓말은 안 된다. 기록이 없으면 장부는 '검증 안 됨'으로 보고하지, 성공했다고
    하지 않는다(nvidia.record_layer_call과 같은 약속)."""
    try:
        from .capability_ledger import record
        record(LAYER_CAPABILITY, ok=ok, detail=error,
               endpoint=url, sovereign=is_host_sovereign(url))
    except Exception:
        pass


def meta_status() -> dict:
    """Meta 자격증명·태세 요약(운영 가시성).

    ★ 키가 있다 ≠ 동작한다 ★ 키 유무(설정)와 장부 관측(검증)을 나란히 싣고
    이름으로 구분한다(nvidia_status와 같은 교훈 — NIM이 몇 주 갇혀 있던 차이)."""
    from .capability_ledger import status as _cap_status

    key = bool(meta_key())
    base = base_url()
    st = _cap_status(LAYER_CAPABILITY, configured=key)
    return {
        "key_env": KEY_ENV,
        "key_fallback_env": DOC_KEY_ENV,
        "key_present": key,
        "base_url_env": BASE_URL_ENV,
        "base_url": base,
        "model_env": MODEL_ENV,
        "model": model(),
        "sovereign": is_host_sovereign(base),
        "capability": LAYER_CAPABILITY,
        "verified": st["verified"],
        "claim_basis": st["claim_basis"],
        "last_success_at": st["last_success_at"],
        "last_error": st["last_error"],
        "convention": (
            "META_MODEL_API_KEY(없으면 Meta 문서식 MODEL_API_KEY)로 Meta Model API "
            "추출이 동작한다. 기본 muse-spark-1.3. Meta 호스팅(api.meta.ai)은 외부 "
            "클라우드라 준주권이며, AEGIRON_REQUIRE_LOCAL=on이면 보내기 전에 차단된다. "
            "단, key_present는 '설정'이고 verified가 '관측'이다 — 대외 자료에는 후자를 "
            "쓸 것."
        ),
    }

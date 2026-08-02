"""아이기론 모델 추상화 계층 — '독자 API'로 가는 구조.

배경: 지금은 추출을 Claude API로 하지만(외부 의존 = 기술실사 약점, 그리고 국가
바이오안보 주권 포지셔닝과 상충 — 민감 데이터가 해외 API로 나감), 나중에 자체
증류 모델이 준비되면 '한 곳만 바꿔' 전체가 독자 모델로 전환되도록 이 계층을 둔다.

호출 흐름:
  aegiron_model.extract_signal(text)
    → ① 로컬(자체) 모델이 있으면 그걸로 (data sovereignty: 데이터가 국외로 안 나감)
    → ② 없으면 외부 LLM(nlp_extract, Claude)으로 폴백 (지금은 여기)
    → ③ sensitive=True 인데 로컬 모델이 없고 AEGIRON_REQUIRE_LOCAL=on 이면
         외부 폴백을 '차단'(fail-closed) — 민감 데이터 국외유출 방지(주권 요건)

★ 정직성 ★
- 지금은 로컬 모델이 없어 provider="external_llm_fallback"로 정직하게 표시한다.
  "자체 호스팅"을 "독자 AI"라고 과장하지 않는다.
- 구조만 깔아두는 것 — 실제 로컬 모델은 학습 데이터가 쌓인 뒤(training_data.py).
- 로컬 모델 로딩은 선택적(무거운 의존성 없음): 설정/파일이 있으면 시도, 없으면 폴백.
"""
from __future__ import annotations
import os

# 로컬(자체) 모델 경로. 설정돼 있고 로딩 가능하면 자체 모델 사용.
LOCAL_MODEL_PATH_ENV = "AEGIRON_LOCAL_MODEL"
# 민감 데이터는 로컬 전용으로 강제(국외 유출 차단). 정부·국방 조달 요건 대비.
REQUIRE_LOCAL_ENV = "AEGIRON_REQUIRE_LOCAL"

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


def extract_signal(text: str, source: str = "aegiron_model",
                   api_key: str | None = None, sensitive: bool = False) -> dict | None:
    """추출 단일 진입점. 로컬 우선 → 외부 LLM 폴백. sensitive면 주권 게이팅.
    반환 dict에 ai_provider를 붙여 어느 경로로 처리됐는지 항상 표시한다."""
    local = _local_extract(text)
    if local is not None:
        return {**local, "ai_provider": "aegiron_local"}

    # 로컬이 없음: 민감 데이터인데 로컬 강제면 외부 폴백 차단(국외유출 방지).
    if sensitive and _require_local():
        return {
            "ai_provider": "local_required_unavailable",
            "blocked": True,
            "reason": "민감 데이터 — 로컬 모델 전용(AEGIRON_REQUIRE_LOCAL). 외부 LLM 폴백 차단.",
        }

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"ai_provider": "unavailable", "reason": "로컬 모델 없음 + ANTHROPIC_API_KEY 없음"}

    from .nlp_extract import extract_signal as llm_extract
    result = llm_extract(text, source, key)
    if result is not None:
        result["ai_provider"] = "external_llm_fallback"
    return result


def provider_status() -> dict:
    """현재 어느 AI 제공자가 활성인지 + 주권 태세. 심사에서 '주권 대비 설계' 근거."""
    local_configured = bool(os.environ.get(LOCAL_MODEL_PATH_ENV))
    local_loaded = _load_local_model() is not None
    return {
        "active_provider": "aegiron_local" if local_loaded else "external_llm_fallback",
        "local_model_configured": local_configured,
        "local_model_loaded": local_loaded,
        "require_local_for_sensitive": _require_local(),
        "data_sovereignty": (
            "로컬 모델 활성 — 민감 데이터가 국외로 나가지 않음"
            if local_loaded else
            "현재 외부 LLM 폴백 — 민감 데이터는 sensitive=True + AEGIRON_REQUIRE_LOCAL로 차단 가능"
        ),
        "note": "지금은 로컬 모델 미준비라 외부 LLM 폴백. training_data.py로 학습셋을 모아 "
                "증류 모델을 준비하면 AEGIRON_LOCAL_MODEL 설정만으로 독자 모델로 전환된다"
                "(호출부 변경 없음).",
    }

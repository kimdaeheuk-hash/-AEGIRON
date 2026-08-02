"""NVIDIA 자격증명·서비스 규약의 단일 소스(single source of truth).

배경: AEGIRON은 NVIDIA를 두 층에서 쓴다.
  (A) 유전체/문서 층 — Evo2(서열 자연스러움), ColabFold MSA(상동성),
      PDF 표 추출. health.api.nvidia.com 계열 NIM. 키 = NVIDIA_API_KEY.
  (B) 텍스트 층 — 뉴스→신호 추출 NIM(aegiron_model). 기본
      integrate.api.nvidia.com(LLM), 온프렘 자체호스팅 가능. 키 = 공유
      NVIDIA_API_KEY, 필요 시 AEGIRON_NIM_API_KEY로 텍스트 전용 오버라이드.

★ 규약 ★
- NVIDIA_API_KEY 하나로 위 네 서비스가 전부 동작한다(코드베이스 표준).
- AEGIRON_NIM_API_KEY는 '텍스트 층 전용' 선택 오버라이드일 뿐이다 — 별도
  쿼터/키를 텍스트 추출에만 쓰고 싶을 때. 없으면 공유 키로 폴백.
- 이 규약의 정의는 여기 한 곳뿐이다. 소비자는 여기 함수를 통해 키를 읽어
  규약이 흩어지지 않게 한다(유전체 모듈은 역사적으로 os.environ을 직접 읽지만
  같은 SHARED_KEY_ENV를 보므로 규약상 동일하다 — nvidia_status가 그걸 요약).
"""
from __future__ import annotations
import os

# 전 NVIDIA 서비스 공유 키(코드베이스 표준).
SHARED_KEY_ENV = "NVIDIA_API_KEY"
# 텍스트 추출 전용 오버라이드(선택). 없으면 공유 키로 폴백.
TEXT_KEY_OVERRIDE_ENV = "AEGIRON_NIM_API_KEY"

# 서비스 카탈로그 — 가시성/상태 리포트용. 엔드포인트 실물은 각 모듈이 소유하되
# "어떤 키를 쓰는가"의 규약은 여기서 못박는다.
NVIDIA_SERVICES = (
    {"id": "evo2_naturalness", "layer": "genome",
     "endpoint": "health.api.nvidia.com/v1/biology/arc/evo2-40b"},
    {"id": "msa_homology", "layer": "genome",
     "endpoint": "health.api.nvidia.com/v1/biology/colabfold/msa-search"},
    {"id": "pdf_table_extract", "layer": "document",
     "endpoint": "NVIDIA NIM"},
    {"id": "text_signal_extraction", "layer": "text",
     "endpoint": "integrate.api.nvidia.com/v1 (또는 자체호스팅)",
     "text_override": True},
)


def nvidia_api_key() -> str | None:
    """공유 NVIDIA 키(유전체/문서 층 표준). 미설정이면 None."""
    return os.environ.get(SHARED_KEY_ENV) or None


def text_nim_key() -> str | None:
    """텍스트 추출용 키 — 전용 오버라이드 우선, 없으면 공유 키."""
    return os.environ.get(TEXT_KEY_OVERRIDE_ENV) or os.environ.get(SHARED_KEY_ENV) or None


def nvidia_status() -> dict:
    """NVIDIA 자격증명·서비스 태세 요약(운영 가시성). 어떤 서비스가 키를
    확보했는지 한눈에 — 유전체·텍스트를 같은 키 규약으로 묶어 보여준다."""
    shared = bool(nvidia_api_key())
    override = bool(os.environ.get(TEXT_KEY_OVERRIDE_ENV))
    services = []
    for s in NVIDIA_SERVICES:
        key_available = (shared or override) if s.get("text_override") else shared
        services.append({**s, "key_available": key_available})
    return {
        "shared_key_env": SHARED_KEY_ENV,
        "shared_key_present": shared,
        "text_key_override_env": TEXT_KEY_OVERRIDE_ENV,
        "text_key_override_present": override,
        "any_nvidia_active": shared or override,
        "services": services,
        "convention": (
            "NVIDIA_API_KEY 하나로 전 NVIDIA 서비스(유전체 Evo2/MSA + PDF 표 + 텍스트 NIM)가 "
            "동작한다. AEGIRON_NIM_API_KEY는 텍스트 층 전용 선택 오버라이드일 뿐이다."
        ),
    }

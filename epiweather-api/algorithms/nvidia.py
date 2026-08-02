"""NVIDIA 자격증명·서비스 규약의 단일 소스(single source of truth).

배경: AEGIRON은 NVIDIA를 세 층에서 쓴다. **베이스 호스트가 층마다 다르다** —
이걸 뭉뚱그리면 라우팅에서 한 층이 조용히 빠진다(실제로 문서 층이 빠져 있었다).
  (A) 유전체 층 — Evo2(서열 자연스러움), ColabFold MSA(상동성).
      health.api.nvidia.com 계열 NIM. 키 = NVIDIA_API_KEY.
  (B) 문서 층 — PDF 표 추출(nemotron-parse). OpenAI 호환 chat/completions라
      health.api가 아니라 integrate.api.nvidia.com 계열이다. 키 = 공유 NVIDIA_API_KEY.
  (C) 텍스트 층 — 뉴스→신호 추출 NIM(aegiron_model). 기본
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

# ── 완전 주권 온프렘 ──
# 이 하나만 설정하면 전 NVIDIA 층(유전체 Evo2/MSA + 텍스트 NIM)이 온프렘 NIM
# 클러스터로 라우팅되어 '어떤 데이터도 NVIDIA 클라우드로 나가지 않는다'(완전 주권).
# 예: AEGIRON_NVIDIA_ONPREM_BASE=https://nim.internal.aegiron.gov
# 자체호스팅 방법: NVIDIA BioNeMo/NIM 컨테이너를 사설 GPU에 배포(NGC 카탈로그).
ONPREM_BASE_ENV = "AEGIRON_NVIDIA_ONPREM_BASE"
# 텍스트 층 전용 base_url(온프렘 공통과 별개로 텍스트만 다른 호스트를 쓸 때).
TEXT_BASE_URL_ENV = "AEGIRON_NIM_BASE_URL"

# NVIDIA 클라우드 기본 엔드포인트(온프렘 미설정 시).
CLOUD_HEALTH_BASE = "https://health.api.nvidia.com"
CLOUD_LLM_BASE = "https://integrate.api.nvidia.com/v1"
EVO2_PATH = "/v1/biology/arc/evo2-40b/generate"
MSA_PATH = "/v1/biology/colabfold/msa-search/predict"
# PDF 표 추출(nemotron-parse)은 OpenAI 호환 chat/completions로 부르므로
# 유전체(health.api)가 아니라 LLM 계열 베이스를 쓴다.
PARSE_PATH = "/chat/completions"


def onprem_base() -> str | None:
    """설정된 온프렘 NIM 베이스 URL(없으면 None)."""
    b = os.environ.get(ONPREM_BASE_ENV)
    return b.rstrip("/") if b else None


def health_base_url() -> str:
    """유전체(Evo2/MSA·health.api 계열) 베이스 — 온프렘 있으면 온프렘, 없으면 클라우드."""
    return onprem_base() or CLOUD_HEALTH_BASE


def evo2_url() -> str:
    return health_base_url() + EVO2_PATH


def msa_url() -> str:
    return health_base_url() + MSA_PATH


def text_base_url() -> str:
    """텍스트 NIM 베이스 — 텍스트 전용 URL 우선 → 온프렘 공통 → 클라우드 LLM."""
    return (os.environ.get(TEXT_BASE_URL_ENV) or onprem_base() or CLOUD_LLM_BASE).rstrip("/")


def document_base_url() -> str:
    """문서(PDF 표 추출) 층 베이스 — 온프렘 있으면 온프렘, 없으면 클라우드 LLM.

    텍스트 전용 오버라이드(AEGIRON_NIM_BASE_URL)는 따르지 않는다. 그건 '텍스트
    추출 LLM만 다른 호스트로'라는 뜻이지 문서 파서까지 그리 보내라는 뜻이 아니라서다.
    텍스트만 온프렘으로 돌리면 문서 층은 클라우드에 남고, sovereignty_posture가
    그걸 partial로 정직하게 잡는다."""
    base = onprem_base()
    return f"{base}/v1" if base else CLOUD_LLM_BASE


def parse_url() -> str:
    return document_base_url() + PARSE_PATH


def is_host_sovereign(url: str) -> bool:
    """NVIDIA 공용 클라우드가 아니면(온프렘/사설) 주권 경로로 본다."""
    return "api.nvidia.com" not in url


def sovereignty_posture() -> str:
    """전 층을 종합한 주권 태세: full_onprem / partial / cloud.
    어느 한 층이라도 NVIDIA 클라우드로 나가면 '완전 주권'이 아니다.

    ★ 문서 층을 반드시 포함할 것 ★ 처음엔 유전체·텍스트만 검사해서, 온프렘을
    켜면 PDF 페이지 이미지가 그대로 NVIDIA 클라우드로 나가는데도 full_onprem으로
    보고했다. '데이터 국외반출 금지' 요건을 겨냥한 기능에서 거짓 보증은 기능
    하나가 아니라 신뢰 전체를 깎는다."""
    layers = [health_base_url(), document_base_url(), text_base_url()]
    if all(is_host_sovereign(u) for u in layers):
        return "full_onprem"      # 전 층 온프렘 → 완전 주권
    if any(is_host_sovereign(u) for u in layers):
        return "partial"          # 일부만 온프렘
    return "cloud"                # 전부 NVIDIA 클라우드


def is_fully_sovereign() -> bool:
    return sovereignty_posture() == "full_onprem"

# 서비스 카탈로그 — 가시성/상태 리포트용. 엔드포인트 실물은 각 모듈이 소유하되
# "어떤 키를 쓰는가"의 규약은 여기서 못박는다.
NVIDIA_SERVICES = (
    {"id": "evo2_naturalness", "layer": "genome",
     "endpoint": "health.api.nvidia.com/v1/biology/arc/evo2-40b"},
    {"id": "msa_homology", "layer": "genome",
     "endpoint": "health.api.nvidia.com/v1/biology/colabfold/msa-search"},
    {"id": "pdf_table_extract", "layer": "document",
     "endpoint": "integrate.api.nvidia.com/v1 (또는 온프렘)"},
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
    posture = sovereignty_posture()
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
        # 주권 태세: 온프렘 설정 여부에 따른 데이터 국외유출 판정.
        "onprem_base_env": ONPREM_BASE_ENV,
        "onprem_configured": bool(onprem_base()),
        "sovereignty_posture": posture,
        "fully_sovereign": posture == "full_onprem",
        "layer_endpoints": {
            "genome_health": health_base_url(),
            "document_parse": document_base_url(),
            "text_nim": text_base_url(),
        },
        "convention": (
            "NVIDIA_API_KEY 하나로 전 NVIDIA 서비스(유전체 Evo2/MSA + PDF 표 + 텍스트 NIM)가 "
            "동작한다. AEGIRON_NIM_API_KEY는 텍스트 층 전용 선택 오버라이드. "
            "AEGIRON_NVIDIA_ONPREM_BASE를 설정하면 전 층이 온프렘으로 라우팅되어 완전 주권."
        ),
    }

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


# ── 층별 실제 호출 기록 ────────────────────────────────────────────
# 아래 3개 층은 '설정만 보고' 주권을 주장하던 자리다. 실제 요청을 보낸 직후
# record_layer_call을 불러, 어느 호스트가 정말로 응답했는지를 장부에 남긴다.
# 계측 지점: evo2_naturalness / msa_homology / pdf_table_extract / aegiron_model.
LAYER_CAPABILITIES = {
    "genome": "nvidia_genome",
    "document": "nvidia_document",
    "text": "nvidia_text",
}


def record_layer_call(layer: str, url: str, ok: bool, error: str | None = None) -> None:
    """NVIDIA 층 호출 1건의 실제 결과를 능력 장부에 남긴다.

    기록 실패가 본 기능을 막으면 안 되므로 예외를 삼킨다 — 다만 조용히 넘어가도
    거짓말은 안 된다. 기록이 없으면 장부는 '검증 안 됨'으로 보고하지, 성공했다고
    하지 않는다."""
    capability = LAYER_CAPABILITIES.get(layer)
    if not capability:
        return
    try:
        from .capability_ledger import record
        record(capability, ok=ok, detail=error,
               endpoint=url, sovereign=is_host_sovereign(url))
    except Exception:
        pass


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
    """설정상 완전 주권인가. ★ 이건 '의도'지 '검증'이 아니다 ★
    실제로 그 경로로 트래픽이 갔는지는 sovereignty_verification()이 답한다."""
    return sovereignty_posture() == "full_onprem"


def sovereignty_verification() -> dict:
    """주권 주장의 '관측' 쪽. 설정(posture)과 나란히 놓아 둘이 갈리면 보이게 한다.

    온프렘으로 설정해두고 한 번도 호출하지 않았다면 그건 검증된 주권이 아니라
    의도일 뿐이다. 실제로 데이터가 국외로 나갔는지 여부는 각 층이 마지막으로
    어느 호스트에 붙었는가로만 알 수 있다 — 그 관측을 여기서 모은다.

    verified_full_onprem은 **세 층 전부** 관측됐고 전부 주권 호스트였을 때만
    참이다. 한 층이라도 안 불려봤으면 모른다(unverified_layers에 남는다) —
    모르는 걸 참으로 올리지 않는다. 문서 층이 조용히 클라우드로 나가던
    사고가 정확히 이 칸에서 났다."""
    from .capability_ledger import status

    layers = {
        "genome": health_base_url(),
        "document": document_base_url(),
        "text": text_base_url(),
    }
    observed: dict[str, dict] = {}
    unverified: list[str] = []
    leaked: list[str] = []
    for layer, configured_url in layers.items():
        st = status(LAYER_CAPABILITIES[layer])
        observed[layer] = {
            "configured_endpoint": configured_url,
            "configured_sovereign": is_host_sovereign(configured_url),
            "observed_endpoint": st["last_endpoint"],
            "observed_sovereign": st["last_sovereign"],
            "verified": st["verified"],
            "claim_basis": st["claim_basis"],
            "last_success_at": st["last_success_at"],
        }
        if st["last_sovereign"] is None:
            unverified.append(layer)
        elif st["last_sovereign"] is False:
            leaked.append(layer)

    return {
        "layers": observed,
        "unverified_layers": unverified,
        "layers_observed_leaving_sovereign_boundary": leaked,
        "verified_full_onprem": not unverified and not leaked,
        "note": (
            "sovereignty_posture는 환경변수를 읽은 '설정'이고, 이 블록은 실제 호출이 "
            "어느 호스트에 붙었는지의 '관측'이다. 둘이 다르면 관측이 사실이다. "
            "unverified_layers는 아직 한 번도 안 불린 층이며, 검증되지 않은 것을 "
            "주권으로 세지 않는다."
        ),
    }

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
    from .capability_ledger import status as _cap_status

    shared = bool(nvidia_api_key())
    override = bool(os.environ.get(TEXT_KEY_OVERRIDE_ENV))
    posture = sovereignty_posture()
    verification = sovereignty_verification()

    services = []
    for s in NVIDIA_SERVICES:
        key_available = (shared or override) if s.get("text_override") else shared
        # ★ 키가 있다 ≠ 동작한다 ★ 서비스마다 실제 관측을 나란히 싣는다.
        st = _cap_status(LAYER_CAPABILITIES[s["layer"]], configured=key_available)
        services.append({
            **s,
            "key_available": key_available,
            "verified": st["verified"],
            "claim_basis": st["claim_basis"],
            "last_success_at": st["last_success_at"],
            "last_error": st["last_error"],
        })

    verified_any = any(s["verified"] for s in services)
    return {
        "shared_key_env": SHARED_KEY_ENV,
        "shared_key_present": shared,
        "text_key_override_env": TEXT_KEY_OVERRIDE_ENV,
        "text_key_override_present": override,
        # ★ 이름을 고쳤다 ★ 예전엔 키 유무를 any_nvidia_active(활성)라고 불렀다.
        # 키가 꽂혀 있다는 것과 그 층이 실제로 도는 것은 다른 사실이고, NIM이
        # 몇 주 갇혀 있던 게 정확히 그 차이였다. 둘 다 싣고 이름으로 구분한다.
        "any_nvidia_key_present": shared or override,
        "any_nvidia_verified": verified_any,
        "services": services,
        # 주권 태세: 온프렘 '설정' 여부(의도).
        "onprem_base_env": ONPREM_BASE_ENV,
        "onprem_configured": bool(onprem_base()),
        "sovereignty_posture": posture,
        "fully_sovereign": posture == "full_onprem",
        # 주권 '관측' — 설정과 갈리면 이쪽이 사실이다.
        "sovereignty_verification": verification,
        "verified_full_onprem": verification["verified_full_onprem"],
        "layer_endpoints": {
            "genome_health": health_base_url(),
            "document_parse": document_base_url(),
            "text_nim": text_base_url(),
        },
        "convention": (
            "NVIDIA_API_KEY 하나로 전 NVIDIA 서비스(유전체 Evo2/MSA + PDF 표 + 텍스트 NIM)가 "
            "동작한다. AEGIRON_NIM_API_KEY는 텍스트 층 전용 선택 오버라이드. "
            "AEGIRON_NVIDIA_ONPREM_BASE를 설정하면 전 층이 온프렘으로 라우팅되어 완전 주권. "
            "단, fully_sovereign은 '설정'이고 verified_full_onprem이 '관측'이다 — "
            "대외 자료에는 후자를 쓸 것."
        ),
    }

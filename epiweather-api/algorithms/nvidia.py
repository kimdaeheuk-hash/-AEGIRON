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
# ── 완전 주권 온프렘 ──
# 이 하나만 설정하면 전 NVIDIA 층(유전체 Evo2/MSA + 텍스트 NIM)이 온프렘 NIM
# 클러스터로 라우팅되어 '어떤 데이터도 NVIDIA 클라우드로 나가지 않는다'(완전 주권).
# 예: AEGIRON_NVIDIA_ONPREM_BASE=https://nim.internal.aegiron.gov
# 자체호스팅 방법: NVIDIA BioNeMo/NIM 컨테이너를 사설 GPU에 배포(NGC 카탈로그).
ONPREM_BASE_ENV = "AEGIRON_NVIDIA_ONPREM_BASE"
# NVIDIA 클라우드 기본 엔드포인트(온프렘 미설정 시).
CLOUD_HEALTH_BASE = "https://health.api.nvidia.com"
EVO2_PATH = "/v1/biology/arc/evo2-40b/generate"
MSA_PATH = "/v1/biology/colabfold/msa-search/predict"
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


def is_host_sovereign(url: str) -> bool:
    """NVIDIA 공용 클라우드가 아니면(온프렘/사설) 주권 경로로 본다."""
    return "api.nvidia.com" not in url


# ── 층별 실제 호출 기록 ────────────────────────────────────────────
# 아래 3개 층은 '설정만 보고' 주권을 주장하던 자리다. 실제 요청을 보낸 직후
# record_layer_call을 불러, 어느 호스트가 정말로 응답했는지를 장부에 남긴다.
# 계측 지점: evo2_naturalness / msa_homology (문서·텍스트 층은 개편 2차에서 지웠다).
LAYER_CAPABILITIES = {
    "genome": "nvidia_genome",
}


def record_layer_call(layer: str, url: str, ok: bool, error: str | None = None,
                      capability: str | None = None) -> None:
    """NVIDIA 층 호출 1건의 실제 결과를 능력 장부에 남긴다.

    기록 실패가 본 기능을 막으면 안 되므로 예외를 삼킨다 — 다만 조용히 넘어가도
    거짓말은 안 된다. 기록이 없으면 장부는 '검증 안 됨'으로 보고하지, 성공했다고
    하지 않는다.

    capability를 주면 층 집계(nvidia_genome 등)에 더해 엔진별 ID에도 같은
    관측을 남긴다(이중 기록). 층 집계만으론 Evo2가 죽었는지 MSA가 죽었는지
    가릴 수 없어서 BAIKAL 요청시-엔진 감사(헤임달 P2)가 엔진별 ID를 읽는다.
    기존 호출자는 그대로 두면 층 집계만 남는다(하위 호환)."""
    capabilities = [c for c in (LAYER_CAPABILITIES.get(layer), capability) if c]
    if not capabilities:
        return
    try:
        from .capability_ledger import record
        for cap in capabilities:
            record(cap, ok=ok, detail=error,
                   endpoint=url, sovereign=is_host_sovereign(url))
    except Exception:
        pass



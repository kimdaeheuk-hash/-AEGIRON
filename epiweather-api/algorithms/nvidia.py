"""NVIDIA 유전체 서비스 주소 규약 (2026-11-22 개편 2차: 유전체 층만 남음).

헤임달 유전체 분석이 쓰는 두 NIM 의 베이스 호스트를 한 곳에서 정한다 —
Evo2(서열 자연스러움)·ColabFold MSA(상동성). 둘 다 health.api.nvidia.com 계열이고,
키는 `NVIDIA_API_KEY` 하나다(evo2_naturalness·msa_homology 가 os.environ 에서 직접 읽는다).
문서·텍스트 층은 호출부가 사라져 지웠다(복원 기준 커밋 83406e4).
"""
from __future__ import annotations
import os

# ── 완전 주권 온프렘 ──
# 이 하나만 설정하면 유전체 NIM(Evo2/MSA)이 온프렘 NIM 클러스터로 라우팅되어
# '어떤 데이터도 NVIDIA 클라우드로 나가지 않는다'(완전 주권).
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
# '설정만 보고' 주권을 주장하지 않는다. 실제 요청을 보낸 직후 record_layer_call 을
# 불러, 어느 호스트가 정말로 응답했는지를 장부에 남긴다. 계측 지점: evo2_naturalness / msa_homology.
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



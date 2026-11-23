"""NVIDIA 유전체 서비스 주소 규약 (2026-11-22 개편 2차: 유전체 층만 남음).

헤임달 유전체 분석이 쓰는 두 NIM 의 베이스 호스트를 한 곳에서 정한다 —
Evo2(서열 자연스러움)·ColabFold MSA(상동성). 둘 다 health.api.nvidia.com 계열이고,
키는 `NVIDIA_API_KEY` 하나다(evo2_naturalness·msa_homology 가 os.environ 에서 직접 읽는다).
문서·텍스트 층은 호출부가 사라져 지웠다(복원 기준 커밋 83406e4). 호출 결과를 적던 능력 장부
(capability_ledger)는 아무도 읽지 않아 2026-11-23 지웠다 — 엔진 상태는 BAIKAL 이 본다.
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

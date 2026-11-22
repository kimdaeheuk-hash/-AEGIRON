"""아이기론 온톨로지 — 지금 남은 엔진과 그 사이의 실제 연결 (2026-11-22).

BAIKAL MOB(상태변화 엔진, algorithms/baikal.py)은 이 층 **위에** 선다. 온톨로지는
"무엇이 있고 무엇이 무엇에 기대는가"를 적고, BAIKAL 은 그 위에서 "지금 각 엔진이 어떤
상태이고, 언제 바뀌었고, 한 엔진의 이상이 어디로 번지는가"를 판정·기록한다.

★ 연결은 코드에 실제로 있는 것만 적는다 ★
간선마다 `wired_at` 이 그 연결이 일어나는 코드 자리를 가리킨다. 그림을 그리려고
연결을 지어내면, BAIKAL 의 영향 판정이 없는 경로로 번진다(옛 YGGDRASIL 이 11-05 부터
실제 코드와 어긋나 시험 2건이 깨져 있던 사고).
"""
from __future__ import annotations

# 엔진(노드). cadence 는 그 엔진이 언제 도는가 — 매시 상태가 있는지, 요청 때만 도는지.
NODES: dict[str, dict] = {
    "COLLECTOR": {
        "name_ko": "수집 주기", "name_en": "Collection cycle", "name_fr": "Cycle de collecte",
        "role_ko": "기반", "cadence": "hourly",
        "describes_ko": "매시 정각 극지·헤임달·발할라를 한 번씩 돌리는 스케줄러",
    },
    "HEIMDALL_VARIANTS": {
        "name_ko": "헤임달 변이 추적", "name_en": "Heimdall variant tracking",
        "name_fr": "Heimdall — suivi des variants",
        "role_ko": "변이 추적", "cadence": "hourly",
        "describes_ko": "Nextstrain 공개 빌드의 우세 계통·신규 계통을 읽어 변이 원장에 기록",
    },
    "HEIMDALL_SCREENER": {
        "name_ko": "헤임달 서열 스크리닝", "name_en": "Heimdall sequence screening",
        "name_fr": "Heimdall — criblage de séquences",
        "role_ko": "서열 스크리닝(개발 중)", "cadence": "on_request",
        "describes_ko": "요청한 서열의 방어적 이상 지표 계산 — 개발 중(검증 진행)",
    },
    "VALHALLA": {
        "name_ko": "발할라 대응 판정", "name_en": "Valhalla countermeasure coverage",
        "name_fr": "Valhalla — couverture des contre-mesures",
        "role_ko": "대응 판정", "cadence": "hourly",
        "describes_ko": "위협별 대응제(비축·승인·임상) 준비태세 스냅숏과 대조 원장",
    },
    "POLAR": {
        "name_ko": "극지 감시", "name_en": "Polar watch", "name_fr": "Veille polaire",
        "role_ko": "감지(연구)", "cadence": "hourly",
        "describes_ko": "8개 극지 관측지의 기상(Open-Meteo)·현지어 보도 관찰",
    },
}

# 표시 순서 — 홈·운영 화면의 고리 순서(변이 추적 → 대응 판정 → 감지)를 따른다.
NODE_ORDER: tuple[str, ...] = (
    "COLLECTOR", "HEIMDALL_VARIANTS", "HEIMDALL_SCREENER", "VALHALLA", "POLAR",
)

# 간선: (상류, 하류, 무엇이 흐르나, 코드 자리). 상류가 멈추면 하류의 그 입력이 낡는다.
EDGES: tuple[dict, ...] = (
    {"from": "COLLECTOR", "to": "HEIMDALL_VARIANTS",
     "carries_ko": "매시 Nextstrain 조회 실행", "wired_at": "collector.collect_free_sources"},
    {"from": "COLLECTOR", "to": "VALHALLA",
     "carries_ko": "매시 준비태세 스냅숏 실행", "wired_at": "collector.collect_free_sources"},
    {"from": "COLLECTOR", "to": "POLAR",
     "carries_ko": "매시 극지 관측 실행", "wired_at": "collector.collect_free_sources"},
    {"from": "HEIMDALL_VARIANTS", "to": "VALHALLA",
     "carries_ko": "최근 7일 변이 전이 → 대조 판정의 '재확인' 플래그",
     "wired_at": "match_ledger.record_daily_verdict (variant_flag)"},
)


def downstream(node: str) -> list[dict]:
    """node 에서 바로 나가는 간선들."""
    return [e for e in EDGES if e["from"] == node]


def describe() -> dict:
    """API·화면용 — 노드와 간선을 그대로."""
    return {
        "nodes": [{"key": k, **NODES[k]} for k in NODE_ORDER],
        "edges": list(EDGES),
    }

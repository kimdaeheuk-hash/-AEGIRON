"""YGGDRASIL — 아이기론 생태계 온톨로지 (2026-10-19).

캡틴: "7개의 묶음을 각 시스템으로 보고 이름을 붙이고, 7개를 온톨로지로 연결해줘."

엔진 카탈로그의 7개 묶음을 이름 붙은 시스템으로 두고, 시스템 사이에 **실제로
흐르는 데이터**를 관계(간선)로 적는다. 그 위에서 BAIKAL MOB(baikal.py)이 매시간
각 시스템의 상태를 읽어 생태계의 상태 변화를 기록한다.

★ 간선은 코드에 있는 흐름만 적는다 ★
그럴듯해 보이는 연결을 그려 넣는 순간 이 그림은 홍보물이 된다. 간선마다 그 흐름이
지나가는 코드 자리(`code_path`)와 주기(`cadence`)를 같이 둔다 — 코드가 바뀌면
이 표도 바뀌어야 하고, 시험(test_baikal.py)이 간선의 끝점을 고정한다.

  · VALHALLA 에서 나가는 데이터 간선은 **없다.** 대응제 준비태세는 경보 계산에
    입력되지 않는 독립 축이다(alerts.py·gai.py·alert_intervention.py 어디에서도
    valhalla 를 읽지 않는다, 2026-10-19 확인). 연결된 척 그리지 않는다.
  · 피드백 간선(VAR → SKULD)은 **기록만 된다.** 채점 결과가 예측 모델을 자동으로
    고치지 않는다(`automatic: False`). 자동 반영은 예측·경보 동작을 바꾸는 별도
    결정이라 이 층이 하지 않는다.

이름은 내부 코드명이다 — 실제 기관·기밀등급이 아니고 능력 주장도 아니다
(HEIMDALL·VALHALLA 에 이미 달린 선을 그대로 지킨다).

형식: 표준 JSON-LD(W3C)로도 내보낸다. 어휘는 W3C 의 rdfs·owl 을 쓰고, 아이기론
고유 어휘는 실제 도메인을 주장하지 않도록 `urn:` 이름공간에 둔다. 새 의존성 없음.
"""
from __future__ import annotations

from typing import Any

# ── 7개 시스템 ──────────────────────────────────────────────
# order 는 화면·로그에서 늘 같은 순서로 나오게 하는 값이다(신호가 흐르는 방향).
SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "HUGINN", "order": 1, "group": "detect",
        "name_ko": "후긴", "role_ko": "감시", "role_en": "Surveillance",
        "myth_ko": "오딘의 까마귀 — 온 세상을 날며 본 것을 보고한다",
        "summary_ko": "178개국·52개 언어 현지 보도와 각국 공식 자료를 매시간 수집하고 이상을 탐지",
        "engines": ["local_news", "gai", "negative_space", "unexplained", "pathogen_sentinel",
                    "sentinel", "disaster_watch", "polar_signals", "comtrade_signals",
                    "global_watch", "who_don_declarations"],
        "on_request": [],
    },
    {
        "key": "MIMIR", "order": 2, "group": "extract",
        "name_ko": "미미르", "role_ko": "추출", "role_en": "Extraction",
        "myth_ko": "지혜의 샘 — 원문에서 의미를 길어 올린다",
        "summary_ko": "보도 본문과 보고서 PDF 표를 질병·국가·확진·사망의 구조화 신호로 변환",
        "engines": ["nlp_extract", "pdf_table_extract", "bulletin_ingest", "country_resolve",
                    "event_dedup", "declaration_ingest"],
        "on_request": [],
    },
    {
        "key": "FORSETI", "order": 3, "group": "judge",
        "name_ko": "포르세티", "role_ko": "판정", "role_en": "Judgment",
        "myth_ko": "심판의 신 — 무엇을 위로 올릴지 가른다",
        "summary_ko": "국가 위험지수와 경보 등급·일일 상한으로 사람에게 보낼 것만 선별",
        "engines": ["alerts", "country_risk", "notifier", "trust"],
        "on_request": ["risk_quantification"],
    },
    {
        "key": "SKULD", "order": 4, "group": "predict",
        "name_ko": "스쿨드", "role_ko": "예측·시뮬레이션", "role_en": "Prediction",
        "myth_ko": "미래를 맡은 노른 — 앞으로 될 것",
        "summary_ko": "위험도를 예측으로 기록하고, 확산·유입·개입 시나리오를 산출",
        "engines": ["country_risk._record_prediction", "forecast_engine"],
        # 요청이 올 때만 도는 엔진 — 매시간 상태가 없다. 가동 중인 척하지 않는다.
        "on_request": ["digital_twin", "global_inflow", "defense", "alert_intervention"],
    },
    {
        "key": "HEIMDALL", "order": 5, "group": "genomics",
        "name_ko": "헤임달", "role_ko": "유전체", "role_en": "Genomics",
        "myth_ko": "다리를 지키는 감시자",
        "summary_ko": "공개 시퀀스 계통 추적과 방어적 유전체 스크리닝(판정이 아니라 검토 우선순위)",
        "engines": ["genomic_variants"],
        "on_request": ["evo2_naturalness", "msa_homology", "genome_signals"],
    },
    {
        "key": "VALHALLA", "order": 6, "group": "countermeasures",
        "name_ko": "발할라", "role_ko": "대응제", "role_en": "Countermeasures",
        "myth_ko": "전투를 준비하는 전당",
        "summary_ko": "공개 자료로 비축 커버리지 격차·생산 주권 격차·임상 파이프라인을 집계",
        "engines": ["valhalla_watch", "procurement_watch", "readiness_scopes", "approved_products"],
        "on_request": [],
    },
    {
        "key": "VAR", "order": 7, "group": "verify",
        "name_ko": "바르", "role_ko": "검증", "role_en": "Verification",
        "myth_ko": "맹세의 여신 — 약속을 지켜보고 어기면 벌한다",
        "summary_ko": "예측 봉인·공식 선언 대조 채점·선행성 원장으로 스스로의 숫자를 검증",
        "engines": ["prediction_timestamp", "prediction_resolver", "prediction_scoring",
                    "lead_time_ledger", "source_health", "quality_health"],
        "on_request": [],
    },
)

SYSTEM_KEYS: tuple[str, ...] = tuple(s["key"] for s in SYSTEMS)

# ── 관계(간선) ─────────────────────────────────────────────
# kind: data(데이터가 실제로 흐른다) · feedback(결과가 되돌아간다 — 기록만).
RELATIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "huginn-mimir", "from": "HUGINN", "to": "MIMIR", "kind": "data",
        "label_ko": "원문 제공", "cadence": "daily_21utc",
        "code_path": "collector.collect_ai_sources: global_watch → nlp_extract",
    },
    {
        "id": "huginn-forseti", "from": "HUGINN", "to": "FORSETI", "kind": "data",
        "label_ko": "이상도 신호", "cadence": "hourly",
        "code_path": "gai.compute_gai → alerts.refresh_alerts",
    },
    {
        "id": "mimir-forseti", "from": "MIMIR", "to": "FORSETI", "kind": "data",
        "label_ko": "구조화 신호", "cadence": "hourly",
        "code_path": "db.extracted_signals → country_risk (국가 매칭 심각도)",
    },
    {
        "id": "heimdall-forseti", "from": "HEIMDALL", "to": "FORSETI", "kind": "data",
        "label_ko": "신규 계통 지표", "cadence": "hourly",
        "code_path": "genomic_variants → signal_metrics(genomic_new_clades_*) → gai → alerts",
    },
    {
        "id": "forseti-skuld", "from": "FORSETI", "to": "SKULD", "kind": "data",
        "label_ko": "위험도 → 예측 기록", "cadence": "hourly",
        "code_path": "country_risk.log_notable_predictions → db.predictions",
    },
    {
        "id": "skuld-var", "from": "SKULD", "to": "VAR", "kind": "data",
        "label_ko": "예측 봉인·채점 대상", "cadence": "hourly",
        "code_path": "prediction_timestamp.seal_pending_predictions · prediction_resolver",
    },
    {
        "id": "mimir-var", "from": "MIMIR", "to": "VAR", "kind": "data",
        "label_ko": "정답 후보(공식 선언 추출)", "cadence": "daily_21utc",
        "code_path": "declaration_ingest(document_extracted ≥0.90) → outbreak_timeline",
    },
    {
        "id": "huginn-var", "from": "HUGINN", "to": "VAR", "kind": "data",
        "label_ko": "정답 적재(WHO DON)", "cadence": "daily_21utc",
        "code_path": "who_don_declarations → outbreak_timeline",
    },
    {
        "id": "var-skuld", "from": "VAR", "to": "SKULD", "kind": "feedback",
        "label_ko": "채점 결과", "cadence": "daily_21utc",
        "code_path": "prediction_resolver → predictions.correct / lead_days",
        # 결과는 원장에 기록될 뿐 예측 모델을 자동으로 고치지 않는다.
        "automatic": False,
    },
)

# 피드백 루프 — 정답 적재 → 예측 → 채점. 세 고리가 다 돌아야 증거가 쌓인다
# (.claude/skills/prediction-loop). BAIKAL 이 고리마다 흐르는 양을 기록한다.
FEEDBACK_LOOP: tuple[dict[str, str], ...] = (
    {"key": "ground_truth", "label_ko": "① 정답 적재", "system": "VAR",
     "via": "huginn-var · mimir-var"},
    {"key": "predictions", "label_ko": "② 예측 기록", "system": "SKULD",
     "via": "forseti-skuld"},
    {"key": "scoring", "label_ko": "③ 채점", "system": "VAR",
     "via": "skuld-var · var-skuld"},
)

CADENCE_KO = {
    "hourly": "매시",
    "daily_21utc": "매일 21:00 UTC",
}

# 우리가 쓰는 개념의 클래스. 개체(7개 시스템)와 흐름(간선)은 이 클래스의 인스턴스다.
CLASSES: tuple[dict[str, str], ...] = (
    {"key": "System", "label_ko": "시스템", "comment_ko": "엔진 묶음 하나 — 7개"},
    {"key": "Flow", "label_ko": "흐름", "comment_ko": "시스템 사이를 실제로 지나가는 데이터"},
    {"key": "Signal", "label_ko": "신호", "comment_ko": "수집·추출된 관측"},
    {"key": "Alert", "label_ko": "경보", "comment_ko": "판정을 거쳐 사람에게 갈 수 있는 것"},
    {"key": "Prediction", "label_ko": "예측", "comment_ko": "봉인되고 채점되는 주장"},
    {"key": "GroundTruth", "label_ko": "정답", "comment_ko": "공식 선언 — 채점 기준"},
    {"key": "State", "label_ko": "상태", "comment_ko": "BAIKAL 이 매시간 기록하는 시스템 상태"},
)


def system(key: str) -> dict[str, Any]:
    for s in SYSTEMS:
        if s["key"] == key:
            return s
    raise KeyError(key)


def ontology() -> dict[str, Any]:
    """평문(JSON) 형태 — 화면과 BAIKAL 이 쓴다."""
    return {
        "name": "YGGDRASIL",
        "systems": [dict(s) for s in SYSTEMS],
        "relations": [
            {**r, "cadence_ko": CADENCE_KO.get(r["cadence"], r["cadence"]),
             "automatic": r.get("automatic", True)}
            for r in RELATIONS
        ],
        "feedback_loop": [dict(link) for link in FEEDBACK_LOOP],
        "classes": [dict(c) for c in CLASSES],
        "isolated_systems": isolated_systems(),
        "note": (
            "간선은 코드에 실제로 있는 데이터 흐름만 적는다. VALHALLA 는 경보 계산에 "
            "입력되지 않는 독립 축이다. 피드백 간선은 기록만 되고 예측 모델을 자동으로 "
            "고치지 않는다. 이름은 내부 코드명이다."
        ),
    }


def isolated_systems() -> list[str]:
    """다른 시스템으로 아무 간선도 내보내지 않는 시스템 — 숨기지 않고 밝힌다.

    VAR 는 피드백 간선(기록만)을 내보내므로 여기 들지 않는다. 그 간선이 자동 반영이
    아니라는 사실은 간선 자체의 `automatic: False` 가 말한다."""
    senders = {r["from"] for r in RELATIONS}
    return [k for k in SYSTEM_KEYS if k not in senders]


_NS = "urn:aegiron:yggdrasil#"


def to_jsonld() -> dict[str, Any]:
    """W3C JSON-LD. 클래스는 owl:Class, 시스템·흐름은 그 인스턴스로 낸다."""
    graph: list[dict[str, Any]] = []
    for c in CLASSES:
        graph.append({
            "@id": f"ygg:{c['key']}", "@type": "owl:Class",
            "rdfs:label": {"@value": c["label_ko"], "@language": "ko"},
            "rdfs:comment": {"@value": c["comment_ko"], "@language": "ko"},
        })
    for prop, label in (("from", "출발"), ("to", "도착"), ("kind", "종류"),
                        ("cadence", "주기"), ("codePath", "코드 자리"),
                        ("automatic", "자동 반영"), ("role", "역할")):
        graph.append({
            "@id": f"ygg:{prop}",
            "@type": "owl:ObjectProperty" if prop in ("from", "to") else "owl:DatatypeProperty",
            "rdfs:label": {"@value": label, "@language": "ko"},
        })
    for s in SYSTEMS:
        graph.append({
            "@id": f"ygg:{s['key']}", "@type": "ygg:System",
            "rdfs:label": s["key"],
            "ygg:role": {"@value": s["role_ko"], "@language": "ko"},
            "rdfs:comment": {"@value": s["summary_ko"], "@language": "ko"},
        })
    for r in RELATIONS:
        graph.append({
            "@id": f"ygg:flow/{r['id']}", "@type": "ygg:Flow",
            "rdfs:label": {"@value": r["label_ko"], "@language": "ko"},
            "ygg:from": {"@id": f"ygg:{r['from']}"},
            "ygg:to": {"@id": f"ygg:{r['to']}"},
            "ygg:kind": r["kind"],
            "ygg:cadence": r["cadence"],
            "ygg:codePath": r["code_path"],
            "ygg:automatic": r.get("automatic", True),
        })
    return {
        "@context": {
            "ygg": _NS,
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
        },
        "@graph": graph,
    }

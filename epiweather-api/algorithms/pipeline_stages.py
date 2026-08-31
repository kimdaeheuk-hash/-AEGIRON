"""아이기론 파이프라인 9단계 — 이름의 단일 출처.

## 왜 이 파일이 생겼나 (2026-08-31)

단계 번호가 코드 여기저기에 흩어져 있었다. `main.py` 구획 머리말, 모듈
docstring, 엔드포인트 태그에 `Stage 0`·`Stage 1`·`Stage 2`·`Stage 5`·
`Stage 6`·`Stage 8` 이 적혀 있었는데 **3·4·7 은 아무 데도 없었다.**

그런데 그 자리의 기능은 **멀쩡히 돌고 있었다.** 번호만 안 붙어 있었을 뿐이다.
이름이 없으니 대외 문서를 쓸 때마다 사람이 즉석에서 지어냈고, 그래서 문서마다
단계 이름이 달랐다(포트폴리오 PDF에 실제로 그런 일이 있었다).

**이 파일이 유일한 출처다.** 대외 자료·영상·API 응답은 전부 여기서 읽는다.
여기 없는 단계 이름을 문서에 쓰면 그건 지어낸 것이다.

## 3·4·7 은 새로 만든 기능이 아니다

이미 있던 모듈에 **번호를 붙인 것**이다. 근거를 각 단계의 `modules` 에 적어
두었으니, 이름이 맞는지는 그 파일을 열어 확인하면 된다.

## 0단계와 8단계는 성격이 다르다

나머지가 '감시'라면 이 둘은 '연구'다. 사내 최고 보안등급으로 분리 관리되고
코드명이 따로 있다(`classified_programs.py`). 다만 그 등급은 **아이기론 자체
내부 정의**이며 정부 기밀등급이 아니다 — 대외 표기에서 이걸 흐리면 안 된다.
"""
from __future__ import annotations

from typing import TypedDict


class Stage(TypedDict):
    stage: int
    name_ko: str
    name_en: str
    summary_ko: str
    modules: list[str]
    special: bool
    program_key: str | None


PIPELINE_STAGES: list[Stage] = [
    {
        "stage": 0,
        "name_ko": "발원지·합성위협 탐지",
        "name_en": "Origin & Synthetic Threat Detection",
        "summary_ko": (
            "아직 어디에도 보고되지 않은 단계. 유전체 서열 자체를 보고 자연에서 "
            "생긴 것인지 판별하고, 발원 후보 지점을 격자로 역산한다."
        ),
        "modules": ["synthetic_threat.py", "genome_signals.py"],
        "special": True,
        "program_key": "stage0",
    },
    {
        "stage": 1,
        "name_ko": "민간 신호 융합",
        "name_en": "Civic Signal Fusion",
        "summary_ko": (
            "정부 발표보다 먼저 움직이는 신호를 본다. 현지어 뉴스·검색량·소셜 "
            "언급·위키 조회수를 묶어 그 지역이 평소와 다른지 판단한다."
        ),
        "modules": ["civic.py", "local_signal.py", "local_news.py"],
        "special": False,
        "program_key": None,
    },
    {
        "stage": 2,
        "name_ko": "해외 유입일 예측",
        "name_en": "Global Inflow Forecast",
        "summary_ko": (
            "특정 지역의 발생이 항공 여객을 타고 자국에 닿기까지 걸리는 시간을 "
            "추정한다. 출발지 규모와 노선 여객량을 함께 계산한다."
        ),
        "modules": ["global_inflow.py", "origin_catalog.py"],
        "special": False,
        "program_key": None,
    },
    {
        # ★ 2026-08-31 명명 ★ 기능은 이미 있었고 번호만 없었다.
        "stage": 3,
        "name_ko": "신호 추출·구조화",
        "name_en": "Signal Extraction & Structuring",
        "summary_ko": (
            "보건 보고서의 표와 기사 본문에서 질병·국가·확진·사망을 뽑아 비교 "
            "가능한 형태로 만들어 적재한다. 못 알아본 항목은 추측하지 않고 "
            "비운 채 개수를 보고한다."
        ),
        "modules": ["bulletin_signals.py", "bulletin_ingest.py", "bulletin_trend.py"],
        "special": False,
        "program_key": None,
    },
    {
        # ★ 2026-08-31 명명 ★
        "stage": 4,
        "name_ko": "이상 판정",
        "name_en": "Anomaly Scoring",
        "summary_ko": (
            "신호를 6계층(공식·비공식·행동·환경·동물·설명불가)으로 묶어 각 "
            "신호원의 과거 누적치 대비 이상도(z-score)로 평가한다. 절대량이 "
            "아니라 그 나라의 평소 대비로 보기 때문에 작은 나라의 변화도 잡힌다."
        ),
        "modules": ["signal_metrics.py", "country_risk.py", "country_indicators.py"],
        "special": False,
        "program_key": None,
    },
    {
        "stage": 5,
        "name_ko": "방어 시뮬레이션",
        "name_en": "Defense Simulation (SEIR)",
        "summary_ko": (
            "표준 전염병 모델(SEIR)로 아무것도 하지 않았을 때와 개입했을 때를 "
            "나란히 계산한다. 디지털 트윈은 육로 국경과 항공 노선을 타고 "
            "159개국으로 퍼지는 경로를 함께 낸다."
        ),
        "modules": ["defense.py", "digital_twin.py", "country_borders.py",
                    "alert_intervention.py"],
        "special": False,
        "program_key": None,
    },
    {
        "stage": 6,
        "name_ko": "AI 통합 추론",
        "name_en": "Integrated AI Inference",
        "summary_ko": (
            "여러 층에서 올라온 신호를 묶어 원인과 결과를 잇는다. "
            "'왜 이 지역에서 지금인가'를 설명하는 근거 사슬을 만든다."
        ),
        "modules": ["ai_inference.py", "knowledge_graph.py"],
        "special": False,
        "program_key": None,
    },
    {
        # ★ 2026-08-31 명명 ★
        "stage": 7,
        "name_ko": "예측 검증·채점",
        "name_en": "Prediction Scoring",
        "summary_ko": (
            "낸 예측을 나중에 실제와 대조해 적중률·Brier 점수·보정도를 매긴다. "
            "맞았다고 주장하는 대신 성적표를 남기는 층이다."
        ),
        "modules": ["prediction_scoring.py", "prediction_resolver.py",
                    "historical_backtest.py"],
        "special": False,
        "program_key": None,
    },
    {
        "stage": 8,
        "name_ko": "대응제 준비태세",
        "name_en": "Countermeasure Readiness",
        "summary_ko": (
            "경보의 끝이 아니라 대응 물자의 시작을 본다. 지금 이 병원체에 쓸 수 "
            "있는 백신·치료제가 실제로 있는지, 비축이 어디에 얼마나 있는지, "
            "생산 능력이 수요를 감당하는지를 확인한다."
        ),
        "modules": ["biodefense_readiness.py"],
        "special": True,
        "program_key": "stage8",
    },
]

# 대외 문서에서 이 값을 인용할 때 같이 적어야 하는 것.
NAMED_ON = "2026-08-31"
NEWLY_NAMED_STAGES = (3, 4, 7)


def stage(number: int) -> Stage | None:
    """번호로 단계 하나. 없는 번호는 **추측하지 않고 None**."""
    return next((s for s in PIPELINE_STAGES if s["stage"] == number), None)


def stage_names() -> dict[int, str]:
    """번호 → 한국어 이름. 대외 자료가 이걸 그대로 쓴다."""
    return {s["stage"]: s["name_ko"] for s in PIPELINE_STAGES}


def special_stages() -> list[Stage]:
    """성격이 다른 단계(0·8). 감시가 아니라 연구다."""
    return [s for s in PIPELINE_STAGES if s["special"]]


def pipeline_summary() -> dict:
    """대외 응답용. 새로 명명한 단계를 **숨기지 않고 밝힌다.**"""
    return {
        "stages": PIPELINE_STAGES,
        "total": len(PIPELINE_STAGES),
        "special_stages": [s["stage"] for s in PIPELINE_STAGES if s["special"]],
        "newly_named": list(NEWLY_NAMED_STAGES),
        "newly_named_on": NAMED_ON,
        "note": (
            "3·4·7 단계는 2026-08-31 에 이름을 붙였다. 새로 만든 기능이 아니라 "
            "이미 돌고 있던 모듈에 번호를 부여한 것이며, 근거 모듈은 각 단계의 "
            "modules 에 적혀 있다."
        ),
        "classification_note": (
            "0·8 단계의 보안등급과 코드명은 아이기론 자체 내부 정의이며 "
            "실제 정부기관 소속이나 공식 기밀등급이 아니다."
        ),
    }

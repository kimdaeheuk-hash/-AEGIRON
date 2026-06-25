"""
역병예보 FastAPI 서비스
=======================
Python 추론 엔진을 REST API로 노출.
Next.js 프론트엔드(epiweather-web)와 연동 가능.

실행:
    cd epiweather-api
    uvicorn main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
"""
from __future__ import annotations
import sys, os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# 원본 엔진 src 경로 추가 (backtest·scorer 재사용)
ENGINE_SRC = Path(__file__).parent.parent / "epiweather-handoff" / "engine" / "src"
sys.path.insert(0, str(ENGINE_SRC))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from algorithms.patient_zero import generate_grid
from algorithms.civic import fuse_civic
from algorithms.global_inflow import compute_import
from algorithms.defense import run_defense
from algorithms.decision_tree import classify_alert_level, get_priority_actions
from algorithms.common import PRESETS, CIVIC, THREAT
from algorithms.gai import compute_gai
from algorithms.negative_space import scan_negative_space
from algorithms.alerts import refresh_alerts
from algorithms.country_risk import rank_countries, compute_country_risk, COUNTRIES
from algorithms.event_dedup import dedupe_events
import db

app = FastAPI(
    title="역병예보 API",
    description="감염병 조기경보 추론 엔진 REST API",
    version="0.1.0",
)
db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 헬스체크 ─────────────────────────────────────────────────
@app.get("/health", tags=["시스템"])
def health():
    return {"status": "ok", "version": "0.1.0", "engine": "역병예보 추론 엔진 v1"}


# ── 누적 시계열 신호 (collector.py가 쌓은 데이터) ────────────
@app.get("/api/signals", tags=["시스템"])
def signals(limit: int = 50, type: Optional[str] = None):
    """
    collector.py가 data/signals_log.jsonl 에 누적한 신호 조회.
    type=free_sources|ai_sources 로 필터 가능. limit 만큼 최신순 반환.
    """
    log_path = Path(__file__).parent / "data" / "signals_log.jsonl"
    if not log_path.exists():
        return {"count": 0, "records": [], "note": "아직 수집된 데이터 없음 — collector.py 실행 필요"}

    records = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if type and rec.get("type") != type:
                continue
            records.append(rec)

    records = records[-limit:][::-1]
    return {"count": len(records), "records": records}


# ── Stage 0: 발원지 격자 추론 ────────────────────────────────
class PatientZeroRequest(BaseModel):
    origin_id: str = Field("WUH", description="발원 도시 ID (WUH, JKT, BKK 등)")
    seed: int = Field(42, description="결정론적 시뮬레이션 시드")

@app.post("/api/patient-zero/grid", tags=["Stage 0: 발원지"])
def patient_zero_grid(req: PatientZeroRequest):
    """
    10×10 격자의 발원 후방확률 계산.
    피셔 결합 p-value (6채널 약신호) → 격자별 후방확률 정규화.
    """
    try:
        return generate_grid(req.origin_id, req.seed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patient-zero/local-signal", tags=["Stage 0: 발원지"])
def patient_zero_local_signal(origin_id: str = "WUH"):
    """
    발원지 현지어 Wikipedia 조회량 — 한국 데이터로 못 보는 '현지' 신호의 실제 대체재.
    최근 14일 vs 이전 14일 조회량 비교로 이상치 탐지. 키 불필요, 실시간.
    """
    from algorithms.local_signal import fetch_local_signal
    return fetch_local_signal(origin_id)


# ── Stage 1: 민간 신호 융합 ──────────────────────────────────
class CivicRequest(BaseModel):
    active_ids: list[str] = Field(
        default=["citi", "sewer", "otc", "kit", "lab"],
        description="활성 신호 ID 목록 (citi, sewer, otc, kit, lab)"
    )

@app.post("/api/civic-fusion", tags=["Stage 1: 민간 신호"])
def civic_fusion(req: CivicRequest):
    """
    민간 신호 융합 — 정부 공식 발표 대비 선행일 계산.
    활성 신호들의 최대 선행일·품질가중 점수 반환.
    """
    valid = {s["id"] for s in CIVIC}
    invalid = [id for id in req.active_ids if id not in valid]
    if invalid:
        raise HTTPException(status_code=422, detail=f"알 수 없는 신호 ID: {invalid}")
    return fuse_civic(req.active_ids)


@app.get("/api/civic-fusion/backtest-evidence", tags=["Stage 1: 민간 신호"])
def civic_fusion_backtest_evidence():
    """
    '시민 신호가 정부보다 빠르다'는 주장의 실측 근거.
    2020 COVID-19 검색트렌드 vs 대구 집단감염 백테스트 결과(run_covid_backtest.py)를 반환.
    값은 가정이 아니라 실제 네이버 데이터랩 API + KDCA 공식 발표(OWID/JHU 집계) 교차검증 결과.
    """
    result_path = (
        Path(__file__).parent.parent / "epiweather-handoff" / "engine" / "output" / "covid_backtest_result.json"
    )
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="백테스트 결과 없음 — run_covid_backtest.py 실행 필요")
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    reliable = [r for r in data["results"] if r.get("reliable")]
    best = max(reliable, key=lambda r: r.get("lead_days_vs_daegu") or -999, default=None)
    return {
        "best_lead_days": best["lead_days_vs_daegu"] if best else None,
        "best_keyword_group": best["keyword_group"] if best else None,
        "benchmark": "2020-02-18 대구 집단감염(2차 대유행) 시작",
        "case_data_source": data["case_data_source"],
        "search_data_source": data["search_data_source"],
        "all_results": data["results"],
    }


@app.get("/api/patient-zero/ebola-backtest-evidence", tags=["Stage 0: 발원지"])
def ebola_backtest_evidence():
    """
    '발원지 현지어 신호가 WHO 공식 선언보다 빠르다'는 주장의 실측 근거.
    2026년 진행 중인 DRC/우간다 에볼라 PHEIC — 위키피디아 실시간 조회량 백테스트
    (run_ebola_backtest.py) 결과를 반환. 합성 데이터 없음.
    """
    result_path = (
        Path(__file__).parent.parent / "epiweather-handoff" / "engine" / "output" / "ebola_backtest_result.json"
    )
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="백테스트 결과 없음 — run_ebola_backtest.py 실행 필요")
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    detected = [r for r in data["results"] if r.get("anomaly_date")]
    best = max(detected, key=lambda r: r.get("lead_days_vs_pheic", -999), default=None)
    return {
        "best_lead_days": best.get("lead_days_vs_pheic") if best else None,
        "best_label": best.get("label") if best else None,
        "who_pheic_date": data["who_pheic_date"],
        "data_source": data["data_source"],
        "caveat": data["caveat"],
        "all_results": data["results"],
    }


# ── Stage 2: 해외 유입일 예측 ────────────────────────────────
class ImportRequest(BaseModel):
    origin_id: str = Field("WUH", description="발원 도시 ID")
    threat: str = Field("novel", description="위협 강도 (flu | novel | severe)")

@app.post("/api/import-day", tags=["Stage 2: 글로벌 유입"])
def import_day(req: ImportRequest):
    """
    해외 발원지 → 한국 첫 유입일 예측.
    항공 여객량 × 출현위험 × 지수성장 (BlueDot 방식).
    """
    if req.threat not in ("flu", "novel", "severe"):
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")
    try:
        return compute_import(req.origin_id, req.threat)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Stage 5: SEIR 방어 시뮬레이션 ───────────────────────────
class DefenseRequest(BaseModel):
    threat: str = Field("novel", description="위협 강도 (flu | novel | severe)")
    preset: Optional[str] = Field(None, description="프리셋 사용 시 (none | mild | strong)")
    levers: Optional[dict] = Field(None, description="개별 레버 값 (0~1 범위)")

@app.post("/api/seir-simulate", tags=["Stage 5: 방어 시뮬레이션"])
def seir_simulate(req: DefenseRequest):
    """
    SEIR + 시간가변 개입 시뮬레이션.
    무대응 대비 구한 생명·정점감염·누적사망·병상초과일수 반환.
    """
    if req.threat not in ("flu", "novel", "severe"):
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")

    if req.preset:
        if req.preset not in PRESETS:
            raise HTTPException(status_code=422, detail=f"preset은 {list(PRESETS)} 중 하나")
        lev = dict(PRESETS[req.preset])
    elif req.levers:
        lev = req.levers
    else:
        lev = dict(PRESETS["strong"])

    return run_defense(lev, req.threat)


# ── Stage 5: 후향 검증 ───────────────────────────────────────
class BacktestRequest(BaseModel):
    seasons: int = Field(5, ge=1, le=20, description="검증할 시즌 수")
    signal_choice: str = Field("fused", description="탐지 신호 (official | search | waste | fused)")
    methods: list[str] = Field(
        default=["farrington", "zscore", "ewma"],
        description="비교할 탐지 방법"
    )

@app.post("/api/backtest", tags=["후향 검증"])
def backtest(req: BacktestRequest):
    """
    Farrington / z-score / EWMA 비교 후향 검증.
    합성 데이터로 선행성·탐지율·헛경보를 자동 채점.
    """
    valid_signals = {"official", "search", "waste", "fused"}
    valid_methods = {"farrington", "zscore", "ewma"}

    if req.signal_choice not in valid_signals:
        raise HTTPException(status_code=422, detail=f"signal_choice는 {valid_signals} 중 하나")
    invalid_m = [m for m in req.methods if m not in valid_methods]
    if invalid_m:
        raise HTTPException(status_code=422, detail=f"알 수 없는 방법: {invalid_m}")

    try:
        # 원본 엔진 재사용
        from backtest import make_season, run_backtest
        seasons_data = [
            make_season(f"Season{i+1}", seed=i * 7, n=150, onset=100,
                        lead_offsets={"official": 0, "search": 7, "waste": 10})
            for i in range(req.seasons)
        ]
        reports = run_backtest(seasons_data, req.signal_choice, req.methods)

        result = {}
        for method, rep in reports.items():
            result[method] = {
                "detection_rate": round(rep.detection_rate, 3),
                "mean_lead_days": round(rep.mean_lead, 1) if rep.mean_lead is not None else None,
                "median_lead_days": round(rep.median_lead, 1) if rep.median_lead is not None else None,
                "total_false_alarms": rep.total_false_alarms,
                "seasons": [
                    {
                        "season": s.season,
                        "detected": s.detected,
                        "lead_days": s.lead_time_days,
                        "false_alarms": s.false_alarms,
                    }
                    for s in rep.scores
                ],
            }
        return {
            "signal": req.signal_choice,
            "n_seasons": req.seasons,
            "results": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Global Anomaly Index ─────────────────────────────────────
@app.get("/api/anomaly-score", tags=["GAI"])
def anomaly_score():
    """
    수집기(collector.py)가 data/signals_log.jsonl에 쌓은 신호를
    6계층(공식·비공식·행동·환경·동물·설명불가)으로 묶어 가중합산한 단일 점수.
    각 신호원은 자기 과거 누적치 대비 이상도(z-score)로 평가됨.
    70점↑ 주의, 80점↑ 경보, 90점↑ 위험.
    """
    return compute_gai()


@app.get("/api/negative-space", tags=["GAI"])
def negative_space():
    """
    부정적 공간 감시 — 평소 활발하던 신호원이 과거 평균의 50% 미만으로
    급감했는지 전체 스캔. 신호 증가가 아니라 '보고가 끊긴 것'을 잡아낸다.
    (2014 기니 에볼라 — 보건부 보고 급감 → 실제론 의료체계 붕괴였던 사례 참고)
    """
    return scan_negative_space()


@app.get("/api/alerts", tags=["GAI"])
def alerts():
    """
    경보 피로 방지 — GAI·부정적 공간 감시 후보를 Critical/High/Medium/Low로
    분류하고 일일 캡(Critical 3개, High 5개)을 적용. 대시보드엔 상위 5개만 노출.
    """
    return refresh_alerts()


@app.get("/api/extracted-signals", tags=["GAI"])
def extracted_signals(disease: Optional[str] = None, limit: int = 50):
    """
    NLP 구조화 추출 결과 조회. collector.py의 AI 갭필링이 모아온 자유문장을
    Claude가 disease/location/signal_type 등으로 구조화해 쌓은 것.
    """
    return {"records": db.list_extracted_signals(disease=disease, limit=limit)}


# ── 국가별 위험지수 ───────────────────────────────────────────
@app.get("/api/risk-index", tags=["GAI"])
def risk_index():
    """
    국가별 위험지수 전체 랭킹. 최종위험도 = 원시위험도(직접수치+NLP신호) × 취약성지수.
    취약성지수 4요소는 WHO GHO·World Bank·OpenFlights·UNWTO 실연동 전까지의 추정 시드값.
    """
    return rank_countries()


@app.get("/api/risk-index/{country}", tags=["GAI"])
def risk_index_country(country: str):
    """특정 국가 상세. country는 COUNTRIES 키(DRC, Uganda, South Korea 등)."""
    if country not in COUNTRIES:
        raise HTTPException(
            status_code=404,
            detail=f"지원하지 않는 국가 ID. 지원 목록: {list(COUNTRIES)}",
        )
    return compute_country_risk(country)


@app.get("/api/threats", tags=["GAI"])
def threats():
    """
    현재 진행 중인 위협 — NLP 구조화 추출(⑦) 결과를 disease 기준으로 병합한
    중복제거 이벤트 목록(⑩). 같은 사건을 출처 여러 곳이 따로 보고해도
    하나로 합쳐 신뢰도가중 평균 점수를 매긴다.
    """
    return {"events": dedupe_events()}


# ── 예측 검증 ─────────────────────────────────────────────────
class PredictionCreate(BaseModel):
    country: str = Field(..., description="대상 국가")
    disease: str = Field(..., description="예측 질병")
    risk_score: float = Field(..., description="예측 위험도 (0~100)")
    basis: list[str] = Field(..., min_length=1, description="예측 근거 (최소 1개, 권장 3개)")

@app.post("/api/predictions", tags=["예측 검증"])
def create_prediction(req: PredictionCreate):
    """
    예측 시점에 근거와 함께 기록.
    나중에 실제 결과가 나오면 /api/predictions/{id}/verify로 채점.
    """
    return db.create_prediction(req.country, req.disease, req.risk_score, req.basis)


@app.get("/api/predictions", tags=["예측 검증"])
def get_predictions(country: Optional[str] = None, verified_only: bool = False):
    """
    예측 기록 목록 + 검증된 예측의 정확도 통계.
    '우리가 72% 맞췄다'를 뒷받침하는 실측 수치.
    """
    return {
        "predictions": db.list_predictions(country=country, verified_only=verified_only),
        "accuracy": db.accuracy_stats(country=country),
    }


class PredictionVerify(BaseModel):
    actual_result: str = Field(..., description="실제 발생 여부/내용")
    correct: bool = Field(..., description="예측이 맞았는지")
    lead_days: Optional[int] = Field(None, description="공식 발표 대비 선행 일수 (양수=먼저 감지)")

@app.post("/api/predictions/{prediction_id}/verify", tags=["예측 검증"])
def verify_prediction(prediction_id: int, req: PredictionVerify):
    """예측을 실제 결과로 검증·채점."""
    result = db.verify_prediction(prediction_id, req.actual_result, req.correct, req.lead_days)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 prediction_id 없음")
    return result


# ── Stage 6: AI 통합 추론 ────────────────────────────────────
class AIInferRequest(BaseModel):
    origin_id: str = Field("WUH")
    threat: str = Field("novel")
    rt: float = Field(...)
    arrival_day: int = Field(...)
    detect_lead: int = Field(0)
    civic_lead: int = Field(0)
    pz_top_prob: float = Field(0.0)
    pz_top_cell: str = Field("")
    saved_lives: int = Field(0)
    deaths: int = Field(0)
    peak_infected: int = Field(0)
    hosp_overflow_days: int = Field(0)
    levers: Optional[dict] = Field(None)
    api_key: Optional[str] = Field(None, description="Anthropic API 키 (없으면 환경변수)")

@app.post("/api/ai/infer", tags=["Stage 6: AI 추론"])
def ai_infer(req: AIInferRequest):
    """
    7단계 통합 AI 역학 추론.
    1. 의사결정 트리 → 즉시 권고 (LLM 없이)
    2. RAG → 한국 방역 가이드라인 검색
    3. Claude API → 통합 정책 권고 (프롬프트 캐싱)
    API 키 없이도 의사결정 트리 결과는 반환됨.
    """
    if req.threat not in ("flu", "novel", "severe"):
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")

    from algorithms.common import CITY_MAP
    city = CITY_MAP.get(req.origin_id, {})
    sp = THREAT.get(req.threat, THREAT["novel"])

    situation = {
        "rt": req.rt, "threat": req.threat, "threat_nm": sp["nm"], "r0": sp["R0"],
        "origin_nm": city.get("nm", req.origin_id), "origin_note": city.get("note", ""),
        "arrival_day": req.arrival_day, "detect_lead": req.detect_lead,
        "civic_lead": req.civic_lead, "pz_top_prob": req.pz_top_prob,
        "pz_top_cell": req.pz_top_cell, "saved_lives": req.saved_lives,
        "deaths": req.deaths, "peak_infected": req.peak_infected,
        "hosp_overflow_days": req.hosp_overflow_days,
    }

    alert_level = classify_alert_level(req.rt, req.arrival_day, req.hosp_overflow_days)
    tree_result = get_priority_actions(
        rt=req.rt, alert_level=alert_level, civic_lead_days=req.civic_lead,
        arrival_day=req.arrival_day, saved_lives=req.saved_lives, threat=req.threat,
    )

    key = req.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {
            "mode": "decision_tree_only", "alert_level": alert_level,
            "decision_tree": tree_result, "llm_analysis": None,
            "note": "ANTHROPIC_API_KEY 없음 — 의사결정 트리 결과만 반환",
        }

    try:
        from algorithms.ai_inference import run_ai_inference
        result = run_ai_inference(situation, api_key=key)
        result["mode"] = "full_rag_llm"
        return result
    except Exception as e:
        return {
            "mode": "decision_tree_fallback", "alert_level": alert_level,
            "decision_tree": tree_result, "llm_analysis": None, "error": str(e),
        }


@app.get("/api/synthetic-threat/biorxiv", tags=["Stage 0: 합성위협 탐지"])
def synthetic_threat_biorxiv():
    """bioRxiv 프리프린트 검색 — 서버 경유로 브라우저 CORS 차단을 회피."""
    from algorithms.synthetic_threat import fetch_biorxiv
    return {"papers": fetch_biorxiv()}


@app.get("/api/synthetic-threat/who", tags=["Stage 0: 합성위협 탐지"])
def synthetic_threat_who():
    """WHO 발생 동향 — WHO 뉴스 RSS를 발생 키워드로 필터링 (실시간)."""
    from algorithms.synthetic_threat import fetch_who
    return {"items": fetch_who()}


class SyntheticThreatAnalyzeRequest(BaseModel):
    summary: dict = Field(..., description="0단계 스캔 결과 요약 (종합점수, CI, 유전체/역학/인텔 점수 등)")
    api_key: Optional[str] = Field(None, description="Anthropic API 키 (없으면 환경변수)")

@app.post("/api/synthetic-threat/analyze", tags=["Stage 0: 합성위협 탐지"])
def synthetic_threat_analyze(req: SyntheticThreatAnalyzeRequest):
    """0단계 합성위협 탐지 스캔 결과를 Claude로 분석 (설계-탐지 이중성 관점)."""
    key = req.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=422, detail="ANTHROPIC_API_KEY 없음")
    try:
        from algorithms.synthetic_threat import analyze_synthetic_threat
        analysis = analyze_synthetic_threat(req.summary, api_key=key)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/global-watch", tags=["Stage 6: AI 추론"])
def global_watch():
    """
    WHO EMRO/WPRO·Africa CDC·MSF 등 RSS 없는 지역의 신호 갭필링.
    Perplexity(주) → Tavily(폴백) 검색 + Claude 종합 분석.
    키가 없으면 해당 단계는 건너뛰고 사유를 반환.
    """
    from algorithms.global_watch import run_global_watch
    return run_global_watch()


@app.post("/api/ai/triage", tags=["Stage 6: AI 추론"])
def ai_triage(
    rt: float, arrival_day: int, hosp_overflow_days: int = 0,
    civic_lead: int = 0, saved_lives: int = 0, threat: str = "novel",
):
    """빠른 위험 분류 — 의사결정 트리만 사용 (LLM 없이 즉시 응답)."""
    alert_level = classify_alert_level(rt, arrival_day, hosp_overflow_days)
    return get_priority_actions(
        rt=rt, alert_level=alert_level, civic_lead_days=civic_lead,
        arrival_day=arrival_day, saved_lives=saved_lives, threat=threat,
    )

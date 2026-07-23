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
import sys, os, json, secrets
import asyncio
import datetime as dt
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# 원본 엔진 src 경로 추가 (backtest·scorer 재사용)
ENGINE_SRC = Path(__file__).parent.parent / "epiweather-handoff" / "engine" / "src"
sys.path.insert(0, str(ENGINE_SRC))

from fastapi import FastAPI, HTTPException, Depends, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
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
from algorithms.unexplained import scan_unexplained
import db

app = FastAPI(
    title="역병예보 API",
    description="감염병 조기경보 추론 엔진 REST API",
    version="0.1.0",
)
db.init_db()

# ALLOWED_ORIGINS 환경변수로 배포된 프론트엔드 도메인을 추가할 수 있게 함
# (예: "https://epiweather.vercel.app,https://epiweather.kr") — 쉼표로 구분.
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", *_extra_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 쓰기(POST) 엔드포인트 인증 ────────────────────────────────
# 조회(GET)는 대시보드가 공개적으로 보여줘야 하므로 그대로 공개.
# 상태를 바꾸는 POST 엔드포인트만 X-API-Key 헤더로 보호한다.
# EPIWEATHER_API_KEY(또는 EPIWEATHER_API_KEYS)가 설정 안 되어 있으면
# fail-closed(503)로 막는다 — "키가 없으면 조용히 전체 공개"가 되는
# fail-open보다 운영 사고를 막기 쉬움.
#
# 다중 키 지원: EPIWEATHER_API_KEYS="라벨1:키1,라벨2:키2" 형식.
# 향후 고객사별로 키를 발급할 때를 대비한 최소 골격 — 실제 요율제한은
# 아직 안 만듦(고객사가 없는 상태에서 임계값을 정하면 근거 없는 숫자가 됨).
# 지금은 라벨별 호출 이력만 db.api_key_usage에 쌓아서 나중에 정책을 정할
# 근거를 모은다. 기존 단일 EPIWEATHER_API_KEY도 label="default"로 계속 동작.
def _valid_api_keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    single = os.environ.get("EPIWEATHER_API_KEY")
    if single:
        keys[single] = "default"
    for pair in os.environ.get("EPIWEATHER_API_KEYS", "").split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        label, _, key = pair.partition(":")
        if key:
            keys[key] = label.strip() or "unlabeled"
    return keys


def require_api_key(
    request: Request, x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    keys = _valid_api_keys()
    if not keys:
        raise HTTPException(
            status_code=503,
            detail="서버에 EPIWEATHER_API_KEY(또는 EPIWEATHER_API_KEYS)가 설정되지 않아 쓰기 API가 비활성화됨",
        )
    if not x_api_key:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키 (X-API-Key 헤더 필요)")

    matched_label = next(
        (label for key, label in keys.items() if secrets.compare_digest(x_api_key, key)),
        None,
    )
    if matched_label is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키 (X-API-Key 헤더 필요)")

    try:
        db.log_api_key_usage(matched_label, request.url.path)
    except Exception:
        pass  # 사용량 로깅 실패가 실제 요청을 막으면 안 됨
    return matched_label


_auth = [Depends(require_api_key)]


# ── 대시보드 WebSocket ────────────────────────────────────────
# 기존 30초 폴링 대신 실시간 푸시. 수집기(스케줄러)가 새 신호를 쌓을 때마다
# 연결된 클라이언트에 최신 /api/dashboard 페이로드를 브로드캐스트한다.
_ws_clients: set[WebSocket] = set()


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        # 연결 직후 최신 스냅샷을 바로 보내서, 다음 수집 주기까지 안 기다려도
        # 화면을 그릴 수 있게 함(REST 초기 로드와 동등한 경험).
        await websocket.send_json(_build_dashboard())
        while True:
            # 클라이언트가 보내는 메시지는 쓰지 않지만, 연결이 끊기면
            # WebSocketDisconnect가 여기서 발생하도록 계속 대기한다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


async def _broadcast_dashboard() -> None:
    if not _ws_clients:
        return
    payload = _build_dashboard()
    dead: list[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


# ── 자동 수집 스케줄러 ──────────────────────────────────────────
# collector.py는 원래 로컬 PC의 Windows 작업 스케줄러로 무인 실행되도록
# 만들어졌는데, 클라우드(Railway)에는 별도 스케줄러가 없어 배포만 해서는
# 신호가 전혀 쌓이지 않았음. API 프로세스 안에서 백그라운드로 직접 돌려
# 이 문제를 해결한다. EPIWEATHER_SCHEDULER=off 로 끌 수 있음(로컬 개발 시
# 작업 스케줄러와 중복 수집하지 않도록).
_FREE_INTERVAL_SEC   = 3600           # 무료 소스: 1시간마다
_AI_HOUR_UTC         = 21             # AI 갭필링(유료): 하루 1회, UTC 21시(KST 06시)경
_WEEKLY_INTERVAL_SEC = 7 * 24 * 3600  # 기준선·국가지표: 느리게 변하는 데이터라 주간이면 충분
_WEEKLY_STATE_FILE   = Path(__file__).parent / "data" / "last_weekly_run.json"


async def _run_collector(mode: str) -> None:
    import collector
    try:
        if mode == "free":
            await asyncio.to_thread(collector.collect_free_sources)
        elif mode == "ai":
            await asyncio.to_thread(collector.collect_ai_sources)
        await _broadcast_dashboard()
    except Exception as e:
        collector.log_error(f"scheduler_{mode}", e)


def _load_last_weekly_run() -> dt.datetime | None:
    if not _WEEKLY_STATE_FILE.exists():
        return None
    try:
        with open(_WEEKLY_STATE_FILE, encoding="utf-8") as f:
            return dt.datetime.fromisoformat(json.load(f)["last_run"])
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


def _save_last_weekly_run(when: dt.datetime) -> None:
    _WEEKLY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_WEEKLY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_run": when.isoformat()}, f)


async def _run_weekly_job() -> None:
    """
    기준선(collect_baseline)·국가지표(refresh_country_indicators) 갱신.
    컨테이너가 재시작돼도(Railway 등) data/last_weekly_run.json에 마지막 실행
    시각을 남겨서 "7일 지났으면 바로 실행"을 유지한다 — _AI_HOUR_UTC의
    last_ai_run_date는 메모리 변수라 재시작하면 초기화되는 것과 대비됨.
    """
    import collector
    try:
        from algorithms.baseline_collector import collect_baseline
        result = await asyncio.to_thread(collect_baseline)
        collector.log(f"주간 작업: 기준선 갱신 완료 (레코드 {result.get('total_records', 0)}건)")
    except Exception as e:
        collector.log_error("scheduler_weekly_baseline", e)

    try:
        from algorithms.country_indicators import refresh_country_indicators
        result = await asyncio.to_thread(refresh_country_indicators)
        collector.log(
            f"주간 작업: 국가지표 갱신 완료 "
            f"(World Bank {result['worldbank_countries']}개국, OpenFlights {result['openflights_countries']}개국)"
        )
    except Exception as e:
        collector.log_error("scheduler_weekly_country_indicators", e)

    try:
        from algorithms.world_countries import refresh_world_countries
        result = await asyncio.to_thread(refresh_world_countries)
        collector.log(f"주간 작업: 전세계 국가 참조데이터 갱신 완료 ({result['countries_fetched']}개국)")
    except Exception as e:
        collector.log_error("scheduler_weekly_world_countries", e)

    _save_last_weekly_run(dt.datetime.now(dt.timezone.utc))


async def _scheduler_loop() -> None:
    last_ai_run_date: dt.date | None = None
    await _run_collector("free")

    last_weekly = _load_last_weekly_run()
    now = dt.datetime.now(dt.timezone.utc)
    if last_weekly is None or (now - last_weekly).total_seconds() >= _WEEKLY_INTERVAL_SEC:
        await _run_weekly_job()

    while True:
        await asyncio.sleep(_FREE_INTERVAL_SEC)
        await _run_collector("free")

        now = dt.datetime.utcnow()
        if now.hour == _AI_HOUR_UTC and last_ai_run_date != now.date():
            last_ai_run_date = now.date()
            await _run_collector("ai")

        last_weekly = _load_last_weekly_run()
        now_utc = dt.datetime.now(dt.timezone.utc)
        if last_weekly is None or (now_utc - last_weekly).total_seconds() >= _WEEKLY_INTERVAL_SEC:
            await _run_weekly_job()


@app.on_event("startup")
async def _start_scheduler() -> None:
    if os.environ.get("EPIWEATHER_SCHEDULER", "on").lower() == "off":
        return
    asyncio.create_task(_scheduler_loop())


# ── 헬스체크 ─────────────────────────────────────────────────
@app.get("/health", tags=["시스템"])
def health():
    return {"status": "ok", "version": "0.1.0", "engine": "역병예보 추론 엔진 v1"}


def _file_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "updated_at": None, "size_bytes": 0}
    stat = path.stat()
    return {
        "exists": True,
        "updated_at": dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
    }


def _recent_errors(limit: int = 10) -> list[dict]:
    """collector.py가 error_log.txt에 남긴 최근 에러. '<시각> | <출처> | <메시지>' 형식."""
    err_file = Path(__file__).parent / "data" / "error_log.txt"
    if not err_file.exists():
        return []
    with open(err_file, encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    errors = []
    for line in lines:
        parts = line.rstrip("\n").split(" | ", 2)
        if len(parts) == 3:
            errors.append({"at": parts[0], "context": parts[1], "message": parts[2]})
    return errors


@app.get("/api/status", tags=["시스템"])
def status():
    """
    운영 모니터링 — 수집 파이프라인이 살아있는지 한눈에 확인.
    Sentry 등 외부 모니터링 서비스 없이도 "언제 마지막으로 수집됐는지·
    최근 에러가 뭔지·데이터가 얼마나 쌓였는지"를 바로 보기 위한 용도.
    """
    data_dir = Path(__file__).parent / "data"
    err_file = data_dir / "error_log.txt"
    error_count = 0
    if err_file.exists():
        with open(err_file, encoding="utf-8") as f:
            error_count = sum(1 for _ in f)

    last_weekly = _load_last_weekly_run()
    from algorithms.country_risk import discovered_tier2_countries
    from algorithms.source_health import source_health_report
    return {
        "scheduler_enabled": os.environ.get("EPIWEATHER_SCHEDULER", "on").lower() != "off",
        "last_weekly_job_at": last_weekly.isoformat() if last_weekly else None,
        "files": {
            "signals_log":              _file_status(data_dir / "signals_log.jsonl"),
            "baseline_signals":         _file_status(data_dir / "baseline_signals.jsonl"),
            "country_indicators_cache": _file_status(data_dir / "country_indicators_cache.json"),
            "world_countries_cache":    _file_status(data_dir / "world_countries_cache.json"),
        },
        "db_table_counts": db.table_counts(),
        # 최근 30일 내 country_iso3로 새로 발견된, COUNTRIES(Tier-1) 밖 국가 수 —
        # 별칭사전 없이 얼마나 넓게 자동 커버리지가 열렸는지 보여주는 지표(⑱).
        "tier2_countries_discovered": len(discovered_tier2_countries()),
        # 소스별 헬스(㉔) — degraded_sources가 비어있지 않으면 조용히 죽은 소스가
        # 실제로 눈에 보이는 것. 조기경보 시스템의 '조용한 실패'를 막는 핵심 지표.
        "source_health": source_health_report(),
        "recent_errors": _recent_errors(),
        "total_error_count": error_count,
    }


@app.get("/api/admin/api-key-usage", tags=["시스템"], dependencies=_auth)
def api_key_usage(days: int = 30):
    """
    라벨별 API 키 호출 이력 — 대시보드용 공개 데이터가 아니라 운영 데이터라
    다른 GET 엔드포인트와 다르게 인증을 건다(고객사별 사용량은 노출하면 안 됨).
    """
    return {"days": days, "usage": db.api_key_usage_summary(days=days)}


@app.get("/api/admin/db-backup", tags=["시스템"], dependencies=_auth)
def db_backup():
    """
    운영 DB(SQLite) 스냅샷 다운로드 — Railway 같은 컨테이너 배포 환경은 영구
    볼륨을 마운트하지 않으면 재배포할 때 파일시스템이 초기화될 수 있음.
    이러면 예측 트랙레코드·검증 이력 등 시간이 지나야 쌓이는 자산이 전부
    사라질 수 있어(⑲), 이 엔드포인트를 로컬 머신에서 주기적으로 호출해
    타임스탬프 백업을 남기는 걸 권장한다(scripts/backup_db.sh 참고).

    파일을 그대로 복사하지 않고 sqlite3 backup API로 뜨는 이유: WAL 모드에서
    동시 쓰기가 일어나는 중에 파일을 직접 복사하면 손상된 스냅샷이 될 수
    있음 — backup API는 진행 중인 쓰기와 안전하게 분리된 일관 스냅샷을 보장함.
    """
    import sqlite3
    import tempfile

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    tmp_path = Path(tempfile.gettempdir()) / f"epiweather_backup_{stamp}.db"

    src = sqlite3.connect(db.DB_PATH)
    dest = sqlite3.connect(tmp_path)
    with dest:
        src.backup(dest)
    src.close()
    dest.close()

    return FileResponse(
        tmp_path,
        filename=f"epiweather_backup_{stamp}.db",
        media_type="application/octet-stream",
        background=BackgroundTask(lambda: tmp_path.unlink(missing_ok=True)),
    )


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

@app.post("/api/patient-zero/grid", tags=["Stage 0: 발원지"], dependencies=_auth)
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

@app.post("/api/civic-fusion", tags=["Stage 1: 민간 신호"], dependencies=_auth)
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

@app.post("/api/import-day", tags=["Stage 2: 글로벌 유입"], dependencies=_auth)
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

@app.post("/api/seir-simulate", tags=["Stage 5: 방어 시뮬레이션"], dependencies=_auth)
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

@app.post("/api/backtest", tags=["후향 검증"], dependencies=_auth)
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


@app.get("/api/backtest/historical", tags=["후향 검증"])
def backtest_historical():
    """
    실제 발병 이력 기반 백테스트(⑳) — 위 /api/backtest가 합성 데이터로
    "탐지 방법론"을 비교하는 것과 달리, 이건 실제 outbreak_timeline
    milestone(WHO PHEIC 선언 등 진짜 날짜)과 실제 extracted_signals를
    대조해 "아이기론이 실제로 며칠 먼저 알았는가"를 계산한다.
    extracted_signals가 아직 없는 이벤트는 verified=False로 정직하게 표시
    — 합성 데이터로 대신 채우지 않음. 벤치마크(㉕)가 있는 이벤트(코로나 등)는
    블루닷 대비 비교(bluedot_comparison)도 함께 반환한다.
    """
    from algorithms.historical_backtest import backtest_all_known_events
    db.init_db()
    _seed_known_timelines()  # 코로나 등 벤치마크 이벤트가 항상 등록돼 있도록(멱등)
    return backtest_all_known_events()


@app.get("/api/backtest/historical/{event_id}", tags=["후향 검증"])
def backtest_historical_event(event_id: str):
    """특정 발병 이벤트 하나만 실제 이력 기반으로 백테스트."""
    from algorithms.historical_backtest import backtest_event
    db.init_db()
    _seed_known_timelines()
    return backtest_event(event_id)


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
    취약성지수 4요소 중 의료인프라·인구밀도(World Bank)·공항연결성(OpenFlights)은
    실데이터 캐시 확보 시 실측값 사용, 국경이동량은 UNWTO 유료라 계속 추정 시드값.
    각 응답의 vulnerability_source(real_data|seed_fallback)로 실측 여부 확인 가능.
    """
    return rank_countries()


@app.get("/api/risk-index/{country}", tags=["GAI"])
def risk_index_country(country: str):
    """특정 국가 상세. country는 ISO 3166-1 alpha-3 코드(COD, KOR, USA 등).
    Tier-1(큐레이션 14개국)뿐 아니라 최근 실제 신호가 있는 Tier-2(자동발견)
    국가도 조회 가능 — 신호 근거가 전혀 없는 코드만 404."""
    try:
        return compute_country_risk(country)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"지원하지 않는 국가 ID이거나 최근 신호가 없음. Tier-1 목록: {list(COUNTRIES)}",
        )


@app.get("/api/risk-quantification", tags=["GAI"])
def risk_quantification():
    """
    팬데믹 리스크 계량화(㉓) — BlueDot의 '탐지'와 Metabiota의 '계량화' 사이의
    빈 시장. 이미 수집된 실제 신호를 국가별 노출 지수(exposure_index, 0~100)로
    합성하고, 상대 백분위와 실증 근거(실제 이력 백테스트로 검증된 선행탐지
    사례 수)를 함께 준다. is_probability=False — 절대 발생 확률이 아니라 비교용
    모델 지표임을 응답에 못박아, 보험·금융이 자체 기저율로 재보정해 쓰게 한다.
    """
    from algorithms.risk_quantification import quantify_portfolio
    return quantify_portfolio()


@app.get("/api/risk-quantification/{country}", tags=["GAI"])
def risk_quantification_country(country: str):
    """특정 국가의 노출 지수 상세(구성요소·가중치·정직성 플래그 포함)."""
    from algorithms.risk_quantification import quantify_country_exposure
    try:
        return quantify_country_exposure(country)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"지원하지 않는 국가 ID이거나 최근 신호가 없음. Tier-1 목록: {list(COUNTRIES)}",
        )


@app.get("/api/threats", tags=["GAI"])
def threats():
    """
    현재 진행 중인 위협 — NLP 구조화 추출(⑦) 결과를 disease 기준으로 병합한
    중복제거 이벤트 목록(⑩). 같은 사건을 출처 여러 곳이 따로 보고해도
    하나로 합쳐 신뢰도가중 평균 점수를 매긴다. 이 경로는 결정론적(질병명
    기준)이라 매 대시보드 로드마다 빠르게 동작(clustering_method 참고).
    """
    return {"events": dedupe_events()}


@app.get("/api/threats/semantic", tags=["GAI"])
def threats_semantic():
    """
    교차언어 의미 클러스터링(㉚) — Claude가 여러 언어·표기의 신호를 '뜻'으로
    묶어, 질병명이 문자로 안 겹쳐도(예: 태국어 "람파 정체불명 폐렴" vs 영어
    "unknown pneumonia northern Thailand") 같은 실제 발병이면 하나로 병합한다.
    EIOS/EMM의 다국어 클러스터링을 LLM으로 흉내낸 것. ANTHROPIC_API_KEY가 없거나
    호출 실패 시 결정론적 방식으로 자동 폴백 — 각 이벤트의 clustering_method로
    실제 어느 방식이 쓰였는지 정직하게 표시한다(비용·지연이 있어 별도 엔드포인트).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    events = dedupe_events(api_key=api_key)
    method = events[0]["clustering_method"] if events else (
        "semantic_llm" if api_key else "disease_name_fallback"
    )
    return {
        "events": events,
        "clustering_method": method,
        "note": None if api_key else "ANTHROPIC_API_KEY 미설정 — 결정론적(질병명) 폴백으로 동작",
    }


@app.get("/api/unexplained-signals", tags=["GAI"])
def unexplained_signals():
    """
    설명 불가 신호 탐지 — NLP 구조화추출(⑦) 결과 중 알려진 질병 별칭에 안
    걸리는 신호를 즉시경보로 표시. 조건1(병원방문 급증)은 데이터 소스가
    없어 측정 불가 — caveat에 명시.
    """
    return scan_unexplained()


# ── 예측 검증 ─────────────────────────────────────────────────
class PredictionCreate(BaseModel):
    country: str = Field(..., description="대상 국가")
    disease: str = Field(..., description="예측 질병")
    risk_score: float = Field(..., description="예측 위험도 (0~100)")
    basis: list[str] = Field(..., min_length=1, description="예측 근거 (최소 1개, 권장 3개)")

@app.post("/api/predictions", tags=["예측 검증"], dependencies=_auth)
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

@app.post("/api/predictions/{prediction_id}/verify", tags=["예측 검증"], dependencies=_auth)
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

@app.post("/api/ai/infer", tags=["Stage 6: AI 추론"], dependencies=_auth)
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

@app.post("/api/synthetic-threat/analyze", tags=["Stage 0: 합성위협 탐지"], dependencies=_auth)
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


# ── 과거 기준선 데이터 수집 (Phase 2 ⑮) ──────────────────────
@app.post("/api/baseline/collect", tags=["기준선"], dependencies=_auth)
def baseline_collect(months_back: int = 24, years_back: int = 5, weeks_back: int = 104):
    """
    Wikipedia 최대 24개월 + KDCA 최대 5년치 + CDC NWSS(하수감시) 최대 24개월 +
    브라질 InfoDengue 최대 104주 역사 데이터를 data/baseline_signals.jsonl에 저장.
    GAI 이상도 계산의 역사적 기준선으로 쓰임. KDCA는 환경변수 KDCA_API_KEY가 있어야 수집됨.
    """
    from algorithms.baseline_collector import collect_baseline
    return collect_baseline(months_back=months_back, years_back=years_back, weeks_back=weeks_back)


@app.post("/api/country-indicators/refresh", tags=["기준선"], dependencies=_auth)
def country_indicators_refresh():
    """
    국가 취약성 지수 실데이터 갱신 — World Bank(병상수·인구밀도) + OpenFlights
    (공항연결성) 조회해 data/country_indicators_cache.json에 저장.
    /api/risk-index의 vulnerability_source가 real_data로 바뀌는 기반 데이터.
    """
    from algorithms.country_indicators import refresh_country_indicators
    return refresh_country_indicators()


@app.get("/api/country-indicators/status", tags=["기준선"])
def country_indicators_status():
    """국가 지표 캐시 현황 — 갱신 시각과 실데이터 확보된 국가 수."""
    from algorithms.country_indicators import load_country_indicators, CACHE_FILE
    import json as _json
    countries = load_country_indicators()
    if not CACHE_FILE.exists():
        return {"status": "없음", "count": 0, "hint": "POST /api/country-indicators/refresh 실행 필요"}
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = _json.load(f)
    return {
        "status": "있음",
        "updated_at": cache.get("updated_at"),
        "countries_with_real_data": len(countries),
        "countries": list(countries.keys()),
    }


@app.post("/api/world-countries/refresh", tags=["기준선"], dependencies=_auth)
def world_countries_refresh():
    """
    전세계 국가 참조데이터(이름·수도 위경도) 갱신 — World Bank 국가목록 API 조회해
    data/world_countries_cache.json에 저장. Tier-2(자동발견) 국가의 표시명·지도
    좌표가 여기서 채워짐(⑱).
    """
    from algorithms.world_countries import refresh_world_countries
    return refresh_world_countries()


@app.get("/api/world-countries/status", tags=["기준선"])
def world_countries_status():
    """전세계 국가 참조데이터 캐시 현황 — 갱신 시각과 확보된 국가 수."""
    from algorithms.world_countries import load_world_countries, CACHE_FILE
    import json as _json
    countries = load_world_countries()
    if not CACHE_FILE.exists():
        return {"status": "없음", "count": 0, "hint": "POST /api/world-countries/refresh 실행 필요"}
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = _json.load(f)
    return {
        "status": "있음",
        "updated_at": cache.get("updated_at"),
        "countries_count": len(countries),
    }


# ── 발병 타임라인 (Phase 2 ㉑) ──────────────────────────────
@app.get("/api/timeline", tags=["타임라인"])
def timeline_list():
    """
    등록된 발병 이벤트 목록 (event_id별 최신 마일스톤 날짜 + 마일스톤 수).
    """
    return {"events": db.list_timeline_events()}


@app.get("/api/timeline/current", tags=["타임라인"])
def timeline_current():
    """
    현재 진행 중인 위협 타임라인 — 인수인계서에 기록된 에볼라 PHEIC 등
    알려진 이벤트의 시드 데이터를 포함해 반환.
    """
    db.init_db()
    _seed_known_timelines()
    return {"events": db.list_timeline_events()}


@app.get("/api/timeline/{event_id}", tags=["타임라인"])
def timeline_event(event_id: str):
    """특정 발병 이벤트의 전체 타임라인 (날짜순)."""
    result = db.get_timeline(event_id)
    if not result["milestones"]:
        raise HTTPException(status_code=404, detail=f"이벤트 없음: {event_id}")
    return result


class TimelineMilestone(BaseModel):
    event_id:    str = Field(..., description="이벤트 식별자 (예: ebola_drc_2026)")
    event_name:  str = Field(..., description="이벤트 이름")
    event_date:  str = Field(..., description="날짜 YYYY-MM-DD")
    milestone:   str = Field(..., description="마일스톤 키 (예: who_pheic, first_report)")
    description: str = Field(..., description="설명")
    source:      Optional[str] = Field(None)
    source_type: Optional[str] = Field(None, description="who | cdc | media | ai_detected")

@app.post("/api/timeline", tags=["타임라인"], dependencies=_auth)
def timeline_add(req: TimelineMilestone):
    """발병 타임라인에 마일스톤 추가 (같은 milestone은 갱신)."""
    return db.upsert_timeline_event(
        req.event_id, req.event_name, req.event_date,
        req.milestone, req.description, req.source, req.source_type,
    )


def _seed_known_timelines():
    """인수인계서 Part8 — 현재 진행 중인 발병의 시드 데이터."""
    known = [
        ("ebola_drc_2026", "에볼라 DRC 2026", [
            ("2026-05-09", "msf_first_alert",   "MSF 현장 첫 경보", "MSF 보고서", "media"),
            ("2026-05-15", "drc_official",       "DRC 보건부 공식 선언", "DRC Ministry of Health", "who"),
            ("2026-05-16", "who_pheic",          "WHO PHEIC 선언", "WHO DON", "who"),
            ("2026-05-17", "wiki_spike",         "Wikipedia 영어판 조회수 급증", "Wikimedia API", "ai_detected"),
            ("2026-06-25", "status_update",      "확진 896명·사망 232명", "WHO Situation Report", "who"),
        ]),
        ("mers_saudi_2026", "MERS 사우디아라비아 2026", [
            ("2026-01-01", "year_start",         "2026년 감시 시작", "WHO DON591", "who"),
            ("2026-06-25", "status_update",      "2026년 확진 11건·사망 2명 / 리야드 병원 집단감염 7건", "WHO DON591", "who"),
        ]),
        ("dengue_2026", "뎅기열 글로벌 2026", [
            ("2026-06-25", "status_update",      "방글라데시 1,870명 / 태국 3,191명 / 전세계 50만+", "WHO/ECDC", "who"),
        ]),
        # 코로나19 초기 — BlueDot 대비 벤치마크(㉕)용 실측 타임라인. 날짜는 공개
        # 문헌 인용(WHO COVID-19 타임라인). first_report는 우한 비정상 폐렴
        # 클러스터 최초 보도, who_pheic는 국제공중보건위기 선언.
        ("covid19_wuhan_2019", "코로나19 우한 초기 2019-2020", [
            ("2019-12-30", "first_report",       "우한 비정상 폐렴 클러스터 최초 보도(ProMED 등)", "ProMED/미디어", "media"),
            ("2019-12-31", "official_declaration","중국, WHO에 우한 폐렴 클러스터 통보", "WHO 타임라인", "who"),
            ("2020-01-09", "who_statement",       "WHO 신종 코로나바이러스 첫 공개 성명", "WHO", "who"),
            ("2020-01-30", "who_pheic",           "WHO 국제공중보건위기(PHEIC) 선언", "WHO", "who"),
            ("2020-03-11", "who_pandemic",        "WHO 팬데믹 선언", "WHO", "who"),
        ]),
    ]
    for event_id, event_name, milestones in known:
        for event_date, milestone, description, source, source_type in milestones:
            db.upsert_timeline_event(event_id, event_name, event_date, milestone, description, source, source_type)


# ── Phase 3 ──────────────────────────────────────────────────
# ── 대시보드 6개 화면 통합 API ────────────────────────────────
def _build_dashboard() -> dict:
    """
    대시보드 6개 화면 데이터를 한 번에 반환.

    화면1: 글로벌 위험 지도    → screen1_global_map
    화면2: 실시간 이벤트 스트림 → screen2_event_stream
    화면3: 발병 타임라인       → screen3_timeline
    화면4: 국가별 위험 랭킹    → screen4_country_ranking
    화면5: AI 예측 패널        → screen5_forecast
    화면6: 경보 센터           → screen6_alert_center

    GET /api/dashboard와 /ws/dashboard 브로드캐스트가 이 함수 하나를 공유함
    (계산 로직 이중 관리 방지).
    """
    import datetime as dt
    from algorithms.gai import compute_gai
    from algorithms.alerts import refresh_alerts
    from algorithms.country_risk import rank_countries
    from algorithms.event_dedup import dedupe_events
    from algorithms.forecast_engine import forecast_summary
    from algorithms.anomaly_engine import compute_anomalies
    from algorithms.knowledge_graph import match_active_signals

    today = dt.date.today().isoformat()
    country_data  = rank_countries()
    events        = dedupe_events()
    gai_data      = compute_gai()
    forecast_data = forecast_summary()
    anomalies     = compute_anomalies()
    active_metrics = [a["metric"] for a in anomalies["anomalies"]]
    chain_warnings = match_active_signals(active_metrics)
    alert_data    = refresh_alerts(today)
    timeline_events = db.list_timeline_events()

    return {
        "generated_at": dt.datetime.now().isoformat(),
        "screen1_global_map": {
            "gai": gai_data["gai"],
            "tier": gai_data["tier"],
            "countries": country_data["countries"][:50],
        },
        "screen2_event_stream": {
            "events": events[:20],
            "total":  len(events),
        },
        "screen3_timeline": {
            "active_outbreaks": timeline_events,
        },
        "screen4_country_ranking": {
            "top20": country_data["countries"][:20],
        },
        "screen5_forecast": {
            "score_7d":       forecast_data.get("score_7d"),
            "score_14d":      forecast_data.get("score_14d"),
            "tier_7d":        forecast_data.get("tier_7d", "정상"),
            "tier_14d":       forecast_data.get("tier_14d", "정상"),
            "chain_warnings": chain_warnings[:5],
            "top_alerts":     forecast_data.get("top_alerts", [])[:5],
            # "우리가 X% 맞췄다"를 실제로 보여주는 부분 — country_risk.py의
            # log_notable_predictions()가 매시간 자동 기록한 예측 중 검증된 것들.
            "prediction_track_record": {
                "accuracy": db.accuracy_stats(),
                "recent_verified": db.list_predictions(verified_only=True)[:5],
            },
        },
        "screen6_alert_center": {
            "dashboard":    alert_data["dashboard"],
            "tier_summary": alert_data["tier_summary"],
        },
    }


@app.get("/api/dashboard", tags=["대시보드"])
def dashboard():
    return _build_dashboard()


@app.post("/api/digital-twin/simulate", tags=["Phase3"], dependencies=_auth)
def digital_twin_simulate(
    origin: str = "Kinshasa",
    threat: str = "novel",
    days: int = 90,
):
    """
    디지털 트윈 — 다도시 전파 시뮬레이션.
    origin에서 발생한 감염이 항공 네트워크를 타고 서울까지 도달하는 경로·일정 예측.
    origin: Kinshasa, Bangkok, Riyadh 등 / threat: flu | novel | severe
    """
    from algorithms.digital_twin import simulate_spread
    if threat not in ("flu", "novel", "severe"):
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")
    return simulate_spread(origin=origin, threat=threat, days=min(days, 180))


@app.get("/api/cities", tags=["Phase3"])
def cities_risk():
    """
    도시 단위 위험도 — 국가 위험도 × 공항연결성·왕래량·인프라 가중치.
    인천공항 직항 노선 여부와 연간 탑승객 수 반영.
    """
    from algorithms.geo_resolution import rank_cities
    from algorithms.country_risk import rank_countries
    country_data = rank_countries()
    country_risks = {c["country"]: c["risk_score"] for c in country_data["countries"]}
    return {"cities": rank_cities(country_risks)}


@app.get("/api/cities/{city}/inflow", tags=["Phase3"])
def city_inflow(city: str):
    """인천공항 → 서울 유입 경로 분석. city: Bangkok, Dubai, Kinshasa 등"""
    from algorithms.geo_resolution import compute_city_risk, get_korea_inflow_path, CITY_RISK_DATA
    from algorithms.country_risk import rank_countries
    country_data = rank_countries()
    country_risks = {c["country"]: c["risk_score"] for c in country_data["countries"]}
    # country_risks는 국가ID로 키가 잡혀있어 city명으로는 조회가 안 됨 —
    # 도시→국가 매핑을 먼저 거쳐야 실제 국가위험도가 들어감 (안 거치면 항상 폴백 50.0)
    city_country = CITY_RISK_DATA.get(city, {}).get("country")
    country_risk_score = country_risks.get(city_country, 50.0)
    city_data = compute_city_risk(city, country_risk_score)
    if "error" in city_data:
        raise HTTPException(status_code=404, detail=city_data["error"])
    return get_korea_inflow_path(city, city_data["city_risk"])


@app.get("/api/profiles", tags=["Phase3"])
def profiles_list():
    """기업 고객 맞춤 프로파일 목록 — airline, insurance, school, military, hospital, kdca."""
    from algorithms.customer_profiles import PROFILES
    return {
        "profiles": [
            {"id": k, "name": v["name"], "example": v["example"],
             "threshold": v["alert_threshold"], "description": v["description"]}
            for k, v in PROFILES.items()
        ]
    }


@app.get("/api/profiles/{profile_id}/risk", tags=["Phase3"])
def profile_risk(profile_id: str):
    """
    특정 프로파일 맞춤 위험도.
    현재 이상 신호 + 7일 예측을 프로파일 필터로 걸러서 반환.
    """
    from algorithms.customer_profiles import filter_risk_for_profile
    from algorithms.anomaly_engine import compute_anomalies
    from algorithms.forecast_engine import forecast_summary
    anomalies = compute_anomalies()["anomalies"]
    forecast  = forecast_summary()
    return filter_risk_for_profile(profile_id, anomalies, forecast)


@app.get("/api/forecast", tags=["Phase3"])
def forecast():
    """
    7·14일 위험도 예측 — 선형회귀 + 지수평활 앙상블.
    모든 신호원 시계열에서 7일·14일 후 위험도 점수 계산.
    데이터가 쌓일수록 정확도 상승.
    """
    from algorithms.forecast_engine import forecast_summary
    return forecast_summary()


@app.get("/api/forecast/detail", tags=["Phase3"])
def forecast_detail():
    """신호원별 상세 예측값 (delta: 현재 대비 점수 변화량)."""
    from algorithms.forecast_engine import forecast_all_metrics
    return forecast_all_metrics()


@app.get("/api/knowledge-graph", tags=["Phase3"])
def knowledge_graph_all():
    """질병 지식 그래프 전체 — 질병별 원인-결과 인과 체인 + 한국 유입 경로."""
    from algorithms.knowledge_graph import get_disease_graph
    return get_disease_graph()


@app.get("/api/knowledge-graph/{disease}", tags=["Phase3"])
def knowledge_graph_disease(disease: str):
    """특정 질병의 인과 체인. disease: H5N1, Ebola, MERS, Dengue, Novel"""
    from algorithms.knowledge_graph import get_disease_graph
    return get_disease_graph(disease)


@app.get("/api/knowledge-graph/{disease}/verify", tags=["Phase3"])
def knowledge_graph_verify(disease: str):
    """
    지식그래프의 lead_days(손으로 추정한 값)를 outbreak_timeline 실측
    마일스톤과 비교. 발병 사례가 쌓일수록 이 그래프 자체가 정확해지는 게
    목표 — 경쟁사가 복제 못 하는 건 알고리즘이 아니라 이렇게 축적된
    실측 검증 이력임.
    """
    from algorithms.knowledge_graph import verify_chain_lead_time
    return verify_chain_lead_time(disease)


@app.get("/api/knowledge-graph-active", tags=["Phase3"])
def knowledge_graph_active():
    """
    현재 이상 탐지된 신호와 지식 그래프를 매핑.
    "어떤 인과 체인이 지금 활성화됐는가" 경고 반환.
    """
    from algorithms.anomaly_engine import compute_anomalies
    from algorithms.knowledge_graph import match_active_signals
    anomalies = compute_anomalies()
    active = [a["metric"] for a in anomalies["anomalies"]]
    return {"active_metrics": active, "chain_warnings": match_active_signals(active)}


@app.get("/api/behavioral", tags=["Phase3"])
def behavioral():
    """
    행동 변화 데이터 — HIRA 약품 처방 건수 + 서울 응급실 포화도.
    HIRA_API_KEY, SEOUL_OPEN_DATA_KEY 환경변수 필요 (둘 다 무료 발급).
    키 없으면 상태와 발급 안내 반환.
    """
    from algorithms.behavioral_data import get_behavioral_signal
    return get_behavioral_signal()


@app.get("/api/anomaly-engine", tags=["Phase2"])
def anomaly_engine():
    """
    이상 신호 탐지 엔진 — (오늘값-30일평균)/30일평균 방식으로 모든 신호원 이상도 계산.
    임계값(50점) 이상 항목 목록 + 증상 클러스터(질병명 없이 패턴 탐지) 반환.
    """
    from algorithms.anomaly_engine import compute_anomalies
    return compute_anomalies()


@app.get("/api/extra-sources", tags=["Phase2"])
def extra_sources():
    """
    추가 데이터 소스 — medRxiv 감염병 프리프린트 수, Google Trends 전세계/한국.
    pytrends 설치 시 Google Trends 활성화. 미설치 시 null 반환.
    """
    from algorithms.extra_sources import get_extra_signals
    return get_extra_signals()


@app.get("/api/mobility", tags=["Phase2"])
def mobility():
    """
    이동성 신호 — OpenSky API로 주요 발병국 공항 24시간 항공편 수 조회.
    항공편 급감 = 해당 지역 유행 간접 신호. 무료, 인증 불필요.
    """
    from algorithms.mobility import fetch_mobility_signals
    return fetch_mobility_signals()


@app.get("/api/supply-chain", tags=["Phase2"])
def supply_chain():
    """
    공급망 신호 — 해열제·마스크·산소발생기 등 의약품 수요 급증 감지.
    네이버 DataLab 트렌드 기반. NAVER_CLIENT_ID/SECRET 필요.
    2003 SARS 선행 사례: 해열제 품절이 공식 발표 11일 전.
    """
    from algorithms.supply_chain import get_supply_signal
    return get_supply_signal()


@app.get("/api/local-news", tags=["Phase2"])
def local_news():
    """
    현지어 뉴스 RSS — 스와힐리어·프랑스어·태국어·베트남어 감염병 키워드 감지.
    영어 번역 전에 감지. hit_ratio가 높을수록 현지 감염병 보도 활발.
    """
    from algorithms.local_news import fetch_all_local_news
    return fetch_all_local_news()


@app.get("/api/animal-signals", tags=["Phase2"])
def animal_signals():
    """
    WAHIS(세계동물보건기구) 동물질병 신호.
    30일 내 발병 건수, 감시 대상 질병 활성 수, WOAH RSS 항목 수.
    WAHIS_API_KEY 환경변수가 있으면 전체 API, 없으면 RSS로만 수집.
    """
    from algorithms.wahis import get_animal_signal
    return get_animal_signal()


@app.get("/api/genomic-variants", tags=["Phase2"])
def genomic_variants():
    """
    Nextstrain 실시간 유전체 계통(clade) 추적 — SARS-CoV-2/엠폭스/RSV-A.
    최근 60일 구간에 이전 60일 구간엔 없던 신규 계통이 등장했는지, 우세 계통
    구성비를 반환. 무료·인증 불필요. 빌드가 오래 갱신 안 됐으면 available=False.
    """
    from algorithms.genomic_variants import get_genomic_variant_signals
    return get_genomic_variant_signals()


@app.get("/api/social-signal", tags=["Phase2"])
def social_signal():
    """
    Mastodon 실시간 SNS 신호 — 질병별 해시태그(ebola/mpox/birdflu 등) 최근
    7일 게시량과 직전 수집 회차 대비 급변 여부. 무료·인증 불필요.
    (트위터/X는 유료화, 레딧 공개 JSON은 403으로 막혀있어 실측으로 확인된
    유일한 접근 가능 무료 실시간 SNS 소스 — mastodon.social 단일 인스턴스 표본)
    """
    from algorithms.social_signal import get_social_signal
    return get_social_signal()


@app.get("/api/groq-pulse", tags=["Phase2"])
def groq_pulse():
    """
    Groq compound-beta(웹서치 내장) 기반 실시간 발병 뉴스 체크.
    Perplexity/Tavily(유료·AI 갭필링 단계 전용)와 달리 무료 티어라
    free_sources 수집(매시간)에 포함. GROQ_API_KEY 필요.
    """
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY 환경변수 없음")
    from algorithms.groq_watch import fetch_groq_pulse
    result = fetch_groq_pulse(key)
    if result is None:
        raise HTTPException(status_code=502, detail="Groq 응답 파싱 실패")
    return result


@app.get("/api/baseline/status", tags=["기준선"])
def baseline_status():
    """기준선 파일 현황 — 저장된 레코드 수와 최신/최고 타임스탬프."""
    from algorithms.baseline_collector import load_baseline_records
    records = load_baseline_records()
    if not records:
        return {"status": "없음", "count": 0, "hint": "POST /api/baseline/collect 실행 필요"}
    timestamps = [r.get("_logged_at", "") for r in records if r.get("_logged_at")]
    return {
        "status": "있음",
        "count": len(records),
        "oldest": min(timestamps) if timestamps else None,
        "newest": max(timestamps) if timestamps else None,
        "wiki_records": sum(1 for r in records if r.get("_source") == "wikipedia_monthly"),
        "kdca_records": sum(1 for r in records if r.get("_source") == "kdca_annual"),
    }


# ── Sentinel + Verification 2층 구조 (Phase 2 ⑭) ────────────
@app.get("/api/sentinel/status", tags=["Sentinel"])
def sentinel_status():
    """
    Sentinel 대기열 현황 — pending/confirmed/dismissed 건수와 최신 목록.
    Sentinel은 spike_ratio >= 2.0인 신호를 자동 탐지해 쌓는다.
    """
    from algorithms.sentinel import get_sentinel_status
    return get_sentinel_status()


@app.get("/api/sentinel/reliability", tags=["Sentinel"])
def sentinel_reliability(min_samples: int = 3):
    """
    지표(layer+metric)별 오탐율 전체 리포트 — 시스템이 스스로 "이 신호는
    못 믿는다"를 검증 이력으로 드러낸다. negative_space.py의
    UNRELIABLE_METRICS·SEASONAL_METRICS(사람이 로그 보고 하드코딩한 예외
    목록)를 앞으로 이 리포트가 먼저 가리켜줄 수 있음 — 실제 반영은 여전히
    사람이 판단(자동 제외는 진짜 신호를 스스로 꺼버릴 위험이 있어 안 함).
    """
    return {"metrics": db.metric_reliability_report(min_samples=min_samples)}


@app.post("/api/sentinel/scan", tags=["Sentinel"], dependencies=_auth)
def sentinel_scan():
    """
    즉시 스파이크 스캔 실행 — signals_log.jsonl을 읽어 기준선 2배 이상 급등 탐지.
    탐지 결과를 sentinel_queue에 upsert. 5분 이내 응답 목표.
    """
    from algorithms.sentinel import scan_spikes
    spikes = scan_spikes()
    return {"detected": len(spikes), "spikes": spikes}


@app.post("/api/sentinel/verify", tags=["Sentinel"], dependencies=_auth)
def sentinel_verify(max_items: int = 10):
    """
    pending 항목을 Perplexity → Tavily 순서로 검증.
    키가 없으면 안내 메시지 반환. 30~60분 주기로 실행 권장.
    """
    from algorithms.verification import verify_pending
    return verify_pending(max_items=max_items)


@app.post("/api/sentinel/{sentinel_id}/verify", tags=["Sentinel"], dependencies=_auth)
def sentinel_manual_verify(
    sentinel_id: int,
    status: str,
    evidence: Optional[str] = None,
    confidence: Optional[float] = None,
):
    """수동 검증 — status는 confirmed | dismissed."""
    if status not in ("confirmed", "dismissed"):
        raise HTTPException(status_code=422, detail="status는 confirmed | dismissed 중 하나")
    db.update_sentinel_verification(sentinel_id, status, evidence, confidence, verified_by="human")
    rows = db.list_sentinel_queue(limit=1)
    match = next((r for r in db.list_sentinel_queue() if r["id"] == sentinel_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="sentinel_id 없음")
    return match


@app.post("/api/ai/triage", tags=["Stage 6: AI 추론"], dependencies=_auth)
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

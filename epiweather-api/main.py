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
    except Exception as e:
        # 로깅 실패가 실제 요청을 막으면 안 된다(원래 의도 유지). 다만 조용히
        # 넘기면 안 된다 — 이 표는 나중에 제휴사·개발자에게 **비용을 청구할 근거**다.
        # DB가 잠겨 일주일치 사용량이 통째로 안 남아도 아무도 모르면, 그건 장부가
        # 비는 것이다. 청구서를 못 쓰거나, 더 나쁘게는 틀린 청구서를 쓰게 된다.
        _log_error(f"API 사용량 기록 실패({matched_label} → {request.url.path}): "
                   f"{type(e).__name__}: {str(e)[:150]}")
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
# AI 갭필링 마지막 실행일. 메모리 변수로만 두면 재배포마다 초기화돼 같은 날
# 유료 AI가 두 번 돈다(아래 _load_last_ai_run 주석 참고).
_AI_STATE_FILE       = Path(__file__).parent / "data" / "last_ai_run.json"


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


async def _run_alert_cycle() -> None:
    """수집 직후 경보를 계산하고, 신규 critical/high를 사람에게 내보낸다.

    ★ 왜 이 함수가 2026-09-19에야 생겼나 ★
    캡틴: "왜 질병이 퍼지고 있는데 아이기론은 보고를 안해!?"

    경보 엔진(alerts.refresh_alerts)은 처음부터 있었고, 텔레그램 발송도
    그 안에 붙어 있었다. 없던 건 **그걸 부르는 사람**이다. 스케줄러가 매시간
    부르는 건 수집기뿐이었고, refresh_alerts는 누가 /api/alerts·/api/dashboard를
    열 때와 하루 1회 일일 브리핑 안에서만 돌았다. 그나마 브리핑 쪽은
    `try/except: alerts = []`로 감싸여 있어 실패해도 조용하다.

    즉 **수집기가 급증을 잡아도 아무도 대시보드를 안 열면 경보가 사람에게
    안 갔다.** 이 리포에서 반복된 실패 유형 그대로다 — 층은 다 만들어놨는데
    아무도 안 부른다(예측 자동 채점도 같은 이유로 성적표가 0건이었다).

    비용: refresh_alerts가 부르는 층은 전부 로컬 파일·DB 계산이고, 유일하게
    바깥에 나가는 무역 스캔(UN 18회)은 6시간 캐시가 있어 하루 4회로 묶인다.
    """
    import collector
    try:
        from algorithms.alerts import (
            already_notified_line, negative_space_line, refresh_alerts, retired_alerts_line,
            summary_line, undetermined_alerts_line,
        )
        result = await asyncio.to_thread(refresh_alerts)
        collector.log(f"🚨 경보 주기: {summary_line(result)}")
        retired_line = retired_alerts_line(result)
        if retired_line:
            collector.log(retired_line)
        undetermined_line = undetermined_alerts_line(result)
        if undetermined_line:
            collector.log(undetermined_line)
        already_line = already_notified_line(result)
        if already_line:
            collector.log(already_line)
        ns_line = negative_space_line(result)
        if ns_line:
            collector.log(ns_line)
        from algorithms.comtrade_signals import trade_scan_line
        collector.log(trade_scan_line())
    except Exception as e:
        collector.log_error("scheduler_alerts", e)


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


def _load_last_ai_run() -> dt.date | None:
    """AI 갭필링 마지막 실행일(UTC). 주간작업(_load_last_weekly_run)과 같은 패턴.

    왜 파일로 남기는가: 예전엔 스케줄러 루프의 지역변수(last_ai_run_date)로만
    들고 있어서 **재배포할 때마다 초기화**됐다. 그 상태로 아래 '따라잡기'를
    허용하면 배포 직후 같은 날 유료 AI가 한 번 더 돈다.
    """
    if not _AI_STATE_FILE.exists():
        return None
    try:
        with open(_AI_STATE_FILE, encoding="utf-8") as f:
            return dt.date.fromisoformat(json.load(f)["last_run_date"])
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


def _save_last_ai_run(day: dt.date) -> None:
    try:
        _AI_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_AI_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_run_date": day.isoformat()}, f)
    except OSError as e:
        # 저장 실패를 조용히 넘기면 다음 틱에 또 돌아 유료 AI가 중복 호출된다.
        _log_error(f"AI 실행일 저장 실패({day}): {type(e).__name__}: {e}")


async def _run_bulletin_collection() -> None:
    """WHO 상황보고서 자동 수집 — 하루 1회 확인, 새 회차가 있을 때만 파싱.

    확인 자체는 IRIS API 호출 몇 번이라 사실상 공짜다. 비용은 표 추출(회차당 VLM
    4회 호출)에 걸려 있는데, 이미 적재한 회차는 PDF를 열지도 않으므로 새 보고서가
    없는 날은 비용이 0이다. 보고서는 주 1회 나오므로 실제 파싱도 주 1회다.
    NVIDIA_API_KEY가 없으면 조용히 건너뛴다(키 없는 환경에서 로그만 더럽히지 않게)."""
    import collector

    if not os.environ.get("NVIDIA_API_KEY"):
        return
    try:
        from algorithms.bulletin_collect import collect_new_reports
        result = await asyncio.to_thread(collect_new_reports, db)
        if result.get("parsed"):
            collector.log(
                f"WHO 상황보고서: 새 회차 {result['parsed']}건 파싱, "
                f"신호 {result['inserted']}건 적재 "
                f"(기존 {result['skipped_existing']}건은 건너뜀)"
            )
            await _broadcast_dashboard()
    except Exception as e:
        collector.log_error("scheduler_bulletin", e)


async def _run_nowcast_maintenance() -> None:
    """Tier 2 학습셋 백필 — 커버리지가 찰 때까지만 조금씩, 차면 스스로 멈춘다.

    GDELT 속도제한 탓에 16건을 한 번에 못 채운다(실측 커버리지 38~56%). 그래서
    회차당 4건씩만 시도하고 나머지는 다음 날로 미룬다. 이미 채운 사건은 GDELT를
    아예 안 부르므로 **기준을 넘긴 뒤에는 비용이 0이다**.
    새로 채운 게 있을 때만 재학습한다 — 같은 데이터로 반복 학습할 이유가 없다."""
    import collector

    try:
        from algorithms.nowcast_backfill import maintain
        result = await asyncio.to_thread(maintain, 4)
        if result.get("action") == "backfilled":
            bf = result["backfill"]
            training = result.get("training") or {}
            collector.log(
                f"Tier2 백필: 신호 {bf['signals_created']}건 추가, "
                f"커버리지 {bf['event_coverage']:.0%}"
                f"({bf['events_covered']}/{len(bf['per_event_signals'])})"
                f"{' — 재학습 완료' if training.get('trained') else ''}"
                f"{', 다음 회차로 ' + str(len(bf.get('deferred_to_next_run', []))) + '건 이월' if bf.get('deferred_to_next_run') else ''}"
            )
    except Exception as e:
        collector.log_error("scheduler_nowcast_backfill", e)


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

    # ── 기준 스냅샷 갱신 (2026-09-04) ────────────────────────────────
    # 발할라의 두 축(백신 공급·국가 역량)은 정적 파일에 얹혀 있는데, 갱신
    # 스크립트를 **아무도 안 불렀다.** 그래서 파일이 2026-09-02 에 멈춘 채
    # /api/status 는 계속 available: true 로 답했다. 묵은 것만 새로 받는다 —
    # 안 바뀐 걸 매주 긁을 이유가 없다.
    try:
        from algorithms.reference_snapshots import refresh_due
        result = await asyncio.to_thread(refresh_due)
        for item in result["refreshed"]:
            if item["refreshed"]:
                collector.log(f"주간 작업: 기준 스냅샷 {item['name']} 갱신 완료 "
                              f"({item['record_count']}건, {item['snapshot_date']})")
            else:
                # 갱신 실패를 조용히 넘기면 파일이 계속 묵는다. 기존 파일은 살아있다.
                collector.log(f"  ⚠ 기준 스냅샷 {item['name']} {item['reason']} "
                              "— 기존 스냅샷 유지")
        if result["skipped_fresh"]:
            ages = ", ".join(f"{s['name']} {s['age_days']}일"
                             for s in result["skipped_fresh"])
            collector.log(f"주간 작업: 기준 스냅샷 아직 신선함({ages}) — 원본 호출 안 함")
    except Exception as e:
        collector.log_error("scheduler_weekly_reference_snapshots", e)

    _save_last_weekly_run(dt.datetime.now(dt.timezone.utc))


_DAILY_BRIEF_HOUR_UTC = 22   # 일일 브리핑 생성·발송: UTC 22시(KST 07시)경


def _log_error(message: str) -> None:
    """error_log.txt에 한 줄 남기고 **stdout에도 찍는다**(/api/status가 파일을 읽음).

    stdout에도 찍는 이유는 collector.log_error와 같다 — 파일에만 있으면 배포 로그가
    깨끗해 보여서, 스케줄러가 며칠째 실패해도 아무도 모른다(2026-08-13 KDCA 사례).
    """
    print(f"  ❌ [scheduler] {message}", flush=True)
    try:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(data_dir / "error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} | scheduler | {message}\n")
    except Exception:
        pass


async def _run_daily_brief_job(today: str) -> None:
    """오늘자 일일 브리핑을 지원 언어 전부 생성해 DB에 아카이브하고, 한국어판을
    텔레그램으로 발송한다. 재시작에도 안전하도록 '오늘 ko가 이미 있으면 건너뜀'을
    호출 측에서 판단한다(DB 기준이라 메모리 플래그와 달리 재시작에 살아남음).

    언어 목록을 여기 손으로 적지 않고 daily_brief.SUPPORTED_LANGS를 따른다.
    예전엔 "ko", "en"을 직접 나열해서, 프랑스어 지원이 추가되고 홈페이지가 3개
    언어로 나간 뒤에도 **fr 아카이브만 계속 0건**이었다(2026-08-23 발견).
    목록을 따라가면 다음에 언어가 늘어도 여기가 또 뒤처지지 않는다.

    언어별로 예외를 격리하는 이유: 예전엔 try 하나가 전부를 감싸서 en 생성이
    실패하면 그 뒤가 통째로 사라졌다. 한 언어의 실패가 나머지 언어를 죽이면
    안 된다(KDCA 사고와 같은 구조).
    """
    from algorithms.daily_brief import SUPPORTED_LANGS, generate_daily_brief
    from algorithms.notifier import notify_daily_brief

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    briefs: dict[str, dict] = {}
    for lang in SUPPORTED_LANGS:
        try:
            brief = await asyncio.to_thread(generate_daily_brief, lang, api_key, today)
            db.save_daily_brief(today, lang, brief)
            briefs[lang] = brief
        except Exception as e:
            _log_error(f"daily_brief_job failed({lang}): {type(e).__name__}: {e}")

    if not briefs:
        _log_error(f"daily_brief_job: {today} 브리핑을 한 언어도 생성하지 못함")
        return

    # 텔레그램은 한국어판으로 보낸다. 한국어가 실패했으면 발송을 건너뛴다 —
    # 다른 언어로 대신 보내면 캡틴이 못 읽는 알림이 가고, 실패를 성공으로 착각한다.
    if "ko" in briefs:
        try:
            await asyncio.to_thread(notify_daily_brief, briefs["ko"])
        except Exception as e:
            _log_error(f"daily_brief 텔레그램 발송 실패: {type(e).__name__}: {e}")


async def _maybe_run_daily_brief() -> None:
    """정해진 시각(UTC 22시)이 지났고 오늘자 브리핑에 빠진 언어가 있으면 생성.

    예전엔 ko 하나만 보고 판단해서, ko가 있으면 그날은 끝난 것으로 쳤다. 그러면
    다른 언어가 실패했을 때 그날은 영영 안 채워진다 — 재시도 기회가 없다.
    지원 언어 중 하나라도 없으면 돈다(이미 있는 언어는 같은 내용으로 덮어써도
    무해하고, 하루 한 번뿐이라 비용도 문제되지 않는다).
    """
    from algorithms.daily_brief import SUPPORTED_LANGS

    now = dt.datetime.utcnow()
    today = now.date().isoformat()
    if now.hour < _DAILY_BRIEF_HOUR_UTC:
        return
    missing = [l for l in SUPPORTED_LANGS if db.get_daily_brief(today, l) is None]
    if missing:
        await _run_daily_brief_job(today)


async def _run_prediction_resolution() -> None:
    """미해소 예측을 공식 선언과 대조해 자동 채점한다 (2026-08-30).

    ★ 왜 이게 없으면 안 되는가 ★
    `predictions` 테이블에는 처음부터 `verified_at`·`lead_days`·`correct` 가 있었고
    `prediction_scoring` 에는 Brier 채점기까지 있었는데, **그 사이를 잇는 게 없었다.**
    해소는 수동 API 로만 가능했고 아무도 부르지 않았다. 그래서 예측은 쌓이는데
    채점이 0건이었고, "남보다 먼저 안다"는 제품의 논지를 증명할 경로가 끊겨 있었다.

    시간이 흘러도 증거가 안 생기는 구조였다 — 이 한 줄이 그걸 잇는다.
    """
    import collector

    try:
        # ★ 채점 전에 정답부터 갱신한다 ★ (2026-09-21)
        # 정답 테이블(outbreak_timeline)을 채우던 건 손으로 적은 16건뿐이었고
        # 가장 최근 선언이 2024-09-27 이었다. 채점 조건이 '선언일 > 예측일' 이라
        # 2026년 예측은 그 선언을 영원히 못 만난다 — 적중이 구조적으로 불가능했고,
        # 빗나간 예측만 90일 뒤 incorrect 로 쌓여 '측정된 것처럼 보이는 적중률 0%'
        # 가 만들어지는 중이었다. 순서가 중요하다: 적재가 먼저, 채점이 나중이다.
        from algorithms.declaration_ingest import ingest_declarations, summary as decl_summary
        try:
            ingested = await asyncio.to_thread(ingest_declarations)
            collector.log(f"📌 {decl_summary(ingested)}")
        except Exception as e:
            # 정답 적재가 실패해도 채점은 돈다(기한 지난 예측을 방치하지 않는다).
            # 다만 조용히 넘어가지 않는다 — 정답이 안 늘면 적중은 영원히 0이다.
            _log_error(f"declaration_ingest: {type(e).__name__}: {e}")

        from algorithms.prediction_resolver import resolve_due_predictions
        outcome = await asyncio.to_thread(resolve_due_predictions)
        resolved = outcome["resolved"]
        if resolved:
            hits = [r for r in resolved if r["correct"] == 1]
            collector.log(
                f"📋 예측 자동 채점: {len(resolved)}건 해소"
                f"(적중 {len(hits)}건, 미결 {outcome['still_open']}건)"
            )
            for r in hits:
                # ★ 이 줄이 이 제품의 논지가 처음으로 실측되는 자리다 ★
                collector.log(
                    f"   ★ 선행일수 실측: {r['country']}/{r['disease']} "
                    f"{r['lead_days']}일 선행 (근거 {r['event_id']})"
                )
        else:
            collector.log(
                f"예측 자동 채점: 해소할 예측 없음(미결 {outcome['still_open']}건)"
            )
    except Exception as e:
        _log_error(f"prediction_resolution: {type(e).__name__}: {e}")


# 없는 기준 스냅샷을 다시 받아 보는 최소 간격. 원본(openFDA)을 매시간 두드리지 않으려는 것이다.
_MISSING_SNAPSHOT_RETRY_SEC = 6 * 3600
_last_missing_snapshot_try: float | None = None


async def _maybe_refresh_missing_snapshots() -> None:
    """파일이 없는 기준 스냅샷을 주간 타이머와 무관하게 받아 본다(6시간에 한 번까지).

    결과는 성공이든 실패든 로그에 **이유와 함께** 남긴다 — 이 자리가 없던 동안 '없다'는
    경고가 이틀 넘게 반복됐는데 왜 안 채워지는지는 로그에 한 줄도 없었다.
    """
    import time
    import collector
    global _last_missing_snapshot_try
    now = time.time()
    if _last_missing_snapshot_try is not None and now - _last_missing_snapshot_try < _MISSING_SNAPSHOT_RETRY_SEC:
        return
    try:
        from algorithms.reference_snapshots import SNAPSHOTS, refresh_missing, snapshot_status
        if all(snapshot_status(n)["present"] for n in SNAPSHOTS):
            return
        _last_missing_snapshot_try = now
        result = await asyncio.to_thread(refresh_missing)
        for item in result["refreshed"]:
            if item["refreshed"]:
                collector.log(f"기준 스냅샷 {item['name']}: 없어서 새로 받음 "
                              f"({item['record_count']}건, {item['snapshot_date']})")
            else:
                collector.log(f"  ⚠ 기준 스냅샷 {item['name']}: 없어서 받아 봤으나 {item['reason']}")
    except Exception as e:
        collector.log_error("scheduler_missing_snapshots", e)


def _weekly_state_line(now: dt.datetime | None = None) -> str:
    """주간작업이 마지막으로 언제 돌았고 이번 시작에서 도는지 — 값으로 말한다.

    ★ 왜 필요한가 ★ (2026-10-04) 기준 스냅샷 파일이 재배포로 사라지는데 주간작업이 이를 다시
    채우지 못한 이유가 '마지막 실행 시각은 남고 7일을 기다린다'는 추정뿐이었다. 시작할 때 이 줄이
    찍히면 추정이 아니라 값이 된다: `기록 없음` 이면 상태 파일이 재배포로 사라진 것이고, `N일 전`
    이면 남아 있는 것이다.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    last = _load_last_weekly_run()
    if last is None:
        return "주간 작업: 마지막 실행 기록 없음 → 이번 시작에서 실행"
    age = now - last
    stamp = last.strftime("%Y-%m-%d %H:%M UTC")
    if age.total_seconds() >= _WEEKLY_INTERVAL_SEC:
        return f"주간 작업: 마지막 실행 {stamp}({age.days}일 전) → 이번 시작에서 실행"
    wait_days = max(0, (_WEEKLY_INTERVAL_SEC - age.total_seconds()) / 86400)
    return f"주간 작업: 마지막 실행 {stamp}({age.days}일 전) → 다음 실행까지 약 {wait_days:.1f}일"


async def _scheduler_loop() -> None:
    # 재배포로 초기화되지 않게 디스크에서 읽어온다(주간작업과 같은 패턴).
    last_ai_run_date: dt.date | None = _load_last_ai_run()
    import collector
    collector.log(_weekly_state_line())
    await _run_collector("free")
    await _run_alert_cycle()
    await _maybe_run_daily_brief()
    await _maybe_refresh_missing_snapshots()

    last_weekly = _load_last_weekly_run()
    now = dt.datetime.now(dt.timezone.utc)
    if last_weekly is None or (now - last_weekly).total_seconds() >= _WEEKLY_INTERVAL_SEC:
        await _run_weekly_job()

    while True:
        # ★ 다음 정시까지만 잔다 ★ 예전엔 sleep(3600) '뒤에' 수집을 돌려서, 수집에
        # 걸린 시간(45~60초)이 매 주기 누적됐다. 하루 약 20분씩 밀리고, 분이 :59를
        # 넘는 순간 **한 시간 슬롯이 통째로 건너뛰어진다** — 실측상 2.5~3.3일마다
        # 한 번씩. 그 시간이 21시면 그날 AI 수집이 에러 한 줄 없이 사라진다.
        # 정시에 맞춰 자면 수집 시간이 누적되지 않는다.
        now = dt.datetime.now(dt.timezone.utc)
        next_hour = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        await asyncio.sleep(max(60.0, (next_hour - now).total_seconds()))
        await _run_collector("free")
        # 수집 바로 뒤에 붙인다 — 방금 들어온 값으로 판정해야 "빨리 알린다"가
        # 실제로 지켜진다. 같은 source 재통보는 refresh_alerts가 막는다.
        await _run_alert_cycle()
        await _maybe_refresh_missing_snapshots()

        now = dt.datetime.utcnow()
        # ★ '정확히 21시'가 아니라 '21시 이후'로 판정한다 ★
        # 예전엔 `now.hour == _AI_HOUR_UTC` 라 그 한 틱을 놓치면 따라잡을 방법이
        # 없었다. 2026-08-22에 실제로 그 일이 났다 — 21:54 배포가 21:58 틱을
        # 4분 앞두고 컨테이너를 죽였고, 재시작 후 다음 틱은 23시라 그날 AI
        # 갭필링·불리틴·나우캐스트 백필이 통째로 빠졌다. 에러는 한 줄도 안 났다.
        # 일일 브리핑(_maybe_run_daily_brief)이 이미 쓰는 `>=` 방식과 맞춘다.
        # 하루 1회 보장은 last_ai_run_date(파일 영속화)가 담당한다.
        if now.hour >= _AI_HOUR_UTC and last_ai_run_date != now.date():
            last_ai_run_date = now.date()
            _save_last_ai_run(last_ai_run_date)
            await _run_collector("ai")
            # 같은 하루 1회 슬롯에서 함께 확인 — 새 회차가 없으면 비용이 들지 않는다.
            await _run_bulletin_collection()
            # 학습셋 백필도 같은 슬롯에서. 커버리지가 차면 GDELT를 아예 안 부른다.
            await _run_nowcast_maintenance()
            # ★ 예측 자동 채점 ★ 이게 없어서 성적표가 영원히 비어 있었다.
            await _run_prediction_resolution()

        await _maybe_run_daily_brief()

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
        # 품질 불변식(2026-08-30) — 소스 헬스가 **구조적으로 못 보는** 층.
        # 소스는 값을 돌려주는데 그 값을 만든 방식이 망가진 경우를 센다.
        # 2026-08 사고 6건이 전부 이 유형이었다(소스 헬스는 내내 정상이었다).
        "quality_health": _quality_health_safe(),
        # 능력 장부(2026-09-04) — 소스 헬스도 품질 불변식도 못 보는 세 번째 층.
        # 소스는 멀쩡하고 값도 옳은데, **상태 필드가 설정을 근거로 능력을 주장**하는
        # 경우를 센다. 실측 사고 4건이 전부 이 유형이었다(NIM 배선 누락, 온프렘
        # 문서 층 누출, 선행일수 18일, 정확도 0.988). unverified가 비어 있지 않으면
        # "설정은 됐는데 한 번도 안 돌아본" 능력이 있다는 뜻이다.
        "capability_health": _capability_health_safe(),
        # 기준 스냅샷 신선도(2026-09-04) — 발할라의 백신 공급·국가 역량 축이
        # 정적 파일에 얹혀 있다. 예전엔 나이를 재는 코드가 아예 없어서, 파일이
        # 몇 달 묵어도 available: true 로 답했다. stale_snapshots 가 비어 있지
        # 않으면 '조용히 굳은 기준 데이터'가 눈에 보이는 것.
        "reference_snapshots": _reference_snapshots_safe(),
        # 선행일수 실측 — 0건이면 0건이라고 말한다. 이 값이 비어 있는 동안에는
        # 선행성 주장을 할 근거가 없다.
        "lead_time": _lead_time_safe(),
        "recent_errors": _recent_errors(),
        "total_error_count": error_count,
    }


def _quality_health_safe() -> dict | None:
    """품질 헬스가 터져도 /api/status 전체를 죽이지 않는다.

    다만 **조용히 없애지도 않는다** — 실패하면 그 사실이 그대로 실린다. 이 시스템에서
    가장 나쁜 건 지표가 조용히 사라지는 것이다.
    """
    try:
        from algorithms.quality_health import quality_report
        return quality_report()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "invariants": []}


def _reference_snapshots_safe() -> dict | None:
    """스냅샷 신선도가 터져도 /api/status를 죽이지 않되, 조용히 사라지지도 않는다."""
    try:
        from algorithms.reference_snapshots import report
        return report()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "snapshots": []}


def _capability_health_safe() -> dict | None:
    """능력 장부가 터져도 /api/status를 죽이지 않되, 조용히 사라지지도 않는다.
    빈 장부는 오류가 아니다 — 아직 아무 능력도 안 불렸다는 정직한 상태다."""
    try:
        from algorithms.capability_ledger import report
        from algorithms import nvidia as _nv
        from algorithms.nlp_extract import EXTERNAL_LLM_CAPABILITY
        from algorithms.notifier import ALERT_CAPABILITY, telegram_configured

        # ★ 아는 능력을 전부 넘긴다 ★ 장부에 기록된 것만 나열하면 '설정만 되고
        # 한 번도 안 불린' 능력이 목록에서 통째로 빠진다 — 잡으려는 상태가 바로
        # 그건데. 설정 여부는 각 소유 모듈이 답한다.
        text_key = bool(_nv.text_nim_key())
        shared_key = bool(_nv.nvidia_api_key())
        configured = {
            _nv.LAYER_CAPABILITIES["genome"]: shared_key,
            _nv.LAYER_CAPABILITIES["document"]: shared_key,
            _nv.LAYER_CAPABILITIES["text"]: text_key,
            # 외부 LLM 폴백(2026-09-04). NIM 층만 장부에 있어서, NIM이 죽고
            # 폴백까지 죽었을 때 "둘 다 죽었다"를 여기서 볼 수가 없었다.
            # 폴백은 마지막 방어선이라 그게 서 있는지가 특히 중요하다.
            EXTERNAL_LLM_CAPABILITY: bool(os.environ.get("ANTHROPIC_API_KEY")),
            ALERT_CAPABILITY: telegram_configured(),
        }
        return report(configured)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "capabilities": []}


def _lead_time_safe() -> dict | None:
    try:
        from algorithms.prediction_resolver import lead_time_record
        return lead_time_record()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "measured_events": 0}


def _ledger_safe() -> dict | None:
    try:
        from algorithms.lead_time_ledger import ledger_record
        return ledger_record()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "measured_events": 0}


@app.get("/api/lead-time-ledger", tags=["후향 검증"])
def lead_time_ledger(outcome: Optional[str] = None, limit: int = 100):
    """★ 선행성 원장 ★ "우리가 언제 알았나" 를 **선언 전에** 적어둔 기록.

    지금까지는 선언이 난 뒤에 신호를 거꾸로 뒤져 "그때 갖고 있었나" 를 따졌다.
    그러다 에볼라 DRC 2026 에서 **선언 42~85일 뒤에 적재한 신호**로 "선언보다
    5일 먼저" 를 계산하는 사고가 났다(2026-09-03 발견).

    이 원장은 순서를 뒤집는다 — 매 수집 주기에 문턱을 넘는 순간 그 자리에서
    적고, 선언은 그 뒤에 온다. 그러므로 `crossed_at` 이 선언일보다 앞선다는
    **사실 자체가 증거**다. 나중에 무엇을 적재하든 이미 적힌 시각은 안 바뀐다.

    ★ 빗나간 것도 남긴다 ★ 문턱을 넘었는데 기한 내 선언이 없으면
    `no_declaration` 으로 닫는다. 맞은 것만 세면 정밀도만 남고 재현율이 사라진다.
    """
    from algorithms.lead_time_ledger import list_entries

    db.init_db()
    return {
        "summary": _ledger_safe(),
        "entries": list_entries(outcome=outcome, limit=limit),
    }


@app.get("/api/launch-readiness", tags=["시스템"])
def launch_readiness():
    """런칭 준비도 — **"런칭해도 되나"를 의견이 아니라 측정값으로 낸다.**

    관문 4개(수집 살아있음 · 조용한 저하 없음 · 선행일수 실측 · 캘리브레이션)를
    라이브 데이터에서 계산하고, 막힌 이유와 무엇이 채워져야 풀리는지를 함께 낸다.

    `ready_for` 가 용도별로 갈리는 이유: 무료 베타(신호 대시보드)는 지금도 되고,
    유료 예보는 실측이 쌓여야 한다. 그 둘을 한 덩어리로 묻는 게 질문이 틀린 것이었다.

    ⚠️ `lead_time` 관문은 **코드로 열 수 없다.** 실제 발병을 먼저 잡아야 열린다.
    """
    from algorithms.launch_readiness import readiness_report
    return readiness_report()


@app.get("/api/lead-time", tags=["시스템"])
def lead_time():
    """선행일수 실측 성적표 — 자동 채점된 예측만 집계한다.

    `measured_events: 0` 이면 아직 증거가 없다는 뜻이고, 그 상태에서 "블루닷보다
    빠르다" 같은 주장을 하면 근거가 없다. `benchmark_baselines` 의 블루닷 9일은
    **넘어야 할 목표선**이지 우리 실적이 아니다.
    """
    from algorithms.prediction_resolver import lead_time_record
    return lead_time_record()


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


@app.get("/api/patient-zero/origins", tags=["Stage 0: 발원지"])
def patient_zero_origins():
    """
    발원지 선택지 전체 목록 — 큐레이션 8개 도시(tier=curated, 실제 발병
    역사 기반 위험도)에 World Bank 실제 국가 데이터(tier=auto, ~210개국)를
    더한 것. auto 국가는 위험도(er)·여객량(pax)이 중립 기본값이고 실측이
    아님을 note로 항상 명시 — 지어낸 정밀도로 오인되지 않게 함.
    """
    from algorithms.origin_catalog import build_origin_catalog
    return {"origins": build_origin_catalog()}


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


# ── 경보 → NPI 반사실 브리핑 (예측→의사결정) ─────────────────
class InterventionBriefRequest(BaseModel):
    disease: Optional[str] = Field(None, description="질병명 (위협 시나리오 추정에 사용)")
    country: Optional[str] = Field(None, description="국가 ISO3")
    tier: str = Field("high", description="경보 등급 critical|high")
    score: float = Field(0, description="위험 점수")
    threat: Optional[str] = Field(None, description="위협 시나리오 명시 flu|novel|severe (없으면 질병에서 추정)")
    seal: bool = Field(True, description="OpenTimestamps 봉인 시도 여부")

@app.post("/api/alerts/intervention-brief", tags=["Stage 5: 방어 시뮬레이션"], dependencies=_auth)
def alert_intervention_brief(req: InterventionBriefRequest):
    """경보를 '무대응 vs 개입' 반사실 브리핑으로 승격(예측→의사결정) + OpenTimestamps
    봉인(검증 가능한 트랙레코드 자동 축적). 반사실 수치는 표준 SEIR 모델 시나리오이며
    disclaimer로 '방향성 참고'임을 항상 명시(‘구할 생명’은 모델 추정, 실측·보장 아님)."""
    from algorithms.alert_intervention import sealed_brief
    if req.threat is not None and req.threat not in THREAT:
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")
    return sealed_brief(req.disease, req.country, req.tier, req.score, req.threat, seal=req.seal)


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


@app.get("/api/backtest/gdelt", tags=["후향 검증"])
def backtest_gdelt():
    """
    GDELT 과거 뉴스 커버리지 백테스트(㉟) — 시작이 늦어 '0에서 출발'처럼 보이는
    문제를, GDELT Project 전세계 뉴스 커버리지(무료)로 과거 발병을 재구성해
    메운다. 발병별로 '뉴스 커버리지 급증일' vs '공식 선언일'의 선행일수를 계산.
    ★ GDELT 볼륨은 뉴스 커버리지 프록시(확진자 수·아이기론 자체 신호 아님)이며,
    라이브 extracted_signals 백테스트와는 별개의 과거 재구성임을 명시. GDELT
    DOC은 2017년 이후만 커버.
    """
    from algorithms.gdelt_signals import backtest_all_gdelt
    db.init_db()
    _seed_known_timelines()
    return backtest_all_gdelt()


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


# ── 독자 모델 IP 준비: 학습데이터 축적 + 모델 추상화 계층 ──────────
@app.get("/api/ai/provider-status", tags=["AI"])
def ai_provider_status():
    """현재 활성 AI 제공자(로컬 자체모델 vs 외부 LLM 폴백)와 데이터 주권 태세.
    자체 모델이 준비되면 AEGIRON_LOCAL_MODEL 설정만으로 독자 모델로 전환 —
    호출부 변경 없음(주권 대비 설계)."""
    from algorithms.aegiron_model import provider_status
    return provider_status()


@app.get("/api/ai/extract-compare", tags=["AI"], dependencies=_auth)
def ai_extract_compare(limit: int = 30, source: Optional[str] = None):
    """추출 모델 교체 판단용 짝 비교 — 이미 쌓인 원문을 현재 NIM 설정으로 다시
    뽑아, 기존 라벨과 어디서 갈리는지 센다.

    정확도가 아니라 '불일치·과충전' 측정이다(기존 라벨도 검증된 정답이 아님).
    사람 없이 오류로 셀 수 있는 건 rule_violations뿐 — 특히 date_invented는
    원문에 연도가 없는데 날짜를 만들어낸 것이라 명백한 위반이다.

    NIM을 호출하므로 비용이 든다 → 인증 필수. limit은 작게 시작할 것."""
    from algorithms.extract_compare import run_comparison
    return run_comparison(limit=limit, source=source)


@app.get("/api/ai/training-data/stats", tags=["AI"])
def ai_training_data_stats(limit: int = 5000):
    """매일 쌓이는 LLM 추출 결과를 '독자 모델 학습셋' 관점으로 집계 — 규모·라벨
    품질(실버/골드)·질병 분포. '운영이 곧 데이터 해자 축적'의 근거 숫자."""
    from algorithms.training_data import dataset_stats
    return dataset_stats(limit=limit)


@app.get("/api/ai/training-data/export", tags=["AI"], dependencies=_auth)
def ai_training_data_export(limit: int = 5000):
    """증류 학습쌍(원문 → 구조화 정답) export — 작은 오픈 모델 파인튜닝용.
    독자 자산이라 인증 필수. 라벨은 Claude 증류(실버)+사람검증(골드)로 구분."""
    from algorithms.training_data import export_extraction_pairs
    pairs = export_extraction_pairs(limit=limit)
    return {
        "count": len(pairs),
        "task": "news_text_to_structured_signal",
        "pairs": pairs,
        "label_note": "실버(Claude 증류)+골드(사람검증). 이 데이터로 파인튜닝하면 "
                      "외부 API 의존 없는 독자 모델이 된다.",
    }


@app.get("/api/ai/nowcast/readiness", tags=["AI"])
def ai_nowcast_readiness(horizon_days: int = 30, lookback_days: int = 30):
    """Tier 2 프레임워크 — '신호→실제 발병' 성과 학습셋의 학습 가능 여부. 표본·클래스
    부족이면 sufficient_data=False로 정직하게 표시(지어낸 성능 없음). 운영이 지속되며
    성과 라벨이 쌓이면 자동으로 충족된다."""
    from algorithms.nowcast_dataset import assemble_dataset, dataset_readiness
    rows = assemble_dataset(horizon_days=horizon_days, lookback_days=lookback_days)
    return dataset_readiness(rows)


@app.get("/api/ai/nowcast/threshold", tags=["AI"], dependencies=_auth)
def ai_nowcast_threshold(horizon_days: int = 30, lookback_days: int = 30):
    """임계값 운영특성 곡선 — 재현율과 오경보율의 균형을 '고를 수 있게' 보여준다.

    정답 임계값을 고르지 않는다. 적정 FAR은 기술이 아니라 운영 정책이라(하루 몇 건을
    사람이 검토할 수 있는가, 발병을 놓치는 비용이 헛경보의 몇 배인가) 조직이 정해야
    한다. 곡선과 FAR 예산별 선택지를 제시하고, alerts_per_100_windows로 실제 운영
    부담을 가늠하게 한다.
    diagnosis에서 '임계값 조정으로 될 문제인지'를 먼저 판정한다 — 곡선이 평평하면
    임계값을 만질 게 아니라 특징·라벨 커버리지를 손봐야 한다."""
    from algorithms.nowcast_dataset import assemble_dataset, train_baseline
    from algorithms.nowcast_threshold import analyze

    rows = assemble_dataset(horizon_days=horizon_days, lookback_days=lookback_days)
    model = train_baseline(rows)
    return analyze(rows, model)


@app.get("/api/ai/nowcast/evaluate", tags=["AI"], dependencies=_auth)
def ai_nowcast_evaluate(horizon_days: int = 30, lookback_days: int = 30,
                        n_folds: int = 4):
    """★ 전향적(out-of-sample) 성능 ★ — /train과 /threshold가 내는 숫자는 학습에 쓴
    그 데이터를 다시 채점한 값이라 특징을 늘릴수록 거의 항상 좋아진다. 여기서는
    시간 전진 검증으로 '그 시점에 알 수 없던 미래'를 채점한다. 모델 판단은 이 값으로.

    coverage 블록을 반드시 같이 볼 것 — 재현율 상한은 모델이 아니라 **수집**이 정한다.
    선언 직전 창에 신호가 한 건도 없던 경우(blind)는 어떤 특징으로도 못 잡는다.
    conditional_sensitivity가 '잡을 수 있었던 것 중 얼마를 잡았나'다."""
    from algorithms.nowcast_dataset import assemble_dataset
    from algorithms.nowcast_eval import evaluate_temporal
    rows = assemble_dataset(horizon_days=horizon_days, lookback_days=lookback_days)
    return evaluate_temporal(rows, n_folds=n_folds)


@app.get("/api/ai/nowcast/feature-ablation", tags=["AI"], dependencies=_auth)
def ai_nowcast_feature_ablation(horizon_days: int = 30, lookback_days: int = 30):
    """확장 특징이 실제로 판별력을 올리는지 같은 시간분할로 비교한다(기본 6개 vs 확장 14개).

    실측(2026-08 기준): 민감도 0.725를 맞춘 지점에서 정밀도 0.207 → 0.370,
    100창당 경보 1.7 → 1.0. 재현율은 이미 커버리지 상한에 걸려 있어 개선 여지가
    없고, 남은 과제가 과다발화였기 때문에 정밀도로 평가한다."""
    from algorithms.nowcast_dataset import assemble_dataset
    from algorithms.nowcast_eval import compare_feature_sets
    kw = {"horizon_days": horizon_days, "lookback_days": lookback_days}
    return compare_feature_sets(assemble_dataset(extended=False, **kw),
                                assemble_dataset(extended=True, **kw),
                                "기본6개", "확장14개")


@app.get("/api/ai/nowcast/train", tags=["AI"], dependencies=_auth)
def ai_nowcast_train(horizon_days: int = 30, lookback_days: int = 30):
    """Tier 2 베이스라인 학습(순수 파이썬 로지스틱). 데이터 부족이면 학습 거부.
    학습돼도 정확도는 참고용 — 전향적 검증 전엔 신뢰 금지(z-score/EARS 대체 '자리' 증명)."""
    from algorithms.nowcast_dataset import assemble_dataset, train_baseline
    rows = assemble_dataset(horizon_days=horizon_days, lookback_days=lookback_days)
    return train_baseline(rows)


@app.post("/api/ai/nowcast/backfill-train", tags=["AI"], dependencies=_auth)
def ai_nowcast_backfill_train(min_volume: float = 0.0):
    """과거 공식 발병 선언(라벨) + 그 시점 GDELT 실제 뉴스량(특징)을 백필해 Tier 2를
    '지금' 학습한다 — 몇 년 대기를 명령어 하나로 압축. GDELT를 못 가져오면 신호를
    지어내지 않고 건너뛰므로(정직), GDELT가 열리는 환경에서 실행해야 실제 학습된다.
    학습 정확도는 'retrospective(과거적합)'로 라벨링 — 전향적 검증 전 실전대체 금지."""
    from algorithms.nowcast_backfill import run_backfill_and_train
    return run_backfill_and_train(min_volume=min_volume)


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


@app.get("/api/pipeline-stages", tags=["시스템"])
def pipeline_stages():
    """
    아이기론 파이프라인 9단계 — **이름의 단일 출처**.

    대외 자료·영상·포트폴리오는 전부 이걸 읽어야 한다. 여기 없는 단계 이름을
    문서에 쓰면 그건 지어낸 것이다(실제로 그런 일이 있었다 — 포트폴리오 PDF 에
    코드에 없는 단계 이름이 들어갔다).

    3·4·7 단계는 2026-08-31 에 이름을 붙였다. 새로 만든 기능이 아니라 이미
    돌고 있던 모듈에 번호를 부여한 것이고, 응답의 `newly_named` 로 그 사실을
    숨기지 않고 밝힌다.
    """
    from algorithms.pipeline_stages import pipeline_summary
    return pipeline_summary()


@app.get("/api/disaster-watch", tags=["GAI"])
def disaster_watch():
    """
    재난 → 발병 감시창(2026-08-28). 홍수·지진·태풍 같은 재난 자체는 발병이
    아니고 발병은 **뒤에** 온다 — 콜레라 3~14일, 렙토스피라 2~28일, 뎅기
    14~42일. 그 사이가 이 시스템이 노리는 시간이다. GDACS(무료·키 불필요)로
    재난을 받아 국가별 감시창을 열고, 창이 열린 나라의 현지어 뉴스 고경보
    문턱을 낮춘다.

    ★ 예측이 아니다 ★ 창이 열렸다는 건 "이 기간 이 질병 보도를 우연으로
    넘기지 말라"는 뜻이다(is_prediction=False). 잠복 구간은 문헌 기반이며
    이 시스템 데이터로 보정하지 않았다(windows_calibrated=False).
    """
    from algorithms.disaster_watch import disaster_watch_report
    return disaster_watch_report()


@app.get("/api/disaster-watch/{country}", tags=["GAI"])
def disaster_watch_country(country: str):
    """특정 국가(ISO3)의 열린 감시창 상세. 창이 없으면 404 가 아니라
    빈 목록이다 — '재난이 없었다'는 것도 답이기 때문이다."""
    from algorithms.disaster_watch import open_windows
    iso3 = country.strip().upper()
    return {
        "country_iso3": iso3,
        "open_windows": open_windows().get(iso3, []),
        "is_prediction": False,
        "windows_calibrated": False,
    }


@app.get("/api/climate-signals", tags=["GAI"])
def climate_signals():
    """
    기후·환경 선행지표(㉛) — 발병 '뒤'가 아니라 '앞'을 보는 층. 온난화·강수가
    매개모기(뎅기·지카 등) 전파에 선행한다는 과학적 근거(Mordecai 2017)를
    정량화. spillover_pressure는 발병 위험 측정치가 아니라 '환경 압력' 모델
    추정(is_leading_indicator=True, measured=False). 데이터: Open-Meteo(무료).
    삼림파괴(스필오버 1순위 동인)는 아직 미구현임을 disclaimer에 정직하게 명시.
    """
    from algorithms.climate_signals import climate_signals_all
    return climate_signals_all()


@app.get("/api/climate-signals/{country}", tags=["GAI"])
def climate_signals_country(country: str):
    """특정 국가(Tier-1 ISO3)의 기후 선행지표 상세."""
    from algorithms.climate_signals import compute_country_climate
    try:
        return compute_country_climate(country)
    except KeyError:
        from algorithms.climate_signals import COUNTRY_COORDS
        raise HTTPException(
            status_code=404,
            detail=f"기후 좌표 미등록 국가. 지원 목록: {list(COUNTRY_COORDS)}",
        )


@app.get("/api/land-signals", tags=["GAI"])
def land_signals():
    """
    토지이용·벌목 선행지표(㉜) — 스필오버 1순위 동인인 삼림파괴를 선행 신호로.
    NASA FIRMS 활성 화재 탐지(위성 실측)를 벌목·화전 프록시로 씀. fire_count는
    실측이지만 '삼림파괴'는 화재로부터 추론한 프록시임을 명시(모든 화재가 벌목은
    아님). FIRMS_MAP_KEY(무료) 없으면 data_available=False로 정직하게 표시.
    기후 선행지표(/api/climate-signals)와 짝을 이뤄 '발병 앞'을 본다.
    """
    from algorithms.forest_signals import land_signals_all
    return land_signals_all()


@app.get("/api/land-signals/{country}", tags=["GAI"])
def land_signals_country(country: str):
    """특정 국가(Tier-1 ISO3)의 토지이용 선행지표 상세."""
    from algorithms.forest_signals import compute_country_land, FIRMS_COUNTRY_CODES
    try:
        return compute_country_land(country)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"FIRMS 국가코드 미등록. 지원 목록: {list(FIRMS_COUNTRY_CODES)}",
        )


@app.get("/api/deforestation-signals", tags=["GAI"])
def deforestation_signals():
    """
    직접 산림손실 선행지표(㉝) — /api/land-signals(FIRMS 화재 '프록시')보다 한
    단계 직접적. Global Forest Watch 통합 위성 산림손실 알림(GLAD/RADD)을 국가별
    조회. 스필오버 1순위 동인(삼림파괴)의 직접 측정 선행 신호. GFW_API_KEY(무료)
    없으면 data_available=False. 정확한 GFW 쿼리는 배포 환경에서 확인 필요(파서는
    예상밖 응답 시 가짜 숫자 대신 실패로 떨어지게 방어적으로 설계).
    """
    from algorithms.deforestation_signals import deforestation_signals_all
    return deforestation_signals_all()


@app.get("/api/deforestation-signals/{country}", tags=["GAI"])
def deforestation_signals_country(country: str):
    """특정 국가(Tier-1 ISO3)의 직접 산림손실 선행지표 상세."""
    from algorithms.deforestation_signals import compute_country_deforestation, GFW_COUNTRIES
    try:
        return compute_country_deforestation(country)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"GFW 미지원 국가. 지원 목록: {GFW_COUNTRIES}",
        )


@app.get("/api/trade-signals", tags=["GAI"])
def trade_signals():
    """
    국제무역 선행지표(Phase 42) — 블루닷의 '항공권 데이터'에 대응하는 각도.
    정부·의료기관이 공식 발표 전에 의료물자(마스크·방호장비·진단키트)를
    대량 수입하기 시작하는 '준비 행동'을 UN Comtrade 관세통계로 포착.
    수입액 자체는 실측이나 '발병 대비 행동'이라는 해석은 프록시임을 명시.
    무역통계 특유의 신고지연(추정 2개월)이 있어 실시간 신호가 아니라
    중기 선행지표임을 항상 표시.

    COMTRADE_API_KEY가 있으면 Tier-1 국가별 정밀 추적(mode 없음),
    없으면 키가 필요 없는 공개 전세계 스캔(mode="public_global_scan")으로
    자동 폴백한다. 폴백은 국가 지정이 불가한 대신 **손으로 정한 목록 밖의
    급증을 발견**한다(outside_tier1_surges) — 목록 밖이 안 보이는 게
    2026-08-13 KDCA 사고의 원인이었다. 500행 상한이라 전수가 아니므로
    coverage.complete=false를 항상 함께 반환한다.
    """
    from algorithms.comtrade_signals import trade_signals_all
    return trade_signals_all()


@app.get("/api/trade-signals/{country}", tags=["GAI"])
def trade_signals_country(country: str):
    """특정 국가(Tier-1 ISO3)의 의료물자 수입 선행지표 상세."""
    from algorithms.comtrade_signals import compute_country_trade_signal, UN_M49_CODES
    try:
        return compute_country_trade_signal(country)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Comtrade 미지원 국가. 지원 목록: {list(UN_M49_CODES)}",
        )


@app.get("/api/travel-notices", tags=["GAI"])
def travel_notices():
    """
    CDC 여행 건강경보(신규 각도 탐색, 2026-07-27) — 가입·키 불필요, 즉시 가동.
    CDC Travelers' Health가 공식 4단계(Level 1~4)로 매긴 국가별 여행 위험
    등급을 그대로 노출. 등급 자체는 실측이나, 이 피드엔 감염병 외 자연재해·
    대규모 행사 등도 섞여 있을 수 있음을 note로 명시. 항공사 고객 프로파일과
    특히 맞는 신호(customer_profiles.py).
    """
    from algorithms.cdc_travel_notices import travel_notices_summary
    return travel_notices_summary()


@app.get("/api/countermeasure-gap", tags=["Stage 8: 바이오방어"])
def countermeasure_gap():
    """
    대응제 비축 격차 — 지금 신호가 잡히는 위협 중 **국제 비상 비축이 있는 것과
    없는 것**을 가른다.

    ★ 왜 이 각도인가 ★ 국가 비축 재고는 비공개다(안보 사안이고, 알아내려 해서도
    안 된다). 대신 공개되는 것이 있다 — WHO ICG 국제 비상 비축에 어떤 질병이
    들어 있는가. "우리 창고에 뭐가 있나" 는 못 봐도 "이 병에 세계가 즉시 꺼낼
    물량이 있는가" 는 볼 수 있고, 없는 쪽은 발병하면 조달부터 시작해야 한다.

    말하지 않는 것: 재고량(있다 ≠ 충분하다) · 한국 비축 · 변이별 효능.
    판정 못 한 질병명은 격차로 세지 않고 unclassified 로 따로 센다.
    """
    from algorithms.countermeasure_stockpile import gap_report
    rows = db.list_extracted_signals(limit=500)
    diseases = [r.get("disease") for r in rows if isinstance(r, dict)]
    report = gap_report(diseases)
    report["signals_examined"] = len(rows)
    return report


@app.get("/api/biodefense/valhalla", tags=["Stage 8: 바이오방어"])
def biodefense_valhalla():
    """★ 발할라 현재 상태 ★ **수집기가 쌓아둔 값**을 즉시 돌려준다.

    2026-09-03 이전까지 발할라는 부를 때만 계산됐다. 그래서 어제와 비교할 수
    없었고, `/api/biodefense/procurement` 는 나라장터를 66번 부르느라 47초가
    걸렸다. 이제 수집기가 매 주기 쌓고, 이 엔드포인트는 그걸 읽기만 한다.

    ★ 굳은 값을 새 값인 척하지 않는다 ★ 조각마다 `refreshed` 와 `age_hours` 가
    붙는다. 조달은 6시간, 임상 파이프라인은 24시간마다 갱신되므로 그 사이에는
    나이가 든 값이다. 갱신에 실패하면 사유가 남고 나이가 계속 자란다.
    """
    from algorithms.valhalla_watch import STATE_FILE, _age_hours, _load_state, _now

    state = _load_state()
    if not state:
        # ★ 아직 안 쌓인 것을 '값 없음' 으로 말하지 않는다 ★
        return {"available": False,
                "reason": "수집기가 아직 발할라를 한 번도 돌리지 않았다",
                "state_file": STATE_FILE.name}

    now = _now()
    parts = {}
    for key, entry in state.items():
        if not isinstance(entry, dict):
            continue
        parts[key] = {"age_hours": _age_hours(entry.get("fetched_at"), now),
                      "fetched_at": entry.get("fetched_at"),
                      "value": entry.get("value")}
    return {
        "available": True,
        "parts": parts,
        "note": "수집기가 쌓아둔 값이다. age_hours 는 그 조각이 몇 시간 된 "
                "값인지를 말한다 — 지금 이 순간의 값이 아니다.",
        "refresh_hours": {"procurement": 6, "pipeline": 24},
    }


@app.get("/api/biodefense/vaccine-supply", tags=["Stage 8: 바이오방어"])
def biodefense_vaccine_supply():
    """★ 백신 공급 구조 ★ 비축이 있어도 **다시 채울 수 있는가**.

    발할라에는 생산 주권 축이 원래 설계돼 있었지만(`domestic_producible`)
    값이 손으로 넣은 참/거짓이었다. WHO 사전적격성 목록으로 실제 근거를 붙인다.

    ★ 여기서 나오는 발견 ★ 국제 비상 비축 5종 중 **에볼라·엠폭스는 사전적격성
    제조사가 한 곳뿐이다.** 비축이 있다는 것과 공급이 안전하다는 것은 다른 말이다 —
    그 하나가 멈추면 비축은 다시 안 채워진다. 비축 목록만 봐서는 안 보인다.

    ★ '못 만든다' 고 말하지 않는다 ★ 사전적격성은 UN 조달용 심사라, 자국 시장만
    겨냥한 백신은 아예 신청하지 않는다. 목록에 없는 것과 못 만드는 것은 다르다.
    """
    from algorithms.countermeasure_stockpile import ICG_STOCKPILES, KNOWN_GAP_ALIASES
    from algorithms.vaccine_supply import chokepoints, supply_for_disease

    stockpiled = {v["name_ko"] for v in ICG_STOCKPILES.values()}
    rows, unknown = [], []
    for name in sorted(stockpiled | set(KNOWN_GAP_ALIASES)):
        supply = supply_for_disease(name)
        if not supply.get("available"):
            unknown.append({"disease": name, "reason": supply.get("reason")})
            continue
        rows.append({
            "disease": name,
            "has_global_stockpile": name in stockpiled,
            "prequalified_count": supply["prequalified_count"],
            "manufacturer_count": supply.get("manufacturer_count", 0),
            "is_single_source": supply.get("is_single_source"),
            "authority_countries": supply.get("authority_countries", []),
            "korea_supervises": supply.get("korea_supervises", False),
        })

    # ★ 가장 날카로운 줄 ★ 비축은 있는데 공급원이 하나인 병.
    fragile = [r["disease"] for r in rows
               if r["has_global_stockpile"] and r["is_single_source"]]

    return {
        "diseases": rows,
        "stockpiled_but_single_source": fragile,
        "no_vaccine_term": unknown,
        "chokepoints": chokepoints(),
        "note": "비축이 '있다' 는 것과 공급이 안전하다는 것은 다른 말이다. "
                "사전적격성 제조사가 하나면 그 하나가 멈출 때 비축을 다시 채울 "
                "경로가 없다.",
        "sources": ["WHO ICG (국제 비상 비축)", "WHO Prequalified Vaccines"],
    }


@app.get("/api/biodefense/capacity/{iso3}", tags=["Stage 8: 바이오방어"])
def biodefense_capacity(iso3: str, year: int | None = None):
    """★ 국가 대비 역량 ★ 그 나라가 **스스로 신고한** 15개 역량.

    WHO 국제보건규칙 자가평가(SPAR) — 194개국 × 15개 역량 × 2021~2023.

    ★★ 이 숫자는 자가평가다 ★★ 나라가 자기 점수를 스스로 매긴다. WHO 가 검증한
    값이 아니다. 그래서 '역량' 이 아니라 **'신고한 점수'** 라고 부른다.

    ★ 합산 점수를 만들지 않는다 ★ 15개를 평균 내면 "한국 99.5점" 이 나오는데,
    실험실과 방사선 비상을 더해서 나눌 근거가 없다. 대신 세계 중앙값보다 뒤처진
    역량이 **몇 개인가** 를 센다 — 이건 셀 수 있는 사실이다.
    """
    from algorithms.ihr_capacity import country_capacity

    return country_capacity(iso3, year=year)


@app.get("/api/biodefense/capacity-gap", tags=["Stage 8: 바이오방어"])
def biodefense_capacity_gap():
    """★ 재난이 난 나라는 대비가 돼 있는가 ★ 감시창 × 신고 역량.

    아이기론은 GDACS 로 재난을 잡아 그 나라에 감시창을 연다(`disaster_watch`).
    그 나라가 WHO 에 신고한 대비 역량을 겹치면, **지금 무슨 일이 났는데 그 나라가
    어디가 약하다고 스스로 말했는지** 가 한 화면에 온다.

    실측(2026-09-02): 네팔은 15개 중 8개를 세계 중앙값 아래로 신고했고, 그중에
    실험실과 감시가 있다.

    ★ 예측이 아니다 ★ 역량이 낮다고 발병한다는 뜻이 아니고, 높다고 안 난다는
    뜻도 아니다. 두 사실을 나란히 놓을 뿐이다.
    """
    from algorithms.disaster_watch import watched_countries
    from algorithms.ihr_capacity import country_capacity

    rows, unknown = [], []
    for iso3 in sorted(watched_countries()):
        capacity = country_capacity(iso3)
        if not capacity.get("available"):
            # ★ 신고가 없는 나라를 최악으로 세지 않는다 ★ 따로 담는다.
            unknown.append({"iso3": iso3, "reason": capacity.get("reason")})
            continue
        rows.append({
            "iso3": iso3,
            "year": capacity["year"],
            "behind_world_count": capacity["behind_world_count"],
            "behind_world": capacity["behind_world"],
        })
    rows.sort(key=lambda r: (-r["behind_world_count"], r["iso3"]))

    return {
        "watched_country_count": len(rows) + len(unknown),
        "countries": rows,
        "no_self_report": unknown,
        "is_self_assessed": True,
        "is_prediction": False,
        "note": "감시창이 열린 나라와 그 나라가 WHO 에 신고한 대비 역량을 "
                "나란히 놓은 것이다. 역량이 낮다고 발병한다는 뜻이 아니다.",
        "sources": ["GDACS (재난 경보)", "WHO IHR 자가평가(SPAR)"],
    }


@app.get("/api/biodefense/procurement", tags=["Stage 8: 바이오방어"])
def biodefense_procurement(days: int = 7):
    """★ 국가 조달 감시 ★ 정부가 지금 무엇을 사려고 하는가.

    국가사업은 어느 날 갑자기 오지 않는다 — **입찰공고로 먼저 나오고** 보통
    2~3주 뒤에 닫힌다. 늦게 알면 그걸로 끝이다.

    조달청 나라장터 공고를 바이오안보 낱말로 훑는다. 다만 나라장터 검색은
    느슨해서 무관한 공고가 딸려 나오므로(실측: '방역' 에 여행사 공고), 받아온
    뒤 **공고명·분류명에서 그 낱말을 우리가 다시 짚는다.** 못 짚으면 버린다.

    ★ '우리가 딸 수 있는 사업' 목록이 아니다 ★ 참가자격·실적요건은 공고문
    HWP 안에 있고 이 API 로는 보이지 않는다. 금액도 배정예산이지 낙찰가가 아니다.
    """
    from algorithms.procurement_watch import watch_bids

    return watch_bids(days=days)


@app.get("/api/biodefense/posture", tags=["Stage 8: 바이오방어"])
def biodefense_posture():
    """
    ★ 국가 바이오안보 대비 태세 ★ 병원체별로 **어디까지 와 있는가** 를 낸다.

    비축 유무(WHO ICG)만 보면 "없다" 가 다 같은 없음으로 보인다. 그런데
    뎅기·말라리아는 약이 이미 시판 중인데 비축 체계가 없는 것이고, 마버그·
    라싸열은 약 자체가 2상이다. **대응이 완전히 다르다.**

    그래서 비축(ICG)과 임상 파이프라인(ClinicalTrials.gov)을 겹쳐 다섯 칸으로
    나눈다: 비축 있음 / 후기 임상 완료 / 후기 임상 중 / 초기 임상 / 등록 연구 없음.

    ★ 점수를 내지 않는다 ★ "니파 32점" 같은 숫자를 만들면 그 32 를 설명할
    근거가 우리에게 없다. 임상시험 수도 준비도가 아니다 — 관심의 양이지
    물량이 아니고, 등록부에 없다고 개발이 없는 것도 아니다(군사·기밀 프로그램은
    등재되지 않는다).
    """
    from algorithms.countermeasure_pipeline import (
        PATHOGEN_QUERIES, fetch_pipeline, readiness_stage,
    )
    from algorithms.countermeasure_stockpile import stockpile_status

    rows, failed = [], 0
    for name_ko, query in PATHOGEN_QUERIES.items():
        pipeline = fetch_pipeline(query)
        if not pipeline.get("available"):
            failed += 1
        status = stockpile_status(name_ko)
        has = bool(status.get("has_global_stockpile"))
        rows.append({
            "pathogen": name_ko,
            "has_global_stockpile": has,
            "study_count": pipeline.get("study_count"),
            "furthest_phase_ko": pipeline.get("furthest_phase_ko"),
            **readiness_stage(pipeline, has),
        })

    order = {"stockpiled": 0, "approved_path": 1, "late_trial": 2,
             "early_trial": 3, "research_only": 4,
             "no_registered_trial": 5, "unknown": 6}
    rows.sort(key=lambda r: (order.get(r["stage"], 9), r["pathogen"]))
    return {
        "pathogens": rows,
        "pathogen_count": len(rows),
        "lookup_failed": failed,
        "sources": ["WHO ICG (국제 비상 비축)", "ClinicalTrials.gov API v2 (미국 NIH)"],
        "is_readiness_score": False,
        "limits": [
            "임상시험 수는 준비도가 아니다 — 관심의 양이지 물량이 아니다.",
            "3상을 통과해도 생산·비축은 전혀 다른 문제다.",
            "등록부에 없다고 개발이 없는 것이 아니다(군사·기밀 프로그램 미등재).",
            "한국 국가 비축은 비공개이며 이 보고에 포함되지 않는다.",
            "이 목록은 위험 순위가 아니다.",
        ],
    }


@app.get("/api/polar-watch", tags=["GAI"])
def polar_watch():
    """
    극지·영구동토 관찰 층(㉞) — 온난화로 동토 해빙(→고대 병원체, 2016 시베리아
    탄저 실증)과 극지 신규 발병(→H5N1 남극 도달)을 관찰한다. ★ 이건 '경보'가
    아니라 저확률·고충격 '관찰(watch)' 등급 — 경보 파이프라인과 섞지 않는다.
    기후 층(Open-Meteo)과 현지어 뉴스(극지 키워드)를 재사용. 값은 발병 위험
    측정이 아니라 관찰용 선행 신호 추정.
    """
    from algorithms.polar_signals import polar_watch_all
    return polar_watch_all()


@app.get("/api/threats", tags=["GAI"])
def threats():
    """
    현재 진행 중인 위협 — NLP 구조화 추출(⑦) 결과를 disease 기준으로 병합한
    중복제거 이벤트 목록(⑩). 같은 사건을 출처 여러 곳이 따로 보고해도
    하나로 합쳐 신뢰도가중 평균 점수를 매긴다. 이 경로는 결정론적(질병명
    기준)이라 매 대시보드 로드마다 빠르게 동작(clustering_method 참고).
    """
    return {"events": dedupe_events()}


@app.get("/api/threats/semantic", tags=["GAI"], dependencies=_auth)
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


# (날짜, 언어, 포맷) → 생성된 브리핑. 프로세스 메모리에만 둔다 — 재배포되면
# 비워지지만 그래도 하루 15번이 상한이라 목적(비용 상한)은 그대로 지켜진다.
_DAILY_BRIEF_CACHE: dict[tuple[str, str, str], dict] = {}


@app.get("/api/daily-brief", tags=["GAI"])
def daily_brief(lang: str = "ko", format: Optional[str] = None):
    """
    일일 브리핑(㊱) — 홈페이지 실시간 뉴스·팟캐스트 대본·유튜브 방송 러시트가
    공통으로 읽는 '하나의 재료'. 이미 계산된 중복제거 이벤트·경보·국가위험을 모아
    방송 러시트(headline/summary/segments[anchor_script,lower_third,visual_cue]/
    ticker/disclosure/closing) 한 벌로 조립한다. 페이퍼클립 같은 자동화 플랫폼은
    이 JSON만 받아서 영상·오디오를 찍어낸다.

    매일 같은 형태면 질리므로 여러 'AI 작가(포맷)'가 날짜별로 로테이션된다 —
    속보 데스크·심층 분석·현장 리포트·데이터 브리핑·앵커 대담(2인). format 파라미터
    (breaking|deepdive|field|data|duo)로 특정 포맷을 고정할 수 있고, 응답의
    available_formats로 목록을 준다. 포맷은 '표현 방식'만 바꾸고 숫자·등급·출처
    같은 사실은 절대 바꾸지 않는다.

    lang=ko|en 지원. ANTHROPIC_API_KEY가 있으면 앵커 대본을 그날 포맷 톤에 맞춰
    Claude로 다듬고(내용·숫자 불변), 없으면 결정론적 템플릿으로 폴백 —
    generation_method로 표시. is_official_alert=False이며, 새 위협이 없으면
    quiet_day=True로 조용한 날을 조용하게 전한다(없는 위기를 지어내지 않음).
    """
    from algorithms.daily_brief import generate_daily_brief

    # ★ 캐시 ★ 이 엔드포인트는 인증이 없고(홈페이지가 직접 부른다) 요청마다
    # Claude로 앵커 대본을 다듬는다 — 즉 **방문자 수만큼 돈이 나간다.** 런칭 후
    # 트래픽이 붙으면 그대로 비용이 되고, 악의적으로 반복 호출하면 크레딧이 마른다.
    # 인증을 걸면 홈페이지가 깨지므로 대신 (날짜·언어·포맷)으로 캐시한다.
    # 포맷 5종 × 언어 3종 = 하루 최대 15번 생성. 트래픽이 아무리 와도 그 이상은 없다.
    # 브리핑은 하루 한 번 만들어 하루 종일 같은 내용을 트는 방송이라, 캐시가
    # 성능 최적화가 아니라 원래 의미에 맞는 동작이다.
    today = dt.date.today().isoformat()
    cache_key = (today, lang, format or "auto")
    cached = _DAILY_BRIEF_CACHE.get(cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    brief = generate_daily_brief(lang=lang, api_key=api_key, fmt=format)

    # 날짜가 바뀌면 어제 것은 버린다(무한 증가 방지).
    for stale in [k for k in _DAILY_BRIEF_CACHE if k[0] != today]:
        _DAILY_BRIEF_CACHE.pop(stale, None)
    _DAILY_BRIEF_CACHE[cache_key] = brief
    return brief


@app.get("/api/daily-brief/archive", tags=["GAI"])
def daily_brief_archive(lang: str = "ko", limit: int = 30):
    """스케줄러가 매일 자동 생성해 보관한 브리핑 이력(가벼운 메타). 브리핑
    트랙레코드가 쌓이는 곳 — 페이퍼클립이 과거 방송을 다시 받아갈 수도 있다."""
    return {"briefs": db.list_daily_briefs(lang=lang, limit=limit)}


@app.get("/api/daily-brief/archive/{brief_date}", tags=["GAI"])
def daily_brief_archive_one(brief_date: str, lang: str = "ko"):
    """특정 날짜의 보관된 브리핑 전체(방송 러시트 그대로)."""
    brief = db.get_daily_brief(brief_date, lang)
    if brief is None:
        raise HTTPException(status_code=404, detail=f"보관된 브리핑 없음: {brief_date} ({lang})")
    return brief


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

    생성 직후 존재증명(Phase 44, OpenTimestamps/비트코인)을 best-effort로
    제출한다 — 캘린더 서버가 느리거나 응답 없어도 예측 저장 자체는 절대
    막지 않는다(실패해도 조용히 넘어가고, ots_proof_hex는 null로 남음).
    """
    prediction = db.create_prediction(req.country, req.disease, req.risk_score, req.basis)
    try:
        from algorithms.prediction_timestamp import canonical_hash, submit_timestamp
        digest_hex = canonical_hash(prediction)
        proof_hex = submit_timestamp(digest_hex)
        if proof_hex:
            prediction = db.set_prediction_timestamp(prediction["id"], digest_hex, proof_hex)
    except Exception as e:
        # 봉인 실패가 예측 기록을 막으면 안 된다(설계 원칙). 다만 조용히 넘기면
        # 캘린더 서버가 몇 주째 죽어 있어도 모른 채 '봉인된 트랙레코드'를 주장하게
        # 된다 — 그건 증거가 아니라 착각이다. 기록은 남기고 진행한다.
        _log_error(f"예측 봉인 실패(id={prediction.get('id')}): {type(e).__name__}: {str(e)[:150]}")
    return prediction


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


@app.get("/api/predictions/scorecard", tags=["예측 검증"])
def prediction_scorecard(country: Optional[str] = None):
    """예측 채점표 — 적중률·Brier·보정(calibration).

    ★ 적중률만 보지 말 것 ★ 쉬운 예측만 골라 담으면 적중률은 얼마든지 올라간다.
    - **Brier**: 확신했는데 틀리면 큰 벌점이라 골라 담기를 막는다(낮을수록 좋음).
    - **보정**: "0.8이라고 말한 것들이 실제로 80% 맞았는가". 재보험·보험이
      적중률보다 먼저 보는 지표다. 이게 어긋나면 신뢰도 숫자에 의미가 없다.
    - **overdue**: 판정 기한이 지났는데 판정 안 한 것. 방치하면 불리한 예측만
      남아 성적이 부풀려지므로 반드시 함께 본다.

    채점 형식(판정 기준·기한·신뢰도) 도입 이전 기록은 `unscoreable_legacy`로 빼고
    집계하지 않는다 — 사후에 만든 기준은 증거가 아니기 때문이다.
    """
    from algorithms.prediction_scoring import score
    return score(db.list_predictions(country=country))


class PredictionVerify(BaseModel):
    actual_result: str = Field(..., description="실제 발생 여부/내용")
    correct: Optional[bool] = Field(None, description="예측이 맞았는지(outcome을 쓰면 생략 가능)")
    lead_days: Optional[int] = Field(None, description="공식 발표 대비 선행 일수 (양수=먼저 감지)")
    outcome: Optional[str] = Field(
        None,
        description="correct | incorrect | ambiguous | cancelled. "
                    "참/거짓으로 못 나누는 경우를 억지로 밀어넣지 않기 위한 항목 — "
                    "ambiguous·cancelled는 채점에서 빼되 건수는 센다.",
    )
    resolution_sources: Optional[list[str]] = Field(
        None, description="무엇을 보고 그렇게 판정했는지(URL·문서명). 없으면 판정을 되짚을 수 없다."
    )

@app.get("/api/predictions/{prediction_id}/timestamp-proof", tags=["예측 검증"])
def prediction_timestamp_proof(prediction_id: int):
    """
    존재증명(Phase 44) 상태 조회 — 이 예측을 그 시각에 이미 갖고 있었다는
    증명이 비트코인 블록체인에 새겨졌는지 확인. 제출 직후엔 며칠간 pending이
    정상(비트코인 블록 확정에 몇 시간~하루 소요). '예측이 맞았다'와는 무관한
    별개 증명임을 항상 note로 명시.
    """
    prediction = db.get_prediction(prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="해당 prediction_id 없음")
    if not prediction.get("ots_proof_hex"):
        return {"data_available": False, "reason": "존재증명 미제출(생성 시 캘린더 서버 응답 없었음)"}

    from algorithms.prediction_timestamp import check_timestamp
    result = check_timestamp(prediction["content_hash"], prediction["ots_proof_hex"])
    result["submitted_at"] = prediction.get("ots_submitted_at")
    return result


@app.post("/api/predictions/{prediction_id}/verify", tags=["예측 검증"], dependencies=_auth)
def verify_prediction(prediction_id: int, req: PredictionVerify):
    """예측을 실제 결과로 검증·채점."""
    try:
        result = db.verify_prediction(
            prediction_id, req.actual_result, req.correct, req.lead_days,
            outcome=req.outcome, resolution_sources=req.resolution_sources,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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


class GenomeScreenRequest(BaseModel):
    sequence: str = Field(..., description="뉴클레오타이드 서열(FASTA 헤더·공백 허용, U→T 자동)")
    reference_sequences: Optional[list[str]] = Field(
        None, description="같은 계통의 실제 공개 자연서열(GenBank 등, 3개 이상 권장). 주어지면 "
                           "임의 전역 임계값 대신 이 서열 집합과의 실측 z-score·백분위를 함께 반환.")
    use_evo2: bool = Field(
        False, description="Evo2(유전체 파운데이션 모델)로 '순서의 자연스러움'을 추가 실측할지. "
                           "CAI·CpG 같은 점통계는 조성만 보므로 조성은 자연스럽되 순서가 부자연스러운 "
                           "서열을 놓친다. 켜면 NVIDIA NIM을 호출하므로 수 초~수십 초 더 걸림. "
                           "최소 524bp(context 512 + 12) 이상 연속 구간 필요.")
    use_msa: bool = Field(
        False, description="자연 상동체 커버리지를 상동성 DB 검색으로 실측할지. "
                           "'자연계에 이 서열 전체를 설명하는 단백질이 있는가'를 보고, 없으면 "
                           "여러 출처를 이어붙인 재조합·키메라 후보로 플래그. Evo2와 달리 "
                           "학습 모델이 아니라 DB 검색이라 **바이러스에도 유효**함(실측 확인). "
                           "최장 ORF를 자동 번역해 검색하며, 1회에 약 40초 걸림.")
    organism_domain: str = Field(
        "unknown", description="서열의 분류군 — Evo2 적용범위 판정용. "
                               "bacteria_archaea(세균·고균: 탄저·페스트 등) / eukaryote(진핵) / "
                               "phage(세균 감염 바이러스) 는 판정 가능. "
                               "eukaryotic_virus(코로나·독감·에볼라 등 진핵숙주 감염 바이러스)는 "
                               "Evo2 학습에서 제외되어 자연서열도 30%대라 판정 불가 — 점수만 참고로 "
                               "보고하고 플래그는 올리지 않음. 미선언(unknown)도 같게 처리.")


@app.post("/api/synthetic-threat/genome-screen", tags=["Stage 0: 합성위협 탐지"], dependencies=_auth)
def synthetic_threat_genome_screen(req: GenomeScreenRequest):
    """방어적 유전체 스크리닝 — 서열의 자연스러움 통계(CAI·CpG O/E·엔트로피·
    다이뉴클레오타이드 편향·제한효소부위)를 '실제로 계산'해 인공 설계 신호를 플래그.
    판정이 아니라 추가검토 우선순위 도구(is_screening_only=True) — 최종 판단은
    전문가·계통발생·습식실험 확인 필요. 서열 설계·합성·회피는 제공하지 않음.
    리딩프레임이 안 맞아도 6-frame 최장 ORF를 자동탐지해 CAI를 계산하고,
    모호 염기(N 등)는 조용히 삭제·이어붙이지 않고 가장 긴 연속 구간만 분석함.
    [사내 R&D 프로그램] HEIMDALL — 아이기론 R&D 연구센터, 사내 최고 보안등급."""
    from algorithms.genome_signals import screen_sequence
    from algorithms.classified_programs import classification
    result = screen_sequence(req.sequence, reference_sequences=req.reference_sequences)
    if req.use_evo2:
        # 점통계(조성)가 못 보는 '순서의 자연스러움'을 Evo2로 추가 실측.
        # 외부 API 장애가 순수 통계 결과까지 막지 않도록 실패는 결과에 담아 반환만 한다.
        from algorithms.evo2_naturalness import score_naturalness
        evo2 = score_naturalness(req.sequence, organism_domain=req.organism_domain)
        result["evo2_naturalness"] = evo2
        if evo2.get("ok"):
            result.setdefault("flags", []).extend(evo2.get("flags") or [])
            result["flag_count"] = len(result["flags"])
    if req.use_msa:
        # Evo2가 못 보는 바이러스도 커버하는 축 — 자연 상동체가 전장을 덮는가.
        from algorithms.msa_homology import assess_from_nucleotide
        msa = assess_from_nucleotide(req.sequence)
        result["msa_homology"] = msa
        if msa.get("ok"):
            result.setdefault("flags", []).extend(msa.get("flags") or [])
            result["flag_count"] = len(result["flags"])
    result["classification"] = classification("stage0")
    return result


class BulletinTableRequest(BaseModel):
    url: str = Field(..., description="보건 보고서 PDF 주소(WHO AFRO 주간 상황보고서, "
                                      "각국 보건부 역학주보 등). 공개 문서만.")
    max_pages: int = Field(3, ge=1, le=10, description="앞에서부터 파싱할 페이지 수. "
                                                       "페이지마다 VLM 호출 1회라 기본값을 작게 둠.")


@app.post("/api/bulletin/extract-tables", tags=["데이터 수집"], dependencies=_auth)
def bulletin_extract_tables(req: BulletinTableRequest):
    """보건 보고서 PDF의 '표'를 구조화 추출 — 지금까지 못 읽던 신호를 연다.

    WHO AFRO 주간보고서 같은 문서엔 국가·질병별 확진자·사망자·치명률이 표로
    들어있는데, 기존 텍스트 추출은 글자가 깨지고(multiple→mul2ple) 표가 뭉개져서
    숫자를 신호로 쓸 수 없었다. VLM(nemotron-parse)으로 표 구조를 복원하고,
    뽑은 숫자를 pdftotext 원문과 교차검증해 오독 후보를 표시한다.
    기계 추출값이므로 is_machine_extracted=True — 사람 검증본이 아니다."""
    import requests as _rq
    from algorithms.pdf_table_extract import extract_tables

    if not req.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="http(s) 주소만 허용")
    try:
        r = _rq.get(req.url, timeout=120, headers={"User-Agent": "Mozilla/5.0 (EpiWeather/1.0)"})
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PDF 내려받기 실패: {e}")
    if not r.content[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="PDF 파일이 아님")
    return extract_tables(r.content, max_pages=req.max_pages)


class BulletinIngestRequest(BaseModel):
    url: str = Field(..., description="보건 보고서 PDF 주소(WHO AFRO 주간보고서 등). 공개 문서만.")
    max_pages: int = Field(4, ge=1, le=10, description="파싱할 페이지 수. 표가 있을 법한 페이지를 자동 선택함.")
    source: str = Field("who_afro_bulletin", description="신호 출처 라벨(중복 판정 단위).")
    signal_date: Optional[str] = Field(None, description="보고서 기준일(YYYY-MM-DD). 없으면 비움.")
    dry_run: bool = Field(False, description="True면 DB에 넣지 않고 무엇이 들어갈지만 돌려줌.")


@app.post("/api/bulletin/ingest", tags=["데이터 수집"], dependencies=_auth)
def bulletin_ingest(req: BulletinIngestRequest):
    """보건 보고서 PDF → 표 추출 → 신호 정규화 → extracted_signals 적재(한 번에).

    지금까지 기계가 못 읽던 표 속 수치(국가·질병별 확진·사망·치명률)를 경보
    엔진이 보는 신호로 만든다. 비질병 이벤트(사이클론·인도적 위기)는 적재하지
    않는다 — known_disease가 '설명 불가 → 즉시경보'를 뜻하는 스키마라 그대로
    넣으면 가짜 경보가 나기 때문. 같은 보고서를 두 번 넣어도 중복은 걸러진다.
    신뢰도는 숫자 교차검증 결과에 따라 갈린다(전부 일치 0.90 / 미검증 섞임 0.70)."""
    import requests as _rq
    from algorithms.pdf_table_extract import extract_tables
    from algorithms.bulletin_signals import extract_signals
    from algorithms.bulletin_ingest import ingest, to_extracted_signal

    if not req.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="http(s) 주소만 허용")
    try:
        r = _rq.get(req.url, timeout=120, headers={"User-Agent": "Mozilla/5.0 (EpiWeather/1.0)"})
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PDF 내려받기 실패: {e}")
    if not r.content[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="PDF 파일이 아님")

    parsed = extract_tables(r.content, max_pages=req.max_pages)
    if not parsed.get("ok"):
        return {"ok": False, "stage": "extract_tables", "reason": parsed.get("reason")}
    found = extract_signals(parsed, source=req.source, signal_date=req.signal_date)

    if req.dry_run:
        preview = [p for p in (to_extracted_signal(s, source=req.source)
                               for s in found["signals"]) if p]
        return {"ok": True, "dry_run": True, "pages_selected": parsed.get("pages_selected"),
                "signals_found": found["signal_count"], "would_insert": len(preview),
                "preview": preview[:20]}

    db.init_db()
    result = ingest(found["signals"], source=req.source, dbmod=db)
    result["pages_selected"] = parsed.get("pages_selected")
    result["signals_found"] = found["signal_count"]
    result.pop("rows", None)          # 응답이 너무 길어지지 않게 요약만
    return result


@app.post("/api/bulletin/collect", tags=["데이터 수집"], dependencies=_auth)
def bulletin_collect(source: str = "who_sitrep_bundibugyo",
                     topic: Optional[str] = "Bundibugyo",
                     limit: int = 6, max_new: int = 2):
    """새로 올라온 WHO 상황보고서만 수집·적재(스케줄러가 하루 1회 부르는 것과 동일).

    이미 적재한 회차는 PDF를 열지 않으므로 새 보고서가 없으면 비용이 0이다.
    max_new로 한 번에 파싱할 회차 수를 묶는다 — 과거분을 채우려면 여러 번 호출."""
    from algorithms.bulletin_collect import collect_new_reports

    db.init_db()
    return collect_new_reports(db, source=source, topic=topic,
                               limit=limit, max_new=max_new)


@app.get("/api/bulletin/trend", tags=["데이터 수집"])
def bulletin_trend(source: str = "who_sitrep_bundibugyo", disease: Optional[str] = None,
                   metric: str = "confirmed", days: int = 180, limit: int = 500):
    """적재된 보고서 신호로 지역별 추이를 낸다 — "지금 몇 명"이 아니라 "늘고 있느냐".

    적재 시점엔 비교 대상이 없어 급증·감소를 쓰지 않지만(진행중/불명만), 회차가
    쌓이면 여기서 판정한다. 누적이 줄어든 경우는 '재조정'으로 표시한다 — WHO가
    사례 재분류로 누적을 하향하는 일이 있어 호전으로 읽으면 안 되기 때문.
    회차가 2개 미만인 지역은 판정하지 않는다(assessed=False)."""
    from algorithms.bulletin_trend import assess

    rows = db.list_recent_signals_by_source(source, days=days, limit=limit)
    if not rows:
        return {"ok": False, "reason": f"'{source}' 출처의 최근 {days}일 신호 없음",
                "results": []}
    return assess(rows, disease=disease, metric=metric)


class BiodefenseReadinessRequest(BaseModel):
    countermeasures: Optional[list] = Field(None, description="비축 대응제 목록 [{name,type,targets,declared_efficacy,domestic_producible}]")
    threats: Optional[list] = Field(None, description="위협 목록 [{pathogen,severity}]")


@app.post("/api/biodefense/readiness", tags=["Stage 8: 바이오방어"], dependencies=_auth)
def biodefense_readiness(req: BiodefenseReadinessRequest):
    """Stage 8 대응제 준비태세 — 가짜 분자 중화 예측이 아니라 '실제 커버리지·생산
    주권 격차'를 선언 효능으로 집계. 어떤 위협을 비축이 못 막는가 + 막는 것 중 국산
    생산이 안 되는 게 뭔가(주권 격차). 요청 바디가 없으면: ①등록된 실제 비축
    데이터(`/api/biodefense/stockpile`)가 있으면 그걸 사용, ②없으면 시연용
    예시(is_illustrative)로 폴백. 변이별 분자 중화 예측은 Phase 2(BioNeMo·CEPI)
    통합 — 지어내지 않음.
    [사내 R&D 프로그램] VALHALLA — 아이기론 R&D 연구센터, 사내 최고 보안등급(인증 필수)."""
    from algorithms.biodefense_readiness import compute_readiness, illustrative_readiness, DEFAULT_THREATS
    from algorithms.classified_programs import classification
    if req.countermeasures and req.threats:
        result = compute_readiness(req.countermeasures, req.threats)
    else:
        stored = db.list_countermeasures()
        if stored:
            threats = req.threats or DEFAULT_THREATS
            result = compute_readiness(stored, threats)
            result["is_illustrative"] = False
            result["note"] = (
                "등록된 실제 비축 데이터 기반. 위협 목록: "
                + ("요청값 사용" if req.threats else "기본 감시 병원체 목록(H5N1·Ebola·MERS·Dengue·Novel) 사용")
            )
        else:
            result = illustrative_readiness()
    result["classification"] = classification("stage8")
    return result


class CountermeasureCreate(BaseModel):
    name: str = Field(..., description="대응제 이름")
    type: Optional[str] = Field(None, description="유형 (antiviral/vaccine/mAb 등)")
    targets: list[str] = Field(..., min_length=1, description="대응 병원체 목록")
    declared_efficacy: Optional[float] = Field(None, description="선언된 효능(0~1, 라벨/문헌 근거)")
    domestic_producible: bool = Field(False, description="국내 생산 가능 여부")
    courses: Optional[int] = Field(None, description="비축 인분(선택)")
    population: Optional[int] = Field(None, description="대상 인구(선택, 물류 계산용)")
    attack_rate: Optional[float] = Field(None, description="예상 발병률(0~1, 선택, 물류 계산용)")


@app.get("/api/biodefense/stockpile", tags=["Stage 8: 바이오방어"])
def list_biodefense_stockpile():
    """등록된 실제 대응제 비축 목록 조회(읽기 전용, 인증 불필요)."""
    return {"items": db.list_countermeasures()}


@app.post("/api/biodefense/stockpile", tags=["Stage 8: 바이오방어"], dependencies=_auth)
def create_biodefense_stockpile(req: CountermeasureCreate):
    """실제 대응제 비축 항목 등록 — 등록해두면 `/api/biodefense/readiness`가
    요청 바디 없이도 이 데이터로 계산(더 이상 매번 통째로 안 넣어도 됨)."""
    return db.create_countermeasure(
        req.name, req.type, req.targets, req.declared_efficacy, req.domestic_producible,
        req.courses, req.population, req.attack_rate,
    )


@app.delete("/api/biodefense/stockpile/{item_id}", tags=["Stage 8: 바이오방어"], dependencies=_auth)
def delete_biodefense_stockpile(item_id: int):
    """등록된 비축 항목 삭제."""
    if not db.delete_countermeasure(item_id):
        raise HTTPException(status_code=404, detail="해당 item_id 없음")
    return {"deleted": True, "id": item_id}


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


@app.get("/api/global-watch", tags=["Stage 6: AI 추론"], dependencies=_auth)
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
        ("ebola_drc_2026", "에볼라 DRC 2026 (분디부조형)", [
            ("2026-05-09", "msf_first_alert",   "MSF 현장 첫 경보", "MSF 보고서", "media"),
            ("2026-05-15", "drc_official",       "DRC·우간다 보건부 공식 선언 — 분디부조(Bundibugyo)형", "DRC Ministry of Health", "who"),
            ("2026-05-16", "who_pheic",          "WHO PHEIC 선언", "WHO DON", "who"),
            ("2026-05-17", "wiki_spike",         "Wikipedia 영어판 조회수 급증", "Wikimedia API", "ai_detected"),
            ("2026-06-25", "status_update",      "확진 896명·사망 232명", "WHO Situation Report", "who"),
            # 서울신문 2026-08-01 보도(2026-07-29 기준): 역대 콩고 최대·전세계 2위 규모,
            # 2018년比 6배 빠른 확산. 분디부조형은 백신·치료제 모두 없음.
            ("2026-07-29", "status_update",      "확진 3,532명·사망 1,556명·치명률 44.1% (2018년比 6배 빠름)", "서울신문/WHO·Africa CDC", "media"),
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
    days: int = 180,
):
    """
    디지털 트윈 — 전 세계 전파 시뮬레이션 (159개국).

    발원지에서 **육로 국경**(314개)과 **항공 노선**(11개)을 타고 각 나라에
    언제 도달하는지 예측한다.

    origin: 도시 이름(Kinshasa, Bangkok …) 또는 ISO3 국가코드(NGA, BRA, IND)
    threat: flu | novel | severe

    ★ 결과를 읽을 때 ★ 안 걸린 나라는 두 부류로 나뉘어 나온다.
      * `not_reached`      — 경로는 있는데 기간 안에 안 온 나라
      * `no_route_modeled` — **가는 길 자체를 모르는 나라.** 안전하다는 뜻이
                             아니다. 항공 노선 실측이 11개뿐이라 아메리카
                             대륙은 통째로 여기 들어간다.
    한계는 `limits` 에 같이 실려 나간다.
    """
    from algorithms.digital_twin import simulate_spread
    if threat not in ("flu", "novel", "severe"):
        raise HTTPException(status_code=422, detail="threat는 flu|novel|severe 중 하나")
    # 상한도 180 → 365 로. 기본값이 180이 되면서 상한과 같아져 더 길게 볼 수 없었다.
    return simulate_spread(origin=origin, threat=threat, days=min(days, 365))


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
    이동성 신호 — OpenSky API로 주요 발병국 공항 최근 1시간 항공편 수 조회.
    항공편 급감 = 해당 지역 유행 간접 신호.

    OpenSky는 무료지만 익명 쿼터가 거의 없어 OPENSKY_CLIENT_ID/SECRET(OAuth2)을
    쓴다. 응답의 `auth_status`·`failure_reasons`가 **왜 못 가져왔는지**를 담는다
    — 전 공항 실패 시 인증 거부인지 IP 차단인지 여기서 갈린다.

    ★ 이 엔드포인트는 '부활 확인용'으로 일부러 살려둔 것이다 (2026-08-28) ★
    Mobility 는 매시간 수집에서 빠졌다(source_health.RETIRED_SOURCES). Railway(SFO)
    에서 OpenSky 로 TCP 연결이 성립하지 않아 매 주기 20초를 버리기 때문이다.
    다만 **닿는지 확인할 방법까지 없애면 영영 되살릴 수 없으므로** 여기는 남긴다.
    `auth_status` 가 `authenticated` 로 돌아오면 그때 RETIRED_SOURCES 에서 한 줄을
    지우면 된다. 수집 코드는 그대로 있다.
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

    ★ 재난 감시창을 같이 반영한다 (2026-08-31) ★
    예전엔 이 엔드포인트가 감시창 없이 불렀다. 수집기는 넘기는데 API 는 안
    넘겼다. 그래서 **같은 피드가 수집기에서는 고경보인데 API 로 보면 평범한
    피드로 보였다.**

    실측: 2026-08-26 네팔 홍수로 감시창이 열려 있는 동안 `gn_np` 는 0.11 이었다.
    평시 문턱 0.15 에는 못 미치고 감시창 문턱 0.08 은 넘는 값 — 수집기는
    고경보로 올렸는데 API 응답에는 창이 열렸다는 표시조차 없었다. 대시보드나
    기자가 API 를 보면 실제와 다른 그림을 본다.

    감시창을 못 읽으면 조용히 평시 문턱으로 돌지 않고 `watch_windows_error`
    로 밝힌다 — 문턱이 말없이 달라지면 고경보 수를 아무도 해석할 수 없다.

    참고: 이 엔드포인트는 LLM 재분류를 돌리지 않는다(호출마다 쿼터를 태우게
    되므로). 그래서 비율이 키워드 기준이라 수집기 값과 다를 수 있다.
    """
    from algorithms.local_news import fetch_all_local_news
    from algorithms.disaster_watch import open_windows

    try:
        windows, windows_error = open_windows(), None
    except Exception as e:                       # noqa: BLE001 - 사유를 들고 간다
        windows, windows_error = None, f"{type(e).__name__}: {str(e)[:150]}"

    out = fetch_all_local_news(watch_windows=windows)
    if windows_error:
        out["watch_windows_error"] = windows_error
    return out


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
    try:
        return fetch_groq_pulse(key)
    except Exception as e:
        # 예전엔 무엇이 잘못됐든 "Groq 응답 파싱 실패" 한 문장이었다.
        raise HTTPException(
            status_code=502, detail=f"Groq 호출 실패({type(e).__name__}): {e}"
        ) from e


@app.get("/api/news-pulse", tags=["Phase2"])
def news_pulse():
    """
    NewsWatch — GroqWatch 무료 대체 후보(2026-08-28).

    검색(Google News RSS·키 불필요)과 요약(Cerebras·하루 100만 토큰 무료)을
    분리했다. GroqWatch 는 compound-mini 가 서버 쪽에서 끌어온 검색결과가
    프롬프트의 96% 를 차지해 분당 8,000 토큰 한도를 매 주기 위협했는데,
    여기서는 **주입되는 검색량을 우리가 통제**한다(제목 40개·각 200자 상한).

    응답 형태는 `/api/groq-pulse` 와 의도적으로 동일하다 — 대조가 끝나고
    갈아끼울 때 소비하는 쪽을 안 건드려도 되게. `headline_count` 만 추가인데,
    이건 "얼마나 얕은가" 를 대조할 근거다. CEREBRAS_API_KEY 필요.
    """
    key = os.environ.get("CEREBRAS_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="CEREBRAS_API_KEY 환경변수 없음")
    from algorithms.news_watch import fetch_news_pulse
    try:
        return fetch_news_pulse(key)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"NewsWatch 호출 실패({type(e).__name__}): {e}"
        ) from e


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

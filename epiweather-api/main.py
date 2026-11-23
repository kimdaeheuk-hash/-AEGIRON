"""
아이기론 FastAPI 서비스
=======================
개편(2026-11-22) 뒤 남은 것은 사슬 하나다 — 극지(감지) → 헤임달(식별) → 발할라(대응 판정).
첫 고객은 정부·국가 바이오안보. 나머지 엔드포인트(전 세계 발병 경보·위험지수·예측·브리핑·
AI 추론 등)는 지웠다. 복원 기준 커밋: 83406e4 (`git checkout 83406e4 -- <경로>`).
계획: docs/아이기론_개편계획_2026-11.md

실행:
    cd epiweather-api
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import secrets
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import Depends, FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.background import BackgroundTask  # noqa: E402

import db  # noqa: E402
from algorithms import response_cache  # noqa: E402

app = FastAPI(
    title="아이기론 API",
    description="극지 → 헤임달 → 발할라: 깨어나거나 바뀐 위협을 우리 대응제가 막을 수 있는가",
    version="0.2.0",
)
db.init_db()

# ALLOWED_ORIGINS 환경변수로 배포된 프론트엔드 도메인을 추가할 수 있다(쉼표 구분).
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001",
                   "https://epiweather-web.vercel.app", *_extra_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 쓰기(POST) 엔드포인트 인증 ────────────────────────────────
# 조회(GET)는 공개, 상태를 바꾸는 엔드포인트만 X-API-Key 헤더로 보호한다.
# 키가 설정 안 돼 있으면 fail-closed(503). 다중 키: EPIWEATHER_API_KEYS="라벨1:키1,라벨2:키2".
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


# ── 헬스체크 ─────────────────────────────────────────────────
@app.get("/health", tags=["시스템"])
def health():
    return {"status": "ok", "version": "0.1.0", "engine": "역병예보 추론 엔진 v1"}


@app.get("/api/baikal", tags=["BAIKAL MOB"])
def baikal_state():
    """BAIKAL MOB — 상태변화 엔진(온톨로지 위층). 엔진별 최신 상태·언제부터·영향·최근 전이.

    스냅숏은 매시 수집 주기 끝에서 쌓인다. 스냅숏이 없거나 130분보다 낡으면
    `fresh=false` 와 `freshness_note` 로 그렇게 말한다(지금 상태로 읽지 말 것).
    """
    from algorithms.baikal import api_payload
    try:
        return api_payload()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"BAIKAL 조회 실패({type(e).__name__}): {e}"
        ) from e


@app.get("/api/baikal/transitions", tags=["BAIKAL MOB"])
def baikal_transitions(node: Optional[str] = None, limit: int = 50):
    """BAIKAL 전이 기록 — 상태가 바뀐 순간만(최신순). from_status=null 은 관측 시작."""
    from algorithms.ontology import NODES
    if node is not None and node not in NODES:
        raise HTTPException(status_code=400, detail=f"알 수 없는 node: {node}")
    entries = db.list_baikal_transitions(limit=limit, node=node)
    return {"entries": entries, "count": len(entries)}


@app.get("/api/variant-growth", tags=["후향 검증"])
def variant_growth():
    """헤임달 성장 신호 — 공개 빌드에서 '커지고 있는 계통'(최근 4주 vs 직전 4주 구성비 로그 변화).

    추정값이다. 매시 수집이 계산해 둔 저장본을 준다 — 아직 없으면(재시작 직후 등) 판정 안 함.
    """
    from algorithms import response_cache
    from algorithms.genomic_variants import GROWTH_CACHE_KEY
    hit = response_cache.peek(GROWTH_CACHE_KEY)
    if hit is None:
        return {"determined": False, "reason": "아직 계산된 성장 신호 없음(다음 수집 주기 뒤)", "builds": []}
    _, value = hit
    return {"determined": True, **value}


@app.get("/api/variant-ledger", tags=["후향 검증"])
def variant_ledger(build: Optional[str] = None,
                   transitions_only: bool = False, limit: int = 100):
    """변이 상태원장 — 매 수집 주기 Nextstrain 빌드별 우세 계통·신규 계통 기록.

    BAIKAL이 시스템 상태 전이를 적는다면, 여기는 병원체 자체의 상태 전이를
    적는다. transitions_only면 전이가 있었던 주기만 (none 제외).
    """
    from algorithms.variant_ledger import list_entries, list_transitions
    try:
        if transitions_only:
            entries = list_transitions(limit=limit)
        else:
            entries = list_entries(build=build, limit=limit)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"변이원장 조회 실패({type(e).__name__}): {e}"
        ) from e


@app.get("/api/valhalla/match-ledger", tags=["Stage 8: 바이오방어"])
def valhalla_match_ledger(days: int = 30, pathogen: Optional[str] = None,
                          verdict: Optional[str] = None, latest_only: bool = False):
    """대응제 매칭원장 — "오늘 이 비축이 이 변이를 막는가" 일일 판정 기록.

    holds(유지)/recheck(변이 전이로 재확인 필요)/gap(미커버)/unknown(판정불가).
    latest_only면 가장 최근 판정일의 전 위협 행 — 화면 '오늘의 판정'용.
    """
    from algorithms.match_ledger import latest_verdicts, list_verdicts
    try:
        entries = latest_verdicts() if latest_only else list_verdicts(
            days=days, pathogen=pathogen, verdict=verdict)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"매칭원장 조회 실패({type(e).__name__}): {e}"
        ) from e


@app.get("/api/valhalla/gap-map", tags=["Stage 8: 바이오방어"])
def valhalla_gap_map():
    """발할라 대응제 공백 지도 — WHO 2024 우선 병원체(2차 문헌 기반) × 백신·치료제·FDA 승인·진단·국산.

    칸마다 승인/임상/없음/판정 안 함/검색 불가. '없음'은 그 등록부에 없다는 뜻이다. 10분 캐시.
    """
    from algorithms.gap_map import current
    try:
        return response_cache.swr("valhalla_gap_map", 600, current)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공백 지도 실패({type(e).__name__}): {e}") from e


@app.get("/api/valhalla/country-posture", tags=["Stage 8: 바이오방어"])
def valhalla_country_posture(iso3: str = "KOR"):
    """국가별 대비 현황판(목연결) — WHO SPAR 신고 역량 + 매칭원장 최신 판정.

    ★ 정직 표기 ★ 역량 점수는 자가평가 신고치(측정치 아님)이고, 매칭 판정은
    위협×비축 기준이라 국가별이 아니다. 국가별 비축이 등록되면 국가별 판정으로
    확장한다. "자립까지 D+N" 수치는 플랫폼 소요일 실측이 없어 내지 않는다.
    """
    from algorithms.ihr_capacity import country_capacity
    from algorithms.match_ledger import latest_verdicts
    try:
        capacity = country_capacity(iso3)
        verdicts = latest_verdicts()
        counts: dict[str, int] = {}
        for v in verdicts:
            counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
        return {
            "iso3": (iso3 or "").strip().upper(),
            "capacity": capacity,
            "match_verdicts": verdicts,
            "verdict_counts": counts,
            "note": ("역량은 자가평가 신고치. 매칭 판정은 위협×비축 기준"
                     "(국가별 아님). D+N 수치는 플랫폼 소요일 실측 전이라 내지 않음."),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"국가 현황 조회 실패({type(e).__name__}): {e}"
        ) from e


@app.get("/api/admin/db-backup", tags=["시스템"], dependencies=_auth)
def db_backup():
    """
    운영 DB(SQLite) 스냅샷 다운로드 — Railway 같은 컨테이너 배포 환경은 영구
    볼륨을 마운트하지 않으면 재배포할 때 파일시스템이 초기화될 수 있음.
    이러면 예측 트랙레코드·검증 이력 등 시간이 지나야 쌓이는 자산이 전부
    사라질 수 있어(⑲), 이 엔드포인트를 로컬 머신에서 주기적으로 호출해
    타임스탬프 백업을 남긴다(GitHub Actions `ledger-backup` 이 매일 부른다).

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


@app.get("/api/polar-watch", tags=["GAI"])
def polar_watch():
    """
    극지·영구동토 관찰 층(㉞) — 온난화로 동토 해빙(→고대 병원체, 2016 시베리아
    탄저 실증)과 극지 신규 발병(→H5N1 남극 도달)을 관찰한다. ★ 이건 '경보'가
    아니라 저확률·고충격 '관찰(watch)' 등급 — 경보 파이프라인과 섞지 않는다.
    기후 층(Open-Meteo)과 현지어 뉴스(극지 키워드)를 재사용. 값은 발병 위험
    측정이 아니라 관찰용 선행 신호 추정.
    """
    from algorithms.polar_signals import POLAR_CACHE_KEY, POLAR_CACHE_TTL_S, polar_watch_all
    return response_cache.swr(POLAR_CACHE_KEY, POLAR_CACHE_TTL_S, polar_watch_all)


@app.get("/api/observations/history", tags=["GAI"])
def observations_history(layer: str, target: str | None = None, metric: str | None = None,
                         days: int = 30, limit: int = 2000):
    """관측값 시계열(2026-11-15) — 극지·기후·토지·삼림·무역·재난·여행경보를 매시간 저장한 이력.

    한 행 = 한 대상의 한 값. observed_at 은 그 값이 처음 계산된 시각, confirmed_at 은 같은 값을 마지막으로
    다시 확인한 시각, checks 는 같은 값으로 확인된 횟수. measured(출처 측정값)와 derived(우리가 계산한
    해석값·추정)를 나눠 준다. status='undetermined' 는 그 시각에 못 읽었다는 뜻이다(0 이 아님).
    저장은 2026-11-15 배포부터 — 그 전 이력은 없다.
    """
    from algorithms.observation_store import LAYERS

    if layer not in LAYERS:
        raise HTTPException(status_code=400, detail=f"layer 는 {', '.join(LAYERS)} 중 하나")
    days = max(1, min(days, 365))
    limit = max(1, min(limit, 10000))
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    rows = db.observation_history(layer, target=target, metric=metric, since=since, limit=limit)
    return {
        "layer": layer, "target": target, "metric": metric, "days": days,
        "rows": rows, "row_count": len(rows), "truncated": len(rows) >= limit,
        "fields": {
            "observed_at": "이 값이 처음 계산된 시각(UTC)",
            "confirmed_at": "같은 값을 마지막으로 다시 확인한 시각(UTC)",
            "measured": "출처가 준 측정값",
            "derived": "우리가 계산한 해석값(추정·지수 — 측정 아님)",
            "status": "ok | undetermined(그 시각에 못 읽음 — 0 이 아님)",
        },
        "history_starts": "2026-11-15 배포부터 저장 — 그 전 이력 없음",
    }


# ★ 요청 상한 (2026-11-02) ★ Evo2(윈도당 호출)·MSA(번역+검색) 비용이 길이에
# 비례해 긴 서열은 HTTP 타임아웃 안에 못 끝난다. 상한을 넘기면 413으로 돌려주고
# 구간을 나눠 보내라고 말한다(조용히 자르면 리딩프레임·문맥이 깨진다).
# 429(호출 빈도 제한)는 별도 과제 — 단독 프로세스+쓰기 인증이라 남용 경로가 좁다.
GENOME_SCREEN_MAX_SEQUENCE_CHARS = 1_000_000


GENOME_SCREEN_MAX_REFERENCES = 50


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


def _check_genome_screen_limits(req: GenomeScreenRequest) -> None:
    if len(req.sequence) > GENOME_SCREEN_MAX_SEQUENCE_CHARS:
        raise HTTPException(
            status_code=413,
            detail=(f"서열 {len(req.sequence)}자 — 상한 {GENOME_SCREEN_MAX_SEQUENCE_CHARS}자 초과. "
                    "구간을 나눠 보내라(서버가 임의로 자르지 않는다)"))
    refs = req.reference_sequences or []
    if len(refs) > GENOME_SCREEN_MAX_REFERENCES:
        raise HTTPException(
            status_code=413,
            detail=(f"레퍼런스 {len(refs)}개 — 상한 {GENOME_SCREEN_MAX_REFERENCES}개 초과"))
    for i, ref in enumerate(refs):
        if len(ref) > GENOME_SCREEN_MAX_SEQUENCE_CHARS:
            raise HTTPException(
                status_code=413,
                detail=(f"레퍼런스 {i + 1}번 {len(ref)}자 — 상한 초과. 구간을 나눠 보내라"))


@app.post("/api/synthetic-threat/genome-screen", tags=["Stage 0: 합성위협 탐지"], dependencies=_auth)
def synthetic_threat_genome_screen(req: GenomeScreenRequest):
    """방어적 유전체 스크리닝 — 서열의 자연스러움 통계(CAI·CpG O/E·엔트로피·
    다이뉴클레오타이드 편향·제한효소부위)를 '실제로 계산'해 인공 설계 신호를 플래그.
    판정이 아니라 추가검토 우선순위 도구(is_screening_only=True) — 최종 판단은
    전문가·계통발생·습식실험 확인 필요. 서열 설계·합성·회피는 제공하지 않음.
    리딩프레임이 안 맞아도 6-frame 최장 ORF를 자동탐지해 CAI를 계산하고,
    모호 염기(N 등)는 조용히 삭제·이어붙이지 않고 가장 긴 연속 구간만 분석함. 인증 필수."""
    _check_genome_screen_limits(req)
    from algorithms.genome_signals import screen_sequence
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
    return result


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
    통합 — 지어내지 않음. 인증 필수."""
    from algorithms.biodefense_readiness import compute_readiness, illustrative_readiness, DEFAULT_THREATS
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


# ── 시스템 상태 ─────────────────────────────────────────────
def _file_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "updated_at": None, "size_bytes": 0}
    stat = path.stat()
    return {"exists": True,
            "updated_at": dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat(),
            "size_bytes": stat.st_size}


def _recent_errors(limit: int = 10) -> list[dict]:
    """collector 가 error_log.txt 에 남긴 최근 에러. '<시각> | <출처> | <메시지>' 형식."""
    err_file = Path(__file__).parent / "data" / "error_log.txt"
    if not err_file.exists():
        return []
    with open(err_file, encoding="utf-8") as f:
        rows = f.readlines()[-limit:]
    out = []
    for line in rows:
        parts = line.rstrip("\n").split(" | ", 2)
        if len(parts) == 3:
            out.append({"at": parts[0], "context": parts[1], "message": parts[2]})
    return out


def _status_payload() -> dict:
    """운영 상태 — 수집이 살아 있는지, 세 층의 소스가 건강한지, 기준 스냅샷이 묵지 않았는지."""
    from algorithms.reference_snapshots import report as snapshot_report
    from algorithms.source_health import source_health_report

    data_dir = Path(__file__).parent / "data"
    last_weekly = _load_last_weekly_run()
    try:
        snapshots = snapshot_report()
    except Exception as e:  # noqa: BLE001 — 상태 한 칸이 전체를 죽이지 않게
        snapshots = {"error": f"{type(e).__name__}: {str(e)[:150]}"}
    return {
        "scope": "극지 → 헤임달 → 발할라 (+ BAIKAL MOB 상태변화 엔진)",
        "scheduler_enabled": os.environ.get("EPIWEATHER_SCHEDULER", "on").lower() != "off",
        "last_weekly_job_at": last_weekly.isoformat() if last_weekly else None,
        "files": {"signals_log": _file_status(data_dir / "signals_log.jsonl")},
        "db_table_counts": db.table_counts(),
        "source_health": source_health_report(),
        "reference_snapshots": snapshots,
        "recent_errors": _recent_errors(),
    }


@app.get("/api/status", tags=["시스템"])
def status():
    """운영 모니터링 — 1분 응답 캐시."""
    return response_cache.swr("status", 60, _status_payload)


# ── 스케줄러 ──────────────────────────────────────────────────
# API 프로세스 안에서 매시 수집을 돌린다. EPIWEATHER_SCHEDULER=off 로 끈다.
_WEEKLY_INTERVAL_SEC = 7 * 24 * 3600  # 발할라 기준 스냅샷(백신 공급·국가 역량)은 느리게 바뀐다
_WEEKLY_STATE_FILE = Path(__file__).parent / "data" / "last_weekly_run.json"


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


def _observation_fetchers() -> dict:
    """관측값 저장 — 극지만. 수집기가 매시간 응답 캐시에 넣은 값을 쓴다(Open-Meteo 재호출 없음)."""
    from algorithms.polar_signals import POLAR_CACHE_KEY, POLAR_CACHE_TTL_S, polar_watch_all

    return {"polar": lambda: response_cache.swr(POLAR_CACHE_KEY, POLAR_CACHE_TTL_S, polar_watch_all)}


def _store_observations() -> dict | None:
    import collector
    from algorithms import observation_store

    if not observation_store.enabled():
        collector.log("🗄 관측 저장: 꺼짐(EPIWEATHER_OBSERVATION_STORE=off)")
        return None
    summary = observation_store.store(_observation_fetchers())
    collector.log(observation_store.summary_line(summary))
    return summary


async def _run_collection() -> None:
    import collector
    try:
        await asyncio.to_thread(collector.collect_free_sources)
        await asyncio.to_thread(_store_observations)
    except Exception as e:
        collector.log_error("scheduler_collect", e)


async def _run_weekly_job() -> None:
    """발할라 기준 스냅샷(백신 공급·국가 역량) 갱신 — 묵은 것만 새로 받는다."""
    import collector
    try:
        from algorithms.reference_snapshots import refresh_due
        result = await asyncio.to_thread(refresh_due)
        for item in result["refreshed"]:
            if item["refreshed"]:
                collector.log(f"주간 작업: 기준 스냅샷 {item['name']} 갱신 완료 "
                              f"({item['record_count']}건, {item['snapshot_date']})")
            else:
                collector.log(f"  ⚠ 기준 스냅샷 {item['name']} {item['reason']} — 기존 스냅샷 유지")
        if result["skipped_fresh"]:
            ages = ", ".join(f"{s['name']} {s['age_days']}일" for s in result["skipped_fresh"])
            collector.log(f"주간 작업: 기준 스냅샷 아직 신선함({ages}) — 원본 호출 안 함")
    except Exception as e:
        collector.log_error("scheduler_weekly_reference_snapshots", e)
    _save_last_weekly_run(dt.datetime.now(dt.timezone.utc))


async def _run_with_timeout(step: str, coro, timeout: float) -> None:
    import collector
    try:
        await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        collector.log_error(f"scheduler_timeout_{step}", TimeoutError(f"{timeout}초 초과"))


async def _scheduler_loop() -> None:
    while True:
        await _run_with_timeout("수집", _run_collection(), timeout=3300)
        last_weekly = _load_last_weekly_run()
        now = dt.datetime.now(dt.timezone.utc)
        if last_weekly is None or (now - last_weekly).total_seconds() >= _WEEKLY_INTERVAL_SEC:
            await _run_with_timeout("주간 작업", _run_weekly_job(), timeout=3600)
        # 다음 정시까지만 잔다 — 수집 시간이 매 주기 누적돼 슬롯이 밀리지 않게.
        now = dt.datetime.now(dt.timezone.utc)
        next_hour = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        await asyncio.sleep(max(60.0, (next_hour - now).total_seconds()))


@app.on_event("startup")
async def _start_scheduler() -> None:
    if os.environ.get("EPIWEATHER_SCHEDULER", "on").lower() == "off":
        return
    asyncio.create_task(_scheduler_loop())

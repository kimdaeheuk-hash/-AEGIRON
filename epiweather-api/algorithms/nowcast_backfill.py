"""Tier 2 백필 파이프라인 — 과거 공식 선언(라벨) + 그 시점 실제 뉴스량(특징)으로
학습셋을 '지금' 조립해 몇 년치 대기를 명령어 하나로 압축한다.

흐름:
  ① historical_outbreaks의 공식 선언을 outbreak_timeline에 적재(라벨).
  ② 각 선언에 대해 GDELT 뉴스 커버리지 타임라인을 [선언-LOOKBACK일, 선언+21일]
     구간에서 수집 → 주간으로 묶어 extracted_signals에 '실제 신호'로 적재(특징).
     핵심: 신호 날짜는 그 뉴스가 실제로 난 날 — 선언 이전 창의 신호만 양성 라벨의
     특징이 되므로 미래정보 누수가 없다.
  ③ nowcast_dataset.assemble_dataset → train_baseline.

★ 정직성 ★
- GDELT를 못 가져오면(네트워크 차단 등) 그 사건은 '특징 없음'으로 조용히 건너뛴다.
  신호를 지어내지 않는다. 그래서 이 환경(프록시 차단)에선 signals_created=0이 정상이며,
  GDELT가 열리는 곳(로컬/운영)에서 실행해야 실제 학습이 된다.
- GDELT 볼륨은 '뉴스량 프록시'다 — 라이브 NLP 추출 신호와 분포가 달라(대리 특징),
  학습 결과는 '과거적합(retrospective)'으로만 라벨링하고 전향 검증 전 실전대체 금지.
- 다수 음성이 '무신호 창'이라 학습 정확도가 낙관적으로 나올 수 있음(경고 유지).
"""
from __future__ import annotations
import datetime as dt

import db
from . import historical_outbreaks as ho
from .gdelt_signals import fetch_coverage_timeline
from . import nowcast_dataset as nd

BACKFILL_SOURCE = "gdelt_backfill"      # provenance 태그(라이브 신호와 구분)
BACKFILL_TRUST = 0.5                    # 뉴스량 프록시 — 라이브 추출(0.65)보다 낮게
LOOKBACK_DAYS = 120                     # 선언 전 관찰 창
POST_DAYS = 21                          # 선언 직후(양성 라벨 확정용 여유)


def _parse(d: str) -> dt.date:
    return dt.date.fromisoformat(d)


def backfill_timeline() -> int:
    """공식 선언을 outbreak_timeline에 적재(라벨 소스). 등재 건수 반환."""
    n = 0
    for o in ho.OUTBREAKS:
        db.upsert_timeline_event(
            o["event_id"], o["name"], o["declaration"], o["milestone"],
            f"{o['disease']} 공식 발병 선언(백필 라벨)", o["source"], "official",
        )
        n += 1
    return n


def _weekly(points: list[tuple[dt.date, float]]) -> list[tuple[dt.date, float]]:
    """일간 GDELT 볼륨을 주간(월요일 시작) 평균으로 downsample."""
    buckets: dict[dt.date, list[float]] = {}
    for d, v in points:
        wk = d - dt.timedelta(days=d.weekday())
        buckets.setdefault(wk, []).append(v)
    return sorted((wk, sum(vs) / len(vs)) for wk, vs in buckets.items())


def _signal_type(ratio: float) -> str:
    """창 내 최대 대비 상대 뉴스량 → 신호유형(볼륨 오를수록 심각도↑, 프록시)."""
    if ratio >= 0.5:
        return "급증"        # SIGNAL_TYPE_SEVERITY 80
    if ratio >= 0.2:
        return "진행중"      # 60
    return "불명"            # 40


def backfill_signals_for(outbreak: dict, *, min_volume: float = 0.0) -> int:
    """한 사건의 GDELT 뉴스량을 실제 신호로 적재. GDELT 실패 시 0(건너뜀)."""
    decl = _parse(outbreak["declaration"])
    start = decl - dt.timedelta(days=LOOKBACK_DAYS)
    end = decl + dt.timedelta(days=POST_DAYS)
    points = fetch_coverage_timeline(outbreak["gdelt_query"], start, end)
    if not points:
        return 0                       # 네트워크 차단/무자료 → 지어내지 않고 건너뜀
    weekly = _weekly(points)
    vmax = max((v for _, v in weekly), default=0.0)
    if vmax <= 0:
        return 0
    created = 0
    for wk, v in weekly:
        if v <= min_volume:
            continue
        stype = _signal_type(v / vmax)
        db.create_extracted_signal(
            source=BACKFILL_SOURCE, disease=outbreak["disease"], location=outbreak["iso3"],
            signal_type=stype, severity=[], symptom=None, transmission=None,
            source_trust=BACKFILL_TRUST, signal_date=wk.isoformat(),
            raw_text=f"[GDELT 뉴스량 프록시] {outbreak['disease']} {outbreak['iso3']} 주간볼륨={round(v,3)}",
            known_disease=True, country_iso3=outbreak["iso3"],
        )
        created += 1
    return created


def run_backfill(min_volume: float = 0.0) -> dict:
    """전체 백필 실행(타임라인 라벨 + GDELT 신호). 수집 결과 요약 반환."""
    events = backfill_timeline()
    per_event = {}
    total = 0
    for o in ho.OUTBREAKS:
        c = backfill_signals_for(o, min_volume=min_volume)
        per_event[o["event_id"]] = c
        total += c
    return {
        "timeline_events_loaded": events,
        "signals_created": total,
        "per_event_signals": per_event,
        "gdelt_reachable": total > 0,
        "note": ("GDELT 신호 수집 완료 — 실제 뉴스량 기반." if total > 0 else
                 "GDELT를 가져오지 못함(네트워크 차단 등) — 신호를 지어내지 않고 건너뜀. "
                 "GDELT가 열리는 환경(로컬/운영)에서 실행해야 학습됨."),
    }


def run_backfill_and_train(min_volume: float = 0.0) -> dict:
    """백필 → 학습셋 조립 → 베이스라인 학습. 정직성 라벨을 붙여 반환."""
    backfill = run_backfill(min_volume=min_volume)
    rows = nd.assemble_dataset()
    readiness = nd.dataset_readiness(rows)
    training = nd.train_baseline(rows)
    if training.get("trained"):
        training["accuracy_kind"] = "retrospective_backtest"
        training["caveats"] = [
            "GDELT 뉴스량은 라이브 NLP 신호의 '프록시' — 분포 차이 존재.",
            "다수 음성이 무신호 창이라 정확도가 낙관적일 수 있음.",
            "전향적(prospective) 검증 전 z-score/EARS 대체 금지.",
        ]
    return {"backfill": backfill, "readiness": readiness, "training": training}

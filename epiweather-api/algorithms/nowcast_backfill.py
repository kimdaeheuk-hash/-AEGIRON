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
import re

import db
from . import historical_outbreaks as ho
from .gdelt_signals import fetch_coverage_detailed
from . import nowcast_dataset as nd

BACKFILL_SOURCE = "gdelt_backfill"      # provenance 태그(라이브 신호와 구분)
BACKFILL_TRUST = 0.5                    # 뉴스량 프록시 — 라이브 추출(0.65)보다 낮게
LOOKBACK_DAYS = 120                     # 선언 전 관찰 창
POST_DAYS = 21                          # 선언 직후(양성 라벨 확정용 여유)
# 사건 커버리지 최소 기준. 라벨 대다수가 특징 없이 비면 '학습됐다'가 무의미하다.
MIN_EVENT_COVERAGE = 0.60
# raw_text에 심어둔 사건 태그 — 재실행 시 이미 채운 사건을 가리는 키.
_EVENT_TAG = re.compile(r"\[event=([^\]]+)\]")


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


def backfill_signals_for(outbreak: dict, *, min_volume: float = 0.0,
                         reasons: dict | None = None) -> int:
    """한 사건의 GDELT 뉴스량을 실제 신호로 적재. GDELT 실패 시 0(건너뜀).

    reasons 딕셔너리를 주면 실패 이유를 event_id별로 적어 넣는다 — '왜 비었는지'를
    남기지 않으면 고칠 수 있는 실패(질의문 오류)와 기다릴 실패(429)를 구분 못 한다."""
    decl = _parse(outbreak["declaration"])
    start = decl - dt.timedelta(days=LOOKBACK_DAYS)
    end = decl + dt.timedelta(days=POST_DAYS)
    got = fetch_coverage_detailed(outbreak["gdelt_query"], start, end)
    points = got["points"]
    if not points:
        if reasons is not None:
            reasons[outbreak["event_id"]] = {"error": got["error"], "detail": got["detail"]}
        return 0                       # 네트워크 차단/무자료 → 지어내지 않고 건너뜀
    weekly = _weekly(points)
    vmax = max((v for _, v in weekly), default=0.0)
    if vmax <= 0:
        if reasons is not None:
            reasons[outbreak["event_id"]] = {"error": "zero_volume", "detail": "주간 볼륨 최대가 0"}
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
            # event_id를 실어둔다 — 재실행 시 이미 채운 사건을 건너뛰는 키가 된다.
            raw_text=(f"[GDELT 뉴스량 프록시][event={outbreak['event_id']}] "
                      f"{outbreak['disease']} {outbreak['iso3']} 주간볼륨={round(v,3)}"),
            known_disease=True, country_iso3=outbreak["iso3"],
        )
        created += 1
    return created


def already_backfilled() -> set[str]:
    """이미 신호가 적재된 event_id 집합. raw_text에 심어둔 [event=...]로 판정한다.

    태그 도입 이전에 적재된 신호는 인식되지 않는다 — 그 경우 첫 실행에서 한 번
    중복이 생긴다. 이 기능 자체가 오늘 만들어져 운영 적재분이 없으므로 마이그레이션
    로직을 따로 두지 않았다. 과거 적재분이 있는 DB라면 gdelt_backfill 출처 신호를
    지우고 한 번 다시 돌리는 게 깔끔하다."""
    try:
        rows = db.list_recent_signals_by_source(BACKFILL_SOURCE, days=40000, limit=100000)
    except Exception:
        return set()
    done = set()
    for r in rows:
        m = _EVENT_TAG.search(r.get("raw_text") or "")
        if m:
            done.add(m.group(1))
    return done


def run_backfill(min_volume: float = 0.0, force: bool = False,
                 max_events: int | None = None) -> dict:
    """전체 백필 실행(타임라인 라벨 + GDELT 신호). 수집 결과 요약 반환.

    GDELT 속도제한 때문에 한 번에 다 못 채우는 경우가 많다(실측 6/16). 그래서
    **이미 채운 사건은 GDELT를 다시 부르지 않는다** — 나눠 여러 번 돌려 빈 곳만
    메우는 게 정상 사용법이고, 그때 중복 신호가 쌓이면 학습셋이 왜곡되기 때문이다.
    force=True면 무시하고 전부 다시 긁는다."""
    events = backfill_timeline()
    done = set() if force else already_backfilled()
    per_event = {}
    failure_reasons: dict[str, dict] = {}
    skipped_existing = []
    total = 0
    attempted = 0
    deferred = []
    for o in ho.OUTBREAKS:
        if o["event_id"] in done:
            skipped_existing.append(o["event_id"])
            per_event[o["event_id"]] = 0
            continue
        # 한 번에 다 긁으면 GDELT 속도제한 탓에 회차가 12~17분씩 걸린다.
        # 스케줄러가 부를 땐 회차당 작업량을 묶고 나머지는 다음 회차로 미룬다.
        if max_events is not None and attempted >= max_events:
            deferred.append(o["event_id"])
            per_event[o["event_id"]] = 0
            continue
        attempted += 1
        c = backfill_signals_for(o, min_volume=min_volume, reasons=failure_reasons)
        per_event[o["event_id"]] = c
        total += c
    # 사건 단위 커버리지를 따로 센다. 총 신호 수만 보면 '몇 건이 통째로 비었는지'가
    # 안 보인다 — 실측에서 16건 중 2건만 성공했는데 총 39건이라 '수집 완료'로
    # 보고됐다. 라벨의 87.5%가 특징 없이 비어 있으면 그건 완료가 아니다.
    # 이번에 새로 채운 것 + 이전 실행에서 이미 채운 것 = 커버된 사건.
    # 건너뛴 걸 미수집으로 세면 나눠 돌릴수록 커버리지가 떨어져 보인다.
    covered = [e for e, c in per_event.items() if c > 0 or e in done]
    missing = [e for e in per_event if e not in covered]
    coverage = round(len(covered) / len(per_event), 3) if per_event else 0.0
    sufficient = coverage >= MIN_EVENT_COVERAGE

    if not covered:
        note = ("GDELT를 한 건도 가져오지 못함(속도제한·네트워크 차단 등) — 신호를 "
                "지어내지 않고 건너뜀. GDELT가 열리는 환경에서 실행해야 학습됨.")
    elif not sufficient:
        note = (f"⚠ 사건 커버리지 {coverage:.0%}({len(covered)}/{len(per_event)}) — "
                f"기준 {MIN_EVENT_COVERAGE:.0%} 미만이라 학습셋으로 불충분하다. "
                f"대부분 GDELT 속도제한(429)으로 비었을 가능성이 크다. 미수집 사건: "
                f"{', '.join(missing[:6])}{' 외' if len(missing) > 6 else ''}. "
                "이 상태로 학습하면 소수 사건에만 맞춘 모델이 된다.")
    else:
        note = (f"GDELT 신호 수집 — 사건 커버리지 {coverage:.0%}"
                f"({len(covered)}/{len(per_event)}), 실제 뉴스량 기반.")

    return {
        "timeline_events_loaded": events,
        "signals_created": total,
        "per_event_signals": per_event,
        "events_covered": len(covered),
        "skipped_already_backfilled": skipped_existing,
        "deferred_to_next_run": deferred,
        "events_attempted": attempted,
        "events_missing": missing,
        # 왜 비었는지를 사건별로 남긴다 — bad_query는 지금 고칠 수 있고,
        # rate_limited는 시간을 두고 다시 돌리면 되는, 완전히 다른 문제다.
        "failure_reasons": failure_reasons,
        "event_coverage": coverage,
        "coverage_sufficient": sufficient,
        # 한 건이라도 받았으면 네트워크는 열린 것 — 커버리지 부족과 구분해서 본다.
        "gdelt_reachable": bool(covered),
        "note": note,
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
        # 커버리지가 모자라면 '학습됨'만 보이고 넘어가지 않게 결과에 붙여 보낸다.
        # 16건 중 2건으로 학습해도 trained=True는 그대로 뜨기 때문이다.
        training["event_coverage"] = backfill.get("event_coverage")
        if not backfill.get("coverage_sufficient"):
            training["coverage_warning"] = (
                f"사건 커버리지 {backfill.get('event_coverage', 0):.0%} — "
                f"라벨 대다수가 특징 없이 비었다. 이 모델은 소수 사건에만 맞춰져 있으니 "
                f"GDELT 속도제한이 풀린 환경에서 다시 백필한 뒤 재학습할 것."
            )
            training["caveats"].insert(0, training["coverage_warning"])
    return {"backfill": backfill, "readiness": readiness, "training": training}


def maintain(max_events: int = 4, min_volume: float = 0.0) -> dict:
    """스케줄러용 — 커버리지가 기준에 닿을 때까지만 조금씩 채우고, 차면 멈춘다.

    설계 이유:
    - 이미 채운 사건은 GDELT를 부르지 않으므로 **다 차면 비용이 0이다**. 매일 불러도
      기준을 넘긴 뒤에는 조회조차 안 한다.
    - 한 번에 16건을 긁으면 속도제한 탓에 12~17분이 걸린다. max_events로 회차당
      작업량을 묶어 나눠 채운다(빈 사건이 없어질 때까지 며칠에 걸쳐).
    - 새로 채운 게 있을 때만 재학습한다 — 같은 데이터로 반복 학습할 이유가 없다.
    """
    done = already_backfilled()
    remaining = [o["event_id"] for o in ho.OUTBREAKS if o["event_id"] not in done]
    coverage = round(len(done) / len(ho.OUTBREAKS), 3) if ho.OUTBREAKS else 0.0
    # 남은 게 없을 때만 멈춘다. MIN_EVENT_COVERAGE(60%)로 멈추면 **마지막 빈 사건이
    # 영원히 안 채워진다** — 실측에서 커버리지 94%(15/16)에 도달하자 maintain이
    # '기준 충족'으로 건너뛰어, 남은 1건을 자동으로 메울 경로가 사라졌다.
    # 낭비를 막으려던 기준이 마무리까지 막은 것이다. 이미 채운 사건은 GDELT를 아예
    # 부르지 않으므로, 남은 것만 회차당 max_events씩 시도해도 비용은 그만큼뿐이다.
    if not remaining:
        return {"ok": True, "action": "skipped", "event_coverage": coverage,
                "reason": f"전 사건 수집 완료({len(done)}/{len(ho.OUTBREAKS)}) — GDELT 호출 없음(비용 0)."}

    backfill = run_backfill(min_volume=min_volume, max_events=max_events)
    result = {"ok": True, "action": "backfilled", "backfill": backfill,
              "remaining_before": remaining}
    if backfill["signals_created"] > 0:
        rows = nd.assemble_dataset()
        result["readiness"] = nd.dataset_readiness(rows)
        training = nd.train_baseline(rows)
        training["event_coverage"] = backfill["event_coverage"]
        if not backfill["coverage_sufficient"]:
            training["coverage_warning"] = (
                f"사건 커버리지 {backfill['event_coverage']:.0%} — 아직 기준 미달. "
                f"남은 사건은 다음 회차에 채워진다(자동)."
            )
        result["training"] = training
    else:
        result["training"] = {"trained": False,
                              "reason": "이번 회차에 새로 채운 신호 없음 — 재학습 생략"}
    return result

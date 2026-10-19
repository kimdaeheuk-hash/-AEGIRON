"""BAIKAL MOB — 아이기론 생태계 상태변화 시스템 (2026-10-19).

캡틴: "온톨로지로 연결하고 피드백 루프로 결과 받고 그 위에 상태변화 시스템(바이칼 몹)을
구축해서 아이기론 생태계의 흐름 상태변화를 만들어서 저장하고 보여주는 대표 시스템."

매시간 경보 주기 직후에 7개 시스템(YGGDRASIL)의 상태를 하나씩 판정하고, 피드백 루프의
흐르는 양을 재고, 한 장의 스냅숏으로 남긴다. 상태가 **바뀐 순간만** 전이로 기록한다.
가장 깊고 오래된 호수가 바닥에 층층이 역사를 쌓듯이.

★ 읽기 전용이다 ★
이 층은 새 수집을 하지 않고, 경보·예측·알림 계산을 바꾸지 않는다. 이미 매시간 남는
값(소스 건강 · 품질 불변식 · 경보 표 · 예측 원장 · 수집 주기 기록)만 읽는다.
소킹 기간(런칭전_소킹_2026-09.md)에 들어왔기 때문에 지킨 선이다 — 이 층이 어떻게
고장 나도 경보는 그대로 울려야 한다. 스케줄러는 예외를 삼키고(main._run_baikal_cycle)
`EPIWEATHER_BAIKAL=off` 로 끌 수 있다.

★ 상태를 지어내지 않는다 (honesty-review) ★
  · 상태는 네 가지다: ok(정상) · degraded(저하) · down(중단) · undetermined(판정 안 함).
    읽을 값이 없으면 '판정 안 함'이다 — '정상'으로 세지 않는다.
  · 시스템마다 `scope_ko` 가 이 상태가 **무엇을 보고** 판정했는지 말한다. 예: SKULD 의
    '정상'은 예측 원장이 읽히고 기록이 있다는 뜻이지, 확산 트윈이 잘 돈다는 뜻이 아니다
    (트윈은 요청 시 엔진이라 매시간 상태가 없다 — `on_request` 에 따로 적는다).
  · 피드백 루프는 판정 0건인 동안 '측정 대기'다. 적중률 0% 가 아니다.
  · 루프는 기록만 한다 — 채점 결과가 예측 모델을 자동으로 고치지 않는다.
  · 문턱을 새로 지어내지 않는다. 품질 불변식의 경보 문턱(alarm_after)처럼 이미 시험된
    판정이 있으면 그것을 따른다.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

import db
from algorithms import yggdrasil

STATUS_KO = {
    "ok": "정상",
    "degraded": "저하",
    "down": "중단",
    "undetermined": "판정 안 함",
}
STATUSES = tuple(STATUS_KO)

LOOP_STATE_KO = {
    "measuring": "측정 중",
    "awaiting": "측정 대기",
    "empty": "비어 있음",
    "undetermined": "판정 안 함",
}

EVIDENCE_CLASSES = ("measured", "estimated", "proxy")

# 수집 주기 기록이 이보다 오래됐으면 '지금 상태'로 읽지 않는다(판정 안 함).
CYCLE_RECORD_MAX_AGE_HOURS = 3.0
# 경보 표가 이보다 오래 갱신되지 않았으면 경보 주기가 멎은 것으로 본다.
ALERT_TABLE_STALE_HOURS = 2.0
# 수집기가 이 시간 넘게 조용하면 감시가 멈춘 것이다(source_health.collector_silent_hours).
COLLECTOR_SILENT_DOWN_HOURS = 2.0
# 수집 주기 기록을 찾을 때 파일 끝에서부터 읽는 최대 바이트.
CYCLE_RECORD_SCAN_BYTES = 32 * 1024 * 1024
# 저장된 스냅숏이 이보다 오래되면 API 가 '낡음'으로 표시한다 — 매시 주기를 두 번 놓친 것.
SNAPSHOT_STALE_MINUTES = 130

_SOURCE_STATUS_KO = {
    "failing": "중단", "flaky": "간헐 성공", "stale": "늙는중",
    "no_data": "값없음", "unknown": "판정불가", "recovering": "회복 중",
}
# 소스 건강이 '문제'로 보는 상태. no_data 는 넣지 않는다 — 위키처럼 정상 지연이 잦은
# 소스를 매 주기 저하로 올리면 경보 피로가 된다(source_health._status_for 의 같은 판단).
# 다만 오래 값이 없는 소스(long_no_data_sources)는 저하로 센다.
_SOURCE_PROBLEM = ("failing", "flaky", "stale")

# HUGINN 이 책임지는 품질 불변식(현지어 분류·재난 감시창 층). 추출(extraction)은 MIMIR.
_HUGINN_INVARIANTS = ("llm_reclassify", "llm_coverage", "disaster_watch",
                      "local_feeds", "llm_provider")
_MIMIR_INVARIANT = "extraction"

_TIER_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_RANK_TIER = {v: k for k, v in _TIER_RANK.items()}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_iso(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        t = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    # 수집 주기 기록의 timestamp 는 naive(컨테이너 시각 = UTC)다.
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def snapshot_age_minutes(observed_at: Any, now: dt.datetime | None = None) -> int | None:
    """저장된 스냅숏의 나이(분). 시각을 못 읽으면 None."""
    t = _parse_iso(observed_at)
    if t is None:
        return None
    return int(((now or _now()) - t).total_seconds() // 60)


def _hours_between(later: dt.datetime, earlier: dt.datetime) -> float:
    return round((later - earlier).total_seconds() / 3600, 1)


def _system_result(key: str, status: str, reason: str, *, scope_ko: str,
                   evidence_class: str = "measured",
                   readings: dict | None = None) -> dict:
    assert status in STATUSES, status
    assert evidence_class in EVIDENCE_CLASSES, evidence_class
    meta = yggdrasil.system(key)
    return {
        "key": key,
        "name_ko": meta["name_ko"],
        "role_ko": meta["role_ko"],
        "order": meta["order"],
        "status": status,
        "status_ko": STATUS_KO[status],
        "reason": reason,
        "scope_ko": scope_ko,
        "evidence_class": evidence_class,
        "readings": readings or {},
        "on_request": list(meta["on_request"]),
    }


# ── 판정(순수 함수) ────────────────────────────────────────

_HUGINN_SCOPE = ("매시 수집 소스의 실제 값 유입(소스 건강)과 현지어 분류·재난 감시창 층의 "
                 "품질 불변식")


def judge_huginn(health: dict | None, quality: dict | None) -> dict:
    # None(못 읽음)과 빈 기록을 같은 말로 쓰지 않는다 — 둘 다 판정 안 함이지만 사유가 다르다.
    if health is None:
        return _system_result("HUGINN", "undetermined", "소스 건강을 못 읽음",
                              scope_ko=_HUGINN_SCOPE)
    if not health.get("total_tracked"):
        return _system_result("HUGINN", "undetermined", "소스 건강 기록 없음",
                              scope_ko=_HUGINN_SCOPE)
    healthy, total = health.get("healthy_count", 0), health["total_tracked"]
    readings: dict[str, Any] = {"healthy_sources": healthy, "total_sources": total}

    silent = health.get("collector_silent_hours")
    if silent is not None and silent >= COLLECTOR_SILENT_DOWN_HOURS:
        readings["collector_silent_hours"] = silent
        return _system_result("HUGINN", "down", f"수집기 {silent:.1f}시간 침묵",
                              scope_ko=_HUGINN_SCOPE, readings=readings)

    problems: list[str] = []
    notes: list[str] = []
    for s in health.get("sources") or []:
        st = s.get("status")
        if st in _SOURCE_PROBLEM:
            problems.append(f"{_SOURCE_STATUS_KO[st]} {s.get('source')}")
        elif st in ("no_data", "unknown", "recovering"):
            notes.append(f"{_SOURCE_STATUS_KO[st]} {s.get('source')}")
    for x in health.get("long_no_data_sources") or []:
        problems.append(f"장기 값없음 {x.get('source')}")

    for inv in (quality or {}).get("invariants") or []:
        if inv.get("key") not in _HUGINN_INVARIANTS:
            continue
        if inv.get("alarming"):
            problems.append(f"품질 저하 {inv.get('label')}")
        elif inv.get("last_result") == "violated":
            # 문턱 전 위반은 숨기지 않되 상태를 올리지 않는다(품질 층의 alarm_after 를 따른다).
            notes.append(f"{inv.get('label')} 위반 {inv.get('consecutive_violations')}주기째"
                         f"(문턱 {inv.get('alarm_after')})")

    readings["problems"] = problems
    readings["notes"] = notes
    head = f"정상 {healthy}/{total}"
    if problems:
        return _system_result("HUGINN", "degraded",
                              " · ".join([head] + problems + notes),
                              scope_ko=_HUGINN_SCOPE, readings=readings)
    return _system_result("HUGINN", "ok", " · ".join([head] + notes),
                          scope_ko=_HUGINN_SCOPE, readings=readings)


_MIMIR_SCOPE = ("AI 슬롯의 NLP 구조화 추출 층(품질 불변식 '구조화 추출') — 하루 1회 도는 층이라 "
                "매시간 같은 판정이 이어진다")


def judge_mimir(quality: dict | None, extracted_24h: int | None) -> dict:
    readings: dict[str, Any] = {"extracted_last_24h": extracted_24h}
    if quality is None:
        return _system_result("MIMIR", "undetermined", "품질 불변식을 못 읽음",
                              scope_ko=_MIMIR_SCOPE, readings=readings)
    inv = None
    for item in quality.get("invariants") or []:
        if item.get("key") == _MIMIR_INVARIANT:
            inv = item
            break
    if inv is None:
        return _system_result("MIMIR", "undetermined", "추출 층 품질 기록 없음",
                              scope_ko=_MIMIR_SCOPE, readings=readings)
    detail = inv.get("detail")
    if detail:
        readings["detail"] = detail
    tail = f" · 24시간 추출 {extracted_24h}건" if extracted_24h is not None else ""
    last = inv.get("last_result")
    if last == "ok":
        return _system_result("MIMIR", "ok", f"추출 저장 정상{tail}",
                              scope_ko=_MIMIR_SCOPE, readings=readings)
    if last == "violated":
        # 이 불변식의 위반은 그 자체로 '48시간 넘게 저장 0건'이다(quality_health) — 일시적
        # 흔들림이 아니라 이미 창을 거친 판정이라 문턱 전이어도 저하로 본다.
        streak = inv.get("consecutive_violations")
        return _system_result("MIMIR", "degraded",
                              f"48시간 넘게 추출 저장 0건(위반 {streak}주기째){tail}",
                              scope_ko=_MIMIR_SCOPE, readings=readings)
    return _system_result("MIMIR", "undetermined", f"추출 층 판정불가{tail}",
                          scope_ko=_MIMIR_SCOPE, readings=readings)


_FORSETI_SCOPE = ("오늘 경보 표의 갱신 신선도(경보 주기가 돌았는가)와 등급별 건수 · "
                  "폰으로 실제 전송된 최고 등급")


def _is_held(row: dict) -> bool:
    """판정 못 한 계열이라 지난 값 그대로 붙들린 행(낡음 표시가 근거 맨 앞에 붙는다)."""
    try:
        from algorithms.alerts import is_stale_marked
    except Exception:
        return False
    ev = row.get("evidence")
    return bool(is_stale_marked(ev if isinstance(ev, list) else None))


def judge_forseti(alerts_today: list[dict] | None, now: dt.datetime) -> dict:
    if alerts_today is None:
        return _system_result("FORSETI", "undetermined", "경보 표를 못 읽음",
                              scope_ko=_FORSETI_SCOPE, readings={"tiers": {}, "active": 0})
    rows = alerts_today
    if not rows:
        return _system_result(
            "FORSETI", "undetermined",
            "오늘 경보 표가 비어 있음 — 평온인지 경보 주기 미가동인지 이 표만으로 가리지 않는다",
            scope_ko=_FORSETI_SCOPE, readings={"tiers": {}, "active": 0})

    active = [r for r in rows if not r.get("suppressed")]
    tiers: dict[str, int] = {}
    for r in active:
        tiers[r.get("tier", "?")] = tiers.get(r.get("tier", "?"), 0) + 1
    highest = max((_TIER_RANK.get(r.get("tier"), -1) for r in active), default=-1)
    sent = [r.get("notified_rank") for r in rows if r.get("notified_rank") is not None]
    sent_rank = max(sent) if sent else None
    top = max(active, key=lambda r: r.get("score") or 0) if active else None
    readings = {
        "tiers": tiers,
        "active": len(active),
        "highest_tier": _RANK_TIER.get(highest),
        "phone_sent_highest_tier": _RANK_TIER.get(sent_rank) if sent_rank is not None else None,
        "top_label": top.get("label") if top else None,
        "top_score": top.get("score") if top else None,
    }
    tier_text = " · ".join(f"{t} {n}건" for t, n in sorted(
        tiers.items(), key=lambda kv: -_TIER_RANK.get(kv[0], -1))) or "활성 경보 없음"
    phone = (f" · 폰 전송 최고 {readings['phone_sent_highest_tier']}"
             if sent_rank is not None else " · 폰 전송 없음")
    # ★ 신선도는 활성 행으로만 잰다 ★ 활성 후보는 경보 주기마다 다시 upsert 돼 updated_at
    # 이 갱신되지만, 내려간 행(suppressed)은 내려간 뒤로 멈춘다. 오전에 low 하나가 내려가고
    # 조용한 날이면 표 전체의 최신 시각이 몇 시간째 멈춰 있고, 그걸로 재면 '경보 주기 멎음'
    # 을 거짓으로 낸다(2026-10-19 작성 중 시험에서 발견). 활성 행이 없으면 가리지 않는다.
    if not active:
        return _system_result(
            "FORSETI", "undetermined",
            f"오늘 활성 경보 없음(내려간 행 {len(rows)}건) — 평온인지 경보 주기 미가동인지 "
            f"이 표만으로 가리지 않는다{phone}",
            scope_ko=_FORSETI_SCOPE, readings=readings)
    # ★ 붙들린 행도 신선도에서 뺀다 (2026-10-19 재검토) ★ 무역 스캔·보도 조회가 실패한 주기에
    # 그 계열 행은 내리지 않고 지난 값 그대로 화면에 남는다(alerts._held) — upsert 되지 않아
    # updated_at 이 멈춘다. 활성 행이 전부 이런 행이고 실패가 두 시간을 넘으면, 경보 주기는
    # 돌았는데 '멎음 의심'을 거짓으로 낸다. 이번 주기에 실제로 다시 저장된 행만 증거로 쓴다.
    live = [r for r in active if not _is_held(r)]
    readings["held"] = len(active) - len(live)
    if not live:
        return _system_result(
            "FORSETI", "undetermined",
            f"활성 경보 {len(active)}건 전부 판정 보류(지난 값 유지) — 이번 주기 갱신 여부를 "
            f"이 표만으로 가리지 않는다 · {tier_text}{phone}",
            scope_ko=_FORSETI_SCOPE, readings=readings)
    latest = max((t for t in (_parse_iso(r.get("updated_at")) for r in live) if t),
                 default=None)
    if latest is None:
        return _system_result("FORSETI", "undetermined", f"경보 표 갱신 시각 없음 · {tier_text}",
                              scope_ko=_FORSETI_SCOPE, readings=readings)
    age = _hours_between(now, latest)
    readings["table_age_hours"] = age
    if age >= ALERT_TABLE_STALE_HOURS:
        return _system_result("FORSETI", "down",
                              f"경보 표 {age:.1f}시간째 갱신 없음 — 경보 주기 멎음 의심 · {tier_text}",
                              scope_ko=_FORSETI_SCOPE, readings=readings)
    return _system_result("FORSETI", "ok", f"{tier_text}{phone}",
                          scope_ko=_FORSETI_SCOPE, readings=readings)


_SKULD_SCOPE = ("예측 원장 — 기록 존재와 최근 기록 시각. 새 기록이 없는 시간은 '기록할 이상 "
                "국가 없음'일 수 있어 실패로 세지 않는다. 확산 트윈·유입 추정·개입 비교는 "
                "요청 시 엔진이라 범위 밖")


def _unnamed_label() -> str:
    try:
        from algorithms.country_risk import UNNAMED_DISEASE
        return UNNAMED_DISEASE
    except Exception:
        return "종합 위험도(GAI 기반)"


def judge_skuld(predictions: list[dict] | None, now: dt.datetime) -> dict:
    if predictions is None:
        return _system_result("SKULD", "undetermined", "예측 원장을 못 읽음",
                              scope_ko=_SKULD_SCOPE, readings={"total": None})
    preds = predictions
    if not preds:
        return _system_result("SKULD", "undetermined", "예측 원장 비어 있음",
                              scope_ko=_SKULD_SCOPE, readings={"total": 0})
    unnamed = _unnamed_label()
    named = sum(1 for p in preds if p.get("disease") and p.get("disease") != unnamed)
    stamps = [t for t in (_parse_iso(p.get("predicted_at")) for p in preds) if t]
    latest = max(stamps) if stamps else None
    recent = sum(1 for t in stamps if (now - t).total_seconds() <= 24 * 3600)
    readings = {
        "total": len(preds),
        "named_disease": named,
        "unnamed_disease": len(preds) - named,
        "recorded_last_24h": recent,
        "latest_predicted_at": latest.isoformat() if latest else None,
    }
    age = f" · 최근 기록 {_hours_between(now, latest) / 24:.1f}일 전" if latest else ""
    return _system_result(
        "SKULD", "ok",
        f"원장 {len(preds)}건 · 질병 지목 {named}/{len(preds)}{age}",
        scope_ko=_SKULD_SCOPE, readings=readings)


_HEIMDALL_SCOPE = ("Nextstrain 공개 시퀀스 계통 추적(매시). Evo2 순서 자연성·상동성 검색은 "
                   "요청 시 엔진이라 범위 밖")


def _record_age_reason(record: dict | None, now: dt.datetime) -> str | None:
    """수집 주기 기록을 지금 상태로 읽을 수 없으면 그 사유. 읽을 수 있으면 None."""
    if record is None:
        return "최근 수집 주기 기록을 못 읽음"
    t = _parse_iso(record.get("timestamp"))
    if t is None:
        return "수집 주기 기록에 시각 없음"
    age = _hours_between(now, t)
    if age > CYCLE_RECORD_MAX_AGE_HOURS:
        return f"최근 수집 주기 기록이 {age:.1f}시간 전 — 지금 상태로 읽지 않음"
    return None


def judge_heimdall(record: dict | None, now: dt.datetime) -> dict:
    stale = _record_age_reason(record, now)
    if stale:
        return _system_result("HEIMDALL", "undetermined", stale, scope_ko=_HEIMDALL_SCOPE)
    # 수집기는 이 단계가 예외로 실패하면 키를 남기고 값을 None 으로 둔다(collector.py). 키가
    # 아예 없으면 실패가 아니라 이 기록으로는 모르는 것이다 — 중단과 판정 안 함을 가른다.
    if "genomic_variants" not in record:
        return _system_result("HEIMDALL", "undetermined", "수집 주기 기록에 계통 추적 항목이 없음",
                              scope_ko=_HEIMDALL_SCOPE)
    gv = record["genomic_variants"]
    if gv is None:
        return _system_result("HEIMDALL", "down", "계통 추적 단계 실패(수집 주기 기록상 값 없음)",
                              scope_ko=_HEIMDALL_SCOPE)
    if not gv:
        return _system_result("HEIMDALL", "undetermined", "추적 대상 병원체 없음",
                              scope_ko=_HEIMDALL_SCOPE)
    per: list[dict] = []
    # ★ 실패와 데이터 부재를 가른다 (2026-10-19 프로덕션 첫 관측) ★
    # genomic_variants 는 조회가 실패하거나 빌드가 멈추면 available=False 로 둔다 — 그건 실패다.
    # available=True 인데 우세 계통이 없으면 '최근 구간 시퀀스 없음(제출 지연 가능)' — 고장이
    # 아니라 아직 판정할 데이터가 안 온 것이다. 첫 배포에서 엠폭스가 이 경우였는데 HEIMDALL 이
    # '저하'로 나갔다(관측보다 많이 주장). 그런 병원체는 '판정 불가'로 적고 상태를 올리지 않는다.
    per: list[dict] = []
    for slug, v in sorted(gv.items()):
        if not v.get("available"):
            state = "failed"
        elif v.get("dominant_share") is None:
            state = "no_data"
        else:
            state = "ok"
        per.append({
            "slug": slug, "label": v.get("label") or slug, "state": state, "ok": state == "ok",
            "dominant_clade": v.get("dominant_clade"),
            "dominant_share": v.get("dominant_share"),
            "new_clade_count": v.get("new_clade_count"),
            "n_recent_sequences": v.get("n_recent_sequences"),
            "reason": None if state == "ok" else (v.get("reason") or v.get("note")
                                                  or "최근 구간 데이터 없음"),
        })
    ok_n = sum(1 for p in per if p["state"] == "ok")
    failed = [p for p in per if p["state"] == "failed"]
    no_data = [p for p in per if p["state"] == "no_data"]
    readings = {"pathogens": per, "ok": ok_n, "failed": len(failed),
                "no_data": len(no_data), "total": len(per)}
    parts = [f"계통 추적 {ok_n}/{len(per)} 정상"]
    parts += [f"{p['label']} 실패({p['reason']})" for p in failed]
    parts += [f"{p['label']} 판정 불가({p['reason']})" for p in no_data]
    reason = " · ".join(parts)
    if failed:
        status = "down" if len(failed) == len(per) else "degraded"
    elif ok_n:
        status = "ok"
    else:
        status = "undetermined"
    return _system_result("HEIMDALL", status, reason, scope_ko=_HEIMDALL_SCOPE, readings=readings)


_VALHALLA_SCOPE = "대응제 준비태세 스냅숏의 신선도(조달·임상 파이프라인 조각의 갱신 실패 여부)"


def judge_valhalla(record: dict | None, now: dt.datetime,
                   stale_parts: Callable[[dict], list] | None = None) -> dict:
    stale = _record_age_reason(record, now)
    if stale:
        return _system_result("VALHALLA", "undetermined", stale, scope_ko=_VALHALLA_SCOPE)
    if "valhalla" not in record:
        return _system_result("VALHALLA", "undetermined", "수집 주기 기록에 발할라 항목이 없음",
                              scope_ko=_VALHALLA_SCOPE)
    v = record["valhalla"]
    if not isinstance(v, dict):
        return _system_result("VALHALLA", "down", "발할라 단계 실패(수집 주기 기록상 값 없음)",
                              scope_ko=_VALHALLA_SCOPE)
    if stale_parts is None:
        from algorithms.valhalla_watch import stale_parts as _stale_parts
        stale_parts = _stale_parts
    parts = stale_parts(v)
    readings = {
        "procurement_bid_count": ((v.get("procurement") or {}).get("value") or {}).get("bid_count"),
        "vaccine_single_source_count": (v.get("vaccine_chokepoints") or {}).get("single_source_count"),
        "countermeasure_count": (v.get("readiness") or {}).get("countermeasure_count"),
        "stale_parts": [name for name, _ in parts],
    }
    _ko = {"procurement": "조달", "pipeline": "파이프라인"}
    if parts:
        why = " · ".join(f"{_ko.get(n, n)} 갱신 실패({p.get('age_hours')}시간 전 값)"
                         for n, p in parts)
        return _system_result("VALHALLA", "degraded", why,
                              scope_ko=_VALHALLA_SCOPE, readings=readings)
    return _system_result("VALHALLA", "ok", "준비태세 스냅숏 신선",
                          scope_ko=_VALHALLA_SCOPE, readings=readings)


_VAR_SCOPE = "예측 봉인 따라잡기(미봉인 수)와 채점·선행성 원장이 읽히는가"


def judge_var(unsealed: int | None, scorecard: dict | None, ledger: dict | None,
              seal_batch: int = 10) -> dict:
    if unsealed is None or scorecard is None:
        return _system_result("VAR", "undetermined", "봉인·채점 기록을 못 읽음",
                              scope_ko=_VAR_SCOPE)
    sc = scorecard
    if not sc.get("total"):
        # 검증할 예측이 없으면 '정상'이 아니라 판정할 것이 없다(SKULD 의 빈 원장과 같은 판단).
        return _system_result("VAR", "undetermined", "검증할 예측 없음 — 봉인·채점할 대상이 없다",
                              scope_ko=_VAR_SCOPE, readings={"unsealed": unsealed})
    readings = {
        "unsealed": unsealed,
        "resolved": sc.get("resolved"), "correct": sc.get("correct"),
        "incorrect": sc.get("incorrect"), "unresolved": sc.get("unresolved"),
        "overdue": len(sc.get("overdue") or []),
        "ledger_measured": (ledger or {}).get("measured_events"),
        "ledger_open": (ledger or {}).get("open_crossings"),
        "ledger_false_alarms": (ledger or {}).get("false_alarms"),
    }
    seal_text = "미봉인 없음" if unsealed == 0 else f"미봉인 {unsealed}건"
    body = f"{seal_text} · 판정 {sc.get('resolved', 0)}건 · 미결 {sc.get('unresolved', 0)}건"
    # 원장을 못 읽었으면 'None' 을 찍지 않고 그 사실을 적는다.
    body += (" · 선행성 원장을 못 읽음" if ledger is None
             else f" · 원장 열린 기록 {readings['ledger_open']}")
    if unsealed > seal_batch:
        # 매시 주기가 한 번에 seal_batch 건씩 봉인한다. 그보다 많이 밀려 있으면 따라잡기가
        # 한 주기 안에 안 끝나는 상태다. 관측된 문제라 원장 읽기 실패보다 앞에 둔다.
        return _system_result("VAR", "degraded",
                              f"{body} — 매시 {seal_batch}건 봉인보다 많이 밀림",
                              scope_ko=_VAR_SCOPE, readings=readings)
    if ledger is None:
        # 상태 범위(scope)의 절반을 못 봤다 — 정상이라 하지 않는다.
        return _system_result("VAR", "undetermined", body, scope_ko=_VAR_SCOPE, readings=readings)
    return _system_result("VAR", "ok", body, scope_ko=_VAR_SCOPE, readings=readings)


def weekly_loop_state(card: dict | None) -> dict:
    """주간 추세 예측(weekly_forecast)의 흐르는 양 — 90일 루프와 **따로** 본다.

    주간 예측은 기한이 1~2주라 90일 루프보다 훨씬 먼저 '측정 중'이 된다. 둘을 한 줄로
    합치면 "피드백 루프가 측정 중"이 90일 발병 예측도 채점되기 시작한 것처럼 읽힌다."""
    if card is None:
        state, text = "undetermined", "판정 안 함 — 주간 예측 표를 못 읽음"
    elif not (card.get("scored") or card.get("open") or card.get("void")):
        state, text = "empty", "비어 있음 — 기록된 주간 예측 없음"
    elif not card.get("scored"):
        state, text = "awaiting", f"측정 대기 — 판정 0건 · 미결 {card.get('open', 0)}건"
    elif not card.get("enough"):
        state = "measuring"
        text = (f"측정 중 — 판정 {card['scored']}건 · 성적은 {card.get('min_scored', 8)}건부터 "
                f"말함 · 미결 {card.get('open', 0)}건")
    else:
        state = "measuring"
        text = (f"측정 중 — 판정 {card['scored']}건 · Brier {card.get('brier_model')} "
                f"(동전 {card.get('brier_coin', 0.25)}) · 방향 적중 "
                f"{card.get('hits_model')}/{card.get('calls_model')}")
    return {"state": state, "state_ko": LOOP_STATE_KO[state], "text": text,
            "card": card}


# ── 운영 알림 (2026-10-19, 캡틴 승인 ⑤) ──────────────────────────────
# 시스템이 '중단'으로 바뀌거나 '중단'에서 돌아올 때만 캡틴에게 한 줄 보낸다.
# '저하'는 보내지 않는다 — 위키 소스 하나로도 자주 오가서(HUGINN) 매번 울리면 경보
# 피로가 된다. 전이는 '바뀐 순간'만 생기므로 같은 상태로는 두 번 울리지 않는다.
# 이 알림은 **시스템 자체의 운영 상태**이지 감염병 경보가 아니다 — 본문에 그렇게 쓴다.
_OPS_ICON = {"down": "🔴", "recovered": "🟢"}


def ops_notice_text(transitions: list[dict]) -> str | None:
    """중단 진입·중단 해제 전이를 텔레그램 본문으로. 해당 전이가 없으면 None."""
    import html

    from .yggdrasil import SYSTEMS

    names = {s["key"]: f"{s['key']} {s.get('name_ko', '')}".strip() for s in SYSTEMS}
    lines = []
    for t in transitions or []:
        if t["subject"] not in names:          # LOOP·LOOP_WEEKLY 는 운영 고장이 아니다
            continue
        before = STATUS_KO.get(t["from_status"], "관측 시작") if t["from_status"] else "관측 시작"
        if t["to_status"] == "down":
            icon = _OPS_ICON["down"]
            after = "<b>중단</b>"
        elif t["from_status"] == "down":
            icon = _OPS_ICON["recovered"]
            after = f"<b>{html.escape(STATUS_KO.get(t['to_status'], t['to_status']))}</b> (복구)"
        else:
            continue
        reason = html.escape(str(t.get("reason") or ""), quote=False)
        lines.append(f"{icon} {html.escape(names[t['subject']])}: {html.escape(before)} → {after}"
                     + (f"\n   └ {reason}" if reason else ""))
    if not lines:
        return None
    return ("🌊 <b>BAIKAL 운영 알림</b>\n" + "\n".join(lines) +
            "\n\n<i>시스템 자체의 운영 상태 알림 — 감염병 경보가 아님 · 상세: /baikal</i>")


def loop_state(scorecard: dict | None, predictions: list[dict] | None,
               ground_truth: dict | None, today: dt.date) -> dict:
    """피드백 루프(정답 적재 → 예측 → 채점)의 흐르는 양."""
    sc = scorecard or {}
    preds = predictions or []
    gt = ground_truth or {}
    total = sc.get("total", len(preds))
    resolved = sc.get("resolved") or 0
    if scorecard is None:
        # 원장을 못 읽은 것을 '기록된 예측 없음'으로 쓰면 거짓이다(운영엔 36건이 있다).
        state = "undetermined"
        text = "판정 안 함 — 예측 원장·채점표를 못 읽음"
    elif not total:
        state = "empty"
        text = "비어 있음 — 기록된 예측 없음"
    elif resolved > 0:
        state = "measuring"
        text = (f"측정 중 — 판정 {resolved}건(적중 {sc.get('correct', 0)} · "
                f"실패 {sc.get('incorrect', 0)})")
    else:
        state = "awaiting"
        text = "측정 대기 — 판정된 예측 0건 · 적중률은 0%가 아니라 아직 측정 불가"

    due = sorted(
        str(p.get("resolves_by"))[:10] for p in preds
        if p.get("correct") is None and p.get("resolves_by")
        and str(p.get("resolves_by"))[:10] >= today.isoformat()
    )
    unnamed = _unnamed_label()
    named = sum(1 for p in preds if p.get("disease") and p.get("disease") != unnamed)
    return {
        "state": state,
        "state_ko": LOOP_STATE_KO[state],
        "text": text,
        "links": [
            {"key": "ground_truth", "label_ko": "① 정답 적재",
             "live": gt.get("live"), "other": gt.get("other"),
             "latest_live_event_date": gt.get("latest_live_event_date")},
            {"key": "predictions", "label_ko": "② 예측 기록",
             "total": total, "named_disease": named},
            {"key": "scoring", "label_ko": "③ 채점",
             "resolved": resolved, "correct": sc.get("correct"),
             "incorrect": sc.get("incorrect"), "unresolved": sc.get("unresolved"),
             "overdue": len(sc.get("overdue") or [])},
        ],
        "earliest_due": due[0] if due else None,
        "automatic_feedback": False,
        "note": "채점 결과는 원장에 기록될 뿐 예측 모델을 자동으로 고치지 않는다.",
    }


# ── 입력 읽기 ──────────────────────────────────────────────

def _latest_cycle_record(path: Path | None = None, chunk: int = 1024 * 1024) -> dict | None:
    """수집 주기 기록(signals_log.jsonl)의 마지막 무료 소스 회차. 파일 끝에서 거꾸로 읽는다.

    수집 결과를 다시 계산하지 않으려고 수집기가 이미 남긴 기록을 읽는다 — 다시 부르면
    외부 호출이 생기고(소킹 규칙 위반) 결과도 달라질 수 있다."""
    if path is None:
        from collector import LOG_FILE
        path = LOG_FILE
    if not path.exists():
        return None
    size = path.stat().st_size
    buf = b""
    pos = size
    scanned = 0
    with open(path, "rb") as f:
        while pos > 0 and scanned < CYCLE_RECORD_SCAN_BYTES:
            step = min(chunk, pos)
            pos -= step
            scanned += step
            f.seek(pos)
            buf = f.read(step) + buf
            lines = buf.split(b"\n")
            # 맨 앞 조각은 아직 잘린 줄일 수 있다(파일 처음에 닿았으면 온전한 줄이다).
            head, complete = (b"", lines) if pos == 0 else (lines[0], lines[1:])
            for raw in reversed(complete):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(rec, dict) and rec.get("type") == "free_sources":
                    return rec
            buf = head
    return None


def _safe(fn: Callable[[], Any], errors: dict, name: str) -> Any:
    try:
        return fn()
    except Exception as e:  # 한 입력이 깨져도 나머지 시스템은 판정한다.
        # 예외 종류 이름만 남긴다 — 이 값은 공개 API(/api/baikal)로 나간다. 메시지 원문에는
        # 경로·내부 값이 섞일 수 있다(서버 안 장부는 전문, 밖으로는 모양만 — #28 의 선).
        errors[name] = type(e).__name__
        return None


def gather_inputs(now: dt.datetime) -> dict:
    errors: dict[str, str] = {}

    def _health():
        from algorithms.source_health import source_health_report
        return source_health_report()

    def _quality():
        from algorithms.quality_health import quality_report
        return quality_report()

    def _score(preds):
        from algorithms.prediction_scoring import score
        return score(preds)

    def _ledger():
        from algorithms.lead_time_ledger import ledger_record
        return ledger_record()

    def _seal_batch():
        from algorithms.prediction_timestamp import SEAL_BATCH
        return SEAL_BATCH

    def _weekly():
        from algorithms.weekly_forecast import all_forecasts, scorecard
        return scorecard(all_forecasts())

    preds = _safe(db.list_predictions, errors, "predictions")
    since = (now - dt.timedelta(hours=24)).isoformat()
    return {
        "health": _safe(_health, errors, "source_health"),
        "quality": _safe(_quality, errors, "quality_health"),
        "extracted_24h": _safe(lambda: db.count_extracted_signals_since(since),
                               errors, "extracted_signals"),
        "alerts_today": _safe(lambda: db.list_alerts(dt.date.today().isoformat()),
                              errors, "alerts"),
        "predictions": preds,
        "cycle_record": _safe(_latest_cycle_record, errors, "cycle_record"),
        "unsealed": _safe(db.count_unsealed_predictions, errors, "unsealed"),
        "scorecard": _safe(lambda: _score(preds or []), errors, "scorecard")
        if preds is not None else None,
        "ledger": _safe(_ledger, errors, "ledger"),
        "ground_truth": _safe(db.ground_truth_counts, errors, "ground_truth"),
        "seal_batch": _safe(_seal_batch, errors, "seal_batch") or 10,
        "weekly": _safe(_weekly, errors, "weekly_forecasts"),
        "errors": errors,
    }


def observe(now: dt.datetime | None = None, inputs: dict | None = None) -> dict:
    """한 시점의 생태계 상태. 저장하지 않는다(저장은 run_cycle)."""
    now = now or _now()
    i = inputs if inputs is not None else gather_inputs(now)
    systems = [
        judge_huginn(i.get("health"), i.get("quality")),
        judge_mimir(i.get("quality"), i.get("extracted_24h")),
        judge_forseti(i.get("alerts_today"), now),
        judge_skuld(i.get("predictions"), now),
        judge_heimdall(i.get("cycle_record"), now),
        judge_valhalla(i.get("cycle_record"), now),
        judge_var(i.get("unsealed"), i.get("scorecard"), i.get("ledger"),
                  seal_batch=i.get("seal_batch") or 10),
    ]
    counts = {s: sum(1 for x in systems if x["status"] == s) for s in STATUSES}
    loop = loop_state(i.get("scorecard"), i.get("predictions"), i.get("ground_truth"),
                      now.date())
    return {
        "observed_at": now.isoformat(),
        "systems": systems,
        "summary": {"counts": counts, "total": len(systems)},
        "loop": loop,
        "weekly_loop": weekly_loop_state(i.get("weekly")),
        "read_errors": i.get("errors") or {},
        "ontology": "YGGDRASIL",
    }


def diff_transitions(previous: dict | None, current: dict) -> list[dict]:
    """이전 스냅숏과 비교해 **바뀐 것만** 전이로 낸다. 이전이 없으면 '관측 시작'(from=None)."""
    prev_status: dict[str, str] = {}
    prev_loop = None
    if previous:
        prev_status = {s["key"]: s["status"] for s in previous.get("systems") or []}
        prev_loop = (previous.get("loop") or {}).get("state")
    out = []
    for s in current["systems"]:
        before = prev_status.get(s["key"])
        if before == s["status"]:
            continue
        out.append({"subject": s["key"], "from_status": before, "to_status": s["status"],
                    "reason": s["reason"], "evidence_class": s["evidence_class"]})
    loop = current.get("loop") or {}
    if loop.get("state") and loop.get("state") != prev_loop:
        out.append({"subject": "LOOP", "from_status": prev_loop, "to_status": loop["state"],
                    "reason": loop.get("text"), "evidence_class": "measured"})
    # 주간 루프는 따로 센다 — 90일 루프의 전이와 섞이면 "측정 중"이 어느 루프 얘기인지 흐려진다.
    prev_weekly = ((previous or {}).get("weekly_loop") or {}).get("state")
    weekly = current.get("weekly_loop") or {}
    if weekly.get("state") and weekly.get("state") != prev_weekly:
        out.append({"subject": "LOOP_WEEKLY", "from_status": prev_weekly,
                    "to_status": weekly["state"], "reason": weekly.get("text"),
                    "evidence_class": "measured"})
    return out


def run_cycle(now: dt.datetime | None = None, inputs: dict | None = None) -> dict:
    """관측 → 이전과 비교 → 스냅숏·전이 저장 → 보관 기간 지난 스냅숏 정리."""
    now = now or _now()
    snap = observe(now, inputs)
    prev = db.latest_baikal_snapshot()
    transitions = diff_transitions(prev["payload"] if prev else None, snap)
    db.insert_baikal_snapshot(snap["observed_at"], snap)
    for t in transitions:
        db.insert_baikal_transition(snap["observed_at"], t["subject"], t["from_status"],
                                    t["to_status"], t["reason"], t["evidence_class"])
    cutoff = (now - dt.timedelta(days=db.BAIKAL_SNAPSHOT_RETENTION_DAYS)).isoformat()
    db.prune_baikal_snapshots(cutoff)
    return {**snap, "transitions": transitions}


def summary_line(result: dict) -> str:
    """수집 로그 한 줄 — 소킹 점검이 `filter "BAIKAL"` 로 바로 본다."""
    c = result["summary"]["counts"]
    total = result["summary"]["total"]
    parts = [f"정상 {c.get('ok', 0)}/{total}"]
    for key in ("degraded", "down", "undetermined"):
        if c.get(key):
            parts.append(f"{STATUS_KO[key]} {c[key]}")
    parts.append(f"루프 {result['loop']['state_ko']}")
    weekly = result.get("weekly_loop")
    if weekly:
        parts.append(f"주간 루프 {weekly['state_ko']}")
    trans = result.get("transitions") or []
    if trans:
        shown = []
        for t in trans[:4]:
            before = STATUS_KO.get(t["from_status"], LOOP_STATE_KO.get(t["from_status"])) \
                if t["from_status"] else "관측 시작"
            after = STATUS_KO.get(t["to_status"], LOOP_STATE_KO.get(t["to_status"], t["to_status"]))
            shown.append(f"{t['subject']} {before}→{after}")
        more = f" 외 {len(trans) - 4}" if len(trans) > 4 else ""
        parts.append(f"전이 {len(trans)}건({', '.join(shown)}{more})")
    else:
        parts.append("전이 없음")
    if result.get("read_errors"):
        parts.append(f"읽기 실패 {', '.join(sorted(result['read_errors']))}")
    return "🌊 BAIKAL: " + " · ".join(parts)


def history(snapshots: list[dict]) -> list[dict]:
    """화면 타임라인용 — 스냅숏마다 시스템별 상태만 추린다."""
    out = []
    for snap in snapshots:
        p = snap.get("payload") or {}
        out.append({
            "observed_at": snap.get("observed_at"),
            "statuses": {s["key"]: s["status"] for s in p.get("systems") or []},
            "loop": (p.get("loop") or {}).get("state"),
        })
    return out

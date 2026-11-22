"""BAIKAL MOB — 아이기론 상태변화 엔진 (2026-11-22 재구현).

캡틴: "바이칼 몹을 현재 섹션에 맞게 맞춤으로 구현해라 — 상태변화 엔진으로서 아이기론의
핵심 엔진이야. 온톨로지보다 상위계층이야."

## 무엇을 하나

매시 수집 주기가 끝나면, 온톨로지(algorithms/ontology.py)가 적은 엔진 하나하나의 상태를
판정하고, 한 장의 스냅숏으로 남기고, **상태가 바뀐 순간만** 전이로 기록한다. 그리고
온톨로지의 간선을 따라 "한 엔진의 이상이 어느 엔진의 어떤 입력을 낡게 만드는가"를 적는다.
가장 깊고 오래된 호수가 바닥에 층층이 역사를 쌓듯이.

    온톨로지  = 무엇이 있고 무엇이 무엇에 기대는가     (정적)
    BAIKAL    = 지금 각각 어떤 상태이고 언제 바뀌었나  (동적, 그 위층)

## ★ 읽기 전용이다 ★

새 수집을 하지 않는다. 수집 주기가 이미 만든 결과(dict)만 읽는다. 유일한 예외는 헤임달
서열 스크리너 — 요청 때만 도는 엔진이라 매시 상태가 없으므로, 고정된 합성 문자열로
**엔진이 응답하는지**만 확인한다(정확도 판정이 아니다). BAIKAL 이 어떻게 고장 나도 수집과
원장은 그대로 돌아야 한다 — 호출부(collector)가 예외를 삼킨다.

## ★ 상태를 지어내지 않는다 (honesty-review) ★

- 상태는 넷: ok(정상) · degraded(저하) · down(중단) · undetermined(판정 안 함).
  읽을 값이 없으면 '판정 안 함'이지 '정상'이 아니다.
- 엔진마다 `scope_ko` 가 이 상태가 **무엇을 보고** 판정했는지 말한다. 예: 서열 스크리너의
  '정상'은 엔진이 응답한다는 뜻이지 위험 서열을 잘 잡는다는 뜻이 아니다(민감도 미측정).
- 영향(impact)은 하류 엔진의 상태를 **바꾸지 않는다**. "이 입력이 낡았을 수 있다"는 주석일
  뿐이다 — 상류가 멈췄다고 하류가 틀렸다고 단정하지 않는다.
- 첫 관측은 전이가 아니다. 이전 상태를 지어내지 않는다(from=None, '관측 시작').
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

from algorithms import ontology

STATUS_KO = {"ok": "정상", "degraded": "저하", "down": "중단", "undetermined": "판정 안 함"}
STATUSES = tuple(STATUS_KO)
_PROBLEM = ("degraded", "down", "undetermined")

# 직전 스냅숏과 이보다 멀면 그 사이 주기를 못 봤다(배포·재시작·누락) — 공백을 적는다.
CYCLE_GAP_NOTE_HOURS = 2.0
# 스냅숏이 이보다 오래됐으면 API 는 '최신 아님'으로 표시한다(수집이 멎었을 수 있다).
SNAPSHOT_STALE_MINUTES = 130
# 서열 스크리너 응답 확인용 고정 합성 문자열 — 생물학 서열이 아니다(반복 패턴).
SCREENER_PROBE = "ACGT" * 60


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_iso(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _node(status: str, reason: str, *, scope_ko: str, evidence: str = "measured",
          note: str | None = None) -> dict:
    assert status in STATUSES, status
    out = {"status": status, "status_ko": STATUS_KO[status], "reason": reason,
           "scope_ko": scope_ko, "evidence": evidence}
    if note:
        out["note"] = note
    return out


# ── 엔진별 판정 ─────────────────────────────────────────────────────
_COLLECTOR_SCOPE = "이번 수집 주기가 끝까지 돌았는가와 직전 기록과의 간격"


def judge_collector(previous_observed_at: str | None, now: dt.datetime) -> dict:
    """BAIKAL 은 수집 주기 끝에서 불린다 — 불렸다는 것 자체가 주기가 끝났다는 관측이다."""
    prev = _parse_iso(previous_observed_at)
    note = None
    if prev is not None:
        gap_h = (now - prev).total_seconds() / 3600
        if gap_h > CYCLE_GAP_NOTE_HOURS:
            note = f"직전 기록 이후 {gap_h:.1f}시간 공백 — 그 사이 주기는 못 봤음(배포·재시작·누락)"
    return _node("ok", "이번 주기 완료", scope_ko=_COLLECTOR_SCOPE, note=note)


_POLAR_SCOPE = "이번 주기에 8개 관측지 중 기상 자료(Open-Meteo)를 받은 곳의 수"


def _polar_reason_hint(reasons: dict | None) -> str | None:
    if not reasons:
        return None
    text = " ".join(reasons)
    if "limit" in text.lower() or "429" in text:
        return "기상 서비스(Open-Meteo) 사용 한도 초과(HTTP 429)"
    top = max(reasons.items(), key=lambda kv: kv[1])[0]
    return f"기상 서비스 실패: {str(top)[:80]}"


def judge_polar(result: dict) -> dict:
    if result.get("polar_error"):
        return _node("down", f"수집 예외: {result['polar_error']}", scope_ko=_POLAR_SCOPE)
    total = result.get("polar_regions_total")
    got = result.get("polar_regions_with_weather")
    if not isinstance(total, int) or not isinstance(got, int) or total <= 0:
        return _node("undetermined", "이번 주기 극지 결과를 읽지 못함", scope_ko=_POLAR_SCOPE)
    hint = _polar_reason_hint(result.get("polar_failure_reasons"))
    if got == total:
        return _node("ok", f"기상 자료 {got}/{total}곳", scope_ko=_POLAR_SCOPE)
    tail = f" — {hint}" if hint else ""
    if got == 0:
        return _node("down", f"기상 자료 0/{total}곳{tail}", scope_ko=_POLAR_SCOPE)
    return _node("degraded", f"기상 자료 {got}/{total}곳{tail}", scope_ko=_POLAR_SCOPE)


_VARIANTS_SCOPE = "이번 주기 Nextstrain 감시 빌드에서 우세 계통을 읽었는가와 변이 원장 기록 성공"


def judge_heimdall_variants(result: dict) -> dict:
    if result.get("genomic_variants_error"):
        return _node("down", f"Nextstrain 조회 예외: {result['genomic_variants_error']}",
                     scope_ko=_VARIANTS_SCOPE)
    gv = result.get("genomic_variants")
    if not isinstance(gv, dict) or not gv:
        return _node("undetermined", "이번 주기 변이 결과 없음", scope_ko=_VARIANTS_SCOPE)
    builds = list(gv.values())
    read = [b for b in builds if b.get("available") and b.get("dominant_share") is not None]
    unavailable = [b for b in builds if not b.get("available")]
    if not read:
        if len(unavailable) == len(builds):
            why = (unavailable[0].get("reason") or "조회 실패") if unavailable else "조회 실패"
            return _node("down", f"빌드 0/{len(builds)} 읽음 — {str(why)[:80]}",
                         scope_ko=_VARIANTS_SCOPE)
        return _node("undetermined", f"빌드 0/{len(builds)} — 최근 구간 데이터 없음",
                     scope_ko=_VARIANTS_SCOPE)
    first = read[0]
    lead = (f"{first.get('label')}: 우세 {first.get('dominant_clade')} "
            f"({first['dominant_share'] * 100:.0f}%)")
    if result.get("variant_ledger_ok") is False:
        return _node("degraded", f"읽기는 됐으나 변이 원장 기록 실패 · {lead}",
                     scope_ko=_VARIANTS_SCOPE)
    if len(read) < len(builds):
        return _node("degraded", f"빌드 {len(read)}/{len(builds)} 읽음 · {lead}",
                     scope_ko=_VARIANTS_SCOPE)
    return _node("ok", f"빌드 {len(read)}/{len(builds)} 읽음 · {lead}", scope_ko=_VARIANTS_SCOPE)


_SCREENER_SCOPE = ("고정 합성 문자열로 스크리너가 응답하는가 — 엔진 응답 확인일 뿐 정확도가 아님 "
                   "(민감도 미측정, 개발 중)")


def judge_heimdall_screener(probe: Callable[[str], dict] | None = None) -> dict:
    if probe is None:
        from algorithms.genome_signals import screen_sequence as probe
    try:
        r = probe(SCREENER_PROBE)
    except Exception as e:  # noqa: BLE001 — 상태 판정이 수집을 깨면 안 된다
        return _node("down", f"응답 확인 예외: {type(e).__name__}: {str(e)[:80]}",
                     scope_ko=_SCREENER_SCOPE, note="개발 중(검증 진행)")
    if isinstance(r, dict) and r.get("ok"):
        return _node("ok", "엔진 응답 확인", scope_ko=_SCREENER_SCOPE,
                     note="개발 중(검증 진행) — 정확도가 아니라 응답 여부")
    return _node("down", "엔진이 정상 결과를 돌려주지 않음", scope_ko=_SCREENER_SCOPE,
                 note="개발 중(검증 진행)")


_VALHALLA_SCOPE = "이번 주기 준비태세 스냅숏 생성과 무거운 조각(임상 파이프라인) 갱신 실패 여부"


def judge_valhalla(result: dict) -> dict:
    if result.get("valhalla_error"):
        return _node("down", f"스냅숏 예외: {result['valhalla_error']}", scope_ko=_VALHALLA_SCOPE)
    v = result.get("valhalla")
    if not isinstance(v, dict):
        return _node("undetermined", "이번 주기 발할라 결과 없음", scope_ko=_VALHALLA_SCOPE)
    try:
        from algorithms.valhalla_watch import stale_parts
        stale = stale_parts(v)
    except Exception as e:  # noqa: BLE001
        return _node("undetermined", f"갱신 상태 판정 실패: {type(e).__name__}",
                     scope_ko=_VALHALLA_SCOPE)
    if stale:
        parts = ", ".join(f"{k} {p.get('reason')}({p.get('age_hours')}시간 전 값)" for k, p in stale)
        return _node("degraded", f"스냅숏은 생성 · 굳은 조각: {parts}", scope_ko=_VALHALLA_SCOPE)
    return _node("ok", "준비태세 스냅숏 생성 · 갱신 실패 조각 없음", scope_ko=_VALHALLA_SCOPE)


# ── 영향 · 전이 · 스냅숏 ────────────────────────────────────────────
def impacts(nodes: dict[str, dict]) -> list[dict]:
    """상류가 중단·판정 안 함이면, 온톨로지 간선을 따라 하류의 어떤 입력이 낡는지 적는다.

    하류 상태는 바꾸지 않는다 — 주석이다. 저하(degraded)는 일부가 살아 있으므로 번지지 않는다."""
    out = []
    for key in ontology.NODE_ORDER:
        st = (nodes.get(key) or {}).get("status")
        if st not in ("down", "undetermined"):
            continue
        for e in ontology.downstream(key):
            out.append({"from": key, "to": e["to"], "from_status": st,
                        "note_ko": f"{ontology.NODES[key]['name_ko']} {STATUS_KO[st]} — "
                                   f"{ontology.NODES[e['to']]['name_ko']}의 입력"
                                   f"('{e['carries_ko']}')이 최신이 아닐 수 있음"})
    return out


def diff_transitions(previous: dict | None, nodes: dict[str, dict]) -> list[dict]:
    """상태가 바뀐 엔진만. 직전 스냅숏에 없던 엔진은 '관측 시작'(from=None)."""
    prev_nodes = (previous or {}).get("nodes") or {}
    out = []
    for key in ontology.NODE_ORDER:
        cur = nodes.get(key)
        if not cur:
            continue
        before = (prev_nodes.get(key) or {}).get("status")
        if before == cur["status"]:
            continue
        out.append({"node": key, "from_status": before, "to_status": cur["status"],
                    "reason": cur["reason"], "evidence": cur.get("evidence")})
    return out


def observe(result: dict, previous: dict | None, now: dt.datetime | None = None,
            screener_probe: Callable[[str], dict] | None = None) -> dict:
    """수집 결과 → 스냅숏(전이·영향·각 엔진의 '언제부터' 포함). DB 를 건드리지 않는다."""
    now = now or _now()
    observed_at = now.isoformat()
    nodes = {
        "COLLECTOR": judge_collector((previous or {}).get("observed_at"), now),
        "HEIMDALL_VARIANTS": judge_heimdall_variants(result),
        "HEIMDALL_SCREENER": judge_heimdall_screener(screener_probe),
        "VALHALLA": judge_valhalla(result),
        "POLAR": judge_polar(result),
    }
    transitions = diff_transitions(previous, nodes)
    changed = {t["node"] for t in transitions}
    prev_nodes = (previous or {}).get("nodes") or {}
    for key, n in nodes.items():
        n["since"] = observed_at if key in changed else (prev_nodes.get(key) or {}).get("since",
                                                                                    observed_at)
    counts = {s: sum(1 for n in nodes.values() if n["status"] == s) for s in STATUSES}
    return {"observed_at": observed_at, "nodes": nodes, "impacts": impacts(nodes),
            "transitions": transitions, "counts": counts}


def _hm(iso: str | None) -> str:
    t = _parse_iso(iso)
    return t.strftime("%m-%d %H:%M") if t else "?"


def summary_line(snapshot: dict) -> str:
    nodes = snapshot["nodes"]
    ok = snapshot["counts"].get("ok", 0)
    bad = [f"{ontology.NODES[k]['name_ko']} {nodes[k]['status_ko']}"
           f"({_hm(nodes[k].get('since'))}부터 · {nodes[k]['reason']})"
           for k in ontology.NODE_ORDER if nodes[k]["status"] in _PROBLEM]
    return f"🌊 BAIKAL: 정상 {ok}/{len(nodes)}" + (f" · {' · '.join(bad)}" if bad else "")


def transition_lines(snapshot: dict) -> list[str]:
    out = []
    for t in snapshot["transitions"]:
        before = STATUS_KO.get(t["from_status"], "관측 시작") if t["from_status"] else "관측 시작"
        out.append(f"🌊 BAIKAL 전이: {ontology.NODES[t['node']]['name_ko']} "
                   f"{before} → {STATUS_KO[t['to_status']]} — {t['reason']}")
    return out


def run_cycle(result: dict, now: dt.datetime | None = None,
              screener_probe: Callable[[str], dict] | None = None) -> dict:
    """수집 주기 끝에서 부른다: 직전 스냅숏을 읽고, 판정하고, 스냅숏·전이를 저장한다."""
    import db
    previous = db.latest_baikal_snapshot()
    snap = observe(result, previous, now=now, screener_probe=screener_probe)
    db.insert_baikal_snapshot(snap)
    for t in snap["transitions"]:
        db.insert_baikal_transition(snap["observed_at"], t)
    return snap


def snapshot_age_minutes(observed_at: str | None, now: dt.datetime | None = None) -> int | None:
    t = _parse_iso(observed_at)
    if t is None:
        return None
    return int(((now or _now()) - t).total_seconds() // 60)


def api_payload(now: dt.datetime | None = None, transitions_limit: int = 20) -> dict:
    """GET /api/baikal — 최신 스냅숏 + 온톨로지 + 최근 전이. 스냅숏이 없거나 낡으면 그렇게 말한다."""
    import db
    snap = db.latest_baikal_snapshot()
    age = snapshot_age_minutes((snap or {}).get("observed_at"), now)
    return {
        "engine": "BAIKAL MOB",
        "layer_ko": "상태변화 엔진 — 온톨로지 위층",
        "observed_at": (snap or {}).get("observed_at"),
        "age_minutes": age,
        "fresh": age is not None and age <= SNAPSHOT_STALE_MINUTES,
        "freshness_note": (None if snap is None or (age is not None and age <= SNAPSHOT_STALE_MINUTES)
                           else f"마지막 스냅숏이 {age}분 전 — 수집이 멎었을 수 있음(지금 상태로 읽지 말 것)"),
        "nodes": [{"key": k, **ontology.NODES[k], **((snap or {}).get("nodes") or {}).get(k, {})}
                  for k in ontology.NODE_ORDER] if snap else [],
        "impacts": (snap or {}).get("impacts") or [],
        "counts": (snap or {}).get("counts"),
        "transitions": db.list_baikal_transitions(limit=transitions_limit),
        "ontology": ontology.describe(),
        "statuses_ko": STATUS_KO,
    }

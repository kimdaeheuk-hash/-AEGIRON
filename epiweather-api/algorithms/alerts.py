"""경보 피로 방지 엔진 — 인수인계서 Part5 ⑥.

경보 500개 = 아무도 안 봄. GAI(①)·부정적 공간 감시(⑤)가 만들어내는 후보들을
등급별로 분류하고 일일 캡을 적용해, 정말 봐야 할 것만 상위에 남긴다.

  Critical (90점↑) → 즉시 알림, 최대 3개/일
  High     (80점↑) → 일 1회 요약, 최대 5개
  Medium   (70점↑) → 주간 리포트(캡 없음 — 그냥 쌓아둠)
  Low      (70점↓) → 로그만 저장 (후보로도 만들지 않음)

캡 초과분은 버리지 않고 suppressed=1로 표시해 DB에 남긴다(나중에 "오늘 몇 건이
억제됐는지" 확인 가능). 같은 source가 같은 날 반복되면 갱신만 하므로, 수집기가
매시간 돌아도 캡 카운트가 부풀지 않는다.
"""
from __future__ import annotations
import datetime as dt

import db
from .gai import compute_gai
from .negative_space import scan_negative_space
from .unexplained import scan_unexplained
from .signal_metrics import ALERT_MIN_COUNT, meets_alert_minimum
from .notifier import notify_new_alerts, telegram_configured

CRITICAL = 90
HIGH = 80
MEDIUM = 70

DAILY_CAPS = {"critical": 3, "high": 5}  # medium·low는 캡 없음
CANDIDATE_FLOOR = 50  # 이보다 낮은 점수는 후보로도 안 올림 (잡음 방지)
DASHBOARD_TOP_N = 5

# 알림 결과 — ★ 세 상태를 하나로 뭉개지 않는다 ★
# notify_new_alerts()는 '채널 미설정'과 '전송 실패'에 똑같이 False를 돌려준다.
# 조기경보에서 그 둘은 전혀 다른 사건이다: 앞은 캡틴이 아직 안 켠 것이고,
# 뒤는 켜놨는데 경보가 사람에게 안 닿은 것이다. 뒤쪽은 그 자체로 사고다.
NOTIFY_NONE = "보낼 신규 경보 없음"
NOTIFY_UNCONFIGURED = "채널 미설정"
NOTIFY_SENT = "전송됨"
NOTIFY_FAILED = "전송 실패"


def _notify(new_critical_high: list[dict]) -> dict:
    """신규 critical/high를 내보내고, 결과를 '무엇이 일어났는지'로 돌려준다.

    목록이 비어도 notify_new_alerts를 그대로 부른다 — 발송 여부 판단은 원래
    그 함수 안에 있고(빈 목록이면 False), 여기서 앞질러 막으면 호출 자리가
    조건부가 되어 "신규 0건이면 아무한테도 안 간다"는 기존 계약을 시험하던
    자리가 사라진다. 이 함수가 새로 하는 일은 **보고**뿐이다.
    """
    count = len(new_critical_high)
    sent = notify_new_alerts(new_critical_high)
    if not count:
        status = NOTIFY_NONE
    elif not telegram_configured():
        status = NOTIFY_UNCONFIGURED
    else:
        status = NOTIFY_SENT if sent else NOTIFY_FAILED
    return {
        "status": status,
        "new_critical_high": count,
        # ★ 누가 폰을 울렸는지 ★ 건수만 남기면 "알림: 전송됨" 을 보고도 무엇이
        # 나갔는지 알 수 없다. source 는 경보의 중복제거 키이자 억제 로그
        # (`⏸ [alerts] genomic_new_clades_covid …`)가 쓰는 것과 같은 이름이라,
        # 막힌 경보와 나간 경보를 같은 낱말로 대조할 수 있다.
        "sources": [a.get("source") for a in new_critical_high if a.get("source")],
    }


# 이름을 찍는 등급 — 사람을 깨우는 두 등급만. medium·low 는 건수로 충분하다
# (캡이 없어 수십 개가 되고, 그걸 다 나열하면 정작 critical 이름이 묻힌다).
_NAMED_TIERS = ("critical", "high")
# 한 등급에 이름을 몇 개까지 찍는가. 넘치면 `+N` 으로 넘친 사실을 남긴다 —
# 잘린 줄이 '이게 전부'로 읽히면 안 된다.
_MAX_NAMES = 5


def _names(sources: list) -> str:
    """"[a·b·+3]" — 등급 뒤에 붙는 이름표. 없으면 빈 문자열."""
    names = [s for s in sources if s]
    if not names:
        return ""
    shown = names[:_MAX_NAMES]
    if len(names) > _MAX_NAMES:
        shown = shown + [f"+{len(names) - _MAX_NAMES}"]
    return f"[{'·'.join(shown)}]"


def summary_line(result: dict) -> str:
    """스케줄러 로그 한 줄. 수집기 로그처럼 **시험 가능한 자리**에 둔다
    (naver_trends.summary·extraction_summary와 같은 이유).

    ★ 이 한 줄이 없으면 경보가 나갔는지 로그로 확인할 방법이 없었다 ★
    경보 경로는 지금껏 로그를 한 줄도 남기지 않았다. 소스가 죽으면 로그가
    나지만, 경보가 조용한 것은 '평온해서'와 '경로가 끊겨서'가 똑같이 보인다.

    ★ 건수만으로는 부족했다 (2026-09-20) ★ 09-19 점검이 `critical 1건` 이
    13주기 연속 찍히는 것을 보고도 **그게 무슨 경보인지 로그로 알 수 없었다.**
    그 사이 11:03·01:02 두 번 캡틴 폰으로 알림이 나갔는데, 무엇 때문에 울렸는지
    갈리지 않았다. 더 나쁜 것은 critical 이 주기마다 켜졌다 꺼졌다 하는 것이었다
    (23:01 있음 → 00:01 없음 → 01:02 있음 → 03:01 없음). 깜빡이는 경보는
    이 리포가 GroqWatch·Mobility 에서 두 번 데인 모양이다 — 가끔 사라지는 것이
    오히려 추적을 막는다.

    억제된 경보는 이미 이름을 남기고 있었다(`⏸ [alerts] genomic_new_clades_covid
    — …`). **막은 것은 이름을 남기고 나간 것은 안 남기는** 상태였다.
    """
    ts = result.get("tier_summary") or {}
    parts = []
    for tier in ("critical", "high", "medium", "low"):
        info = ts.get(tier) or {}
        total = info.get("total") or 0
        if not total:
            continue
        suppressed = info.get("suppressed") or 0
        piece = f"{tier} {total}건" + (f"(억제 {suppressed})" if suppressed else "")
        if tier in _NAMED_TIERS:
            piece += _names(info.get("sources") or [])
        parts.append(piece)
    body = " · ".join(parts) if parts else "후보 0건"
    n = result.get("notification") or {}
    # 알림은 '무엇이 나갔는지'까지. 상태만 남기면 전송됨·실패 어느 쪽이든
    # 대상이 사라져, 알림이 닿았는지 되짚을 수가 없다.
    return f"{body} · 알림: {n.get('status', '판정 안 함')}{_names(n.get('sources') or [])}"


def classify_tier(score: float) -> str:
    if score >= CRITICAL:
        return "critical"
    if score >= HIGH:
        return "high"
    if score >= MEDIUM:
        return "medium"
    return "low"


def _gai_overall_evidence(gai_result: dict) -> list[str]:
    """GAI 종합 점수의 근거 — 가장 크게 기여한 계층·지표를 실제 수치로 나열.
    "근거 없는 숫자는 기관이 사용 못 함"(인수인계서 Part5 ⑫) — 결재 올릴 수
    있는 형태를 목표로 함."""
    all_metrics = []
    for layer_key, layer in gai_result["layers"].items():
        for m in layer["metrics"]:
            all_metrics.append((layer["label"], m))
    all_metrics.sort(key=lambda x: -x[1]["trusted_score"])

    evidence = []
    for label, m in all_metrics[:3]:
        evidence.append(
            f"{label} · {m['metric']} — 원시 이상도 {m['raw_score']}점 "
            f"(출처신뢰도 {m['trust']} 반영 후 {m['trusted_score']}점)"
        )
    n_free = gai_result.get("sample_size", {}).get("free_sources")
    if n_free is not None:
        evidence.append(f"누적 표본 {n_free}건 기준")
    return evidence


def collect_candidate_alerts(today: str) -> list[dict]:
    """GAI 층별 신호원 + 부정적 공간 감시 + 설명불가 신호를 경보 후보로 변환."""
    candidates = []

    gai_result = compute_gai()
    if gai_result["gai"] is not None and gai_result["gai"] >= CANDIDATE_FLOOR:
        candidates.append({
            "source": "gai:overall",
            "label": "Global Anomaly Index 종합",
            "score": gai_result["gai"],
            "evidence": _gai_overall_evidence(gai_result),
        })
    for layer_key, layer in gai_result["layers"].items():
        for m in layer["metrics"]:
            if m["trusted_score"] < CANDIDATE_FLOOR:
                continue
            # ★ 최소 절대값 문턱 ★ 평소 0 인 카운트 지표는 1 만 나와도 z-score
            # 상한(=최대 이상도)이 찍힌다. 이상도는 그대로 두고(지수는 측정값이다)
            # **사람을 깨우는 자리에서만** 관측값 하한을 건다. 막았다는 사실은
            # 로그에 남긴다 — 조용히 거르면 이번엔 반대로 진짜를 놓쳐도 모른다.
            if not meets_alert_minimum(m["metric"], m.get("latest")):
                print(f"  ⏸ [alerts] {m['metric']} — 이상도 {m['trusted_score']}점이지만 "
                      f"관측값 {m.get('latest')} 이 경보 최소값 "
                      f"{ALERT_MIN_COUNT.get(m['metric'])} 미만이라 경보로 안 올림"
                      f"(지수에는 그대로 반영됨)", flush=True)
                continue
            candidates.append({
                "source": f"gai:{layer_key}.{m['metric']}",
                "label": f"{layer['label']} · {m['metric']}",
                "score": m["trusted_score"],
                "evidence": [
                    f"관측값 {m.get('latest')}",
                    f"원시 이상도(과거 대비 z-score 환산) {m['raw_score']}점",
                    f"출처신뢰도 {m['trust']} 반영 후 최종 {m['trusted_score']}점",
                    f"{layer['label']} 계층 가중치 {layer['weight']}",
                ],
            })

    for a in scan_negative_space()["alerts"]:
        severity = round((1 - a["drop_ratio"]) * 100, 1) if a.get("drop_ratio") is not None else 70.0
        if severity >= CANDIDATE_FLOOR:
            candidates.append({
                "source": f"negative_space:{a['layer']}.{a['metric']}",
                "label": f"{a['label']} · {a['metric']} 보고 급감",
                "score": severity,
                "evidence": [
                    f"최신값 {a['latest']} (과거 평균 {a['history_avg']}의 {a.get('drop_ratio', '—')}배)",
                    "2014년 기니 에볼라 사례 — 보고 급감이 실제론 의료체계 붕괴 신호였음",
                    "신호 증가가 아니라 '보고가 끊긴 것' 자체를 경보 대상으로 봄",
                ],
            })

    # 설명불가 신호는 문서 요구사항대로 무조건 critical(100점)으로 즉시 올림 —
    # 단, 능동 검색(unexplained_cluster)만 대상으로 함. who_wpro 같은 일반
    # 지역동향 요약은 질병명이 없는 게 흔해서, 전체 source를 다 포함하면
    # "원인불명 클러스터"가 아니라 그냥 막연한 요약문까지 critical로 오탐함.
    # 오늘 추출된 것만 후보로 올림(아니면 과거 발견이 매일 영원히 재후보로 뜸).
    for a in scan_unexplained()["alerts"]:
        if a["source"] != "unexplained_cluster":
            continue
        if (a["extracted_at"] or "")[:10] != today:
            continue
        key = a["location"] or a["raw_disease_text"] or a["source"]
        candidates.append({
            "source": f"unexplained:{key}",
            "evidence": [
                f"위치: {a['location'] or '불명'}",
                f"모델이 추출한 원문 질병명: {a['raw_disease_text'] or '불명'} — 기존 알려진 패턴과 불일치 판정",
                f"원문 발췌: {(a['raw_text'] or '')[:120]}",
            ],
            "label": f"설명불가 신호 · {a['location'] or '지역불명'} ({a['raw_disease_text'] or '질병불명'})",
            "score": 100.0,
        })

    # 무역 선행지표(Phase 42) — 의료물자 수입이 여러 품목 동시에 급증한 국가.
    # 다른 층과 성격이 다르다: 뉴스·공식통계는 '지금 벌어지는 일'이지만 무역은
    # 신고 지연이 2개월이라 '몇 달 전 준비 행동'을 사후에 확인하는 층이다.
    # 그래서 점수 상한을 79로 두어 혼자서는 high(80)에 못 닿게 했다 —
    # 다른 층과 겹칠 때 비로소 등급이 올라가야 정직하다.
    # 스캔이 느려서(UN 18회 호출) 실패해도 경보 수집 전체를 막지 않게 격리한다.
    try:
        from algorithms.comtrade_signals import trade_alert_candidates
        for c in trade_alert_candidates():
            if c["score"] >= CANDIDATE_FLOOR:
                candidates.append(c)
    except Exception as e:
        print(f"  ⚠️ [alerts] 무역 급증 후보 수집 실패 — 나머지 경보는 계속: "
              f"{type(e).__name__}: {str(e)[:120]}", flush=True)

    return candidates


def refresh_alerts(today: str | None = None) -> dict:
    """후보를 분류·저장하고, 등급별 일일 캡을 적용해 오늘자 경보 상태를 반환.
    스케줄러가 매시간 돌면서 같은 경보를 반복 재계산하므로, Telegram 알림은
    "오늘 이 source로 처음 잡힌" critical/high 경보에만 보낸다 — 안 그러면
    같은 진행중 경보를 매시간 재통보하게 됨."""
    today = today or dt.date.today().isoformat()
    already_seen_today = {r["source"] for r in db.list_alerts(today)}

    for c in collect_candidate_alerts(today):
        tier = classify_tier(c["score"])
        db.upsert_alert(today, c["source"], tier, c["label"], c["score"], evidence=c.get("evidence"))

    rows = db.list_alerts(today)  # score 내림차순

    by_tier: dict[str, list[dict]] = {"critical": [], "high": [], "medium": [], "low": []}
    for r in rows:
        by_tier[r["tier"]].append(r)

    visible_ids: list[int] = []
    suppressed_ids: list[int] = []
    tier_summary = {}
    for tier, items in by_tier.items():
        cap = DAILY_CAPS.get(tier)
        shown = items if cap is None else items[:cap]
        hidden = [] if cap is None else items[cap:]
        visible_ids += [i["id"] for i in shown]
        suppressed_ids += [i["id"] for i in hidden]
        # sources 는 **억제분까지 포함한 전체**를 점수 내림차순으로 담는다 —
        # total 이 세는 것과 같은 집합이어야 한다. 보이는 것만 담으면 숫자와
        # 이름이 어긋나 "3건인데 이름은 2개" 가 된다.
        tier_summary[tier] = {"cap": cap, "total": len(items), "suppressed": len(hidden),
                              "sources": [i["source"] for i in items]}

    db.set_suppressed(visible_ids, False)
    db.set_suppressed(suppressed_ids, True)

    visible_rows = [r for r in rows if r["id"] in visible_ids]

    new_critical_high = [
        r for r in visible_rows
        if r["tier"] in ("critical", "high") and r["source"] not in already_seen_today
    ]
    # 경보→NPI 자동연결: 신규 critical/high에 '무대응 vs 개입' 반사실 요약을 붙여
    # 알림이 "무엇이 온다"를 넘어 "뭘 하면 어떻게 바뀐다"까지 답하게 한다.
    # (봉인은 대량 알림에서 생략 — 단건 조회 엔드포인트에서 OpenTimestamps 수행)
    from .alert_intervention import enrich_alerts_with_briefs
    new_critical_high = enrich_alerts_with_briefs(new_critical_high, seal=False)
    notification = _notify(new_critical_high)

    dashboard_top = visible_rows[:DASHBOARD_TOP_N]
    hidden_count = len(visible_rows) - len(dashboard_top)

    return {
        "date": today,
        "dashboard": {
            "top": [
                {
                    "label": r["label"], "tier": r["tier"], "score": r["score"],
                    "source": r["source"], "evidence": r.get("evidence", []),
                }
                for r in dashboard_top
            ],
            "hidden_count": hidden_count,
        },
        "tier_summary": tier_summary,
        "notification": notification,
    }

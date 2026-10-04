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
import contextvars
import datetime as dt

import db
from .gai import compute_gai
from .negative_space import scan_negative_space
from .unexplained import scan_unexplained
from .signal_metrics import (ALERT_MIN_COUNT, COUNT_MIN_SIGMA, cap_count_noise_score,
                             count_significance,
                             is_count_noise_metric, meets_alert_minimum,
                             meets_count_significance)
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
# 등급 순서 — 통보 판단이 '등급이 올라갔는가'를 물을 수 있게 수로 만든다.
TIER_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
# comtrade_signals.trade_alert_candidates 가 붙이는 source 접두 — 스캔 실패 때 이 계열만 '판정 안 함'으로 둔다.
TRADE_SOURCE_PREFIX = "trade_surge:"

# collect_candidate_alerts 가 '이 계열은 이번 주기에 판정하지 못했다'를 refresh_alerts 로 알리는 통로.
# 반환형·시그니처를 바꾸지 않으려고(기존 호출부·시험 스텁이 그대로 동작) 컨텍스트 변수로 둔다 —
# 동시에 도는 refresh_alerts 호출끼리 섞이지 않는다.
_UNDETERMINED: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "alerts_undetermined", default=None)


def _mark_undetermined(prefix: str) -> None:
    bucket = _UNDETERMINED.get()
    if bucket is not None and prefix not in bucket:
        bucket.append(prefix)

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
    return {"status": status, "new_critical_high": count}


# 로그 한 줄에 이름을 적을 경보 수. 등급 캡이 critical 3 · high 5 라 최대 8건까지
# 날 수 있는데 다 적으면 줄이 화면을 덮는다. 점수 높은 순 3건이면 무엇이 울렸는지는
# 드러나고, 나머지는 수로만 알린다.
NAMED_IN_LOG = 3


def named_alerts(result: dict) -> str | None:
    """로그에 적을 '무엇이 울렸나'. 경보가 없으면 None.

    ★ 왜 이게 필요했나 ★ (2026-09-21 캡틴 지시)

    09-21 00:03 에 critical 1건이 캡틴 폰으로 나갔다. 로그에 남은 건 이것뿐이다:

        🚨 경보 주기: critical 1건 · medium 2건 · low 7건 · 알림: 전송됨

    **어느 지표인지 알 수가 없다.** 같은 사이클에서 움직인 값이 넷이었고
    (코로나비율·에볼라비율·공급망·조달), 로그만으로는 좁힐 수 없었다.

    09-19 에 같은 문제를 적어두고 고치지 않았다 — 그때는 "다음에"라고 했다.
    그런데 런칭 전 소킹의 1번 판정 기준이 **'거짓 경보 0건'** 이다. 무엇이
    울렸는지 모르면 그게 거짓인지 판정할 수가 없다. 관측이 안 되는 기준은
    기준이 아니다.

    근거 첫 줄을 같이 적는다. GAI 지표는 "관측값 N", 부정적 공간 감시는
    "최신값 X (과거 평균 Y의 Z배)" 라서, 그 한 줄이면 '몇 점'이 아니라
    **'무엇이 몇인데 몇 점'** 이 된다. 잘라내지 않는다 — 예전에 [:40] 절단이
    진단을 통째로 먹은 적이 있다(2026-09 추출 사고).
    """
    top = (result.get("dashboard") or {}).get("top") or []
    if not top:
        return None
    named = []
    for a in top[:NAMED_IN_LOG]:
        head = f"{a.get('label')} {a.get('score')}점"
        evidence = a.get("evidence") or []
        named.append(f"{head}({evidence[0]})" if evidence else head)
    line = " · ".join(named)
    rest = len(top) - len(named)
    return f"{line} 외 {rest}건" if rest > 0 else line


def summary_line(result: dict) -> str:
    """스케줄러 로그 한 줄. 수집기 로그처럼 **시험 가능한 자리**에 둔다
    (naver_trends.summary·extraction_summary와 같은 이유).

    ★ 이 한 줄이 없으면 경보가 나갔는지 로그로 확인할 방법이 없었다 ★
    경보 경로는 지금껏 로그를 한 줄도 남기지 않았다. 소스가 죽으면 로그가
    나지만, 경보가 조용한 것은 '평온해서'와 '경로가 끊겨서'가 똑같이 보인다.
    """
    ts = result.get("tier_summary") or {}
    parts = []
    for tier in ("critical", "high", "medium", "low"):
        info = ts.get(tier) or {}
        total = info.get("total") or 0
        if not total:
            continue
        suppressed = info.get("suppressed") or 0
        parts.append(f"{tier} {total}건" + (f"(억제 {suppressed})" if suppressed else ""))
    body = " · ".join(parts) if parts else "후보 0건"
    # 내려간 행도 수로 남긴다 — 이 숫자가 0에서 움직이는 순간이 '판정이 화면에
    # 반영됐다'는 증거다. 안 적으면 사라진 경보가 왜 사라졌는지 알 수 없다.
    retired = sum((ts.get(t) or {}).get("retired") or 0 for t in ts)
    if retired:
        body = f"{body} · 내림 {retired}건"
    n = result.get("notification") or {}
    line = f"{body} · 알림: {n.get('status', '판정 안 함')}"
    if n.get("retry_pending"):
        line += f"(미전송 {n['retry_pending']}건, 다음 주기에 재시도)"
    names = named_alerts(result)
    return f"{line} | {names}" if names else line


def retired_alerts_line(result: dict) -> str | None:
    """`내림 N건` 의 **이름 줄**. 내려간 행이 없으면 None.

    ★ 왜 따로 두나 ★ (2026-09-30, #46 배포 직후 관측)

    #46 이 프로덕션에서 돌았다 — `내림 3건` 이 두 주기 연속 찍혔다. 그런데 **어느
    행이 내려갔는지는 로그에 없었다.** 상위 경보 구성이 바뀐 것으로 정황만 짚을 수
    있었고, 그 3건이 정당하게(스캔이 더는 후보로 안 만든 행) 내려간 것인지는 판정하지
    못했다. 관측이 안 되는 것은 검증된 게 아니다.

    경보 건수 줄과 **따로** 둔다 — 그 줄은 소킹 점검이 매일 세는 값이라 길이가
    늘면 읽기 어렵다(#40 에서 정한 원칙, negative_space_line 과 같은 이유).

    이 줄은 **오늘 내려가 있는 행 전부**를 적는다(사이클마다 새로 내려간 것만이
    아니다). 한 번 내려간 행은 되살아나지 않는 한 다음 주기에도 같은 줄에 남는다.
    잘라내지 않는다 — 다 적어야 '무엇이 사라졌나'가 닫힌다.
    """
    rows = result.get("retired") or []
    if not rows:
        return None
    parts = [
        f"{r.get('tier')} {r.get('label')} {r.get('score')}점 [{r.get('source')}]"
        for r in rows
    ]
    return f"🔽 내림: {' · '.join(parts)}"


def undetermined_alerts_line(result: dict) -> str | None:
    """이번 주기에 **판정하지 못해** 내리지도 새로 주장하지도 않은 행. 없으면 None.

    `🔽 내림` 과 다른 사실이다: 내림은 '이번 판정에서 후보가 아니었다', 이 줄은 '이번 주기엔
    판정할 수 없었다'(무역 스캔 조회 실패 등). 한 줄에 섞으면 수집 실패가 '값이 내려갔다'로
    읽힌다 — 그게 이 줄이 따로 있는 이유다.
    """
    rows = result.get("undetermined") or []
    if not rows:
        return None
    parts = [
        f"{r.get('tier')} {r.get('label')} {r.get('score')}점 [{r.get('source')}]"
        for r in rows
    ]
    return (f"⏸ 판정 안 함: {' · '.join(parts)} — 이번 주기 스캔이 불완전해 내리지 않고 "
            f"마지막 상태 그대로 둠")


def negative_space_line(result: dict) -> str | None:
    """부정적 공간 감시가 '무엇을 봤고 무엇을 안 봤는지' 한 줄. 없으면 None.

    경보 건수 줄과 **따로** 둔다 — 그 줄은 소킹 점검이 매일 세는 값이라
    길이가 늘면 읽기 어려워진다(#40 에서 정한 원칙).
    """
    ns = result.get("negative_space") or {}
    if not ns:
        return None
    from .negative_space import summary_line as ns_summary
    return f"🔇 부정적 공간: {ns_summary(ns)}"


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


def seen_rank_today(rows: list[dict]) -> dict[str, int]:
    """오늘 이미 잡혀 있는 source 별 **최고 등급**. 통보 판단의 기준선이다."""
    out: dict[str, int] = {}
    for r in rows:
        rank = TIER_RANK.get(r.get("tier"), 0)
        if rank > out.get(r["source"], -1):
            out[r["source"]] = rank
    return out


def carried_rank_from_yesterday(rows: list[dict]) -> dict[str, int]:
    """어제 *화면에 떠 있던* source 별 최고 등급 — 날이 바뀌어도 '진행 중'인 경보의 기준선.

    ★ 왜 필요한가 ★ (2026-10-04 관측)

    `alerts` 는 날짜별로 행을 만든다. 날이 바뀌면 오늘 표가 비어서 어제부터 이어지던
    critical 이 '오늘 처음 보는 것'이 되고, 00:01 주기에 같은 경보가 폰으로 다시 나갔다
    (social_cholera 가 10-03 에 나가고 10-04 00:01 에 또 나갔다). 같은 등급으로 이어지는
    경보는 `escalated` 의 원칙대로 새 소식이 아니다 — 날짜 경계에서만 그 원칙이 깨져 있었다.

    ★ 센 것과 안 센 것 ★ `suppressed` 인 행(자정 직전에 내려간 행 · 등급 캡에 밀린 행)은
    어제 화면에 없었으므로 세지 않는다 — 어제 안 보이던 것이 오늘 올라오면 새 소식이다.
    **보냈는지가 아니라 화면에 떠 있었는지**를 본다: 전송 실패가 기록되지 않아서, 실패한
    통보가 다음 날 재시도되는 일은 이 규칙으로 없다(오늘 안에서도 원래 없던 동작이다).
    """
    out: dict[str, int] = {}
    for r in rows:
        if r.get("suppressed"):
            continue
        rank = TIER_RANK.get(r.get("tier"), 0)
        if rank > out.get(r["source"], -1):
            out[r["source"]] = rank
    return out


def notified_rank_of(rows: list[dict]) -> dict[str, int]:
    """source 별로 **실제로 전송된** 최고 등급. 보낸 적 없는 행(notified_rank 없음)은 안 센다.

    ★ 왜 '화면에 떠 있었나'에서 '보냈나'로 바꿨나 ★ (2026-10-04, 캡틴 지시 9번)

    이월 규칙(`carried_rank_from_yesterday`)은 전송 기록이 없어서 *화면에 떠 있던 것*을 '보낸
    것'으로 간주했다. 그래서 전송이 실패한 critical 도 다음 날 '이미 본 것'이 되어 **재시도되지
    않았다** — 있는 경보를 없는 것으로 만드는 방향이고, 이 제품에서 더 나쁜 쪽이다. 이제는
    전송이 성공했을 때만 기록하고(db.mark_alerts_notified), 이 기록을 기준선으로 쓴다.
    """
    out: dict[str, int] = {}
    for r in rows:
        rank = r.get("notified_rank")
        if rank is None:
            continue
        if rank > out.get(r["source"], -1):
            out[r["source"]] = rank
    return out


def baseline_rank(today_rows: list[dict], yesterday_rows: list[dict],
                  channel_configured: bool) -> dict[str, int]:
    """'이미 알린 것'의 기준선 — 이보다 높은 등급이어야 다시 보낸다.

    - 채널이 설정돼 있으면 **전송 기록**을 쓴다: 실패한 통보는 기준선에 안 들어가 다음 주기에
      재시도된다. 오늘과 어제(이월)를 합친다.
    - 채널이 없으면 재시도할 곳이 없다 — 예전처럼 '잡힌 행 = 본 것'으로 센다. 안 그러면 보낼 수
      없는 통보를 매 주기 만들고 브리프를 붙이느라 일만 한다(기록을 거짓으로 채우지는 않는다).
    """
    if channel_configured:
        return merge_seen_rank(notified_rank_of(today_rows), notified_rank_of(yesterday_rows))
    return merge_seen_rank(seen_rank_today(today_rows), carried_rank_from_yesterday(yesterday_rows))


def merge_seen_rank(today_rank: dict[str, int], carried: dict[str, int]) -> dict[str, int]:
    out = dict(carried)
    for source, rank in today_rank.items():
        if rank > out.get(source, -1):
            out[source] = rank
    return out


def escalated(source: str, tier: str, seen_rank: dict[str, int]) -> bool:
    """이 경보를 사람에게 보내야 하는가.

    ★ 왜 등급을 봐야 하나 ★ (2026-09-27, 소킹 3일차에 관측)

    예전 조건은 `source not in already_seen_today` 였다 — **등급을 안 봤다.**
    그래서 오늘 `low` 로 한 번 잡힌 지표는 그 뒤 `critical` 로 올라가도 '이미 본
    것'이라 조용했다. 09-22 에 `supply_alert_count` 가 critical 로 23시간 떠
    있었는데 통보가 한 번도 안 나갔다.

    거짓 경보의 정반대 방향이고, 조기경보 제품에서는 이쪽이 더 나쁘다 — 거짓은
    신뢰를 깎지만 이건 **있는 경보를 없는 것으로 만든다.**

    매시간 재통보를 막으려는 원래 의도는 그대로다. 달라진 건 '같은 등급'이 아니라
    **'올라간 등급'**만 뚫고 나간다는 것이다:

        처음 보는 source              → 보낸다(기존과 같음)
        low → critical                → 보낸다 ★ 고친 자리
        critical → critical (진행중)  → 안 보낸다(기존과 같음)
        critical → high (완화)        → 안 보낸다 — 나아진 것은 새 소식이 아니다
        high → critical (악화)        → 보낸다
    """
    return TIER_RANK.get(tier, 0) > seen_rank.get(source, -1)


def collect_candidate_alerts(today: str, negative_space: dict | None = None) -> list[dict]:
    """GAI 층별 신호원 + 부정적 공간 감시 + 설명불가 신호를 경보 후보로 변환.

    negative_space 를 받으면 그걸 쓴다 — 호출자가 같은 스캔 결과를 로그에도
    써야 해서다(두 번 돌리면 파일을 두 번 읽는다). 기존 호출부는 그대로 동작한다.
    """
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
            # ★ 소표본 카운트 유의도 ★ (2026-10-04) 게시자 +2명이 최대 이상도를 만든다.
            # 이상도는 그대로 두고 **승격 자리에서만** 카운트 기준 유의도를 본다. 통과·차단
            # 모두 계산값을 로그에 남긴다 — 실제 평균이 얼마였는지가 다음 점검에 값으로 읽힌다.
            if is_count_noise_metric(m["metric"]):
                sig = count_significance(m.get("latest"), m.get("baseline_mean"))
                ok = meets_count_significance(m["metric"], m.get("latest"), m.get("baseline_mean"))
                sig_txt = "계산 불가" if sig is None else f"{sig:.2f}σ"
                print(f"  🧮 [alerts] 소표본 유의도 {m['metric']}: 관측값 {m.get('latest')} · "
                      f"과거 평균 {m.get('baseline_mean')} · {sig_txt} "
                      f"(문턱 {COUNT_MIN_SIGMA}σ) → {'통과' if ok else '경보로 안 올림(지수에는 그대로 반영됨)'}",
                      flush=True)
                if not ok:
                    continue
            # ★ 단독 사회 카운트 신호는 high 미만 ★ 2σ 문턱을 통과한 뒤에도 폰이 울렸다(관측:
            # 평균 1.73 → 5명 2.49σ). 지수 점수는 그대로, 경보 점수만 깎고 깎은 사실을 남긴다.
            score = cap_count_noise_score(m["metric"], m["trusted_score"])
            capped = score < m["trusted_score"]
            if capped:
                print(f"  🧢 [alerts] {m['metric']} — 이상도 {m['trusted_score']}점을 경보 점수 "
                      f"{score}점으로 제한(단독 사회 카운트 신호는 high 미만, 지수에는 그대로 반영됨)",
                      flush=True)
            evidence = [
                f"관측값 {m.get('latest')}",
                f"원시 이상도(과거 대비 z-score 환산) {m['raw_score']}점",
                f"출처신뢰도 {m['trust']} 반영 후 최종 {m['trusted_score']}점",
                f"{layer['label']} 계층 가중치 {layer['weight']}",
            ]
            if capped:
                evidence.append(
                    f"경보 점수는 {score}점으로 제한 — 게시자 수(7일, 겹치는 창) 단독 신호라 "
                    "다른 층과 겹칠 때 비로소 등급이 올라간다")
            candidates.append({
                "source": f"gai:{layer_key}.{m['metric']}",
                "label": f"{layer['label']} · {m['metric']}",
                "score": score,
                "evidence": evidence,
            })

    ns = negative_space if negative_space is not None else scan_negative_space()
    for a in ns["alerts"]:
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
    #
    # ★ 스캔이 못 낸 것과 값이 내려간 것을 가른다 ★ 스캔이 일부 실패했거나 아예 예외가
    # 났으면 '후보가 없다'는 '급증이 없다'가 아니라 '모른다'이다. 그 주기에는 무역 행을
    # 내리지 않고 `undetermined_prefixes` 로 알린다(refresh_alerts 가 '판정 안 함'으로 센다).
    try:
        from algorithms.comtrade_signals import last_scan_incomplete, trade_alert_candidates
        for c in trade_alert_candidates():
            if c["score"] >= CANDIDATE_FLOOR:
                candidates.append(c)
        if last_scan_incomplete():
            _mark_undetermined(TRADE_SOURCE_PREFIX)
    except Exception as e:
        print(f"  ⚠️ [alerts] 무역 급증 후보 수집 실패 — 나머지 경보는 계속: "
              f"{type(e).__name__}: {str(e)[:120]}", flush=True)
        _mark_undetermined(TRADE_SOURCE_PREFIX)

    return candidates


def refresh_alerts(today: str | None = None) -> dict:
    """후보를 분류·저장하고, 등급별 일일 캡을 적용해 오늘자 경보 상태를 반환.
    스케줄러가 매시간 돌면서 같은 경보를 반복 재계산하므로, Telegram 알림은
    "오늘 이 source로 처음 잡힌" critical/high 경보에만 보낸다 — 안 그러면
    같은 진행중 경보를 매시간 재통보하게 됨."""
    today = today or dt.date.today().isoformat()
    # ★ 등급까지 기억한다 ★ source 만 보면 low→critical 승격이 조용해진다(escalated 참조).
    yesterday = (dt.date.fromisoformat(today) - dt.timedelta(days=1)).isoformat()
    seen_rank = baseline_rank(
        db.list_alerts(today), db.list_alerts(yesterday), telegram_configured(),
    )

    negative_space = scan_negative_space()
    live_sources: set[str] = set()
    undetermined_prefixes: list[str] = []
    token = _UNDETERMINED.set(undetermined_prefixes)
    try:
        candidates = collect_candidate_alerts(today, negative_space)
    finally:
        _UNDETERMINED.reset(token)
    for c in candidates:
        tier = classify_tier(c["score"])
        live_sources.add(c["source"])
        db.upsert_alert(today, c["source"], tier, c["label"], c["score"], evidence=c.get("evidence"))

    rows = db.list_alerts(today)  # score 내림차순

    # ★ 후보에서 빠진 행은 내린다 ★ (2026-09-27, #44 배포 직후 관측)
    #
    # upsert 만 하고 내리는 경로가 없어서, 한 번 만들어진 행이 자정까지 남았다.
    # #44 가 social_mpox 를 판정에서 뺀 뒤에도 같은 사이클 로그가 이렇게 찍혔다:
    #
    #     🔇 부정적 공간: 판정 8개 · 급감 0건          ← 스캔은 0건
    #     🚨 경보 주기: critical 1건 … social_mpox …   ← 그런데 화면엔 있다
    #
    # 스캔이 0건인데 경보가 남아 있다는 건 **그 경보가 이번 판정에서 나온 게
    # 아니라는 뜻**이다. 고친 판정이 화면에 반영되지 않으면 고친 게 아니다.
    #
    # 행은 지우지 않는다 — 오늘 무엇이 울렸는지는 감사 기록이고, 되살아나면
    # upsert 가 다시 올린다. 등급 캡 초과분과는 **따로 센다**: 둘 다 '안 보임'
    # 이지만 '한도에 밀림'과 '판정에서 빠짐'은 다른 사실이다.
    #
    # ★ 단, 이번 주기에 *판정하지 못한* 계열은 내리지 않는다 ★ 무역 스캔이 실패한 주기에
    # 후보가 없는 것은 값이 내려간 것이 아니라 못 본 것이다. 그 행은 마지막으로 안 상태 그대로
    # 두고(= 새로 주장도, 지우지도 않는다) 따로 센다. 수집 실패가 진짜 경보를 조용히 내리는
    # 경로를 막는다(09-30 BLZ·AZE 가설).
    def _held(r: dict) -> bool:
        return (bool(undetermined_prefixes) and r["source"] not in live_sources
                and r["source"].startswith(tuple(undetermined_prefixes)))

    held_rows = [r for r in rows if _held(r)]
    retired_rows = [r for r in rows if r["source"] not in live_sources and not _held(r)]
    retired_ids = [r["id"] for r in retired_rows]
    rows = [r for r in rows if r["source"] in live_sources or _held(r)]

    by_tier: dict[str, list[dict]] = {"critical": [], "high": [], "medium": [], "low": []}
    for r in rows:
        by_tier[r["tier"]].append(r)

    retired_by_tier: dict[str, int] = {}
    for r in retired_rows:
        retired_by_tier[r["tier"]] = retired_by_tier.get(r["tier"], 0) + 1

    visible_ids: list[int] = []
    suppressed_ids: list[int] = list(retired_ids)
    tier_summary = {}
    for tier, items in by_tier.items():
        cap = DAILY_CAPS.get(tier)
        shown = items if cap is None else items[:cap]
        hidden = [] if cap is None else items[cap:]
        visible_ids += [i["id"] for i in shown]
        suppressed_ids += [i["id"] for i in hidden]
        tier_summary[tier] = {
            "cap": cap, "total": len(items), "suppressed": len(hidden),
            "retired": retired_by_tier.get(tier, 0),
        }

    db.set_suppressed(visible_ids, False)
    db.set_suppressed(suppressed_ids, True)

    visible_rows = [r for r in rows if r["id"] in visible_ids]

    new_critical_high = [
        r for r in visible_rows
        if r["tier"] in ("critical", "high") and escalated(r["source"], r["tier"], seen_rank)
    ]
    # 경보→NPI 자동연결: 신규 critical/high에 '무대응 vs 개입' 반사실 요약을 붙여
    # 알림이 "무엇이 온다"를 넘어 "뭘 하면 어떻게 바뀐다"까지 답하게 한다.
    # (봉인은 대량 알림에서 생략 — 단건 조회 엔드포인트에서 OpenTimestamps 수행)
    from .alert_intervention import enrich_alerts_with_briefs
    to_mark = [(r["source"], TIER_RANK[r["tier"]]) for r in new_critical_high]
    new_critical_high = enrich_alerts_with_briefs(new_critical_high, seal=False)
    notification = _notify(new_critical_high)
    # ★ 전송이 성공했을 때만 기록한다 ★ 실패·미설정은 기록하지 않는다 — 실패한 critical 은
    # 기준선에 안 들어가 다음 주기에 다시 시도된다(채널이 있을 때). 거짓으로 '보냄'을 적지 않는다.
    if notification["status"] == NOTIFY_SENT:
        db.mark_alerts_notified(today, to_mark)
    elif notification["status"] == NOTIFY_FAILED:
        notification["retry_pending"] = len(to_mark)

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
        # 내려간 행의 이름 — `내림 N건` 이 건수만 말하면 '정당하게 빠진 것'인지 로그로
        # 판정할 수 없다(#40 이 고친 '몇 건만 말하고 무엇을 안 말한다'와 같은 모양).
        "retired": [
            {"label": r["label"], "tier": r["tier"], "score": r["score"], "source": r["source"]}
            for r in retired_rows
        ],
        # 이번 주기에 판정하지 못해 그대로 둔 행 — 내림이 아니다.
        "undetermined": [
            {"label": r["label"], "tier": r["tier"], "score": r["score"], "source": r["source"]}
            for r in held_rows
        ],
        "notification": notification,
        # 무엇이 부정적 공간 감시 밖에 있는지 — 로그로 나가야 목록을 근거로 늘릴 수 있다.
        "negative_space": {
            "metrics_checked": negative_space.get("metrics_checked", 0),
            "alert_count": negative_space.get("alert_count", 0),
            "skipped": negative_space.get("skipped") or {},
        },
    }

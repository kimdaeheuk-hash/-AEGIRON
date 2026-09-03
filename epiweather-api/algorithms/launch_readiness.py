"""런칭 준비도 — **"런칭해도 되나"를 의견이 아니라 측정값으로 만든다.**

## 왜 이게 코드여야 하나

"런칭해도 될 수준인가"는 지금까지 사람이 로그를 뒤져 감으로 답하던 질문이었다.
그러면 두 가지가 일어난다. 답하는 사람마다 기준이 다르고, **낙관 쪽으로 밀린다.**
만든 사람은 잘 돌아가는 날을 더 많이 기억하기 때문이다.

그래서 관문(gate)을 코드로 박는다. 각 관문은 라이브 데이터에서 계산되고, 막힌
이유와 **무엇이 채워져야 풀리는지**를 함께 돌려준다.

## 관문이 이 넷인 이유

| 관문 | 근거 |
|---|---|
| 수집 살아있음 | 제품의 최소 조건 |
| 조용한 저하 없음 | 2026-08 한 달간 조용한 실패 6건 — 전부 소스 헬스를 통과했다 |
| 선행일수 실측 ≥1 | "먼저 안다"가 논지인데 실측이 0건이면 파는 게 논지뿐이다 |
| 캘리브레이션 | 문턱 0.08 은 임의값, 잠복 구간은 문헌값 — 근거처럼 인용하면 안 된다 |

## ★ 이 모듈이 하지 않는 것 ★

**통과를 만들어내지 않는다.** 특히 `lead_time` 관문은 실제 발병이 일어나고 우리가
그걸 먼저 잡아야만 열린다 — 코드로 열 수 있는 게 아니다. 그렇게 만든 것은 의도다.
숫자를 지어내 관문을 여는 순간 이 모듈은 정반대의 물건이 된다.

`ready_for` 는 용도별로 나눠 답한다. 무료 베타는 지금도 되고, 유료 예보는 실측이
쌓여야 한다 — 그 둘을 한 덩어리로 묻는 게 애초에 질문이 틀린 것이었다.
"""
from __future__ import annotations


def _gate(key: str, label: str, passed: bool | None, detail: str,
          unblocks: str, blocking_for: list[str]) -> dict:
    return {
        "key": key,
        "label": label,
        # None = 판정 불가. '모른다'를 '통과'로 세지 않는다.
        "passed": passed,
        "detail": detail,
        "unblocks": unblocks,
        "blocking_for": blocking_for,
    }


def _collection_gate() -> dict:
    from algorithms.source_health import source_health_report, collector_silent_hours

    try:
        report = source_health_report()
        silent = collector_silent_hours()
    except Exception as e:
        return _gate("collection", "수집 파이프라인", None,
                     f"판정 불가 — 소스 헬스를 읽지 못했다: {type(e).__name__}",
                     "소스 헬스 파일이 읽히면 판정된다", ["beta", "paid"])

    degraded = report.get("degraded_sources") or []
    stalled = silent is not None and silent >= 2
    passed = not degraded and not stalled
    if stalled:
        detail = f"수집기가 {silent:.1f}시간째 조용하다 — 스케줄러가 멈춘 것이다"
    elif degraded:
        detail = f"죽은 소스 {len(degraded)}개: {', '.join(str(d) for d in degraded[:5])}"
    else:
        detail = (f"정상 {report.get('healthy_count')}/{report.get('total_tracked')}"
                  f" · 마지막 수집 {silent:.1f}시간 전" if silent is not None
                  else f"정상 {report.get('healthy_count')}/{report.get('total_tracked')}")
    return _gate("collection", "수집 파이프라인", passed, detail,
                 "죽은 소스를 복구하거나 정식으로 은퇴시키면 열린다", ["beta", "paid"])


def _quality_gate() -> dict:
    from algorithms.quality_health import quality_report

    try:
        report = quality_report()
    except Exception as e:
        return _gate("quality", "조용한 저하 감지", None,
                     f"판정 불가: {type(e).__name__}",
                     "품질 헬스가 읽히면 판정된다", ["beta", "paid"])

    degraded = report.get("degraded") or []
    passed = not degraded
    if degraded:
        names = [i["label"] for i in report["invariants"] if i["alarming"]]
        detail = f"저하 중인 불변식 {len(degraded)}개: {', '.join(names)}"
    else:
        detail = (f"불변식 정상 {report.get('healthy_count')}/"
                  f"{report.get('total_invariants')}"
                  + (f" · 판정불가 {report['unknown_count']}"
                     if report.get("unknown_count") else ""))
    return _gate("quality", "조용한 저하 감지", passed, detail,
                 "저하된 층을 고치면 열린다", ["beta", "paid"])


def _lead_time_gate() -> dict:
    from algorithms.prediction_resolver import lead_time_record

    try:
        record = lead_time_record()
    except Exception as e:
        return _gate("lead_time", "선행일수 실측", None,
                     f"판정 불가: {type(e).__name__}",
                     "예측 채점이 돌면 판정된다", ["paid"])

    # ★ 선행성 원장도 함께 센다 ★ (2026-09-03)
    # 예측 채점은 90일 기한이라 첫 결과가 늦게 나온다. 원장은 문턱을 넘는 순간
    # 선제적으로 적어두므로, 다음 공식 선언이 나면 그 자리에서 채점된다 —
    # 실제로는 이쪽이 먼저 열릴 가능성이 높다. 두 경로 중 하나라도 실측이면 연다.
    ledger = {}
    try:
        from algorithms.lead_time_ledger import ledger_record
        ledger = ledger_record()
    except Exception:                                # noqa: BLE001
        ledger = {}

    n = record.get("measured_events") or 0
    ledger_n = ledger.get("measured_events") or 0
    passed = (n + ledger_n) >= 1
    if passed:
        parts = []
        if n:
            parts.append(f"예측 채점 {n}건 · 중앙값 {record.get('median_lead_days')}일 "
                         f"· 최고 {record.get('best_lead_days')}일")
        if ledger_n:
            # ★ 오경보를 같이 적는다 ★ 안 적으면 정밀도 없는 성적표가 인용된다.
            parts.append(f"원장 실측 {ledger_n}건 · 평균 {ledger.get('mean_lead_days')}일 "
                         f"· 오경보 {ledger.get('false_alarms')}건")
        detail = " / ".join(parts)
    else:
        detail = ("실측 0건 — 공식 선언과 대조된 기록이 아직 없다. "
                  "이 상태에서 선행성을 주장하면 근거가 없다. "
                  f"원장이 추적 중인 문턱 통과 {ledger.get('open_crossings') or 0}건")
    return _gate("lead_time", "선행일수 실측", passed, detail,
                 "실제 발병 1건을 먼저 잡아 자동 채점되면 열린다"
                 "(예측 채점 또는 선행성 원장). "
                 "**코드로 열 수 없다 — 시간과 사건이 필요하다**", ["paid"])


def _calibration_gate() -> dict:
    """캘리브레이션 상태 — 미보정 파라미터를 한자리에 모은다.

    흩어져 있으면 각각은 '작은 단서'로 보이지만, 모아놓으면 **무엇을 근거처럼
    인용하면 안 되는지**가 한눈에 보인다.
    """
    uncalibrated = []
    try:
        from algorithms import disaster_watch as dw
        if not getattr(dw, "WINDOWS_CALIBRATED", False):
            uncalibrated.append("재난→발병 잠복 구간(문헌값, 우리 데이터로 미보정)")
        if not getattr(dw, "THRESHOLD_CALIBRATED", False):
            uncalibrated.append("감시창 문턱 0.08(임의값, 실증 근거 없음)")
    except Exception:
        uncalibrated.append("disaster_watch 캘리브레이션 상태를 읽지 못함")

    try:
        from algorithms.prediction_resolver import lead_time_record
        if not lead_time_record().get("is_evidence"):
            uncalibrated.append("예측 문턱(실측 성적이 없어 재보정 불가)")
    except Exception:
        pass

    passed = not uncalibrated
    detail = ("전부 보정됨" if passed
              else f"미보정 {len(uncalibrated)}건: " + " · ".join(uncalibrated))
    return _gate("calibration", "캘리브레이션", passed, detail,
                 "실측 성적이 쌓이면 문헌값·임의값을 우리 데이터로 재보정한다",
                 ["paid"])


def readiness_report() -> dict:
    """런칭 준비도 종합. `/api/launch-readiness` 가 이걸 그대로 낸다."""
    gates = [
        _collection_gate(),
        _quality_gate(),
        _lead_time_gate(),
        _calibration_gate(),
    ]

    def _blockers(audience: str) -> list[dict]:
        # 판정 불가(None)도 막는다 — '모른다'로 런칭하지 않는다.
        return [g for g in gates
                if audience in g["blocking_for"] and g["passed"] is not True]

    beta_blockers = _blockers("beta")
    paid_blockers = _blockers("paid")

    return {
        "gates": gates,
        "passed_count": sum(1 for g in gates if g["passed"] is True),
        "total_gates": len(gates),
        "ready_for": {
            # 무료 베타 — 신호 대시보드. 실측을 쌓는 **유일한** 방법이므로,
            # 파이프라인이 살아있고 저하가 없으면 지금 시작하는 게 맞다.
            "free_beta": not beta_blockers,
            # 유료 예보 — 선행성을 파는 것이므로 실측 없이는 불가.
            "paid_forecast": not paid_blockers,
            # 투자·심사 데모는 '통과'의 문제가 아니라 **정직한 고지**의 문제다.
            # 그래서 불리언으로 답하지 않는다.
            "investor_demo": "가능 — 단 아래 disclosure 를 먼저 제시할 것",
        },
        "blockers": {
            "free_beta": [g["key"] for g in beta_blockers],
            "paid_forecast": [g["key"] for g in paid_blockers],
        },
        "disclosure": _disclosure(gates),
    }


def _disclosure(gates: list[dict]) -> list[str]:
    """심사·영업 자리에서 **먼저** 말해야 하는 것.

    숨겼다가 발각되면 나머지 정직성까지 같이 죽는다. 이 시스템의 가장 큰 자산이
    "지어내지 않는다"는 신뢰이므로, 그걸 지키는 비용은 항상 더 싸다.
    """
    out = []
    for gate in gates:
        if gate["passed"] is True:
            continue
        out.append(f"{gate['label']}: {gate['detail']}")
    if not out:
        out.append("현재 막힌 관문 없음 — 그래도 캘리브레이션 근거는 함께 제시할 것")
    return out

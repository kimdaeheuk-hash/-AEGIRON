"""예측 채점 — 적중률·Brier·보정(calibration).

## 왜 필요한가

지금까지 이 시스템은 예측을 **기록은 했지만 채점 가능한 형식이 아니었다.**
`predictions` 테이블에는 국가·질병·위험도만 있고, 나중에 사람이 `correct`에
참/거짓을 넣는 구조였다. 그건 채점이 아니라 자기평가다:

- **판정 기준이 예측 시점에 없다** → 결과를 본 뒤에 기준을 만들면 합리화가 된다.
- **신뢰도가 없다** → "얼마나 자주 맞았나"는 재도 **"확신한 만큼 맞았나"는 못 잰다.
- **판정 기한이 없다** → 불리한 예측만 미판정으로 남겨두면 적중률이 저절로 오른다.

마지막 항목이 특히 위험하다. 지금 `/api/predictions?verified_only=true`는 판정한
것만 돌려주는데, 판정 **안 한** 것이 왜 안 됐는지는 아무도 보지 않는다.

## 위험도와 신뢰도는 다르다

  위험도 85   "이 나라가 위험하다"          ← 대상에 대한 판단
  신뢰도 0.7  "내 이 판단이 70% 맞을 것 같다" ← 판단에 대한 판단

재보험·보험 쪽은 적중률보다 **보정**을 본다. "0.8이라고 말한 것들이 실제로 80%
맞았는가." 이게 어긋나면 그 회사가 내놓는 확률은 쓸 수 없다. 신뢰도를 안 적으면
아무리 오래 운영해도 보정을 낼 수 없다.

## 채점 지표

- **적중률** — 맞은 비율. 직관적이지만 쉬운 예측만 하면 부풀릴 수 있다.
- **Brier** — `mean((신뢰도 - 실제)²)`. 낮을수록 좋다. 확신했는데 틀리면 크게 벌점이
  붙어 **쉬운 것만 골라 담는 것을 막는다.**
  0.0=완벽, 0.25=전부 0.5로 찍은 것과 동등, 1.0=최악.
- **보정** — 신뢰도 구간별 실제 적중률.

※ 이 모듈의 설계는 자매 프로젝트 I2OS(`app/predictions.py`, 2026-08-08)에서 가져왔다.
   그쪽이 먼저 제대로 만들었고, 도메인만 산업→감염병으로 바꿔 옮겼다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

#: 판정 결과. 채점에 들어가는 것은 correct/incorrect뿐이다.
OUTCOMES = {"correct", "incorrect", "ambiguous", "cancelled", None}
SCORED_OUTCOMES = {"correct", "incorrect"}
#: 판정은 했지만 채점에서 제외되는 것 — 근거 출처는 이쪽도 요구한다.
RESOLVED_OUTCOMES = SCORED_OUTCOMES | {"ambiguous", "cancelled"}

#: 판정 기준이 이보다 짧으면 나중에 해석 여지가 생겨 결국 합리화된다.
MIN_CRITERIA_LEN = 20

#: 보정을 볼 신뢰도 구간.
_BUCKETS = ((0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0))


class PredictionRuleError(ValueError):
    """예측 레코드가 채점 규칙을 어겼다."""


def _parse_date(value: Any) -> dt.date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def is_scoreable(record: dict) -> bool:
    """채점 가능한 형식인가.

    이 기능 이전에 쌓인 기록은 판정 기준·신뢰도가 없어 채점할 수 없다. 그걸
    억지로 점수에 넣으면 없는 실적이 생기므로, **집계에서 빼고 그 수를 따로 센다.**
    """
    return (
        record.get("confidence") is not None
        and bool(record.get("resolution_criteria"))
        and bool(record.get("resolves_by"))
    )


def validate(record: dict) -> list[str]:
    """규칙 위반을 전부 모아 돌려준다. 빈 목록이면 통과.

    ★ 핵심 ★ 판정 기준을 **예측과 동시에** 요구한다. 나중에 쓰게 두면 결과를 보고
    기준을 맞추게 되고, 그 순간 채점표는 증거가 아니라 장식이 된다.
    """
    problems: list[str] = []
    rid = record.get("id", "<id 없음>")

    confidence = record.get("confidence")
    if confidence is None:
        problems.append(f"{rid}: 신뢰도(confidence)가 없다 — 없으면 보정을 못 낸다")
    elif not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        problems.append(f"{rid}: 신뢰도가 숫자가 아니다")
    elif not 0 < float(confidence) < 1:
        # 0이나 1은 '절대'라는 뜻이라 Brier에서 사실상 무한 벌점이다.
        # 그건 예측이 아니라 단정이므로 허용하지 않는다.
        problems.append(f"{rid}: 신뢰도는 0과 1 사이여야 한다 (현재 {confidence})")

    criteria = record.get("resolution_criteria") or ""
    if not criteria:
        problems.append(f"{rid}: 판정 기준(resolution_criteria)이 없다")
    elif len(criteria) < MIN_CRITERIA_LEN:
        problems.append(
            f"{rid}: 판정 기준이 너무 짧다 — 무엇을 보고 어떻게 판정할지 적을 것"
        )

    made_at = _parse_date(record.get("predicted_at"))
    resolves_by = _parse_date(record.get("resolves_by"))
    if resolves_by is None:
        problems.append(f"{rid}: 판정 기한(resolves_by)이 없거나 날짜 형식이 아니다")
    elif made_at and resolves_by <= made_at:
        problems.append(f"{rid}: 판정 기한이 예측 시점보다 뒤여야 한다")

    outcome = record.get("outcome")
    if outcome not in OUTCOMES:
        problems.append(f"{rid}: 알 수 없는 판정 결과 '{outcome}'")

    if outcome in RESOLVED_OUTCOMES:
        # 판정했으면 언제·무엇을 근거로 했는지 남아야 한다. 안 그러면 나중에
        # 그 판정이 옳았는지 아무도 되짚을 수 없다.
        if not record.get("verified_at"):
            problems.append(f"{rid}: 판정했는데 판정 시각이 없다")
        if not record.get("resolution_sources"):
            problems.append(f"{rid}: 판정했는데 근거 출처가 없다")

    return problems


def score(records: Iterable[dict], *, today: dt.date | None = None) -> dict:
    """예측 목록을 채점한다. 판정되지 않은 것은 점수에 넣지 않는다."""
    now = today or dt.date.today()
    records = list(records)

    total = len(records)
    unscoreable = [r for r in records if not is_scoreable(r)]
    usable = [r for r in records if is_scoreable(r)]

    correct = incorrect = excluded = 0
    unresolved = 0
    overdue: list[Any] = []
    scored: list[tuple[float, int]] = []

    for r in usable:
        outcome = r.get("outcome")
        if outcome in SCORED_OUTCOMES:
            actual = 1 if outcome == "correct" else 0
            correct += actual
            incorrect += 1 - actual
            scored.append((float(r["confidence"]), actual))
        elif outcome in {"ambiguous", "cancelled"}:
            # 판정 불가는 채점에서 뺀다. 다만 많아지면 예측을 모호하게 쓰고 있다는
            # 신호라서 별도로 센다.
            excluded += 1
        else:
            unresolved += 1
            by = _parse_date(r.get("resolves_by"))
            if by and by < now:
                # ★ 방치하면 불리한 예측만 미판정으로 남아 적중률이 부풀려진다 ★
                overdue.append(r.get("id"))

    resolved = correct + incorrect
    brier = (
        sum((c - a) ** 2 for c, a in scored) / len(scored) if scored else None
    )

    return {
        "total": total,
        "scoreable": len(usable),
        # 이 기능 이전에 쌓인 기록 — 채점 불가라고 명시한다(조용히 빼지 않는다).
        "unscoreable_legacy": len(unscoreable),
        "resolved": resolved,
        "correct": correct,
        "incorrect": incorrect,
        "unresolved": unresolved,
        "excluded": excluded,
        "accuracy": round(correct / resolved, 4) if resolved else None,
        "brier": round(brier, 4) if brier is not None else None,
        "calibration": _calibration(scored),
        "overdue": overdue,
        "note": _note(resolved, len(overdue), len(unscoreable)),
    }


def _calibration(scored: list[tuple[float, int]]) -> list[dict]:
    """신뢰도 구간별 실제 적중률.

    "0.8이라고 한 것들이 실제로 80% 맞았는가" — 이게 어긋나면 신뢰도 숫자가
    의미를 잃는다. 재보험사가 적중률보다 먼저 보는 지표다.
    """
    out: list[dict] = []
    for low, high in _BUCKETS:
        chosen = [
            (c, a) for c, a in scored
            if low <= c < high or (high == 1.0 and c == high)
        ]
        if not chosen:
            continue
        out.append({
            "range": f"{low:.1f}~{high:.1f}",
            "count": len(chosen),
            "stated": round(sum(c for c, _ in chosen) / len(chosen), 4),
            "actual": round(sum(a for _, a in chosen) / len(chosen), 4),
        })
    return out


def _note(resolved: int, overdue: int, legacy: int) -> str:
    parts: list[str] = []
    if resolved == 0:
        parts.append(
            "판정된 예측이 아직 없다 — 적중률·Brier는 계산되지 않는다. "
            "성적이 없는 것이지 좋은 것이 아니다."
        )
    elif resolved < 20:
        parts.append(
            f"판정 {resolved}건은 통계적으로 이르다 — 적중률과 보정 모두 크게 흔들린다."
        )
    if overdue:
        parts.append(
            f"판정 기한이 지난 미판정 {overdue}건이 있다. 방치하면 불리한 예측만 "
            "남아 성적이 부풀려진다 — 반드시 판정할 것."
        )
    if legacy:
        parts.append(
            f"채점 형식 도입 이전 기록 {legacy}건은 판정 기준·신뢰도가 없어 "
            "집계에서 제외했다(소급 추가하지 않는다 — 사후에 만든 기준은 증거가 아니다)."
        )
    return " ".join(parts) or "정상."

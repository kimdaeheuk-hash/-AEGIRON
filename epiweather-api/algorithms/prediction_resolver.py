"""예측 자동 해소 — **성적표가 비어 있던 진짜 이유.**

## 무엇이 없었나

`predictions` 테이블에는 처음부터 `verified_at` · `lead_days` · `correct` 컬럼이
있었고, `prediction_scoring` 에는 Brier·캘리브레이션까지 갖춘 채점기가 있었다.
`log_notable_predictions` 가 매 주기 예측도 쌓고 있었다.

**그런데 그 사이를 잇는 게 없었다.** 해소(resolve)는 `main.py` 의 수동 API 로만
가능했고 아무도 부르지 않았다. 그래서:

    예측은 쌓인다 → 아무도 채점하지 않는다 → verified_at 이 영원히 null
    → accuracy null → "선행일수 실측 0건"

즉 "아이기론이 남보다 먼저 안다"는 **제품의 논지 그 자체를 증명할 경로가
끊겨 있었다.** 시간이 아무리 흘러도 증거가 안 생기는 구조였다.

## 이 모듈이 하는 일

매일 1회, 미해소 예측을 `outbreak_timeline` 의 **공식 선언 마일스톤**과 대조한다.

    예측(국가, 질병, predicted_at)  ×  공식 선언(국가, 질병, milestone_date)
      → 선언이 판정기한 내에 있으면  correct=1, lead_days = 선언일 - 예측일
      → 기한이 지나도 선언이 없으면  correct=0 (조용했다 — 그것도 채점 대상이다)
      → 기한 전이고 선언도 없으면    아직 미결(건드리지 않는다)

## ★ 정직성 경계선 ★

1. **선행일수를 지어내지 않는다.** 근거는 `outbreak_timeline` 에 실제로 적재된
   공식 마일스톤뿐이고, 해소 기록에 그 `event_id` 를 함께 남긴다. 어떤 선언으로
   맞다고 했는지 되짚을 수 없는 채점은 채점이 아니다.
2. **예측일이 선언일보다 뒤면 맞다고 하지 않는다.** 이미 공개된 뒤에 우리가
   신호를 잡은 것은 '먼저 안 것'이 아니다. `lead_days <= 0` 이면 `correct=0` 이다.
   이 한 줄이 없으면 성적표는 자동으로 부풀려진다.
3. **틀린 것도 채점한다.** 기한 내 선언이 없으면 `correct=0` 으로 닫는다. 맞은
   것만 세면 정밀도만 남고 재현율이 사라져 숫자가 무의미해진다.
4. 자동 해소는 `resolution_sources` 에 `auto:<event_id>` 를 남긴다 — 사람이 손으로
   넣은 판정과 섞이면 나중에 근거를 다시 못 가른다. (기존 `verify_prediction` 이
   이미 "무엇을 보고 판정했는지" 자리를 갖고 있어서 새 컬럼을 만들지 않았다.)
"""
from __future__ import annotations

import datetime as dt

import db

# 공식 '선언급' 마일스톤. 이것만 발병 확인으로 친다.
# status_update(확진자 수 갱신)나 wiki_spike(조회수 급증)는 선언이 아니다 —
# 후자를 정답으로 쓰면 우리 신호로 우리를 채점하는 순환이 된다.
DECLARATION_MILESTONES = {
    "who_pheic",           # WHO 국제공중보건위기 선언
    "who_pandemic",        # WHO 팬데믹 선언
    "who_statement",       # WHO 공개 성명
    "official_declaration",  # 당국 공식 통보
    "drc_official",        # 개별국 보건부 공식 선언
    "msf_first_alert",     # 현장 기관 첫 경보(공개 보도 기준)
    "first_report",        # 공개 최초 보도
}

# 예측 판정 기한. country_risk.PREDICTION_HORIZON_DAYS 와 같은 값을 쓰되,
# import 순환을 만들지 않으려고 여기서 다시 정의하지 않고 읽어온다.
def _horizon_days() -> int:
    try:
        from algorithms.country_risk import PREDICTION_HORIZON_DAYS
        return int(PREDICTION_HORIZON_DAYS)
    except Exception:
        return 90


def _parse_date(value) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    for cut in (10, len(text)):
        try:
            return dt.date.fromisoformat(text[:cut])
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _matches(prediction: dict, event: dict) -> bool:
    """예측과 타임라인 이벤트가 같은 사건을 가리키는가.

    국가·질병 이름이 표기마다 달라서(한글/영문/ISO3) 느슨하게 맞춘다. 느슨한 게
    위험한 쪽은 **거짓 정답**인데, 여기서는 양쪽 다 우리가 적재한 값이라 표기
    변형이 주된 문제이고 무관한 사건이 섞일 여지는 작다. 그래도 질병은 반드시
    겹쳐야 한다 — 국가만 같다고 맞다고 하면 아무 발병이나 정답이 된다.
    """
    disease = (prediction.get("disease") or "").strip().lower()
    country = (prediction.get("country") or "").strip().lower()
    hay = " ".join(str(event.get(k) or "") for k in ("event_id", "event_name")).lower()
    if not disease or not country:
        return False
    disease_hit = disease in hay or any(
        tok and tok in hay for tok in disease.split() if len(tok) >= 3
    )
    country_hit = country in hay or any(
        tok and tok in hay for tok in country.split() if len(tok) >= 3
    )
    return disease_hit and country_hit


def _declarations() -> list[dict]:
    """공식 선언 마일스톤만 모아서 (이벤트, 선언일) 목록으로.

    `list_timeline_events()` 는 event_id 별 **요약**(최신 날짜·마일스톤 수)만 준다.
    우리는 마일스톤 종류와 그 날짜가 필요하므로 `get_timeline()` 으로 펼친다.
    """
    out = []
    for summary in db.list_timeline_events() or []:
        event_id = summary.get("event_id")
        if not event_id:
            continue
        timeline = db.get_timeline(event_id) or {}
        for milestone in timeline.get("milestones") or []:
            if (milestone.get("milestone") or "") not in DECLARATION_MILESTONES:
                continue
            when = _parse_date(milestone.get("event_date"))
            if when is None:
                continue
            out.append({
                "event_id": event_id,
                "event_name": timeline.get("event_name") or summary.get("event_name"),
                "milestone": milestone.get("milestone"),
                "_date": when,
            })
    return out


def resolve_due_predictions(today: dt.date | None = None) -> dict:
    """미해소 예측을 공식 선언과 대조해 채점한다.

    반환: {"resolved": [...], "still_open": n, "checked": n}
    """
    today = today or dt.date.today()
    horizon = _horizon_days()
    declarations = _declarations()

    resolved: list[dict] = []
    still_open = 0
    checked = 0

    for pred in db.list_predictions() or []:
        if pred.get("verified_at"):
            continue                      # 이미 채점됨(수동 포함) — 덮어쓰지 않는다
        predicted = _parse_date(pred.get("predicted_at"))
        if predicted is None:
            continue
        checked += 1
        deadline = predicted + dt.timedelta(days=horizon)

        # ① 기한 내 공식 선언이 있었는가
        hit = None
        for event in declarations:
            if not _matches(pred, event):
                continue
            lead = (event["_date"] - predicted).days
            # ★ 예측이 선언보다 뒤면 '먼저 안 것'이 아니다 ★
            if lead <= 0:
                continue
            if event["_date"] > deadline:
                continue
            if hit is None or event["_date"] < hit["_date"]:
                hit = event

        if hit is not None:
            lead_days = (hit["_date"] - predicted).days
            db.verify_prediction(
                pred["id"],
                actual_result=(
                    f"공식 선언 확인: {hit.get('event_name') or hit.get('event_id')} "
                    f"({hit['_date'].isoformat()}, {hit.get('milestone') or ''})"
                ),
                correct=True,
                lead_days=lead_days,
                outcome="correct",
                resolution_sources=[
                    f"auto:outbreak_timeline:{hit.get('event_id')}:{hit.get('milestone')}"
                    f"@{hit['_date'].isoformat()}"
                ],
            )
            resolved.append({
                "prediction_id": pred["id"], "country": pred.get("country"),
                "disease": pred.get("disease"), "correct": 1,
                "lead_days": lead_days, "event_id": hit.get("event_id"),
            })
            continue

        # ② 기한이 지났는데 선언이 없었다 — 조용했다. 그것도 채점한다.
        if today > deadline:
            db.verify_prediction(
                pred["id"],
                actual_result=f"판정기한({horizon}일) 내 공식 선언 없음",
                correct=False,
                lead_days=None,
                outcome="incorrect",
                resolution_sources=[
                    f"auto:no_declaration_within_{horizon}d"
                    f":deadline={deadline.isoformat()}"
                ],
            )
            resolved.append({
                "prediction_id": pred["id"], "country": pred.get("country"),
                "disease": pred.get("disease"), "correct": 0,
                "lead_days": None, "event_id": None,
            })
            continue

        still_open += 1

    return {"resolved": resolved, "still_open": still_open, "checked": checked}


def lead_time_record() -> dict:
    """선행일수 실측 성적표 — **비어 있으면 비어 있다고 말한다.**

    이 함수가 `measured_events: 0` 을 돌려주는 동안에는 "블루닷보다 빠르다" 같은
    주장을 할 근거가 없다. `benchmark_baselines` 가 세워둔 목표선(블루닷 9일)은
    넘어야 할 기준이지 우리 실적이 아니다.
    """
    leads: list[int] = []
    correct = incorrect = 0
    for pred in db.list_predictions() or []:
        if not pred.get("verified_at"):
            continue
        if pred.get("correct") == 1:
            correct += 1
            if pred.get("lead_days") is not None:
                leads.append(int(pred["lead_days"]))
        elif pred.get("correct") == 0:
            incorrect += 1

    leads.sort()
    n = len(leads)
    median = None
    if n:
        median = float(leads[n // 2]) if n % 2 else (leads[n // 2 - 1] + leads[n // 2]) / 2

    return {
        "measured_events": n,
        "mean_lead_days": round(sum(leads) / n, 1) if n else None,
        "median_lead_days": median,
        "best_lead_days": max(leads) if n else None,
        "resolved_correct": correct,
        "resolved_incorrect": incorrect,
        # ↓ 이 문장이 성적표의 절반이다. 숫자만 내보내면 0건이 '0일 선행'으로 읽힌다.
        "note": (
            "선행일수 실측 없음 — 아직 공식 선언과 대조된 예측이 없다. "
            "이 값이 0인 동안에는 선행성 주장을 할 근거가 없다."
            if n == 0 else
            f"공식 선언과 대조해 자동 채점된 예측 {n}건 기준."
        ),
        "is_evidence": n > 0,
    }

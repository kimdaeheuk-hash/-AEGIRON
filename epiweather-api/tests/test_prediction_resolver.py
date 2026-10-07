"""예측 자동 채점 — 성적표가 비어 있던 진짜 이유 (2026-08-30).

## 무엇이 없었나
`predictions` 에는 `verified_at`·`lead_days`·`correct` 가 처음부터 있었고
`prediction_scoring` 에는 Brier 채점기까지 있었다. `log_notable_predictions` 가
예측도 쌓고 있었다. **그런데 그 사이를 잇는 게 없었다** — 해소는 수동 API 로만
가능했고 아무도 부르지 않았다. 그래서 시간이 아무리 흘러도 증거가 안 생겼다.

## 이 파일이 고정하는 것 — 대부분이 '정직성 경계선'이다
채점기는 성적을 부풀리는 쪽으로 틀리기 가장 쉬운 코드다. 그래서 맞히는 것보다
**부당하게 맞다고 하지 않는 것**을 더 많이 검사한다.

1. ★ 예측이 선언보다 뒤면 맞다고 하지 않는다 ★ — 이미 공개된 걸 잡은 건 선행이 아니다
2. 기한 내 선언이 없으면 틀린 것으로 닫는다 — 맞은 것만 세면 숫자가 무의미해진다
3. 질병이 다르면 국가가 같아도 맞다고 하지 않는다
4. 근거(event_id)를 반드시 남긴다 — 되짚을 수 없는 채점은 채점이 아니다
5. 우리 신호(wiki_spike)로 우리를 채점하지 않는다 — 순환이다
6. 실측이 0건이면 0건이라고 말한다
"""
from __future__ import annotations

import datetime as dt

import db
from algorithms.prediction_resolver import (
    resolve_due_predictions, lead_time_record, DECLARATION_MILESTONES,
)


def _predict(country="DR Congo", disease="에볼라", days_ago=30):
    """과거 시점 예측을 만든다.

    `create_prediction` 은 `predicted_at` 을 항상 '지금'으로 박는다(그게 맞다 —
    예측 시점을 호출부가 정할 수 있으면 소급 기록이 가능해지고, 그 순간 성적표가
    증거이길 그만둔다). 그래서 **프로덕션 API 를 넓히지 않고** 테스트에서만
    행을 직접 백데이트한다.
    """
    row = db.create_prediction(
        country=country, disease=disease, risk_score=80.0, basis=["테스트"],
        confidence=0.7, resolution_criteria="공식 선언이 나오는지로 판정한다(테스트)",
        resolves_by=(dt.date.today() + dt.timedelta(days=60)).isoformat(),
    )
    pid = row["id"] if isinstance(row, dict) else row
    when = (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()
    with db.get_connection() as conn:
        conn.execute("UPDATE predictions SET predicted_at = ? WHERE id = ?", (when, pid))
    return pid


def _declare(event_id="ebola_drc_2026", name="에볼라 DR Congo 2026",
             milestone="who_pheic", days_ago=10):
    db.upsert_timeline_event(
        event_id, name,
        (dt.date.today() - dt.timedelta(days=days_ago)).isoformat(),
        milestone, "테스트 선언", "WHO", "who",
    )


# ── ★핵심★ 선행일수가 실제로 측정된다 ──────────────────────────────

def test_declaration_after_prediction_is_scored_with_lead_days(isolated_db):
    """예측 30일 전 → 선언 10일 전 = 20일 선행."""
    pid = _predict(days_ago=30)
    _declare(days_ago=10)

    outcome = resolve_due_predictions()
    hit = next(r for r in outcome["resolved"] if r["prediction_id"] == pid)

    assert hit["correct"] == 1
    assert hit["lead_days"] == 20
    assert hit["event_id"] == "ebola_drc_2026"

    record = lead_time_record()
    assert record["measured_events"] == 1
    assert record["best_lead_days"] == 20
    assert record["is_evidence"] is True


def test_resolution_records_its_evidence(isolated_db):
    """★되짚을 수 없는 채점은 채점이 아니다★"""
    pid = _predict(days_ago=30)
    _declare(days_ago=10)
    resolve_due_predictions()

    stored = db.get_prediction(pid)
    assert stored["verified_at"]
    sources = stored.get("resolution_sources") or ""
    assert "ebola_drc_2026" in str(sources)
    assert "auto:" in str(sources), "사람 판정과 자동 판정이 구분돼야 한다"


# ── ★가장 위험한 쪽★ 부당하게 맞다고 하지 않는다 ────────────────────

def test_prediction_after_declaration_is_not_credited(isolated_db):
    """★이 한 줄이 없으면 성적표는 자동으로 부풀려진다★

    선언이 60일 전, 예측이 30일 전 — 이미 공개된 뒤에 신호를 잡은 것이다.
    그건 '먼저 안 것'이 아니므로 적중으로 세면 안 된다.
    """
    pid = _predict(days_ago=30)
    _declare(days_ago=60)

    resolve_due_predictions()
    stored = db.get_prediction(pid)

    # 기한(90일) 안이므로 아직 미결이거나, 닫혔다면 반드시 '틀림'이어야 한다.
    assert stored.get("correct") != 1, "선언보다 뒤에 한 예측을 적중으로 세면 안 된다"
    assert lead_time_record()["measured_events"] == 0


def test_different_disease_same_country_is_not_credited(isolated_db):
    """국가만 같다고 맞다고 하면 아무 발병이나 정답이 된다."""
    _predict(country="DR Congo", disease="콜레라", days_ago=30)
    _declare(event_id="ebola_drc_2026", name="에볼라 DR Congo 2026", days_ago=10)

    resolve_due_predictions()
    assert lead_time_record()["measured_events"] == 0


def test_our_own_signal_is_not_used_as_ground_truth(isolated_db):
    """★순환 방지★ wiki_spike 는 우리가 만든 신호다 — 정답지로 쓰면 자기채점이다."""
    assert "wiki_spike" not in DECLARATION_MILESTONES
    assert "status_update" not in DECLARATION_MILESTONES

    _predict(days_ago=30)
    _declare(milestone="wiki_spike", days_ago=10)

    resolve_due_predictions()
    assert lead_time_record()["measured_events"] == 0


# ── 틀린 것도 채점한다 ──────────────────────────────────────────────

def test_silent_period_closes_as_incorrect_after_the_horizon(isolated_db):
    """기한이 지나도 선언이 없으면 틀린 것으로 닫는다.

    맞은 것만 세면 정밀도만 남고 재현율이 사라져 숫자가 무의미해진다.
    """
    pid = _predict(days_ago=200)              # 판정기한(90일) 한참 지남
    # 정답 경로가 그 기간을 보고 있었다는 전제(예측 전날부터 가동, 구간 안에 선언 1건)
    from tests._live_channel import seed_live_channel
    start = dt.date.today() - dt.timedelta(days=200)
    seed_live_channel(start - dt.timedelta(days=1), start + dt.timedelta(days=10))

    outcome = resolve_due_predictions()
    closed = next(r for r in outcome["resolved"] if r["prediction_id"] == pid)

    assert closed["correct"] == 0
    assert closed["lead_days"] is None
    record = lead_time_record()
    assert record["resolved_incorrect"] == 1
    assert record["measured_events"] == 0     # 선행일수는 적중에서만 나온다


def test_open_prediction_within_horizon_is_left_alone(isolated_db):
    """기한 전이고 선언도 없으면 아직 미결이다 — 성급히 틀렸다고 닫지 않는다."""
    pid = _predict(days_ago=10)

    outcome = resolve_due_predictions()

    assert outcome["still_open"] == 1
    assert not any(r["prediction_id"] == pid for r in outcome["resolved"])
    assert db.get_prediction(pid).get("verified_at") is None


def test_already_verified_predictions_are_not_overwritten(isolated_db):
    """사람이 손으로 넣은 판정을 자동 채점이 덮으면 근거가 사라진다."""
    pid = _predict(days_ago=30)
    db.verify_prediction(pid, actual_result="사람이 판정", correct=True,
                         lead_days=5, outcome="correct",
                         resolution_sources=["manual:캡틴"])
    _declare(days_ago=10)

    resolve_due_predictions()
    stored = db.get_prediction(pid)

    assert stored["lead_days"] == 5, "수동 판정이 유지돼야 한다"
    assert "manual" in str(stored.get("resolution_sources") or "")


# ── 비어 있으면 비어 있다고 말한다 ──────────────────────────────────

def test_empty_record_says_it_has_no_evidence(isolated_db):
    """★0건을 '0일 선행'으로 읽히게 두면 안 된다★"""
    record = lead_time_record()

    assert record["measured_events"] == 0
    assert record["is_evidence"] is False
    assert record["mean_lead_days"] is None
    assert "근거가 없다" in record["note"]

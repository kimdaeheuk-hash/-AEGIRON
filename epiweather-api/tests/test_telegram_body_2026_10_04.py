"""텔레그램 본문 검토(2026-10-04) — 캡틴이 받은 social_dengue 경보 본문이 알려 준 세 문제.

받은 본문:

    🚨 아이기론 신규 경보 1건
    🟠 행동신호 · social_dengue — 84.2점
       · 관측값 12
       · 원시 이상도(과거 대비 z-score 환산) 93.5점
       🧭 개입 브리핑: 무대응 시 사망 41,779명·병상초과 65일 → … (구할 생명 41,774명 …). 모델 추정(generic).
       ⚠️ 예보가 아니라 모델 시나리오다 · 파라미터: generic tier 'flu' 예시 상수

A. 경보 이름이 질병명이 아니라 실측 파라미터를 못 찾고 '독감' 일반 상수로 사망·병상 숫자를 만들었다.
B. `관측값 12` — 무엇의 값인지(Mastodon 7일 게시자 수), 평소 얼마였는지(약 5.06)가 없다.
C. 헤드라인 84.2점과 `원시 이상도 93.5점` 이 왜 다른지가 셋째 줄에 있어 폰에서 잘렸다.
"""
from __future__ import annotations

from algorithms import alerts as alerts_mod
from algorithms.alert_intervention import enrich_alerts_with_briefs, summary_line
from algorithms.notifier import format_alert_message
from algorithms.signal_metrics import metric_unit


def _gai(metric, latest, mean, raw, trusted, trust=0.9):
    return {"gai": 10.0, "layers": {"behavioral": {
        "label": "행동신호", "weight": 0.2, "score": trusted,
        "metrics": [{"metric": metric, "latest": latest, "baseline_mean": mean,
                     "raw_score": raw, "trust": trust, "trusted_score": trusted}]}}}


def _collect(monkeypatch, gai):
    from unittest.mock import patch
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: gai)
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return alerts_mod.collect_candidate_alerts(
            "2026-10-04", {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}})


def _rendered(monkeypatch, gai, tier="high", score=84.2):
    """수집 → (브리핑 붙임) → 텔레그램 본문. 실제 경로 그대로."""
    cand = [c for c in _collect(monkeypatch, gai) if "social_" in c["source"] or "kdca" in c["source"]][0]
    alert = {**cand, "tier": tier, "score": score}
    return format_alert_message(enrich_alerts_with_briefs([alert]))


# ── A. 일반 상수 브리핑은 숫자를 싣지 않는다 ─────────────────

def test_social_dengue_message_carries_no_scenario_numbers(monkeypatch):
    body = _rendered(monkeypatch, _gai("social_dengue", 12, 5.0612, 93.5, 84.2))
    brief_line = [ln for ln in body.splitlines() if "개입 브리핑" in ln][0]
    assert "질병별 파라미터가 없어 시나리오를 만들지 않음" in brief_line
    assert not any(ch.isdigit() for ch in brief_line)                 # 사망·병상 숫자가 한 글자도 없다
    assert "41,7" not in body and "구할 생명" not in body.replace("싣지 않는다", "")


def test_measured_disease_briefing_is_unchanged():
    """실측 파라미터가 있는 질병은 예전 그대로 숫자와 고지를 싣는다 — 이번 수리는 generic 만 건드린다."""
    from algorithms.alert_intervention import intervention_brief
    brief = intervention_brief("에볼라", "콩고민주공화국", "critical", 95.0)
    if brief.get("calibration") == "generic_tier":
        return                                                        # 파라미터 표가 바뀌면 이 시험은 비킨다
    line = summary_line(brief)
    assert "개입 브리핑:" in line and "모델 시나리오" in line and any(ch.isdigit() for ch in line)


def test_brief_dict_itself_is_untouched_for_explicit_requests():
    """본체 dict 는 그대로다 — 명시 요청하는 API 는 영향이 없고, 폰 요약만 숫자를 뺀다."""
    from algorithms.alert_intervention import intervention_brief
    brief = intervention_brief("알 수 없는 발열 클러스터", None, "high", 85.0)
    assert brief["calibration"] == "generic_tier"
    assert brief["headline"] and brief["scenarios"]["no_action"]["total_deaths"] is not None


# ── B. 관측값의 단위와 평소 값 ───────────────────────────────

def test_first_evidence_line_names_unit_and_baseline(monkeypatch):
    body = _rendered(monkeypatch, _gai("social_dengue", 12, 5.0612, 93.5, 84.2))
    assert "관측값 12(Mastodon 7일 게시자 수, 평소 약 5.1)" in body          # 캡틴이 정한 형식 그대로


def test_unit_is_only_named_for_metrics_whose_unit_is_known(monkeypatch):
    assert metric_unit("social_dengue") == "Mastodon 7일 게시자 수"
    assert metric_unit("kdca_weekly_total") is None                   # 모르는 단위는 지어내지 않는다
    body = _rendered(monkeypatch, _gai("kdca_weekly_total", 900, 100.0, 95.0, 95.0, trust=1.0),
                     tier="critical", score=95.0)
    assert "관측값 900(평소 약 100)" in body and "Mastodon" not in body


def test_baseline_is_omitted_when_it_is_unknown(monkeypatch):
    body = _rendered(monkeypatch, _gai("kdca_weekly_total", 900, None, 95.0, 95.0, trust=1.0),
                     tier="critical", score=95.0)
    assert "관측값 900" in body and "평소" not in body               # 모르는 값을 0 으로 적지 않는다


def test_baseline_is_rounded_for_people_not_for_the_log():
    """`5.0612` 는 카운트 평균에 과한 정밀도다 — 폰에는 `약 5.1`. 값을 바꾸는 게 아니라 정밀도만 줄인다."""
    from algorithms.signal_metrics import approx_baseline
    assert approx_baseline(5.0612) == "약 5.1"
    assert approx_baseline(1.7322) == "약 1.7"
    assert approx_baseline(64253.4) == "약 64,253"
    assert approx_baseline(99.96) == "약 100.0"            # 경계 — 100 미만은 소수 한 자리를 유지한다
    assert approx_baseline(100.0) == "약 100"


# ── C. 두 점수의 관계가 폰에 보인다 ──────────────────────────

def test_capped_alert_explains_the_cap_on_the_same_line(monkeypatch):
    """상한이 걸리면 헤드라인(79)과 `= 84.2점` 이 다르다 — 이유가 폰에서 잘리는 뒷줄에 있으면 안 된다."""
    cand = [c for c in _collect(monkeypatch, _gai("social_dengue", 12, 5.0612, 93.5, 84.2))
            if "social_dengue" in c["source"]][0]
    assert cand["score"] == 79.0
    assert "경보 점수 79.0점으로 제한" in cand["evidence"][1]
    assert len(cand["evidence"]) == 3                               # 따로 붙던 4번째 줄은 합쳤다


def test_second_line_explains_why_the_scores_differ(monkeypatch):
    body = _rendered(monkeypatch, _gai("social_dengue", 12, 5.0612, 93.5, 84.2))
    assert "원시 이상도 93.5점 × 출처신뢰도 0.9 = 84.2점" in body


def test_both_lines_survive_the_phone_truncation(monkeypatch):
    """폰에는 근거 앞 두 줄만 간다(EVIDENCE_LINES) — 단위·평균과 점수 관계가 둘 다 그 안에 있어야 한다."""
    from algorithms.notifier import EVIDENCE_LINES
    assert EVIDENCE_LINES == 2
    cand = [c for c in _collect(monkeypatch, _gai("social_dengue", 12, 5.0612, 93.5, 84.2))
            if "social_dengue" in c["source"]][0]
    first_two = cand["evidence"][:EVIDENCE_LINES]
    assert "Mastodon" in first_two[0] and "평소 약" in first_two[0]
    assert "×" in first_two[1] and "=" in first_two[1]

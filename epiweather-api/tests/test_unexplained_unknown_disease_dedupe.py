"""질병을 모르는 원인불명 보고도 같은 곳이면 같은 사건이다 (2026-10-25, 소킹 10-22 22:02 폰 재경보).

이르쿠츠크 사건이 `질병불명` · `러시아 이르쿠츠크, 중국` 으로 다시 뽑히자 재탐지 판정이 질병명이 비었다는
이유로 통째로 건너뛰어졌다 → '설명 불가 — 즉시경보'로 다시 저장 → critical 이 폰으로 갔다. 고정하는 것:
① 질병을 모르면 곳만 본다 ② 같은 곳은 지역 낱말 또는 같은 나라(한·영 표기 무관) ③ 곳이 다르면 새 사건
④ 질병을 둘 다 알면 예전처럼 질병도 맞아야 한다.
"""
from __future__ import annotations

from algorithms.unexplained import _is_duplicate_event


def test_the_2026_10_22_irkutsk_rerun_is_a_duplicate():
    recent = [{"disease": "질병불명", "location": "Irkutsk, Russia"}]
    assert _is_duplicate_event({"disease": "질병불명", "location": "러시아 이르쿠츠크, 중국"}, recent)
    assert _is_duplicate_event({"disease": None, "location": "러시아 시베리아"}, recent)


def test_unknown_disease_elsewhere_is_new():
    recent = [{"disease": "질병불명", "location": "Irkutsk, Russia"}]
    assert not _is_duplicate_event({"disease": "질병불명", "location": "Lagos, Nigeria"}, recent)


def test_known_diseases_must_still_agree():
    recent = [{"disease": "한타바이러스 심폐증후군", "location": "Argentina"}]
    assert _is_duplicate_event({"disease": "한타바이러스", "location": "아르헨티나"}, recent)
    assert not _is_duplicate_event({"disease": "콜레라", "location": "Argentina"}, recent)


def test_one_side_unknown_matches_by_place():
    recent = [{"disease": "페스트", "location": "러시아 이르쿠츠크"}]
    assert _is_duplicate_event({"disease": "unknown", "location": "Irkutsk, Russia"}, recent)

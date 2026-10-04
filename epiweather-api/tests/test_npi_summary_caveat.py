"""텔레그램에 실제로 실리는 한 줄이 스스로 단서를 달고 가는가 (2026-09-19).

## 왜 이 파일이 있나

09-19 05:47, 아이기론이 **처음으로 사람에게 보낸 경보**에 이 줄이 붙어 나갔다:

    🧭 개입 브리핑: 무대응 시 사망 69,092명·병상초과 57일 → … 질병별 실측 캘리브레이션.

브리핑 dict 에는 경고가 제대로 들어 있었다(`disclaimer`: "절대값이 아닌 방향성
참고", "구할 생명은 모델 추정이며 실측·보장이 아니다"). 그런데 **사람이 읽는
한 줄에는 그게 하나도 안 실렸다.** 그리고 headline 이 하필 "질병별 실측
캘리브레이션"으로 끝나서, 경고가 빠진 자리에 오히려 더 믿음직한 말이 들어갔다.

모듈은 정직했는데 **출구가 그걸 흘렸다.** 이 리포가 반복해서 잡아온 모양이다 —
근거가 숫자에서 떨어져 나가 숫자만 돌아다닌다.
"""
from __future__ import annotations

from algorithms.alert_intervention import intervention_brief, summary_line


def _line(disease: str, tier: str = "high", score: float = 85.0) -> str:
    return summary_line(intervention_brief(disease, None, tier, score))


# ── ★핵심★ 숫자는 단서 없이 혼자 나가지 않는다 ──────────────────
def test_the_telegram_line_says_it_is_a_model_scenario():
    """★이 테스트가 이 파일의 이유다★ 사망자 수가 단서 없이 폰에 뜨면 그건
    예보로 읽힌다. dict 안에만 있는 경고는 아무도 안 읽는다."""
    line = _line("비공식신호 · genomic_new_clades_covid")
    assert "69,092" in line          # 숫자는 그대로 간다 — 숨기는 게 아니다
    assert "모델 시나리오" in line     # 다만 정체를 같이 밝힌다
    assert "예보가 아니" in line


def test_the_line_carries_the_parameters_the_number_came_from():
    """★핵심★ 69,092명은 covid19 실측 파라미터로 나오는데, 그 출처가
    'COVID-19 조상주 추정 … 초기 CFR ~1.5%(IFR 더 낮음)' 이다. 지금 도는
    계통에 2020년 초기 치명률을 적용한 값이라는 뜻이고, 그게 빠지면
    '실측 캘리브레이션'이라는 말이 실제보다 강하게 읽힌다."""
    line = _line("비공식신호 · genomic_new_clades_covid")
    assert "조상주" in line
    assert "IFR 더 낮음" in line


def test_generic_tier_sends_no_scenario_numbers():
    """실측 파라미터가 없는 질병은 일반 예시 상수로 돈다 — 이제 **그 숫자를 폰에 안 싣는다**.

    예전 계약은 '숫자는 싣되 generic 이라고 고지'였다. 그런데 `행동신호 · social_dengue`(Mastodon
    게시자 12명) 경보에 '사망 41,779명 … 구할 생명 41,774명'이 독감 일반 상수로 나갔다(2026-10-04).
    고지문이 있어도 폰에서는 큰 숫자가 먼저 읽힌다. 근거 없는 숫자는 만들지 않는다 — 사유만 보낸다.
    """
    line = _line("알 수 없는 발열 클러스터")
    assert "질병별 파라미터가 없다" in line
    assert "만들지 않음" in line
    assert not any(ch.isdigit() for ch in line)          # 사망·병상 숫자가 한 글자도 없다
    assert "구할 생명" not in line.replace("싣지 않는다", "")


# ── 전파 양식 단서 ──────────────────────────────────────────────
def test_limited_transmission_note_rides_along():
    """R0<1 병원체는 SEIR 숫자만 남으면 대유행처럼 읽힌다. '사람간 지속전파가
    제한적'이라는 단서가 같은 줄에 붙어야 숫자가 오해되지 않는다."""
    brief = intervention_brief("니파", None, "critical", 95.0)
    line = summary_line(brief)
    if brief.get("spread_note"):        # 파라미터가 바뀌어도 테스트가 거짓말하지 않게
        assert brief["spread_note"] in line


def test_summary_survives_a_brief_without_parameters():
    """브리핑 모양이 바뀌어도 한 줄 만들기가 터지면 안 된다 — 경보 발송이
    처방 생성 실패로 막히지 않는다는 기존 계약(enrich_alerts_with_briefs)과
    같은 방향이다."""
    line = summary_line({"headline": "무대응 시 사망 1명"})
    assert "무대응 시 사망 1명" in line
    assert "모델 시나리오" in line

"""출구 감사 ① — 숫자가 폰에 도착할 때 근거도 같이 도착하는가 (2026-09-20).

## 왜 이 파일이 있나

캡틴: *"이제 곧 런칭할까 해. 그런데 문제점이 너무 많이 남은 거 같아서 걱정이다"*

이틀간 나온 버그 넷이 전부 같은 모양이었다 — **경계에서 자격이 떨어져 나간다.**
그래서 숫자가 사람에게 나가는 자리를 전부 훑었다. 두 군데가 더 있었고, 둘 다
**폰으로 가는 길**이었다.

    웹 대시보드   evidence·disclaimer·honesty·caveat 를 그린다 ✅
    텔레그램      셋 다 안 보냈다                              ❌

먼저 도착하는 쪽, 묻지도 않았는데 도착하는 쪽, 스크린샷이 찍히는 쪽이 폰이다.

## 무엇이 빠져 있었나

1. **경보 근거** — 폰에 뜬 건 `🟠 … genomic_new_clades_covid — 85.0점` 한 줄.
   그게 '신규 계통 1건'이라는 걸 알아내려고 Railway 로그를 뒤져야 했다(09-19).
   `alerts._gai_overall_evidence` 는 *"근거 없는 숫자는 기관이 사용 못 함"* 이라고
   docstring 에 적고 evidence 를 만들고 있었다. 만들어만 두고 안 보냈다.

2. **섹션 정직성 고지** — `brief_sections` 는 섹션마다 honesty 를 붙인다. 예보
   섹션 것은 *"측정된 발병 수가 아니라 신호 시계열의 외삽"*. 텔레그램은
   icon·title·lead·rows 만 읽었다. 그래서 폰에는 `4,885명 → 14일 후 6,200명` 이
   **사람 수처럼** 떴다.
"""
from __future__ import annotations

from algorithms.notifier import (EVIDENCE_LINES, _special_lines,
                                 format_alert_message, format_daily_brief_message)


def _alert(**kw) -> dict:
    base = {
        "tier": "high", "label": "비공식신호 · genomic_new_clades_covid", "score": 85.0,
        "evidence": ["관측값 1", "원시 이상도(과거 대비 z-score 환산) 100.0점",
                     "출처신뢰도 0.85 반영 후 최종 85.0점", "비공식신호 계층 가중치 0.2"],
    }
    return {**base, **kw}


# ── ★핵심★ 근거가 숫자를 따라간다 ─────────────────────────────
def test_the_observation_behind_the_score_reaches_the_phone():
    """★이 테스트가 이 파일의 이유다★ 09-19 에 폰으로 간 그 경보다. '85.0점'
    옆에 '관측값 1' 이 없으면, 받는 사람은 그게 계통 하나인지 천 건인지 모른다."""
    msg = format_alert_message([_alert()])
    assert "85.0점" in msg
    assert "관측값 1" in msg


def test_evidence_is_capped_so_the_message_stays_readable():
    """근거를 다 싣는 게 목적이 아니다 — 여러 건이 한 번에 오면 화면을 덮는다.
    앞 2줄이 관측값과 원시 이상도다(alerts.py 가 그 순서로 쌓는다)."""
    msg = format_alert_message([_alert()])
    assert EVIDENCE_LINES == 2
    assert "계층 가중치" not in msg          # 뒤쪽 설명은 폰에서 생략
    assert msg.count("   · ") == 2


def test_an_alert_without_evidence_still_sends():
    """근거가 없다고 경보를 막으면 안 된다 — 알리는 게 먼저다."""
    msg = format_alert_message([_alert(evidence=[])])
    assert "85.0점" in msg


# ── 경보가 '도착하는 것' 자체를 지킨다 ─────────────────────────
def test_angle_brackets_in_data_do_not_break_the_send():
    """★핵심★ parse_mode=HTML 이라 데이터에 < 나 & 가 섞이면 400 이 나고
    **경보가 통째로 안 간다.** 설명불가 경보의 label 은 LLM 이 뽑은 문장이고
    근거에는 '원문 발췌'가 들어간다 — 남의 문장이 그대로 오는 자리다."""
    msg = format_alert_message([_alert(
        label="설명불가 신호 · <unknown> & 지역미상",
        evidence=["원문 발췌: fever <5 cases> & cough"])])
    assert "&lt;unknown&gt;" in msg
    assert "&amp;" in msg
    assert "<unknown>" not in msg


def test_our_own_tags_are_not_escaped():
    """이스케이프가 템플릿까지 먹으면 굵은 글씨가 깨진다 — 값만 거른다."""
    assert "<b>" in format_alert_message([_alert()])


# ── 섹션 정직성 고지 ───────────────────────────────────────────
def _brief(section: dict) -> dict:
    return {"headline": "테스트", "summary": None, "segments": [],
            "special_sections": [section]}


def test_forecast_numbers_carry_the_extrapolation_note():
    """★핵심★ '14일 후 6,200명'은 예보다. 고지가 빠지면 사람 수를 센 것처럼
    읽힌다 — 이 제품에서 가장 비싼 오독이다."""
    honesty = "측정된 발병 수가 아니라 신호 시계열의 외삽이며, 적중률 트랙레코드가 쌓이는 중입니다."
    lines = _special_lines(_brief({
        "id": "forecast", "icon": "🔮", "title": "예보", "lead": "7일 후 위험도 60.",
        "honesty": honesty,
        "rows": [{"label": "지표", "counts_people": True, "current": 4885.5, "in_14d": 6200.4}],
    }))
    text = "\n".join(lines)
    assert "4,886명" in text          # 사람은 쪼갤 수 없다(기존 계약)
    assert honesty in text


def test_every_section_kind_passes_its_honesty_through():
    """예보만이 아니다 — 침묵·극지·설명불가 섹션도 각자 고지를 들고 있다."""
    for sec_id in ("silence", "polar", "unexplained"):
        lines = _special_lines(_brief({
            "id": sec_id, "icon": "•", "title": "제목", "lead": "리드",
            "honesty": f"{sec_id} 고지", "rows": [],
        }))
        assert f"{sec_id} 고지" in "\n".join(lines)


def test_honesty_alone_does_not_conjure_a_section():
    """내용이 없는 섹션은 원래 안 나간다. 고지만 붙여 빈 섹션을 만들지 않는다."""
    assert _special_lines(_brief({
        "id": "forecast", "icon": "🔮", "title": "예보",
        "honesty": "고지", "rows": [],
    })) == []


def test_the_global_disclaimer_is_still_there():
    """섹션별 고지가 생겼다고 전체 고지를 떼지 않는다 — 둘은 다른 말을 한다."""
    msg = format_daily_brief_message(_brief({
        "id": "forecast", "icon": "🔮", "title": "예보", "lead": "리드",
        "honesty": "외삽입니다", "rows": [],
    }))
    assert "공식 경보 아님" in msg
    assert "외삽입니다" in msg

"""품질 불변식 — 소스 헬스가 구조적으로 못 보는 층 (2026-08-30).

## 왜
2026-08 한 달의 조용한 실패 6건이 **전부 소스 헬스를 통과하면서** 일어났다.
대표가 8/28·8/30 이다 — `local_news` 는 정상적으로 값을 돌려주는데, 그 값이 LLM
재분류를 거친 게 아니라 오탐 많은 키워드 매칭 결과였다. 소스 헬스는 "값이 왔는가"만
보므로 이걸 볼 방법이 없다.

    소스 헬스 = 값이 왔는가              (liveness)
    품질 헬스 = 그 값을 만든 방식이 온전한가  (integrity)

## 이 파일이 고정하는 것
1. 단발 위반은 안 울린다(외부 API 순간 장애는 흔하다) — 지속될 때 울린다
2. ★ 판정 불가를 정상으로 세지 않는다 ★ — '모른다'와 '괜찮다'는 다르다
3. 판정 불가가 연속 카운터를 리셋하지 않는다 — 리셋되면 경보가 영영 안 뜬다
4. 8/30 사고(키워드 폴백)를 실제로 잡는다
5. 검사기 자체가 터져도 거짓 경보를 만들지 않는다
"""
from __future__ import annotations

import pytest

from algorithms import quality_health as qh


# 상태 파일 격리는 conftest 의 `_isolated_quality_state`(autouse)가 한다 —
# 이 층은 "연속 몇 주기"를 파일에 누적하는 게 핵심이라 오염되면 순서 의존이 생긴다.


def _result(basis="llm", answered=60, sent=60, fetched=5,
            active=179, total=179, provider="Groq(x)"):
    return {
        "local_news": {
            "high_alert_basis": basis,
            "llm_answered_titles": answered,
            "llm_sent_titles": sent,
            "active_feeds": active,
            "total_feeds": total,
            "llm_provider": provider,
        },
        "disaster_watch": {"fetched": fetched},
    }


def _streak(key: str) -> int:
    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == key)
    return entry["consecutive_violations"]


def _alarming(key: str) -> bool:
    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == key)
    return entry["alarming"]


# ── ★핵심★ 8/30 사고를 실제로 잡는가 ────────────────────────────────

def test_keyword_fallback_alarms_after_a_streak():
    """★이 모듈이 존재하는 이유★ 고경보가 키워드 기준으로 떨어진 게 이어지면 울린다.

    8/30 실측: 24주기 중 14주기가 키워드 기준이었고 18~23시는 6주기 연속이었다.
    그동안 소스 헬스는 내내 `정상 20/21` 이었다.
    """
    for _ in range(2):
        qh.record_cycle(_result(basis="keyword"))
    assert not _alarming("llm_reclassify"), "단발·2회는 아직 안 울린다(순간 장애가 흔하다)"

    qh.record_cycle(_result(basis="keyword"))
    assert _alarming("llm_reclassify"), "3주기 연속이면 울려야 한다"

    pending = qh.pending_notifications()
    assert any(d["key"] == "llm_reclassify" for d in pending["degraded"])
    # 경보에 '왜 중요한가'가 함께 와야 사람이 판단할 수 있다.
    reason = next(d for d in pending["degraded"] if d["key"] == "llm_reclassify")
    assert "오탐" in reason["why"]


def test_recovery_resets_the_streak_and_reports_recovered():
    for _ in range(3):
        qh.record_cycle(_result(basis="keyword"))
    qh.mark_notified(["llm_reclassify"])

    qh.record_cycle(_result(basis="llm"))
    assert _streak("llm_reclassify") == 0
    assert "LLM 재분류" in qh.pending_notifications()["recovered"]


# ── ★가장 위험한 쪽★ 모른다를 괜찮다로 세지 않는다 ──────────────────

def test_unknown_is_not_counted_as_healthy():
    """'모른다'와 '괜찮다'는 다르다.

    이 구분이 없으면 그 층이 아예 안 도는 주기에 `정상 5/5` 가 찍혀서, 층이
    사라진 것을 정상으로 읽게 된다 — 이 시스템 최악의 실패 방식이다.
    """
    qh.record_cycle({})                       # local_news·disaster_watch 없음
    report = qh.quality_report()

    assert report["healthy_count"] == 0, "판정 불가를 정상으로 세면 안 된다"
    assert report["unknown_count"] == report["total_invariants"]
    assert "판정불가" in qh.summary_line()


def test_unknown_does_not_reset_an_existing_streak():
    """★놓치기 쉬운 함정★ 판정 불가가 회복으로 오인되면 경보가 영영 안 뜬다.

    층이 격주기로 안 돌면 위반→불가→위반→불가가 되고, 불가에서 리셋되면
    연속 카운터가 절대 문턱에 도달하지 못한다.
    """
    for _ in range(2):
        qh.record_cycle(_result(basis="keyword"))
    assert _streak("llm_reclassify") == 2

    qh.record_cycle({})                       # 판정 불가 주기
    assert _streak("llm_reclassify") == 2, "판정 불가는 카운터를 건드리지 않는다"

    qh.record_cycle(_result(basis="keyword"))
    assert _alarming("llm_reclassify"), "이어서 위반하면 울려야 한다"


# ── 나머지 불변식 ───────────────────────────────────────────────────

def test_truncated_llm_coverage_is_tracked():
    """잘려서 절반만 분류되는 게 이어지면 보인다 — 부분 성공을 성공으로만 세지 않는다."""
    for _ in range(qh.INVARIANTS[1].alarm_after):
        qh.record_cycle(_result(answered=29, sent=60))
    assert _alarming("llm_coverage")


def test_disaster_watch_zero_fetch_alarms():
    """GDACS 0건은 '재난 없음'이 아니라 파서가 형식과 안 맞는 것이다."""
    for _ in range(3):
        qh.record_cycle(_result(fetched=0))
    assert _alarming("disaster_watch")


def test_mass_feed_failure_alarms_while_source_health_would_not():
    """179개 중 절반이 죽어도 active_feeds가 0이 아니면 소스 헬스는 정상으로 본다."""
    for _ in range(3):
        qh.record_cycle(_result(active=80, total=179))
    assert _alarming("local_feeds")


def test_missing_llm_provider_alarms():
    """Cerebras 402 이후 Groq 단일 의존 — 그 하나가 빠지면 보여야 한다."""
    for _ in range(3):
        qh.record_cycle(_result(provider=None))
    assert _alarming("llm_provider")


# ── 검사기가 터져도 거짓 경보를 만들지 않는다 ────────────────────────

def test_a_crashing_check_is_unknown_not_a_violation(monkeypatch):
    """검사기의 버그로 진짜 경보를 만들어내면 경보 전체를 못 믿게 된다."""
    def boom(_result):
        raise RuntimeError("검사기 버그")

    monkeypatch.setattr(qh.INVARIANTS[0], "check", boom)
    for _ in range(5):
        qh.record_cycle(_result())

    assert _streak("llm_reclassify") == 0
    assert not _alarming("llm_reclassify")


def test_healthy_cycle_reports_clean_summary():
    qh.record_cycle(_result())
    line = qh.summary_line()
    assert line.startswith("🔎 품질 불변식: 정상")
    assert "판정불가" not in line

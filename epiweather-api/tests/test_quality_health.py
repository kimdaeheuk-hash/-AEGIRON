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
6. ★2026-09-06 추가★ 하루 1회 도는 추출층도 이 그물에 걸린다 — 09-02~09-05
   나흘 내리 0건이었는데 소스 건강 `23/23`·품질 `5/5` 를 둘 다 통과했다.
   주기 수가 경과를 대신 말하지 않게, 진짜 시각과 실패 경로를 같이 싣는다.
"""
from __future__ import annotations

import datetime as dt

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


def _brief(method="llm_polished", sections=None, polish=None, alerts=None):
    """generate_daily_brief() 가 돌려주는 모양 중 이 층이 보는 칸만."""
    out = {"generation_method": method, "llm_available": True}
    if sections:
        out["special_section_errors"] = [{"section": s, "error": "X"} for s in sections]
    if polish:
        out["polish_error"] = polish
    if alerts:
        out["alerts_error"] = alerts
    return out


def _briefs(method="llm_polished", **kw):
    """세 언어 한 벌 — SUPPORTED_LANGS 를 따라간다(하드코딩하면 언어가 늘 때
    이 테스트가 조용히 한 언어를 안 보게 된다. 08-23 의 fr 사고가 그 모양이었다)."""
    from algorithms.daily_brief import SUPPORTED_LANGS
    return {lang: _brief(method, **kw) for lang in SUPPORTED_LANGS}


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
    # 추출층·브리핑은 하루 1회 슬롯이 남긴 상태를 보므로, '온전한 주기'를 만들려면
    # 그 성공도 같이 있어야 한다 — 이게 없으면 판정불가가 뜨는 게 정상이다.
    qh.record_extraction_outcome(_extraction(saved=3))
    qh.record_brief_outcome(_briefs())
    qh.record_cycle(_result())
    line = qh.summary_line()
    assert line.startswith("🔎 품질 불변식: 정상")
    assert "판정불가" not in line


def test_summary_line_does_not_double_the_word_normal():
    """`🔎 품질 불변식: 정상 정상 6/6` 이 09-19 점검까지 그대로 찍혔다.

    09-15 에 두 갈래가 같은 셈법(_healthy_tail)을 쓰게 묶으면서 접두어가 겹쳤고,
    기존 테스트가 `startswith(... "정상")` 이라 중복을 통과시켰다. 사고는 아니지만
    로그를 읽는 사람이 '정상'을 두 번 읽는다 — 값을 말하는 줄은 한 번만 말해야 한다.
    """
    qh.record_extraction_outcome(_extraction(saved=3))
    qh.record_brief_outcome(_briefs())
    qh.record_cycle(_result())
    line = qh.summary_line()
    assert "정상 정상" not in line
    assert line == f"🔎 품질 불변식: 정상 {len(qh.INVARIANTS)}/{len(qh.INVARIANTS)}"


# ── ★2026-09-06★ 추출층 — 나흘을 두 그물이 다 놓쳤던 자리 ─────────────
#
# 09-02~09-05 NLP 구조화 추출이 내리 0건이었는데 소스 건강은 `정상 23/23`,
# 품질 불변식은 `정상 5/5` 였다. 다섯 불변식이 전부 local_news·disaster_watch 만
# 봐서 추출층은 아무도 안 보는 자리였다.


def _extraction(saved=0, failed=0, blocked=0, reasons=None):
    """extract_from_global_watch_detailed() 의 반환 모양."""
    return {
        "records": [{"id": i} for i in range(saved)],
        "failed": failed,
        "blocked": blocked,
        "failure_reasons": reasons or {},
    }


def _age_state(**fields):
    """상태 파일을 직접 늙힌다 — 48시간을 실제로 기다릴 수는 없다."""
    data = qh._load_raw()
    data[qh.EXTRACTION_STATE_KEY] = {**(data.get(qh.EXTRACTION_STATE_KEY) or {}), **fields}
    qh._save_raw(data)


def _hours_ago(hours: float) -> str:
    return (qh._now() - dt.timedelta(hours=hours)).isoformat()


def test_extraction_failing_for_two_days_alarms():
    """★이 불변식이 존재하는 이유★ 09-05 의 모양을 실제로 잡는가.

    실측: `0건 저장 · 추출실패 5 · 경로별: nvidia_nim_hosted: HTTPError 410×5 ·
    external_llm_fallback: BadRequestError 400×5`. 양쪽 경로가 다 죽었는데
    소스 건강도 품질 불변식도 조용했다.
    """
    reasons = {"nvidia_nim_hosted: HTTPError 410": 5,
               "external_llm_fallback: BadRequestError 400": 5}
    qh.record_extraction_outcome(_extraction(saved=0, failed=5, reasons=reasons))
    _age_state(first_attempt_at=_hours_ago(96), last_attempt_at=_hours_ago(1))

    for _ in range(2):
        qh.record_cycle(_result())
    assert not _alarming("extraction"), "단발·2회는 아직 안 울린다"

    qh.record_cycle(_result())
    assert _alarming("extraction"), "이어지면 울려야 한다"

    # 경보에 '왜'가 따라와야 사람이 판단할 수 있다.
    reason = next(d for d in qh.pending_notifications()["degraded"]
                  if d["key"] == "extraction")
    assert "설명불가" in reason["why"], "같이 멎는 층까지 알려줘야 한다"


def test_extraction_failure_reasons_survive_into_the_report():
    """'몇 번' 뒤에 '왜'. #27 이 살려낸 경로별 사유를 여기서 다시 버리지 않는다."""
    reasons = {"nvidia_nim_hosted: HTTPError 410": 5}
    qh.record_extraction_outcome(_extraction(saved=0, failed=5, reasons=reasons))

    detail = qh.quality_report()["extraction"]
    assert detail["last_failure_reasons"] == reasons
    assert detail["last_outcome"] == "failed"
    assert detail["last_success_at"] is None


def test_report_carries_real_elapsed_time_not_just_cycle_count():
    """★숫자가 사고를 작아 보이게 하면 안 된다★

    연속 위반은 **무료 주기** 수라, 하루 1회 도는 이 층에서는 나흘째 죽은 것도
    문턱 직후엔 '3주기째'다. 진짜 경과는 따로 실려야 한다.
    """
    qh.record_extraction_outcome(_extraction(saved=1))
    _age_state(last_success_at=_hours_ago(96))
    qh.record_cycle(_result())

    detail = qh.quality_report()["extraction"]
    assert detail["success_age_hours"] >= 95, "며칠째인지가 보여야 한다"
    assert _streak("extraction") == 1, "주기 수는 주기 수일 뿐이다"


def test_slot_that_stops_running_entirely_is_a_violation():
    """★가장 놓치기 쉬운 쪽★ 사고 ②의 모양 — 슬롯 자체가 안 돈다.

    값이 안 오는 걸 판정불가로 빼면 '안 도는 층'은 영영 안 울린다. Mobility
    190시간과 GroqWatch 간헐이 정확히 그 함정이었다.
    """
    qh.record_extraction_outcome(_extraction(saved=3))
    _age_state(last_success_at=_hours_ago(72), last_attempt_at=_hours_ago(72))

    for _ in range(3):
        qh.record_cycle(_result())
    assert _alarming("extraction")


def test_a_day_with_nothing_to_extract_is_not_a_failure():
    """중복만 있던 날은 고장이 아니다.

    #30 의 'TED 열림 0건' 이 이 모양이었다 — '진짜 없었다'와 '와 있는데 다
    버렸다'가 한 값에 뭉개져 있었다. 여기서 되풀이하지 않는다.
    """
    qh.record_extraction_outcome(_extraction(saved=2))
    ok_at = qh.quality_report()["extraction"]["last_success_at"]

    qh.record_extraction_outcome({"records": [], "failed": 0, "skipped_duplicate": 7})
    detail = qh.quality_report()["extraction"]

    assert detail["last_outcome"] == "no_attempt"
    assert detail["last_success_at"] == ok_at, "성공 시각을 뒤로 밀면 안 된다"

    qh.record_cycle(_result())
    assert not _alarming("extraction")


def test_missing_backend_is_unknown_not_a_violation():
    """안 돌린 것과 돌렸는데 실패한 것은 다르다(capability_ledger 와 같은 구분).

    키가 없는 환경에서 위반으로 세면 영영 울리고, 정상으로 세면 층이 통째로
    빠진 걸 정상으로 읽는다. 숨지도 않는다 — 판정불가로 숫자에 남는다.
    """
    qh.record_extraction_outcome(None, available=False)
    qh.record_cycle(_result())

    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == "extraction")
    assert entry["last_result"] == "unknown"
    assert not entry["alarming"]
    assert "판정불가" in qh.summary_line()


def test_never_run_layer_is_unknown_then_judged_after_the_grace_window():
    """한 번도 성공 못 한 층을 정상으로 세지 않되, 첫 실패로 바로 울리지도 않는다."""
    qh.record_extraction_outcome(_extraction(saved=0, failed=2))
    qh.record_cycle(_result())
    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == "extraction")
    assert entry["last_result"] == "unknown", "배포 직후 한 번 실패로 울리면 거짓 경보다"

    _age_state(first_attempt_at=_hours_ago(qh.EXTRACTION_STALE_HOURS + 1))
    for _ in range(3):
        qh.record_cycle(_result())
    assert _alarming("extraction"), "유예가 지나면 판정해야 한다"


def test_alarm_carries_the_real_cause_not_just_a_cycle_count():
    """★경보 한 줄만 보고도 손댈 곳을 알아야 한다★

    '3주기째/0시간'만 찍히면 나흘째 죽은 층이 방금 생긴 일로 읽힌다. 실패 경로가
    같이 와야 NIM 을 볼지 폴백을 볼지가 그 자리에서 갈린다.
    """
    reasons = {"nvidia_nim_hosted: HTTPError 410": 5,
               "external_llm_fallback: BadRequestError 400": 5}
    qh.record_extraction_outcome(_extraction(saved=0, failed=5, reasons=reasons))
    _age_state(first_attempt_at=_hours_ago(96))
    for _ in range(3):
        qh.record_cycle(_result())

    line = qh.summary_line()
    assert "HTTPError 410" in line and "BadRequestError 400" in line, (
        "양쪽 경로가 다 죽었다는 사실이 경보 줄에 있어야 한다"
    )
    detail = next(d for d in qh.pending_notifications()["degraded"]
                  if d["key"] == "extraction")["detail"]
    assert "HTTPError 410" in detail


def test_a_broken_detail_never_costs_us_the_report(monkeypatch):
    """부가 정보 하나 때문에 상태 응답을 잃는 건 남는 장사가 아니다."""
    def boom():
        raise RuntimeError("detail 버그")

    inv = next(i for i in qh.INVARIANTS if i.key == "extraction")
    monkeypatch.setattr(inv, "detail", boom)
    qh.record_extraction_outcome(_extraction(saved=2))
    qh.record_cycle(_result())

    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == "extraction")
    assert entry["detail"] is None
    assert entry["last_result"] == "ok"


def test_recovery_clears_the_extraction_alarm():
    qh.record_extraction_outcome(_extraction(saved=0, failed=5))
    _age_state(first_attempt_at=_hours_ago(96))
    for _ in range(3):
        qh.record_cycle(_result())
    qh.mark_notified(["extraction"])
    assert _alarming("extraction")

    qh.record_extraction_outcome(_extraction(saved=4))
    qh.record_cycle(_result())
    assert _streak("extraction") == 0
    assert "구조화 추출" in qh.pending_notifications()["recovered"]


# ── 저하 중에도 나머지 층의 상태를 말한다 (2026-09-15) ────────────
#
# ★ 이 층을 만든 이유가 저하 중에는 작동하지 않았다 ★
#
# 요약 줄은 두 갈래였고 배타적이었다: 위반이 하나라도 있으면 `정상 n/6` 줄이
# **아예 안 찍혔다.** 그래서 09-13·09-15 아침 점검이 이렇게 끝났다:
#
#   "구조화 추출 하나가 위반인 건 알겠는데, 나머지 다섯 중 판정불가가 있는지는
#    로그로는 알 수 없다."
#
# 이 층의 제1원칙이 "판정 불가를 정상으로 세지 않는다"인데, 정작 위반이 있을 때
# — 즉 다른 층이 조용히 사라졌는지가 가장 중요할 때 — 그 숫자가 보이지 않았다.


def test_degraded_line_still_reports_the_other_invariants():
    """★핵심★ 위반 줄만 찍고 나머지를 안 말하면, 그 사이 다른 층이 사라져도
    모른다. 저하 중이야말로 그게 중요하다."""
    qh.record_extraction_outcome(_extraction(saved=0, failed=5))
    _age_state(first_attempt_at=_hours_ago(96))
    for _ in range(3):
        qh.record_cycle(_result())

    line = qh.summary_line()
    assert line.startswith("⚠️ 품질 저하:")
    report = qh.quality_report()
    assert f"정상 {report['healthy_count']}/{report['total_invariants']}" in line


def test_unknown_count_is_visible_while_degraded_too():
    """'모른다'와 '괜찮다'의 구분은 저하 중에도 살아 있어야 한다."""
    qh.record_extraction_outcome(_extraction(saved=0, failed=5))
    _age_state(first_attempt_at=_hours_ago(96))
    for _ in range(3):
        qh.record_cycle({})            # 나머지 층은 이 주기에 안 돌았다

    report = qh.quality_report()
    assert report["unknown_count"] > 0, "전제: 판정불가가 있는 상황"
    line = qh.summary_line()
    assert line.startswith("⚠️ 품질 저하:")
    assert f"판정불가 {report['unknown_count']}" in line


def test_both_branches_use_the_same_arithmetic():
    """두 갈래가 각자 세면 언젠가 어긋난다 — 한 곳에서 만든다."""
    qh.record_cycle(_result())
    report = qh.quality_report()
    assert qh._healthy_tail(report) in qh.summary_line()


# ── ★2026-09-20★ 일곱 번째 불변식: 일일 브리핑 ────────────────────────
#
# 브리핑은 여섯 그물 어디에도 없었다 — 소스 헬스 23개에도, 품질 불변식 여섯에도.
# `llm_provider` 불변식은 local_news 재분류 제공자(Groq)만 보고, Anthropic 층은
# 아무도 안 봤다.
#
# 그 결과가 09-18 이다: 크레딧이 말라 대본이 LLM 을 못 거치는데도 아카이브에는
# 3개 언어가 그대로 쌓였고, 로그·/api/status 에 한 줄도 안 남았다. 09-15 점검은
# 그 침묵을 "매일 3개 언어 성공한다"로 읽고 **모델 ID 를 고쳤다** — 틀린 곳이었다.
#
# 이 절이 고정하는 것은 "값이 나왔다"와 "그 값을 만든 방식이 온전하다"의 구분이
# 브리핑에도 적용된다는 것이다.


def _age_brief_state(**fields):
    data = qh._load_raw()
    data[qh.BRIEF_STATE_KEY] = {**(data.get(qh.BRIEF_STATE_KEY) or {}), **fields}
    qh._save_raw(data)


def test_template_fallback_brief_is_not_counted_as_success():
    """★이 불변식이 존재하는 이유★ 09-18 의 모양을 실제로 잡는가.

    3개 언어가 다 생성되고 아카이브에 쌓이는데 대본은 LLM 을 못 거친 상태.
    값은 나오므로 예전 그물 여섯은 전부 통과한다.
    """
    qh.record_brief_outcome(_briefs(method="template_fallback",
                                    polish="BadRequestError 400: credit balance is too low"))
    _age_brief_state(first_attempt_at=_hours_ago(96), last_attempt_at=_hours_ago(1))
    for _ in range(3):
        qh.record_cycle(_result())

    assert _alarming("daily_brief")
    line = qh.summary_line()
    assert "일일 브리핑" in line
    # ★ 사유가 경보에 실려야 그날 조치가 된다 ★ 크레딧은 코드로 못 고친다 —
    # 캡틴만 고칠 수 있고, 그러려면 경보가 이유를 말해야 한다.
    assert "credit balance is too low" in line
    assert "템플릿 방송" in line


def test_intact_brief_clears_the_invariant():
    qh.record_brief_outcome(_briefs())
    for _ in range(3):
        qh.record_cycle(_result())
    assert not _alarming("daily_brief")
    assert _streak("daily_brief") == 0


def test_missing_api_key_is_unknown_not_a_violation():
    """키가 없으면 template_fallback 은 설계대로 동작한 것이다.

    이걸 실패로 세면 캡틴이 키를 안 넣은 운영 선택이 매일 고장으로 울린다 —
    capability_ledger 의 not_configured / observed_failure 와 같은 갈림이다.
    """
    qh.record_brief_outcome({}, available=False)
    _age_brief_state(first_attempt_at=_hours_ago(96))
    for _ in range(5):
        qh.record_cycle(_result())

    assert not _alarming("daily_brief")
    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == "daily_brief")
    assert entry["last_result"] == "unknown"


def test_one_language_falling_back_is_enough_to_alarm():
    """08-23 의 fr 사고가 '한 언어만 조용히 비는' 모양이었다. 한 벌 전체가
    온전해야 온전한 것으로 센다 — ko 가 멀쩡하다고 넘어가면 같은 일이 반복된다."""
    briefs = _briefs()
    briefs["fr"] = _brief(method="template_fallback")
    qh.record_brief_outcome(briefs)
    _age_brief_state(first_attempt_at=_hours_ago(96), last_attempt_at=_hours_ago(1))
    for _ in range(3):
        qh.record_cycle(_result())

    assert _alarming("daily_brief")
    assert "fr" in qh.summary_line()


def test_special_section_errors_alarm_even_when_llm_polished():
    """대본이 LLM 을 거쳤어도 특수 섹션이 비면 08-26(7일 연속 같은 헤드라인)의
    모양으로 되돌아간다. 두 조건은 AND 다."""
    qh.record_brief_outcome(_briefs(sections=["polar_signals"]))
    _age_brief_state(first_attempt_at=_hours_ago(96), last_attempt_at=_hours_ago(1))
    for _ in range(3):
        qh.record_cycle(_result())

    assert _alarming("daily_brief")
    assert "polar_signals" in qh.summary_line()


def test_alerts_engine_failure_reaches_the_invariant():
    """경보 조회가 죽어 alerts=[] 로 나간 브리핑은 '조용한 날'과 같아 보였다."""
    qh.record_brief_outcome(_briefs(alerts="RuntimeError: db locked"))
    _age_brief_state(first_attempt_at=_hours_ago(96), last_attempt_at=_hours_ago(1))
    for _ in range(3):
        qh.record_cycle(_result())

    assert _alarming("daily_brief")
    assert "경보 조회 실패" in qh.summary_line()


def test_brief_slot_not_running_at_all_alarms():
    """★ 08-22 사고 ②의 모양 ★ 슬롯 자체가 안 도는 것을 판정불가로 빼면
    '안 도는 층'이 영영 안 울린다. 마지막 성공을 늙히면 위반이 돼야 한다."""
    qh.record_brief_outcome(_briefs())
    _age_brief_state(last_success_at=_hours_ago(96))
    for _ in range(3):
        qh.record_cycle(_result())

    assert _alarming("daily_brief")


def test_first_failure_right_after_deploy_defers_judgment():
    """빈 볼륨에 첫 실패 하나로 울리면 거짓 경보가 된다 — 판정을 미룬다."""
    qh.record_brief_outcome(_briefs(method="template_fallback"))
    for _ in range(5):
        qh.record_cycle(_result())

    assert not _alarming("daily_brief")
    entry = next(i for i in qh.quality_report()["invariants"] if i["key"] == "daily_brief")
    assert entry["last_result"] == "unknown"


def test_status_carries_brief_methods_per_language():
    """/api/status 에서 언어별 generation_method 가 바로 읽혀야 한다 — 09-18 에
    "브라우저로 /api/daily-brief 를 열어 확인하라"고 적어둬야 했던 값이다."""
    briefs = _briefs()
    briefs["en"] = _brief(method="template_fallback")
    qh.record_brief_outcome(briefs)
    brief = qh.quality_report()["brief"]
    assert brief["last_methods"]["ko"] == "llm_polished"
    assert brief["last_methods"]["en"] == "template_fallback"
    assert brief["success_age_hours"] is None      # 온전한 적이 없다

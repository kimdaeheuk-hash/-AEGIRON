"""고위험 병원체 제목 조회 — '0건으로 성공한 주기' 가 16일 동안 조용했다 (2026-11-16).

## 관측 (Railway 로그 · 11-16 아침 점검)

보존된 로그 전 구간(11-08 00:00 ~ 11-15 23:01)에서 **0 이 아닌 주기가 하나도 없다**:

    📰 고위험 병원체 보도: 제목 0건 조회 → 후보 0개      ← 매 주기, 예외 없이

10월 점검보고의 같은 층은 `제목 20건 조회 → 후보 1개` 였다. 그리고 **Google 이 막힌
것이 아니다** — 같은 22:00·23:00 주기에 NewsWatch 가
`NewsWatch[google_news+groq(...)] · 제목 20/21개` 로 Google News RSS 에서 정상으로 받았다.

## 왜 아무도 몰랐나

두 겹이었다.

1. **'0건으로 성공'이 '사건 없음'으로 세어졌다.** 이 층의 정직성 규칙은
   *"조회 실패는 '없다'가 아니라 '모른다'"* 인데 그 규칙이 **예외만** 덮었다.
   `_fetch_google()` 은 `status == "error"` 일 때만 올리므로 HTTP 200 에 항목이
   0개면 조용히 빈 목록이 돌아온다.
2. **이 층은 어느 그물에도 없었다.** 소스 건강 25개에도, 품질 불변식 6개에도 없다.
   소킹 일지는 그 기간을 `medium 0` — '오탐 수리가 들은 조용한 날' 로 읽었다.
   일지가 센 것은 **후보 수**였고 **제목 수는 아무도 세지 않았다**:

       후보 0건 = 들어온 제목을 걸러냈다       (층은 살아 있다)
       제목 0건 = 걸러낼 거리가 안 들어왔다    (층이 눈을 감았다)

## 고친 모양 — 단발 0건은 판정, 이어지는 0건은 '모름'

0건을 **무조건** 보류하면 조용한 주기에 행이 영영 안 내려간다. 그 성질은 이미
`test_pathogen_sentinel_and_news_digest_2026_10_07.py` 의 대조군이 일부러 못박아 뒀다.
그래서 단발 0건은 판정으로 인정하고, 질의의 `when:1d` 와 같은 길이인
**24시간**을 0건이 이어진 뒤부터 보류하고 일곱 번째 불변식으로 울린다.
`source_health` 의 staleness·추출층 `EXTRACTION_STALE_HOURS` 와 같은 사고방식이다.
"""
import datetime as dt

import pytest

from algorithms import quality_health as qh


GOOGLE_OK, GOOGLE_ZERO, FALLBACK = (5, True), (0, True), (0, False)


def _record(step, *, hours_ago=0.0):
    """한 주기를 기록한다. `hours_ago` 로 과거 주기를 흉내낸다."""
    count, google = step
    if hours_ago:
        real_now = qh._now
        moment = real_now() - dt.timedelta(hours=hours_ago)
        qh._now = lambda: moment
        try:
            return qh.record_sentinel_cycle(count, google=google)
        finally:
            qh._now = real_now
    return qh.record_sentinel_cycle(count, google=google)


# ── 상태 기록: 세 갈래를 뭉개지 않는다 ───────────────────────────────────

def test_titles_arriving_closes_the_zero_run():
    _record(GOOGLE_ZERO, hours_ago=30)
    assert qh.sentinel_zero_hours() is not None
    _record(GOOGLE_OK)
    assert qh.sentinel_zero_hours() is None
    assert qh.sentinel_zero_run_is_stale() is False


def test_the_zero_run_is_measured_from_its_first_cycle_not_the_latest():
    """11-15 의 모양 — 매 주기 0건이면 경과가 쌓여야 한다. 매번 now 로 덮으면 영영 0시간이다."""
    _record(GOOGLE_ZERO, hours_ago=26)
    _record(GOOGLE_ZERO, hours_ago=10)
    _record(GOOGLE_ZERO)
    assert qh.sentinel_zero_hours() == pytest.approx(26, abs=0.5)
    assert qh.sentinel_zero_run_is_stale() is True


def test_a_fallback_cycle_does_not_touch_the_google_zero_run():
    """★ 대체(Tavily·GDELT) 주기의 0건으로 Google 질의의 건강을 판정하면 안 된다 ★

    대체 경로는 관련도 순 상위 일부라 '빠짐없이'를 보장하지 않는다. 또 Google 이
    막힌 기간에 0건 구간이 이어지면 '질의가 망가졌다'와 '구글이 막혔다'가 한
    숫자로 섞인다 — 조치가 전혀 다른 두 사건이다.
    """
    _record(GOOGLE_OK, hours_ago=3)
    _record(FALLBACK, hours_ago=2)
    _record(FALLBACK)
    assert qh.sentinel_zero_hours() is None          # 0건 구간이 열리지 않았다

    _record(GOOGLE_ZERO, hours_ago=30)
    before = qh.sentinel_zero_hours()
    _record(FALLBACK)
    assert qh.sentinel_zero_hours() == pytest.approx(before, abs=0.2)   # 구간이 안 끊긴다


# ── 불변식: 판정 불가를 정상으로 세지 않는다 ─────────────────────────────

def _check():
    return qh._check_headline_sentinel({})


def test_no_record_at_all_is_undetermined_not_healthy():
    """첫 배포·빈 볼륨. '모른다'와 '괜찮다'는 다르다."""
    assert _check() is None


def test_a_short_zero_run_is_undetermined_not_a_violation():
    """배포 직후 한 주기 0건으로 울리면 거짓 경보가 된다 — 추출층의 같은 자리와 같은 판단."""
    _record(GOOGLE_ZERO)
    assert _check() is None
    assert qh.sentinel_zero_run_is_stale() is False


def test_a_zero_run_past_the_threshold_is_a_violation():
    _record(GOOGLE_ZERO, hours_ago=qh.SENTINEL_ZERO_STALE_HOURS + 1)
    assert _check() is False


def test_titles_present_is_healthy():
    _record(GOOGLE_OK)
    assert _check() is True


def test_only_fallback_records_stay_undetermined():
    """대체 주기만 있었으면 Google 질의에 대해 아는 게 없다."""
    _record(FALLBACK)
    assert _check() is None


def test_the_invariant_is_registered_and_surfaces_in_the_summary_line():
    """★ 만들어만 두고 아무도 안 부르면 그물이 아니다 ★"""
    keys = [i.key for i in qh.INVARIANTS]
    assert "headline_sentinel" in keys
    inv = next(i for i in qh.INVARIANTS if i.key == "headline_sentinel")
    assert inv.detail is not None            # 경보에 '몇 시간째'가 실린다

    _record(GOOGLE_ZERO, hours_ago=40)
    for _ in range(inv.alarm_after):
        qh.record_cycle({})
    line = qh.summary_line()
    assert line.startswith("⚠️ 품질 저하:")
    assert "고위험 병원체 제목 조회" in line and "40시간째 제목 0건" in line


def test_the_summary_line_no_longer_says_jeongsang_twice():
    """`정상 정상 6/6` — 2026-09-15 리팩터가 남긴 중복. 11-16 점검 로그에서 발견."""
    _record(GOOGLE_OK)
    qh.record_cycle({})
    line = qh.summary_line()
    assert line.startswith("🔎 품질 불변식: 정상")
    assert "정상 정상" not in line


def test_detail_says_when_titles_were_last_seen():
    _record(GOOGLE_OK, hours_ago=50)
    _record(GOOGLE_ZERO, hours_ago=30)
    detail = qh._sentinel_detail_line()
    assert "30시간째 제목 0건" in detail and "마지막 제목 50시간 전(5건)" in detail


def test_detail_admits_when_no_titles_were_ever_seen():
    """프로덕션의 실제 모양 — 배포 시점에 이미 0건이던 경우."""
    _record(GOOGLE_ZERO, hours_ago=30)
    assert "제목을 받은 기록이 아예 없음" in qh._sentinel_detail_line()


# ── 호출부(alerts): 보류 판정이 공급자·0건 구간에 묶여 있다 ───────────────

def test_alerts_records_every_cycle_and_ties_the_hold_to_both_conditions():
    """배선 확인 — `collect_candidate_alerts` 가 기록을 남기고 둘 중 하나면 붙든다.

    기록을 안 남기면 불변식이 영영 '판정 불가'로 남아 그물이 작동하지 않는다.
    이 리포가 반복해서 데인 '만들어만 두고 아무도 안 부른다' 의 짝이다.
    """
    import ast
    import inspect

    from algorithms import alerts as alerts_mod

    src = inspect.getsource(alerts_mod.collect_candidate_alerts)
    assert "record_sentinel_cycle" in src        # 매 주기 기록한다

    tree = ast.parse(src)
    guarded = [n for n in ast.walk(tree) if isinstance(n, ast.If)
               and any(isinstance(c, ast.Call)
                       and getattr(c.func, "id", "") == "_mark_undetermined"
                       for b in n.body for c in ast.walk(b))
               and "provider" in ast.dump(n.test)]
    assert guarded, "보류가 provider 조건 밖으로 나갔다 — 10-09 에 고정한 성질이다"
    # 그리고 같은 조건에 0건 구간 판정이 함께 들어 있다
    assert any("sentinel_zero_run_is_stale" in ast.dump(n.test) for n in guarded), \
        "0건 구간 판정이 보류 조건에서 빠졌다 — 11-16 에 고친 바로 그 구멍이다"

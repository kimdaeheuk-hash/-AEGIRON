"""수집기가 죽은 것을 '세상이 조용하다'로 읽지 않는다 (2026-09-19).

## 왜 이 파일이 있나

11:03, **critical 경보**가 캡틴 폰으로 나갔다. 같은 사이클 로그:

    [11:01:49] 현지어 뉴스: 0/179개 피드(고유 0묶음), 키워드 히트 0건, 고경보 0개
    [11:03:14] 📊 소스 건강: 정상 22/23 · 값없음 LocalNews
    [11:03:21] 🚨 경보 주기: critical 1건 · high 1건 … · 알림: 전송됨

179개 피드가 전멸했는데 `fetch_all_local_news` 는 **정상 모양의 dict** 를
돌려준다 — `total_kw_hits: 0` 으로. `collector.py:798` 은 이미 그걸 알고
`active_feeds` 가 0 이면 `mark_no_data` 를 찍는다(그래서 소스 건강에 '값없음'이
떴다). 그런데 **지표 추출기가 그 구분을 안 봤다.**

그 0 이 negative_space 로 간다. 과거 평균 1,600건대 대비 latest=0 →
drop_ratio 0.0 → severity 100점 → **critical**. 2014년 기니 에볼라를 잡으라고
만든 층이 **우리 스크레이퍼 장애**에 울린 것이다.

이 리포가 반복해서 고쳐온 모양이다 — naver_trends 의 "그룹 부재 ≠ 검색량 0",
mark_no_data 의 "실패로 세도 성공으로 세도 둘 다 거짓이다".
"""
from __future__ import annotations

import statistics

from algorithms.negative_space import DROP_RATIO, check_negative_space
from algorithms.signal_metrics import LAYERS


def _extractor():
    return next(m[2] for m in LAYERS["informal"]["metrics"]
                if m[0] == "local_news_kw_hits")


# ── ★핵심★ 못 읽은 것과 0건은 다르다 ──────────────────────────
def test_total_feed_failure_is_unknown_not_zero():
    """★이 테스트가 이 파일의 이유다★ 0/179 는 '아무도 그 말을 안 했다'가
    아니라 '우리가 한 곳도 못 읽었다'다. 0 으로 읽으면 부정적 공간 감시가
    보고 체계 붕괴로 판정한다."""
    assert _extractor()({"local_news": {"active_feeds": 0, "total_kw_hits": 0}}) is None


def test_a_real_quiet_cycle_is_still_zero():
    """★핵심★ 반대 방향도 막는다. 피드는 다 읽혔는데 히트가 0 인 것은
    **관측**이다 — 그걸 None 으로 만들면 이번엔 진짜 급감을 못 본다."""
    assert _extractor()({"local_news": {"active_feeds": 179, "total_kw_hits": 0}}) == 0


def test_normal_cycle_passes_through():
    assert _extractor()({"local_news": {"active_feeds": 179, "total_kw_hits": 1668}}) == 1668


def test_missing_block_is_unknown():
    assert _extractor()({"local_news": None}) is None
    assert _extractor()({}) is None


# ── 이 값이 실제로 무엇을 만들었는가 ────────────────────────────
def test_zero_against_a_busy_history_would_have_been_a_collapse_verdict():
    """실제로 무슨 일이 있었는지를 고정한다 — 평소 1,600건대에서 0 이 오면
    부정적 공간 감시는 '보고 체계 붕괴 가능성'으로 판정한다. 그 판정 자체는
    옳다. 틀린 건 **0 이라는 입력**이었다."""
    history_avg = statistics.mean([1668, 1700, 1650, 1620])
    assert check_negative_space(0, history_avg)["alert"] is True
    assert 0 < history_avg * DROP_RATIO        # 기준을 확실히 넘는다


def test_unknown_value_is_skipped_by_the_scan():
    """None 은 판정 대상이 아니다 — 스캔이 '판정 불가'로 비켜간다."""
    assert check_negative_space(None, 1660.0)["alert"] is False

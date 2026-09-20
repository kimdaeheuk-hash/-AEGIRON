"""조각이 빠진 합계는 낮은 값이 아니라 다른 값이다 (2026-09-20).

## 왜 이 파일이 있나

09-19 에 LocalNews 가 이 경로로 critical 경보를 냈다 — 179개 피드가 전멸했는데
`total_kw_hits: 0` 이 그대로 읽혀서, 부정적 공간 감시가 "보고 체계 붕괴"로
판정했다. 무너진 건 세상의 보고가 아니라 **우리 수집기**였다.

런칭 전 출구 감사(②)에서 **같은 모양을 세 군데 더** 찾았다. 전부 여러 곳에서
가져와 더하는 지표다:

    vals = [v for v in totals.values() if v is not None]
    return sum(vals) if vals else None

전부 실패해야 None 이고, **일부만 실패하면 조용히 낮은 숫자**가 된다.

## 제일 위험한 건 일본이었다

11개 질병을 합치는데 독감 하나가 12,299건으로 전체의 90% 가 넘는다.
그 한 줄만 파싱에 실패해도:

    합계 ≈ 13,000 → 700
    drop_ratio 0.054 → severity 94.6 → 🔴 critical

그리고 `fetch_japan_idwr` docstring 이 이미 적어뒀다 — *"유행이 커질수록
데이터가 사라지는 최악의 방향으로 틀린다"*. **진짜 유행이 오는 순간** 거짓
경보가 나가는 구조였다.

## 수집은 그대로 둔다

*"한 도시 실패해도 나머지는 계속 수집"* 은 의도된 설계다. 바꾸는 건 **판정**뿐이다.
"""
from __future__ import annotations

from algorithms.negative_space import check_negative_space
from algorithms.signal_metrics import LAYERS, sum_if_complete


def _metric(metric_id: str):
    return next(m[2] for m in LAYERS["official"]["metrics"] if m[0] == metric_id)


# ── ★핵심★ 일본 — 유행이 클수록 깨지던 자리 ───────────────────
def test_japan_total_is_unknown_when_the_biggest_disease_is_missing():
    """★이 테스트가 이 파일의 이유다★ 독감이 전체의 90% 다. 그 한 줄이 빠진
    합계를 '줄어든 값'으로 읽으면 진짜 유행 때 '보고가 끊겼다'가 된다."""
    jp = _metric("japan_idwr_total")
    full = {"japan_idwr": {"national_totals": {"독감": 12299, "기타": 700}}}
    holed = {"japan_idwr": {"national_totals": {"독감": None, "기타": 700}}}
    assert jp(full) == 12999
    assert jp(holed) is None


def test_the_partial_sum_would_have_been_read_as_a_collapse():
    """무엇이 위험했는지를 숫자로 고정한다 — 예전 동작(700)이 평소 13,000 과
    만나면 부정적 공간 감시가 붕괴로 판정한다. 판정 자체는 옳다. 입력이 틀렸다."""
    verdict = check_negative_space(700, 12999)
    assert verdict["alert"] is True
    assert round((1 - 700 / 12999) * 100, 1) > 90      # critical 등급


# ── 나머지 둘 ──────────────────────────────────────────────────
def test_hong_kong_half_read_is_unknown_not_halved():
    """피드 2개 중 하나가 죽으면 합계가 절반이 된다 — 홍콩이 보고를 줄인 게
    아니라 우리가 절반을 못 읽은 것이다."""
    hk = _metric("hk_chp_total")
    assert hk({"hk_chp": {"a": 10, "b": 10}}) == 20
    assert hk({"hk_chp": {"a": 10, "b": None}}) is None


def test_infodengue_skips_judgement_when_a_city_failed():
    """09-20 01:00 실측 — `InfoDengue(브라질): 상파울루=실패, 리우데자네이루=…`.
    지금은 계절성 제외 목록 덕에 경보로 안 갔지만, 그 보호가 사라지면 바로
    같은 사고가 난다. 지표 쪽에서 막는다."""
    inf = _metric("infodengue_casos_total")
    assert inf({"infodengue": {"상파울루": {"casos": 80}, "리우": {"casos": 120}}}) == 200
    assert inf({"infodengue": {"상파울루": None, "리우": {"casos": 120}}}) is None


# ── 공용 규칙 ──────────────────────────────────────────────────
def test_all_present_still_sums():
    """★핵심★ 조용해지는 게 목적이 아니다. 다 받았으면 그대로 더한다."""
    assert sum_if_complete([1, 2, 3]) == 6
    assert sum_if_complete([0, 0]) == 0          # 진짜 0 은 관측이다


def test_nothing_at_all_is_also_unknown():
    """한 조각도 못 받은 것과 일부만 못 받은 것 — 둘 다 판정 불가다."""
    assert sum_if_complete([]) is None
    assert sum_if_complete([None, None]) is None


def test_the_three_metrics_share_one_helper():
    """같은 실수를 네 번째로 반복하지 않으려고 공용 자리에 뒀다 —
    각자 만들면 각자 흘린다(common.tally 와 같은 이유)."""
    import inspect
    from algorithms import signal_metrics as sm
    for name in ("_japan_idwr_total", "_hk_chp_total", "_infodengue_total"):
        assert "sum_if_complete" in inspect.getsource(getattr(sm, name))

"""경보 최소 절대값 문턱 — 1건이 85점 경보를 내던 것 (2026-09-19).

## 왜 이 파일이 있나

아이기론이 **처음으로 사람에게 보낸 경보**가 이것이었다:

    🟠 비공식신호 · genomic_new_clades_covid — 85.0점

그 85점을 만든 관측값은 **신규 계통 1건**이었다:

    Nextstrain SARS-CoV-2(공개시퀀스): 우세계통 25C (XFG)(50%, n=559) 🆕신규계통1건

85.0 ÷ 0.85(academic 신뢰도) = raw 100 = **z-score 상한**. 평소 0 인 카운트
지표는 과거 표준편차가 작아서 **0→1 이 곧 3σ** 다. 1 만 나와도 최대 이상도다.

산술은 맞다. 틀린 건 그 다음 문장이다 — "그러므로 사람을 깨울 일이다".

## 이 파일이 지키는 경계선

**이상도는 측정값이라 안 건드린다.** 1 이 통계적 이상값인 건 사실이고, 그걸
0 으로 고쳐 쓰면 상태 필드가 관측을 왜곡하는 쪽이 된다. 문턱은 **경보 승격
자리에만** 둔다 — 측정은 그대로, 사람을 깨우는 판단만 명시적으로.
"""
from __future__ import annotations

from unittest.mock import patch

from algorithms import gai
from algorithms.alerts import CANDIDATE_FLOOR, collect_candidate_alerts
from algorithms.signal_metrics import ALERT_MIN_COUNT, meets_alert_minimum


def _gai_with(metric_id: str, latest, trusted: float = 85.0) -> dict:
    return {
        "gai": 10.0,        # 종합은 낮게 — 이 테스트는 개별 지표 승격만 본다
        "layers": {"informal": {
            "label": "비공식신호", "weight": 0.20, "score": trusted,
            "metrics": [{"metric": metric_id, "latest": latest,
                         "raw_score": 100.0, "trust": 0.85, "trusted_score": trusted}],
        }},
        "sample_size": {"free_sources": 100},
    }


def _sources(gai_result: dict) -> list[str]:
    with patch("algorithms.alerts.compute_gai", return_value=gai_result), \
         patch("algorithms.alerts.scan_negative_space", return_value={"alerts": []}), \
         patch("algorithms.alerts.scan_unexplained", return_value={"alerts": []}), \
         patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return [c["source"] for c in collect_candidate_alerts("2026-09-19")]


# ── ★핵심★ 1건은 사람을 깨우지 않는다 ──────────────────────────
def test_one_new_clade_does_not_become_an_alert():
    """★이 테스트가 이 파일의 이유다★ 09-19 05:47 에 실제로 나간 그 경보다.
    85점이어도 관측값이 1건이면 경보로 안 올라간다."""
    assert "gai:informal.genomic_new_clades_covid" not in _sources(
        _gai_with("genomic_new_clades_covid", 1))


def test_two_new_clades_still_alert():
    """★핵심★ 문턱이 신호를 죽이면 안 된다. 2건부터는 그대로 올라간다 —
    조용해지는 게 목적이 아니라 '1건에 최대치'를 막는 게 목적이다."""
    assert "gai:informal.genomic_new_clades_covid" in _sources(
        _gai_with("genomic_new_clades_covid", 2))


def test_metrics_without_a_minimum_are_untouched():
    """이 표는 '막는 목록'이지 '허용 목록'이 아니다. 새 지표가 표에 없다고
    조용히 막히면, 이번엔 반대 방향으로 진짜 신호를 죽인다."""
    assert "gai:informal.naver_covid_ratio" in _sources(
        _gai_with("naver_covid_ratio", 0.5))


def test_unknown_value_does_not_pass_the_minimum():
    """값을 못 본 상태에서 '문턱을 넘었다'고 할 수 없다 — 모르는 것을
    통과로 세지 않는다."""
    assert meets_alert_minimum("genomic_new_clades_covid", None) is False


def test_below_floor_is_still_dropped_by_the_floor():
    """문턱이 CANDIDATE_FLOOR 를 대체하는 게 아니다. 둘 다 통과해야 한다."""
    assert _sources(_gai_with("genomic_new_clades_covid", 5,
                              trusted=CANDIDATE_FLOOR - 1)) == []


# ── 지수는 안 건드린다 ──────────────────────────────────────────
def test_the_index_still_counts_what_it_measured():
    """★핵심★ 경보로 안 올린 것과 이상하지 않았던 것은 다르다. 1건이
    z-상한이었다는 사실 자체는 GAI 에 그대로 남아야 한다 — 측정을 고쳐
    쓰면 그게 이 리포가 금지하는 바로 그 짓이다."""
    result = _gai_with("genomic_new_clades_covid", 1)
    _sources(result)   # 경보 승격을 돌려도
    assert result["layers"]["informal"]["metrics"][0]["trusted_score"] == 85.0


# ── 점수와 문턱이 같은 숫자를 본다 ──────────────────────────────
def test_latest_uses_the_same_rule_as_the_score():
    """★핵심★ _latest_value 와 _anomaly_score 가 서로 다른 원소를 '최신값'으로
    잡으면, 문턱이 점수와 **다른 숫자**를 보고 판단하게 된다. 둘 다 마지막
    non-None 을 쓴다는 걸 고정한다."""
    series = [0.0, None, 0.0, 0.0, None, 3.0]
    assert gai._latest_value(series) == 3.0
    assert gai._anomaly_score(series) is not None      # 같은 계열에서 점수도 난다
    assert gai._latest_value([None, None]) is None
    assert gai._latest_value([]) is None


def test_compute_gai_carries_the_observed_value():
    """지수 출력에 관측값이 실려야 경보 쪽이 그걸 보고 판단할 수 있다."""
    records = [{"type": "free_sources", "naver_covid_ratio": v} for v in (1, 2, 3, 40)]
    with patch("algorithms.gai.load_records", return_value=records):
        out = gai.compute_gai()
    m = next(x for x in out["layers"]["behavioral"]["metrics"]
             if x["metric"] == "naver_covid_ratio")
    assert m["latest"] == 40


# ── 문턱 표 자체 ────────────────────────────────────────────────
def test_the_three_clade_metrics_share_the_minimum():
    """같은 함수(genomic_variants.analyze_build)가 같은 모양으로 만드는
    0 근처 카운트라 셋을 함께 묶었다 — 하나만 고치면 나머지가 남는다."""
    for slug in ("covid", "mpox", "rsv"):
        assert ALERT_MIN_COUNT[f"genomic_new_clades_{slug}"] == 2

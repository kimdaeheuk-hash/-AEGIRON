"""소표본 카운트 유의도 문턱 — 게시자 +2명이 critical 을 만든 것 (2026-10-03).

## 배경

닷새 조용하던 캡틴 폰이 10-03 에 세 번 울렸다. 전부 Mastodon 7일 게시자 수(`social_*`):

    콜레라  3명 ·· 3명(사흘 넘게 평평) → 5명     critical 90.0  (11:03 전송됨)
    뎅기열  9명 → 12명                              high     87.6  (13:02 전송됨)
    그리고 10-04 00:01 — 새 날 표에서 같은 critical 이 다시 나갔다

90.0 = 100 × 0.90 은 원시 이상도가 **상한(z ≥ 3)** 에 닿았다는 역산이다. 경험적 표준편차는
'과거가 얼마나 평평했나'를 재지 카운트의 불확실성을 재지 않는다.

## 이 파일이 지키는 경계선

**이상도(지수)는 측정값이라 안 건드린다.** 문턱은 경보 **승격 자리에서만**, 카운트 기준
유의도 `(관측값 − 평균) / √max(평균, 1)` 로 본다. 대상은 `social_*` 뿐이다 — 같은 함수가 같은
모양으로 만드는 카운트라서(`test_alert_minimum.py` 의 genomic 셋과 같은 이유). 다른 지표는
조용히 막히면 안 된다(막는 목록이지 허용 목록이 아니다).

## 시험이 말하지 못하는 것

이 시험은 **합성 입력**이다. 프로덕션 지표의 실제 과거 평균은 샌드박스에서 못 본다 — 평균이
2 라면 콜레라 5명은 `(5−2)/√2 = 2.12σ` 로 **통과**한다. 그래서 통과·차단 모두 계산값을
로그로 남긴다(`🧮 [alerts] 소표본 유의도`) — 실제 값은 배포 뒤 로그가 말한다.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
from unittest.mock import patch

from algorithms import gai
from algorithms.alerts import collect_candidate_alerts
from algorithms.signal_metrics import (COUNT_MIN_SIGMA, count_significance,
                                       is_count_noise_metric, meets_count_significance)

ALERTS_PY = Path(__file__).resolve().parent.parent / "algorithms" / "alerts.py"


def _gai_with(metric_id: str, latest, baseline_mean, trusted: float = 90.0) -> dict:
    return {
        "gai": 10.0,
        "layers": {"behavioral": {
            "label": "행동신호", "weight": 0.20, "score": trusted,
            "metrics": [{"metric": metric_id, "latest": latest, "baseline_mean": baseline_mean,
                         "raw_score": 100.0, "trust": 0.90, "trusted_score": trusted}],
        }},
        "sample_size": {"free_sources": 100},
    }


def _sources(gai_result: dict) -> list[str]:
    with patch("algorithms.alerts.compute_gai", return_value=gai_result), \
         patch("algorithms.alerts.scan_negative_space", return_value={"alerts": []}), \
         patch("algorithms.alerts.scan_unexplained", return_value={"alerts": []}), \
         patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return [c["source"] for c in collect_candidate_alerts("2026-10-03")]


# ── 산식 ────────────────────────────────────────────────────────────

def test_significance_is_poisson_scaled():
    assert math.isclose(count_significance(5, 3), (5 - 3) / math.sqrt(3))
    assert math.isclose(count_significance(12, 9), (12 - 9) / 3.0)


def test_denominator_floor_avoids_zero_division_and_overreaction():
    """평균 0 근처에서 분모를 1 로 둔다 — 평균 0.1 에서 관측값 1 이 9σ 가 되지 않는다."""
    assert math.isclose(count_significance(1, 0.0), 1.0)
    assert math.isclose(count_significance(1, 0.1), 0.9)


def test_decrease_is_negative_not_promoted():
    assert count_significance(1, 4) < 0


def test_unknown_values_give_none():
    assert count_significance(None, 3) is None
    assert count_significance(5, None) is None


# ── ★핵심★ 10-03 의 모양 ────────────────────────────────────────────

def test_cholera_3_to_5_on_a_flat_history_is_not_promoted():
    """10-03 11:03 의 critical 이다. 평소 3 → 5 는 포아송 잡음 수준(1.15σ)이다."""
    assert "gai:behavioral.social_cholera" not in _sources(
        _gai_with("social_cholera", 5, 3.0))


def test_dengue_9_to_12_is_not_promoted():
    """10-03 13:02 의 high 다. 9 → 12 는 (12−9)/3 = 1.0σ."""
    assert "gai:behavioral.social_dengue" not in _sources(
        _gai_with("social_dengue", 12, 9.0, trusted=87.6))


def test_a_real_surge_still_alerts():
    """★핵심★ 문턱이 신호를 죽이면 안 된다. 평소 3 → 12 는 (12−3)/√3 = 5.2σ 라 그대로 올라간다.
    조용해지는 게 목적이 아니라 '+2명에 최대치'를 막는 게 목적이다."""
    assert "gai:behavioral.social_cholera" in _sources(
        _gai_with("social_cholera", 12, 3.0))


def test_threshold_boundary_is_inclusive():
    """정확히 문턱(2σ)이면 통과한다 — (x − 4)/2 = 2 → x = 8."""
    assert math.isclose(count_significance(8, 4), COUNT_MIN_SIGMA)
    assert meets_count_significance("social_x", 8, 4) is True
    assert meets_count_significance("social_x", 7, 4) is False


def test_when_the_real_mean_is_low_the_same_count_passes():
    """★이 시험은 한계를 고정한다★ 실제 과거 평균이 2 라면 5명은 (5−2)/√2 = 2.12σ 로 통과한다.
    프로덕션의 평균은 샌드박스에서 못 봤다 — 그래서 계산값을 로그로 남긴다."""
    assert "gai:behavioral.social_cholera" in _sources(
        _gai_with("social_cholera", 5, 2.0))


# ── 막는 목록이지 허용 목록이 아니다 ────────────────────────────────────

def test_only_social_metrics_are_covered():
    assert is_count_noise_metric("social_cholera")
    assert is_count_noise_metric("social_mpox")
    assert not is_count_noise_metric("naver_covid_ratio")
    assert not is_count_noise_metric("japan_idwr_total")
    assert not is_count_noise_metric("genomic_new_clades_covid")


def test_other_metrics_are_untouched_even_without_a_mean():
    """대상이 아닌 지표는 평균이 없어도 그대로 통과한다 — 조용히 막으면 반대로 진짜를 놓친다."""
    assert "gai:behavioral.naver_covid_ratio" in _sources(
        _gai_with("naver_covid_ratio", 0.5, None))


def test_unknown_mean_for_a_covered_metric_is_not_promoted():
    """값을 못 본 상태에서 '문턱을 넘었다'고 할 수 없다(meets_alert_minimum 과 같은 방향)."""
    assert meets_count_significance("social_cholera", 5, None) is False
    assert meets_count_significance("social_cholera", None, 3.0) is False


# ── 지수는 안 건드린다 ──────────────────────────────────────────────

def test_the_index_still_counts_what_it_measured():
    """경보로 안 올린 것과 이상하지 않았던 것은 다르다 — 점수는 그대로 남는다."""
    result = _gai_with("social_cholera", 5, 3.0)
    _sources(result)
    m = result["layers"]["behavioral"]["metrics"][0]
    assert m["trusted_score"] == 90.0 and m["raw_score"] == 100.0


def test_baseline_mean_is_exposed_without_changing_scores():
    """compute_gai 가 과거 평균을 내보내되 점수는 이전과 같은 산식에서 나온다."""
    # 실제 레코드 모양: social_signal[태그] = {"available": True, "count_recent": N}
    records = [{"type": "free_sources",
                "social_signal": {"cholera": {"available": True, "count_recent": v}}}
               for v in (2, 3, 4, 3, 3, 3, 5)]
    with patch("algorithms.gai.load_records", return_value=records):
        out = gai.compute_gai()
    # 소셜 지표가 어느 계층에 있든 찾는다 — 계층 키는 이 시험의 대상이 아니다.
    m = next(x for layer in out["layers"].values() for x in layer["metrics"]
             if x["metric"] == "social_cholera")
    history = [2, 3, 4, 3, 3, 3]
    assert math.isclose(m["baseline_mean"], round(sum(history) / len(history), 4))
    assert m["latest"] == 5
    assert m["raw_score"] == gai._anomaly_score([2, 3, 4, 3, 3, 3, 5])


def test_baseline_mean_uses_the_same_history_as_the_score():
    """_baseline_mean 이 _anomaly_score 와 같은 과거(None 제거 · 마지막이 최신값)를 본다."""
    series = [1.0, None, 2.0, 0.0, None, 3.0]
    assert gai._baseline_mean(series) == round((1.0 + 2.0 + 0.0) / 3, 4)
    assert gai._baseline_mean([1.0, 2.0]) is None       # 표본 부족 — 0 으로 쓰지 않는다


# ── 배선 ────────────────────────────────────────────────────────────

def test_promotion_path_actually_uses_the_gate():
    """★ 만들어만 두고 아무도 안 부르는 층 ★ collect_candidate_alerts 가 유의도 문턱을 부르고
    통과·차단 모두 로그로 남기는지 AST 로 고정한다."""
    tree = ast.parse(ALERTS_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "collect_candidate_alerts")
    called = {n.func.id for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "meets_count_significance" in called, "승격 자리가 유의도 문턱을 부르지 않는다"
    assert "count_significance" in called, "계산값을 로그로 남기지 않는다"
    logged = [n for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
              and any(isinstance(a, ast.JoinedStr) and "소표본 유의도" in ast.dump(a) for a in n.args)]
    assert logged, "통과·차단 계산값 로그 줄이 없다"


def test_gate_logs_the_computed_values(capsys):
    """차단·통과 모두 계산값이 로그에 남는다 — 실제 평균이 내일 값으로 읽힌다."""
    _sources(_gai_with("social_cholera", 5, 3.0))
    blocked = capsys.readouterr().out
    assert "소표본 유의도 social_cholera" in blocked and "1.15σ" in blocked
    assert "경보로 안 올림" in blocked

    _sources(_gai_with("social_cholera", 12, 3.0))
    passed = capsys.readouterr().out
    assert "5.20σ" in passed and "통과" in passed

"""일본 IDWR 감시 합계의 경보 점수 상한 79 (2026-10-27, 캡틴 지시 "일본 계절 상한 79로 걸어").

관측: 10-19 17:28 UTC `공식신호 · japan_idwr_total 82.4점(관측값 67357(평소 약 40,534))` high → 폰.
관측값은 실측(IDWR 40주, 독감 포함 11종 합)이지만 이 지수는 전년 동기와 견주지 않아 해마다 오는 가을·겨울
독감 상승이 '평소 대비 급증'으로 읽힌다. 고정하는 것: ① 경보 점수만 79(medium)로 — 폰에 안 간다
② 이유가 폰에 가는 둘째 줄에 있다 ③ 79 이하 점수는 그대로 ④ 다른 공식 지표는 안 건드린다(막는 목록)
⑤ 지수(GAI)는 안 건드린다 — 이 상한은 경보 후보 수집 자리에만 있다.
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import classify_tier, refresh_alerts
from algorithms.signal_metrics import SEASONAL_ALERT_CAP, seasonal_cap_reason

_EMPTY_NS = {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}}


def _gai(metric, latest, mean, raw, trusted, trust=0.95):
    return {"gai": 10.0, "layers": {"official": {
        "label": "공식신호", "weight": 0.3, "score": trusted,
        "metrics": [{"metric": metric, "latest": latest, "baseline_mean": mean,
                     "raw_score": raw, "trust": trust, "trusted_score": trusted}]}}}


def _collect(monkeypatch, gai):
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: gai)
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return alerts_mod.collect_candidate_alerts("2026-10-19", _EMPTY_NS)


def _one(cands, metric):
    return [c for c in cands if c["source"].endswith(metric)][0]


def test_the_1019_high_is_capped_to_medium_with_the_reason_on_the_second_line(monkeypatch):
    # 10-19 입력(관측값·평소·경보 점수는 로그 그대로, 원시 이상도는 82.4/0.95 로 근사)
    c = _one(_collect(monkeypatch, _gai("japan_idwr_total", 67357, 40534.0, 86.7, 82.4)), "japan_idwr_total")
    assert c["score"] == SEASONAL_ALERT_CAP == 79.0
    assert classify_tier(c["score"]) == "medium"            # high 였다
    assert "경보 점수 79.0점으로 제한(계절 감시 합계" in c["evidence"][1]
    assert "관측값 67357" in c["evidence"][0]


def test_scores_at_or_below_the_cap_are_untouched(monkeypatch):
    c = _one(_collect(monkeypatch, _gai("japan_idwr_total", 50000, 40534.0, 75.0, 71.3)), "japan_idwr_total")
    assert c["score"] == 71.3 and "제한" not in c["evidence"][1]


def test_other_official_metrics_are_not_touched(monkeypatch):
    assert seasonal_cap_reason("kdca_weekly_total") is None
    c = _one(_collect(monkeypatch, _gai("kdca_weekly_total", 67357, 40534.0, 86.7, 82.4)), "kdca_weekly_total")
    assert c["score"] == 82.4


def test_the_capped_high_no_longer_reaches_the_phone(isolated_db, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "보낼 신규 경보 없음", "new_critical_high": len(new)}))
    monkeypatch.setattr(alerts_mod, "scan_negative_space", lambda: _EMPTY_NS)
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: _gai("japan_idwr_total", 67357, 40534.0, 86.7, 82.4))
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        refresh_alerts("2026-10-19")
    row = [r for r in db.list_alerts("2026-10-19") if r["source"].endswith("japan_idwr_total")][0]
    assert row["tier"] == "medium" and sent == [[]]


def test_the_index_is_not_capped():
    """상한은 경보 후보 수집 자리에만 있다 — GAI 계산은 이 상수를 모른다."""
    from algorithms import gai
    assert "SEASONAL_ALERT" not in inspect.getsource(gai)
    assert "seasonal_cap_reason(m[\"metric\"])" in inspect.getsource(alerts_mod.collect_candidate_alerts)

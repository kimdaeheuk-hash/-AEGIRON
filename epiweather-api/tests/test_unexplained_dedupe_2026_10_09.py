"""같은 사건이 추출 표현이 바뀔 때마다 폰을 다시 울리던 것 (2026-10-09, 소킹 일지 10-08).

## 관측
이르쿠츠크 사건을 10-07 21:02 추출은 `Irkutsk, Russia`, 10-08 21:04 추출은 `러시아 시베리아`로 뽑았다.
설명불가 경보의 키가 위치 문구 그대로(`unexplained:{위치}`)라 **키가 달라져 새 경보**로 취급됐고 critical 이
이틀 연속 폰으로 나갔다. 사건이 뉴스에 있는 동안 매일 22시에 울릴 수 있는 구조였다.

## 두 겹으로 막는다
1. 키: 위치가 한 나라로 읽히면 그 나라의 ISO3 (`unexplained:RUS`).
2. 이어짐: 어제 알린 등급이 오늘도 이어지는 행은 이월로 조용했던 날에도 기록을 잇는다 — 안 그러면
   1일차 전송 → 2일차 조용(기록 없음) → 3일차 다시 전송으로 '이틀에 한 번' 울린다.
"""
from __future__ import annotations

from unittest.mock import patch

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import refresh_alerts, unexplained_key


def _a(location, raw="질병불명", extracted_at="2026-10-08T21:04:00"):
    return {"source": "unexplained_cluster", "location": location, "raw_disease_text": raw,
            "raw_text": "원문", "extracted_at": extracted_at}


# ── 1. 키 ────────────────────────────────────────────────────

def test_the_two_phrasings_of_the_irkutsk_event_share_one_key():
    assert unexplained_key(_a("Irkutsk, Russia")) == unexplained_key(_a("러시아 시베리아")) == "RUS"


def test_multi_country_or_unreadable_locations_keep_the_old_key():
    assert unexplained_key(_a("콩고민주공화국, 우간다")) == "콩고민주공화국, 우간다"       # 두 나라 — 하나로 뭉치지 않는다
    assert unexplained_key(_a("시베리아")) == "시베리아"                                   # 나라를 못 읽음
    assert unexplained_key(_a(None, raw="원인불명 폐렴")) == "원인불명 폐렴"
    assert unexplained_key({**_a(None, raw=None), "source": "unexplained_cluster"}) == "unexplained_cluster"


def test_collect_uses_the_country_key_for_both_phrasings(monkeypatch):
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: {"gai": 10.0, "layers": {}})
    out = {}
    for tag, loc in (("a", "Irkutsk, Russia"), ("b", "러시아 시베리아")):
        monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda loc=loc: {"alerts": [_a(loc)]})
        with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
            cands = alerts_mod.collect_candidate_alerts(
                "2026-10-08", {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}})
        out[tag] = [c["source"] for c in cands if c["source"].startswith("unexplained:")]
    assert out["a"] == out["b"] == ["unexplained:RUS"]


# ── 2. 이어짐 ────────────────────────────────────────────────

def _stub(monkeypatch, sources, *, configured=True):
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: [
                            {"source": s, "label": "설명불가 신호", "score": 100.0, "evidence": ["근거"]}
                            for s in sources])
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: configured)
    sent = []
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "전송됨" if new else "보낼 신규 경보 없음",
                                                               "new_critical_high": len(new)}))
    return sent


def test_an_ongoing_event_is_not_repaged_on_alternate_days(isolated_db, monkeypatch):
    """옛 동작의 재현·수리 — 1일차 전송, 2일차 조용, 3일차에 다시 울리던 것이 3일 내내 조용해진다."""
    sent = _stub(monkeypatch, ["unexplained:RUS"])
    for day in ("2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10"):
        refresh_alerts(day)
    assert sent == [["unexplained:RUS"], [], [], []]


def test_the_record_is_carried_onto_each_days_row(isolated_db, monkeypatch):
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-07")
    refresh_alerts("2026-10-08")
    row = db.list_alerts("2026-10-08")[0]
    assert row["notified_rank"] == 3                   # 오늘 보낸 것이 아니라 이어받은 기록


def test_a_gap_day_ends_the_chain_for_sources_that_are_not_unexplained(isolated_db, monkeypatch):
    """설명불가가 아닌 계열은 여전히 '어제까지만' 잇는다 — 하루 빈 뒤의 복귀는 새 소식이다.
    (설명불가는 2026-10-17 부터 며칠을 거슬러 올라간다: test_unexplained_inherit_days_2026_10_17.py)"""
    sent = _stub(monkeypatch, ["gai:behavioral.x"])
    refresh_alerts("2026-10-07")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-08")                       # 하루 비었다 — 행이 없다
    sent3 = _stub(monkeypatch, ["gai:behavioral.x"])
    refresh_alerts("2026-10-09")
    assert sent3 == [["gai:behavioral.x"]]


def test_a_different_country_is_still_news(isolated_db, monkeypatch):
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-07")
    sent = _stub(monkeypatch, ["unexplained:RUS", "unexplained:IND"])
    refresh_alerts("2026-10-08")
    assert sent == [["unexplained:IND"]]


def test_without_a_channel_nothing_is_recorded(isolated_db, monkeypatch):
    """채널이 없으면 '보냄' 기록 자체가 없다 — 이어받을 것도 없다(거짓으로 적지 않는다)."""
    _stub(monkeypatch, ["unexplained:RUS"], configured=False)
    refresh_alerts("2026-10-07")
    refresh_alerts("2026-10-08")
    assert db.list_alerts("2026-10-08")[0]["notified_rank"] is None


def test_escalation_still_notifies_across_days(isolated_db, monkeypatch):
    """이어받은 기록은 같은 등급까지만 막는다 — 등급이 오르면 새 소식이다."""
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    sent = []
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "전송됨" if new else "보낼 신규 경보 없음",
                                                               "new_critical_high": len(new)}))
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts", lambda t, n=None: [
        {"source": "x", "label": "x", "score": 85.0, "evidence": ["e"]}])          # high
    refresh_alerts("2026-10-07")
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts", lambda t, n=None: [
        {"source": "x", "label": "x", "score": 95.0, "evidence": ["e"]}])          # critical
    refresh_alerts("2026-10-08")
    assert sent == [["x"], ["x"]]

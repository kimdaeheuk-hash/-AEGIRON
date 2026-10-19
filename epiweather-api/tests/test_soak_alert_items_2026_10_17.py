"""소킹 10-15·10-16·10-17 일지가 올린 경보 쪽 결함 넷 (2026-10-17, 캡틴 지시 "새항목 전부 실행해").

## 관측 (프로덕션 Railway 로그)
A. 10-17 22:02 UTC `설명불가 신호 · 지역불명 (질병불명) 100.0점(위치: 불명)` critical → 폰. 어디서 무엇이 일어났는지
   하나도 알 수 없는 문장이었다.
B. 10-16 16:01 UTC `환경신호 · cdc_nwss_concentration 95.0점(관측값 1680229.8 · 평소 약 87690)` critical → 폰.
   수집 로그: 직전 윈도 평균 63,488.7(757행) → 새 윈도 1,680,229.8(656행) — 26.5배, 행은 오히려 줄었다.
C. 10-16 00:02 UTC `행동신호 · medrxiv_epi_papers 85.0점(관측값 6(평소 약 1.4))` high → 폰. 프리프린트 편수 6건.
D. 10-13 22:01 UTC 이르쿠츠크 설명불가가 닷새 만에 폰을 다시 울렸다 — 이어받기가 '어제'까지만 거슬러 올라가서
   감시가 비었던 날(10-09 NLP 실패) 뒤의 복귀가 새 소식이 됐다.

## 원칙
지수(GAI)는 측정값이라 안 건드린다. 사람을 깨우는 **경보 점수**만 79(medium)로 제한하고, 제한한 사실과 이유는
로그와 근거에 남긴다(지우지 않는다). 막는 목록이지 허용 목록이 아니다 — 관측된 지표만 건드린다.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import (UNEXPLAINED_INHERIT_DAYS, UNLOCATED_UNEXPLAINED_CAP, classify_tier,
                               is_unlocated, refresh_alerts)
from algorithms.signal_metrics import (IMPLAUSIBLE_JUMP_CAP, count_noise_reason, implausible_jump,
                                       is_count_noise_metric, metric_unit)

ALERTS_PY = Path(alerts_mod.__file__)
_EMPTY_NS = {"alerts": [], "alert_count": 0, "metrics_checked": 0, "skipped": {}}


def _gai(layer_key, layer_label, metric, latest, mean, raw, trusted, trust):
    return {"gai": 10.0, "layers": {layer_key: {
        "label": layer_label, "weight": 0.2, "score": trusted,
        "metrics": [{"metric": metric, "latest": latest, "baseline_mean": mean,
                     "raw_score": raw, "trust": trust, "trusted_score": trusted}]}}}


def _collect(monkeypatch, gai=None, unexplained=None, today="2026-10-17"):
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: gai or {"gai": 10.0, "layers": {}})
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": unexplained or []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        return alerts_mod.collect_candidate_alerts(today, _EMPTY_NS)


def _unex(location, raw="질병불명", today="2026-10-17"):
    return {"source": "unexplained_cluster", "location": location, "raw_disease_text": raw,
            "raw_text": "원문", "extracted_at": f"{today}T21:03:00"}


# ═══ A. 위치를 못 읽은 설명불가 후보 ═══════════════════════════════════════════════

def test_unlocated_unexplained_candidate_is_capped_below_high(monkeypatch):
    """10-17 22:02 의 입력 그대로 — 위치 없음 + 질병 모름."""
    cands = _collect(monkeypatch, unexplained=[_unex(None, raw=None)])
    c = [c for c in cands if c["source"].startswith("unexplained:")][0]
    assert c["label"] == "설명불가 신호 · 지역불명 (질병불명)"         # 폰에 나간 그 문장
    assert c["score"] == UNLOCATED_UNEXPLAINED_CAP == 79.0
    assert classify_tier(c["score"]) == "medium"                      # critical 이었다(옛 동작: 100.0)
    assert "위치를 읽지 못한 후보" in c["evidence"][0]
    assert "위치: 불명" in c["evidence"][1]                           # 후보 자체는 지우지 않고 그대로 보인다


def test_the_old_behaviour_was_critical_for_the_same_input():
    """옛 동작 고정: 점수 100 은 critical — 위치가 있든 없든 폰에 나갔다. 판정은 일관됐고 틀린 건 '정보량'이었다."""
    assert classify_tier(100.0) == "critical"
    assert classify_tier(UNLOCATED_UNEXPLAINED_CAP) == "medium"


@pytest.mark.parametrize("loc", [None, "", "  ", "불명", "지역불명", "미상", "Unknown", "N/A", "-"])
def test_every_unknown_location_spelling_is_unlocated(loc):
    assert is_unlocated(loc) is True


@pytest.mark.parametrize("loc", ["Irkutsk, Russia", "러시아 시베리아", "시베리아", "Hubei", "콩고민주공화국, 우간다"])
def test_a_location_with_information_is_not_unlocated(loc):
    """나라로 안 읽혀도(지방 이름) 문구가 있으면 정보가 있다 — 예전 그대로 100 이다."""
    assert is_unlocated(loc) is False


def test_located_candidate_keeps_its_critical_score(monkeypatch):
    cands = _collect(monkeypatch, unexplained=[_unex("Irkutsk, Russia")])
    c = [c for c in cands if c["source"] == "unexplained:RUS"][0]
    assert c["score"] == 100.0 and not any("위치를 읽지 못한" in e for e in c["evidence"])


def test_an_unlocated_candidate_never_rings_the_phone(isolated_db, monkeypatch):
    """끝까지: refresh_alerts 가 이 후보를 medium 으로 올리고 통보 대상에 안 넣는다."""
    sent = []
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "보낼 신규 경보 없음", "new_critical_high": len(new)}))
    monkeypatch.setattr(alerts_mod, "scan_negative_space", lambda: _EMPTY_NS)
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: {"gai": 10.0, "layers": {}})
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": [_unex(None, raw=None)]})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        refresh_alerts("2026-10-17")
    rows = db.list_alerts("2026-10-17")
    row = [r for r in rows if r["source"].startswith("unexplained:")][0]
    assert row["tier"] == "medium"
    assert sent == [[]]


def test_the_unlocated_cap_is_wired_into_candidate_collection():
    """만들어만 두고 아무도 안 부르는 층을 막는다 — collect_candidate_alerts 가 is_unlocated 를 부른다."""
    tree = ast.parse(ALERTS_PY.read_text(encoding="utf-8"))
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "collect_candidate_alerts"][0]
    called = {c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert {"is_unlocated", "implausible_jump", "count_noise_reason"} <= called


# ═══ B. 한 주 사이 비현실적 점프(NWSS) ═════════════════════════════════════════════

def test_implausible_jump_reports_the_ratio_only_beyond_the_limit():
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, 63488.7) == pytest.approx(26.47, abs=0.01)
    assert implausible_jump("cdc_nwss_concentration", 500000.0, 63488.7) is None      # 7.9배 — 문턱(10배) 아래
    assert implausible_jump("cdc_nwss_concentration", 634887.0, 63488.7) is None      # 정확히 10.0배는 문턱을 넘지 않음
    assert implausible_jump("cdc_nwss_concentration", 634888.0, 63488.7) is not None  # 10.00000x 는 넘는다


def test_implausible_jump_is_silent_when_it_cannot_judge():
    """점수를 *깎는* 쪽이라 모를 때는 깎지 않는다."""
    assert implausible_jump("cdc_nwss_concentration", None, 63488.7) is None
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, None) is None
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, 0.0) is None
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, -5.0) is None


def test_implausible_jump_is_a_blocklist_not_an_allowlist():
    """대상이 아닌 지표는 아무리 커도 건드리지 않는다 — 관측된 지표만."""
    assert implausible_jump("kdca_weekly_total", 1_000_000.0, 100.0) is None
    assert implausible_jump("naver_flu_ratio", 1_000_000.0, 100.0) is None


def test_nwss_1016_replay_is_capped_to_medium_with_the_reason_on_the_second_line(monkeypatch):
    """10-16 16:01 입력 그대로: 관측값 1,680,229.8 · 평균 63,488.7 · 원시 100 × 신뢰도 0.95 = 95.0."""
    gai = _gai("environmental", "환경신호", "cdc_nwss_concentration", 1680229.8, 63488.7, 100.0, 95.0, 0.95)
    cands = _collect(monkeypatch, gai)
    c = [c for c in cands if c["source"].endswith("cdc_nwss_concentration")][0]
    assert c["score"] == IMPLAUSIBLE_JUMP_CAP == 79.0
    assert classify_tier(c["score"]) == "medium"                 # critical 이었다
    assert "경보 점수 79.0점으로 제한" in c["evidence"][1]        # 폰에 가는 둘째 줄 안에 이유가 있다
    assert "26.5배" in c["evidence"][1]
    assert "관측값 1680229.8" in c["evidence"][0] and "평소 약 63,489" in c["evidence"][0]


def test_the_cap_does_not_wear_off_as_the_same_weekly_value_drags_the_mean_up(monkeypatch):
    """★ PR #83 자기검토에서 찾은 구멍 ★ 주간 값이 매시간 다시 기록돼 평균이 시간당 약 650 씩 끌려 올라간다
    (10-16 평소 약 87,690 → 10-18 108,705). 평균만 보면 ~10-21 에 배수가 10 밑으로 떨어져 상한이 풀리고,
    같은 값(1,680,229.8)이 critical 로 되살아나 폰이 다시 울린다. 직전의 다른 값(지난 창 63,488.7)과의 배수는
    그 오염을 안 받는다 — 같은 주 안에서는 판정이 바뀌지 않아야 한다."""
    drifted_mean = 170_000.0                                           # 1,680,229.8 / 170,000 = 9.9배
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, drifted_mean) is None          # 평균만 보면 풀린다
    assert implausible_jump("cdc_nwss_concentration", 1680229.8, drifted_mean, 63488.7) == pytest.approx(26.47, abs=0.01)
    gai = _gai("environmental", "환경신호", "cdc_nwss_concentration", 1680229.8, drifted_mean, 100.0, 95.0, 0.95)
    gai["layers"]["environmental"]["metrics"][0]["previous_distinct"] = 63488.7
    c = [c for c in _collect(monkeypatch, gai) if c["source"].endswith("cdc_nwss_concentration")][0]
    assert c["score"] == 79.0


def test_a_normal_window_after_the_jump_is_not_capped(monkeypatch):
    """창이 굴러 평소 수준(60,000)으로 돌아오면 직전 값(1.68M)보다 훨씬 낮다 — 깎을 일이 없다."""
    assert implausible_jump("cdc_nwss_concentration", 60000.0, 170_000.0, 1680229.8) is None


def test_previous_distinct_is_the_last_value_that_differs_from_the_latest():
    from algorithms.gai import _previous_distinct
    assert _previous_distinct([63488.7] * 3 + [1680229.8] * 40) == 63488.7    # 같은 주간 값이 몇 번 반복돼도
    assert _previous_distinct([1.0, None, 2.0, None, 2.0]) == 1.0             # None 은 건너뛴다(점수와 같은 규칙)
    assert _previous_distinct([5.0, 5.0, 5.0]) is None                         # 다른 값이 없으면 모른다
    assert _previous_distinct([]) is None and _previous_distinct([None]) is None


def test_compute_gai_exports_previous_distinct_for_every_metric(monkeypatch):
    """만들어만 두고 안 내보내는 값을 막는다 — 실제 compute_gai 출력에 들어가야 승격 자리가 읽는다."""
    from algorithms import gai as gai_mod
    weekly = [60000.0, 61000.0, 62000.0, 63488.7] + [63488.7] * 5 + [1680229.8] * 20
    recs = [{"type": "free_sources", "cdc_nwss": {"mean_concentration": v}} for v in weekly]
    monkeypatch.setattr(gai_mod, "load_records", lambda: recs)
    out = gai_mod.compute_gai()
    m = [m for layer in out["layers"].values() for m in layer["metrics"]
         if m["metric"] == "cdc_nwss_concentration"][0]
    assert m["latest"] == 1680229.8 and m["previous_distinct"] == 63488.7
    # 10-17 당시엔 '평균은 반복된 새 값에 끌려 올라가 있다'(> 63488.7)를 고정했다 — 그게 기준선 오염이었다.
    # 10-19(④)부터 주간 지표는 반복을 한 관측으로 접어, 평균은 과거 주 값들의 평균이다.
    assert m["baseline_mean"] == round((60000.0 + 61000.0 + 62000.0 + 63488.7) / 4, 4)


def test_nwss_ordinary_variation_is_untouched(monkeypatch):
    """평소의 3배(문턱 아래)는 옛 동작 그대로 95점이다 — 진짜 신호를 죽이지 않는다."""
    gai = _gai("environmental", "환경신호", "cdc_nwss_concentration", 190000.0, 63488.7, 100.0, 95.0, 0.95)
    c = [c for c in _collect(monkeypatch, gai) if c["source"].endswith("cdc_nwss_concentration")][0]
    assert c["score"] == 95.0 and "제한" not in c["evidence"][1]


def test_another_metric_with_the_same_shape_is_not_touched(monkeypatch):
    gai = _gai("official", "공식신호", "kdca_weekly_total", 1680229.8, 63488.7, 100.0, 95.0, 0.95)
    c = [c for c in _collect(monkeypatch, gai) if c["source"].endswith("kdca_weekly_total")][0]
    assert c["score"] == 95.0


def test_nwss_critical_no_longer_reaches_the_phone(isolated_db, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (sent.append([r["source"] for r in new]) or
                                                              {"status": "보낼 신규 경보 없음", "new_critical_high": len(new)}))
    monkeypatch.setattr(alerts_mod, "scan_negative_space", lambda: _EMPTY_NS)
    monkeypatch.setattr(alerts_mod, "compute_gai", lambda: _gai(
        "environmental", "환경신호", "cdc_nwss_concentration", 1680229.8, 63488.7, 100.0, 95.0, 0.95))
    monkeypatch.setattr(alerts_mod, "scan_unexplained", lambda: {"alerts": []})
    with patch("algorithms.comtrade_signals.trade_alert_candidates", return_value=[]):
        refresh_alerts("2026-10-16")
    row = [r for r in db.list_alerts("2026-10-16") if r["source"].endswith("cdc_nwss_concentration")][0]
    assert row["tier"] == "medium" and sent == [[]]


# ═══ C. medrxiv_epi_papers (academic 카운트) ═══════════════════════════════════════

def test_medrxiv_is_now_a_count_noise_metric_with_its_own_unit():
    assert is_count_noise_metric("medrxiv_epi_papers") is True
    assert metric_unit("medrxiv_epi_papers") == "medRxiv 감염병 프리프린트 편수"
    assert is_count_noise_metric("cidrap_ebola") is False             # 같은 academic 이라도 관측 안 된 지표는 그대로
    assert is_count_noise_metric("genomic_new_clades_covid") is False


def test_medrxiv_1016_replay_is_capped_to_medium_with_its_own_reason(monkeypatch):
    """10-16 00:02 입력 그대로: 관측값 6 · 평균 1.5 → 85.0(high, 폰)."""
    gai = _gai("behavioral", "행동신호", "medrxiv_epi_papers", 6, 1.4955, 100.0, 85.0, 0.85)
    c = [c for c in _collect(monkeypatch, gai) if c["source"].endswith("medrxiv_epi_papers")][0]
    assert c["score"] == 79.0 and classify_tier(c["score"]) == "medium"
    assert "medRxiv 감염병 프리프린트 편수" in c["evidence"][0] and "평소 약 1.5" in c["evidence"][0]
    assert "프리프린트 편수는 게재 주기" in c["evidence"][1]
    assert "게시자 수" not in c["evidence"][1]                         # 사회 신호의 이유를 빌려 쓰지 않는다


def test_social_metric_keeps_its_own_reason(monkeypatch):
    gai = _gai("behavioral", "행동신호", "social_dengue", 12, 5.0612, 93.5, 84.2, 0.9)
    c = [c for c in _collect(monkeypatch, gai) if "social_dengue" in c["source"]][0]
    assert "경보 점수 79.0점으로 제한" in c["evidence"][1] and "7일 겹치는 창" in c["evidence"][1]
    assert count_noise_reason("social_dengue").startswith("단독 사회 신호")


def test_medrxiv_small_change_is_blocked_by_the_poisson_significance_test(monkeypatch):
    """평소 1.5 인데 3편: (3−1.5)/√1.5 = 1.22σ < 2σ — 포아송 잡음 안이라 후보로도 안 올린다."""
    gai = _gai("behavioral", "행동신호", "medrxiv_epi_papers", 3, 1.5, 100.0, 85.0, 0.85)
    assert not [c for c in _collect(monkeypatch, gai) if c["source"].endswith("medrxiv_epi_papers")]


# ═══ D. 설명불가 이어받기가 며칠을 거슬러 올라간다 ═══════════════════════════════════

def _stub(monkeypatch, sources, *, score=100.0, configured=True):
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: [
                            {"source": s, "label": "설명불가 신호", "score": score, "evidence": ["근거"]}
                            for s in sources])
    monkeypatch.setattr(alerts_mod, "scan_negative_space", lambda: _EMPTY_NS)
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: configured)
    sent = []
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: (
        sent.append([r["source"] for r in new]) or
        {"status": "전송됨" if new else "보낼 신규 경보 없음", "new_critical_high": len(new)}))
    return sent


def test_unexplained_inherit_window_is_a_short_named_constant():
    """대가가 있다(같은 나라의 다른 사건이 이 기간 안에 나오면 같은 등급은 조용) — 그래서 짧고 이름이 있다."""
    assert UNEXPLAINED_INHERIT_DAYS == 5


def test_a_quiet_gap_inside_the_window_does_not_ring_the_phone_again(isolated_db, monkeypatch):
    """10-13 사고의 모양: 감시가 며칠 비었다가 같은 사건이 돌아왔다."""
    sent = _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-08")
    assert sent == [["unexplained:RUS"]]
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")                       # 감시가 눈이 멀었다 — 행 없음
    refresh_alerts("2026-10-10")
    sent3 = _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-11")                       # 3일 뒤 복귀
    assert sent3 == [[]]


def test_the_return_is_labelled_as_an_older_carry_over(isolated_db, monkeypatch):
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")
    _stub(monkeypatch, ["unexplained:RUS"])
    result = refresh_alerts("2026-10-10")
    assert [a["origin"] for a in result["already_notified"]] == ["이전 이월"]
    assert alerts_mod.already_notified_line(result).endswith("(이전 이월)")


def test_the_chain_continues_after_an_older_carry_over(isolated_db, monkeypatch):
    """이전 이월로 조용했던 날에도 기록을 이어 두어야 다음 날 또 조용하다(이틀에 한 번 울리지 않는다)."""
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-10")                       # 이전 이월 — 기록을 잇는다
    assert db.list_alerts("2026-10-10")[0]["notified_rank"] == 3
    sent = _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-11")                       # 어제 이월
    assert sent == [[]]


def test_the_window_edge_is_inclusive_at_five_days(isolated_db, monkeypatch):
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-12")
    sent = _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-13")                       # 마지막 전송 10-08 → 5일 뒤: 창 안 — 조용
    assert sent == [[]]


def test_the_window_is_closed_at_six_days_and_a_return_is_news_again(isolated_db, monkeypatch):
    _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-13")
    sent = _stub(monkeypatch, ["unexplained:RUS"])
    refresh_alerts("2026-10-14")                       # 6일 뒤: 창 밖 — 새 소식(대가를 코드가 말한다)
    assert sent == [["unexplained:RUS"]]


def test_an_escalation_inside_the_window_still_notifies(isolated_db, monkeypatch):
    """이어받은 기록은 같은 등급까지만 막는다 — 등급이 오르면 새 소식이다(조기경보에선 이쪽이 더 나쁜 오류)."""
    _stub(monkeypatch, ["unexplained:RUS"], score=85.0)            # high
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")
    sent = _stub(monkeypatch, ["unexplained:RUS"], score=100.0)    # critical
    refresh_alerts("2026-10-10")
    assert sent == [["unexplained:RUS"]]


def test_other_sources_still_only_look_back_one_day(isolated_db, monkeypatch):
    sent = _stub(monkeypatch, ["gai:behavioral.x"])
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [])
    refresh_alerts("2026-10-09")
    sent3 = _stub(monkeypatch, ["gai:behavioral.x"])
    refresh_alerts("2026-10-10")
    assert sent3 == [["gai:behavioral.x"]]


def test_without_a_channel_the_older_days_are_not_invented(isolated_db, monkeypatch):
    """채널이 없으면 '보냄' 기록 자체가 없다 — 이월할 것도 없다(거짓으로 적지 않는다)."""
    _stub(monkeypatch, ["unexplained:RUS"], configured=False)
    refresh_alerts("2026-10-08")
    _stub(monkeypatch, [], configured=False)
    refresh_alerts("2026-10-09")
    _stub(monkeypatch, ["unexplained:RUS"], configured=False)
    refresh_alerts("2026-10-10")
    assert db.list_alerts("2026-10-10")[0]["notified_rank"] is None

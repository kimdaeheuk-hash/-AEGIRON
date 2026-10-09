"""같은 사건이 위치 이름만 달라 폰을 이틀 연속 울렸다 (2026-10-09 브리핑 검토에서 관측).

## 사고
설명불가 경보의 키는 `unexplained:{위치 문자열}` 이고 위치는 추출 모델이 자유 문장으로 쓴다.
러시아 페스트 사건이 이렇게 두 번 기록됐다(브리핑 설명불가 목록에 둘 다 있었다):

    10-07 22:01  unexplained:Irkutsk, Russia   → critical 폰 1회
    10-08 22:03  unexplained:러시아 시베리아     → critical 폰 1회   ← 같은 사건인데 '처음 보는 source'

기준선(`baseline_rank`)이 문자열 그대로라서, 이름이 바뀌면 어제 알린 것이 기준선에 안 걸린다.

## 고친 방식
행의 `source` 는 그대로 둔다(바꾸면 배포 순간 오늘 행이 기준선에서 빠져 한 번 더 울린다).
기준선 **조회만** 같은 나라로 묶는다 — `resolve_country` 가 국가를 풀 때만 `unexplained:@RUS`.

## 이 파일이 막아야 하는 것
1. 이름이 바뀌었다고 어제 알린 사건이 새 경보가 되는 것(사고 재현).
2. **너무 많이 합치는 것** — 다른 나라, 국가가 안 풀리는 이름은 합치지 않는다. 있는 경보를 없는 것으로
   만드는 쪽이 이 제품에서 더 나쁘다.
3. 합치면서 **'보냈다'를 거짓으로 기록하는 것** — 억제된 행에 notified_rank 를 쓰면 실패 재시도 원칙이 깨진다.
4. 전송 실패가 같은 나라 묶음 때문에 재시도되지 않는 것.
5. 등급이 올라간 경보가 묶음 때문에 조용해지는 것.
"""
from __future__ import annotations

import ast
import inspect

import pytest

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import (NOTIFY_FAILED, NOTIFY_NONE, NOTIFY_SENT, TIER_RANK, alert_group_key,
                               already_notified_line, baseline_rank, escalated, matched_country,
                               notified_rank_of, rank_for, refresh_alerts)

IRKUTSK = "unexplained:Irkutsk, Russia"
SIBERIA = "unexplained:러시아 시베리아"
CRIT = TIER_RANK["critical"]


# ── 1. 묶음 키 ──────────────────────────────────────────────────

def test_the_two_real_names_of_the_siberian_event_share_one_key():
    assert alert_group_key(IRKUTSK) == alert_group_key(SIBERIA) == "unexplained:@RUS"


@pytest.mark.parametrize("a, b", [
    ("unexplained:Russia", "unexplained:러시아"),
    ("unexplained:Russian Federation", "unexplained:Irkutsk, Russia"),
    ("unexplained:Kinshasa, DRC", "unexplained:콩고민주공화국"),
])
def test_other_spellings_of_one_country_share_a_key(a, b):
    assert alert_group_key(a) == alert_group_key(b) != a


def test_different_countries_do_not_share_a_key():
    assert alert_group_key("unexplained:India") != alert_group_key(IRKUTSK)
    assert alert_group_key("unexplained:Guinea") != alert_group_key("unexplained:Papua New Guinea")
    assert alert_group_key("unexplained:Niger") != alert_group_key("unexplained:Nigeria")
    assert alert_group_key("unexplained:Sudan") != alert_group_key("unexplained:South Sudan")


@pytest.mark.parametrize("name", ["시베리아", "이르쿠츠크", "Siberia", "원인불명 폐렴", "불명", ""])
def test_unresolvable_locations_are_not_guessed_to_be_the_same(name):
    """★ 모르는 것을 같다고 추측하지 않는다 ★ 국가가 안 풀리면 키는 그대로다."""
    src = f"unexplained:{name}"
    assert alert_group_key(src) == src


@pytest.mark.parametrize("src", ["headline:plague", "social_dengue", "trade:BLZ", "gai_overall",
                                 "wiki_ebola_daily", "kdca_weekly_total"])
def test_other_alert_kinds_are_never_grouped(src):
    assert alert_group_key(src) == src


def test_a_group_key_can_never_collide_with_a_real_location_string():
    assert "@" in alert_group_key(IRKUTSK)
    assert alert_group_key(IRKUTSK) not in {"unexplained:RUS", "unexplained:Russia"}


# ── 2. 기준선 ───────────────────────────────────────────────────

def _row(source, tier="critical", notified=CRIT, suppressed=0):
    return {"source": source, "tier": tier, "notified_rank": notified, "suppressed": suppressed}


def test_baseline_keeps_the_exact_key_and_adds_the_group_key():
    ranks = baseline_rank([], [_row(IRKUTSK)], channel_configured=True)
    assert ranks[IRKUTSK] == CRIT and ranks["unexplained:@RUS"] == CRIT


def test_baseline_without_a_channel_groups_too():
    ranks = baseline_rank([], [_row(IRKUTSK, notified=None)], channel_configured=False)
    assert ranks["unexplained:@RUS"] == CRIT


def test_yesterdays_notified_irkutsk_silences_todays_siberia():
    """★사고 재현★ 10-07 에 알린 Irkutsk 가 10-08 의 러시아 시베리아를 조용하게 한다."""
    ranks = baseline_rank([], [_row(IRKUTSK)], channel_configured=True)
    assert escalated(SIBERIA, "critical", ranks) is False
    assert rank_for(SIBERIA, ranks) == CRIT


def test_the_old_exact_only_baseline_would_have_rung_again():
    """옛 동작이 경보였다는 사실까지 고정한다 — '판정은 옳았고 틀린 건 키였다'."""
    old_baseline = notified_rank_of([_row(IRKUTSK)])           # 묶음 키가 없던 시절의 기준선
    assert escalated(SIBERIA, "critical", old_baseline) is True


def test_a_different_country_still_rings():
    ranks = baseline_rank([], [_row(IRKUTSK)], channel_configured=True)
    assert escalated("unexplained:India", "critical", ranks) is True


def test_an_unresolvable_name_still_rings_even_if_it_is_really_the_same_event():
    """알려진 한계 — 놓침보다 중복 쪽 실패를 택했다. 이 시험은 그 선택을 고정한다."""
    ranks = baseline_rank([], [_row(IRKUTSK)], channel_configured=True)
    assert escalated("unexplained:시베리아", "critical", ranks) is True


def test_a_higher_tier_still_breaks_through_the_group():
    ranks = baseline_rank([], [_row(IRKUTSK, tier="high", notified=TIER_RANK["high"])], channel_configured=True)
    assert escalated(SIBERIA, "critical", ranks) is True        # 악화는 새 소식이다
    assert escalated(SIBERIA, "high", ranks) is False           # 같은 등급은 아니다


def test_an_unsent_row_does_not_silence_anything():
    """전송 기록이 없으면(실패·미전송) 묶음도 만들어지지 않는다 — 재시도 원칙."""
    ranks = baseline_rank([], [_row(IRKUTSK, notified=None)], channel_configured=True)
    assert "unexplained:@RUS" not in ranks
    assert escalated(SIBERIA, "critical", ranks) is True


def test_a_hand_built_exact_baseline_keeps_working():
    assert escalated(IRKUTSK, "critical", {IRKUTSK: CRIT}) is False
    assert escalated(IRKUTSK, "critical", {}) is True


def test_matched_country_names_the_group_only_when_the_exact_key_missed():
    ranks = baseline_rank([], [_row(IRKUTSK)], channel_configured=True)
    assert matched_country(SIBERIA, "critical", ranks) == "RUS"
    assert matched_country(IRKUTSK, "critical", ranks) is None      # 정확히 같은 키로 걸렸다
    assert matched_country("unexplained:India", "critical", ranks) is None
    assert matched_country("headline:plague", "critical", ranks) is None


# ── 3. 경보 주기 전체 ───────────────────────────────────────────

def _candidate(source, label="설명불가 신호", score=100.0):
    return {"source": source, "label": f"{label} · {source}", "score": score, "evidence": ["근거"]}


def _setup(monkeypatch, *, outcome=NOTIFY_SENT):
    candidates: list[dict] = []
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: list(candidates))
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0, "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "telegram_configured", lambda: True)
    attempts: list[list[str]] = []
    state = {"outcome": outcome}

    def notify(new):
        attempts.append([r["source"] for r in new])
        if not new:
            return {"status": NOTIFY_NONE, "new_critical_high": 0}
        return {"status": state["outcome"], "new_critical_high": len(new)}

    monkeypatch.setattr(alerts_mod, "_notify", notify)
    return candidates, attempts, state


def test_renamed_event_on_the_next_day_does_not_ring_the_phone_again(isolated_db, monkeypatch):
    """★핵심★ 10-07 Irkutsk, 10-08 러시아 시베리아 — 폰은 한 번만."""
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-07")
    cands[:] = [_candidate(SIBERIA)]
    result = refresh_alerts("2026-10-08")

    assert attempts == [[IRKUTSK], []]
    (held,) = result["already_notified"]
    assert held["source"] == SIBERIA and held["origin"] == "어제 이월" and held["same_country"] == "RUS"
    assert "같은 나라 RUS 로 이미 알림" in already_notified_line(result)


def test_a_suppressed_row_is_never_recorded_as_sent(isolated_db, monkeypatch):
    """★ 거짓으로 '보냄'을 적지 않는다 ★ 억제된 행의 notified_rank 는 비어 있어야 한다."""
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-07")
    cands[:] = [_candidate(SIBERIA)]
    refresh_alerts("2026-10-08")

    (row,) = [r for r in db.list_alerts("2026-10-08") if r["source"] == SIBERIA]
    assert row["notified_rank"] is None
    # 행 자체는 화면에 남는다 — 억제되는 건 폰뿐이다
    assert row["tier"] == "critical" and not row["suppressed"]


def test_a_suppressed_row_stays_unrecorded_even_when_another_alert_is_sent_in_the_same_cycle(
        isolated_db, monkeypatch):
    """전송이 일어나는 주기에서만 드러나는 거짓 기록 — 억제된 행이 같이 '보냄'으로 묶이면 안 된다."""
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-07")
    cands[:] = [_candidate(SIBERIA), _candidate("unexplained:India")]       # 하나는 억제, 하나는 신규
    result = refresh_alerts("2026-10-08")

    assert attempts[-1] == ["unexplained:India"]                             # 실제로 전송이 일어났다
    notified = {r["source"]: r["notified_rank"] for r in db.list_alerts("2026-10-08")}
    assert notified["unexplained:India"] == CRIT
    assert notified[SIBERIA] is None                                         # 억제된 행은 비어 있다
    assert [r["source"] for r in result["already_notified"]] == [SIBERIA]


def test_renamed_event_in_the_same_day_is_not_rung_twice(isolated_db, monkeypatch):
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-08")
    cands[:] = [_candidate(IRKUTSK), _candidate(SIBERIA)]
    result = refresh_alerts("2026-10-08")
    assert attempts == [[IRKUTSK], []]
    assert {r["source"]: r["origin"] for r in result["already_notified"]}[SIBERIA] == "오늘"


def test_a_different_country_rings_the_next_day(isolated_db, monkeypatch):
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-07")
    cands[:] = [_candidate("unexplained:India")]
    refresh_alerts("2026-10-08")
    assert attempts == [[IRKUTSK], ["unexplained:India"]]


def test_a_failed_send_is_still_retried_under_a_new_name(isolated_db, monkeypatch):
    """전송 기록 원칙 — 실패한 통보는 기준선에 없으므로 이름이 바뀌어도 다시 시도된다."""
    cands, attempts, state = _setup(monkeypatch, outcome=NOTIFY_FAILED)
    cands[:] = [_candidate(IRKUTSK)]
    refresh_alerts("2026-10-07")
    state["outcome"] = NOTIFY_SENT
    cands[:] = [_candidate(SIBERIA)]
    refresh_alerts("2026-10-08")
    assert attempts == [[IRKUTSK], [SIBERIA]]


def test_other_alert_kinds_dedupe_exactly_as_before(isolated_db, monkeypatch):
    cands, attempts, _ = _setup(monkeypatch)
    cands[:] = [_candidate("headline:plague", score=95.0)]
    refresh_alerts("2026-10-07")
    refresh_alerts("2026-10-08")
    assert attempts == [["headline:plague"], []]


def test_the_log_line_says_nothing_about_countries_for_exact_matches():
    line = already_notified_line({"already_notified": [
        {"tier": "critical", "label": "x", "score": 100.0, "source": IRKUTSK,
         "origin": "오늘", "same_country": None}]})
    assert "같은 나라" not in line and "(오늘)" in line


# ── 4. 배선 (AST) ───────────────────────────────────────────────

def _names(fn):
    tree = ast.parse(inspect.getsource(fn))
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
           {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def test_wiring_every_lookup_goes_through_the_group_aware_helpers():
    assert "rank_for" in _names(escalated)
    assert "_with_group_keys" in _names(baseline_rank)
    refresh = _names(refresh_alerts)
    assert {"matched_country", "rank_for"} <= refresh
    assert "resolve_country" in _names(alert_group_key)

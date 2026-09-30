"""후보에서 빠진 경보 행은 내려간다 — #44 배포 직후 관측된 고장.

## 배경 (2026-09-27)

#44 가 `social_mpox` 를 부정적 공간 판정에서 뺐다. 배포 직후 **같은 사이클**의
로그가 이렇게 찍혔다:

    🔇 부정적 공간: 판정 8개 · 급감 0건          ← 스캔은 0건
    🚨 경보 주기: critical 1건 … social_mpox …   ← 그런데 화면엔 있다

스캔이 0건인데 경보가 남아 있다는 건 **그 경보가 이번 판정에서 나온 게 아니라는
뜻**이다. `refresh_alerts` 가 후보를 upsert 만 하고 내리는 경로가 없어서, 그날
00:02 에 만들어진 행이 자정까지 화면에 붙어 있었다.

**고친 판정이 화면에 반영되지 않으면 고친 게 아니다.**

행은 지우지 않는다 — 오늘 무엇이 울렸는지는 감사 기록이다. 그리고 등급 캡
초과분과 따로 센다: 둘 다 '안 보임'이지만 **'한도에 밀림'과 '판정에서 빠짐'은
다른 사실**이고, 뭉개면 왜 사라졌는지 알 수 없다.
"""
from __future__ import annotations

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import refresh_alerts, summary_line


def _candidate(source: str, score: float, label: str = "테스트 경보"):
    return {"source": source, "label": label, "score": score, "evidence": ["근거"]}


def _stub(monkeypatch, candidates):
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: list(candidates))
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0,
                                 "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: {
        "status": "전송됨" if new else "보낼 신규 경보 없음",
        "new_critical_high": len(new)})


def test_row_that_stopped_being_a_candidate_leaves_the_dashboard(isolated_db, monkeypatch):
    """09-27 의 모양 그대로 — 어제 만들어진 critical 이 후보에서 빠지면 화면에서 내려간다."""
    _stub(monkeypatch, [_candidate("negative_space:behavioral.social_mpox", 100.0)])
    first = refresh_alerts("2026-09-27")
    assert first["tier_summary"]["critical"]["total"] == 1
    assert [a["source"] for a in first["dashboard"]["top"]] == \
        ["negative_space:behavioral.social_mpox"]

    # 판정이 고쳐져 더 이상 후보가 아니다 — 같은 날, 같은 행.
    _stub(monkeypatch, [])
    second = refresh_alerts("2026-09-27")
    assert second["tier_summary"]["critical"]["total"] == 0
    assert second["dashboard"]["top"] == []


def test_retired_is_counted_separately_from_cap_suppression(isolated_db, monkeypatch):
    """'한도에 밀림'과 '판정에서 빠짐'을 같은 칸에 넣지 않는다."""
    _stub(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-09-27")
    _stub(monkeypatch, [])
    result = refresh_alerts("2026-09-27")
    crit = result["tier_summary"]["critical"]
    assert crit["retired"] == 1
    assert crit["suppressed"] == 0     # 한도에 밀린 게 아니다


def test_retired_row_is_kept_in_the_table(isolated_db, monkeypatch):
    """감사 기록 — 오늘 무엇이 울렸는지는 남는다. 지우면 되짚을 수 없다."""
    _stub(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-09-27")
    _stub(monkeypatch, [])
    refresh_alerts("2026-09-27")
    rows = db.list_alerts("2026-09-27")
    assert [r["source"] for r in rows] == ["a"]
    assert rows[0]["suppressed"] == 1   # 남아 있고, 안 보인다


def test_returning_candidate_comes_back_up(isolated_db, monkeypatch):
    """되살아나면 다시 올라간다 — 내리는 것이 영구 삭제가 아니다."""
    _stub(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-09-27")
    _stub(monkeypatch, [])
    refresh_alerts("2026-09-27")
    _stub(monkeypatch, [_candidate("a", 95.0)])
    again = refresh_alerts("2026-09-27")
    assert again["tier_summary"]["critical"]["total"] == 1


def test_returning_candidate_does_not_ring_the_phone_again(isolated_db, monkeypatch):
    """★ 깜빡이는 경보가 폰을 두 번 때리면 안 된다 ★ 내려간 행도 '오늘 이미 본 것'
    이라 seen_rank 에 남는다 — 안 그러면 판정이 흔들릴 때마다 재통보한다."""
    _stub(monkeypatch, [_candidate("a", 95.0)])
    first = refresh_alerts("2026-09-27")
    assert first["notification"]["new_critical_high"] == 1   # 처음엔 나간다

    _stub(monkeypatch, [])
    refresh_alerts("2026-09-27")
    _stub(monkeypatch, [_candidate("a", 95.0)])
    again = refresh_alerts("2026-09-27")
    assert again["notification"]["new_critical_high"] == 0    # 두 번은 안 나간다


def test_summary_line_shows_the_retired_count():
    """이 숫자가 0에서 움직이는 순간이 '판정이 화면에 반영됐다'는 증거다."""
    line = summary_line({
        "tier_summary": {"critical": {"total": 0, "suppressed": 0, "retired": 1},
                         "low": {"total": 3, "suppressed": 0, "retired": 0}},
        "notification": {"status": "보낼 신규 경보 없음"},
    })
    assert "내림 1건" in line


def test_summary_line_has_no_retired_segment_when_nothing_was_retired():
    line = summary_line({
        "tier_summary": {"low": {"total": 2, "suppressed": 0, "retired": 0}},
        "notification": {"status": "보낼 신규 경보 없음"},
    })
    assert "내림" not in line


def test_other_days_rows_are_untouched(isolated_db, monkeypatch):
    """어제 행을 오늘 판정으로 내리지 않는다 — 날짜별 기록이 뒤섞이면 안 된다."""
    _stub(monkeypatch, [_candidate("a", 95.0)])
    refresh_alerts("2026-09-26")
    _stub(monkeypatch, [])
    refresh_alerts("2026-09-27")
    assert [r["source"] for r in db.list_alerts("2026-09-26")] == ["a"]
    assert db.list_alerts("2026-09-26")[0]["suppressed"] == 0

"""`내림 N건` 은 이름을 같이 말한다 — #46 배포 직후 관측된 빈칸.

## 배경 (2026-09-30)

#46 이 프로덕션에서 돌았다. 07:20·08:01 UTC 두 주기 연속:

    🚨 경보 주기: medium 1건 · low 3건 · 내림 3건 · 알림: 보낼 신규 경보 없음 | …

`내림 0 → 3` 은 관측됐다. 그런데 **어느 행이 내려갔는지는 로그에 없었다.** 상위 경보
구성이 바뀐 것으로 정황만 짚을 수 있었고, 그 3건이 정당하게(스캔이 더는 후보로 안 만든
행) 내려간 것인지는 판정하지 못했다. #40 이 고친 '몇 건만 말하고 무엇을 안 말한다'와
같은 모양이 새로 생긴 것이다.

이 시험은 (1) 결과가 내려간 행의 정체를 들고, (2) 그것이 한 줄로 찍히고, (3) 그 줄이
실제 스케줄러 경로에서 불리는지를 고정한다. 셋째가 빠지면 '만들어만 두고 아무도 안
부르는 층'이 된다.
"""
from __future__ import annotations

import ast
from pathlib import Path

import db
from algorithms import alerts as alerts_mod
from algorithms.alerts import refresh_alerts, retired_alerts_line

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


def _candidate(source: str, score: float, label: str = "테스트 경보"):
    return {"source": source, "label": label, "score": score, "evidence": ["근거"]}


def _stub(monkeypatch, candidates):
    monkeypatch.setattr(alerts_mod, "collect_candidate_alerts",
                        lambda today, negative_space=None: list(candidates))
    monkeypatch.setattr(alerts_mod, "scan_negative_space",
                        lambda: {"alerts": [], "alert_count": 0,
                                 "metrics_checked": 8, "skipped": {}})
    monkeypatch.setattr(alerts_mod, "_notify", lambda new: {
        "status": "보낼 신규 경보 없음", "new_critical_high": 0})


def test_result_names_the_rows_that_were_retired(isolated_db, monkeypatch):
    _stub(monkeypatch, [_candidate("gone", 62.5, "의료물자 수입 동시 급증 · BRB"),
                        _candidate("stays", 70.0, "남는 경보")])
    refresh_alerts("2026-09-30")
    _stub(monkeypatch, [_candidate("stays", 70.0, "남는 경보")])
    result = refresh_alerts("2026-09-30")

    assert result["tier_summary"]["medium"]["retired"] + \
        result["tier_summary"]["low"]["retired"] == 1
    assert result["retired"] == [
        {"label": "의료물자 수입 동시 급증 · BRB", "tier": "low",
         "score": 62.5, "source": "gone"}]


def test_retired_is_empty_when_nothing_was_retired(isolated_db, monkeypatch):
    _stub(monkeypatch, [_candidate("a", 70.0)])
    result = refresh_alerts("2026-09-30")
    assert result["retired"] == []
    assert retired_alerts_line(result) is None


def test_line_names_tier_label_score_and_source():
    line = retired_alerts_line({"retired": [
        {"label": "행동신호 · social_cholera", "tier": "medium",
         "score": 70.6, "source": "gai:behavioral.social_cholera"}]})
    assert line == ("🔽 내림: medium 행동신호 · social_cholera 70.6점 "
                    "[gai:behavioral.social_cholera]")


def test_line_lists_every_retired_row_without_truncating():
    """다 적어야 '무엇이 사라졌나'가 닫힌다 — 3건만 적으면 나머지가 다시 빈칸이다."""
    rows = [{"label": f"경보{i}", "tier": "low", "score": 60.0 + i, "source": f"s{i}"}
            for i in range(6)]
    line = retired_alerts_line({"retired": rows})
    for i in range(6):
        assert f"경보{i}" in line and f"[s{i}]" in line
    assert "외 " not in line


def test_line_is_none_without_retired_key():
    """옛 형태의 결과(키 없음)도 깨지지 않는다."""
    assert retired_alerts_line({}) is None


def test_a_returning_row_is_no_longer_listed(isolated_db, monkeypatch):
    """되살아난 행은 '내려가 있는 행' 이 아니다 — 줄이 거짓으로 남으면 안 된다."""
    _stub(monkeypatch, [_candidate("a", 70.0)])
    refresh_alerts("2026-09-30")
    _stub(monkeypatch, [])
    assert refresh_alerts("2026-09-30")["retired"][0]["source"] == "a"
    _stub(monkeypatch, [_candidate("a", 70.0)])
    assert refresh_alerts("2026-09-30")["retired"] == []


def test_named_rows_are_the_ones_the_table_marks_suppressed(isolated_db, monkeypatch):
    """이름 줄과 실제 테이블이 같은 사실을 말한다."""
    _stub(monkeypatch, [_candidate("a", 70.0), _candidate("b", 65.0)])
    refresh_alerts("2026-09-30")
    _stub(monkeypatch, [_candidate("b", 65.0)])
    result = refresh_alerts("2026-09-30")
    named = {r["source"] for r in result["retired"]}
    suppressed = {r["source"] for r in db.list_alerts("2026-09-30") if r["suppressed"]}
    assert named == suppressed == {"a"}


def test_scheduler_path_actually_logs_the_line():
    """★ 만들어만 두고 아무도 안 부르는 층 ★ 이 저장소에서 반복된 실패 유형이다.
    `_run_alert_cycle` 이 retired_alerts_line 을 부르고 그 결과를 로그로 보내는지
    AST 로 고정한다."""
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "_run_alert_cycle")

    calls_line_fn = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "retired_alerts_line" for n in ast.walk(fn))
    assert calls_line_fn, "_run_alert_cycle 이 retired_alerts_line 을 부르지 않는다"

    logs_something = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "log"
        and any(isinstance(a, ast.Name) and a.id == "retired_line" for a in n.args)
    ]
    assert logs_something, "내림 줄을 collector.log 로 내보내지 않는다"

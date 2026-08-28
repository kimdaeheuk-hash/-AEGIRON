"""수집기가 매 주기 건강 요약을 stdout에 남기는지 (2026-08-23).

배경: 아침 점검 세션이 egress 정책 때문에 /api/status를 못 불렀다. Railway 로그로
우회했지만, 로그에는 degraded_sources도 staleness_hours도 안 찍혀 있었다. 즉
**"소스가 조용히 늙고 있는 상태"를 그 점검으로는 못 잡는다** — 8/13 사고를 나흘
끌었던 바로 그 사각지대다. 그래서 수집기가 자기 건강을 로그에 직접 남기게 했다.

★ 테스트가 실제 코드를 부른다 ★ 로직을 테스트에 복사하면 코드가 바뀌어도
테스트는 통과한다. 그건 검증이 아니라 흉내다."""
from __future__ import annotations
from unittest.mock import patch

import collector


def _run_summary(report, capsys) -> str:
    """collect_free_sources의 건강 요약 블록만 실제로 실행시켜 출력 줄을 얻는다.

    전체 수집은 외부 API를 20번 넘게 타므로, 요약 직전까지의 단계는 전부
    가짜로 막고 요약 블록만 진짜로 돌린다."""
    with patch("collector.log_error"), \
         patch("algorithms.source_health.source_health_report", return_value=report), \
         patch("algorithms.source_health.record_cycle", return_value=[]), \
         patch("algorithms.source_health.pending_notifications",
               return_value={"degraded": [], "recovered": []}), \
         patch("algorithms.notifier.notify_source_health", return_value=False), \
         patch("collector.requests.get", side_effect=Exception("blocked")), \
         patch("collector.requests.post", side_effect=Exception("blocked")), \
         patch("collector.append_signal"):
        collector.collect_free_sources()
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if "소스 건강" in l]
    assert lines, f"건강 요약이 출력되지 않았다:\n{out[-500:]}"
    return lines[-1]


def test_summary_shows_healthy_ratio_and_problem_sources(capsys):
    """★핵심★ ok인데 늙고 있는 소스가 보여야 한다 — 그게 사각지대였다."""
    line = _run_summary({
        "healthy_count": 19, "total_tracked": 21,
        "degraded_sources": ["KDCA"],
        "no_data_sources": ["GroqWatch"],
        "sources": [
            {"source": "KDCA", "status": "failing", "staleness_hours": 95.0},
            {"source": "Naver", "status": "ok", "staleness_hours": 0.2},
            {"source": "PubMed", "status": "ok", "staleness_hours": 7.5},
        ],
    }, capsys)
    assert "정상 19/21" in line
    assert "KDCA" in line
    assert "GroqWatch" in line
    assert "PubMed(7.5h)" in line       # status는 ok지만 조용히 늙는 중


def test_summary_is_short_when_all_healthy(capsys):
    """평소엔 짧아야 한다 — 빈 항목을 나열하면 진짜 문제가 눈에 안 띈다."""
    line = _run_summary({
        "healthy_count": 21, "total_tracked": 21,
        "degraded_sources": [], "no_data_sources": [],
        "sources": [{"source": "Naver", "status": "ok", "staleness_hours": 0.2}],
    }, capsys)
    assert "정상 21/21" in line
    assert "문제 없음" in line
    assert "중단" not in line and "늙는중" not in line


def test_summary_stays_readable_when_everything_breaks(capsys):
    """21개가 다 죽어도 한 줄이 화면을 넘기면 안 된다 — 안 읽히는 로그는 없는 것과 같다."""
    names = [f"SRC{i}" for i in range(21)]
    line = _run_summary({
        "healthy_count": 0, "total_tracked": 21,
        "degraded_sources": names, "no_data_sources": [],
        "sources": [{"source": n, "status": "failing", "staleness_hours": 99.0} for n in names],
    }, capsys)
    assert "외 16개" in line            # 5개만 이름, 나머지는 개수로
    assert len(line) < 200


def test_summary_failure_does_not_break_collection(capsys):
    """요약을 못 만들어도 수집 자체는 완료돼야 한다(KDCA 교훈)."""
    with patch("collector.log_error"), \
         patch("algorithms.source_health.source_health_report",
               side_effect=RuntimeError("health file corrupt")), \
         patch("algorithms.source_health.record_cycle", return_value=[]), \
         patch("algorithms.source_health.pending_notifications",
               return_value={"degraded": [], "recovered": []}), \
         patch("algorithms.notifier.notify_source_health", return_value=False), \
         patch("collector.requests.get", side_effect=Exception("blocked")), \
         patch("collector.requests.post", side_effect=Exception("blocked")), \
         patch("collector.append_signal"):
        collector.collect_free_sources()
    assert "무료 소스 수집 완료" in capsys.readouterr().out

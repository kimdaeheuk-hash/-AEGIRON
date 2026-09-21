"""로그가 '몇 건'만 말하고 '무엇'을 안 말했다 (2026-09-21).

## 왜 이 파일이 있나

09-21 00:03 에 critical 1건이 캡틴 폰으로 나갔다. 로그에 남은 건 이것뿐이다:

    🚨 경보 주기: critical 1건 · medium 2건 · low 7건 · 알림: 전송됨

**어느 지표인지 알 수가 없다.** 같은 사이클에서 값이 넷 움직였고(코로나비율
50.87→56.33, 에볼라비율 5.179→5.231, 공급망 542.79→589.9, 조달 임박 5→14)
로그만으로는 좁힐 수 없었다.

09-19 에 같은 문제를 적어두고 고치지 않았다 — 그때는 "다음에"라고 했다.
그런데 런칭 전 소킹의 1번 판정 기준이 **'거짓 경보 0건'** 이다. 무엇이 울렸는지
모르면 그게 거짓인지 판정할 수가 없다. **관측이 안 되는 기준은 기준이 아니다.**

(캡틴 지시로 소킹 중에 넣은 유일한 코드 변경이다 — 관측 공백을 메우는 것이라
소킹의 목적에 부합한다.)
"""
from __future__ import annotations

from algorithms.alerts import NAMED_IN_LOG, named_alerts, summary_line


def _result(top: list[dict], **kw) -> dict:
    base = {
        "tier_summary": {"critical": {"total": 1, "suppressed": 0}},
        "notification": {"status": "전송됨"},
        "dashboard": {"top": top},
    }
    return {**base, **kw}


def _row(label: str, score: float, evidence: list[str] | None = None) -> dict:
    return {"label": label, "score": score, "evidence": evidence or []}


# ── ★핵심★ 무엇이 울렸는지가 로그에 남는다 ────────────────────
def test_the_log_names_what_fired():
    """★이 테스트가 이 파일의 이유다★ 09-21 00:03 에 없던 바로 그 정보다."""
    line = summary_line(_result([_row("행동신호 · supply_total_ratio", 90.0, ["관측값 589.9"])]))
    assert "critical 1건" in line          # 세는 것도 그대로
    assert "supply_total_ratio" in line    # 무엇인지도
    assert "관측값 589.9" in line          # 몇인지도


def test_evidence_first_line_rides_along():
    """★핵심★ 근거 첫 줄이 '관측값 N'(GAI)이거나 '최신값 X (과거 평균 …)'
    (부정적 공간)이다. 그 한 줄이면 '몇 점'이 아니라 **'무엇이 몇인데 몇 점'**
    이 된다 — 09-19 에 로그를 뒤져 알아내야 했던 그 정보다."""
    line = summary_line(_result([
        _row("비공식신호 · local_news_kw_hits", 94.6,
             ["최신값 0 (과거 평균 1656.0의 0.0배)"])]))
    assert "최신값 0 (과거 평균 1656.0의 0.0배)" in line


def test_evidence_is_not_truncated():
    """예전에 [:40] 절단이 진단을 통째로 먹은 적이 있다(2026-09 추출 사고).
    로그 줄이 길어지는 것보다 원인을 못 읽는 게 나쁘다."""
    long_evidence = "관측값 " + "9" * 120
    assert long_evidence in summary_line(_result([_row("x", 90.0, [long_evidence])]))


# ── 줄이 화면을 덮지 않는다 ────────────────────────────────────
def test_only_the_top_few_are_named_and_the_rest_are_counted():
    """등급 캡이 critical 3 · high 5 라 최대 8건까지 난다. 다 적으면 줄이
    화면을 덮는다 — 점수 높은 순 3건이면 무엇이 울렸는지는 드러난다."""
    rows = [_row(f"지표{i}", 90.0 - i) for i in range(6)]
    line = summary_line(_result(rows))
    assert NAMED_IN_LOG == 3
    assert "지표0" in line and "지표2" in line
    assert "지표3" not in line
    assert "외 3건" in line


def test_no_leftover_suffix_when_everything_is_named():
    assert "외" not in summary_line(_result([_row("하나", 90.0)]))


# ── 없는 것을 지어내지 않는다 ──────────────────────────────────
def test_quiet_cycle_stays_quiet():
    """경보가 없으면 이름 칸도 없다 — 빈 괄호를 붙여 줄을 늘리지 않는다."""
    line = summary_line({"tier_summary": {}, "notification": {"status": "보낼 신규 경보 없음"},
                         "dashboard": {"top": []}})
    assert line == "후보 0건 · 알림: 보낼 신규 경보 없음"
    assert named_alerts({"dashboard": {"top": []}}) is None


def test_missing_evidence_still_names_the_metric():
    """근거가 없는 경보도 이름은 적는다 — 이름이 없는 것보다 낫다."""
    line = summary_line(_result([_row("공식신호 · hk_chp_total", 55.0, [])]))
    assert "hk_chp_total 55.0점" in line


def test_counts_and_notification_survive_the_addition():
    """★핵심★ 이름을 붙이느라 기존 정보를 밀어내면 안 된다 — 건수와 알림
    결과는 소킹 점검이 매일 세는 값이다."""
    line = summary_line(_result([_row("x", 90.0)],
                                tier_summary={"critical": {"total": 2, "suppressed": 1}},
                                notification={"status": "전송 실패"}))
    assert "critical 2건(억제 1)" in line
    assert "알림: 전송 실패" in line

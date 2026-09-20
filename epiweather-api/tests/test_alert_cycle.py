"""경보가 사람에게 닿는 경로 — 누가 부르고, 결과를 어떻게 보고하는가 (2026-09-19).

## 왜 이 파일이 있나

캡틴: "왜 질병이 퍼지고 있는데 아이기론은 보고를 안해!?"

경보 엔진도, 텔레그램 발송도 처음부터 있었다. 없던 건 **그걸 부르는 사람**이다.
스케줄러가 매시간 부르는 건 수집기뿐이었고, refresh_alerts 는

    · 누가 /api/alerts · /api/dashboard 를 열 때
    · 하루 1회 일일 브리핑 안에서(그것도 `try/except: alerts = []` 안에서)

만 돌았다. 수집기가 급증을 잡아도 **아무도 대시보드를 안 열면 경보가 안 나갔다.**
이 리포에서 반복된 실패 유형 그대로다 — 층은 다 있는데 아무도 안 부른다.

## 이 파일이 지키는 두 가지

1. 스케줄러가 매시간 경보 주기를 부른다 (아래 호출자 테스트)
2. 그 결과가 로그 한 줄로 남고, 알림 상태가 세 갈래로 갈린다
   (미설정 / 전송됨 / 전송실패 — 뭉개면 고장이 정상으로 둔갑한다)
"""
from __future__ import annotations

import ast
import pathlib
from unittest.mock import patch

from algorithms import alerts


ROOT = pathlib.Path(__file__).resolve().parent.parent


def _called_names(func_node: ast.AST) -> set[str]:
    """함수 본문에서 호출되는 이름들(await 포함)."""
    out = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


def _referenced_names(func_node: ast.AST) -> set[str]:
    """본문에 등장하는 이름 전부. 호출만 세면 부족하다 — asyncio.to_thread 로
    넘기는 함수는 '호출'이 아니라 '인자'로 나타난다."""
    return {n.id for n in ast.walk(func_node) if isinstance(n, ast.Name)} | \
           {n.attr for n in ast.walk(func_node) if isinstance(n, ast.Attribute)}


def _find_func(tree: ast.Module, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} 을 찾지 못함")


# ── ★핵심★ 누가 부르는가 ────────────────────────────────────────
def test_scheduler_loop_runs_the_alert_cycle():
    """★이 테스트가 이 파일의 이유다★ 경보 계산이 스케줄러에 없으면, 신호가
    잡혀도 사람이 대시보드를 열기 전까지 아무한테도 안 간다. 이 호출이
    사라지는 변경은 에러 한 줄 없이 조기경보를 끄는 변경이다."""
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    assert "_run_alert_cycle" in _called_names(_find_func(tree, "_scheduler_loop"))


def test_alert_cycle_calls_refresh_and_logs_the_outcome():
    """돌리기만 하고 로그를 안 남기면 '평온해서 조용한 것'과 '경로가 끊겨서
    조용한 것'이 똑같이 보인다 — 소스 장애와 달리 경보 침묵은 티가 안 난다."""
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    node = _find_func(tree, "_run_alert_cycle")
    names = _referenced_names(node)
    assert "refresh_alerts" in names      # 별도 스레드로 넘기므로 '인자'로 나타난다
    assert "summary_line" in _called_names(node)
    assert "log" in _called_names(node)


# ── 알림 상태는 세 갈래다 ───────────────────────────────────────
def _notify_with(sent: bool, configured: bool, count: int = 1):
    rows = [{"source": f"s{i}", "tier": "critical"} for i in range(count)]
    with patch("algorithms.alerts.notify_new_alerts", return_value=sent), \
         patch("algorithms.alerts.telegram_configured", return_value=configured):
        return alerts._notify(rows)["status"]


def test_unconfigured_channel_is_not_reported_as_failure():
    """★핵심★ notify_new_alerts 는 '미설정'과 '전송 실패'에 똑같이 False 를
    준다. 앞은 캡틴이 아직 안 켠 것이고 뒤는 켜놨는데 경보가 안 닿은 것이다 —
    뒤쪽은 그 자체로 사고다. 뭉치면 진짜 고장이 '원래 안 켰나 보다'가 된다."""
    assert _notify_with(sent=False, configured=False) == alerts.NOTIFY_UNCONFIGURED
    assert _notify_with(sent=False, configured=True) == alerts.NOTIFY_FAILED


def test_successful_send_is_reported_as_sent():
    assert _notify_with(sent=True, configured=True) == alerts.NOTIFY_SENT


def test_nothing_to_send_is_its_own_state():
    """'보낼 게 없었다'는 성공도 실패도 아니다 — 판정 결과다."""
    assert _notify_with(sent=False, configured=True, count=0) == alerts.NOTIFY_NONE


def test_notify_is_called_even_when_there_is_nothing_new():
    """빈 목록에서 호출을 앞질러 막지 않는다 — 발송 판단은 notifier 안에 있고,
    여기서 막으면 '신규 0건이면 아무한테도 안 간다'를 시험하던 자리가 사라진다."""
    with patch("algorithms.alerts.notify_new_alerts", return_value=False) as m, \
         patch("algorithms.alerts.telegram_configured", return_value=True):
        alerts._notify([])
    assert m.call_count == 1
    assert m.call_args[0][0] == []


# ── 로그 한 줄 ──────────────────────────────────────────────────
def test_summary_line_shows_tiers_and_notification_status():
    line = alerts.summary_line({
        "tier_summary": {"critical": {"total": 1, "suppressed": 0},
                         "high": {"total": 7, "suppressed": 2},
                         "medium": {"total": 0, "suppressed": 0}},
        "notification": {"status": alerts.NOTIFY_SENT, "new_critical_high": 1},
    })
    assert "critical 1건" in line
    assert "high 7건(억제 2)" in line
    assert "medium" not in line          # 0건은 줄을 채우지 않는다
    assert alerts.NOTIFY_SENT in line


def test_summary_line_survives_a_quiet_day():
    line = alerts.summary_line({"tier_summary": {}, "notification":
                                {"status": alerts.NOTIFY_NONE, "new_critical_high": 0}})
    assert "후보 0건" in line
    assert alerts.NOTIFY_NONE in line


def test_summary_line_does_not_invent_a_status_it_was_not_given():
    """알림 결과가 없는 결과 dict 를 받으면 '전송됨'으로 보이면 안 된다."""
    assert "판정 안 함" in alerts.summary_line({"tier_summary": {}})


# ── 반환 계약 ───────────────────────────────────────────────────
def test_refresh_alerts_reports_the_notification_outcome(isolated_db):
    """경보 결과에 알림 상태가 실려야 스케줄러·API 어느 쪽에서 봐도 같은
    사실을 본다(로그용 문자열을 호출부에서 따로 조립하지 않는 이유)."""
    candidates = [{"source": "gai:overall", "label": "종합", "score": 95.0, "evidence": []}]
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=candidates), \
         patch("algorithms.alerts.notify_new_alerts", return_value=True), \
         patch("algorithms.alerts.telegram_configured", return_value=True):
        result = alerts.refresh_alerts("2026-09-19")

    assert result["notification"]["status"] == alerts.NOTIFY_SENT
    assert result["notification"]["new_critical_high"] == 1


# ── ★2026-09-20★ 등급 수만으로는 무엇이 울렸는지 알 수 없었다 ──────────
#
# 09-19 점검이 `critical 1건` 이 13주기 연속 찍히는 것을 보고도 그게 무슨 경보인지
# 로그로 알 수 없었다. 그 사이 11:03·01:02 두 번 캡틴 폰으로 알림이 나갔다.
#
# 더 나쁜 것은 critical 이 주기마다 켜졌다 꺼졌다 한 것이다
# (23:01 있음 → 00:01 없음 → 01:02 있음 → 03:01 없음). 깜빡이는 신호는 이 리포가
# GroqWatch·Mobility 에서 두 번 데인 모양이다 — 가끔 사라지는 것이 추적을 막는다.
#
# 억제된 경보는 이미 이름을 남기고 있었다:
#   ⏸ [alerts] genomic_new_clades_covid — 이상도 85.0점이지만 관측값 1 이 …
# **막은 것은 이름을 남기고 나간 것은 안 남기는** 상태였다.

def test_summary_line_names_the_critical_and_high_alerts():
    """★이 변경의 이유★ 무엇이 critical 인지 로그 한 줄에서 갈려야 한다."""
    line = alerts.summary_line({
        "tier_summary": {
            "critical": {"total": 1, "suppressed": 0, "sources": ["negative_space:local_news"]},
            "high": {"total": 2, "suppressed": 0, "sources": ["gai:overall", "kdca:flu"]},
        },
        "notification": {"status": alerts.NOTIFY_SENT, "new_critical_high": 1,
                         "sources": ["negative_space:local_news"]},
    })
    assert "critical 1건[negative_space:local_news]" in line
    assert "high 2건[gai:overall·kdca:flu]" in line
    # 알림도 '무엇이 나갔는지'까지. 상태만 남기면 대상이 사라진다.
    assert f"알림: {alerts.NOTIFY_SENT}[negative_space:local_news]" in line


def test_summary_line_does_not_name_medium_and_low():
    """medium·low 는 캡이 없어 수십 개가 된다. 다 나열하면 정작 critical 이름이 묻힌다."""
    line = alerts.summary_line({
        "tier_summary": {
            "critical": {"total": 1, "suppressed": 0, "sources": ["a"]},
            "medium": {"total": 2, "suppressed": 0, "sources": ["m1", "m2"]},
            "low": {"total": 3, "suppressed": 0, "sources": ["l1", "l2", "l3"]},
        },
        "notification": {"status": alerts.NOTIFY_NONE, "new_critical_high": 0, "sources": []},
    })
    assert "critical 1건[a]" in line
    assert "medium 2건" in line and "m1" not in line
    assert "low 3건" in line and "l1" not in line


def test_long_name_lists_say_how_many_were_cut():
    """잘린 줄이 '이게 전부'로 읽히면 안 된다 — 넘친 사실을 남긴다."""
    line = alerts.summary_line({
        "tier_summary": {"high": {"total": 8, "suppressed": 3,
                                  "sources": [f"s{i}" for i in range(8)]}},
        "notification": {"status": alerts.NOTIFY_NONE, "new_critical_high": 0},
    })
    assert "high 8건(억제 3)[s0·s1·s2·s3·s4·+3]" in line


def test_summary_line_still_works_without_source_names():
    """예전 모양의 결과 dict(이름 없음)로도 죽지 않아야 한다 — 이 줄은 사고
    조사용이고, 조사 도구가 입력 모양 때문에 터지면 조사가 멈춘다."""
    line = alerts.summary_line({
        "tier_summary": {"critical": {"total": 1, "suppressed": 0}},
        "notification": {"status": alerts.NOTIFY_SENT},
    })
    assert "critical 1건" in line
    assert "[" not in line


def test_tier_sources_count_the_same_set_as_total(isolated_db):
    """숫자와 이름이 같은 집합을 세야 한다 — 억제분을 빼면 "3건인데 이름 2개"가 된다."""
    candidates = [
        {"source": f"gai:x{i}", "label": f"후보{i}", "score": 95.0 - i * 0.1, "evidence": []}
        for i in range(4)                      # critical 캡은 3 → 1건이 억제된다
    ]
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=candidates), \
         patch("algorithms.alerts.notify_new_alerts", return_value=True), \
         patch("algorithms.alerts.telegram_configured", return_value=True):
        result = alerts.refresh_alerts("2026-09-20")

    crit = result["tier_summary"]["critical"]
    assert crit["total"] == 4 and crit["suppressed"] == 1
    assert len(crit["sources"]) == crit["total"]


def test_notification_names_what_actually_went_out(isolated_db):
    """전송된 대상이 결과에 실려야, 폰이 울린 이유를 나중에 되짚을 수 있다."""
    candidates = [{"source": "negative_space:local_news", "label": "보고 붕괴",
                   "score": 100.0, "evidence": []}]
    with patch("algorithms.alerts.collect_candidate_alerts", return_value=candidates), \
         patch("algorithms.alerts.notify_new_alerts", return_value=True), \
         patch("algorithms.alerts.telegram_configured", return_value=True):
        result = alerts.refresh_alerts("2026-09-20")

    assert result["notification"]["sources"] == ["negative_space:local_news"]
    assert "negative_space:local_news" in alerts.summary_line(result)

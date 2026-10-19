"""가끔만 성공하는 소스 — 두 그물을 **동시에** 빠져나가던 구멍 (2026-08-30).

## 사고
GroqWatch 는 08-30 UTC 02~16시 14주기 중 **성공 1회(7%)** 였다(12주기가
SearchContextTooLarge). 08-29 도 22주기 중 20주기 값없음(9%). 사실상 죽어 있었다.
**그런데 경보가 하나도 울리지 않았고 `정상 20/21` 로 집계됐다.**

## 왜 안 잡혔나 — 기존 장치 둘을 다 통과한다

    no_data 는 consecutive_failures 를 리셋한다     → failing 못 됨(연속 3회 필요)
    가끔 성공하면 last_success_at 이 갱신된다        → long_no_data 못 됨(72h 필요)
    healthy_count 는 no_data 를 아예 안 센다         → `정상 20/21` 로 보임

연속 카운팅으로는 이 모양을 못 잡는다. 그래서 **최근 창의 성공률**을 본다.

## 이 파일이 고정하는 것
1. 간헐 성공을 잡는다 (연속 카운팅이 못 하는 것)
2. ★ 창이 다 차기 전에는 판정하지 않는다 ★ — 배포 직후 거짓 경보 방지
3. flaky 는 degraded 이고 **울린다** — 보이기만 하고 안 울리면 지금과 똑같다
4. 정상 지연이 잦은 소스(위키)를 거짓 경보로 만들지 않는다
5. 회복하면 복구로 알린다

※ 2026-09-01 — 이 파일의 시험용 소스 이름을 GroqWatch → NewsWatch 로 바꿨다.
   아래 사고 기록은 실제 GroqWatch 이야기 그대로다. 다만 GroqWatch 는 그날
   은퇴했고(성공률 0%, NewsWatch 로 교대) 은퇴한 소스는 record_cycle 이 아예
   기록하지 않아 시험 픽스처로 쓸 수 없다. 지금 그 층에 있는 것이 NewsWatch 이므로
   **다음에 같은 모양이 생기면 잡힐 대상**으로 이름을 옮겼다.
"""
from __future__ import annotations

import pytest

from algorithms import source_health as sh


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sh, "HEALTH_FILE", tmp_path / "source_health.json")


def _run(source: str, pattern: list[str]):
    """pattern 의 각 원소대로 한 주기씩 기록. 'ok'|'no_data'|'fail'"""
    for outcome in pattern:
        sh.record_source_result(
            source, ok=(outcome == "ok"), no_data=(outcome == "no_data"),
            error=None if outcome != "fail" else "boom",
        )


def _row(source: str) -> dict:
    return next(s for s in sh.source_health_report()["sources"] if s["source"] == source)


# ── ★핵심★ GroqWatch 모양을 실제로 잡는다 ──────────────────────────

def test_mostly_no_data_with_occasional_success_is_caught():
    """★이 커밋의 이유★ 실측 7% 성공률이 `정상` 으로 집계되던 것.

    24주기 중 2회만 성공 — 연속실패는 계속 0 이고(no_data 라서),
    staleness 도 계속 리셋된다(가끔 성공하니까). 그런데도 잡혀야 한다.
    """
    pattern = ["ok" if i % 12 == 0 else "no_data" for i in range(sh.FLAKY_WINDOW)]
    _run("NewsWatch", pattern)

    row = _row("NewsWatch")
    assert row["status"] == "flaky", f"간헐 성공을 잡아야 한다: {row}"
    assert row["recent_success_rate"] == pytest.approx(2 / 24, abs=0.01)

    report = sh.source_health_report()
    assert "NewsWatch" in report["degraded_sources"], "flaky 는 degraded 다"
    assert any(f["source"] == "NewsWatch" for f in report["flaky_sources"])


def test_flaky_source_actually_alarms():
    """★보이기만 하고 안 울리면 지금까지와 똑같다★"""
    _run("NewsWatch", ["no_data"] * (sh.FLAKY_WINDOW - 1) + ["ok"])

    pending = sh.pending_notifications()
    assert any(d["source"] == "NewsWatch" and d["status"] == "flaky"
               for d in pending["degraded"])


def test_flaky_is_judged_before_no_data():
    """no_data 를 먼저 보면 간헐 소스는 이 상태에 영영 도달하지 못한다.

    간헐 소스는 **대부분의 주기가 no_data** 라, 판정 순서가 곧 이 기능의 생사다.
    """
    _run("NewsWatch", ["no_data"] * (sh.FLAKY_WINDOW - 1) + ["ok"])
    # 마지막 주기를 no_data 로 만들어도 flaky 로 잡혀야 한다
    sh.record_source_result("NewsWatch", ok=False, no_data=True)
    assert _row("NewsWatch")["status"] == "flaky"


# ── ★거짓 경보를 만들지 않는다★ ────────────────────────────────────

def test_partial_window_is_not_judged():
    """★배포 직후 몇 주기로 울리면 거짓 경보다★

    Railway 볼륨이 비어 있는 새 소스는 표본이 없다. 모른다고 해야 한다.
    """
    _run("NewSource", ["no_data"] * (sh.FLAKY_WINDOW - 1))

    row = _row("NewSource")
    assert row["status"] != "flaky", "창이 안 찼으면 판정하지 않는다"
    assert row["recent_success_rate"] is None
    assert row["recent_samples"] == sh.FLAKY_WINDOW - 1


def test_healthy_source_with_occasional_no_data_is_not_flaky():
    """위키 에볼라처럼 하루 두세 시간 '정상 지연'이 있는 소스는 건드리지 않는다.

    정상인 걸 계속 울리면 사람이 경보를 무시하게 되고, 그러면 진짜 사고를 놓친다.
    """
    pattern = ["no_data" if i < 3 else "ok" for i in range(sh.FLAKY_WINDOW)]
    _run("Wikipedia_Ebola", pattern)

    row = _row("Wikipedia_Ebola")
    assert row["status"] == "ok"
    assert row["recent_success_rate"] == pytest.approx(21 / 24, abs=0.01)


def test_window_only_looks_at_recent_cycles():
    """누적 총계로는 '지금 살아있나'를 알 수 없다 — 옛 이력이 오늘의 고장을 가린다."""
    _run("Src", ["ok"] * 50)                      # 과거엔 완벽했다
    _run("Src", ["no_data"] * sh.FLAKY_WINDOW)    # 그런데 지금은 죽었다

    assert _row("Src")["status"] == "flaky", "옛 성공이 오늘을 가리면 안 된다"


# ── 회복 ────────────────────────────────────────────────────────────

def test_recovery_is_reported():
    _run("NewsWatch", ["no_data"] * (sh.FLAKY_WINDOW - 1) + ["ok"])
    sh.mark_notified(["NewsWatch"])

    _run("NewsWatch", ["ok"] * sh.FLAKY_WINDOW)   # 되살아났다
    assert _row("NewsWatch")["status"] == "ok"
    assert "NewsWatch" in sh.pending_notifications()["recovered"]


def test_retired_source_is_still_excluded():
    """은퇴 소스가 flaky 로 되살아나 울리면 은퇴시킨 의미가 없다."""
    _run("Mobility", ["no_data"] * sh.FLAKY_WINDOW)

    report = sh.source_health_report()
    assert "Mobility" not in report["degraded_sources"]
    assert not any(f["source"] == "Mobility" for f in report["flaky_sources"])


# ── 회복 중 (2026-10-19) ────────────────────────────────────────────
# 운영 관측: Wikipedia_Ebola 가 12:00 부터 매시간 성공했는데 13:01 에
# `⚠️ 소스 중단: Wikipedia_Ebola (flaky, 연속 실패 0회)` 로그와 함께 텔레그램이
# '중단 · 1시간째 데이터 없음' 을 보냈다. 24주기 창은 회복을 하루 늦게 본다.

def _wiki_like_recovery():
    """하루 내내 실패하다가 최근 3주기 연속 성공 — 창 성공률은 아직 50% 미만."""
    _run("Wikipedia_Ebola", ["fail", "no_data"] * 10 + ["no_data"] + ["ok"] * 3)


def test_recent_success_streak_is_recovering_not_flaky():
    _wiki_like_recovery()
    row = _row("Wikipedia_Ebola")
    assert row["status"] == "recovering", row
    assert row["recent_success_rate"] < sh.FLAKY_SUCCESS_RATE, "창 성공률은 아직 낮다"
    report = sh.source_health_report()
    assert "Wikipedia_Ebola" not in report["degraded_sources"]
    assert report["healthy_count"] == 0, "회복 중은 정상으로 세지 않는다"
    assert report["recovering_sources"][0]["streak"] == sh.RECOVERY_STREAK


def test_recovering_source_is_not_renotified_as_down_and_recovery_is_sent_once():
    _run("Wikipedia_Ebola", ["no_data"] * sh.FLAKY_WINDOW)
    assert any(d["status"] == "flaky" for d in sh.pending_notifications()["degraded"])
    sh.mark_notified(["Wikipedia_Ebola"])
    _run("Wikipedia_Ebola", ["ok"] * sh.RECOVERY_STREAK)
    pending = sh.pending_notifications()
    assert pending["degraded"] == []
    assert pending["recovered"] == ["Wikipedia_Ebola"]
    assert pending["recovering"] == ["Wikipedia_Ebola"]
    sh.mark_notified(pending["recovered"])
    assert sh.pending_notifications() == {"degraded": [], "recovered": [], "recovering": []}, \
        "회복 통보는 한 번만"
    _run("Wikipedia_Ebola", ["ok"] * sh.FLAKY_WINDOW)          # 완전히 정상으로
    assert sh.pending_notifications()["recovered"] == [], "회복 중 → 정상은 다시 울리지 않는다"


def test_relapse_after_recovering_alarms_again():
    _run("Wikipedia_Ebola", ["no_data"] * sh.FLAKY_WINDOW)
    sh.mark_notified(["Wikipedia_Ebola"])
    _run("Wikipedia_Ebola", ["ok"] * sh.RECOVERY_STREAK)
    sh.mark_notified(sh.pending_notifications()["recovered"])
    _run("Wikipedia_Ebola", ["no_data"])                       # 다시 끊김
    assert [d["status"] for d in sh.pending_notifications()["degraded"]] == ["flaky"]


def test_two_successes_are_not_enough_to_call_recovery():
    _run("Wikipedia_Ebola", ["no_data"] * (sh.FLAKY_WINDOW - 2) + ["ok", "ok"])
    assert _row("Wikipedia_Ebola")["status"] == "flaky"


def test_flaky_message_says_success_rate_not_down():
    from algorithms.notifier import format_source_health_message
    msg = format_source_health_message({"degraded": [
        {"source": "Wikipedia_Ebola", "status": "flaky", "staleness_hours": 1.0,
         "consecutive_failures": 0, "recent_success_rate": 0.25, "window": 24},
        {"source": "KDCA", "status": "failing", "staleness_hours": 30.0,
         "consecutive_failures": 30, "recent_success_rate": 0.0, "window": 24},
    ], "recovered": ["NewsWatch"], "recovering": ["NewsWatch"]})
    wiki = next(line for line in msg.splitlines() if "Wikipedia_Ebola" in line)
    assert "간헐 성공" in wiki and "성공률 25%" in wiki and "마지막 성공 1시간 전" in wiki
    assert "중단" not in wiki and "데이터 없음" not in wiki, "한 시간 전에 성공한 소스를 중단이라 하지 않는다"
    kdca = next(line for line in msg.splitlines() if "KDCA" in line)
    assert "중단" in kdca and "1.2일째" in kdca and "연속 실패 30회" in kdca
    assert "2개 이상" in msg and "NewsWatch (회복 중" in msg


def test_baikal_huginn_reads_recovering_as_note_not_problem():
    from algorithms import baikal
    health = {"total_tracked": 23, "healthy_count": 22, "collector_silent_hours": 0.1,
              "sources": [{"source": "Wikipedia_Ebola", "status": "recovering"}],
              "long_no_data_sources": []}
    res = baikal.judge_huginn(health, {"invariants": []})
    assert res["status"] == "ok" and "회복 중 Wikipedia_Ebola" in res["reason"]

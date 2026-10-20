"""매시 주기 결손·멈춤을 스스로 말하게 한다 (2026-10-20, 소킹 10-19 22시 결손 — 원인 판정 못 함).

고정하는 것: ① 직전 완료와 지금 사이의 빈 정시 슬롯만 결손으로 센다(지금 슬롯·배포 재시작으로 같은
시간에 두 번 돈 것은 결손 아님) ② 장부가 없으면 모른다고 하고 말하지 않는다 ③ 장부는 볼륨(data/)에
쓴다 ④ 멈춤 감시는 기준 시간을 넘긴 단계에서만 `⏳` 와 호출 위치를 찍고, 단계를 끊지 않는다
⑤ 스케줄러의 매시 세 단계가 감시 아래에서 돈다.
"""
from __future__ import annotations

import asyncio
import ast
import datetime as dt
import inspect

from algorithms import cycle_watch as cw

UTC = dt.timezone.utc


def _t(day, hour, minute=0):
    return dt.datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_the_22h_hole_is_named():
    missed = cw.missed_slots(_t(19, 21, 1), _t(19, 23, 1))
    assert missed == [_t(19, 22)]
    line = cw.gap_line(missed, _t(19, 21, 1))
    assert line.startswith("⚠ 경보 주기 결손: 10-19 22시 슬롯 완료 기록 없음") and "21:01" in line


def test_no_gap_for_consecutive_hours_or_a_restart_within_the_hour():
    assert cw.missed_slots(_t(19, 21, 1), _t(19, 22, 1)) == []
    assert cw.missed_slots(_t(19, 17, 51), _t(19, 18, 2)) == []
    assert cw.missed_slots(None, _t(19, 22, 1)) == []
    assert cw.gap_line([], _t(19, 21)) is None


def test_long_outage_lists_a_few_and_counts_the_rest():
    missed = cw.missed_slots(_t(19, 0, 1), _t(19, 12, 1))
    line = cw.gap_line(missed, _t(19, 0, 1))
    assert len(missed) == 11 and f"외 {11 - cw.MAX_SLOTS_NAMED}개" in line


def test_ledger_round_trip_and_unreadable_file(tmp_path):
    path = tmp_path / "last_alert_cycle.json"
    assert cw.load_last_done(path) is None
    cw.save_done(path, _t(19, 21, 1))
    assert cw.load_last_done(path) == _t(19, 21, 1)
    path.write_text("not json")
    assert cw.load_last_done(path) is None


def test_ledger_lives_on_the_volume():
    import main
    assert main._ALERT_CYCLE_FILE.parent.name == "data"


def test_stall_watch_reports_only_slow_steps(monkeypatch, capsys):
    import main
    monkeypatch.setattr(cw, "STALL_WARN_SECONDS", 0.05)

    async def slow():
        await asyncio.sleep(0.15)

    async def fast():
        return None

    asyncio.run(main._watched("경보 주기", fast()))
    assert "⏳" not in capsys.readouterr().out
    asyncio.run(main._watched("경보 주기", slow()))
    out = capsys.readouterr().out
    assert "⏳ 경보 주기 0분째 안 끝남" in out and "⏳ 경보 주기 끝남" in out
    assert "호출 위치" in out


def test_thread_stacks_names_our_frames():
    text = cw.thread_stacks()
    assert "test_cycle_watch.py" in text or "(우리 코드를 지나는 스레드 없음)" in text


def test_scheduler_hourly_steps_are_watched():
    import main
    tree = ast.parse(inspect.getsource(main._scheduler_loop))
    watched = [c.args[0].value for c in ast.walk(tree)
               if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "_watched"]
    assert watched.count("경보 주기") == 2 and watched.count("BAIKAL") == 2 and watched.count("무료 수집") == 2


def test_alert_cycle_writes_the_ledger_after_the_summary_line():
    import main
    src = inspect.getsource(main._run_alert_cycle)
    assert src.index("🚨 경보 주기") < src.index("save_done(_ALERT_CYCLE_FILE")
    assert src.index("gap_line(") < src.index("asyncio.to_thread(refresh_alerts)")

"""AI 갭필링 슬롯이 하루를 통째로 건너뛰지 않는지 (2026-08-23).

실제 사고: 2026-08-22에 AI 갭필링·불리틴·나우캐스트 백필이 통째로 빠졌다.
에러는 한 줄도 안 났다. 원인 두 가지가 겹쳤다 —

① 슬롯 조건이 `now.hour == _AI_HOUR_UTC`(정확일치)라 한 틱을 놓치면 따라잡을
   방법이 없었다. 21:54 배포가 21:58 틱을 4분 앞두고 컨테이너를 죽였고,
   재시작 후 다음 틱은 23시였다.
② 루프가 `sleep(3600)` **뒤에** 수집을 돌려서 수집 시간(45~60초)이 매 주기
   누적됐다. 하루 약 20분씩 밀리고, 2.5~3.3일마다 한 시간 슬롯이 통째로
   사라진다. 그 시간이 21시면 그날 AI 수집이 조용히 없어진다.

여기 테스트는 두 결함이 다시 들어오지 못하게 고정한다."""
from __future__ import annotations
import datetime as dt
import json

import main


def test_ai_slot_allows_catch_up_after_missed_tick():
    """★핵심★ 21시 틱을 놓쳐도 23시에 따라잡을 수 있어야 한다."""
    # 주석에도 '예전엔 ==였다'는 설명이 들어 있으므로, 주석을 뺀 실제 코드만 본다.
    code = "\n".join(
        ln for ln in _scheduler_source().splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "now.hour >= _AI_HOUR_UTC" in code, "정확일치(==)로 되돌아갔다 — 놓치면 못 따라잡는다"
    assert "now.hour == _AI_HOUR_UTC" not in code


def test_loop_sleeps_to_the_next_hour_not_a_fixed_3600():
    """수집 시간이 누적되면 슬롯이 통째로 밀려 사라진다."""
    src = _scheduler_source()
    assert "replace(minute=0, second=0, microsecond=0)" in src, "정시 정렬이 사라졌다"
    assert "await asyncio.sleep(_FREE_INTERVAL_SEC)" not in src, "고정 sleep으로 되돌아갔다"


def _scheduler_source() -> str:
    import inspect
    return inspect.getsource(main._scheduler_loop)


def test_hour_aligned_sleep_never_accumulates_drift():
    """정시 정렬이면 몇 바퀴를 돌아도 분 단위가 밀리지 않는다."""
    now = dt.datetime(2026, 8, 22, 21, 38, 12, tzinfo=dt.timezone.utc)
    for _ in range(48):                      # 이틀치
        nxt = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait = max(60.0, (nxt - now).total_seconds())
        now = now + dt.timedelta(seconds=wait) + dt.timedelta(seconds=55)   # 수집 55초
        assert now.minute == 0, f"{now}에서 정시를 벗어났다"
    # 이틀 뒤에도 여전히 정시 근처 — 예전 방식이면 약 44분 밀려 있었을 것
    assert now.minute == 0


def test_ai_run_date_survives_restart(tmp_path, monkeypatch):
    """★비용★ 메모리 변수만 쓰면 재배포마다 초기화돼 유료 AI가 하루 두 번 돈다."""
    state = tmp_path / "last_ai_run.json"
    monkeypatch.setattr(main, "_AI_STATE_FILE", state)

    assert main._load_last_ai_run() is None          # 아직 기록 없음
    main._save_last_ai_run(dt.date(2026, 8, 23))
    assert main._load_last_ai_run() == dt.date(2026, 8, 23)   # 재시작해도 남는다
    assert json.loads(state.read_text())["last_run_date"] == "2026-08-23"


def test_corrupt_ai_state_is_treated_as_no_record(tmp_path, monkeypatch):
    """상태 파일이 깨졌으면 '오늘 이미 돌았다'고 단정하면 안 된다 — 그럼 영영 안 돈다."""
    state = tmp_path / "last_ai_run.json"
    monkeypatch.setattr(main, "_AI_STATE_FILE", state)
    for bad in ("", "{}", "not json", '{"last_run_date": "어제"}'):
        state.write_text(bad, encoding="utf-8")
        assert main._load_last_ai_run() is None


def test_save_failure_is_logged_not_swallowed(tmp_path, monkeypatch):
    """저장 실패를 조용히 넘기면 다음 틱에 또 돌아 유료 AI가 중복 호출된다."""
    logged = []
    monkeypatch.setattr(main, "_AI_STATE_FILE", tmp_path / "nodir" / "x.json")
    monkeypatch.setattr(main, "_log_error", lambda m: logged.append(m))
    monkeypatch.setattr(main.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("readonly")))
    main._save_last_ai_run(dt.date(2026, 8, 23))
    assert logged and "AI 실행일 저장 실패" in logged[0]

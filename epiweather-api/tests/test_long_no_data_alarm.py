"""값없음이 며칠씩 이어지면 경보를 울린다 (2026-08-25).

`no_data` 는 원래 텔레그램 경보에서 **일부러 뺐다.** 위키 404 지연·OpenSky 차단처럼
'정상이거나 이미 아는 조건'이 대부분이라 매일 울리면 경보 피로만 쌓이기 때문이다.
그 판단 자체는 옳았다.

그런데 그 예외가 구멍이 됐다. 실측(2026-08-25 `/api/status`):

    Mobility  status=no_data  staleness_hours=190.1   ← 8일
    degraded_sources: []                              ← 비어 있음
    healthy_count: 20 / 21                            ← no_data 를 아예 안 셈

**소스가 8일을 죽어 있었는데 아무 데서도 울리지 않았다.**
GroqWatch 는 시끄럽게 실패해서 잡혔지만, 이건 조용해서 아무도 몰랐다.

이 테스트가 고정하는 선:
    **짧은 값없음은 조용하다(경보 피로 방지). 사흘을 넘기면 그건 지연이 아니라 죽음이다.**

※ 2026-09-01 — 이 파일의 시험용 소스 이름을 GroqWatch → NewsWatch 로 바꿨다.
   아래 사고 기록은 실제 GroqWatch 이야기 그대로다. 다만 GroqWatch 는 그날
   은퇴했고(성공률 0%, NewsWatch 로 교대) 은퇴한 소스는 record_cycle 이 아예
   기록하지 않아 시험 픽스처로 쓸 수 없다. 지금 그 층에 있는 것이 NewsWatch 이므로
   **다음에 같은 모양이 생기면 잡힐 대상**으로 이름을 옮겼다.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from algorithms import source_health as sh


@pytest.fixture
def health_file(tmp_path, monkeypatch):
    """헬스 파일을 임시 경로로 돌려 실제 운영 데이터를 건드리지 않는다."""
    path = tmp_path / "source_health.json"
    monkeypatch.setattr(sh, "HEALTH_FILE", path)
    return path


def _write(path, entries: dict):
    path.write_text(json.dumps(entries), encoding="utf-8")


def _hours_ago(h: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=h)).isoformat()


def _no_data_entry(hours: float, notified: str | None = None) -> dict:
    entry = {
        "last_outcome": "no_data",
        "last_success_at": _hours_ago(hours),
        "last_no_data_at": _hours_ago(0.1),
        "consecutive_failures": 0,
    }
    if notified:
        entry["notified_status"] = notified
        entry["last_notified_at"] = _hours_ago(0.1)
    return entry


# ─────────────────────────────────────────────────────────────────────────────

def test_short_no_data_stays_quiet(health_file):
    """★경보 피로 방지★ 몇 시간짜리 값없음은 울리지 않는다 — 원래 설계 그대로."""
    _write(health_file, {"Wikipedia_Ebola": _no_data_entry(5)})

    report = sh.source_health_report()
    pending = sh.pending_notifications()

    assert report["no_data_sources"] == ["Wikipedia_Ebola"]
    assert report["long_no_data_sources"] == []     # 아직 아니다
    assert pending["degraded"] == []                # 조용하다


def test_multi_day_no_data_raises_the_alarm(health_file):
    """★핵심★ 사흘을 넘기면 '아는 조건'이 아니라 죽은 것이다 — 울려야 한다."""
    # 이 결함을 드러낸 실측 사례는 Mobility(190.1시간)였다. Mobility 는
    # 2026-08-28 에 추적에서 정식 제외됐으므로(RETIRED_SOURCES), 예시는 살아있는
    # 소스로 바꾼다 — 은퇴한 이름을 쓰면 필터에 걸려 **아무것도 검사하지 않는다.**
    _write(health_file, {"NewsWatch": _no_data_entry(190.1)})

    report = sh.source_health_report()
    pending = sh.pending_notifications()

    assert report["no_data_sources"] == ["NewsWatch"]
    assert [x["source"] for x in report["long_no_data_sources"]] == ["NewsWatch"]
    # 예전에는 여기가 비어 있어서 8일 동안 아무도 몰랐다
    assert [x["source"] for x in pending["degraded"]] == ["NewsWatch"]


def test_threshold_boundary(health_file):
    """경계에서 뒤집히는지 — 71시간은 조용, 73시간은 경보."""
    _write(health_file, {"A": _no_data_entry(71), "B": _no_data_entry(73)})

    long_names = [x["source"] for x in sh.source_health_report()["long_no_data_sources"]]

    assert "A" not in long_names
    assert "B" in long_names


def test_alarm_does_not_repeat_within_renotify_window(health_file):
    """★경보 피로 방지★ 이미 알린 건 24시간 안에 다시 울리지 않는다."""
    # ⚠️ 여기에 은퇴한 소스명을 쓰면 degraded 가 무조건 비어서 **테스트가 통과하되
    # 아무것도 검사하지 않는다**(2026-08-28 에 실제로 그럴 뻔했다). 살아있는 소스로.
    _write(health_file, {"NewsWatch": _no_data_entry(190, notified="no_data")})

    pending = sh.pending_notifications()

    assert pending["degraded"] == []   # 방금 알렸으니 조용


def test_recovery_is_announced_after_long_no_data(health_file):
    """죽었다고 알린 소스가 살아나면 살아났다고도 말해야 한다."""
    _write(health_file, {
        "NewsWatch": {
            "last_outcome": "ok",
            "last_success_at": _hours_ago(0.5),
            "consecutive_failures": 0,
            "notified_status": "no_data",
            "last_notified_at": _hours_ago(2),
        }
    })

    pending = sh.pending_notifications()

    assert pending["recovered"] == ["NewsWatch"]


def test_failing_sources_still_behave_as_before(health_file):
    """고치면서 원래 경보(연속 실패)를 깨지 않았는지."""
    _write(health_file, {
        "NewsWatch": {
            "last_outcome": "failure",
            "last_success_at": _hours_ago(3),
            "consecutive_failures": 3,
        }
    })

    report = sh.source_health_report()
    pending = sh.pending_notifications()

    assert report["degraded_sources"] == ["NewsWatch"]
    assert [x["source"] for x in pending["degraded"]] == ["NewsWatch"]


def test_healthy_source_is_not_dragged_in(health_file):
    """정상 소스가 새 규칙에 걸려들지 않는지."""
    _write(health_file, {
        "KDCA": {
            "last_outcome": "ok",
            "last_success_at": _hours_ago(0.5),
            "consecutive_failures": 0,
        }
    })

    report = sh.source_health_report()

    assert report["healthy_count"] == 1
    assert report["long_no_data_sources"] == []
    assert sh.pending_notifications()["degraded"] == []

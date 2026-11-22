"""값없음이 며칠씩 이어지면 경보를 울린다 (2026-08-25).

`no_data` 는 원래 경보에서 **일부러 뺐다.** 위키 404 지연·OpenSky 차단처럼
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

    assert report["no_data_sources"] == ["Wikipedia_Ebola"]
    assert report["long_no_data_sources"] == []     # 아직 아니다


def test_multi_day_no_data_raises_the_alarm(health_file):
    """★핵심★ 사흘을 넘기면 '아는 조건'이 아니라 죽은 것이다 — 울려야 한다."""
    # 이 결함을 드러낸 실측 사례는 Mobility(190.1시간)였다.
    _write(health_file, {"NewsWatch": _no_data_entry(190.1)})

    report = sh.source_health_report()

    assert report["no_data_sources"] == ["NewsWatch"]
    assert [x["source"] for x in report["long_no_data_sources"]] == ["NewsWatch"]


def test_threshold_boundary(health_file):
    """경계에서 뒤집히는지 — 71시간은 조용, 73시간은 경보."""
    _write(health_file, {"A": _no_data_entry(71), "B": _no_data_entry(73)})

    long_names = [x["source"] for x in sh.source_health_report()["long_no_data_sources"]]

    assert "A" not in long_names
    assert "B" in long_names



"""추적에서 정식으로 뺀 소스는 조용히 사라지지도, 영영 울지도 않는다 (2026-08-28).

Mobility(OpenSky)를 21개 추적 목록에서 뺐다. 근거는 실측이다 — 연결 타임아웃을
3초에서 10초로 올려도 동일하게 ConnectTimeout 이 났다(auth.opensky-network.org:443).
403 이 아니라 무응답이므로 정책적 IP 차단이 아니라 경로/방화벽 문제이고,
우리 쪽에서 고칠 수 없다.

★ 이 테스트가 존재하는 진짜 이유 — 그냥 지웠으면 지금보다 나빠졌다 ★

`total_tracked` 는 collector 의 FREE_SOURCE_HEALTH_KEYS 가 아니라
**source_health.json 파일의 항목 수**다(`len(sources)`). 그 파일은 Railway
볼륨에 있어 배포해도 남는다. 그래서 수집 맵에서 이름만 지우면:

  - record_cycle 이 갱신을 멈춘다
  - last_success_at 이 **영원히 멈춘 채** staleness_hours 만 계속 증가한다
  - long_no_data 경보가 **영영 울리는데 회복될 수조차 없다**

즉 "빼는" 가장 자연스러운 방법이 가장 나쁜 결과를 낸다. 그래서 명시적
RETIRED_SOURCES 장치를 두고, 그 성질을 여기서 고정한다.

동시에 반대 방향의 실패도 막는다: **뺐다고 안 보이면 안 된다.** 조용히 사라진
소스는 이 시스템에서 가장 위험한 실패 방식이라, retired_sources 로 이유와 함께
계속 드러나야 한다.
"""
from __future__ import annotations

import json
import pytest

from algorithms import source_health as sh


@pytest.fixture
def health_file(tmp_path, monkeypatch):
    f = tmp_path / "source_health.json"
    monkeypatch.setattr(sh, "HEALTH_FILE", f)
    return f


def _write(health_file, data: dict):
    health_file.write_text(json.dumps(data), encoding="utf-8")


def _stale_no_data_entry(hours: float) -> dict:
    """값없음 상태로 `hours` 시간 묵은 항목 — 경보 임계(72h)를 넘긴 모양."""
    import datetime as dt
    old = (sh._now() - dt.timedelta(hours=hours)).isoformat()
    return {
        "last_success_at": old, "last_failure_at": None,
        "last_no_data_at": sh._now().isoformat(), "last_outcome": "no_data",
        "consecutive_failures": 0, "total_successes": 1, "total_failures": 0,
    }


# ── 뺀 소스는 집계·경보에서 빠진다 ────────────────────────────────

def test_retired_source_is_excluded_from_counts(health_file):
    """★핵심★ 뺀 소스는 total_tracked 에도 sources 목록에도 안 들어간다."""
    _write(health_file, {
        "Mobility": _stale_no_data_entry(257),
        "KDCA": {"last_success_at": sh._now().isoformat(), "last_outcome": "ok",
                 "consecutive_failures": 0},
    })
    rep = sh.source_health_report()

    assert rep["total_tracked"] == 1, "Mobility 는 세지 않는다"
    assert [s["source"] for s in rep["sources"]] == ["KDCA"]
    assert rep["healthy_count"] == 1


def test_retired_source_never_alarms_even_when_ancient(health_file):
    """★가장 중요★ 파일에 남은 옛 항목이 영영 울리면 안 된다.

    그냥 지웠을 때의 함정이 정확히 이것이다 — staleness 만 계속 늘어나는데
    아무도 갱신하지 않으니 경보가 멈추지 않고, 회복될 수조차 없다.
    """
    _write(health_file, {"Mobility": _stale_no_data_entry(257)})

    rep = sh.source_health_report()
    assert rep["no_data_sources"] == []
    assert rep["long_no_data_sources"] == [], "257시간이어도 울리지 않는다"
    assert rep["degraded_sources"] == []

    pending = sh.pending_notifications()
    assert pending["degraded"] == []
    assert pending["recovered"] == []


def test_retired_source_is_not_recorded_by_record_cycle(health_file):
    """기록 자체를 안 한다 — 기록하면 값이 안 오는 게 당연한데도 계속 쌓인다."""
    result = {"kdca_weekly": {"x": 1}, "mobility": None}
    sh.record_cycle(result, {"KDCA": "kdca_weekly", "Mobility": "mobility"})

    data = json.loads(health_file.read_text(encoding="utf-8"))
    assert "KDCA" in data
    assert "Mobility" not in data, "뺀 소스는 파일에 새로 만들지도 않는다"


# ── 그런데 숨기지는 않는다 ────────────────────────────────────────

def test_retired_sources_stay_visible_with_a_reason(health_file):
    """★반대 방향의 실패를 막는다★ 조용히 사라지는 게 이 시스템 최악의 실패다.

    집계에서는 빼되 목록에는 이유와 함께 남아야 한다. 안 그러면 6개월 뒤에
    "원래 20개였나?" 가 되고, 뺀 근거도 되살릴 방법도 사라진다.
    """
    _write(health_file, {"KDCA": {"last_success_at": sh._now().isoformat(),
                                  "last_outcome": "ok", "consecutive_failures": 0}})
    rep = sh.source_health_report()

    retired = {r["source"]: r["reason"] for r in rep["retired_sources"]}
    assert "Mobility" in retired
    reason = retired["Mobility"]
    assert "ConnectTimeout" in reason, "왜 뺐는지가 남아야 한다"
    assert "2026-08-28" in reason, "언제 뺐는지가 남아야 한다"
    assert "/api/mobility" in reason, "어떻게 되살리는지가 남아야 한다"


def test_retired_list_is_reported_even_with_no_history(health_file):
    """헬스 파일이 비어 있어도(새 볼륨) 뺀 목록은 그대로 보인다."""
    _write(health_file, {})
    rep = sh.source_health_report()
    assert [r["source"] for r in rep["retired_sources"]] == ["Mobility"]


# ── 되살리기가 한 줄이어야 한다 ───────────────────────────────────

def test_un_retiring_restores_normal_tracking(health_file, monkeypatch):
    """RETIRED_SOURCES 에서 지우면 곧바로 예전처럼 추적된다 — 코드는 그대로다."""
    monkeypatch.setattr(sh, "RETIRED_SOURCES", {})

    result = {"mobility": {"mobility_airports_ok": 11, "mobility_total_flights": 22}}
    sh.record_cycle(result, {"Mobility": "mobility"})

    rep = sh.source_health_report()
    assert rep["total_tracked"] == 1
    assert rep["healthy_count"] == 1
    assert rep["retired_sources"] == []


def test_only_the_named_source_is_retired(health_file):
    """다른 소스는 영향받지 않는다 — 은퇴가 전역 스위치가 되면 안 된다."""
    assert sh.is_retired("Mobility") is True
    for other in ("KDCA", "GroqWatch", "Wikipedia_Ebola", "WHO_AFRO"):
        assert sh.is_retired(other) is False, other


# ── 수집기가 실제로 호출을 건너뛰는가 ─────────────────────────────

def test_collector_guards_the_mobility_call_with_is_retired():
    """★비용 근거★ 닿지 않는 곳에 매 주기 20초를 버리지 않는다.

    연결 타임아웃 10초 × 2회(토큰 + 첫 공항) = 주기당 20초, 하루 8분. 게다가
    뒤에 오는 소스가 전부 그만큼 밀린다. 그래서 은퇴한 소스는 호출 자체를 건너뛴다.

    이 테스트가 잡으려는 실패는 **누군가 그 가드를 지우는 것**이다. 가드가
    사라지면 조용히 20초씩 다시 버리기 시작하는데, 테스트도 로그도 안 깨져서
    아무도 모른다. 그래서 호출부 코드에 가드가 실제로 있는지를 본다.
    """
    import inspect
    import collector

    src = inspect.getsource(collector.collect_free_sources)
    mobility_block = src[src.index("이동성(OpenSky)") - 2000:src.index("이동성(OpenSky)")]
    assert 'is_retired("Mobility")' in mobility_block, (
        "collect_free_sources 의 Mobility 호출 앞에 is_retired 가드가 있어야 한다"
    )
    # 가드가 get_mobility_score() 호출보다 먼저 와야 의미가 있다.
    assert src.index('is_retired("Mobility")') < src.index("get_mobility_score()")

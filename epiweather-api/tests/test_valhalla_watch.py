"""발할라가 **쌓이는지**, 그리고 굳은 값을 새 값인 척하지 않는지 (2026-09-03).

## 왜 만들었나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해!"* → 점검해보니 **아무것도 안
쌓이고 있었다.** 수집기가 발할라를 도는 횟수 0회. 부를 때만 계산됐다.
극지 관찰층이 2026-09-01 에 겪은 것과 똑같은 문제였다.

## ★ 이 파일이 지키는 두 가지 ★

**1. 무거운 조각을 안 돌린 주기가 '값없음' 이 되지 않는 것.** 조달은 나라장터를
66번 부르느라 47초가 걸려서 매시간 돌릴 수 없다. 그런데 하루 한 번만 돌리면
나머지 23주기가 값없음으로 쌓여 소스 헬스에 거짓 경보가 뜬다. 그래서 가벼운
조각(로컬 계산)이 매 주기 키를 채운다.

**2. 굳은 값을 새 값처럼 내지 않는 것.** 갱신에 실패하면 지난 값을 쓰되
`refreshed=False` 와 사유를 남기고, `age_hours` 가 계속 자라게 둔다.
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import valhalla_watch as vw


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """상태 파일을 임시 폴더로 옮긴다 — 실제 수집 상태를 건드리지 않는다."""
    monkeypatch.setattr(vw, "STATE_FILE", tmp_path / "valhalla_state.json")
    return tmp_path


@pytest.fixture
def no_network(monkeypatch):
    """무거운 조각을 가짜로 — 테스트가 나라장터를 부르면 안 된다."""
    calls = {"procurement": 0, "pipeline": 0}

    def proc():
        calls["procurement"] += 1
        return {"bid_count": 30, "excluded_count": 5,
                "categories": ["감염병 감시·대응"], "notice_nos": ["A1"]}

    def pipe():
        calls["pipeline"] += 1
        return {"stages": {"에볼라": "stockpiled"}, "lookup_failed": 0}

    monkeypatch.setattr(vw, "_fetch_procurement", proc)
    monkeypatch.setattr(vw, "_fetch_pipeline", pipe)
    return calls


# ── 쌓인다 ────────────────────────────────────────────────────────────────

def test_first_cycle_fetches_and_stores(isolated, no_network):
    """첫 주기엔 받아서 저장한다."""
    out = vw.valhalla_snapshot()

    assert out["procurement"]["refreshed"] is True
    assert out["procurement"]["value"]["bid_count"] == 30
    assert no_network["procurement"] == 1
    assert vw.STATE_FILE.exists(), "다음 주기가 읽을 파일이 안 생겼다"


def test_second_cycle_reuses_instead_of_refetching(isolated, no_network):
    """★★핵심★★ 주기 전이면 다시 안 받는다.

    매시간 나라장터를 66번씩 부르면 하루 1,584회다. 값은 하루 단위로 바뀌는데.
    """
    vw.valhalla_snapshot()
    out = vw.valhalla_snapshot()

    assert no_network["procurement"] == 1, "주기 전인데 또 받았다"
    assert out["procurement"]["refreshed"] is False
    assert out["procurement"]["reason"] == "갱신 주기 전"
    assert out["procurement"]["value"]["bid_count"] == 30, "재사용값이 비었다"


def test_refetches_once_the_interval_passes(isolated, no_network):
    """주기가 지나면 새로 받는다."""
    start = dt.datetime(2026, 9, 3, 0, 0, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    later = start + dt.timedelta(hours=vw.PROCUREMENT_EVERY_HOURS)
    out = vw.valhalla_snapshot(now=later)

    assert out["procurement"]["refreshed"] is True
    assert no_network["procurement"] == 2


def test_heavy_parts_have_different_intervals(isolated, no_network):
    """★핵심★ 조달과 임상은 변하는 속도가 다르다 — 주기도 달라야 한다."""
    start = dt.datetime(2026, 9, 3, 0, 0, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    out = vw.valhalla_snapshot(now=start + dt.timedelta(hours=7))

    assert out["procurement"]["refreshed"] is True, "6시간 주기가 안 돌았다"
    assert out["pipeline"]["refreshed"] is False, "24시간짜리를 7시간만에 받았다"
    assert vw.PIPELINE_EVERY_HOURS > vw.PROCUREMENT_EVERY_HOURS


# ── 굳은 값을 새 값인 척하지 않는다 ────────────────────────────────────────

def test_fetch_failure_keeps_the_old_value_but_says_so(isolated, no_network,
                                                       monkeypatch):
    """★★핵심★★ 갱신 실패를 조용히 넘기지 않는다 — 사유와 나이를 남긴다."""
    start = dt.datetime(2026, 9, 3, 0, 0, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    def boom():
        raise ConnectionError("나라장터 안 됨")
    monkeypatch.setattr(vw, "_fetch_procurement", boom)

    later = start + dt.timedelta(hours=8)
    out = vw.valhalla_snapshot(now=later)

    assert out["procurement"]["refreshed"] is False
    assert "ConnectionError" in out["procurement"]["reason"]
    assert out["procurement"]["value"]["bid_count"] == 30, "실패했다고 값을 버렸다"
    assert out["procurement"]["age_hours"] == 8.0, "나이가 안 자란다"


def test_age_keeps_growing_while_refresh_keeps_failing(isolated, monkeypatch):
    """★핵심★ 계속 실패하면 나이가 계속 자라서 눈에 보인다."""
    def boom():
        raise TimeoutError("느림")
    monkeypatch.setattr(vw, "_fetch_procurement", lambda: {"bid_count": 1,
                        "excluded_count": 0, "categories": [], "notice_nos": []})
    monkeypatch.setattr(vw, "_fetch_pipeline", lambda: {"stages": {}, "lookup_failed": 0})
    start = dt.datetime(2026, 9, 3, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    monkeypatch.setattr(vw, "_fetch_procurement", boom)
    ages = [vw.valhalla_snapshot(now=start + dt.timedelta(hours=h))["procurement"]["age_hours"]
            for h in (7, 20, 50)]

    assert ages == [7.0, 20.0, 50.0]
    assert ages == sorted(ages), "굳은 값이 계속 새 값처럼 보인다"


def test_broken_state_file_does_not_kill_the_layer(isolated, no_network):
    """상태 파일이 깨져도 층이 죽지 않는다 — 다음 주기에 다시 쌓인다."""
    vw.STATE_FILE.write_text("{깨진 json", encoding="utf-8")

    out = vw.valhalla_snapshot()

    assert out["procurement"]["refreshed"] is True


# ── 가벼운 조각은 매 주기 채운다 ───────────────────────────────────────────

def test_light_layers_fill_every_cycle(isolated, no_network):
    """★★핵심★★ 무거운 걸 안 돌린 주기에도 키가 비지 않는다.

    비면 소스 헬스가 값없음으로 세고, 6시간 주기가 곧 거짓 경보가 된다.
    """
    vw.valhalla_snapshot()
    out = vw.valhalla_snapshot()          # 주기 전 — 무거운 건 안 받는다

    assert "vaccine_chokepoints" in out and "readiness" in out
    assert out["vaccine_chokepoints"].get("single_source_count") is not None
    assert out["collected_at"]


def test_never_stores_illustrative_readiness(isolated, no_network, monkeypatch):
    """★★핵심★★ 등록된 대응제가 없을 때 시연값을 쌓지 않는다.

    쌓으면 시계열에 가짜 값이 섞이고, 나중에 그 구간이 진짜처럼 읽힌다.
    """
    import db as _db
    monkeypatch.setattr(_db, "list_countermeasures", lambda *a, **k: [])

    readiness = vw.valhalla_snapshot()["readiness"]

    assert "error" in readiness
    assert "시연값을 쌓지 않는다" in readiness["error"]
    assert "coverage_rate" not in readiness


def test_it_is_a_watch_layer_not_an_alert_layer(isolated, no_network):
    """★핵심★ 관찰층이다 — 여기서 경보를 울리지 않는다."""
    out = vw.valhalla_snapshot()

    assert out["watch_grade"] is True
    for banned in ("alert", "grade", "severity", "score"):
        assert banned not in out, f"경보처럼 보이는 키: {banned}"


# ── 수집기·엔드포인트 배선 ─────────────────────────────────────────────────

def test_collector_registers_valhalla_for_source_health():
    """★핵심★ 소스 헬스에 등록돼야 이 층이 죽었을 때 보인다."""
    from collector import FREE_SOURCE_HEALTH_KEYS

    assert FREE_SOURCE_HEALTH_KEYS.get("Valhalla") == "valhalla"


def test_endpoint_serves_stored_state_without_refetching(isolated, no_network):
    """★핵심★ 엔드포인트는 쌓인 걸 읽기만 한다 — 47초짜리 조회를 다시 하지 않는다."""
    from fastapi.testclient import TestClient
    import main

    vw.valhalla_snapshot()
    body = TestClient(main.app).get("/api/biodefense/valhalla").json()

    assert body["available"] is True
    assert body["parts"]["procurement"]["value"]["bid_count"] == 30
    assert no_network["procurement"] == 1, "엔드포인트가 다시 받았다"


def test_endpoint_says_when_nothing_has_been_collected_yet(isolated):
    """★핵심★ 아직 안 쌓인 것을 '값 없음' 으로 말하지 않는다."""
    from fastapi.testclient import TestClient
    import main

    body = TestClient(main.app).get("/api/biodefense/valhalla").json()

    assert body["available"] is False
    assert "한 번도 돌리지 않았다" in body["reason"]

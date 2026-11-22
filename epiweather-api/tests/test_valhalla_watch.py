"""발할라가 **쌓이는지**, 그리고 굳은 값을 새 값인 척하지 않는지 (2026-09-03).

## 왜 만들었나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해!"* → 점검해보니 **아무것도 안
쌓이고 있었다.** 수집기가 발할라를 도는 횟수 0회. 부를 때만 계산됐다.
극지 관찰층이 2026-09-01 에 겪은 것과 똑같은 문제였다.

## ★ 이 파일이 지키는 두 가지 ★

**1. 무거운 조각을 안 돌린 주기가 '값없음' 이 되지 않는 것.** 임상 파이프라인은
ClinicalTrials 를 17번 불러서 매시간 돌릴 수 없다(조달은 개편 2차에서 뺐다). 그런데 하루 한 번만 돌리면
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
    """무거운 조각을 가짜로 — 테스트가 ClinicalTrials 를 부르면 안 된다.
    (조달은 2026-11-22 개편 2차에서 뺐다 — 남은 무거운 조각은 임상 파이프라인 하나.)"""
    calls = {"pipeline": 0}

    def pipe():
        calls["pipeline"] += 1
        return {"stages": {"에볼라": "stockpiled"}, "lookup_failed": 0}

    monkeypatch.setattr(vw, "_fetch_pipeline", pipe)
    return calls


# ── 쌓인다 ────────────────────────────────────────────────────────────────

def test_first_cycle_fetches_and_stores(isolated, no_network):
    """첫 주기엔 받아서 저장한다."""
    out = vw.valhalla_snapshot()

    assert out["pipeline"]["refreshed"] is True
    assert out["pipeline"]["value"]["stages"] == {"에볼라": "stockpiled"}
    assert no_network["pipeline"] == 1
    assert vw.STATE_FILE.exists(), "다음 주기가 읽을 파일이 안 생겼다"


def test_second_cycle_reuses_instead_of_refetching(isolated, no_network):
    """★★핵심★★ 주기 전이면 다시 안 받는다.

    매시간 ClinicalTrials 를 17번씩 부르면 하루 408회다. 값은 달 단위로 바뀌는데.
    """
    vw.valhalla_snapshot()
    out = vw.valhalla_snapshot()

    assert no_network["pipeline"] == 1, "주기 전인데 또 받았다"
    assert out["pipeline"]["refreshed"] is False
    assert out["pipeline"]["reason"] == "갱신 주기 전"
    assert out["pipeline"]["value"]["stages"] == {"에볼라": "stockpiled"}, "재사용값이 비었다"


def test_refetches_once_the_interval_passes(isolated, no_network):
    """주기가 지나면 새로 받는다."""
    start = dt.datetime(2026, 9, 3, 0, 0, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    later = start + dt.timedelta(hours=vw.PIPELINE_EVERY_HOURS)
    out = vw.valhalla_snapshot(now=later)

    assert out["pipeline"]["refreshed"] is True
    assert no_network["pipeline"] == 2


# ── 굳은 값을 새 값인 척하지 않는다 ────────────────────────────────────────

def test_fetch_failure_keeps_the_old_value_but_says_so(isolated, no_network,
                                                       monkeypatch):
    """★★핵심★★ 갱신 실패를 조용히 넘기지 않는다 — 사유와 나이를 남긴다."""
    start = dt.datetime(2026, 9, 3, 0, 0, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    def boom():
        raise ConnectionError("ClinicalTrials 안 됨")
    monkeypatch.setattr(vw, "_fetch_pipeline", boom)

    later = start + dt.timedelta(hours=26)
    out = vw.valhalla_snapshot(now=later)

    assert out["pipeline"]["refreshed"] is False
    assert "ConnectionError" in out["pipeline"]["reason"]
    assert out["pipeline"]["value"]["stages"] == {"에볼라": "stockpiled"}, "실패했다고 값을 버렸다"
    assert out["pipeline"]["age_hours"] == 26.0, "나이가 안 자란다"


def test_age_keeps_growing_while_refresh_keeps_failing(isolated, monkeypatch):
    """★핵심★ 계속 실패하면 나이가 계속 자라서 눈에 보인다."""
    def boom():
        raise TimeoutError("느림")
    monkeypatch.setattr(vw, "_fetch_pipeline", lambda: {"stages": {}, "lookup_failed": 0})
    start = dt.datetime(2026, 9, 3, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    monkeypatch.setattr(vw, "_fetch_pipeline", boom)
    ages = [vw.valhalla_snapshot(now=start + dt.timedelta(hours=h))["pipeline"]["age_hours"]
            for h in (25, 30, 50)]

    assert ages == [25.0, 30.0, 50.0]
    assert ages == sorted(ages), "굳은 값이 계속 새 값처럼 보인다"


def test_broken_state_file_does_not_kill_the_layer(isolated, no_network):
    """상태 파일이 깨져도 층이 죽지 않는다 — 다음 주기에 다시 쌓인다."""
    vw.STATE_FILE.write_text("{깨진 json", encoding="utf-8")

    out = vw.valhalla_snapshot()

    assert out["pipeline"]["refreshed"] is True


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


# ── 굳은 조각 판정 (2026-09-03 운영 장애에서 나옴) ─────────────────────────

def test_success_does_not_look_like_a_failure(isolated, no_network):
    """★★핵심★★ 성공한 조각을 '갱신 실패' 로 읽지 않는다.

    수집기에서 `part.get("reason", "")` 로 짰다가 운영에서 터졌다 —
    **키가 있는데 값이 None** 이면 `.get` 의 기본값이 안 먹는다. 성공 시
    reason 이 None 이라 첫 성공 주기에서 AttributeError 가 났고, 발할라 층
    전체가 실패로 기록됐다(2026-09-03 11:11 운영 로그).
    """
    out = vw.valhalla_snapshot()

    assert out["pipeline"]["reason"] is None
    assert vw.stale_parts(out) == [], "성공을 실패로 읽었다"


def test_stale_parts_finds_only_real_failures(isolated, no_network, monkeypatch):
    """★핵심★ 주기 전이라 안 받은 것은 실패가 아니다."""
    start = dt.datetime(2026, 9, 3, tzinfo=dt.timezone.utc)
    vw.valhalla_snapshot(now=start)

    # 주기 전 — 재사용이지 실패가 아니다.
    reused = vw.valhalla_snapshot(now=start + dt.timedelta(hours=1))
    assert vw.stale_parts(reused) == []

    monkeypatch.setattr(vw, "_fetch_pipeline",
                        lambda: (_ for _ in ()).throw(ConnectionError("x")))
    failed = vw.valhalla_snapshot(now=start + dt.timedelta(hours=25))

    names = [name for name, _ in vw.stale_parts(failed)]
    assert names == ["pipeline"]


def test_stale_parts_survives_a_dead_layer(isolated):
    """조각이 통째로 없거나 None 이어도 판정이 터지지 않는다."""
    assert vw.stale_parts({}) == []
    assert vw.stale_parts({"pipeline": "이상한 값"}) == []


# ── 파이프라인 결과 가시화 (2026-09-04) ─────────────────────────────
# 점검에서 나온 것: 24시간마다 17개 병원체를 조회해놓고 **로그에도 요약에도
# 아무 값이 안 실렸다.** 돌고는 있는데 뭐가 나오는지 아무도 모르는 층이었다.
# 게다가 일부 조회가 실패하면 조용히 '판정불가'로 섞였다.

def _fake_pipeline(monkeypatch, per_pathogen: dict):
    """병원체 이름 → fetch_pipeline 반환값을 흉내낸다."""
    from algorithms import countermeasure_pipeline as cp
    from algorithms import countermeasure_stockpile as cs

    queries = {name: name for name in per_pathogen}
    monkeypatch.setattr(cp, "PATHOGEN_QUERIES", queries)
    monkeypatch.setattr(cp, "fetch_pipeline", lambda q, **kw: per_pathogen[q])
    monkeypatch.setattr(cs, "stockpile_status",
                        lambda name: {"has_global_stockpile": name == "콜레라"})


def test_pipeline_keeps_more_than_stage_keys(monkeypatch):
    """단계 키만 남기면 로그에 찍을 게 없다. 한글 단계·연구 수도 들고 온다."""
    _fake_pipeline(monkeypatch, {
        "콜레라": {"available": True, "study_count": 40, "furthest_phase": 5},
        "니파": {"available": True, "study_count": 0, "furthest_phase": None},
    })
    out = vw._fetch_pipeline()
    assert out["stage_ko"]["콜레라"] == "국제 비상 비축 있음"
    assert out["study_counts"]["니파"] == 0
    assert out["stage_counts"]["stockpiled"] == 1
    assert out["pathogen_count"] == 2


def test_lookup_failure_is_not_the_same_as_no_registered_trial(monkeypatch):
    """★핵심★ '조회 실패'는 우리가 못 본 것이고 '등록 연구 없음'은 보고 없다고
    확인한 것이다. 합치면 조회 실패가 발견으로 둔갑한다."""
    _fake_pipeline(monkeypatch, {
        "니파": {"available": True, "study_count": 0, "furthest_phase": None},
        "치쿤구니야": {"available": False, "reason": "조회 실패: Timeout"},
    })
    out = vw._fetch_pipeline()
    assert out["no_registered_trial"] == ["니파"]
    assert out["failed_pathogens"] == ["치쿤구니야"]
    assert out["lookup_failed"] == 1
    assert out["stages"]["치쿤구니야"] == "unknown"      # 등록없음이 아니다


def test_pipeline_raises_only_when_every_lookup_fails(monkeypatch):
    _fake_pipeline(monkeypatch, {
        "니파": {"available": False, "reason": "x"},
        "치쿤구니야": {"available": False, "reason": "y"},
    })
    with pytest.raises(RuntimeError):
        vw._fetch_pipeline()


def test_partial_failure_still_produces_a_snapshot(monkeypatch):
    """하나가 죽었다고 나머지 16종을 버리지 않는다."""
    _fake_pipeline(monkeypatch, {
        "콜레라": {"available": True, "study_count": 40},
        "치쿤구니야": {"available": False, "reason": "y"},
    })
    out = vw._fetch_pipeline()
    assert out["stage_counts"]["stockpiled"] == 1
    assert out["lookup_failed"] == 1


# ── 로그 한 줄 ───────────────────────────────────────────────────
def test_summary_separates_bare_from_unknown():
    line = vw.pipeline_summary({
        "stage_counts": {"stockpiled": 5, "no_registered_trial": 2, "unknown": 1},
        "no_registered_trial": ["니파", "한타바이러스"],
    })
    assert "등록없음 2종" in line and "판정불가 1종" in line
    assert "니파·한타바이러스" in line


def test_summary_returns_none_when_there_is_nothing(monkeypatch):
    """값이 없으면 없는 걸 지어내지 않는다 — 빈 줄을 로그에 흘리지도 않는다."""
    assert vw.pipeline_summary(None) is None
    assert vw.pipeline_summary({}) is None
    assert vw.pipeline_summary({"stage_counts": {}}) is None


def test_summary_orders_from_stockpiled_to_bare():
    """시장에서 먼 쪽이 뒤로 가야 눈에 띈다."""
    line = vw.pipeline_summary({
        "stage_counts": {"no_registered_trial": 1, "stockpiled": 1, "early_trial": 1},
        "no_registered_trial": ["니파"],
    })
    assert line.index("비축") < line.index("초기임상") < line.index("등록없음")


def test_summary_reads_the_legacy_shape(monkeypatch):
    """★실측 회귀★ 파이프라인은 24시간 주기라, 새 코드를 배포해도 볼륨의 값은
    한동안 stage_counts 가 없는 옛 모양이다. 그걸 못 읽으면 최대 하루 —
    갱신이 계속 실패하면 영영 — 로그가 조용하다. 이 층을 보이게 하려고 만든
    함수가 바로 그 이유로 침묵한 것이 운영에서 실제로 확인됐다(2026-09-04,
    배포 후 두 주기 연속 무출력)."""
    legacy = {"stages": {"에볼라": "stockpiled", "니파": "no_registered_trial",
                         "MERS": "early_trial"},
              "lookup_failed": 0}
    line = vw.pipeline_summary(legacy)
    assert line is not None
    assert "비축 1종" in line and "초기임상 1종" in line and "등록없음 1종" in line
    assert "[등록없음: 니파]" in line


def test_new_shape_still_wins_over_derived_counts():
    """새 모양이 있으면 그걸 쓴다 — 파생 계산이 덮어쓰지 않는다."""
    line = vw.pipeline_summary({
        "stages": {"에볼라": "stockpiled"},
        "stage_counts": {"stockpiled": 7},
        "no_registered_trial": [],
    })
    assert "비축 7종" in line

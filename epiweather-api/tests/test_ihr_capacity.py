"""국가 역량 층이 **자가평가를 측정치로 팔지 않는지** 지킨다 (2026-09-02).

## 왜 만들었나

캡틴: *"발할라 더 크게 확장할 수 있는 방법 있어?"*

발할라에 국가 축이 없었다 — 위협 8종이 코드에 박혀 있고 나라는 한국뿐이라
"다른 나라 대비 우리가 어디쯤인가" 를 못 냈다. WHO 국제보건규칙 자가평가로
194개국 × 15개 역량을 붙였다.

## ★★ 이 파일이 막는 것 ★★

**자가평가를 측정치로 파는 것.** 나라가 자기 점수를 스스로 매긴다. 인도가 감시
100점, 네팔이 50점이라고 스스로 적어냈다. `is_self_assessed` 한 줄을 빼면 이게
"WHO 가 측정한 역량" 으로 읽히고, 그건 정부 문서에서 가장 먼저 지적당한다.

**그리고 합산 점수를 만드는 것.** 15개를 평균 내면 "한국 99.5점" 이 나오고 그게
문서에 실린다. 실험실과 방사선 비상을 더해서 나눌 근거가 우리에게 없다.
"""
from __future__ import annotations

import json

import pytest

from algorithms import ihr_capacity as ic
from algorithms.ihr_capacity import (
    BEHIND_MARGIN, country_capacity, weakest_countries, world_medians,
)


def _clear():
    """lru_cache 를 비운다. monkeypatch 로 갈아끼운 뒤엔 캐시가 없으므로 건너뛴다."""
    for fn in (ic._snapshot, ic.world_medians):
        clear = getattr(fn, "cache_clear", None)
        if clear:
            clear()


@pytest.fixture
def fake(monkeypatch):
    """세 나라뿐인 작은 스냅샷 — 중앙값을 손으로 확인할 수 있게."""
    snap = {
        "source": "WHO SPAR (테스트)",
        "snapshot_date": "2026-09-02",
        "latest_year": 2023,
        "years": [2023],
        "capacities": {"C04": "실험실", "C05": "감시"},
        "country_count": 3,
        "is_self_assessed": True,
        "scores": {
            "KOR": {"2023": {"C04": 100, "C05": 100}},
            "NPL": {"2023": {"C04": 40, "C05": 50}},
            "XXX": {"2023": {"C04": 80, "C05": 80}},
        },
    }
    _clear()
    monkeypatch.setattr(ic, "_snapshot", lambda: snap)
    yield snap
    _clear()


# ── 자가평가라는 사실을 숨기지 않는다 ──────────────────────────────────────

def test_every_answer_says_it_is_self_assessed(fake):
    """★★핵심★★ 모든 응답에 자가평가 표시가 붙는다 — 실패 응답에도."""
    for out in (country_capacity("KOR"), weakest_countries("C05"),
                country_capacity("ZZZ"), country_capacity("KOR", year=1999)):
        assert out["is_self_assessed"] is True, out


def test_limits_name_who_did_the_scoring(fake):
    """누가 점수를 매겼는지 밝힌다."""
    limits = " ".join(country_capacity("KOR")["limits"])

    assert "스스로 매긴 점수" in limits
    assert "WHO 가 검증한 값이 아니다" in limits
    assert "100점이 무결점이라는 뜻이 아니다" in limits


# ── 합산 점수를 만들지 않는다 ─────────────────────────────────────────────

def test_no_composite_national_score(fake):
    """★★핵심★★ 15개를 하나로 합치지 않는다.

    합치면 "한국 99.5점" 이 문서에 실리고, 그 99.5 를 설명할 근거가 없다.
    """
    out = country_capacity("KOR")

    for banned in ("overall", "total_score", "composite", "average",
                   "national_score", "score"):
        assert banned not in out, f"합산 점수처럼 보이는 키: {banned}"
    limits = " ".join(out["limits"])
    assert "하나의 국가 점수를 만들지 않는다" in limits


def test_counts_facts_instead_of_scoring(fake):
    """점수 대신 **셀 수 있는 것**을 센다 — 중앙값보다 뒤처진 역량 수."""
    assert country_capacity("KOR")["behind_world_count"] == 0
    assert country_capacity("NPL")["behind_world_count"] == 2
    assert "실험실" in country_capacity("NPL")["behind_world"]


# ── 모르는 것을 나쁜 점수로 바꾸지 않는다 ─────────────────────────────────

def test_missing_country_is_unknown_not_zero(fake):
    """★★핵심★★ 신고 기록이 없는 나라를 0점으로 접지 않는다.

    접으면 **신고를 안 한 곳이 세계 최악으로 보고된다.** 실제로 대만·홍콩·
    팔레스타인은 WHO 회원이 아니거나 별도 신고 주체가 아니라 SPAR 기록이 없다
    (2026-09-02 스냅샷 확인). 역량이 없어서가 아니다.
    """
    out = country_capacity("TWN")

    assert out["available"] is False
    assert "기록이 없다" in out["reason"]
    assert "capacities" not in out and "behind_world_count" not in out


def test_missing_snapshot_is_not_an_empty_world(monkeypatch):
    """기준 파일이 없으면 '모든 나라가 0점' 이 아니라 '모른다' 이다."""
    _clear()
    monkeypatch.setattr(ic, "_snapshot", lambda: None)

    out = country_capacity("KOR")

    assert out["available"] is False
    assert "기준 파일이 없다" in out["reason"]


def test_unknown_capacity_code_is_refused(fake):
    """없는 역량 코드를 조용히 빈 목록으로 답하지 않는다."""
    out = weakest_countries("C99")

    assert out["available"] is False
    assert "없는 역량 코드" in out["reason"]


# ── 통계를 정직하게 ───────────────────────────────────────────────────────

def test_median_not_mean(fake):
    """★핵심★ 중앙값이다 — 0점 몇 나라에 세계 기준이 끌려가면 안 된다."""
    medians = world_medians(2023)

    assert medians["C04"] == 80          # 40·80·100 의 중앙값
    assert medians["C04"] != pytest.approx((40 + 80 + 100) / 3)


def test_a_point_below_median_is_not_a_gap(fake):
    """★핵심★ 중앙값보다 1점 낮은 걸 격차라 하면 절반이 매년 격차가 된다."""
    fake["scores"]["YYY"] = {"2023": {"C04": 80 - 1, "C05": 80 - 1}}
    _clear()

    out = country_capacity("YYY")

    assert out["behind_world_count"] == 0
    assert BEHIND_MARGIN >= 5, "여유폭이 너무 좁으면 잡음이 격차가 된다"


def test_weakest_list_is_not_a_risk_ranking(fake):
    """★핵심★ 낮게 신고한 목록을 위험 순위로 팔지 않는다.

    정직하게 신고한 나라가 불리하게 보이고, 아예 신고 안 한 나라는 목록에
    오르지도 않는다.
    """
    out = weakest_countries("C05", limit=2)

    assert out["is_risk_ranking"] is False
    limits = " ".join(out["limits"])
    assert "정직하게 신고한 나라가 불리하게 보인다" in limits
    assert "신고를 아예 안 한 나라는 애초에 목록에 오르지 않는다" in limits
    assert [c["iso3"] for c in out["countries"]] == ["NPL", "XXX"]


# ── 실제 스냅샷의 정합성 ──────────────────────────────────────────────────

def test_snapshot_excludes_regional_aggregate_rows():
    """★★핵심★★ WHO 는 국가 행 사이에 지역·전세계 집계를 섞어 준다.

    안 거르면 국가 수를 240 으로 세고 "아프리카 지역" 을 한 나라처럼 순위에 넣는다.
    실측: COUNTRY 193 · UNREGION 40 · REGION 6 · GLOBAL 1.
    """
    snap = json.loads(ic.REFERENCE.read_text(encoding="utf-8"))

    assert 150 < snap["country_count"] < 210, snap["country_count"]
    for iso3 in snap["scores"]:
        assert len(iso3) == 3 and iso3.isalpha(), f"국가 코드가 아니다: {iso3}"
    for aggregate in ("EUR", "AFR", "SEAR", "GLOBAL", "WPR"):
        assert aggregate not in snap["scores"], f"집계행이 섞였다: {aggregate}"


def test_snapshot_carries_its_own_honesty_label():
    """파일만 보는 사람도 자가평가임을 알아야 한다."""
    snap = json.loads(ic.REFERENCE.read_text(encoding="utf-8"))

    assert snap["is_self_assessed"] is True
    assert "스스로 매긴" in snap["assessment_note"]
    assert snap["snapshot_date"] and snap["latest_year"] >= 2023


def test_real_snapshot_answers_for_korea():
    """실제 파일로 한국이 나온다 — 15개 역량이 다 있어야 한다."""
    out = country_capacity("KOR")

    assert out["available"] is True
    assert out["capacity_count"] == 15
    assert all(0 <= c["reported_score"] <= 100 for c in out["capacities"])


# ── 감시창 × 신고 역량 (엔드포인트) ────────────────────────────────────────

def _client():
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)


def test_capacity_gap_joins_open_windows_with_reports(monkeypatch):
    """★핵심★ 재난이 난 나라와 그 나라의 신고 역량을 나란히 놓는다.

    실측에서 네팔이 15개 중 8개를 세계 중앙값 아래로 신고했다 — 실험실·감시 포함.
    """
    monkeypatch.setattr("algorithms.disaster_watch.watched_countries",
                        lambda *a, **k: {"NPL", "KOR"})

    body = _client().get("/api/biodefense/capacity-gap").json()

    assert body["watched_country_count"] == 2
    top = body["countries"][0]
    assert top["iso3"] == "NPL", "뒤처진 역량이 많은 나라가 먼저 와야 한다"
    assert top["behind_world_count"] > 0
    assert "감시" in top["behind_world"]


def test_capacity_gap_keeps_non_reporters_apart(monkeypatch):
    """★★핵심★★ 신고를 안 한 곳을 '가장 취약' 으로 세지 않는다.

    대만은 WHO 회원이 아니라 SPAR 기록이 아예 없다. 그걸 0점으로 접으면 GDACS 가
    대만에 재난을 잡은 날 "세계 최악의 대비" 로 보고하게 된다.
    """
    monkeypatch.setattr("algorithms.disaster_watch.watched_countries",
                        lambda *a, **k: {"TWN", "NPL"})

    body = _client().get("/api/biodefense/capacity-gap").json()

    assert [c["iso3"] for c in body["countries"]] == ["NPL"]
    assert [c["iso3"] for c in body["no_self_report"]] == ["TWN"]
    assert body["watched_country_count"] == 2


def test_capacity_gap_is_not_sold_as_prediction(monkeypatch):
    """★핵심★ 역량이 낮다고 발병한다고 말하지 않는다."""
    monkeypatch.setattr("algorithms.disaster_watch.watched_countries",
                        lambda *a, **k: {"NPL"})

    body = _client().get("/api/biodefense/capacity-gap").json()

    assert body["is_prediction"] is False
    assert body["is_self_assessed"] is True
    assert "발병한다는 뜻이 아니다" in body["note"]


def test_capacity_endpoint_reports_unknown_country_honestly():
    """수록 없는 곳을 0점으로 답하지 않는다(대만 — WHO 회원이 아니다)."""
    body = _client().get("/api/biodefense/capacity/TWN").json()

    assert body["available"] is False
    assert body["is_self_assessed"] is True

"""백신 공급 층이 **'목록에 없음' 을 '못 만든다' 로 바꾸지 않는지** 지킨다 (2026-09-02).

## 왜 만들었나

캡틴: *"발할라에 더 많은 데이터가 쌓여야 해! 바이오산업이 발할라에서 진행되지 않아?"*

발할라에 생산 주권 축은 원래 있었는데(`domestic_producible`) 그 값이 **손으로
넣은 참/거짓** 이었다. WHO 사전적격성 목록으로 실제 근거를 붙였다.

실측(2026-09-02): 284건 · 56종 · 제조사 51곳.

## ★ 여기서 나온 진짜 발견 ★

국제 비상 비축 5종 중 **에볼라·엠폭스는 사전적격성 제조사가 한 곳뿐이다.**
비축이 있다는 것과 공급이 안전하다는 것은 다른 말이다 — 그 하나가 멈추면
비축은 다시 안 채워진다. 비축 목록만 봐서는 안 보인다.

## ★ 이 파일이 막는 것 ★

**"목록에 없다" 를 "못 만든다" 로 읽는 것.** 사전적격성은 UN 조달용 심사라
자국 시장만 겨냥한 백신은 아예 신청하지 않는다. 이 둘을 섞으면 "일본은 백신을
못 만든다" 같은 소리를 국가 문서에 쓰게 된다.
"""
from __future__ import annotations

import json

import pytest

from algorithms import vaccine_supply as vs
from algorithms.countermeasure_stockpile import ICG_STOCKPILES, KNOWN_GAP_ALIASES
from algorithms.vaccine_supply import (
    DISEASE_VACCINE_TERMS, chokepoints,
)


def _clear():
    """monkeypatch 로 갈아끼운 뒤엔 lru_cache 가 없으므로 건너뛴다."""
    clear = getattr(vs._snapshot, "cache_clear", None)
    if clear:
        clear()


@pytest.fixture
def fake(monkeypatch):
    snap = {
        "source": "WHO PQ (테스트)", "snapshot_date": "2026-09-02",
        "record_count": 4,
        "limits": ["여기 없다고 못 만든다는 뜻이 아니다."],
        "records": [
            {"vaccine_type": "Ebola Zaire", "manufacturer": "Merck",
             "regulatory_authority": "EMA", "authority_country": "EUR"},
            {"vaccine_type": "Cholera (oral)", "manufacturer": "EuBiologics",
             "regulatory_authority": "MFDS", "authority_country": "KOR"},
            {"vaccine_type": "Cholera (oral)", "manufacturer": "Shantha",
             "regulatory_authority": "CDSCO", "authority_country": "IND"},
            {"vaccine_type": "Rabies", "manufacturer": "미상 제조사",
             "regulatory_authority": "알 수 없는 기관", "authority_country": None},
        ],
    }
    _clear()
    monkeypatch.setattr(vs, "_snapshot", lambda: snap)
    yield snap
    _clear()


# ── 없음 ≠ 못 만듦 ────────────────────────────────────────────────────────

def test_missing_snapshot_is_not_an_empty_world(monkeypatch):
    """기준 파일이 없으면 '아무도 백신을 못 만든다' 가 아니라 '모른다' 이다."""
    _clear()
    monkeypatch.setattr(vs, "_snapshot", lambda: None)

    for out in (chokepoints(),):
        assert out["available"] is False
        assert "기준 파일이 없다" in out["reason"]


# ── 병목 판정 ─────────────────────────────────────────────────────────────

def test_single_source_is_not_sold_as_world_wide_monopoly(fake):
    """★★핵심★★ '사전적격성 제조사 하나' 를 '세상에 하나' 로 팔지 않는다."""
    limits = " ".join(chokepoints()["limits"])

    assert "위험 순위가 아니다" in limits
    assert "생산량은 이 자료에 없다" in limits


def test_chokepoints_counts_types_not_records(fake):
    """백신 '종류' 로 세야 한다 — 같은 종류 두 줄을 두 병목으로 세면 안 된다."""
    out = chokepoints()

    assert out["vaccine_type_count"] == 3          # Ebola · Cholera · Rabies
    assert out["single_source_count"] == 2         # Ebola · Rabies
    assert [c["vaccine_type"] for c in out["single_source"]] == ["Ebola Zaire", "Rabies"]


# ── 감독국 ≠ 제조지 ───────────────────────────────────────────────────────

# ── 실제 스냅샷의 정합성 ──────────────────────────────────────────────────

def test_real_snapshot_maps_every_authority():
    """★핵심★ 모르는 규제기관이 남아 있으면 그 나라 몫이 통째로 사라진다."""
    snap = json.loads(vs.REFERENCE.read_text(encoding="utf-8"))

    assert snap["unmapped_authorities"] == [], snap["unmapped_authorities"]
    assert snap["record_count"] > 200
    assert all(r.get("authority_country") for r in snap["records"])


def test_every_watched_threat_has_a_search_term():
    """★★핵심★★ 감시하는 위협은 전부 검색어가 있어야 한다.

    빠지면 "표에 없는 병"(= 우리가 안 찾아봤다)으로 나온다. 그런데 실제로는
    "찾아봤는데 사전적격성 백신이 없다"(= 발견) 인 경우가 많다. 이 둘을 섞으면
    발견이 우리 작업 누락처럼 보인다.
    """
    watched = {v["name_ko"] for v in ICG_STOCKPILES.values()} | set(KNOWN_GAP_ALIASES)

    missing = sorted(watched - set(DISEASE_VACCINE_TERMS))
    assert not missing, f"검색어가 없는 위협: {missing}"



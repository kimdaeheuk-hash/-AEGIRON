"""규제 승인 제품 범위 (A-2) — "허가가 끝난 물건이 있는가".

A안에서 준비태세를 셋으로 나눴는데 그 사이에 구멍이 있었다: **이미 허가가
끝났는데 아무도 안 비축한 것**이 어느 칸에도 안 잡혔다. 비축 축은 "없음",
임상 축은 "이미 끝남" 이라 조용했다.

그 구분이 대비 우선순위를 바꾼다 — 승인 제품이 없으면 개발부터(몇 년),
있으면 조달부터(몇 달)다.

여기서 가장 조심하는 것: **이 자료를 '국가 비축'에 부으면 안 된다.** 미국에서
허가됐다는 것과 한국이 비축했다는 것은 아무 관계가 없다.
"""
from __future__ import annotations

from unittest.mock import patch

from algorithms import approved_products as ap
from algorithms import readiness_scopes as rsc

THREATS = [{"pathogen": p} for p in
           ("Anthrax", "Ebola", "MERS", "Novel", "Plague")]

SNAP = {
    "snapshot_date": "2026-09-04",
    "by_threat": {
        "Anthrax": {"product_count": 7, "examples": ["BIOTHRAX", "ANTHIM"]},
        "Ebola": {"product_count": 3, "examples": ["ERVEBO"]},
        "MERS": {"product_count": 0, "examples": []},
        # Plague 는 이 스냅샷이 조회하지 않았다 — 없는 것과 다르다
    },
}


# ── 네 갈래를 구분한다 ───────────────────────────────────────────
def test_approved_none_unknown_unsearchable_are_four_different_things():
    """★핵심★ 있다 / 없다 / 안 물어봤다 / 물어볼 수 없다. 이 넷을 뭉치면
    조회 실패와 신종 위협이 '승인 제품 없는 병'으로 둔갑한다."""
    assert ap.products_for("Anthrax", SNAP)["status"] == "approved"
    assert ap.products_for("MERS", SNAP)["status"] == "none"
    assert ap.products_for("Plague", SNAP)["status"] == "unknown"
    assert ap.products_for("Novel", SNAP)["status"] == "unsearchable"


def test_novel_is_unsearchable_by_definition_not_absent():
    """신종 위협은 아직 이름이 없어 적응증 낱말이 없다. 0으로 접으면 안 된다."""
    r = ap.products_for("Novel", SNAP)
    assert r["status"] == "unsearchable"
    assert "정의상" in r["reason"]


def test_threat_missing_from_term_table_is_unknown():
    """검색어 표에 없는 위협은 '안 찾아본 것'이다."""
    r = ap.products_for("Tularemia_오타", SNAP)
    assert r["status"] == "unknown" and "검색어 표에 없는" in r["reason"]


# ── 분모 ─────────────────────────────────────────────────────────
def test_unknown_and_unsearchable_stay_out_of_the_denominator():
    """★회귀★ 넣으면 안 찾아본 것 때문에 승인률이 낮아져 없는 격차를 만든다."""
    s = ap.approved_scope(THREATS, SNAP)
    assert s["approved"] == 2 and s["none"] == 1
    assert s["unknown"] == 1 and s["unsearchable"] == 1
    assert s["approval_rate"] == round(2 / 3, 3)      # 5종이 아니라 3종이 분모


def test_missing_snapshot_is_unavailable_not_zero():
    """스냅샷이 없으면 0%가 아니라 '아직 없다'로 답한다."""
    s = ap.approved_scope(THREATS, None)
    assert s["available"] is False
    assert "아직 없다" in s["reason"]


# ── 경계선이 값과 함께 나간다 ────────────────────────────────────
def test_scope_says_it_is_not_stock_and_not_domestic():
    s = ap.approved_scope(THREATS, SNAP)
    assert "물량이 아니다" in s["does_not_mean"]
    assert s["domestic_approval"] == "unknown"
    assert "식약처" in s["domestic_reason"]


def test_summary_names_the_procurement_ready_threats():
    """승인은 끝났는데 비축이 없는 것 = 조달부터 하면 되는 목록."""
    line = ap.approved_summary(ap.approved_scope(THREATS, SNAP))
    assert "승인 2종" in line and "Anthrax" in line and "Ebola" in line


def test_summary_none_when_unavailable():
    assert ap.approved_summary(None) is None
    assert ap.approved_summary(ap.approved_scope(THREATS, None)) is None


# ── 네 번째 범위로 붙었는가 ──────────────────────────────────────
def test_fourth_scope_is_wired_and_still_not_combined():
    r = rsc.readiness_by_scope([], THREATS, None, SNAP)
    assert "approved_products" in r["scopes"]
    assert r["combined_score"] is None
    assert r["scopes"]["approved_products"]["approved"] == 2


def test_scope_summary_includes_approved_products():
    line = rsc.scope_summary(rsc.readiness_by_scope([], THREATS, None, SNAP))
    assert "승인제품 2/3종" in line


def test_summary_omits_approved_when_snapshot_absent():
    """없는 범위를 0으로 찍지 않는다."""
    line = rsc.scope_summary(rsc.readiness_by_scope([], THREATS, None, None))
    assert "승인제품" not in line


# ── 수집: 실패를 '없음'으로 접지 않는다 ──────────────────────────
def test_fetch_treats_404_as_zero_not_failure():
    """openFDA 는 매칭이 없으면 404 를 준다. 그건 '없음'이지 실패가 아니다."""
    from algorithms import reference_fetch as rf

    class _R:
        status_code = 404
        def raise_for_status(self): raise AssertionError("404에 예외를 내면 안 된다")

    with patch("requests.get", return_value=_R()):
        total, names = rf._openfda_products("anthrax")
    assert total == 0 and names == []


def test_fetch_omits_threats_it_could_not_query(monkeypatch):
    """★핵심★ 조회 실패한 위협을 by_threat 에 0으로 넣으면 '승인 제품 없음'이라는
    발견으로 둔갑한다. 아예 빼서 소비자가 unknown 으로 읽게 한다."""
    from algorithms import reference_fetch as rf

    def fake(term, timeout=30):
        if "anthrax" in term:
            return 7, ["BIOTHRAX"]
        raise RuntimeError("timeout")

    monkeypatch.setattr(rf, "_openfda_products", fake)
    monkeypatch.setattr(rf, "OPENFDA_SLEEP", 0)
    monkeypatch.setattr(rf, "THREAT_SEARCH_TERMS", None, raising=False)
    with patch.dict(ap.THREAT_SEARCH_TERMS,
                    {"Anthrax": ["anthrax"], "Ebola": ["ebola"]}, clear=True):
        payload = rf.fetch_approved_products()

    assert set(payload["by_threat"]) == {"Anthrax"}
    assert payload["lookup_failed"] == ["Ebola"]
    # 소비자는 빠진 것을 unknown 으로 읽는다
    assert ap.products_for("Ebola", payload)["status"] == "unknown"


def test_fetch_raises_when_everything_fails(monkeypatch):
    """전부 실패하면 스냅샷을 만들지 않는다 — 빈 파일이 좋은 파일을 덮으면 안 된다."""
    from algorithms import reference_fetch as rf
    import pytest

    monkeypatch.setattr(rf, "_openfda_products",
                        lambda term, timeout=30: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(rf, "OPENFDA_SLEEP", 0)
    with patch.dict(ap.THREAT_SEARCH_TERMS, {"Anthrax": ["anthrax"]}, clear=True):
        with pytest.raises(RuntimeError):
            rf.fetch_approved_products()

"""발할라 P1 — 엔드포인트 캐시 전환+stale+식약처 국내분기.

전부 mock·직접 호출. TestClient(소켓) 미사용, 외부 HTTP 없음.
"""
from __future__ import annotations

import datetime as dt
import os


os.environ.setdefault("EPIWEATHER_SCHEDULER", "off")

from algorithms import approved_products as ap
from algorithms import countermeasure_pipeline as cp
from algorithms import readiness_scopes as scopes
from algorithms import valhalla_watch as vw


def _iso(hours_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(hours=hours_ago)).isoformat()


PROC_STATE = {
    "procurement": {
        "fetched_at": None,  # 테스트에서 채운다
        "value": {"bid_count": 5, "ted": {"bid_count": 3},
                  "coverage": ["KOR/나라장터", "EU/TED(미검증)"]}},
}
PIPE_DETAILS = {
    "X병": {"study_count": 12, "furthest_phase": 4,
            "furthest_phase_ko": "3상", "completed_late_phase": 0,
            "available": True},
}


def _pipe_state(hours_ago=2.0, with_details=True):
    value = {"stages": {"X병": "late_trial"},
             "stage_ko": {"X병": "후기 임상 진행 중"},
             "study_counts": {"X병": 12},
             "stage_counts": {"late_trial": 1},
             "lookup_failed": 0, "failed_pathogens": []}
    if with_details:
        value["details"] = dict(PIPE_DETAILS)
    return {"pipeline": {"fetched_at": _iso(hours_ago), "value": value}}


# ── 조달 캐시 전환 ────────────────────────────────────────────────
# ── posture 캐시 전환 ─────────────────────────────────────────────
def test_fetch_pipeline_persists_details(monkeypatch):
    """적재값에 판정 재료(details)가 같이 쌓인다."""
    import algorithms.countermeasure_stockpile as csp

    # _fetch_pipeline은 함수 안에서 임포트하므로 모듈 attr 패치로 충분하다.
    monkeypatch.setattr(cp, "fetch_pipeline",
                        lambda q: {"available": True, "study_count": 3,
                                   "furthest_phase": 2,
                                   "furthest_phase_ko": "2상",
                                   "completed_late_phase": 0})
    monkeypatch.setattr(csp, "stockpile_status",
                        lambda n: {"known": True,
                                   "has_global_stockpile": False})
    value = vw._fetch_pipeline()
    assert "details" in value
    det = value["details"]["에볼라"]
    assert det["furthest_phase"] == 2 and det["study_count"] == 3


# ── 식약처 국내분기 ───────────────────────────────────────────────
class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _envelope(total, names=(), code="00"):
    items = [{"ITEM_NAME": n} for n in names]
    return {"response": {"header": {"resultCode": code, "resultMsg": "OK"},
                         "body": {"totalCount": total,
                                  "items": {"item": items}}}}  # noqa: E501


def test_domestic_terms_cover_openfda_keys():
    assert set(ap.DOMESTIC_THREAT_TERMS) == set(ap.THREAT_SEARCH_TERMS)


def test_approved_scope_domestic_rated():
    threats = [{"pathogen": "Anthrax"}, {"pathogen": "Ebola"},
               {"pathogen": "Novel"}]
    snap = {"snapshot_date": "2026-11-01",
            "by_threat": {"Anthrax": {"product_count": 1, "examples": ["A"]},
                          "Ebola": {"product_count": 0, "examples": []}}}
    dom = {"snapshot_date": "2026-11-01",
           "by_threat": {"Anthrax": {"product_count": 2,
                                     "examples": ["탄저백신주"]},
                         "Ebola": {"product_count": 0, "examples": []}}}
    out = ap.approved_scope(threats, snap, dom)
    assert out["domestic_approval"] == "rated"
    assert out["domestic_approved"] == 1 and out["domestic_none"] == 1
    assert out["domestic_unsearchable"] == 1  # Novel
    assert out["domestic_approval_rate"] == 0.5
    assert out["domestic_approved_names"] == ["Anthrax"]


def test_approved_scope_domestic_unknown_by_default():
    """국내 스냅샷 없으면 예전처럼 unknown(하위 호환)."""
    out = ap.approved_scope([{"pathogen": "Anthrax"}], None)
    assert out["available"] is False
    assert out["domestic_approval"] == "unknown"
    assert "활용신청" in out["domestic_reason"]


def test_domestic_none_note_names_domestic_registry():
    """국내 '없음'에 미국 FDA 문구가 붙으면 안 된다."""
    out = ap.domestic_products_for(
        "Ebola", {"by_threat": {"Ebola": {"product_count": 0,
                                          "examples": []}}})
    assert out["status"] == "none"
    assert "국내" in out["note"] and "FDA" not in out["note"]


def test_readiness_by_scope_passes_domestic():
    dom = {"snapshot_date": "2026-11-01",
           "by_threat": {"Anthrax": {"product_count": 1,
                                     "examples": ["탄저백신주"]}}}
    out = scopes.readiness_by_scope(
        [], [{"pathogen": "Anthrax"}], None, None, dom)
    appr = out["scopes"]["approved_products"]
    assert appr["available"] is False  # openFDA 스냅샷 없음
    assert appr["domestic_approval"] == "rated"
    assert appr["domestic_approved"] == 1

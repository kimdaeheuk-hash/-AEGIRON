"""KDCA 국내 법정감염병 — 전부 수집 + 질병별 개별 급증.
핵심: 상재성 질병이 총합을 지배해도 단일 질병 급증(레지오넬라 등)이 개별로 잡히고,
목록에 손으로 안 넣은 신규 질병도 자동 수집되는지 검증."""
from __future__ import annotations
import datetime as dt
from unittest.mock import patch

import collector
from algorithms import kdca_anomaly as ka


def test_legionella_in_notable_set():
    """놓쳤던 그 구멍 — 레지오넬라증이 위험군(집계 대상)에 있어야 한다."""
    assert "레지오넬라증" in collector.KDCA_WATCH_DISEASES
    assert len(collector.KDCA_WATCH_DISEASES) >= 40
    for d in ("장티푸스", "세균성이질", "뎅기열", "결핵", "말라리아"):
        assert d in collector.KDCA_WATCH_DISEASES


def _fake_kdca_response(items):
    class _R:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"body": {"items": {"item": items}}}}
    return _R()


def _recent_period():
    now = dt.date.today()
    return f"{now.year}년 {now.isocalendar()[1]:02d}주"


def test_fetch_collects_all_diseases_not_just_notable():
    """★핵심 전환★ 이제 감시목록 밖 질병도 '전부' 수집한다(손으로 안 넣어도 잡힘)."""
    period = _recent_period()
    items = [
        {"icdNm": "레지오넬라증", "period": period, "resultVal": "5"},
        {"icdNm": "목록에없는신규병", "period": period, "resultVal": "3"},   # 예전엔 유실됐음
        {"icdNm": "장티푸스", "period": "2000년 01주", "resultVal": "9"},     # 오래됨 → 스킵
    ]
    with patch("collector.requests.get", return_value=_fake_kdca_response(items)):
        out = collector.fetch_kdca_weekly("KEY", weeks_back=4)
    assert out["레지오넬라증"][period] == 5
    assert out["목록에없는신규병"][period] == 3    # 목록 밖이어도 수집됨
    assert "장티푸스" not in out                    # 오래된 주는 스킵


def test_spike_detected_despite_endemic_dominated_total():
    """상재성 질병(수두)이 총합을 지배해도 레지오넬라 급증(5→40)은 개별로 잡힌다."""
    kw = {
        "수두": {"w1": 2000, "w2": 2050, "w3": 2100, "w4": 2080},          # 크지만 안정 → 급증 아님
        "결핵": {"w1": 400, "w2": 410, "w3": 405, "w4": 420},
        "레지오넬라증": {"w1": 5, "w2": 6, "w3": 4, "w4": 40},              # 8배 급증
    }
    spikes = ka.disease_spikes(kw)
    names = [s["disease"] for s in spikes]
    assert "레지오넬라증" in names
    assert "수두" not in names and "결핵" not in names          # 안정적이라 급증 아님
    leg = next(s for s in spikes if s["disease"] == "레지오넬라증")
    assert leg["ratio"] == 8.0 and leg["is_notable"] is True
    # 집계 총합은 위험군만 → 안정적인 수두·결핵이 들어가도, 레지오넬라 급증은 총합에
    # 안 묻히고 별도 지표(max_spike)로 뜬다
    assert ka.max_spike_signal(spikes) >= 8.0


def test_spike_from_zero_flagged():
    """0에서 발생으로 튀면 from_zero로 잡되 비율은 억지 계산 안 한다."""
    kw = {"신규병": {"w1": 0, "w2": 0, "w3": 12}}
    spikes = ka.disease_spikes(kw)
    assert len(spikes) == 1
    assert spikes[0]["from_zero"] is True and spikes[0]["ratio"] is None


def test_no_spike_when_stable_or_tiny():
    """안정적이거나 표본이 너무 작으면(min_count 미만) 급증으로 안 본다."""
    kw = {
        "안정병": {"w1": 100, "w2": 102, "w3": 98, "w4": 101},
        "소수변동": {"w1": 0, "w2": 0, "w3": 3},   # 3건 < min_count 5 → 무시
    }
    assert ka.disease_spikes(kw) == []


def test_notable_total_excludes_nonnotable():
    """집계 총합은 위험군만 — 목록 밖 상재성 질병은 총합을 오염시키지 않는다."""
    kw = {
        "레지오넬라증": {"w1": 40},           # notable
        "목록밖상재성병": {"w1": 99999},       # not notable → 총합서 제외
    }
    assert ka.notable_latest_total(kw) == 40.0

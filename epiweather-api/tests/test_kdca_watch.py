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


# ── 천단위 쉼표 회귀 (2026-08-13~17 실제 장애) ──────────────────────────
# allowlist를 폐지해 '전부 수집'으로 바꾼 순간, 그동안 목록 밖이라 안 보이던
# CRE 감염증(주 1,296건)이 들어왔다. KDCA는 1000 이상을 "1,296"으로 주는데
# int()가 여기서 터져 그 주 KDCA 수집이 통째로 사라졌다 — 나흘간 국내 데이터 공백.
# 660개 테스트가 통과했는데도 못 잡은 이유: 픽스처에 세 자리 값밖에 없었다.

def test_parse_kdca_count_handles_thousands_comma():
    assert ka.parse_kdca_count("1,296") == 1296
    assert ka.parse_kdca_count("1,353") == 1353
    assert ka.parse_kdca_count("12,345") == 12345
    assert ka.parse_kdca_count("5") == 5
    assert ka.parse_kdca_count(7) == 7


def test_parse_kdca_count_returns_none_for_unreadable():
    """읽을 수 없는 값은 0이 아니라 None — '0건 신고'와 '못 읽음'은 다른 사실이다."""
    for bad in ("-", "", "   ", None, "미상", True):
        assert ka.parse_kdca_count(bad) is None


def test_fetch_survives_comma_value_and_keeps_other_diseases():
    """★회귀 핵심★ 쉼표 값이 있어도 KDCA 수집 전체가 죽지 않고, 그 값도 제대로 읽힌다."""
    period = _recent_period()
    items = [
        {"icdNm": "카바페넴내성장내세균목(CRE) 감염증", "period": period, "resultVal": "1,296"},
        {"icdNm": "에볼라바이러스병", "period": period, "resultVal": "0"},
        {"icdNm": "홍역", "period": period, "resultVal": "3"},
    ]
    with patch("collector.requests.get", return_value=_fake_kdca_response(items)):
        out = collector.fetch_kdca_weekly("KEY", weeks_back=4)
    assert out["카바페넴내성장내세균목(CRE) 감염증"][period] == 1296
    assert out["에볼라바이러스병"][period] == 0     # 뒤 항목이 유실되지 않음
    assert out["홍역"][period] == 3


def test_fetch_drops_only_the_unreadable_item():
    """'-' 한 항목 때문에 나머지 질병까지 날아가면 안 된다."""
    period = _recent_period()
    items = [
        {"icdNm": "니파바이러스감염증", "period": period, "resultVal": "-"},
        {"icdNm": "콜레라", "period": period, "resultVal": "2"},
    ]
    with patch("collector.requests.get", return_value=_fake_kdca_response(items)):
        out = collector.fetch_kdca_weekly("KEY", weeks_back=4)
    assert "니파바이러스감염증" not in out          # 0으로 지어내지 않음
    assert out["콜레라"][period] == 2

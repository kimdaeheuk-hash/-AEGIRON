"""국내 법정감염병 감시목록 확장 + 이름 불일치 안전망.
레지오넬라 같은 국내 발생을 놓치지 않는지, 그리고 감시목록 밖 신고가 조용히
유실되지 않고 드러나는지 검증."""
from __future__ import annotations
import datetime as dt
from unittest.mock import patch

import collector


def test_legionella_in_kdca_watch_list():
    """오늘 놓친 그 구멍 — 레지오넬라증이 국내 감시목록에 있어야 한다."""
    assert "레지오넬라증" in collector.KDCA_WATCH_DISEASES
    # 폭넓게: 수인성·매개체·백신예방까지 넓어졌는지(9종 → 대폭 확대)
    assert len(collector.KDCA_WATCH_DISEASES) > 30
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


def test_fetch_kdca_collects_watched_and_flags_unwatched():
    """감시 대상은 수집, 감시 밖 신고(>0)는 로그로 드러낸다(조용히 안 버림)."""
    period = _recent_period()
    items = [
        {"icdNm": "레지오넬라증", "period": period, "resultVal": "5"},   # watched → 수집
        {"icdNm": "가상의새질병", "period": period, "resultVal": "3"},    # unwatched → 로그
        {"icdNm": "장티푸스", "period": "2000년 01주", "resultVal": "9"},  # 오래됨 → 스킵
    ]
    logs = []
    with patch("collector.requests.get", return_value=_fake_kdca_response(items)), \
         patch("collector.log", side_effect=lambda m: logs.append(m)):
        out = collector.fetch_kdca_weekly("KEY", weeks_back=4)

    assert "레지오넬라증" in out and out["레지오넬라증"][period] == 5
    assert "가상의새질병" not in out                       # 감시 밖은 결과에 안 들어감
    assert "장티푸스" not in out                            # 오래된 주는 스킵
    # 감시 밖이지만 신고가 있으니 안전망 로그가 떠야 한다
    assert any("감시목록 밖" in m and "가상의새질병" in m for m in logs)


def test_zero_value_unwatched_not_flagged():
    """감시 밖이라도 신고 0이면 굳이 로그로 소란 피우지 않는다."""
    period = _recent_period()
    items = [{"icdNm": "가상의새질병", "period": period, "resultVal": "0"}]
    logs = []
    with patch("collector.requests.get", return_value=_fake_kdca_response(items)), \
         patch("collector.log", side_effect=lambda m: logs.append(m)):
        collector.fetch_kdca_weekly("KEY")
    assert not any("감시목록 밖" in m for m in logs)

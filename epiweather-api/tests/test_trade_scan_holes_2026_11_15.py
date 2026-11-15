"""무역 스캔 — 빠진 달로 급증을 계산하지 않는다 + 직렬 조회로 복귀 (소킹 11-03~11-14).

관측: 11-03 15:04 '무역스캔 병렬'(3워커) 배포 뒤 매 주기 `부분 스캔`(품목당 4~5/6달,
HTTP 429×1~2). 빠진 달 위치가 주기마다 달라 같은 데이터에서 BLZ 최대 배수가
3.1·5.5·10.2·18.4배로 매시 바뀌었고, 최신 달이 빠지면 후보국이 35 → 57곳으로 바뀌었다.
배포 전(14:03~14:30)은 세 품목 모두 6/6달이었다.
"""
from unittest.mock import patch

from algorithms import comtrade_signals as cs


def _notes_series(ok: int, total: int = 6, empty: int = 0):
    """fetch_public_series 대역 — notes 를 채우고 급증 시계열을 돌려준다."""
    def _fake(hs, months=6, notes=None):
        if notes is not None:
            notes.update({"months_total": total, "months_ok": ok, "months_empty": empty})
            if ok < total:
                notes["reasons"] = {"HTTP 429": total - ok}
        return {"BLZ": [100.0, 100.0, 1800.0], "KOR": [100.0, 100.0, 105.0]}
    return _fake


def _clear_cache():
    cs._SCAN_CACHE.clear()


def test_serial_month_fetch_is_back():
    # 병렬 3워커가 429 를 불렀다 — 직렬(1)이 배포 전 6/6 을 내던 모양이다.
    assert cs.PARALLEL_MONTH_WORKERS == 1


def test_product_with_missing_months_is_not_used_for_surges():
    _clear_cache()
    with patch.object(cs, "fetch_public_series", side_effect=_notes_series(ok=4)):
        scan = cs.global_trade_scan(use_cache=False)
    for p in scan["products"].values():
        assert p["data_available"] is False
        assert p["holes"] is True
        assert "계산하지 않음" in p["reason"]
    assert scan["top_surges"] == []
    assert cs.trade_alert_candidates(scan) == []      # 구멍에서 경보를 지어내지 않는다
    assert cs.scan_incomplete(scan) is True          # → 경보 쪽은 '판정 안 함'으로 둔다


def test_empty_month_is_not_a_hole():
    # 응답은 왔는데 0개국인 달(신고 지연)은 실패가 아니다 — 그대로 쓴다.
    _clear_cache()
    with patch.object(cs, "fetch_public_series", side_effect=_notes_series(ok=6, empty=1)):
        scan = cs.global_trade_scan(use_cache=False)
    assert all(p["data_available"] for p in scan["products"].values())
    assert any(s["country_iso3"] == "BLZ" for s in scan["top_surges"])


def test_complete_scan_still_produces_multi_product_candidate():
    _clear_cache()
    with patch.object(cs, "fetch_public_series", side_effect=_notes_series(ok=6)):
        scan = cs.global_trade_scan(use_cache=False)
    out = cs.trade_alert_candidates(scan)
    assert [c["source"] for c in out] == ["trade_surge:BLZ"]
    assert out[0]["score"] <= 79.0


def test_scan_line_says_why_product_was_skipped():
    p = {"data_available": False, "holes": True,
         "fetch": {"months_total": 6, "months_ok": 4, "reasons": {"HTTP 429": 2}}}
    part = cs._product_part("masks_breathing", p)
    assert "4/6달" in part
    assert "빠진 달 있어 계산 안 함" in part
    assert "HTTP 429×2" in part
    assert "사용 불가" not in part

"""식약처 국내 허가 품목 연결 (2026-11-23).

키 없음은 판정 안 함 · 응답 두 모양 · 버전 08→07 · 실패는 '없음'으로 접지 않음 · 키가 오류 문구에 안 샘 ·
공백 지도 국내 칸 · 발할라 준비태세 배선을 네트워크 없이 고정한다.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from algorithms import gap_map
from algorithms import reference_fetch as rf

FAKE_KEY = "fake-key-for-tests"


def _resp(status=200, body=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    if body is None:
        r.json.side_effect = ValueError("not json")
    else:
        r.json.return_value = body
    r.raise_for_status.side_effect = None if status < 400 else RuntimeError(f"HTTP {status}")
    return r


def _ok(total, names):
    return {"header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {"totalCount": total, "items": [{"ITEM_NAME": n, "ENTP_NAME": "회사"} for n in names]}}


def test_no_key_raises_and_says_what_to_do(monkeypatch):
    monkeypatch.delenv("MFDS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MFDS_API_KEY"):
        rf.fetch_domestic_products()


def test_encoded_key_is_unquoted(monkeypatch):
    monkeypatch.setenv("MFDS_API_KEY", "abc%2Bdef%3D%3D")
    assert rf._mfds_key() == "abc+def=="


def test_parse_accepts_both_portal_shapes():
    assert rf._mfds_parse(_ok(3, ["가", "나"])) == (3, [{"ITEM_NAME": "가", "ENTP_NAME": "회사"},
                                                         {"ITEM_NAME": "나", "ENTP_NAME": "회사"}])
    nested = {"response": {"header": {"resultCode": "00"},
                           "body": {"totalCount": "1", "items": {"item": {"ITEM_NAME": "다"}}}}}
    assert rf._mfds_parse(nested) == (1, [{"ITEM_NAME": "다"}])
    with pytest.raises(RuntimeError, match="오류 30"):
        rf._mfds_parse({"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}})
    with pytest.raises(RuntimeError, match="body"):
        rf._mfds_parse({"header": {"resultCode": "00"}})


def test_falls_back_to_v07_and_hides_key_in_errors(monkeypatch):
    calls = []

    def fake_get(url, params, timeout, headers):
        calls.append(url)
        if "Service08" in url:
            return _resp(404)
        return _resp(200, _ok(2, ["에볼라백신주"]))
    monkeypatch.setattr(rf.requests, "get", fake_get)
    total, names, fields, url = rf._mfds_products("에볼라", FAKE_KEY)
    assert (total, names) == (2, ["에볼라백신주"]) and "Service07" in url
    assert fields == ["ENTP_NAME", "ITEM_NAME"]

    monkeypatch.setattr(rf.requests, "get",
                        lambda *a, **k: _resp(200, None, text=f"<OpenAPI_ServiceResponse>{FAKE_KEY}"))
    with pytest.raises(RuntimeError) as e:
        rf._mfds_products("에볼라", FAKE_KEY)
    assert FAKE_KEY not in str(e.value)


def test_failed_threat_is_left_out_not_zero(monkeypatch):
    monkeypatch.setenv("MFDS_API_KEY", FAKE_KEY)
    monkeypatch.setattr(rf.time, "sleep", lambda s: None)

    def fake(term, key, timeout=20):
        if term == "탄저":
            raise RuntimeError("timeout")
        return (1, [f"{term}품목"], ["ITEM_NAME"], rf.MFDS_URLS[0]) if term == "에볼라" else (0, [], [], rf.MFDS_URLS[0])
    monkeypatch.setattr(rf, "_mfds_products", fake)
    out = rf.fetch_domestic_products()
    assert "Anthrax" not in out["by_threat"] and "Anthrax" in out["lookup_failed"]
    assert out["by_threat"]["Ebola"]["product_count"] == 1
    assert out["by_threat"]["Plague"]["product_count"] == 0
    assert out["fields_seen"] == ["ITEM_NAME"]


def _row(m, key):
    return next(r for r in m["rows"] if r["key"] == key)


def test_gap_map_domestic_cells():
    m = gap_map.build(None, None, None)
    assert _row(m, "nipah")["cells"]["domestic"]["status"] == "undetermined"
    assert "판정 안 함" in m["sources"]["domestic"]

    snap = {"by_threat": {"Ebola": {"product_count": 2, "examples": ["가"]}, "Nipah": {"product_count": 0}}}
    m = gap_map.build(None, None, None, None, snap)
    assert _row(m, "ebola")["cells"]["domestic"]["status"] == "approved"
    assert _row(m, "nipah")["cells"]["domestic"]["status"] == "none"
    assert _row(m, "marburg")["cells"]["domestic"]["status"] == "undetermined"   # 조회 안 한 위협
    assert _row(m, "pathogen_x")["cells"]["domestic"]["status"] == "unsearchable"


def test_readers_load_the_domestic_snapshot():
    from algorithms import valhalla_watch
    assert '_load("domestic_products")' in inspect.getsource(valhalla_watch._readiness_scopes)
    assert '_load("domestic_products")' in inspect.getsource(gap_map.current)


def test_snapshot_registered():
    from algorithms import reference_snapshots as rs
    cfg = rs.SNAPSHOTS["domestic_products"]
    assert cfg["fetch"] == "fetch_domestic_products" and hasattr(rf, cfg["fetch"])

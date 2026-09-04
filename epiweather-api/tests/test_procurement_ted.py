"""EU 조달(TED) — 국제 확장 (2026-09-04, C-2).

★ 이 층은 아직 실측되지 않았다 ★ 개발 환경의 외부 접속이 막혀(403) TED
엔드포인트를 한 번도 실제로 부르지 못했다. 그래서 아래 테스트가 지키는 것은
"TED 가 잘 동작한다" 가 아니라 **"검증 안 된 값이 검증된 값처럼 보이지 않는다"**
와 **"실패가 0건으로 둔갑하지 않는다"** 이다.

국내 층에서 배운 것도 그대로 적용됐는지 본다: 나라장터에서 `방역` 에 청소년
해외역사탐방 공고가 딸려 온 전례가 있어, 서버가 준 것을 그대로 믿지 않는다.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from algorithms import procurement_ted as ted
from algorithms.procurement_watch import procurement_summary


def _notice(title, **over):
    row = {"publication_number": "2026/S 001-000001", "title": title,
           "description": None, "buyer_name": "HERA", "buyer_country": "BEL",
           "publication_date": "2026-09-01", "deadline": "2026-09-20",
           "estimated_value": 1000000, "currency": "EUR", "links": {}}
    row.update(over)
    return row


# ── 검증 안 됨을 값에 담는다 ─────────────────────────────────────
def test_layer_reports_itself_as_unverified():
    """★핵심★ 첫 실측 성공 전까지 이 층의 숫자를 대외 자료에 쓰면 안 된다.
    그 사실이 주석이 아니라 값에 실려야 한다 — 숫자만 떼어 가도 따라가게."""
    assert ted.IS_VERIFIED is False
    with patch.object(ted, "_search", return_value=[_notice("Vaccine procurement")]):
        out = ted.watch_ted(days=7)
    assert out["is_verified"] is False
    assert "대외 자료에" in out["unverified_note"]


def test_log_line_marks_ted_as_unverified():
    line = procurement_summary({
        "bid_count": 31,
        "deadline": {"counts": {"open": 12, "closing_soon": 3, "closed": 15}},
        "ted": {"bid_count": 8, "is_verified": False,
                "deadline": {"counts": {"open": 6, "closing_soon": 2}}}})
    assert "※미검증" in line


# ── 실패를 0건으로 접지 않는다 ───────────────────────────────────
def test_all_lookups_failing_is_unavailable_not_zero():
    """★핵심★ 한 낱말도 못 물었으면 '공고 0건'이 아니라 조회 실패다.
    섞으면 조회 실패가 'EU 가 아무것도 안 산다'는 발견으로 둔갑한다."""
    with patch.object(ted, "_search", return_value="ConnectionError"):
        out = ted.watch_ted(days=7)
    assert out["available"] is False
    assert "모든 낱말 조회 실패" in out["reason"]
    assert "bid_count" not in out


def test_partial_failure_still_returns_what_was_found():
    """하나가 죽었다고 나머지를 버리지 않는다."""
    calls = {"n": 0}

    def flaky(keyword, begin, end):
        calls["n"] += 1
        if calls["n"] % 2:
            return "Timeout"
        return [_notice(f"Vaccine {keyword}", publication_number=f"P{calls['n']}")]

    with patch.object(ted, "_search", side_effect=flaky):
        out = ted.watch_ted(days=7)
    assert out["available"] is True
    assert out["bid_count"] > 0
    assert out["lookup_failures"]          # 실패도 같이 보고한다


def test_missing_notices_key_is_a_failure_not_empty():
    """응답 형식이 바뀌면 빈 결과로 접지 않는다."""
    class _R:
        def raise_for_status(self): pass
        def json(self): return {"unexpected": []}

    with patch("requests.post", return_value=_R()):
        result = ted._search("vaccine", "20260901", "20260904")
    assert isinstance(result, str) and "형식 변경 의심" in result


# ── 서버가 준 것을 그대로 믿지 않는다 ────────────────────────────
def test_notice_without_the_keyword_is_dropped():
    """★국내 층에서 배운 것★ 나라장터에서 '방역'에 청소년 여행 공고가 딸려 왔다.
    검색이 느슨하면 무관한 공고가 섞인다 — 우리가 낱말을 다시 짚는다."""
    with patch.object(ted, "_search",
                      return_value=[_notice("Office furniture supply")]):
        out = ted.watch_ted(days=7)
    assert out["bid_count"] == 0
    assert out["dropped_unconfirmed"] > 0


def test_confirm_reports_where_it_matched():
    assert ted._confirm(_notice("Vaccine tender"), "vaccine") == "title"
    assert ted._confirm(_notice("X", description="antiviral stock"), "antiviral") == "description"
    assert ted._confirm(_notice("X"), "vaccine") is None


# ── 다국어 응답 평탄화 ───────────────────────────────────────────
def test_flatten_prefers_english_and_never_invents():
    row = ted._flatten({
        "publication-number": "2026/S 1",
        "notice-title": {"eng": ["Vaccine procurement"], "fra": ["Marché vaccin"]},
        "buyer-name": ["HERA"],
        "deadline-receipt-request": None,
    })
    assert row["title"] == "Vaccine procurement"
    assert row["buyer_name"] == "HERA"
    assert row["deadline"] is None            # 없으면 None — 지어내지 않는다


def test_flatten_falls_back_when_english_absent():
    row = ted._flatten({"notice-title": {"fra": ["Marché vaccin"]}})
    assert row["title"] == "Marché vaccin"


# ── 발할라 배선: 합치지 않는다 ───────────────────────────────────
def test_valhalla_keeps_sources_separate(monkeypatch):
    """★핵심★ 합쳐서 한 숫자로 내면 '31건'이 어느 나라 것인지 알 수 없고,
    한쪽이 죽어도 총계가 줄기만 해서 안 보인다. 그리고 미검증 층의 값이
    검증된 값과 섞인다."""
    from algorithms import valhalla_watch as vw
    monkeypatch.setattr(
        "algorithms.procurement_watch.watch_bids",
        lambda days=7: {"available": True, "bid_count": 2, "excluded_count": 0,
                        "source": "나라장터",
                        "bids": [{"title": "방역", "closes_at": "2026-12-01 10:00:00",
                                  "category": "감염병 감시·대응", "notice_no": "K1",
                                  "agency": "질병관리청", "assigned_budget_krw": None}]})
    monkeypatch.setattr(
        "algorithms.procurement_ted.watch_ted",
        lambda days=7: {"available": True, "bid_count": 5, "dropped_unconfirmed": 1,
                        "lookup_failures": [], "is_verified": False,
                        "unverified_note": "n",
                        "bids": [{"title": "Vaccine", "closes_at": "2026-12-05",
                                  "category": "대응제·비축", "notice_no": "E1",
                                  "agency": "HERA", "assigned_budget_krw": None}]})

    value = vw._fetch_procurement()
    assert value["bid_count"] == 2                      # 국내 숫자는 그대로
    assert value["ted"]["bid_count"] == 5               # EU 는 따로
    assert value["coverage"] == ["KOR/나라장터", "EU/TED(미검증)"]
    assert value["ted"]["is_verified"] is False


def test_ted_failure_does_not_kill_the_domestic_layer(monkeypatch):
    """EU 가 죽어도 국내 감시는 계속돼야 한다."""
    from algorithms import valhalla_watch as vw
    monkeypatch.setattr(
        "algorithms.procurement_watch.watch_bids",
        lambda days=7: {"available": True, "bid_count": 2, "excluded_count": 0,
                        "source": "나라장터", "bids": []})
    monkeypatch.setattr("algorithms.procurement_ted.watch_ted",
                        lambda days=7: (_ for _ in ()).throw(RuntimeError("TED down")))

    value = vw._fetch_procurement()
    assert value["bid_count"] == 2
    assert value["ted"]["available"] is False and "TED down" in value["ted"]["reason"]
    # 실패했으면 범위에 EU 를 넣지 않는다 — 안 보는 걸 본다고 하면 안 된다.
    assert value["coverage"] == ["KOR/나라장터"]


def test_log_line_shows_ted_failure_rather_than_hiding_it():
    line = procurement_summary({
        "bid_count": 31,
        "deadline": {"counts": {"open": 12}},
        "ted": {"available": False, "reason": "모든 낱말 조회 실패", "is_verified": False}})
    assert "EU/TED 실패" in line

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

    def flaky(keyword, begin, end, fields=None):
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


# ── 첫 실호출이 실패했는데 왜인지 말하지 못했다 (2026-09-05) ──────
# 운영 로그 실측. TED 층이 처음으로 실제 호출된 사이클:
#
#     발할라 조달: 열림 23건 … | EU/TED 실패(모든 낱말 조회 실패(20건) — 예: epidemic: HTTPErro)
#
# 미검증 표시는 제 몫을 했다 — 실패가 0건으로 둔갑하지 않았고, 국내 숫자도 안 죽었다.
# 그런데 **고칠 수가 없었다.** 두 군데서 사유를 깎아먹었기 때문이다:
#   (1) _search 가 예외 이름만 돌려주고 상태코드를 버렸다
#   (2) 요약 줄이 [:40] 으로 잘라 "HTTPErro" 로 만들었다
# 401(키)·404(경로)·400(쿼리 형식)은 처방이 전부 다르다. 진단하라고 만든 값을
# 진단 못 하게 깎으면 없느니만 못하다.
class _Resp:
    def __init__(self, status): self.status_code = status


class _HTTPish(Exception):
    def __init__(self, status):
        super().__init__(f"{status} Client Error for url https://api.ted.europa.eu/v3/notices/search")
        self.response = _Resp(status)


def test_lookup_failure_keeps_the_status_code():
    """★핵심★ 이름만으로는 못 고친다. 숫자가 처방을 가른다."""
    with patch("requests.post", side_effect=_HTTPish(404)):
        result = ted._search("vaccine", "20260901", "20260905")
    assert result == "_HTTPish 404"


def test_total_failure_tallies_reasons_instead_of_showing_only_the_first():
    """전부 같은 이유인지 제각각인지가 원인 추정을 완전히 바꾼다.
    예전엔 첫 건만 '예:' 로 보여줘서 알 수 없었다."""
    with patch.object(ted, "_search", return_value="HTTPError 404"):
        out = ted.watch_ted(days=7)
    assert out["available"] is False
    assert "HTTPError 404×20" in out["reason"]
    assert "예:" not in out["reason"]
    assert out["lookup_failures"]          # 낱말별 원본도 같이 남긴다


def test_log_line_does_not_truncate_the_diagnosis():
    """★실측 결함★ [:40] 이 상태코드를 먹어서 'HTTPErro' 로 나갔다."""
    line = procurement_summary({
        "bid_count": 29,
        "deadline": {"counts": {"open": 23}},
        "ted": {"available": False, "is_verified": False,
                "reason": "모든 낱말 조회 실패(20건) — HTTPError 404×20"}})
    assert "HTTPError 404×20" in line
    assert "HTTPErro)" not in line


def test_log_line_says_so_when_the_reason_itself_is_missing():
    line = procurement_summary({
        "bid_count": 29, "deadline": {"counts": {"open": 23}},
        "ted": {"available": False, "is_verified": False}})
    assert "사유 미상" in line


# ── 400 을 보고 고친 것 (2026-09-05) ─────────────────────────────
# 첫 실호출: `EU/TED 실패(모든 낱말 조회 실패(20건) — HTTPError 400×20)`.
# 404 도 401 도 아니었으니 경로는 맞고 인증도 필요 없었다 — 요청 본문이 틀렸다.
# 상태코드를 살려둔 덕에 여기까지 좁혀졌다(#28 이 없었으면 "HTTPErro" 였다).
def _sent_body(keyword="vaccine"):
    """실제로 보내는 본문을 잡아낸다."""
    seen = {}

    class _R:
        def raise_for_status(self): pass
        def json(self): return {"notices": []}

    def _capture(url, **kw):
        seen["url"] = url
        seen["json"] = kw.get("json")
        return _R()

    with patch("requests.post", side_effect=_capture):
        ted._search(keyword, "20260901", "20260905")
    return seen


def test_query_uses_PD_not_the_field_identifier():
    """★400 의 주범★ 날짜는 질의 안에서 `PD` 로 쓴다. `publication-date` 는
    fields 쪽 식별자이지 질의 연산자가 아니다."""
    body = _sent_body()["json"]
    assert "PD>=20260901" in body["query"]
    assert "PD<=20260905" in body["query"]
    assert "publication-date>=" not in body["query"]


def test_query_still_full_text_searches_the_keyword():
    body = _sent_body("antiviral")["json"]
    assert 'FT~"antiviral"' in body["query"]


def test_fields_are_the_confirmed_identifiers_plus_nothing_else():
    """★한 번에 한 변수만★ 확인 안 된 식별자를 하나라도 넣으면 또 400 이고,
    조달은 6시간 주기라 다음 시도가 6시간 뒤다.

    09-15 에 설명 식별자 **하나만** 되돌렸다(_search 를 직접 부르면 기존 목록이
    기본값이다 — 후보를 붙이는 건 watch_ted 다). 나머지 셋은 여전히 안 쓴다."""
    body = _sent_body()["json"]
    assert body["fields"] == ted.TED_FIELDS
    for risky in ("deadline-receipt-request", "estimated-value", "links",
                  "publication-date"):
        assert risky not in body["fields"]


def test_only_one_unconfirmed_identifier_is_in_play():
    """되돌린 식별자가 늘어나면 이 테스트가 먼저 걸린다 — 400 한 번이 6시간이다."""
    extra = set(ted._fields_with_description()) - set(ted.TED_FIELDS)
    assert extra == {ted.TED_DESCRIPTION_FIELD}


def test_scope_includes_closed_notices():
    """마감 판정은 우리가 한다 — ACTIVE 로 걸러 받으면 그 판정을 못 한다.
    국내 층에서 '닫힌 공고 3건'이 헤드라인에 섞여 있던 걸 드러낸 것과 같은 이유."""
    assert _sent_body()["json"]["scope"] == "ALL"


def test_flatten_reads_the_new_field_names():
    row = ted._flatten({
        "publication-number": "2026/S 1",
        "notice-title": {"eng": ["Vaccine procurement"]},
        "buyer-name": ["HERA"],
        "deadline": "2026-09-20",
        "total-value": 1000000,
    })
    assert row["title"] == "Vaccine procurement"
    assert row["deadline"] == "2026-09-20"
    assert row["estimated_value"] == 1000000


def test_unrequested_fields_come_back_empty_not_invented():
    """★안 받는 것을 받은 척하지 않는다★ 발행일·링크는 아직 요청에 없다.
    서버가 보내줘도 우리가 안 물었으므로 None 이다.

    09-15: description 만 되돌렸다 — 다만 **우리가 요청한 식별자**로 온 것만
    읽는다. 아래처럼 예전 이름(`description`)으로 와도 안 읽는다."""
    row = ted._flatten({
        "notice-title": {"eng": ["X"]},
        "description": {"eng": ["우리가 안 물어본 이름으로 온 설명"]},
        "publication-date": "2026-09-01",
        "links": {"html": "https://ted.europa.eu/x"},
    })
    assert row["description"] is None
    assert row["publication_date"] is None
    assert row["links"] is None


def test_description_is_read_when_the_server_sends_it():
    """★09-13~15 실측: 매 갱신 74~77건이 제목 불일치로 버려졌다★
    설명이 오면 읽는다 — 그게 버려지던 공고를 살리는 유일한 길이다."""
    row = ted._flatten({
        "notice-title": {"eng": ["Framework agreement"]},
        ted.TED_DESCRIPTION_FIELD: {"eng": ["Supply of antiviral stockpile"]},
    })
    assert row["description"] == "Supply of antiviral stockpile"


def test_description_match_rescues_a_notice_the_title_would_drop():
    """제목엔 낱말이 없고 설명에만 있는 공고 — 09-05~15 내내 버려지던 모양이다."""
    notice = {"publication_number": "2026/S 9",
              "title": "Framework agreement",
              "description": "Supply of antiviral stockpile",
              "buyer_name": "HERA", "buyer_country": "BEL",
              "deadline": None, "estimated_value": None,
              "currency": None, "links": None, "publication_date": None}
    assert ted._confirm(notice, "antiviral") == "description"

    # 'antiviral' 낱말에만 걸리게 한다 — 모든 낱말에 같은 공고를 물리면
    # 나머지 낱말에서 버려져 버림 수가 의미를 잃는다.
    def only_antiviral(keyword, begin, end, fields=None):
        return [notice] if keyword == "antiviral" else []

    with patch.object(ted, "_search", side_effect=only_antiviral):
        out = ted.watch_ted(days=7)
    assert out["bid_count"] == 1                 # 제목만 봤으면 0 이었다
    assert out["dropped_unconfirmed"] == 0
    assert out["description_checked"] is True
    assert out["bids"][0]["matched_in"] == "description"


def test_title_only_confirmation_still_drops_unmatched():
    """설명을 못 받으므로 확인이 제목에서만 된다 — 더 엄격해진 것이지
    느슨해진 게 아니다."""
    assert ted._confirm({"title": "Vaccine tender", "description": None}, "vaccine") == "title"
    assert ted._confirm({"title": "Office chairs", "description": None}, "vaccine") is None


# ── '0건'이 감추는 두 상태 (2026-09-05) ──────────────────────────
# 첫 실호출(#29 배포 후)에서 실제로 이 결과가 나왔다:
#   EU/TED 열림 0건 · 임박 0건 ※미검증
# 이게 "이번 주 EU에 정말 없었다"인지 "공고는 왔는데 제목만으로 확인하다
# 다 버렸다"인지 로그만 보고는 구분이 안 됐다.
def test_zero_open_shows_how_many_were_dropped():
    """★핵심★ 0건 뒤에 버려진 개수가 붙어야 '진짜 없음'과 '다 버림'을 가른다."""
    line = procurement_summary({
        "bid_count": 20, "deadline": {"counts": {"open": 20}},
        "ted": {"available": True, "is_verified": False,
                "deadline": {"counts": {"open": 0, "closing_soon": 0}},
                "dropped_unconfirmed": 37, "lookup_failures": 0}})
    assert "열림 0건" in line
    assert "제목 불일치로 버림 37건" in line


def test_genuinely_empty_week_says_nothing_extra():
    """버린 것도 실패한 낱말도 없으면 군더더기를 안 붙인다."""
    line = procurement_summary({
        "bid_count": 20, "deadline": {"counts": {"open": 20}},
        "ted": {"available": True, "is_verified": False,
                "deadline": {"counts": {"open": 0, "closing_soon": 0}},
                "dropped_unconfirmed": 0, "lookup_failures": 0}})
    assert "제목 불일치" not in line
    assert "부분 실패" not in line


def test_partial_lookup_failures_visible_even_on_success():
    """전부 실패가 아니라 일부만 실패해도(watch_ted가 available=True로 넘어온
    경우) 그 사실이 요약 줄에서 사라지면 안 된다."""
    line = procurement_summary({
        "bid_count": 20, "deadline": {"counts": {"open": 20}},
        "ted": {"available": True, "is_verified": False,
                "deadline": {"counts": {"open": 3, "closing_soon": 1}},
                "dropped_unconfirmed": 0, "lookup_failures": 4}})
    assert "부분 실패 4개 낱말" in line


# ── 설명 식별자: 넣되, 거부당하면 스스로 물러선다 (2026-09-15) ──────
#
# ★ 왜 이 장치가 필요한가 ★ `description-lot` 은 문서로만 맞춘 것이고 실호출로
# 확인되지 않았다(샌드박스가 api.ted.europa.eu 로 못 나간다). 그냥 넣었다가
# 틀리면 20개 낱말이 전부 400 이 되고, 조달은 6시간 주기라 EU 감시가 통째로
# 6시간 더 죽는다. 되돌리기 전(제목만 확인)보다 **나빠진다.**
#
# 그래서 400 이면 한 번만 물러서고 나머지는 기존 목록으로 돈다. 맞으면 76건이
# 살아나고, 틀리면 요청 한 번 더 쓰고 오늘과 똑같이 동작한다.


def _run_with(responses):
    """_search 를 가로채 (fields 목록, 반환값) 자취를 남긴다."""
    seen = []

    def fake(keyword, begin, end, fields=None):
        seen.append(list(fields or ted.TED_FIELDS))
        return responses(keyword, len(seen))

    with patch.object(ted, "_search", side_effect=fake):
        out = ted.watch_ted(days=7)
    return out, seen


def test_first_attempt_asks_for_the_description():
    """되돌린 식별자가 실제로 요청에 실리는지 — 안 실리면 76건은 그대로 버려진다."""
    out, seen = _run_with(lambda word, n: [])
    assert ted.TED_DESCRIPTION_FIELD in seen[0]
    assert out["description_checked"] is True


def test_a_400_retreats_once_and_keeps_the_layer_alive():
    """★핵심★ 식별자가 틀려도 층이 죽지 않는다. 같은 낱말을 즉시 다시 물어보고,
    그 뒤로는 기존 목록으로 돈다."""
    def responses(word, n):
        if n == 1:
            return "HTTPError 400: unknown field description-lot"
        return [_notice(f"Vaccine {word}", publication_number=f"P{n}")]

    out, seen = _run_with(responses)
    assert ted.TED_DESCRIPTION_FIELD in seen[0]          # 1회차: 붙여서 시도
    assert ted.TED_DESCRIPTION_FIELD not in seen[1]      # 2회차: 같은 낱말 재시도
    assert out["available"] is True
    assert out["bid_count"] > 0                          # 층이 살아 있다
    assert out["description_checked"] is False           # 물러섰음을 값에 담는다


def test_the_retreat_happens_only_once_not_per_keyword():
    """낱말마다 다시 시험하면 20개가 전부 두 번씩 나간다 — 판정은 한 번이면 족하다."""
    def responses(word, n):
        return "HTTPError 400: unknown field" if n == 1 else []

    _out, seen = _run_with(responses)
    asked = [f for f in seen if ted.TED_DESCRIPTION_FIELD in f]
    assert len(asked) == 1


def test_a_timeout_does_not_trigger_the_retreat():
    """★사유가 처방을 가른다★ 400 은 '요청이 틀렸다'이고 타임아웃은 '네트워크'다.
    네트워크 때문에 식별자를 버리면, 멀쩡한 식별자를 영영 못 쓰게 된다."""
    _out, seen = _run_with(lambda word, n: "Timeout")
    assert all(ted.TED_DESCRIPTION_FIELD in f for f in seen)


def test_retreat_is_visible_in_the_log_line():
    """물러선 사실이 로그에 안 나오면, 버림 수가 줄었을 때 설명을 읽어서인지
    공고가 없어서인지 또 구분이 안 된다 — #30 이 고친 것과 같은 모양의 함정."""
    base = {"bid_count": 20, "deadline": {"counts": {"open": 20}}}
    retreated = procurement_summary({**base, "ted": {
        "available": True, "is_verified": False,
        "deadline": {"counts": {"open": 0, "closing_soon": 0}},
        "dropped_unconfirmed": 76, "lookup_failures": 0,
        "description_checked": False}})
    assert "설명 식별자 거부됨" in retreated
    assert "제목 불일치로 버림 76건" in retreated

    checked = procurement_summary({**base, "ted": {
        "available": True, "is_verified": False,
        "deadline": {"counts": {"open": 0, "closing_soon": 0}},
        "dropped_unconfirmed": 3, "lookup_failures": 0,
        "description_checked": True}})
    assert "제목·설명 불일치로 버림 3건" in checked
    assert "거부됨" not in checked


def test_description_checked_survives_the_valhalla_wiring(monkeypatch):
    """★배선이 키를 손으로 고른다★ watch_ted 가 아무리 잘 담아도 valhalla_watch
    가 안 옮기면 요약 줄까지 안 온다 — 09-15 에 실제로 그럴 뻔했고, 요약 함수를
    직접 부르는 테스트만 있어서 안 잡혔다. 끝에서 끝까지 한 번은 지나가야 한다."""
    from algorithms import valhalla_watch as vw

    monkeypatch.setattr(
        "algorithms.procurement_watch.watch_bids",
        lambda days=7: {"available": True, "bid_count": 0, "excluded_count": 0,
                        "source": "나라장터", "bids": []})
    monkeypatch.setattr(
        "algorithms.procurement_ted.watch_ted",
        lambda days=7: {"available": True, "bid_count": 0, "bids": [],
                        "dropped_unconfirmed": 76, "lookup_failures": [],
                        "is_verified": False, "unverified_note": "n",
                        "description_checked": False})

    value = vw._fetch_procurement()
    assert value["ted"]["description_checked"] is False
    assert "설명 식별자 거부됨" in procurement_summary(value)

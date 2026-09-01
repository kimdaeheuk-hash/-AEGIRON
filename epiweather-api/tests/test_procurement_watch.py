"""조달 감시가 **못 짚는 것을 보고하지 않는지** 지킨다 (2026-09-02).

## 왜 만들었나

캡틴이 받아둔 공공데이터포털 키에 나라장터만 열려 있었다. 국가사업은 입찰
공고로 먼저 나오고 2~3주 뒤 닫히므로, 늦게 알면 그걸로 끝이다.

## ★ 이 파일이 막는 두 가지 ★

**1. 서버가 준 것을 그대로 믿는 것.** 나라장터 검색은 느슨하다. 실측에서
`bidNtceNm=방역` 에 *"청소년 해외역사탐방 여행사 위탁 용역"* 이 딸려 왔다.
학교 수학여행을 바이오안보 입찰로 보고하면 그 보고서는 두 번 안 읽힌다.

**2. 낱말은 맞는데 다른 세상인 것.** 실측 7일치에서 다섯 건이 그랬다:

    공공비축미 매입용 포대        '비축' 이 쌀이었다
    백신 라이센스(V3)            '백신' 이 안티바이러스였다
    유전체물성연구소 헬륨3 가스    '유전체' 가 연구소 이름이었다

그런데 **조용히 버리면 안 된다.** 낱말 표가 진짜 공고를 잘못 자를 수 있고,
그때 눈에 보여야 고칠 수 있다.
"""
from __future__ import annotations

import datetime as dt

import pytest

from algorithms import procurement_watch as pw
from algorithms.procurement_watch import BIOSECURITY_KEYWORDS, FALSE_FRIENDS, watch_bids


def _item(title, no="A1", ord_="000", clsfc="의료용품", budget="50000000"):
    return {"bidNtceNo": no, "bidNtceOrd": ord_, "bidNtceNm": title,
            "ntceInsttNm": "질병관리청", "dminsttNm": "질병관리청",
            "bidNtceDt": "2026-09-01 10:00:00", "bidClseDt": "2026-09-08 10:00:00",
            "asignBdgtAmt": budget, "bidNtceDtlUrl": "https://g2b.example/1",
            "pubPrcrmntClsfcNm": clsfc}


def _patched(monkeypatch, by_keyword, key="dummy"):
    """낱말별 응답을 정해두고, 물리는 낱말만 답한다."""
    monkeypatch.setattr(pw, "_key", lambda: key)

    def fake(keyword, operation, begin, end, k, rows=100):
        if operation != "getBidPblancListInfoServcPPSSrch":
            return []                                  # 용역만 답하게 해서 중복 배제
        return list(by_keyword.get(keyword, []))
    monkeypatch.setattr(pw, "_search", fake)


# ── 근거 없는 결과는 버린다 ────────────────────────────────────────────────

def test_server_noise_without_the_word_is_dropped(monkeypatch):
    """★★핵심★★ 낱말을 짚지 못하는 공고는 버린다.

    실측에서 '방역' 검색에 여행사 공고가 딸려 왔다. 서버가 왜 줬는지는 모르지만,
    우리가 근거를 못 대면 보고하지 않는다.
    """
    _patched(monkeypatch, {"방역": [_item("청소년 해외역사탐방 여행사 위탁 용역",
                                         clsfc="운송서비스")]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 0
    assert out["dropped_unconfirmed"] == 1


def test_match_records_where_it_was_found(monkeypatch):
    """어디서 걸렸는지 남긴다 — 못 짚는 건 애초에 통과하지 못한다."""
    _patched(monkeypatch, {"감염병": [_item("2026 감염병 대응 역량강화 용역")]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 1
    assert out["bids"][0]["matched_in"] == "bidNtceNm"


def test_classification_counts_as_evidence(monkeypatch):
    """공고명이 애매해도 조달분류명에 낱말이 있으면 진짜다."""
    _patched(monkeypatch, {"방역": [_item("2026년 상반기 위탁 용역", clsfc="방역서비스")]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 1
    assert out["bids"][0]["matched_in"] == "pubPrcrmntClsfcNm"


# ── 같은 낱말, 다른 세상 ──────────────────────────────────────────────────

@pytest.mark.parametrize("title", [
    "2026년산 공공비축미 매입용 포대 제작",
    "26년 스마트생태공장 구축사업-심야전력 비축 활용장치",
    "제어감시시스템 백신 라이센스(V3) 구매",
    "유전체물성연구소 헬륨3 가스 1 SET 구매",
    "국가 희귀·특산식물 보전을 위한 참조 유전체 정보 구축",
])
def test_false_friends_are_excluded(monkeypatch, title):
    """★핵심★ 실측에서 걸린 오탐 다섯 건이 다시 들어오지 않는다."""
    word = next(w for ws in BIOSECURITY_KEYWORDS.values() for w in ws if w in title)
    _patched(monkeypatch, {word: [_item(title)]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 0, f"오탐이 통과했다: {title}"
    assert out["excluded_count"] == 1


def test_exclusions_are_not_silent(monkeypatch):
    """★★핵심★★ 뺀 것을 조용히 없애지 않는다 — 사유와 함께 돌려준다.

    낱말 표가 언젠가 진짜 공고를 잘못 자른다. 그때 눈에 보여야 고칠 수 있다.
    """
    _patched(monkeypatch, {"비축": [_item("2026년산 공공비축미 매입용 포대 제작")]})

    out = watch_bids(days=7)

    (dropped,) = out["excluded"]
    assert "공공비축미" in dropped["title"]
    assert "쌀" in dropped["reason"], "왜 뺐는지가 없다"


def test_real_pest_control_survives_when_it_is_also_infectious_disease(monkeypatch):
    """★핵심★ '해충방역' 이라도 감염병이 같이 있으면 남긴다.

    실측의 '남대문쪽방촌 감염병 방역 및 해충방역' 이 정확히 이 경우다.
    오탐을 자르다가 진짜를 자르면 더 나쁘다.
    """
    _patched(monkeypatch, {"방역": [_item("2026 남대문쪽방촌 감염병 방역 및 해충방역")]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 1
    assert out["excluded_count"] == 0


# ── 정직성 경계선 ─────────────────────────────────────────────────────────

def test_missing_key_is_not_an_empty_result(monkeypatch):
    """★★핵심★★ 키가 없는 것을 '공고 없음' 으로 바꾸지 않는다.

    섞으면 키가 만료된 날 "이번 주엔 국가사업 공고가 없었다" 고 보고하게 된다.
    """
    for name in pw._KEY_NAMES:
        monkeypatch.delenv(name, raising=False)

    out = watch_bids(days=7)

    assert out["available"] is False
    assert "키가 없다" in out["reason"]
    assert "bids" not in out and "bid_count" not in out


@pytest.mark.parametrize("name", ["DATA_GO_KR_KEY", "KDCA_API_KEY"])
def test_either_key_name_works(monkeypatch, name):
    """★핵심★ 운영엔 예전 이름(KDCA_API_KEY)으로 들어 있다 — 같은 키다.

    실측(2026-09-02) 지문 대조로 두 값이 동일함을 확인했다. 새 이름만 보면
    운영에서 조용히 "키 없음" 이 되어 공고가 통째로 사라진다.
    """
    for other in pw._KEY_NAMES:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(name, "dummy-key")

    assert pw._key() == "dummy-key"


def test_new_name_wins_when_both_are_set(monkeypatch):
    """둘 다 있으면 맞는 이름(DATA_GO_KR_KEY)을 쓴다."""
    monkeypatch.setenv("DATA_GO_KR_KEY", "new")
    monkeypatch.setenv("KDCA_API_KEY", "old")

    assert pw._key() == "new"


def test_lookup_failure_is_reported_not_swallowed(monkeypatch):
    """일부 낱말 조회가 실패하면 그 사실을 들고 나온다."""
    monkeypatch.setattr(pw, "_key", lambda: "dummy")
    monkeypatch.setattr(pw, "_search",
                        lambda *a, **k: "조회 실패: ConnectionError")

    out = watch_bids(days=7)

    assert out["available"] is True
    assert out["bid_count"] == 0
    assert out["lookup_failures"], "전부 실패했는데 조용히 0건으로 냈다"
    assert "ConnectionError" in out["lookup_failures"][0]


def test_budget_is_labelled_as_assigned_not_awarded(monkeypatch):
    """★핵심★ 배정예산을 낙찰가로 팔지 않는다 — 이름에 담는다."""
    _patched(monkeypatch, {"백신": [_item("인플루엔자 백신 구매", budget="58203500")]})

    bid = watch_bids(days=7)["bids"][0]

    assert bid["assigned_budget_krw"] == 58203500
    assert "assigned" in "".join(bid)      # 키 이름 자체가 배정임을 밝힌다
    assert not any("awarded" in k or "price" in k for k in bid)


def test_report_does_not_claim_eligibility(monkeypatch):
    """★★핵심★★ '우리가 딸 수 있는 사업' 목록이 아니라고 밝힌다.

    참가자격은 공고문 HWP 안에 있고 이 API 로는 안 보인다.
    """
    _patched(monkeypatch, {"감염병": [_item("감염병 대응 용역")]})

    out = watch_bids(days=7)

    assert out["is_eligibility_check"] is False
    limits = " ".join(out["limits"])
    assert "참가자격" in limits and "아니다" in limits
    assert "낙찰가가 아니다" in limits
    assert "표에 없는 이름을 단 공고는 걸리지 않는다" in limits
    assert "순위를 매기지 않는다" in limits


def test_same_notice_is_not_counted_twice(monkeypatch):
    """여러 낱말에 걸린 한 공고를 두 건으로 세지 않는다."""
    same = _item("감염병 백신 비축 용역")
    _patched(monkeypatch, {"감염병": [same], "백신": [dict(same)], "비축": [dict(same)]})

    out = watch_bids(days=7)

    assert out["bid_count"] == 1


def test_window_is_capped(monkeypatch):
    """조회 기간 상한을 넘기지 않는다 — API 가 거절한다."""
    _patched(monkeypatch, {})

    assert watch_bids(days=999)["window_days"] == pw.MAX_WINDOW_DAYS
    assert watch_bids(days=0)["window_days"] == 1


def test_every_false_friend_has_a_reason():
    """★핵심★ 제외 규칙에는 전부 사유가 붙어 있다 — 근거 없이 자르지 않는다."""
    for phrase, reason in FALSE_FRIENDS.items():
        assert reason.strip() and len(reason) > 4, f"{phrase} 에 사유가 없다"


def test_keywords_are_not_too_generic():
    """★핵심★ 흔한 낱말을 넣으면 하루치가 수백 건이 되고 아무도 안 본다."""
    words = [w for ws in BIOSECURITY_KEYWORDS.values() for w in ws]

    for banned in ("검사", "조사", "관리", "구매", "용역", "시스템"):
        assert banned not in words, f"'{banned}' 는 너무 흔하다"
    assert all(len(w) >= 2 for w in words), "한 글자 낱말은 아무 데나 걸린다"

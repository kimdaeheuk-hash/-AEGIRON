"""같은 나라 설명불가 사건이 둘이면 하나가 **흔적 없이 사라졌다** (2026-10-12).

## 배경

#67(10-09)이 설명불가 경보 키를 나라 단위(`unexplained:{ISO3}`)로 묶었다. 그 수리는
맞다 — 같은 이르쿠츠크 사건을 `Irkutsk, Russia` / `러시아 시베리아` 로 달리 추출해
폰이 이틀 연속 울리던 것을 막았다. 소킹 일지 10-08 의 '결정 대기' 항목이었다.

그런데 그 수리에 **관측되지 않은 대가**가 딸려 있었다. `db.upsert_alert` 는 이렇다:

    ON CONFLICT(alert_date, source) DO UPDATE SET
        tier = excluded.tier, label = excluded.label,
        score = excluded.score, evidence = excluded.evidence

옛 코드는 `scan_unexplained()` 가 준 사건마다 후보를 따로 만들어 이 경로를 그대로
탔다. 같은 나라 사건이 둘이면 **마지막 것이 앞의 것을 통째로 덮어쓴다** — 제목도
근거도. 화면에도 로그에도 근거에도 남지 않아 **'한 건뿐'과 구별할 수 없었다.**
경보 피로가 아니라 조용한 정보 손실이다. 이 저장소가 반복해서 당한 그 모양이다.

## 이 수리의 입장

합치는 것 자체는 유지한다(폰을 두 번 울리지 않는다). **잃지만 않으면 된다** —
개수는 제목에, 사건 목록은 근거 **첫 줄**에(텔레그램은 앞 두 줄만 보낸다), 원문은
전부 싣는다. 판정·점수·통보 시점은 건드리지 않는다.

## ⚠️ 관측된 사고가 아니다

로그 보존 기간(2026-09-01~10-12) 전체에서 설명불가 경보는 이르쿠츠크 **한 사건**
뿐이었고, 같은 나라 동시 발생은 **0건**이다. 이것은 코드를 읽어 확정한 결함이지
프로덕션에서 본 사고가 아니다. 그래서 수리도 표시에만 머문다 — 그리고 합침이 실제로
일어나기 시작하면 `🧷 [alerts]` 로그가 세어 준다. 임베딩 같은 유사도 판정을 붙일지는
그 숫자가 모인 뒤에 결정할 일이다(지금은 문턱을 정할 근거가 없다).

## 합침 조건은 생각보다 좁다 (시험을 쓰다가 확인)

`resolve_countries` 는 **위치 문구에 나라 이름이 들어 있을 때만** 나라를 읽는다:
`Irkutsk, Russia`·`러시아 시베리아`·`Moscow, Russia` → `RUS` 이지만 `Moscow` 단독은 `[]`
(도시명은 나라 사전에 없다). 즉 두 사건이 한 키로 묶이려면 **둘 다** 나라가 읽히는
문구여야 한다. 이 제약 자체가 묶임을 더 드물게 만든다 — 그래서 더더욱, 지금 필요한
것은 유사도 판정이 아니라 묶였을 때 잃지 않는 것과 그 횟수를 세는 것이다.
"""
from __future__ import annotations

import db
from algorithms.alerts import unexplained_candidates

TODAY = "2026-10-12"


def _a(location, raw_disease="질병불명", raw_text="원문", extracted_at=f"{TODAY}T21:04:00",
       source="unexplained_cluster"):
    return {"source": source, "location": location, "raw_disease_text": raw_disease,
            "raw_text": raw_text, "extracted_at": extracted_at}


# ── 옛 동작의 재현 — 왜 합쳐야 하는가 ───────────────────────────

def test_old_behaviour_silently_lost_the_first_event(isolated_db):
    """★ 옛 동작을 DB 로 그대로 재현한다 ★ 같은 (날짜, source) 로 두 번 upsert 하면
    먼저 온 제목과 근거가 사라진다. 이 성질이 살아 있는 한, 같은 나라 사건마다
    후보를 따로 만드는 코드는 조용한 손실을 낸다."""
    db.upsert_alert(TODAY, "unexplained:RUS", "critical",
                    "설명불가 신호 · Irkutsk, Russia (질병불명)", 100.0,
                    evidence=["원문 발췌: 이르쿠츠크 연구원 사망"])
    db.upsert_alert(TODAY, "unexplained:RUS", "critical",
                    "설명불가 신호 · Moscow, Russia (원인불명 폐렴)", 100.0,
                    evidence=["원문 발췌: 모스크바 집단 폐렴"])

    rows = db.list_alerts(TODAY)
    assert len(rows) == 1
    joined = " ".join(rows[0]["evidence"]) + rows[0]["label"]
    assert "모스크바" in joined
    assert "이르쿠츠크" not in joined      # ← 사라졌다. 이 수리가 막는 손실이다.


# ── 단건은 예전 문구 그대로 (회귀 방지) ─────────────────────────

def test_a_single_event_keeps_the_exact_wording_that_went_to_the_phone():
    """10-07·10-08 에 실제로 폰으로 나간 줄이다 — 바꾸지 않는다."""
    cands, notes = unexplained_candidates([_a("Irkutsk, Russia")], TODAY)

    assert len(cands) == 1
    assert cands[0]["source"] == "unexplained:RUS"
    assert cands[0]["label"] == "설명불가 신호 · Irkutsk, Russia (질병불명)"
    assert cands[0]["score"] == 100.0
    assert cands[0]["evidence"] == [
        "위치: Irkutsk, Russia",
        "모델이 추출한 원문 질병명: 질병불명 — 기존 알려진 패턴과 불일치 판정",
        "원문 발췌: 원문",
    ]
    assert notes == []                     # 합침이 없으면 로그도 없다


def test_single_event_with_missing_fields_still_reads():
    cands, _ = unexplained_candidates([_a(None, raw_disease=None, raw_text=None)], TODAY)
    assert cands[0]["label"] == "설명불가 신호 · 지역불명 (질병불명)"
    assert cands[0]["evidence"][0] == "위치: 불명"


# ── 합쳐도 잃지 않는다 ──────────────────────────────────────────

def test_two_events_in_one_country_become_one_row():
    """행은 하나다 — 폰을 두 번 울리지 않는다는 #67 의 입장을 유지한다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", raw_text="이르쿠츠크 연구원 사망"),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴", raw_text="모스크바 집단 폐렴")], TODAY)

    assert len(cands) == 1
    assert cands[0]["source"] == "unexplained:RUS"
    assert cands[0]["score"] == 100.0


def test_the_count_is_in_the_title():
    """제목에서 개수를 숨기면 합친 것이 손실처럼 보인다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia"), _a("Moscow, Russia", raw_disease="원인불명 폐렴")], TODAY)
    assert cands[0]["label"] == "설명불가 신호 · Irkutsk, Russia (질병불명) + 같은 나라 1건"


def test_every_merged_event_survives_in_the_evidence():
    """★ 이 수리의 핵심 ★ 합쳐진 사건의 위치·질병·원문이 전부 남아야 한다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", raw_text="이르쿠츠크 연구원 사망"),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴", raw_text="모스크바 집단 폐렴"),
         _a("Kazan, Russia", raw_disease="급성 간염", raw_text="카잔 소아 간염")], TODAY)
    joined = " ".join(cands[0]["evidence"])

    for fragment in ("Irkutsk, Russia", "Moscow, Russia", "Kazan, Russia",
                     "원인불명 폐렴", "급성 간염",
                     "이르쿠츠크 연구원 사망", "모스크바 집단 폐렴", "카잔 소아 간염"):
        assert fragment in joined, f"{fragment} 를 잃었다"


def test_no_event_is_truncated_more_than_another():
    """★ 리뷰에서 잡은 손실 ★ 1번 원문을 폰 미리보기 줄(80자)에만 두면 1번만
    짧게 잘려 2번 이후(120자)보다 불리해진다. 손실을 막는 수리가 1번에서 손실을
    만드는 셈이다 — 모든 사건이 같은 길이로 남아야 한다."""
    long_a = "가" * 200
    long_b = "나" * 200
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", raw_text=long_a),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴", raw_text=long_b)], TODAY)
    joined = " ".join(cands[0]["evidence"])

    assert long_a[:120] in joined, "1번 원문이 120자로 남지 않았다"
    assert long_b[:120] in joined, "2번 원문이 120자로 남지 않았다"


def test_the_merge_is_visible_in_the_first_two_evidence_lines():
    """★ 텔레그램은 근거 앞 두 줄만 보낸다 ★ 묶였다는 사실이 셋째 줄로 밀리면
    폰에서 안 보이고, 그러면 합친 것이 다시 손실이 된다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", raw_text="이르쿠츠크 연구원 사망"),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴")], TODAY)
    head = " ".join(cands[0]["evidence"][:2])

    assert "2건" in head
    assert "Irkutsk, Russia" in head and "Moscow, Russia" in head
    assert "원인불명 폐렴" in head
    # 모델 판단이라는 정직 표시도 폰에 가는 두 줄 안에 남아야 한다.
    assert "불일치 판정" in head


def test_merging_is_logged():
    """제목·근거에만 있으면 '왜 한 행인가'를 경보 표에서 거꾸로 읽어야 한다."""
    _, notes = unexplained_candidates(
        [_a("Irkutsk, Russia"), _a("Moscow, Russia", raw_disease="원인불명 폐렴")], TODAY)

    assert len(notes) == 1
    assert "설명불가 2건" in notes[0]
    assert "unexplained:RUS" in notes[0]


# ── 갈라야 하는 것은 갈린다 ────────────────────────────────────

def test_different_countries_stay_separate():
    cands, notes = unexplained_candidates(
        [_a("Irkutsk, Russia"), _a("Mumbai, India", raw_disease="원인불명 발열")], TODAY)

    assert sorted(c["source"] for c in cands) == ["unexplained:IND", "unexplained:RUS"]
    assert notes == []                     # 합친 게 없다


def test_unreadable_locations_are_not_lumped_together():
    """나라를 못 읽는 위치끼리 한 덩어리가 되면 안 된다 — 키가 원문 위치로 남는다."""
    cands, _ = unexplained_candidates(
        [_a("시베리아"), _a("북부 고원지대", raw_disease="원인불명 발열")], TODAY)
    assert sorted(c["source"] for c in cands) == [
        "unexplained:북부 고원지대", "unexplained:시베리아"]


# ── 후보 자격 (예전 필터 유지) ─────────────────────────────────

def test_only_active_search_qualifies():
    """who_wpro 같은 일반 지역동향 요약은 질병명이 없는 게 흔해 critical 오탐이 된다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", source="who_wpro")], TODAY)
    assert cands == []


def test_only_todays_extractions_qualify():
    """아니면 과거 발견이 매일 영원히 재후보로 뜬다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", extracted_at="2026-10-07T21:02:00")], TODAY)
    assert cands == []


def test_a_stale_event_does_not_drag_todays_event_into_a_merge():
    """어제 사건이 섞여 들어오면 개수가 틀리고 로그가 거짓이 된다."""
    cands, notes = unexplained_candidates(
        [_a("Irkutsk, Russia", extracted_at="2026-10-07T21:02:00"),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴")], TODAY)

    assert len(cands) == 1
    assert cands[0]["label"] == "설명불가 신호 · Moscow, Russia (원인불명 폐렴)"   # 합침 표시 없음
    assert notes == []


def test_missing_extracted_at_is_not_treated_as_today():
    cands, _ = unexplained_candidates([{**_a("Irkutsk, Russia"), "extracted_at": None}], TODAY)
    assert cands == []


# ── 끝에서 끝까지 — 합친 행이 DB 에 온전히 남는다 ───────────────

def test_the_merged_row_survives_the_upsert_that_used_to_lose_it(isolated_db):
    """위 `test_old_behaviour_silently_lost_the_first_event` 와 같은 입력을 새 경로로
    넣는다. 행은 하나지만 두 사건이 **둘 다** DB 에 남는다."""
    cands, _ = unexplained_candidates(
        [_a("Irkutsk, Russia", raw_text="이르쿠츠크 연구원 사망"),
         _a("Moscow, Russia", raw_disease="원인불명 폐렴", raw_text="모스크바 집단 폐렴")], TODAY)
    for c in cands:
        db.upsert_alert(TODAY, c["source"], "critical", c["label"], c["score"],
                        evidence=c["evidence"])

    rows = db.list_alerts(TODAY)
    assert len(rows) == 1
    joined = " ".join(rows[0]["evidence"]) + rows[0]["label"]
    assert "이르쿠츠크 연구원 사망" in joined      # 옛 경로에서 사라졌던 쪽
    assert "모스크바 집단 폐렴" in joined

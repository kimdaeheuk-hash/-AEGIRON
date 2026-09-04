"""준비태세 범위 분리 — "대응제" 정의를 고르는 대신 셋으로 나눈다.

발할라 점검(2026-09-04)에서 나온 것: 준비태세 축이 수기 등록 5건만 보고 위협
8종의 커버리지율을 계산하고 있었다. 그런데 국제 비축(WHO ICG 5종)과 임상
파이프라인(ClinicalTrials 17종)은 **이미 매일 받아오면서도** 판정에 한 번도
안 들어갔다 — compute_readiness 가 db.list_countermeasures() 만 보기 때문.

여기서 가장 조심하는 것은 셋을 합치지 않는 것이다. 창고에 있는 것, 국제 체계가
들고 있는 것, 아직 임상 중인 것은 대비 수준이 전혀 다르다.
"""
from __future__ import annotations

from algorithms import readiness_scopes as rsc

THREATS = [
    {"pathogen": "Ebola"},        # ICG 비축 있음
    {"pathogen": "H5N1"},         # 격차로 등재(비축 없음)
    {"pathogen": "MERS"},         # 격차로 등재
    {"pathogen": "Plague"},       # 어느 표에도 없음 → 모른다
]

CMS = [
    {"name": "에볼라 백신", "targets": ["Ebola"],
     "declared_efficacy": 0.9, "domestic_producible": False},
    {"name": "국산 H5N1 백신", "targets": ["H5N1"],
     "declared_efficacy": None, "domestic_producible": True},   # 효능 미기재
]

PIPE = {"stages": {"에볼라": "stockpiled", "인플루엔자(조류·계절)": "late_trial",
                   "MERS": "early_trial"}}


# ── 합치지 않는다 ────────────────────────────────────────────────
def test_four_scopes_and_no_combined_score():
    """★핵심★ 하나의 준비도 점수로 합치면 '임상 중이니까 대비됨'이 되어버린다.
    범위가 늘어도(A-2 에서 승인 제품이 넷째로 붙었다) 합치지 않는 원칙은 그대로다."""
    r = rsc.readiness_by_scope(CMS, THREATS, PIPE)
    assert set(r["scopes"]) == {"national_stockpile", "international_stockpile",
                                "approved_products", "clinical_pipeline"}
    assert r["combined_score"] is None
    assert "합치면" in r["why_no_combined_score"]


def test_clinical_scope_refuses_to_report_a_coverage_rate():
    """★핵심★ 3상 진행 중은 지금 쓸 수 있는 물량이 아니다. 비율을 내면 안 된다."""
    c = rsc.clinical_scope(THREATS, PIPE)
    assert c["coverage_rate"] is None
    assert "보유 물량이 아니다" in c["why_no_coverage_rate"]
    assert "커버리지가 아니다" in c["does_not_mean"]


def test_every_scope_carries_what_it_does_not_mean():
    """숫자만 떼어 자료에 옮겨도 경계선이 따라가야 한다."""
    r = rsc.readiness_by_scope(CMS, THREATS, PIPE)
    for scope in r["scopes"].values():
        assert scope["does_not_mean"]


# ── 모르는 것을 격차로 세지 않는다 ───────────────────────────────
def test_unknown_pathogen_is_not_counted_as_a_gap():
    """★회귀★ Plague 는 ICG 표에도 격차 표에도 없다. '비축 없음'이 아니라 '모른다'다.
    모르는 것을 격차로 접으면 없는 위기를 만들어낸다."""
    intl = rsc.international_scope(THREATS)
    assert intl["unknown"] == 1
    assert "Plague" in intl["unknown_names"]
    assert "Plague" not in intl["uncovered_names"]


def test_unknown_is_excluded_from_the_denominator():
    """분모에 넣으면 이름을 못 알아본 것 때문에 커버리지가 낮아진다."""
    intl = rsc.international_scope(THREATS)
    # 판정된 것은 Ebola(있음) + H5N1·MERS(없음) = 3종
    assert intl["coverage_rate"] == round(1 / 3, 3)


def test_pipeline_not_asked_about_is_unknown_not_absent():
    """파이프라인이 안 물어본 병원체와 '등록 연구 없음'은 다르다."""
    c = rsc.clinical_scope([{"pathogen": "Plague"}], PIPE)
    assert c["unknown"] == 1 and c["no_registered_trial"] == 0


# ── 이름 다리 (영문 위협 ↔ 한글 파이프라인 키) ───────────────────
def test_english_threat_names_reach_korean_pipeline_keys():
    """★핵심 회귀★ DEFAULT_THREATS 는 영문(H5N1), 파이프라인 키는 한글
    (인플루엔자(조류·계절))이다. 다리를 안 놓으면 전부 미커버로 잡힌다."""
    assert rsc._resolve_ko("H5N1") == "인플루엔자(조류·계절)"
    assert rsc._resolve_ko("Ebola") == "에볼라"
    assert rsc._resolve_ko("Anthrax") == "탄저"
    assert rsc._resolve_ko("Plague") is None       # 모르면 None — 지어내지 않는다


def test_h5n1_lands_in_advanced_through_the_bridge():
    c = rsc.clinical_scope([{"pathogen": "H5N1"}], PIPE)
    assert c["advanced"] == 1
    assert c["advanced_names"] == ["인플루엔자(조류·계절)"]


# ── 없으면 없다고 한다 ───────────────────────────────────────────
def test_empty_countermeasures_is_unavailable_not_zero():
    """0%로 내보내면 '대비가 전혀 안 됐다'는 발견처럼 읽힌다. 등록이 없을 뿐이다."""
    n = rsc.national_scope([], THREATS)
    assert n["available"] is False
    assert n["countermeasure_count"] == 0
    assert "시연값" in n["reason"]


def test_missing_pipeline_is_unavailable_not_zero():
    c = rsc.clinical_scope(THREATS, None)
    assert c["available"] is False
    assert "24시간 주기" in c["reason"]


def test_national_scope_keeps_unrated_separate():
    """효능 미기재를 미커버로 접지 않는다(2026-09-03 에 고친 그 구분)."""
    n = rsc.national_scope(CMS, THREATS)
    assert n["covered"] == 1          # 에볼라만 효능 기재
    assert n["unrated"] == 1          # 국산 H5N1 백신은 판정 불가


# ── 로그 한 줄 ───────────────────────────────────────────────────
def test_summary_shows_each_scope_separately():
    line = rsc.scope_summary(rsc.readiness_by_scope(CMS, THREATS, PIPE))
    assert "국가비축" in line and "국제비축" in line and "임상" in line


def test_summary_returns_none_when_nothing():
    assert rsc.scope_summary(None) is None
    assert rsc.scope_summary({}) is None
    assert rsc.scope_summary({"error": "boom"}) is None


def test_valhalla_snapshot_carries_scopes(monkeypatch, tmp_path):
    """배선 회귀 — 계산해놓고 스냅샷에 안 실으면 아무도 못 본다."""
    from algorithms import valhalla_watch as vw
    monkeypatch.setattr(vw, "STATE_FILE", tmp_path / "valhalla_state.json")
    monkeypatch.setattr(vw, "_fetch_procurement", lambda: {"bid_count": 0})
    monkeypatch.setattr(vw, "_fetch_pipeline", lambda: PIPE)

    snap = vw.valhalla_snapshot()
    scopes = snap["readiness_by_scope"]["scopes"]
    assert scopes["clinical_pipeline"]["available"] is True
    assert snap["readiness_by_scope"]["combined_score"] is None

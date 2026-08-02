"""Tier 2 백필 — 과거 공식 선언(라벨)+GDELT 실제 뉴스량(특징)으로 지금 학습.
GDELT는 mock. 핵심: 실제로 학습셋이 조립돼 학습되는지 + 네트워크 실패 시 지어내지
않는지(정직) 검증."""
from __future__ import annotations
import datetime as dt
from unittest.mock import patch

from algorithms import nowcast_backfill as bf
from algorithms import historical_outbreaks as ho


def _fake_timeline(query, start, end):
    """선언 근처에서 뉴스량이 치솟는 가짜 GDELT 타임라인(선언 앞뒤로 상승)."""
    pts = []
    d = start
    # 창의 마지막(=선언 직전~직후)에 가까울수록 볼륨↑ — 조기 뉴스 상승 모사
    span = (end - start).days or 1
    while d <= end:
        frac = (d - start).days / span
        vol = 0.1 if frac < 0.7 else 2.0 + (frac - 0.7) * 10   # 후반부 급상승
        pts.append((d, vol))
        d += dt.timedelta(days=1)
    return pts


def test_backfill_timeline_loads_official_declarations(isolated_db):
    n = bf.backfill_timeline()
    assert n == len(ho.OUTBREAKS)
    import db
    ids = {e["event_id"] for e in db.list_timeline_events()}
    assert "ebola_cod_pheic_2019" in ids


def test_backfill_signals_skips_when_gdelt_unreachable(isolated_db):
    """GDELT가 None(차단)이면 신호를 지어내지 않고 0건 — 정직."""
    with patch("algorithms.nowcast_backfill.fetch_coverage_timeline", return_value=None):
        created = bf.backfill_signals_for(ho.OUTBREAKS[0])
    assert created == 0


def test_backfill_signals_creates_dated_signals(isolated_db):
    with patch("algorithms.nowcast_backfill.fetch_coverage_timeline", side_effect=_fake_timeline):
        created = bf.backfill_signals_for(ho.OUTBREAKS[4])   # ebola_cod_pheic_2019
    assert created > 0
    import db
    sigs = db.list_extracted_signals(limit=1000)
    assert any(s["country_iso3"] == "COD" and s["source"] == bf.BACKFILL_SOURCE for s in sigs)
    # 신호 날짜가 선언(2019-07-17) 이전 창에도 존재 → 양성 라벨의 '이전 신호'
    decl = dt.date(2019, 7, 17)
    dates = [dt.date.fromisoformat(s["signal_date"]) for s in sigs if s["signal_date"]]
    assert any(d < decl for d in dates)


def test_run_backfill_and_train_learns_on_real_labels(isolated_db):
    """백필 전체 → 학습셋 조립 → 베이스라인 학습이 실제로 됨(프레임워크 작동 증명).
    정확도는 retrospective로 라벨링되고 전향검증 경고가 유지되는지 확인."""
    with patch("algorithms.nowcast_backfill.fetch_coverage_timeline", side_effect=_fake_timeline):
        out = bf.run_backfill_and_train()
    assert out["backfill"]["signals_created"] > 0
    assert out["readiness"]["positives"] >= 10      # 게이트 통과(양성 충분)
    assert out["readiness"]["negatives"] >= 10
    assert out["training"]["trained"] is True
    assert out["training"]["accuracy_kind"] == "retrospective_backtest"
    assert any("전향적" in c for c in out["training"]["caveats"])


def test_gdelt_blocked_yields_no_training(isolated_db):
    """이 샌드박스처럼 GDELT 차단이면 학습셋이 안 차서 학습 거부 — 정직."""
    with patch("algorithms.nowcast_backfill.fetch_coverage_timeline", return_value=None):
        out = bf.run_backfill_and_train()
    assert out["backfill"]["signals_created"] == 0
    assert out["backfill"]["gdelt_reachable"] is False
    assert out["training"]["trained"] is False


# ── 커버리지 정직성(GDELT 속도제한으로 대다수가 비는 경우) ────────
def _fake_fetch(succeed_for: set):
    """지정한 사건만 데이터를 주고 나머지는 None(429·차단 상황 재현)."""
    import datetime as dt

    def fetch(query, start, end):
        if not any(k in query for k in succeed_for):
            return None
        return [(start + dt.timedelta(days=i), float(i)) for i in range(30)]
    return fetch


def test_low_event_coverage_is_reported_not_called_complete(monkeypatch, isolated_db):
    """★핵심 회귀★ 16건 중 2건만 수집됐는데 총 신호 수가 0이 아니라는 이유로
    'gdelt_reachable=True, 수집 완료'로 보고됐다. 라벨 87.5%가 비었으면 완료가 아니다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({"Kivu", "Guinea"}))
    out = nb.run_backfill()
    assert out["signals_created"] > 0          # 신호는 있지만
    assert out["coverage_sufficient"] is False  # 커버리지는 불충분
    assert out["event_coverage"] < 0.6
    assert "⚠" in out["note"] and "불충분" in out["note"]
    assert len(out["events_missing"]) > 10


def test_sufficient_coverage_reports_cleanly(monkeypatch, isolated_db):
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({'"'}))  # 전부 매칭
    out = nb.run_backfill()
    assert out["coverage_sufficient"] is True
    assert out["event_coverage"] == 1.0
    assert "⚠" not in out["note"]


def test_zero_coverage_distinguished_from_partial(monkeypatch, isolated_db):
    """한 건도 못 받은 것과 일부만 받은 것은 다른 상태다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", lambda q, s, e: None)
    out = nb.run_backfill()
    assert out["gdelt_reachable"] is False and out["events_covered"] == 0
    assert "한 건도" in out["note"]


def test_training_carries_coverage_warning(monkeypatch, isolated_db):
    """소수 사건으로 학습해도 trained=True는 그대로 뜬다 — 경고가 결과에 붙어야 한다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({"Kivu"}))
    out = nb.run_backfill_and_train()
    training = out["training"]
    if training.get("trained"):
        assert "coverage_warning" in training
        assert training["caveats"][0] == training["coverage_warning"]


# ── 증분 실행(속도제한 때문에 나눠 돌려야 함) ────────────────────
def test_second_run_skips_already_backfilled_events(monkeypatch, isolated_db):
    """★핵심★ GDELT 속도제한으로 한 번에 다 못 채운다(실측 6/16). 나눠 돌려
    빈 곳만 메워야 하는데, 이미 채운 사건을 다시 긁으면 신호가 중복돼 학습셋이
    왜곡되고 GDELT 호출도 낭비된다."""
    import algorithms.nowcast_backfill as nb
    calls = []

    def counting_fetch(query, start, end):
        calls.append(query)
        return _fake_fetch({"Kivu"})(query, start, end)

    monkeypatch.setattr(nb, "fetch_coverage_timeline", counting_fetch)
    first = nb.run_backfill()
    assert first["signals_created"] > 0
    calls_after_first = len(calls)

    second = nb.run_backfill()
    assert second["signals_created"] == 0                  # 새로 만든 신호 없음
    assert "ebola_cod_kivu_2018" in second["skipped_already_backfilled"]
    # 이미 채운 사건은 GDELT를 다시 부르지 않는다
    assert len(calls) == calls_after_first + (16 - 1)


def test_covered_events_stay_covered_across_runs(isolated_db, monkeypatch):
    """건너뛴 사건이 '미수집'으로 세지면 나눠 돌릴수록 커버리지가 떨어져 보인다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({"Kivu"}))
    nb.run_backfill()
    second = nb.run_backfill()
    assert "ebola_cod_kivu_2018" not in second["events_missing"]
    assert second["events_covered"] >= 1


def test_force_refetches_everything(isolated_db, monkeypatch):
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({"Kivu"}))
    nb.run_backfill()
    forced = nb.run_backfill(force=True)
    assert forced["signals_created"] > 0
    assert forced["skipped_already_backfilled"] == []


# ── 스케줄러용 maintain(다 차면 멈춤) ─────────────────────────────
def test_maintain_skips_entirely_when_coverage_sufficient(monkeypatch, isolated_db):
    """★비용 핵심★ 커버리지가 차면 GDELT를 아예 부르지 않아야 한다 —
    매일 불러도 비용이 0이어야 스케줄러에 물릴 수 있다."""
    import algorithms.nowcast_backfill as nb
    calls = []
    monkeypatch.setattr(nb, "already_backfilled",
                        lambda: {o["event_id"] for o in nb.ho.OUTBREAKS})
    monkeypatch.setattr(nb, "fetch_coverage_timeline",
                        lambda q, s, e: calls.append(q))
    out = nb.maintain()
    assert out["action"] == "skipped" and calls == []
    assert out["event_coverage"] >= nb.MIN_EVENT_COVERAGE


def test_maintain_caps_events_per_run(monkeypatch, isolated_db):
    """한 번에 16건을 긁으면 12~17분 걸린다 — 회차당 작업량을 묶고 나머지는 이월."""
    import algorithms.nowcast_backfill as nb
    calls = []

    def fetch(query, start, end):
        calls.append(query)
        return _fake_fetch({'"'})(query, start, end)

    monkeypatch.setattr(nb, "fetch_coverage_timeline", fetch)
    out = nb.maintain(max_events=3)
    assert len(calls) == 3
    assert len(out["backfill"]["deferred_to_next_run"]) == len(nb.ho.OUTBREAKS) - 3


def test_maintain_retrains_only_when_new_signals(monkeypatch, isolated_db):
    """새로 채운 게 없으면 재학습을 건너뛴다 — 같은 데이터로 반복 학습할 이유가 없다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", lambda q, s, e: None)
    out = nb.maintain(max_events=2)
    assert out["training"]["trained"] is False
    assert "재학습 생략" in out["training"]["reason"]


def test_maintain_marks_coverage_still_short(monkeypatch, isolated_db):
    """기준에 못 미치면 학습 결과에 '아직 미달'이 붙어야 한다."""
    import algorithms.nowcast_backfill as nb
    monkeypatch.setattr(nb, "fetch_coverage_timeline", _fake_fetch({"Kivu"}))
    out = nb.maintain(max_events=16)
    training = out.get("training") or {}
    if training.get("trained"):
        assert "기준 미달" in training.get("coverage_warning", "")

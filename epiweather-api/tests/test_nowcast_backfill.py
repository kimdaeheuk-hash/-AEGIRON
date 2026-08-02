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

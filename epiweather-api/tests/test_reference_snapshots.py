"""기준 스냅샷 신선도·갱신 — "파일이 있다"와 "데이터가 최신이다"를 가른다.

발할라 점검(2026-09-04)에서 나온 것: 백신 공급(284건)·국가 역량(194개국)이
정적 파일에 얹혀 있는데 **나이를 재는 코드가 코드베이스에 하나도 없었다.**
갱신 스크립트는 있는데 주간작업이 안 불렀다. 파일이 몇 달 묵어도 시스템은
계속 available: true 로 답한다.

여기서 가장 조심하는 것은 갱신 자체가 아니라 **갱신이 데이터를 망가뜨리지 않는
것**이다. 원본은 우리 것이 아니라 언제든 모양이 바뀌고, 검증 없이 덮으면 파서가
깨진 날 멀쩡하던 스냅샷이 사라진다(8월 KDCA 쉼표 사고와 같은 모양).
"""
from __future__ import annotations

import datetime as dt
import json
from unittest.mock import patch

import pytest

from algorithms import reference_snapshots as rs


@pytest.fixture
def snapdir(tmp_path, monkeypatch):
    """스냅샷 디렉터리를 임시로. 테스트가 진짜 기준 파일을 건드리면 안 된다."""
    monkeypatch.setattr(rs, "REFERENCE_DIR", tmp_path)
    return tmp_path


def _write(snapdir, name, payload):
    (snapdir / rs.SNAPSHOTS[name]["filename"]).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _vaccine_payload(count=284, date=None):
    return {
        "source": "WHO Prequalified Vaccines (사전적격성 목록)",
        "source_url": rs.SNAPSHOTS["vaccine_supply"]["filename"],
        "snapshot_date": date or dt.date.today().isoformat(),
        "records": [{"vaccine_type": f"V{i}", "manufacturer": "M"} for i in range(count)],
    }


# ── 나이 측정 ────────────────────────────────────────────────────
def test_age_days_counts_from_snapshot_date():
    today = dt.datetime(2026, 9, 4, tzinfo=dt.timezone.utc)
    assert rs.age_days("2026-09-02", now=today) == 2
    assert rs.age_days("2026-06-04", now=today) == 92


def test_unreadable_date_is_stale_not_fresh(snapdir):
    """★핵심★ 날짜를 못 읽으면 '신선하다'고 우기지 않는다. 모르면 묵은 것으로 본다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(date="언제였더라"))
    s = rs.snapshot_status("vaccine_supply")
    assert s["age_days"] is None
    assert s["stale"] is True
    assert "읽을 수 없다" in s["reason"]


def test_missing_file_is_absent_and_stale(snapdir):
    s = rs.snapshot_status("vaccine_supply")
    assert s["present"] is False and s["stale"] is True
    assert s["record_count"] == 0


def test_fresh_snapshot_is_not_stale(snapdir):
    _write(snapdir, "vaccine_supply", _vaccine_payload())
    s = rs.snapshot_status("vaccine_supply")
    assert s["stale"] is False
    assert s["record_count"] == 284


def test_snapshot_past_max_age_is_stale(snapdir):
    old = (dt.date.today() - dt.timedelta(days=200)).isoformat()
    _write(snapdir, "vaccine_supply", _vaccine_payload(date=old))
    s = rs.snapshot_status("vaccine_supply")
    assert s["stale"] is True
    assert "묵음" in s["reason"]


def test_report_lists_stale(snapdir):
    old = (dt.date.today() - dt.timedelta(days=200)).isoformat()
    _write(snapdir, "vaccine_supply", _vaccine_payload(date=old))
    r = rs.report()
    assert "vaccine_supply" in r["stale_snapshots"]
    assert "ihr_capacity" in r["stale_snapshots"]     # 파일 자체가 없다
    assert r["fresh_count"] == 0


# ── 좋은 데이터를 나쁜 것으로 덮지 않는다 ────────────────────────
def test_validate_rejects_far_too_few(snapdir):
    ok, why = rs.validate("vaccine_supply", _vaccine_payload(count=3))
    assert ok is False and "너무 적다" in why


def test_validate_rejects_sudden_shrink(snapdir):
    """★핵심 회귀★ 절대 하한만으로는 못 잡는 경우. 284건이 150건으로 줄면
    하한(100건)은 통과하지만 원본이 깨진 것이다 — 덮으면 134건이 사라진다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    ok, why = rs.validate("vaccine_supply", _vaccine_payload(count=150))
    assert ok is False and "급감" in why


def test_validate_allows_normal_growth(snapdir):
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    ok, why = rs.validate("vaccine_supply", _vaccine_payload(count=290))
    assert ok is True and why is None


def test_validate_allows_small_shrink(snapdir):
    """정상적인 목록 축소(품목 폐지 등)까지 막으면 영영 갱신이 안 된다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    ok, _ = rs.validate("vaccine_supply", _vaccine_payload(count=270))
    assert ok is True


# ── 갱신: 실패해도 기존 파일은 살아야 한다 ───────────────────────
def test_fetch_failure_keeps_existing_file(snapdir):
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               side_effect=RuntimeError("WHO 502")):
        out = rs.refresh("vaccine_supply")
    assert out["refreshed"] is False and "수집 실패" in out["reason"]
    assert rs.snapshot_status("vaccine_supply")["record_count"] == 284   # 그대로


def test_rejected_payload_keeps_existing_file(snapdir):
    """★그 사고 그대로★ 원본 표 구조가 바뀌어 0건이 왔다. 덮으면 안 된다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               return_value=_vaccine_payload(count=0)):
        out = rs.refresh("vaccine_supply")
    assert out["refreshed"] is False and "검증 거부" in out["reason"]
    assert rs.snapshot_status("vaccine_supply")["record_count"] == 284


def test_successful_refresh_writes_and_reports(snapdir):
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               return_value=_vaccine_payload(count=300)):
        out = rs.refresh("vaccine_supply")
    assert out["refreshed"] is True and out["record_count"] == 300
    assert rs.snapshot_status("vaccine_supply")["record_count"] == 300


def test_refresh_records_outcome_in_capability_ledger(snapdir):
    """갱신이 매번 조용히 실패하는 상태를 /api/status에서 볼 수 있어야 한다."""
    from algorithms import capability_ledger as cl

    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               side_effect=RuntimeError("WHO 502")):
        rs.refresh("vaccine_supply")
    s = cl.status("snapshot_vaccine_supply", configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_FAILED
    assert "WHO 502" in s["last_error"]

    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               return_value=_vaccine_payload(count=284)):
        rs.refresh("vaccine_supply")
    assert cl.status("snapshot_vaccine_supply", configured=True)["verified"] is True


# ── 갱신 뒤 소비자가 새 값을 보는가 ──────────────────────────────
def test_refresh_clears_consumer_cache(snapdir, monkeypatch):
    """★조용한 실패★ 소비자는 파일을 lru_cache로 읽는다. 캐시를 안 비우면
    파일을 새로 써도 같은 프로세스는 옛 값을 계속 본다 — 수집기는 재배포 전까지
    안 죽으므로 '갱신했다'는 로그만 남고 실제로는 몇 주가 그대로 간다."""
    from algorithms import vaccine_supply

    target = snapdir / rs.SNAPSHOTS["vaccine_supply"]["filename"]
    monkeypatch.setattr(vaccine_supply, "REFERENCE", target)
    vaccine_supply._snapshot.cache_clear()

    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    assert len(vaccine_supply._snapshot()["records"]) == 284      # 캐시에 태운다

    with patch("algorithms.reference_fetch.fetch_vaccine_supply",
               return_value=_vaccine_payload(count=300)):
        rs.refresh("vaccine_supply")

    assert len(vaccine_supply._snapshot()["records"]) == 300      # 새 값이 보여야 한다
    vaccine_supply._snapshot.cache_clear()


# ── 묵은 것만 받는다 ─────────────────────────────────────────────
def test_refresh_due_skips_fresh_and_refreshes_stale(snapdir):
    """안 바뀐 걸 매주 긁을 이유가 없다. 신선한 것은 원본을 부르지도 않는다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))       # 오늘자
    old = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    _write(snapdir, "ihr_capacity",
           {"snapshot_date": old, "scores": {f"C{i}": {} for i in range(194)}})

    with patch("algorithms.reference_fetch.fetch_vaccine_supply") as pq, \
            patch("algorithms.reference_fetch.fetch_ihr_capacity",
                  return_value={"snapshot_date": dt.date.today().isoformat(),
                                "scores": {f"C{i}": {} for i in range(194)}}) as gho:
        out = rs.refresh_due()

    pq.assert_not_called()                       # 신선해서 안 부름
    gho.assert_called_once()                     # 묵어서 부름
    assert [s["name"] for s in out["skipped_fresh"]] == ["vaccine_supply"]
    assert out["refreshed"][0]["name"] == "ihr_capacity"
    assert out["refreshed"][0]["refreshed"] is True


def test_atomic_write_leaves_no_debris_on_failure(snapdir):
    """쓰다 죽어도 기존 파일이 안 깨지고 임시 파일도 안 남아야 한다."""
    _write(snapdir, "vaccine_supply", _vaccine_payload(count=284))
    with patch("algorithms.reference_snapshots.json.dump",
               side_effect=OSError("디스크 가득")), \
            patch("algorithms.reference_fetch.fetch_vaccine_supply",
                  return_value=_vaccine_payload(count=300)):
        out = rs.refresh("vaccine_supply")

    assert out["refreshed"] is False and "저장 실패" in out["reason"]
    assert rs.snapshot_status("vaccine_supply")["record_count"] == 284
    assert list(snapdir.glob("*.tmp")) == []

"""예측 존재증명(Phase 44) — 정규화 해시·캘린더 제출·확인 로직 검증.
실제 캘린더 서버 호출은 mock(단, 라이브 왕복 테스트로 실제 동작은
이미 별도 확인함 — 2026-07-27, a.pool.opentimestamps.org 실제 제출 성공)."""
from __future__ import annotations
import hashlib
from unittest.mock import patch, MagicMock

from algorithms.prediction_timestamp import (
    canonical_hash, submit_timestamp, check_timestamp, CALENDAR_URLS,
)


def test_canonical_hash_deterministic():
    pred = {"id": 1, "predicted_at": "2026-07-27T00:00:00Z", "country": "KOR",
            "disease": "Ebola", "risk_score": 80.0, "basis": ["a", "b"]}
    h1 = canonical_hash(pred)
    h2 = canonical_hash(dict(pred))  # 같은 내용 재구성
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_canonical_hash_ignores_verification_fields():
    """예측 시점 이후에 채워지는 verified_at 등은 해시에 영향 없어야 함
    — '예측 시점에 뭘 알고 있었는지'만 증명하는 게 목적."""
    base = {"id": 1, "predicted_at": "2026-07-27T00:00:00Z", "country": "KOR",
            "disease": "Ebola", "risk_score": 80.0, "basis": ["a"]}
    verified = dict(base, verified_at="2026-08-01T00:00:00Z", correct=True, lead_days=5)
    assert canonical_hash(base) == canonical_hash(verified)


def test_canonical_hash_changes_with_content():
    a = {"id": 1, "predicted_at": "t", "country": "KOR", "disease": "X", "risk_score": 1.0, "basis": ["a"]}
    b = dict(a, risk_score=2.0)
    assert canonical_hash(a) != canonical_hash(b)


def test_submit_timestamp_success_on_first_calendar():
    fake_ts = MagicMock()
    fake_ts.serialize = MagicMock()
    with patch("algorithms.prediction_timestamp.RemoteCalendar") as MockCal, \
         patch("algorithms.prediction_timestamp.BytesSerializationContext") as MockCtx:
        MockCal.return_value.submit.return_value = fake_ts
        MockCtx.return_value.getbytes.return_value = b"\x01\x02\x03"
        result = submit_timestamp("ab" * 32)
    assert result == "010203"
    MockCal.assert_called_with(CALENDAR_URLS[0])


def test_submit_timestamp_falls_back_to_next_calendar_on_failure():
    fake_ts = MagicMock()
    with patch("algorithms.prediction_timestamp.RemoteCalendar") as MockCal, \
         patch("algorithms.prediction_timestamp.BytesSerializationContext") as MockCtx:
        instances = [MagicMock(), MagicMock()]
        instances[0].submit.side_effect = Exception("timeout")
        instances[1].submit.return_value = fake_ts
        MockCal.side_effect = instances
        MockCtx.return_value.getbytes.return_value = b"\xff"
        result = submit_timestamp("cd" * 32, calendar_urls=["https://x", "https://y"])
    assert result == "ff"


def test_submit_timestamp_all_calendars_fail_returns_none():
    with patch("algorithms.prediction_timestamp.RemoteCalendar") as MockCal:
        MockCal.return_value.submit.side_effect = Exception("blocked")
        result = submit_timestamp("ef" * 32)
    assert result is None


def test_check_timestamp_malformed_proof_returns_unavailable():
    digest_hex = hashlib.sha256(b"x").hexdigest()
    result = check_timestamp(digest_hex, "not-a-valid-hex-proof-00")
    assert result["data_available"] is False


def test_check_timestamp_pending_when_not_yet_confirmed():
    digest_hex = hashlib.sha256(b"x").hexdigest()
    with patch("algorithms.prediction_timestamp.Timestamp") as MockTimestamp:
        MockTimestamp.deserialize.return_value = MagicMock()
        with patch("algorithms.prediction_timestamp.RemoteCalendar") as MockCal:
            MockCal.return_value.get_timestamp.return_value = None
            result = check_timestamp(digest_hex, "aa" * 20)
    assert result["data_available"] is True
    assert result["confirmed"] is False


def test_check_timestamp_confirmed_when_calendar_returns_upgrade():
    digest_hex = hashlib.sha256(b"x").hexdigest()
    with patch("algorithms.prediction_timestamp.Timestamp") as MockTimestamp:
        MockTimestamp.deserialize.return_value = MagicMock()
        with patch("algorithms.prediction_timestamp.RemoteCalendar") as MockCal:
            MockCal.return_value.get_timestamp.return_value = MagicMock()  # 업그레이드됨
            result = check_timestamp(digest_hex, "aa" * 20, calendar_urls=["https://x"])
    assert result["data_available"] is True
    assert result["confirmed"] is True
    assert result["calendar_url"] == "https://x"

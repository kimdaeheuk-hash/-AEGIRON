"""능력 장부 — 상태 필드가 '설정됐나' 대신 '실제로 돌았나'를 답하는지.

이 장부가 없어서 난 실측 사고 4건: NIM 배선 누락(nim_configured=true인데 몇 주째
Claude), 온프렘 문서 층 누출(full_onprem인데 PDF는 클라우드행), 선행일수 18일
(실측 0건), 정확도 0.988(다수 클래스). 넷 다 코드가 안 죽고 상태 필드만
부풀었다 — 그래서 아무 소리도 안 났다. 아래 테스트가 그 조용함을 막는다.
"""
from __future__ import annotations

import datetime as dt
import json
from unittest.mock import patch

from algorithms import capability_ledger as cl
from algorithms import nvidia

# 장부 격리는 conftest 의 _isolate_capability_ledger 가 전역으로 한다 —
# 계측이 실제 호출 경로에 붙어 있어서 이 파일만 격리하면 다른 테스트가
# 운영 장부에 가짜 성공을 적는다(실측으로 확인됨).


def _clear_nvidia(monkeypatch):
    for env in (nvidia.SHARED_KEY_ENV, nvidia.TEXT_KEY_OVERRIDE_ENV,
                nvidia.ONPREM_BASE_ENV, nvidia.TEXT_BASE_URL_ENV):
        monkeypatch.delenv(env, raising=False)


# ── 설정과 관측의 구분 ───────────────────────────────────────────
def test_configured_but_never_run_is_not_verified():
    """★핵심★ 설정만 되고 한 번도 안 불린 능력. NIM이 몇 주 갇혀 있던 바로 그 칸이다.
    실패도 아니고 성공도 아닌 제3의 상태로 정직하게 표시돼야 한다."""
    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_CONFIG      # not_configured도 failed도 아님
    assert s["observations"] == 0


def test_not_configured_is_distinct_from_configured_but_unused():
    """'설정 안 함'과 '설정했는데 안 씀'은 전혀 다른 상태다 — 후자만 사고다."""
    assert cl.status("x", configured=False)["claim_basis"] == cl.BASIS_ABSENT
    assert cl.status("x", configured=True)["claim_basis"] == cl.BASIS_CONFIG


def test_success_makes_it_verified():
    cl.record("nvidia_text", ok=True, endpoint="https://integrate.api.nvidia.com/v1")
    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is True
    assert s["claim_basis"] == cl.BASIS_VERIFIED
    assert s["last_success_at"] is not None


def test_failure_after_success_drops_verified():
    """마지막 성공이 창 안이어도 그 뒤로 계속 실패 중이면 지금은 검증된 게 아니다."""
    cl.record("nvidia_text", ok=True, endpoint="u")
    cl.record("nvidia_text", ok=False, endpoint="u", detail="ConnectTimeout")
    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_FAILED
    assert "ConnectTimeout" in s["last_error"]


def test_old_success_goes_stale():
    """옛 성공이 오늘의 고장을 가리면 안 된다."""
    old = (dt.datetime.now(dt.timezone.utc)
           - dt.timedelta(hours=cl.VERIFY_WINDOW_HOURS + 1)).isoformat()
    cl.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    cl.LEDGER_FILE.write_text(json.dumps(
        {"nvidia_text": {"last_success_at": old, "total_successes": 1,
                         "consecutive_failures": 0}}), encoding="utf-8")
    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_STALE


def test_report_lists_unverified():
    cl.record("nvidia_text", ok=True, endpoint="u")
    cl.record("nvidia_document", ok=False, endpoint="u", detail="boom")
    r = cl.report()
    assert r["verified_count"] == 1
    assert r["unverified"] == ["nvidia_document"]


def test_ledger_write_failure_never_claims_success(monkeypatch):
    """장부 저장이 실패해도 기능은 살아야 하지만, 없는 성공을 있다고 하면 안 된다."""
    monkeypatch.setattr(cl, "_save", lambda data: None)   # 저장 실패 흉내
    cl.record("nvidia_text", ok=True, endpoint="u")
    assert cl.status("nvidia_text", configured=True)["verified"] is False


# ── 주권: 설정(의도) vs 관측(사실) ───────────────────────────────
def test_onprem_configured_but_unobserved_is_not_verified_sovereign(monkeypatch):
    """★핵심 회귀★ 온프렘으로 설정만 해두면 sovereignty_posture는 full_onprem이지만,
    아무 층도 안 불려봤으면 그건 검증된 주권이 아니라 의도일 뿐이다."""
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.ONPREM_BASE_ENV, "https://nim.internal.aegiron.kr")

    assert nvidia.sovereignty_posture() == "full_onprem"     # 설정
    v = nvidia.sovereignty_verification()                    # 관측
    assert v["verified_full_onprem"] is False
    assert set(v["unverified_layers"]) == {"genome", "document", "text"}


def test_all_layers_observed_sovereign_verifies(monkeypatch):
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.ONPREM_BASE_ENV, "https://nim.internal.aegiron.kr")
    for layer in ("genome", "document", "text"):
        nvidia.record_layer_call(layer, "https://nim.internal.aegiron.kr/v1", ok=True)

    v = nvidia.sovereignty_verification()
    assert v["verified_full_onprem"] is True
    assert v["unverified_layers"] == []
    assert v["layers_observed_leaving_sovereign_boundary"] == []


def test_document_layer_leaking_to_cloud_is_caught(monkeypatch):
    """★그 사고 그대로★ 온프렘 설정인데 문서 층만 클라우드로 나간 경우.
    예전엔 full_onprem으로 보고했다. 이제 관측이 그걸 뒤집어야 한다."""
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.ONPREM_BASE_ENV, "https://nim.internal.aegiron.kr")
    nvidia.record_layer_call("genome", "https://nim.internal.aegiron.kr/v1", ok=True)
    nvidia.record_layer_call("text", "https://nim.internal.aegiron.kr/v1", ok=True)
    nvidia.record_layer_call("document", "https://integrate.api.nvidia.com/v1", ok=True)

    v = nvidia.sovereignty_verification()
    assert v["verified_full_onprem"] is False
    assert v["layers_observed_leaving_sovereign_boundary"] == ["document"]
    # 설정은 여전히 full_onprem이라고 말한다 — 그래서 둘을 같이 실어야 한다.
    assert nvidia.sovereignty_posture() == "full_onprem"


def test_nvidia_status_carries_both_intent_and_observation(monkeypatch):
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "k")
    s = nvidia.nvidia_status()
    assert s["any_nvidia_key_present"] is True     # 키는 있다
    assert s["any_nvidia_verified"] is False       # 하지만 돈 적은 없다
    assert s["verified_full_onprem"] is False
    assert all(svc["claim_basis"] == cl.BASIS_CONFIG for svc in s["services"])


# ── 실제 호출 경로에 계측이 붙어 있는가 ─────────────────────────
def test_nim_call_records_into_the_ledger(monkeypatch):
    """★배선 회귀★ 계측이 떨어지면 장부가 영영 비고, 그러면 이 모든 구분이 무의미하다."""
    import algorithms.aegiron_model as am
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "k")
    monkeypatch.delenv("AEGIRON_NIM_EXTRACT", raising=False)

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "{}"}}]}

    with patch("requests.post", return_value=_Resp()):
        am.nim_raw("텍스트", am._nim_config())

    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is True
    assert s["last_sovereign"] is False        # 호스팅이라 준주권


def test_nim_failure_is_recorded_not_swallowed(monkeypatch):
    """NIM이 죽으면 폴백은 하되, 죽었다는 사실이 남아야 한다.
    이게 없으면 매번 실패하는데도 상태 필드는 계속 좋게 말한다."""
    import algorithms.aegiron_model as am
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "k")
    monkeypatch.delenv("AEGIRON_NIM_EXTRACT", raising=False)

    with patch("requests.post", side_effect=RuntimeError("502 Bad Gateway")):
        assert am.nim_raw("텍스트", am._nim_config()) is None    # 폴백은 유지

    s = cl.status("nvidia_text", configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_FAILED
    assert "502" in s["last_error"]


def test_provider_status_reports_observation_alongside_configuration(monkeypatch):
    import algorithms.aegiron_model as am
    _clear_nvidia(monkeypatch)
    monkeypatch.setenv(nvidia.SHARED_KEY_ENV, "k")
    monkeypatch.delenv("AEGIRON_NIM_EXTRACT", raising=False)
    monkeypatch.delenv("AEGIRON_LOCAL_MODEL", raising=False)

    ps = am.provider_status()
    assert ps["nim_configured"] is True        # 설정
    assert ps["nim_verified"] is False         # 관측 — 아직 안 돌았다
    assert ps["nim_claim_basis"] == cl.BASIS_CONFIG


# ── 목록에서 사라지지 않기 ───────────────────────────────────────
def test_report_lists_configured_capabilities_that_never_ran():
    """★설계 회귀★ 장부에 기록된 것만 나열하면, 이 모듈이 잡으려는 상태
    ('설정됐는데 한 번도 안 불림')가 목록에서 통째로 빠진다 — 기록이 없으니까.
    없는 게 안 보이면 옛날과 똑같다."""
    cl.record("nvidia_text", ok=True, endpoint="u")
    r = cl.report({"nvidia_text": True, "nvidia_document": True,
                   "telegram_alerting": True})
    names = [c["capability"] for c in r["capabilities"]]
    assert "nvidia_document" in names          # 한 번도 안 불렸지만 보인다
    assert "telegram_alerting" in names
    assert set(r["configured_but_never_run"]) == {"nvidia_document", "telegram_alerting"}
    assert r["verified_count"] == 1


def test_report_without_configured_map_still_lists_recorded():
    cl.record("nvidia_text", ok=True, endpoint="u")
    assert [c["capability"] for c in cl.report()["capabilities"]] == ["nvidia_text"]


# ── 경보 채널 ────────────────────────────────────────────────────
def test_telegram_send_failure_is_recorded(monkeypatch):
    """★가장 위험한 칸★ 알림 실패는 알림으로 알려줄 수 없다(알림이 고장난 거니까).
    토큰만 꽂혀 있고 매번 실패하는 상태가 조용히 지속되면 안 된다."""
    from algorithms import notifier
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")

    class _Resp:
        status_code = 500

    with patch("requests.post", return_value=_Resp()):
        assert notifier.send_telegram_message("x") is False

    s = cl.status(notifier.ALERT_CAPABILITY, configured=True)
    assert s["verified"] is False
    assert s["claim_basis"] == cl.BASIS_FAILED
    assert "500" in s["last_error"]


def test_telegram_send_success_verifies_the_channel(monkeypatch):
    from algorithms import notifier
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")

    class _Resp:
        status_code = 200

    with patch("requests.post", return_value=_Resp()):
        assert notifier.send_telegram_message("x") is True
    assert cl.status(notifier.ALERT_CAPABILITY, configured=True)["verified"] is True


def test_unconfigured_telegram_is_not_counted_as_failure(monkeypatch):
    """안 켠 것과 켰는데 안 되는 것은 다르다 — 전자를 실패로 세면 경보 피로가 된다."""
    from algorithms import notifier
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notifier.send_telegram_message("x") is False
    assert cl.status(notifier.ALERT_CAPABILITY)["observations"] == 0

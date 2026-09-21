"""2026-09-21 점검이 찾은 '실패했는데 사유가 없는' 자리들.

이 리포가 반복해서 고쳐온 한 가지 모양이 또 네 군데 있었다 —
**실패한 건 아는데 왜인지 어디에도 없다.**

| 자리 | 증상 | 대가 |
|---|---|---|
| NIM 빈 응답 | `nvidia_nim_hosted: 실패×5` 상태코드조차 없음 | 09-20 점검이 하루를 잃음 |
| 브리핑 LLM | 조용히 template_fallback, 로그 0줄 | 09-15 추론이 엉뚱한 곳을 고침 |
| Sentinel | 서로 다른 값 2개로 '2배 급등' 판정 | #37 이 고친 걸 세 번째 엔진이 안 씀 |
| 현지어 피드 | 503 이 UTC 08~12시에만 몰리는데 재시도 없음 | 나흘 연속 전멸 |
"""
from __future__ import annotations

import pytest

from algorithms import aegiron_model as am
from algorithms import local_news as ln


# ── NIM — 200 인데 쓸 내용이 없는 갈래 ──────────────────────────────
#
# ★ 실측 (2026-09-20 21:02) ★
#     NLP 구조화 추출: 4건 저장 · … 경로별: nvidia_nim_hosted: 실패×5
#
# 09-18 에 AEGIRON_NIM_MODEL 을 openai/gpt-oss-20b 로 바꾼 뒤 410(EOL) 문자열은
# 사라졌는데, 그 자리에 **상태코드도 없는 `실패`** 가 들어왔다. #32 가 살려낸
# provider_detail 은 예외 경로만 덮었고, 이 갈래는 예외가 아니라 200 이었다.


def test_a_200_with_empty_content_says_why():
    body = {"choices": [{"finish_reason": "length",
                         "message": {"content": "", "reasoning_content": "음..."}}],
            "usage": {"completion_tokens": 300}}
    content, why = am._nim_content(body)
    assert content is None
    assert "finish_reason=length" in why
    assert "reasoning_content 있음" in why
    assert "completion_tokens=300" in why


def test_a_null_content_is_not_the_same_as_an_empty_string():
    """조치가 다르다 — 앞은 모델이 안 채운 것, 뒤는 빈 답을 준 것."""
    null_why = am._nim_content({"choices": [{"message": {"content": None}}]})[1]
    empty_why = am._nim_content({"choices": [{"message": {"content": "   "}}]})[1]
    assert "content=null" in null_why
    assert "빈 문자열" in empty_why
    assert null_why != empty_why


def test_a_malformed_body_does_not_raise():
    """여기서 터지면 사유 대신 스택트레이스가 남는다 — 고치려던 것과 반대다."""
    for body in (None, [], {}, {"choices": []}, {"choices": [None]},
                 {"choices": [{"message": None}]}):
        content, why = am._nim_content(body)
        assert content is None and why


def test_a_usable_content_passes_through():
    content, why = am._nim_content({"choices": [{"message": {"content": "  ok  "}}]})
    assert content == "  ok  " and why == ""


def test_an_empty_response_is_recorded_as_a_failure_not_a_success(monkeypatch):
    """★ 이게 진짜 문제였다 ★ 200 이라 능력 장부에 ok=True 로 찍히고 있었다.

    즉 NIM 이 한 건도 못 뽑는 동안 /api/status 는 그 층을 정상이라고 말했다.
    """
    calls = []
    monkeypatch.setattr(am._nvidia, "record_layer_call",
                        lambda *a, **k: calls.append(k.get("ok")))
    monkeypatch.setattr(am, "build_prompt", lambda t: t, raising=False)

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": ""}}]}

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp())

    content, reason = am.nim_raw_detailed("x", {"base_url": "https://n/v1",
                                                "key": "k", "model": "m"})
    assert content is None
    assert reason and reason.startswith("빈 응답")
    assert calls == [False], "빈 응답을 성공으로 기록하면 안 된다"


def test_the_fallback_word_for_a_missing_reason_points_at_us_not_the_provider(monkeypatch):
    """`실패` 는 외부 고장처럼 읽히는데 실제로는 **우리 계측의 구멍**이다.

    이제 도달할 수 없는 자리지만(빈 응답까지 사유가 붙었다), 만약 새 경로가
    사유 없이 실패하면 그 줄을 보고 NVIDIA 를 쳐다보지 않게 해둔다.
    """
    monkeypatch.setattr(am, "_nim_config",
                        lambda: {"provider": "nvidia_nim_hosted", "sovereign": False,
                                 "base_url": "https://n/v1", "key": "k", "model": "m"})
    monkeypatch.setattr(am, "_nim_extract_detailed", lambda *a, **k: (None, None))
    monkeypatch.setattr(am, "_local_extract", lambda *a, **k: None)
    monkeypatch.setattr(am, "_require_local", lambda: False)

    _result, attempts = am.extract_signal_detailed("x", "s", api_key=None)
    assert attempts[0] == "nvidia_nim_hosted: 사유 없음(계측 누락)"


# ── 현지어 피드 — 한 번만 다시 묻는다 ───────────────────────────────


class _FakeResp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code} Server Error",
                                     response=self)


def test_a_503_is_asked_once_more(monkeypatch):
    seen = []
    replies = [_FakeResp(503), _FakeResp(200, "<item><title>ok</title></item>")]
    monkeypatch.setattr(ln.requests, "get",
                        lambda *a, **k: (seen.append(1), replies[len(seen) - 1])[1])
    monkeypatch.setattr(ln.time, "sleep", lambda *_: None)

    out = ln.fetch_local_feed("gn_kr", "ko", "KOR", "http://x", ["ok"])
    assert out["status"] == "ok"
    assert out["retried"] is True
    assert len(seen) == 2


def test_a_timeout_is_not_retried(monkeypatch):
    """이미 15초를 쓴 뒤다. 179개가 두 번씩 기다리면 주기가 밀린다."""
    import requests
    seen = []

    def _boom(*a, **k):
        seen.append(1)
        raise requests.ReadTimeout("too slow")

    monkeypatch.setattr(ln.requests, "get", _boom)
    out = ln.fetch_local_feed("gn_kr", "ko", "KOR", "http://x", ["ok"])
    assert out["status"] == "error"
    assert len(seen) == 1, "타임아웃은 다시 묻지 않는다"


def test_a_404_is_not_retried(monkeypatch):
    """되풀이해도 결과가 같은 실패에 요청을 두 번 쓰지 않는다."""
    seen = []
    monkeypatch.setattr(ln.requests, "get",
                        lambda *a, **k: (seen.append(1), _FakeResp(404))[1])
    out = ln.fetch_local_feed("gn_kr", "ko", "KOR", "http://x", ["ok"])
    assert out["status"] == "error"
    assert len(seen) == 1


def test_the_rescue_count_survives_a_clean_cycle():
    """★ 판정이 여기 달려 있다 ★ 전부 503 을 맞고 전부 재시도로 살아난 주기는
    겉보기에 완벽히 깨끗한데, 그게 '그 시간대에 스로틀된다'의 가장 강한 증거다.
    실패 줄에만 실으면 그 주기가 통째로 조용해진다."""
    feeds = [{"status": "ok", "retried": True} for _ in range(179)]
    assert ln.failure_summary(feeds) is None, "실패가 없으면 실패 줄은 안 만든다"
    rescued = sum(1 for f in feeds if f.get("status") == "ok" and f.get("retried"))
    assert rescued == 179, "그래도 숫자 자체는 남아야 한다(retried_feeds)"


def test_the_failure_line_carries_the_rescue_count():
    feeds = ([{"status": "error", "reason": "HTTPError 503"} for _ in range(100)]
             + [{"status": "ok", "retried": True} for _ in range(79)])
    line = ln.failure_summary(feeds)
    assert "HTTPError 503×100" in line
    assert "재시도 구제 79건" in line


# ── Sentinel — #37 의 문턱을 안 쓰던 세 번째 엔진 ────────────────────
#
# ★ 실측 (2026-09-20 22:01) ★
#     🚨 Sentinel: 기준선 대비 2배 이상 급등 1건 감지 → 검증 대기열 등록
#        - behavioral/social_cholera: x2.0 (최근값 2 vs 기준선 1)
#
# 마스토돈 콜레라 언급이 1명에서 2명이 된 것이다. #37 이 같은 모양(네이버 축이
# 같은 값을 168번 복제해 '3σ'를 만든 것)을 고치면서 gai·anomaly_engine 양쪽에
# MIN_DISTINCT_HISTORY 를 걸었는데, 같은 iter_metric_series 를 읽는 **세 번째**
# 엔진인 Sentinel 은 그때 빠졌다.


def _series(values):
    """iter_metric_series() 가 내놓는 모양 한 줄."""
    return [("behavioral", "social_cholera", 0.6, list(values))]


@pytest.fixture
def _sentinel(monkeypatch):
    """(급등 스캔 실행기, upsert 기록).

    ★ monkeypatch 로만 바꾼다 ★ 모듈 속성에 직접 대입하면 테스트가 끝나도
    남아서 다음 테스트가 그걸 본다 — conftest 가 품질 상태 파일에 대해 막고
    있는 그 순서 의존을 여기서 새로 만들게 된다.
    """
    from algorithms import sentinel as sn
    monkeypatch.setattr(sn, "load_records", lambda: [])
    upserts = []
    monkeypatch.setattr(sn.db, "upsert_sentinel",
                        lambda **kw: (upserts.append(kw), len(upserts))[1])

    def _run(series):
        monkeypatch.setattr(sn, "iter_metric_series", lambda _r: series)
        return sn.scan_spikes()

    return _run, upserts


def test_two_distinct_values_do_not_make_a_spike(_sentinel):
    """09-20 의 실측 그대로 — [1,1,1,…,1,2] 는 '2배'가 아니라 표본 부족이다."""
    run, upserts = _sentinel
    assert run(_series([1] * 14 + [2])) == []
    assert upserts == [], "대기열에도 안 들어가야 한다"


def test_a_real_spike_with_a_varied_history_still_fires(_sentinel):
    """★ 문턱이 진짜 신호를 죽이면 고치는 것보다 나쁘다 ★"""
    run, upserts = _sentinel
    spikes = run(_series([3, 5, 4, 6, 5, 4, 3, 5, 40]))
    assert len(spikes) == 1
    assert spikes[0]["metric"] == "social_cholera"
    assert upserts, "진짜 급등은 대기열에 들어가야 한다"


def test_sentinel_and_the_other_two_engines_agree(_sentinel):
    """두 엔진이 같은 지표를 두고 다른 말을 하면 그 자체가 고장이다(#37)."""
    from algorithms.signal_metrics import has_enough_distinct_history
    history = [1] * 14
    assert not has_enough_distinct_history(history), "전제: 다른 두 엔진도 보류한다"
    run, _ = _sentinel
    assert run(_series(history + [2])) == [], "Sentinel 만 다른 말을 하면 안 된다"


def test_the_alert_minimum_table_applies_here_too(_sentinel):
    """#36 이 정한 0 근처 카운트 문턱은 이 승격 자리에도 걸린다."""
    run, _ = _sentinel
    # 관측값 1 은 ALERT_MIN_COUNT(2) 미만 — 이상도가 얼마든 승격 안 한다.
    assert run([("genomic", "genomic_new_clades_covid", 0.85,
                 [0, 1, 0, 2, 0, 1, 0, 0, 1])]) == []


# ── 브리핑 — '왜 템플릿인가'가 남는다 ───────────────────────────────


def test_a_dead_llm_leaves_its_reason_on_the_brief():
    """09-18 의 핵심 — 예전엔 template_fallback 이라는 결과만 남고 이유가 증발했다."""
    from algorithms import daily_brief as dbrief

    class _Boom:
        def __init__(self, *a, **k): raise RuntimeError("anthropic 죽음")

    import sys, types
    fake = types.ModuleType("anthropic")
    fake.Anthropic = _Boom
    sys.modules["anthropic"] = fake
    try:
        brief, reason = dbrief._polish_with_llm(
            {"segments": [{"segment_id": "a", "anchor_script": "x", "kind": "quiet"}]},
            "ko", {"id": "duo", "name": {"ko": "대담"}}, "key")
    finally:
        sys.modules.pop("anthropic", None)

    assert brief is None
    assert "RuntimeError" in reason, f"사유가 증발했다: {reason!r}"


def test_a_missing_api_key_and_a_dead_llm_are_different_states():
    """앞은 설정이고 뒤는 사고다 — generation_method 만으로는 안 갈린다."""
    from algorithms import quality_health as qh
    no_key = qh.record_brief_outcome(
        {"ko": {"generation_method": "template_fallback",
                "generation_error": "ANTHROPIC_API_KEY 없음"}}, ["ko"])
    assert any("ANTHROPIC_API_KEY" in k for k in no_key["last_failure_reasons"])

    dead = qh.record_brief_outcome(
        {"ko": {"generation_method": "template_fallback",
                "generation_error": "BadRequestError 400: credit balance too low"}}, ["ko"])
    assert any("credit balance" in k for k in dead["last_failure_reasons"])


# ── 배선 — 계측이 실제로 불리는가 ───────────────────────────────────
#
# 이 리포의 반복 실패 유형: **층은 다 만들어놨는데 아무도 안 부른다.**
# 예측 자동 채점이 0건이었던 것도, 경보 엔진이 스케줄러에 없던 것(#35)도 같다.
# 일곱 번째 불변식은 슬롯이 결과를 남겨야만 볼 게 생긴다 — 그 호출이 사라지면
# 에러 한 줄 없이 브리핑 감시가 꺼진다.


def test_the_brief_job_records_its_outcome():
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    tree = ast.parse((root / "main.py").read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "_run_daily_brief_job")
    names = {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}
    names |= {x.attr for x in ast.walk(node) if isinstance(x, ast.Attribute)}
    assert "record_brief_outcome" in names, (
        "슬롯이 결과를 안 남기면 일곱 번째 불변식은 영영 판정불가다")


def test_recording_the_outcome_cannot_stop_the_broadcast():
    """계측이 방송을 멈추게 할 수는 없다 — 브리핑은 '절대 멈추지 않는다'가 원칙이다."""
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    tree = ast.parse((root / "main.py").read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "_run_daily_brief_job")
    guarded = [t for t in ast.walk(node) if isinstance(t, ast.Try)
               and any("record_brief_outcome" in {x.attr for x in ast.walk(h)
                                                  if isinstance(x, ast.Attribute)}
                       | {x.id for x in ast.walk(h) if isinstance(x, ast.Name)}
                       for h in t.body)]
    assert guarded, "record_brief_outcome 이 try 밖에 있으면 발송을 막을 수 있다"


def test_a_feed_that_failed_twice_is_distinguishable(monkeypatch):
    """★ 판정이 여기서 갈린다 ★ `503 두 번` 은 '그 시간대에 아예 안 받는다',
    `503 한 번` 은 순간 스로틀이다. 예전 모양(반환값)으로는 첫 요청이 예외로
    죽었을 때 재시도 여부를 알 길이 없었다."""
    monkeypatch.setattr(ln.time, "sleep", lambda *_: None)
    monkeypatch.setattr(ln.requests, "get", lambda *a, **k: _FakeResp(503))

    out = ln.fetch_local_feed("gn_kr", "ko", "KOR", "http://x", ["ok"])
    assert out["status"] == "error"
    assert out["retried"] is True

    line = ln.failure_summary([out])
    assert "재시도했는데도 실패 1건" in line


def test_a_baseline_of_all_zeros_and_one_value_is_not_a_spike(_sentinel):
    """★ 두 셈법이 어긋나던 자리 ★ 기준선은 v>0 만 쓰는데 '서로 다른 값'을
    원본에서 세면 0 이 다양성으로 잡힌다 — 평균을 만든 값과 다른 걸 세게 된다."""
    run, _ = _sentinel
    # 원본 distinct = {0, 4} 밖에 없지만 0 이 여럿이라 옛 방식이면 통과했다.
    assert run(_series([0, 0, 0, 0, 0, 4, 4, 4, 4, 40])) == []

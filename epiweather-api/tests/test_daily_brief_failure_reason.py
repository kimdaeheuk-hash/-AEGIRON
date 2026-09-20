"""브리핑이 조용히 실패하던 자리 — 이제 사유를 남긴다 (2026-09-20).

## 왜 이 파일이 있나

`daily_brief.py` 의 두 `except` 가 사유를 증발시켰다:

    daily_brief.py:840   except Exception: return None      ← LLM 폴리시
    daily_brief.py:338   except Exception: alerts = []       ← 경보 조회

그래서 LLM 이 죽어도 조용히 `template_fallback` 으로 떨어진 채 **정상 반환**했다.
예외가 `main.py` 의 `_log_error` 에 닿지 않으니 로그에도 `/api/status` 에도
아무것도 안 남고, 아카이브에는 3개 언어가 그대로 쌓였다.

★ 그 침묵이 점검을 엉뚱한 곳으로 보냈다 ★ 09-15 점검의 추론은 이랬다:

    daily_brief.py   claude-sonnet-4-5  → 매일 3개 언어 성공
    nlp_extract.py   claude-haiku-...   → 매번 400
    → "키·크레딧은 살아 있다. 차이는 모델 ID 하나뿐이다"

**브리핑은 실패할 수가 없는 구조였다.** "매일 성공"은 관측이 아니라 "실패가
보이지 않는다"였고, 크레딧이 말라 있는 동안에도 그 문장은 똑같이 참으로 보였다.
실제 원인은 크레딧 소진이었다(09-18 확인) — 모델 ID 를 고친 하루가 버려졌다.

## 이 파일이 고정하는 것

1. 폴리시가 실패하면 **사유가 브리핑에 실린다**(generation_method 는 그대로 폴백)
2. 예외가 아닌 조용한 실패(형식 불일치)도 남는다
3. 경보 조회가 죽은 것과 '조용한 날'이 구분된다
4. 방송은 그래도 나간다 — "절대 멈추지 않는다"는 설계 원칙은 안 건드린다
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch

from algorithms.daily_brief import _gather, generate_daily_brief


_ACTIVE = {
    "threats": [{"disease": "dengue", "countries": ["BRA"], "merged_score": 82.0,
                 "tier": "high", "source_count": 3, "sources": ["gnews"]}],
    "alerts": [],
    "top_countries": [],
    "name_lookup": {"BRA": "브라질"},
}


def _client_raising(exc):
    client = MagicMock()
    client.messages.create.side_effect = exc
    return client


# ── 1. 폴리시 실패가 사유를 남긴다 ──────────────────────────────────

def test_polish_failure_records_the_provider_message():
    """★이 변경의 핵심★ 09-18 에 크레딧이 말랐을 때 나왔어야 했던 문장."""
    exc = Exception("BadRequestError")
    exc.body = {"error": {"message": "Your credit balance is too low to access the "
                                     "Anthropic API."}}
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", return_value=_client_raising(exc)):
        brief = generate_daily_brief(lang="ko", api_key="sk-test")

    assert brief["generation_method"] == "template_fallback"
    assert "credit balance is too low" in brief["polish_error"]


def test_broadcast_still_goes_out_when_polish_fails():
    """사유를 남기는 것이 방송을 멈추는 대가로 와서는 안 된다 — 브리핑이
    '절대 멈추지 않는다'는 것은 의도된 설계다."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", return_value=_client_raising(RuntimeError("boom"))):
        brief = generate_daily_brief(lang="ko", api_key="sk-test")

    assert brief["segments"] and brief["headline"] and brief["podcast"]
    assert brief["polish_error"]


def test_malformed_response_is_recorded_too():
    """예외가 아닌 조용한 실패 — 호출은 200 인데 JSON 배열이 없다.
    아래 except 에 안 걸리므로 따로 남기지 않으면 또 증발한다."""
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="죄송합니다, 도와드릴 수 없습니다")])
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", return_value=client):
        brief = generate_daily_brief(lang="ko", api_key="sk-test")

    assert brief["generation_method"] == "template_fallback"
    assert "JSON" in brief["polish_error"]


def test_successful_polish_leaves_no_error():
    """깨끗한 성공은 조용해야 한다 — 빈 사유 칸을 만들면 '있다/없다'가 무의미해진다."""
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[MagicMock(
        text='[{"segment_id": "threat-1", "anchor_script": "다듬은 대본"}]')])
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE), \
         patch("anthropic.Anthropic", return_value=client):
        brief = generate_daily_brief(lang="ko", api_key="sk-test")

    assert brief["generation_method"] == "llm_polished"
    assert "polish_error" not in brief


# ── 2. 키가 없는 것과 실패한 것은 다르다 ────────────────────────────

def test_no_api_key_is_marked_as_unavailable_not_failed():
    """키가 없으면 template_fallback 은 설계대로 동작한 것이다. 이 구분이 없으면
    품질 불변식이 운영 선택을 매일 고장으로 울린다."""
    with patch("algorithms.daily_brief._gather", return_value=_ACTIVE):
        brief = generate_daily_brief(lang="ko", api_key=None)

    assert brief["llm_available"] is False
    assert brief["generation_method"] == "template_fallback"
    assert "polish_error" not in brief


# ── 3. 경보 조회 실패 ≠ 조용한 날 ───────────────────────────────────

def test_alerts_engine_failure_leaves_a_reason():
    """예전엔 `except Exception: alerts = []` 라, 경보 엔진이 통째로 터져도
    경보가 없는 조용한 날과 **똑같이** 보였다.

    ★ 사유는 예외 종류까지다 ★ `common.reason_with_detail` 의 계약을 그대로
    쓴다 — 예외 문자열을 그대로 싣지 않는다(#28: 본문에 요청 URL·경로 조각이
    섞여 나올 수 있다). 여기서 필요한 것도 '조용한 날이 아니라 터진 것'이라는
    사실과 종류이고, 공급자가 message 를 채워 보내면 그건 같이 온다
    (아래 test_polish_failure_records_the_provider_message 가 그 갈래다).
    """
    with patch("algorithms.event_dedup.dedupe_events", return_value=[]), \
         patch("algorithms.alerts.refresh_alerts", side_effect=RuntimeError("db is locked")), \
         patch("algorithms.country_risk.rank_countries", return_value={"countries": []}):
        data = _gather()

    assert data["alerts"] == []                 # 방송은 그대로 나간다
    assert data["alerts_error"] == "RuntimeError"


def test_quiet_day_has_no_alerts_error():
    """진짜 조용한 날에는 사유가 없어야 한다 — 그게 이 칸의 쓸모다."""
    with patch("algorithms.event_dedup.dedupe_events", return_value=[]), \
         patch("algorithms.alerts.refresh_alerts",
               return_value={"dashboard": {"top": []}}), \
         patch("algorithms.country_risk.rank_countries", return_value={"countries": []}):
        data = _gather()

    assert data["alerts"] == []
    assert data["alerts_error"] is None


def test_alerts_error_reaches_the_finished_brief():
    """_localized 를 지나 최종 브리핑까지 살아남아야 품질 불변식이 볼 수 있다."""
    broken = {**_ACTIVE, "alerts_error": "RuntimeError: db is locked"}
    with patch("algorithms.daily_brief._gather", return_value=broken):
        brief = generate_daily_brief(lang="ko")

    assert brief["alerts_error"] == "RuntimeError: db is locked"


# ── 4. 배선이 조용히 사라지지 못하게 ────────────────────────────────
#
# 이 리포의 반복된 실패 유형은 "층은 다 만들어놨는데 아무도 안 부른다"다
# (예측 자동 채점이 그래서 0건이었고, 경보 주기가 #35 까지 그랬다).
# 불변식을 만들어도 슬롯이 결과를 안 남기면 영영 판정불가에 머문다.

def test_daily_brief_job_records_the_quality_outcome():
    """★ 이 호출이 사라지면 에러 한 줄 없이 일곱 번째 그물이 꺼진다 ★"""
    import ast
    import pathlib

    src = (pathlib.Path(__file__).resolve().parent.parent / "main.py").read_text("utf-8")
    tree = ast.parse(src)
    job = next(n for n in ast.walk(tree)
               if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
               and n.name == "_run_daily_brief_job")
    names = {n.attr for n in ast.walk(job) if isinstance(n, ast.Attribute)} | \
            {n.id for n in ast.walk(job) if isinstance(n, ast.Name)}
    assert "record_brief_outcome" in names


def test_outcome_is_recorded_before_the_empty_brief_early_return():
    """한 언어도 못 만든 날이야말로 남겨야 하는 날이다. `if not briefs: return`
    아래에서 부르면 **가장 크게 고장 난 날이 기록에서 통째로 빠진다** —
    추출층에서 이미 한 번 고친 함정이다(collector.py 의 층 전체 예외 처리)."""
    import ast
    import pathlib

    src = (pathlib.Path(__file__).resolve().parent.parent / "main.py").read_text("utf-8")
    tree = ast.parse(src)
    job = next(n for n in ast.walk(tree)
               if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
               and n.name == "_run_daily_brief_job")

    record_lines = [n.lineno for n in ast.walk(job) if isinstance(n, ast.Name)
                    and n.id == "record_brief_outcome"]
    # `if not briefs:` 안의 return 줄
    return_lines = [n.lineno for n in ast.walk(job) if isinstance(n, ast.Return)]
    assert record_lines, "전제: 호출이 있다"
    assert min(record_lines) < min(return_lines)

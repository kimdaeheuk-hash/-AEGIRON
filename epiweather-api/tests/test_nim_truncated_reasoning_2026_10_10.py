"""NIM 이 추론 토큰으로 한도를 다 쓰고 본문 전에 잘리던 것 (2026-10-10).

## 배경 (프로덕션 실측, 3일)

    10-07·10-08·10-09 매 AI 슬롯 21:0x UTC — 5/5 가 같은 사유
    nvidia_nim_hosted: 빈응답(content=null, finish_reason=length,
        응답키=annotations·audio·content·function_call·reasoning·
              reasoning_content·refusal·role·tool_calls)×5

#63(10-07)이 '본문 없는 200' 을 성공으로 적던 장부를 고쳐 사유가 보이게 됐고,
그 사유가 사흘 내리 글자 하나 안 변했다. 두 신호가 같은 곳을 가리킨다:

    finish_reason=length   → 한도에 걸려 잘렸다
    응답키에 reasoning_*   → 추론형 모델이다(답 전에 추론 토큰을 먼저 쓴다)

옛 한도 `max_tokens: 300` 은 추론을 안 하는 `meta/llama-3.1-8b-instruct` 에
맞춰 잡은 값이었다. 09-18 에 `AEGIRON_NIM_MODEL` 로 모델만 추론형으로 갈고
한도는 그대로 둬서, 추론이 300 을 다 쓰고 본문 차례에서 끊겼다.

이 파일이 지키는 것:
 1. 한도가 300 이 아니다 — 추론형 모델의 예산을 끊지 않는다
 2. 추론 노력을 'low' 로 **요청한다**(추론이 예산을 덜 먹게)
 3. ★ 그 요청이 거부되면(400·422) 스스로 물러서서 한 번만 다시 부른다 ★
    — 우리가 불러본 적 없는 필드다. 틀렸을 때 슬롯을 잃으면 안 된다(TED #30 과 같은 판단)
 4. 물러섬은 한 번만 판정한다 — 슬롯마다 5번 부르는데 매번 두 번씩 나가지 않게
 5. 401·404·410·타임아웃에는 물러서지 않는다 — 물러서도 안 고쳐진다
 6. 사유에 토큰 숫자가 실린다 — 한도가 또 모자란 것과 다른 원인을 다음 점검이 갈라 읽게
 7. 토큰 칸에 정수가 아닌 것이 오면 버린다(#28 유출 금지 유지)

⚠️ 라이브 검증 못 함 — 샌드박스는 `integrate.api.nvidia.com` 에 막힌다(403).
판정은 다음 AI 슬롯 로그다. 그래서 '요청이 거부되는 경우' 까지 시험으로 못박는다.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

import algorithms.aegiron_model as am


def _nim_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-key")
    monkeypatch.delenv("AEGIRON_NIM_API_KEY", raising=False)
    monkeypatch.delenv("AEGIRON_REQUIRE_LOCAL", raising=False)
    monkeypatch.delenv("AEGIRON_NVIDIA_ONPREM_BASE", raising=False)
    monkeypatch.delenv("AEGIRON_NIM_BASE_URL", raising=False)


@pytest.fixture(autouse=True)
def _fresh_backoff(monkeypatch):
    """물러섬 기억은 프로세스 수명이라 시험 사이에 새어 나간다 — 매번 비운다."""
    monkeypatch.setattr(am, "_REASONING_EFFORT_REJECTED", False)


@pytest.fixture
def ledger(monkeypatch):
    calls = []
    monkeypatch.setattr(am._nvidia, "record_layer_call",
                        lambda layer, url, ok, error=None: calls.append((layer, ok, error)))
    return calls


def _resp(message: dict, finish_reason="stop", usage=None):
    class _R:
        def raise_for_status(self):
            return None

        def json(self):
            body = {"choices": [{"message": message, "finish_reason": finish_reason}]}
            if usage is not None:
                body["usage"] = usage
            return body
    return _R()


class _HTTPish(Exception):
    """상태코드를 들고 다니는 예외 — reason_with_detail 이 `HTTPError <코드>` 로 읽는다."""

    def __init__(self, code):
        super().__init__(f"{code} Client Error")
        self.status_code = code

    def __str__(self):
        return f"{self.status_code} Client Error"


def _payloads(post):
    return [c.kwargs["json"] for c in post.call_args_list]


# ── 1·2. 한도와 추론 노력 ──────────────────────────────────────────────

def test_the_300_token_cap_that_cut_the_body_off_is_gone(monkeypatch, ledger):
    """★핵심★ 옛 한도 300 이 세 슬롯을 비웠다. 그 숫자가 다시 들어오면 깨진다."""
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"content": '{"disease": "x"}'})) as post:
        am.nim_raw_detailed("원문", am._nim_config())
    sent = _payloads(post)[0]["max_tokens"]
    assert sent != 300, "300 은 추론 안 하는 8B 용 한도였다 — 추론형은 본문 전에 잘린다"
    assert sent == am.NIM_MAX_TOKENS >= 1000


def test_low_reasoning_effort_is_actually_requested(monkeypatch, ledger):
    """한도만 올리면 추론이 그 한도까지 쓸 수 있다. 노력도 같이 낮춰 달라고 한다."""
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"content": "{}"})) as post:
        am.nim_raw_detailed("원문", am._nim_config())
    assert _payloads(post)[0]["chat_template_kwargs"] == {"reasoning_effort": "low"}


# ── 3·4·5. 거부당하면 스스로 물러선다 ─────────────────────────────────

@pytest.mark.parametrize("code", [400, 422])
def test_a_rejected_effort_field_makes_it_retry_once_without_it(monkeypatch, ledger, code):
    """★이 수리의 생사★ `chat_template_kwargs` 는 우리가 불러본 적 없는 필드다.
    서버가 거부하면 그 슬롯이 통째로 날아가는 대신, 그 필드만 빼고 한 번 다시 묻는다."""
    _nim_env(monkeypatch)
    answers = [_HTTPish(code), _resp({"content": '{"disease": "x"}'})]
    with patch("requests.post", side_effect=answers) as post:
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content == '{"disease": "x"}' and reason is None, "물러선 뒤 성공은 성공이다"
    first, second = _payloads(post)
    assert "chat_template_kwargs" in first
    assert "chat_template_kwargs" not in second, "물러섰는데 같은 필드를 또 보냈다"
    assert second["max_tokens"] == am.NIM_MAX_TOKENS, "한도는 물러서지 않는다"
    # ★ 장부는 두 줄이다 ★ 실제로 두 번 불렀으니 거부당한 첫 호출도 적힌다 —
    # 물러섬이 장부에서 지워지면 "요청이 거부된 적 있다"가 서버 안에도 안 남는다.
    assert [(l, ok) for l, ok, _ in ledger] == [("text", False), ("text", True)]
    assert str(code) in (ledger[0][2] or ""), "장부에는 예외 전문이 남는다"


def test_the_rejection_is_judged_once_not_five_times_a_slot(monkeypatch, ledger):
    """슬롯마다 5번 부른다. 낱말마다 다시 시험하면 거부된 뒤에도 매번 두 번씩
    나간다 — TED 설명 식별자(#30)와 같은 판단으로 한 번만 판정한다."""
    _nim_env(monkeypatch)
    ok = _resp({"content": "{}"})
    with patch("requests.post", side_effect=[_HTTPish(400), ok, ok, ok]) as post:
        for _ in range(3):
            am.nim_raw_detailed("원문", am._nim_config())
    sent = _payloads(post)
    assert len(sent) == 4, "첫 호출만 두 번(거부+재시도), 그 뒤 두 번은 한 번씩"
    assert ["chat_template_kwargs" in p for p in sent] == [True, False, False, False]


def test_a_rejection_that_persists_says_so_in_the_reason(monkeypatch, ledger):
    """물러섰는데도 실패하면, 사유가 '요청해봤고 거부됐다'를 같이 말한다 —
    다음 점검이 로그만 보고 이 분기를 탔는지 알 수 있어야 한다."""
    _nim_env(monkeypatch)
    with patch("requests.post", side_effect=[_HTTPish(400), _HTTPish(404)]):
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content is None
    assert "404" in reason, "두 번째 실패의 사유가 본문이다"
    assert reason.count("추론 노력 지정 거부됨") == 1, "같은 말이 두 번 실렸다(tally 가 쪼개진다)"


def test_after_a_rejection_later_failures_say_so_in_the_log_not_only_the_ledger(
        monkeypatch, ledger):
    """★09-15 의 교훈★ 거부된 뒤 두 번째 호출부터는 그 필드를 아예 안 보낸다.
    사유에 안 적으면 '거부당한 상태로 돌고 있다'가 장부(=`/api/status`, 점검이 닿지
    못하는 곳)에만 남고, 다음 점검이 토큰 숫자를 'low 로 돌린 결과'로 잘못 읽는다."""
    _nim_env(monkeypatch)
    empty = _resp({"content": None, "reasoning_content": "x"}, "length",
                  {"completion_tokens": 1500})
    with patch("requests.post", side_effect=[_HTTPish(400), empty, empty]) as post:
        _, first = am.nim_raw_detailed("원문", am._nim_config())
        _, later = am.nim_raw_detailed("원문", am._nim_config())
    assert "chat_template_kwargs" not in _payloads(post)[-1], "거부 뒤엔 안 보낸다"
    for reason in (first, later):
        assert "추론 노력 지정 거부됨" in reason
        assert f"출력토큰 1500/{am.NIM_MAX_TOKENS}" in reason
    assert first == later, "같은 원인은 같은 문자열이어야 tally 가 한 줄로 묶는다"
    assert later.count("추론 노력 지정 거부됨") == 1, "사유에 같은 말이 두 번 붙었다"


def test_a_success_after_the_rejection_is_still_a_clean_success(monkeypatch, ledger):
    """거부 기억이 성공 경로를 오염시키지 않는다 — 본문이 왔으면 사유는 없다."""
    _nim_env(monkeypatch)
    ok = _resp({"content": '{"disease": "x"}'})
    with patch("requests.post", side_effect=[_HTTPish(400), ok, ok]):
        am.nim_raw_detailed("원문", am._nim_config())
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content == '{"disease": "x"}' and reason is None


@pytest.mark.parametrize("code", [401, 404, 410, 429, 500])
def test_it_does_not_back_off_for_failures_a_back_off_cannot_fix(monkeypatch, ledger, code):
    """키(401)·모델명(404)·철수(410)·한도(429)·서버(500) 는 필드를 빼도 그대로다.
    여기서 물러서면 매 호출이 두 번씩 나가면서 아무것도 안 고친다."""
    _nim_env(monkeypatch)
    with patch("requests.post", side_effect=_HTTPish(code)) as post:
        content, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert content is None and str(code) in reason
    assert len(_payloads(post)) == 1, "물러서지 않아야 한다"
    assert "추론 노력 지정 거부됨" not in reason


def test_a_timeout_does_not_trigger_the_back_off(monkeypatch, ledger):
    _nim_env(monkeypatch)
    with patch("requests.post", side_effect=TimeoutError("read timed out")) as post:
        content, _ = am.nim_raw_detailed("원문", am._nim_config())
    assert content is None and len(_payloads(post)) == 1


# ── 6·7. 사유에 토큰 숫자가 실린다 ────────────────────────────────────

def test_the_reason_now_carries_the_token_numbers(monkeypatch, ledger):
    """★사흘을 못 가른 이유★ 사유가 글자 하나 안 변해서 '한도가 모자라다'와
    '다른 원인이다'를 가를 수가 없었다. 숫자가 그걸 가른다."""
    _nim_env(monkeypatch)
    usage = {"completion_tokens": 1500,
             "completion_tokens_details": {"reasoning_tokens": 1480}}
    msg = {"content": None, "reasoning_content": "추론 본문"}
    with patch("requests.post", return_value=_resp(msg, "length", usage)):
        _, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert f"출력토큰 1500/{am.NIM_MAX_TOKENS}" in reason
    assert "추론 1480" in reason
    assert "finish_reason=length" in reason           # 옛 신호도 그대로 남는다
    assert "추론 본문" not in reason                   # 값은 여전히 안 싣는다


def test_the_reason_still_works_when_the_server_sends_no_usage(monkeypatch, ledger):
    """usage 는 서버가 채우는 칸이다. 없으면 숫자 없이, 모양만으로 말한다."""
    _nim_env(monkeypatch)
    with patch("requests.post", return_value=_resp({"content": None}, "length")):
        _, reason = am.nim_raw_detailed("원문", am._nim_config())
    assert "출력토큰" not in reason and "빈응답(content=null" in reason


@pytest.mark.parametrize("usage", [
    {"completion_tokens": "https://evil/?key=SECRET"},
    {"completion_tokens": True},
    {"completion_tokens": None},
    {"completion_tokens": 300, "completion_tokens_details": "SECRET"},
    {"completion_tokens": 300, "completion_tokens_details": {"reasoning_tokens": "SECRET"}},
    "SECRET",
])
def test_only_integers_ride_in_the_token_note(usage):
    """★유출 방지(#28 유지)★ usage 는 서버가 정하는 칸이라 무엇이든 올 수 있다."""
    note = am._token_note(usage)
    assert "SECRET" not in note and "://" not in note
    assert note in ("", "출력토큰 300/1500 · ") or note.startswith("출력토큰 300/")


def test_empty_content_reason_keeps_working_with_two_arguments():
    """옛 호출부·시험이 인자 둘로 부른다 — 세 번째는 선택이어야 한다."""
    assert "빈응답" in am._empty_content_reason({}, None)
    assert "빈응답" in am._empty_content_reason(None, None)


# ── 배선: 고친 값이 실제로 요청에 실리는 경로인지 AST 로 고정 ─────────

def test_the_cap_and_the_effort_are_wired_into_the_request_body():
    """★'만들어만 두고 아무도 안 부른다' 를 막는다★ 상수를 올려놓고 호출부가
    옛 리터럴을 그대로 쓰면 아무것도 안 바뀐다. 요청 본문을 만드는 함수가
    상수를 참조하는지 AST 로 본다 — 주석이 아니라 코드를 본다."""
    src = Path(am.__file__).read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_nim_attempt")
    literals = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)]
    assert 300 not in literals, "옛 한도 리터럴이 요청 본문 조립부에 남아 있다"
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert {"NIM_MAX_TOKENS", "NIM_REASONING_EFFORT"} <= names
    sent_keys = {n.value for n in ast.walk(fn)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert {"max_tokens", "chat_template_kwargs", "reasoning_effort"} <= sent_keys


def test_the_timeout_grew_with_the_cap():
    """한도를 5배로 올리면 생성이 길어진다. 30초를 그대로 두면 ReadTimeout 으로
    슬롯을 잃는다 — 사유는 보이지만 결과는 빈손으로 같다."""
    assert am.NIM_TIMEOUT_SEC >= 60

"""추출 경로 출력 한도 — 추론형 모델이 한도를 다 먹어 본문이 비는 일 (소킹 11-02~11-13).

관측(운영 21시 슬롯):
- 11-02~ `meta_model_api: 빈응답(finish_reason=length, 출력토큰 1500/1500(추론 1498))×3~5`
- 11-13 `nvidia_nim_hosted: 빈응답(finish_reason=length, 출력토큰 1500/1500(추론 1497))×3`

추론이 1500 을 거의 다 쓰고 본문 차례에 끊긴다. 한도를 올리고, 길어진 생성에 맞춰
시간 초과도 늘린다. 이 시험은 '되돌아가지 않게' 고정한다 — 값을 다시 낮추려면
운영 로그의 `출력토큰 N/한도` 가 여유를 보여 준 뒤에 이 시험과 함께 바꾼다.
"""
from unittest.mock import patch

from algorithms import aegiron_model as am
from algorithms import meta_api


def test_extract_limits_leave_room_beyond_observed_reasoning():
    # 관측된 추론 토큰(1497~1498)에 본문 몫을 더해도 남아야 한다.
    observed_reasoning = 1498
    for limit in (am.NIM_MAX_TOKENS, am.META_MAX_TOKENS):
        assert limit >= observed_reasoning * 2, limit


def test_timeouts_grow_with_limits():
    # 1500 에 60초였다. 한도를 올렸으면 시간도 줘야 ReadTimeout 으로 슬롯을 잃지 않는다.
    assert am.NIM_TIMEOUT_SEC >= 120
    assert am.META_TIMEOUT_SEC >= 120


def test_meta_request_actually_sends_new_limit(monkeypatch):
    for k in (meta_api.KEY_ENV, meta_api.BASE_URL_ENV, am.REQUIRE_LOCAL_ENV):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(meta_api.KEY_ENV, "meta-key")
    sent = {}

    class _R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": None},
                                 "finish_reason": "length"}], "usage": {}}

    def _post(url, headers=None, json=None, timeout=None):
        sent.setdefault("calls", []).append((json, timeout))
        return _R()

    with patch("requests.post", side_effect=_post):
        am.extract_signal_detailed("DRC 에볼라", source="who")
    meta_calls = [(j, t) for j, t in sent["calls"] if j and j.get("max_tokens")]
    assert meta_calls, "Meta 호출이 나가야 한다"
    payload, timeout = meta_calls[0]
    assert payload["max_tokens"] == am.META_MAX_TOKENS
    assert timeout == am.META_TIMEOUT_SEC

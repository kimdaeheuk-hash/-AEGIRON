"""종합분석이 죽어도 로그엔 아무것도 없었다 (2026-09-15).

## 무엇이 있었나

`collect_ai_sources` 는 신호 **원문**(Perplexity/Tavily)만 한 줄씩 찍었다.
그 뒤에 도는 Claude 종합분석은 성공하든 실패하든 한 줄도 안 남겼다 —
`run_global_watch` 가 `synthesis_error` 를 반환값에 담는데 **아무도 안 읽었다.**

그래서 09-15 아침 점검이 이렇게 막혔다. 추출층이 14일째 `BadRequestError 400`
이었고, 같은 모델 ID 를 쓰는 층이 셋 더 있었는데(`event_dedup`·`verification`·
`global_watch`) **그 셋이 지금 도는지 안 도는지를 판정할 방법이 로그에 없었다.**
사유는 계산돼 있는데 볼 수 있는 곳에 없는, 이 리포가 반복해서 고쳐온 바로 그 모양이다.

    소스 건강 = 값이 왔는가        ← 종합분석은 여기 안 걸린다
    품질 불변식 = 값이 온전한가     ← 여기에도 없다
    로그       = 아무것도 안 찍힘   ← 그래서 완전한 사각지대였다

## 이 파일이 지키는 것

**성공도 실패도 한 줄은 남는다.** 그래야 다음 점검이 "이 층은 지금 돈다/안 돈다"를
숫자로 적을 수 있다.
"""
from __future__ import annotations

from unittest.mock import patch

import collector


def _watch(**over):
    value = {"signals": [{"label": "WHO EMRO", "text": "원문", "error": None}],
             "synthesis": None, "synthesis_error": None}
    value.update(over)
    return value


def _run(watch):
    """collect_ai_sources 를 돌리고 (로그 줄, 에러 줄) 을 돌려준다."""
    logs, errors = [], []
    with patch.object(collector, "run_global_watch", create=True), \
         patch("algorithms.global_watch.run_global_watch", return_value=watch), \
         patch.object(collector, "get_latest_polymarket_signals", return_value=None), \
         patch.object(collector, "append_signal"), \
         patch.object(collector, "log", side_effect=lambda m: logs.append(m)), \
         patch.object(collector, "log_error",
                      side_effect=lambda c, e: errors.append(f"{c}: {e}")), \
         patch("algorithms.aegiron_model.extraction_available", return_value=False):
        collector.collect_ai_sources()
    return logs, errors


def test_synthesis_failure_reaches_the_log():
    """★핵심★ 예전엔 이 실패가 로그에 한 글자도 안 남았다."""
    _logs, errors = _run(_watch(synthesis_error="BadRequestError 400: model not found"))
    assert any("GlobalWatch종합" in e for e in errors)
    assert any("model not found" in e for e in errors)


def test_synthesis_success_also_leaves_a_line():
    """실패만 찍으면 '조용함'이 두 가지를 뜻하게 된다 — 성공했나, 안 돌았나."""
    logs, errors = _run(_watch(synthesis="종합 분석 본문입니다"))
    assert not errors
    assert any("종합분석" in line for line in logs)


def test_a_missing_key_is_reported_not_silent():
    """키가 없어 건너뛴 것도 사유가 있다 — run_global_watch 가 이미 담아준다."""
    _logs, errors = _run(_watch(synthesis_error="ANTHROPIC_API_KEY 없음"))
    assert any("ANTHROPIC_API_KEY 없음" in e for e in errors)


def test_signal_lines_are_still_printed():
    """원문 줄을 대체한 게 아니라 옆에 붙인 것이다."""
    logs, _errors = _run(_watch(synthesis="x"))
    assert any("WHO EMRO" in line for line in logs)

"""모델 ID 표기 — 14일을 끌게 한 한 글자 (2026-09-15).

## 무엇이 있었나

추출층의 외부 LLM 폴백이 2026-09-02 부터 09-15 까지 **14일 내리** 같은 줄을 찍었다:

    external_llm_fallback: BadRequestError 400×5

400 은 계정·키 문제가 아니다 — 그건 401 이다. 그리고 계정이 멀쩡하다는 증거가
같은 로그 안에 있었다: **일일 브리핑이 같은 ANTHROPIC_API_KEY 로 매일 세 언어를
생성하고 있었다**(실패하면 main._log_error 가 stdout 에 찍는데 나흘째 0건).

그럼 두 호출의 차이는 모델 ID 하나였다:

    daily_brief.py   claude-sonnet-4-5            → 매일 성공
    nlp_extract.py   claude-haiku-4-5-20251001    → 매번 400

날짜가 박힌 스냅샷 ID 는 내려가면 그대로 400 이 된다. 요청 형식은 멀쩡한데
가리키는 대상이 없기 때문이고, 그게 이 증상의 모양과 정확히 맞는다.

## 이 파일이 지키는 것

**모델 ID 를 한 곳에서만 정하지 않는 한, 같은 실수가 조용히 다시 들어온다.**
09-15 시점에 같은 날짜 접미사가 네 파일에 흩어져 있었고, 그중 **셋은 실패해도
로그에 아무것도 안 남는 층**이었다 — 추출층만 보였을 뿐이다.

⚠️ 날짜 스냅샷을 **의도적으로** 고정할 일이 생기면 이 테스트를 고치고 왜인지
남겨라. 막으려는 것은 스냅샷 자체가 아니라 **아무도 모르게 박히는 것**이다.
"""
from __future__ import annotations

import re
from pathlib import Path

ALGORITHMS = Path(__file__).resolve().parent.parent / "algorithms"

# "claude-..." 문자열에서 끝에 붙은 -YYYYMMDD 를 찾는다.
_DATED = re.compile(r"""["'](claude-[a-z0-9.\-]*-\d{8})["']""")
_ANY_CLAUDE = re.compile(r"""["'](claude-[a-z0-9.\-]+)["']""")


def _sources():
    for path in sorted(ALGORITHMS.glob("*.py")):
        yield path, path.read_text(encoding="utf-8")


def test_no_claude_model_id_carries_a_date_suffix():
    """★핵심★ 09-02~09-15 를 통째로 날린 것이 바로 이 모양이다."""
    offenders = [f"{path.name}: {m}"
                 for path, text in _sources()
                 for m in _DATED.findall(text)]
    assert not offenders, (
        "날짜 접미사가 붙은 모델 ID 는 스냅샷이 내려가면 400 이 되고, "
        "그 400 은 본문을 읽기 전엔 원인을 알 수 없다. 의도한 것이라면 "
        f"이 테스트를 고치고 이유를 남겨라: {offenders}"
    )


def test_extraction_model_matches_the_ones_that_actually_work():
    """추출층만 따로 놀지 않는지 — 같은 키로 도는 다른 층과 표기가 같아야 한다."""
    from algorithms import nlp_extract as nx

    assert nx.MODEL == "claude-haiku-4-5"
    assert not re.search(r"-\d{8}$", nx.MODEL)


def test_every_claude_id_in_the_tree_is_still_parseable():
    """표기 규칙을 지키는지 훑는다 — 접미사 없는 `claude-<계열>-<버전>` 형태."""
    bad = []
    for path, text in _sources():
        for model_id in _ANY_CLAUDE.findall(text):
            if not re.fullmatch(r"claude-[a-z]+-[0-9]+(-[0-9]+)?", model_id):
                bad.append(f"{path.name}: {model_id}")
    assert not bad, f"낯선 모델 ID 표기: {bad}"

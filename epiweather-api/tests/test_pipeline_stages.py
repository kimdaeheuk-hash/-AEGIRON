"""단계 이름이 **지어낸 것이 아닌지** 지킨다.

## 왜 이 파일이 있는가

2026-08-31 까지 코드에는 Stage 0·1·2·5·6·8 만 번호가 붙어 있었다.
3·4·7 은 기능은 도는데 이름이 없었고, 그래서 대외 문서를 쓸 때마다 사람이
즉석에서 지어냈다 — 실제로 포트폴리오 PDF 에 코드에 없는 단계 이름이 들어갔다.

문서는 나중에 고칠 수 있지만, **그 문서가 회사에 나간 뒤에는 못 고친다.**
그래서 이름을 코드에 박고, 그 이름이 실재하는 모듈을 가리키는지 여기서 막는다.
"""
from __future__ import annotations

import os

import pytest

from algorithms.pipeline_stages import (
    NEWLY_NAMED_STAGES, PIPELINE_STAGES, pipeline_summary, special_stages,
    stage, stage_names,
)

ALGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "algorithms")


def test_stages_are_zero_through_eight_without_gaps():
    """0~8 이 빠짐없이 있어야 한다 — 빈 번호가 생기면 또 누가 지어낸다."""
    numbers = [s["stage"] for s in PIPELINE_STAGES]

    assert numbers == list(range(9))


@pytest.mark.parametrize("entry", PIPELINE_STAGES, ids=lambda e: f"stage{e['stage']}")
def test_every_stage_points_at_real_modules(entry):
    """★핵심★ 근거로 적은 파일이 실제로 있어야 한다.

    이게 없으면 "3단계는 신호 추출입니다" 라고 말해놓고 그런 코드가 없는
    상태가 된다. 그건 지어낸 것이다.
    """
    assert entry["modules"], f"{entry['stage']}단계에 근거 모듈이 없다"
    for module in entry["modules"]:
        path = os.path.join(ALGO_DIR, module)
        assert os.path.exists(path), f"{entry['stage']}단계가 없는 파일을 가리킨다: {module}"


@pytest.mark.parametrize("entry", PIPELINE_STAGES, ids=lambda e: f"stage{e['stage']}")
def test_every_stage_has_a_name_in_both_languages(entry):
    """대외 자료가 한국어·영어를 함께 쓴다. 한쪽이 비면 거기서 또 지어낸다."""
    assert entry["name_ko"].strip()
    assert entry["name_en"].strip()
    assert len(entry["summary_ko"]) >= 30, "설명이 너무 짧으면 문서가 살을 붙이게 된다"


def test_special_stages_are_zero_and_eight():
    """0·8 은 성격이 다르다 — 감시가 아니라 연구다."""
    assert [s["stage"] for s in special_stages()] == [0, 8]
    assert stage(0)["program_key"] == "stage0"
    assert stage(8)["program_key"] == "stage8"
    # 나머지는 코드명이 없다. 없는 것을 있는 척하지 않는다.
    for entry in PIPELINE_STAGES:
        if entry["stage"] not in (0, 8):
            assert entry["program_key"] is None


def test_newly_named_stages_are_disclosed_not_hidden():
    """★핵심★ 3·4·7 을 나중에 붙였다는 사실을 숨기지 않는다.

    기능은 원래 있었지만 이름은 2026-08-31 에 붙였다. 그걸 안 밝히면
    "처음부터 9단계로 설계했다"는 인상을 주게 된다 — 사실이 아니다.
    """
    summary = pipeline_summary()

    assert summary["newly_named"] == [3, 4, 7]
    assert summary["newly_named_on"] == "2026-08-31"
    assert "이미 돌고 있던" in summary["note"]


def test_classification_note_never_claims_government_status():
    """0·8 의 보안등급은 사내 정의다 — 정부 기밀로 읽히면 안 된다."""
    note = pipeline_summary()["classification_note"]

    assert "정부기관" in note and "아니다" in note


def test_unknown_stage_number_is_none_not_a_guess():
    """모르는 번호를 그럴듯하게 채우지 않는다."""
    assert stage(9) is None
    assert stage(-1) is None


def test_stage_names_are_unique():
    """이름이 겹치면 문서에서 어느 단계인지 알 수 없다."""
    names = list(stage_names().values())

    assert len(names) == len(set(names))
    assert len(NEWLY_NAMED_STAGES) == 3

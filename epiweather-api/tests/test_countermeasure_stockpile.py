"""대응제 비축 격차가 **모르는 것을 격차로 세지 않는지** 지킨다 (2026-09-01).

## 왜 만들었나

캡틴: *"우리가 어떻게 대비를 해야 하는지 찾아봐! 아이기론은 국가 안보 분야도
다뤄야 해!"*

아이기론엔 이미 대비 층이 있다 — 8단계 VALHALLA. 그런데 그건 **계산기**라
비축 목록을 입력받아야 돌아가고, 아무도 안 넣어서 시연용 예시만 돌고 있었다.

조사 결과 **국가 비축 재고는 공개되지 않는다.** 안보 사안이니 당연하고,
알아내려 해서도 안 된다. 대신 공개되는 것이 있다 — **WHO ICG 국제 비상 비축에
어떤 질병이 들어 있는가.**

실측(2026-09-01): 지금 신호가 잡히는 12종 중 **9종이 비축 체계 밖**이었다.

## ★ 이 파일이 막는 것 ★

이름을 못 알아본 병을 "비축 없음" 으로 접는 것. 그러면 오탈자 하나가 격차로
집계돼 **없는 위기를 만들어낸다.** 실제로 신호에는 "덴뇌"·"볼로아" 처럼 LLM
추출이 흔들린 이름이 섞여 있다.
"""
from __future__ import annotations

import pytest

from algorithms.countermeasure_stockpile import (
    stockpile_status,
)


@pytest.mark.parametrize("name", ["에볼라", "Ebola", "ebola virus disease",
                                  "콜레라", "cholera", "mpox", "엠폭스",
                                  "yellow fever", "황열", "meningitis"])
def test_icg_stockpiled_diseases_are_recognised(name):
    """국제 비상 비축이 있는 다섯 종은 이름이 흔들려도 잡아야 한다."""
    status = stockpile_status(name)

    assert status["known"] is True
    assert status["has_global_stockpile"] is True
    assert status["mechanism"] == "WHO ICG"


@pytest.mark.parametrize("name,expect", [
    ("H5N1", "인플루엔자(조류·계절)"), ("조류독감", "인플루엔자(조류·계절)"),
    ("dengue", "뎅기열"), ("덴그열병", "뎅기열"), ("덴게 열", "뎅기열"),
    ("MERS", "MERS"), ("nipah", "니파"), ("마버그", "마버그"),
    ("한타바이러스 심폐증후군", "한타바이러스"), ("anthrax", "탄저"),
])
def test_known_gaps_are_named(name, expect):
    """비축 밖 위협도 이름으로 정리한다 — 표기가 흔들려도 하나로 모은다."""
    status = stockpile_status(name)

    assert status["known"] is True
    assert status["has_global_stockpile"] is False
    assert status["name_ko"] == expect


def test_unknown_name_is_not_counted_as_a_gap():
    """★★핵심★★ 모르는 이름을 '비축 없음' 으로 접지 않는다.

    실제 신호에 "덴뇌"·"볼로아" 같은 LLM 추출 흔들림이 섞여 있다. 그걸 격차로
    세면 오탈자 하나가 없는 위기를 만들어낸다.
    """
    for odd in ("볼로아", "오즈 바이러스", "", None, "zzz"):
        status = stockpile_status(odd)
        assert status["known"] is False
        assert "has_global_stockpile" not in status, f"{odd} 를 판정해버렸다"



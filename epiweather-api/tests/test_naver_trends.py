"""네이버 검색어 트렌드 — 코로나 축 추가와 배치 분리 (2026-09-19).

## 왜 이 파일이 있나

캡틴: "우리나라 코로나가 지금 유행하는데 아이기론이 확인했어?"

확인할 수 없었다. 국내 코로나 축이 **아예 없었다**:

    KDCA EIDAPIService  법정감염병 전수감시 — 표본감시 질병(코로나·독감)은 안 줌
    네이버 검색어        독감·에볼라만 추적

그래서 "급증 없음"은 확인한 결과가 아니라 **안 보는 자리**였다.

## 이 파일이 지키는 것 — 재척도 사고

네이버는 **한 요청 안의 모든 그룹 중 최댓값을 100** 으로 정규화한다. 코로나를
기존 요청에 한 줄 더 넣는 '간단한' 방법을 쓰면, 코로나 검색량이 더 많은 순간
독감·에볼라가 통째로 재척도된다. 요청은 200 이고 숫자도 들어오고 로그도 조용하다.

그 값은 anomaly_engine 의 z-score 입력이다. 척도가 갈아엎히면 과거 평균·표준편차가
현재 값과 다른 단위가 되어 **없는 급증이 잡히거나 진짜 급증을 놓친다.** 값이 비는
고장보다 나쁘다 — 그래서 배치를 나눈 것이고, 아래 테스트가 그 구성을 고정한다.
"""
from __future__ import annotations

from algorithms import naver_trends as nt


# ── 재척도 사고를 코드 구조로 막는다 ────────────────────────────
def test_covid_is_not_in_the_same_batch_as_the_existing_axes():
    """★핵심★ 같은 요청에 넣으면 독감·에볼라가 재척도된다. 배치가 갈라져 있어야
    한다 — 이 테스트가 깨지면 3개월치 기준선이 조용히 의미를 잃는 변경이다."""
    batch_of = {}
    for batch_name, groups in nt.NAVER_BATCHES:
        for group in groups:
            batch_of[group["groupName"]] = batch_name

    assert batch_of["코로나"] != batch_of["독감"]
    assert batch_of["코로나"] != batch_of["에볼라"]


def test_existing_axes_stay_together():
    """반대 방향도 막는다. 독감·에볼라를 서로 다른 배치로 쪼개도 척도가 바뀌어
    과거와 안 이어진다 — 2026-06 부터 같은 요청으로 모아온 시계열이다."""
    batch_of = {g["groupName"]: b for b, gs in nt.NAVER_BATCHES for g in gs}
    assert batch_of["독감"] == batch_of["에볼라"]


def test_every_group_has_a_result_field():
    """배치에 그룹을 추가하고 필드를 안 만들면 값이 수집돼도 어디에도 안 담긴다."""
    for _batch, groups in nt.NAVER_BATCHES:
        for group in groups:
            assert group["groupName"] in nt.GROUP_FIELDS


# ── 이름으로 찾는다(위치를 믿지 않는다) ─────────────────────────
def test_ratios_are_matched_by_name_not_position():
    """★핵심★ 예전엔 results[0]·results[1] 로 위치를 믿었다. 순서가 바뀌면
    독감 값이 에볼라 자리에 들어가도 아무도 모른다 — 값이 비는 게 아니라
    틀린 값이 채워지는 쪽이라 더 나쁘다."""
    payload = {"results": [
        {"title": "에볼라", "data": [{"period": "2026-09-14", "ratio": 4.6}]},
        {"title": "독감", "data": [{"period": "2026-09-14", "ratio": 92.5}]},
    ]}
    out = nt.latest_ratios(payload)
    assert out["독감"] == 92.5
    assert out["에볼라"] == 4.6


def test_latest_point_is_the_last_one():
    payload = {"results": [{"title": "코로나", "data": [
        {"period": "2026-09-07", "ratio": 11.0},
        {"period": "2026-09-14", "ratio": 38.2},
    ]}]}
    assert nt.latest_ratios(payload)["코로나"] == 38.2


# ── 못 받은 것을 0 으로 채우지 않는다 ───────────────────────────
def test_missing_group_is_absent_not_zero():
    """★핵심★ 그룹이 응답에 없는 것과 검색량이 0 인 것은 다르다. 앞은 고장이고
    뒤는 관측이다. 섞으면 '네이버가 죽었다'가 '아무도 안 찾는다'로 둔갑한다."""
    out = nt.latest_ratios({"results": [
        {"title": "독감", "data": [{"ratio": 92.5}]},
    ]})
    assert "코로나" not in out


def test_empty_data_array_is_none_not_zero():
    """데이터 배열이 비면 '최근 값'이 없는 것이다 — 0 을 지어내지 않는다."""
    out = nt.latest_ratios({"results": [{"title": "코로나", "data": []}]})
    assert out["코로나"] is None


def test_broken_payload_does_not_raise():
    assert nt.latest_ratios(None) == {}
    assert nt.latest_ratios({}) == {}
    assert nt.latest_ratios({"results": [{"data": [{"ratio": 1}]}]}) == {}   # title 없음


# ── 요청 본문 ───────────────────────────────────────────────────
def test_request_body_uses_the_same_window_for_every_batch():
    """척도는 이미 배치마다 다르다. 시간 창까지 달라지면 비교가 더 어려워진다."""
    import datetime as dt
    bodies = [nt.request_body(groups, today=dt.date(2026, 9, 19))
              for _name, groups in nt.NAVER_BATCHES]
    assert len({(b["startDate"], b["endDate"], b["timeUnit"]) for b in bodies}) == 1
    assert bodies[0]["startDate"] == "2026-06-21"
    assert bodies[0]["endDate"] == "2026-09-19"


def test_covid_group_carries_a_behavioural_proxy():
    """자가검사키트는 증상 의심 시점에 검색되므로 신고 통계보다 앞선다 —
    이 축을 넣은 이유 자체가 '신고보다 먼저 보는 것'이다."""
    covid = [g for _b, gs in nt.NAVER_BATCHES for g in gs if g["groupName"] == "코로나"][0]
    assert "자가검사키트" in covid["keywords"]
    assert "코로나19" in covid["keywords"]


# ── 로그 한 줄 ──────────────────────────────────────────────────
def test_summary_shows_every_axis_it_got():
    line = nt.summary({"독감": 92.5, "에볼라": 4.6, "코로나": 38.2})
    assert "독감비율=92.5" in line
    assert "코로나비율=38.2" in line


def test_summary_does_not_hide_a_failed_batch():
    """★핵심★ 한 배치가 죽어도 다른 값은 찍힌다. 사유를 안 붙이면 코로나비율이
    '원래 없는 것'처럼 읽힌다 — 고장이 정상으로 둔갑하는 그 모양이다."""
    line = nt.summary({"독감": 92.5, "에볼라": 4.6}, {"covid": "HTTPError 429"})
    assert "독감비율=92.5" in line
    assert "covid 실패(HTTPError 429)" in line


def test_summary_survives_total_failure():
    line = nt.summary({}, {"baseline": "Timeout", "covid": "Timeout"})
    assert "값 없음" in line
    assert line.count("실패") == 2


# ── 지수·브리핑 배선 ────────────────────────────────────────────
def test_covid_ratio_is_registered_as_a_behavioural_metric():
    """수집만 하고 등록을 안 하면 값이 로그에만 남고 판정엔 안 쓰인다 —
    '만들어만 두고 아무도 안 부르는' 층이 이 리포에서 반복된 실패 유형이다."""
    from algorithms.signal_metrics import LAYERS
    ids = [m[0] for m in LAYERS["behavioral"]["metrics"]]
    assert "naver_covid_ratio" in ids


def test_covid_metric_reads_the_field_the_collector_writes():
    """등록은 됐는데 다른 키를 읽으면 영영 None 이다. 끝에서 끝까지 확인한다."""
    from algorithms.signal_metrics import LAYERS
    extractor = next(m[2] for m in LAYERS["behavioral"]["metrics"]
                     if m[0] == "naver_covid_ratio")
    assert extractor({nt.GROUP_FIELDS["코로나"]: 38.2}) == 38.2


def test_covid_ratio_has_a_display_label():
    from algorithms.brief_sections import _METRIC_LABEL
    assert "naver_covid_ratio" in _METRIC_LABEL

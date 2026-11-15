"""극지 관찰층이 **실제로 돌고 있는지** 지킨다 (2026-09-01).

## 사고

캡틴이 "극지 감시망 돌고 있지?" 라고 물어 확인해 보니 **돌고 있지 않았다.**

    수집기(collector.py)   극지 호출 없음
    소스 헬스              등록 없음

`/api/polar-watch` 를 **부를 때만** 그 자리에서 계산됐다. 즉 기능은 있는데
감시는 하지 않는 상태였다. 결과가 어디에도 쌓이지 않으니 어제 대비 오늘을
비교할 수 없었고 — 동토 해빙은 추세가 핵심인데 매번 그 순간만 봤다 —
Open-Meteo 나 러시아어 뉴스가 막혀도 21개 소스 어디에도 안 잡혔다.

## ★ 왜 하루 한 번이 아니라 매시간인가 ★

처음엔 "동토는 시간 단위로 안 변하니 하루 한 번" 이라고 판단했다가 바꿨다.
소스 헬스는 **매 주기 기록**을 전제로 돈다(record_cycle). 하루 한 번만 돌면
나머지 23주기가 값없음으로 쌓여 **거짓 경보**가 된다.

호출량은 8개 관측지 × (기후+뉴스) = 시간당 16건 live에 기준선·추세 일 16건
(디스크 캐시)이고 실측 10.6초다. 이미 매시간
179개 현지어 피드를 받고 있으므로 부담이 아니다. 일관성이 미세 최적화보다
중요하다.
"""
from __future__ import annotations

import inspect

import collector


def test_polar_watch_is_a_tracked_source():
    """★핵심★ 수집 대상으로 등록돼 있어야 한다.

    등록이 없으면 죽어도 아무도 모른다 — 이 저장소가 Mobility 245시간·
    GroqWatch 열흘로 배운 것이다.
    """
    assert collector.FREE_SOURCE_HEALTH_KEYS["PolarWatch"] == "polar_watch"


def test_collector_actually_calls_the_polar_layer():
    """등록만 하고 안 부르면 매 주기 값없음으로 쌓여 거짓 경보가 된다."""
    source = inspect.getsource(collector.collect_free_sources)

    assert "polar_watch_all" in source, "수집기가 극지 층을 부르지 않는다"
    assert 'result["polar_watch"]' in source, "결과를 등록 키에 담지 않는다"


def test_polar_failure_is_recorded_not_swallowed():
    """실패를 조용히 넘기지 않는다 — 사유를 남긴다."""
    source = inspect.getsource(collector.collect_free_sources)
    after = source[source.index("polar_watch_all"):]

    assert 'log_error("PolarWatch"' in after, "실패 사유를 기록하지 않는다"
    assert "❌" in after, "실패가 ⏭(소프트 스킵)로 찍히면 점검에서 걸러진다"


def test_polar_stays_a_watch_layer_not_an_alarm():
    """★핵심★ 수집에 넣었다고 경보가 되면 안 된다.

    대부분의 동토 미생물은 사람을 감염시키지 못하고, 이 위험은 토지이용
    동인보다 과대평가되는 경향이 있다(모듈 docstring). 수집하는 이유는
    울리기 위해서가 아니라 **쌓기 위해서**다.
    """
    from algorithms import polar_signals

    doc = polar_signals.__doc__ or ""
    assert "watch_grade" in doc, "관찰 등급이라는 근거가 문서에서 사라졌다"

    # 경보 파이프라인과 섞이지 않아야 한다.
    # ★ 주석에 적힌 것과 실제로 쓰는 것을 구분한다 ★ 이 모듈 docstring 은
    # "classify_tier 와 절대 섞지 않는다" 고 적고 있어서, 단어 등장만 보면
    # 정반대로 읽힌다. import·호출이 있는지를 본다.
    src = inspect.getsource(polar_signals)
    code = chr(10).join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "import classify_tier" not in code
    assert "classify_tier(" not in code, "경보 파이프라인을 실제로 호출한다"

    # 관찰 등급 표시가 결과에 실제로 실려야 한다
    assert "watch_grade" in src


def test_every_region_is_still_watched():
    """관측지가 조용히 줄지 않는다 — 8곳은 설계다(2026-11-02 북극군도·아이슬란드 추가)."""
    from algorithms.polar_signals import POLAR_REGIONS

    keys = {r[0] for r in POLAR_REGIONS}
    assert keys == {
        "siberia_yamal", "alaska_north", "canada_arctic",
        "greenland", "svalbard", "antarctic_peninsula",
        "arctic_archipelago", "iceland",
    }


def test_new_territories_carry_their_jurisdiction_in_the_name():
    """영토 단위 관측 — 이름에 관할이 없으면 어느 영토 신호인지 모른다."""
    from algorithms.polar_signals import POLAR_REGIONS

    names = {r[0]: r[1] for r in POLAR_REGIONS}
    assert "캐나다" in names["arctic_archipelago"] and "레졸루트" in names["arctic_archipelago"]


def test_brief_region_names_cover_every_territory():
    """브리핑 지역명 표가 관측 집합을 다 덮는다 — 빠지면 한국어가 섞인다."""
    from algorithms.brief_sections import _REGION_NAME
    from algorithms.polar_signals import POLAR_REGIONS

    for (key, *_rest) in POLAR_REGIONS:
        entry = _REGION_NAME.get(key)
        assert entry and all(entry.get(lang) for lang in ("ko", "en", "fr")), key


# ─────────────────────────────────────────────────────────────────────────
# 2026-11-14 사고: 요약 로그 한 줄이 수집된 데이터를 버렸다
#
# 21시 UTC 부터 3주기 연속:
#     ❌ 극지 관찰 실패: TypeError: must be real number, not NoneType
#     ⚠️ 소스 이상: PolarWatch (중단, 연속 실패 3회)
#
# 터진 자리는 수집이 아니라 **요약 로그**였다:
#     ", ".join("%s(%.0f)" % (r["name"][:10], r["polar_watch_score"]) ...)
# `polar_watch_score` 는 해빙 자료도 뉴스 신호도 없을 때 None 이 되는
# **정상값**이다(polar_signals.py 151줄, '모른다'고 말하는 쪽). 바로 윗줄의
# 정렬은 `or 0` 으로 그걸 막아놨는데 포맷에서 자격이 떨어져 나가 있었다.
#
# 그리고 그 로그가 `result["polar_watch"] = ...` 와 **같은 try** 안에 있어서
# except 가 이미 받아온 결과를 None 으로 덮었다 — 수집은 성공했는데 장식용
# 한 줄 때문에 3시간치 추세를 버렸다. 추세를 쌓는 게 목적인 층에서 가장 비싼
# 실패 방식이다.
# ─────────────────────────────────────────────────────────────────────────


def test_top_label_survives_a_scoreless_region():
    """★핵심★ 점수 없는 관측지가 상위에 와도 요약이 터지지 않는다.

    2026-11-14 21시 UTC 의 실제 모양이다. `%.0f % None` 이 TypeError 를 냈다.
    """
    assert collector._polar_top_label(
        {"name": "아이슬란드", "polar_watch_score": 74.0}) == "아이슬란드(74)"

    # 점수 없음은 숨기지 않고 `—` 로 적는다 — 0 으로 적으면 '관찰값 0'으로 읽힌다.
    assert collector._polar_top_label(
        {"name": "스발바르(노르웨이)", "polar_watch_score": None}) == "스발바르(노르웨이)(—)"

    # 키가 아예 없어도(앞으로 모양이 바뀌어도) 터지지 않는다.
    assert collector._polar_top_label({}) == "?(—)"


def test_scoreless_region_is_not_reported_as_zero():
    """값 없음을 0 으로 적지 않는다 — 0-on-failure 금지(collector-source 규약 4)."""
    label = collector._polar_top_label({"name": "그린란드", "polar_watch_score": None})
    assert "0" not in label, "점수 없음이 0 으로 보고되면 '관찰값 0'으로 읽힌다"


def test_summary_log_cannot_discard_collected_data():
    """★핵심★ 요약 로그는 데이터를 담는 try 밖에 있어야 한다.

    AST 로 본다 — 문자열 검색은 주석이나 줄바꿈에 속는다. 지키는 성질:
    `result["polar_watch"] = None` 로 데이터를 버리는 except 를 가진 try 의
    **본문 안에** 요약 로그(`극지 관찰:`)가 있으면 안 된다.
    """
    import ast

    tree = ast.parse(inspect.getsource(collector).lstrip())

    def _nulls_polar_watch(handler: ast.ExceptHandler) -> bool:
        return any(
            isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Constant) and n.value.value is None
            and any("polar_watch" in ast.unparse(t) for t in n.targets)
            for n in ast.walk(handler)
        )

    def _has_summary_log(nodes) -> bool:
        return any(
            "극지 관찰:" in ast.unparse(n)
            for node in nodes for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        )

    guarded = [
        t for t in ast.walk(tree)
        if isinstance(t, ast.Try) and any(_nulls_polar_watch(h) for h in t.handlers)
    ]
    assert guarded, "극지 데이터를 None 으로 덮는 except 를 못 찾았다 — 구조가 바뀌었다"

    for t in guarded:
        assert not _has_summary_log(t.body), (
            "요약 로그가 데이터를 버리는 try 안에 있다 — 로그가 깨지면 "
            "수집된 극지 데이터가 또 폐기된다(2026-11-14 재발)"
        )


def test_summary_log_failure_is_not_counted_as_a_collection_failure():
    """요약 줄이 깨져도 ❌/log_error 로 올리지 않는다 — 수집 실패가 아니다."""
    source = inspect.getsource(collector.collect_free_sources)
    after = source[source.index("polar_watch_all"):]
    tail = after[:after.index("현지어 위키")]

    assert "데이터는 보존" in tail, "요약 로그 실패가 데이터를 보존한다는 근거가 없다"


def test_a_cycle_with_no_scores_at_all_is_marked_no_data():
    """★핵심★ 8곳 전부 점수가 없으면 ok 가 아니라 값없음이다.

    ok 로 세면 죽은 층이 살아있다고 보고되고(Mobility 190시간이 그랬다),
    실패로 세면 상시 degraded 로 매일 울려 사람이 경보를 무시한다.
    둘 다 거짓이라 no_data 로 적고 사유를 로그에 남긴다.
    """
    source = inspect.getsource(collector.collect_free_sources)
    after = source[source.index("polar_watch_all"):]
    tail = after[:after.index("현지어 위키")]

    assert 'mark_no_data(result, "polar_watch")' in tail, "전부 점수 없는 주기를 ok 로 센다"
    assert "scored == 0" in tail, "'한 곳도 점수 없음' 조건이 없다"
    assert "전부 점수 없음" in tail, "값없음 사유를 로그에 안 남긴다(mark_no_data 규약)"


def test_summary_log_reports_how_many_regions_are_scored():
    """점수있음 N/M 을 매 주기 남긴다 — 상류가 조용히 마르는 걸 보려면 필요하다.

    11-14 사고 때 로그가 터져서 **어느 지역이 점수를 잃었는지 안 보였다.**
    이 버그가 자기 진단을 가리고 있었다.
    """
    source = inspect.getsource(collector.collect_free_sources)
    after = source[source.index("polar_watch_all"):]

    assert "점수있음" in after[:after.index("현지어 위키")], "점수 있는 관측지 수를 안 남긴다"

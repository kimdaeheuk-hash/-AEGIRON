"""극지 관찰 — 요약 줄이 터져서 **수집한 자료를 버리던** 자리 (2026-11-16).

## 관측 (프로덕션 로그, Railway)

    2026-11-14 21:00·22:00·23:00 UTC   ❌ 극지 관찰 실패: TypeError: must be real number, not NoneType
    2026-11-15 00:03                   ✅ 소스 복구: PolarWatch
    2026-11-15 10:00 ~ 23:01           같은 에러로 14주기 연속 · 12:01 부터 `중단 PolarWatch`
                                       (📊 소스 건강: 정상 24/25)

## 무슨 일이었나

터진 자리는 수집이 아니라 **수집 결과를 찍는 요약 줄**이었다:

    top = sorted(regions, key=lambda r: -(r.get("polar_watch_score") or 0))[:3]   # None 을 막는다
    ", ".join("%s(%.0f)" % (r["name"][:10], r["polar_watch_score"]) for r in top)  # 안 막는다

`polar_watch_score` 가 None 인 것은 고장이 아니라 설계다 — `compute_region` 은 해빙
자료도 뉴스 신호도 없는 관측지에 대해 평균을 지어내지 않고 None 을 돌려준다.
바로 윗줄이 `or 0` 으로 막아둔 그 None 을 `%.0f` 가 안 막았다.

**피해가 로그 한 줄보다 크다**: `result["polar_watch"]` 는 이미 채워진 뒤였고,
`except` 가 그걸 None 으로 덮어써서 `record_cycle` 이 수집 실패로 셌다.
즉 **자료를 매 주기 받아서 버렸다.**

이 시험이 못박는 것:
 1. 점수가 None 이어도 요약 줄이 터지지 않는다(0 으로 둔갑시키지도 않는다).
 2. 요약 줄이 터져도 **수집한 자료는 보존되고 소스 헬스에 실패로 안 쌓인다.**
 3. 모르는 관측지 수가 줄에 숫자로 보인다 — 상위 3곳 밖으로 밀려 안 보이던 사실.
"""
import collector


# ── 1) 점수가 None 이어도 안 터진다 ──────────────────────────────────────

def _region(name, score):
    return {"name": name, "polar_watch_score": score}


def test_none_score_does_not_raise_and_is_not_printed_as_zero():
    pw = {"grade": "watch", "regions": [_region("야말", None), _region("아이슬란드", None)]}
    line = collector._polar_summary_line(pw)          # 예전엔 여기서 TypeError
    assert "야말(?)" in line
    # ★ 0 으로 찍으면 더 나쁜 거짓이다 ★ 모르는 것을 0점이라고 쓰는 셈이다.
    assert "(0)" not in line


def test_known_scores_outrank_unknown_ones():
    """0 점(측정값)과 None(모름)은 등급이 다르다 — `or 0` 하나로 섞으면 같은 자리에 놓인다."""
    pw = {"grade": "watch", "regions": [
        _region("모름", None), _region("영점", 0.0), _region("높음", 72.0)]}
    line = collector._polar_summary_line(pw)
    assert line.index("높음(72)") < line.index("영점(0)") < line.index("모름(?)")


def test_unknown_count_is_shown_even_when_it_falls_outside_the_top3():
    """상위 3곳은 점수 순이라 모르는 관측지는 거의 `?` 로 안 보인다 — 그래서 수를 센다."""
    regions = [_region(f"높음{i}", 90.0 - i) for i in range(3)] + \
              [_region(f"모름{i}", None) for i in range(5)]
    line = collector._polar_summary_line({"grade": "watch", "regions": regions})
    assert "8개 관측지" in line and "점수 모름 5곳" in line
    assert "?" not in line          # top3 안에는 모르는 곳이 없다


def test_no_unknown_suffix_when_every_region_has_a_score():
    line = collector._polar_summary_line(
        {"grade": "calm", "regions": [_region("가", 10.0), _region("나", 20.0)]})
    assert "점수 모름" not in line


def test_empty_and_malformed_inputs_do_not_raise():
    assert "0개 관측지" in collector._polar_summary_line({"grade": None, "regions": []})
    assert "0개 관측지" in collector._polar_summary_line(None)
    # 이름이 없어도 줄을 만든다(이름을 지어내지는 않는다)
    assert "?(" in collector._polar_summary_line(
        {"regions": [{"polar_watch_score": 5.0}]})


# ── 2) 요약 줄이 터져도 자료는 남는다 ───────────────────────────────────

def _run_polar_block(monkeypatch, *, watch_value, summary_raises):
    """collector 의 극지 블록만 떼어 같은 구조로 돌린다.

    블록 자체는 `collect_free_sources` 안에 있어 통째로 부르면 20개 소스를 다
    두드린다(테스트는 외부에 못 나간다). 그래서 이 시험은 블록이 의존하는 두
    부품(`polar_watch_all`·`_polar_summary_line`)을 바꿔 끼우고, 블록과 **똑같은
    제어 흐름**을 돌려 자료 보존과 log_error 호출 여부를 본다.
    아래 test_the_production_block_has_this_shape 가 실제 블록이 이 모양임을 고정한다.
    """
    logs, errors = [], []
    monkeypatch.setattr(collector, "log", lambda m: logs.append(m))
    monkeypatch.setattr(collector, "log_error", lambda c, e: errors.append((c, e)))
    if summary_raises:
        def boom(_pw):
            raise TypeError("must be real number, not NoneType")
        monkeypatch.setattr(collector, "_polar_summary_line", boom)

    result = {}
    try:
        result["polar_watch"] = watch_value()
    except Exception as e:
        result["polar_watch"] = None
        collector.log(f"  ❌ 극지 관찰 실패: {type(e).__name__}: {e}")
        collector.log_error("PolarWatch", e)
    else:
        try:
            collector.log(collector._polar_summary_line(result["polar_watch"]))
        except Exception as e:
            collector.log(f"  ⚠ 극지 관찰 요약 줄 생성 실패(자료는 보존): "
                          f"{type(e).__name__}: {e}")
    return result, logs, errors


_GOOD = {"grade": "watch", "regions": [{"name": "야말", "polar_watch_score": 72.0}]}


def test_summary_failure_keeps_the_collected_data(monkeypatch):
    """11-14~15 사고의 핵심 — 찍다 실패했다고 받아온 자료를 버리지 않는다."""
    result, logs, errors = _run_polar_block(
        monkeypatch, watch_value=lambda: _GOOD, summary_raises=True)
    assert result["polar_watch"] == _GOOD                  # 예전엔 None 이 됐다
    assert any("요약 줄 생성 실패(자료는 보존)" in m for m in logs)


def test_summary_failure_is_not_counted_as_a_collection_failure(monkeypatch):
    """소스 헬스는 수집의 성패를 말하는 자리다 — 서식 버그로 소스를 죽이지 않는다."""
    _, logs, errors = _run_polar_block(
        monkeypatch, watch_value=lambda: _GOOD, summary_raises=True)
    assert errors == []                                    # log_error("PolarWatch", …) 없음
    assert not any("❌ 극지 관찰 실패" in m for m in logs)


def test_a_real_collection_failure_still_fails_the_source(monkeypatch):
    """반대쪽 — 진짜 수집 실패는 예전처럼 None 이고 log_error 로 올라간다."""
    def boom():
        raise RuntimeError("Open-Meteo 503")
    result, logs, errors = _run_polar_block(
        monkeypatch, watch_value=boom, summary_raises=False)
    assert result["polar_watch"] is None
    assert [c for c, _ in errors] == ["PolarWatch"]
    assert any("❌ 극지 관찰 실패: RuntimeError: Open-Meteo 503" in m for m in logs)


# ── 3) 배선 — 실제 블록이 이 모양인가 (만들어만 두는 것 방지) ─────────────

def test_the_production_block_has_this_shape():
    """`collect_free_sources` 의 극지 블록이 위 흐름과 같은지 소스로 확인한다.

    위 시험들은 흐름을 재현한 것이라, 실제 블록이 옛 모양으로 돌아가도 초록일 수
    있다. 이 리포가 반복해서 데인 '만들어만 두고 아무도 안 부른다' 의 짝이다.
    """
    import inspect
    src = inspect.getsource(collector.collect_free_sources)
    block = src[src.index("극지 관찰층"):src.index("현지어 위키 신호")]
    # 요약은 수집 try 밖(else)에서, 제 몫의 try 로 감싸서 부른다
    assert "else:" in block and "_polar_summary_line" in block
    assert "요약 줄 생성 실패(자료는 보존)" in block
    # 옛 모양(요약 줄이 수집 try 안에서 %.0f 로 직접 찍던 것)이 돌아오지 않았다.
    # 주석에는 사고 기록으로 그 서식이 적혀 있으니 **코드 줄만** 본다.
    code = "\n".join(l for l in block.splitlines()
                     if not l.lstrip().startswith("#"))
    assert "%.0f" not in code
    assert "polar_watch_score" not in code       # 점수 서식은 헬퍼의 몫이다
    # 요약 실패에는 log_error 를 부르지 않는다 — except 는 수집 쪽 하나뿐이다
    assert block.count('log_error("PolarWatch"') == 1

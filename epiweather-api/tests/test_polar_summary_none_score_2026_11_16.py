"""극지 관찰 — **판정과 서식을 떼어놓는다** (2026-11-16).

`test_polar_summary_line_2026_11_16.py`(#124)가 같은 사고를 다른 쪽에서 막는다:
점수 None 을 `점수 없음` 으로 적어 **줄이 안 죽게** 했다. 이 파일은 그 뒤에 남는
질문을 맡는다 — **줄이 죽더라도 자료가 안 날아가는가.**

## 왜 둘이 필요한가

11-14~15 사고에서 터진 건 서식(`%.0f` ← None)이었는데, 손실은 자료였다:

    result["polar_watch"] = polar_watch_all()   # ← 8개 관측지, 이미 성공
    log(... "%.0f" % None ...)                  # ← 여기서 TypeError
    except: result["polar_watch"] = None        # ← 성공한 자료를 덮어쓴다
                                                #   record_cycle 이 수집 실패로 센다

#124 는 **이 서식 버그**를 고쳤다. 그런데 서식이 또 다른 이유로 터지면(새 필드,
인코딩, 다음 사람이 넣는 `%d`) **같은 손실이 그대로 되풀이된다.** 고쳐야 할 것은
`%.0f` 하나가 아니라 *"찍다가 실패하면 받아온 것을 버린다"* 는 구조다.

그래서 호출부는 이 순서를 지킨다:

    ① weather_ok = polar_weather_ok(pw)         ← 자료의 성질로 **먼저** 정한다
      result["polar_watch"] = pw if weather_ok else None
    ② try: log(polar_summary_line(pw)[0])       ← 그 다음에 찍는다
      except: 사유만 남기고 자료는 그대로

`polar_weather_ok` 를 `polar_summary_line` 에서 떼어낸 게 이 때문이다 — 판정이
문자열을 만드는 일에 의존하면 안 된다.
"""
import collector


def _region(name, score, weather=True):
    return {"region": name, "name": name, "polar_watch_score": score,
            "thaw": {"data_available": weather}}


_GOOD = {"grade": "watch", "regions": [_region("야말", 72.0), _region("아이슬란드", None, False)]}


# ── 판정이 서식과 같은 답을 내는가 (한 곳에서만 정의된다) ────────────────

def test_the_verdict_is_the_same_whether_you_ask_it_or_the_line():
    """`polar_summary_line` 은 판정을 **스스로 계산하지 않고** 이 함수에 묻는다.

    두 군데서 따로 계산하면 조용히 갈라진다 — 이 리포가 캘리브레이션 플래그에서
    이미 데인 모양이다(응답 dict 안의 `False` 리터럴, 2026-08-30).
    """
    for pw in (_GOOD,
               {"grade": None, "regions": [_region("a", None, False)]},
               {"regions": []}):
        assert collector.polar_summary_line(pw)[1] == collector.polar_weather_ok(pw)


def test_the_verdict_needs_no_formatting():
    assert collector.polar_weather_ok(_GOOD) is True
    assert collector.polar_weather_ok({"regions": [_region("a", None, False)]}) is False
    assert collector.polar_weather_ok({"regions": []}) is False
    assert collector.polar_weather_ok(None) is False      # 호출부가 None 을 줘도 안 터진다


# ── 요약 줄이 터져도 자료는 남는다 ───────────────────────────────────────

def _run_polar_block(monkeypatch, *, watch_value, summary_raises):
    """collector 의 극지 블록과 **같은 제어 흐름**을 돌린다.

    블록 자체는 `collect_free_sources` 안에 있어 통째로 부르면 20여 개 소스를 다
    두드린다(시험은 외부에 못 나간다). 아래
    `test_the_production_block_decides_before_it_prints` 가 실제 블록이 이 순서임을 고정한다.
    """
    logs, errors = [], []
    monkeypatch.setattr(collector, "log", lambda m: logs.append(m))
    monkeypatch.setattr(collector, "log_error", lambda c, e: errors.append((c, e)))
    if summary_raises:
        def boom(_pw):
            raise TypeError("must be real number, not NoneType")
        monkeypatch.setattr(collector, "polar_summary_line", boom)

    result = {}
    try:
        pw = watch_value()
    except Exception as e:
        result["polar_watch"] = None
        collector.log(f"  ❌ 극지 관찰 실패: {type(e).__name__}: {e}")
        collector.log_error("PolarWatch", e)
    else:
        weather_ok = collector.polar_weather_ok(pw)
        result["polar_watch"] = pw if weather_ok else None
        try:
            collector.log(collector.polar_summary_line(pw)[0])
        except Exception as e:
            collector.log(f"  ⚠ 극지 관찰 요약 줄 생성 실패(자료는 보존): "
                          f"{type(e).__name__}: {e}")
        if not weather_ok:
            collector.log("  ❌ 극지 관찰: 모든 관측지 기상 자료 없음 — "
                          "이 주기 측정 없음(소스 헬스 실패로 셈)")
    return result, logs, errors


def test_summary_failure_keeps_the_collected_data(monkeypatch):
    """11-14~15 손실의 핵심 — 찍다 실패했다고 받아온 자료를 버리지 않는다."""
    result, logs, _ = _run_polar_block(
        monkeypatch, watch_value=lambda: _GOOD, summary_raises=True)
    assert result["polar_watch"] == _GOOD                  # 예전엔 None 이 됐다
    assert any("요약 줄 생성 실패(자료는 보존)" in m for m in logs)


def test_summary_failure_is_not_counted_as_a_collection_failure(monkeypatch):
    """소스 헬스는 수집의 성패를 말하는 자리다 — 서식 버그로 소스를 죽이지 않는다."""
    _, logs, errors = _run_polar_block(
        monkeypatch, watch_value=lambda: _GOOD, summary_raises=True)
    assert errors == []                                    # log_error("PolarWatch", …) 없음
    assert not any("❌ 극지 관찰 실패" in m for m in logs)


def test_summary_failure_does_not_mask_a_total_weather_outage(monkeypatch):
    """★ 반대 방향도 지킨다 ★ 줄이 터졌다고 '측정 없음' 판정이 사라지면,
    여덟 곳 모두 눈을 감은 주기가 조용히 정상으로 셈된다."""
    blind = {"grade": None, "regions": [_region("a", None, False), _region("b", None, False)]}
    result, logs, errors = _run_polar_block(
        monkeypatch, watch_value=lambda: blind, summary_raises=True)
    assert result["polar_watch"] is None
    assert any("모든 관측지 기상 자료 없음" in m for m in logs)
    assert errors == []            # 수집은 성공했다 — log_error 는 아니다


def test_a_real_collection_failure_still_fails_the_source(monkeypatch):
    """반대쪽 — 진짜 수집 실패는 예전처럼 None 이고 log_error 로 올라간다."""
    def boom():
        raise RuntimeError("Open-Meteo 503")
    result, logs, errors = _run_polar_block(
        monkeypatch, watch_value=boom, summary_raises=False)
    assert result["polar_watch"] is None
    assert [c for c, _ in errors] == ["PolarWatch"]
    assert any("❌ 극지 관찰 실패: RuntimeError: Open-Meteo 503" in m for m in logs)


# ── 배선 — 실제 블록이 이 순서인가 ──────────────────────────────────────

def test_the_production_block_decides_before_it_prints():
    """위 시험들은 흐름을 재현한 것이라, 실제 블록이 옛 모양으로 돌아가도 초록일 수
    있다. 이 리포가 반복해서 데인 '만들어만 두고 아무도 안 부른다' 의 짝이다.
    """
    import inspect
    src = inspect.getsource(collector.collect_free_sources)
    block = src[src.index("극지 관찰층"):src.index("헤임달: 공개 시퀀스")]
    code = "\n".join(l for l in block.splitlines() if not l.lstrip().startswith("#"))

    # 판정이 서식보다 **먼저** 온다
    assert code.index("polar_weather_ok") < code.index("polar_summary_line")
    # 자료 보존은 판정에만 달려 있다
    assert 'result["polar_watch"] = pw if weather_ok else None' in code
    # 찍는 일은 제 몫의 try 안에 있다
    assert "요약 줄 생성 실패(자료는 보존)" in block
    # 옛 모양(수집 try 안에서 직접 서식)이 돌아오지 않았다
    assert "%.0f" not in code and "polar_watch_score" not in code
    # 요약 실패에 log_error 를 부르지 않는다 — except 는 수집 쪽 하나뿐이다
    assert block.count('log_error("PolarWatch"') == 1

"""브리핑 특수 섹션의 원칙 (2026-08-26).

배경: `algorithms/` 에 모듈이 84개인데 `daily_brief.py` 가 쓰던 건 4개뿐이었다.
극지·조용해진 곳·7일 예보·설명 불가 신호는 **매일 값이 달라지는데** 브리핑에
실리지 않아, 7일 연속으로 헤드라인이 똑같았다(연속 유사도 88~89%).
캡틴: *"나라도 텔레그램 이거 안 보게 되는데."*

이 테스트가 고정하는 선 셋:
  1. **없으면 안 만든다** — 할 말이 없는 칸은 통째로 빠진다. 지어내지 않는다.
  2. **정직성 경계선을 함께 싣는다** — 관찰 vs 경보, 측정 vs 추정.
  3. **한 층이 죽어도 브리핑은 나간다** — 브리핑은 매일 나가야 하는 것이다.
"""
from __future__ import annotations

from unittest.mock import patch

from algorithms import brief_sections as bs


# ── 1. 없으면 안 만든다 ──────────────────────────────────────────────────────

def test_silence_section_is_omitted_when_nothing_dropped():
    """급감한 신호가 없으면 칸을 통째로 뺀다 — '조용한 곳 없음'은 뉴스가 아니다."""
    with patch.object(bs, "__name__", bs.__name__):
        with patch("algorithms.negative_space.scan_negative_space",
                   return_value={"alerts": [], "alert_count": 0, "metrics_checked": 37}):
            assert bs.build_silence_section("ko") is None


def test_polar_section_is_omitted_when_everything_is_frozen():
    """전 지역이 얼어 있으면 관찰할 해빙이 없다 — 억지로 쓰지 않는다."""
    frozen = {"regions": [
        {"region": "greenland", "name": "그린란드",
         "thaw": {"permafrost_thaw_pressure": 0.0, "thaw_days_30d": 0, "heat_trend_c": -8.0}},
    ]}
    with patch("algorithms.polar_signals.polar_watch_all", return_value=frozen):
        assert bs.build_polar_section("ko") is None


def test_unexplained_section_is_omitted_when_empty():
    with patch("algorithms.unexplained.scan_unexplained",
               return_value={"alerts": [], "alert_count": 0}):
        assert bs.build_unexplained_section("ko") is None


def test_forecast_section_is_omitted_without_scores():
    with patch("algorithms.forecast_engine.forecast_summary", return_value={}):
        assert bs.build_forecast_section("ko") is None


# ── 2. 정직성 경계선이 실린다 ────────────────────────────────────────────────

def test_polar_carries_the_watch_not_alert_caveat():
    """★핵심★ '관찰이지 경보가 아니다'가 빠지면 흔한 대시보드와 같아진다."""
    payload = {
        "regions": [{
            "region": "siberia_yamal", "name": "시베리아 야말(러시아)",
            "thaw": {"permafrost_thaw_pressure": 78.7, "thaw_days_30d": 30, "heat_trend_c": 1.4},
            "news": {"sample_titles": []},
        }],
        "grade": "watch",
        "note": "이 층은 저확률·고충격 '관찰(watch)'이지 '경보(alert)'가 아니다.",
        "disclaimer": "thaw_days는 기후 정상값 대비 이상이 아니라 해빙 활동 프록시.",
    }
    with patch("algorithms.polar_signals.polar_watch_all", return_value=payload):
        sec = bs.build_polar_section("ko")

    assert sec is not None
    assert "관찰" in sec["honesty"] and "경보" in sec["honesty"]
    assert "프록시" in sec["honesty"]
    assert sec["grade"] == "watch"


def test_forecast_says_it_is_extrapolation_not_measurement():
    payload = {"score_7d": 58.0, "score_14d": 58.3, "tier_7d": "정상",
               "tier_14d": "정상", "confidence": "medium", "top_alerts": []}
    with patch("algorithms.forecast_engine.forecast_summary", return_value=payload):
        sec = bs.build_forecast_section("ko")

    assert "측정된 발병 수가 아니라" in sec["honesty"]


# ── 3. 한 층이 죽어도 브리핑은 나간다 ───────────────────────────────────────

def test_one_broken_layer_does_not_kill_the_rest():
    """★핵심★ 외부 API 하나가 터졌다고 그날 브리핑이 통째로 빠지면 안 된다."""
    seen = []
    with patch("algorithms.polar_signals.polar_watch_all", side_effect=RuntimeError("극지 API 죽음")), \
         patch("algorithms.negative_space.scan_negative_space",
               return_value={"alerts": [{"metric": "naver_ebola_ratio", "latest": 2.27,
                                         "history_avg": 7.05, "drop_ratio": 0.32,
                                         "message": "⚠️ 신호 50% 감소"}],
                             "metrics_checked": 37}), \
         patch("algorithms.forecast_engine.forecast_summary", return_value={}), \
         patch("algorithms.unexplained.scan_unexplained", return_value={"alerts": []}):
        sections = bs.build_special_sections("ko", on_error=lambda n, e: seen.append(n))

    ids = [s["id"] for s in sections]
    assert "silence" in ids          # 살아남은 층은 나간다
    assert "polar" not in ids        # 죽은 층만 빠진다
    assert seen == ["polar"]         # 조용히 삼키지 않고 알린다


# ── 4. Google News 쓰레기 제목 거르기 ───────────────────────────────────────

def test_search_query_echo_is_not_shown_as_a_headline():
    """★실측★ Google News 는 우리가 던진 검색어를 제목 자리에 돌려준다.

    그대로 브리핑에 실으면 고장난 것처럼 보인다.
    """
    titles = [
        '"сибирская язва OR падёж оленей OR вечная мерзлота OR bird flu" - Google Новости',
        "Google Новости",
        "Ancient viruses are being awakened by melting permafrost - BBC Science Focus",
        "",
        None,
    ]
    out = bs.clean_news_titles(titles)

    assert out == ["Ancient viruses are being awakened by melting permafrost - BBC Science Focus"]


def test_clean_titles_handles_missing_input():
    assert bs.clean_news_titles(None) == []
    assert bs.clean_news_titles([]) == []


# ── 5. 지표 이름을 사람 말로, 모르면 그대로 ─────────────────────────────────

def test_known_metric_gets_a_human_label():
    assert bs.metric_label("africa_cdc_deaths", "ko") == "아프리카 CDC 사망"
    assert bs.metric_label("africa_cdc_deaths", "en") == "Africa CDC deaths"


def test_unknown_metric_keeps_its_identifier():
    """★모르는 건 억지로 번역하지 않는다★ 뜻이 틀어지는 것보다 영어가 낫다."""
    assert bs.metric_label("some_new_metric_v2", "ko") == "some_new_metric_v2"
    assert bs.metric_label(None, "ko") == "?"


# ── 6. 사람 수를 소수점으로 쓰지 않는다 ─────────────────────────────────────

def test_people_counts_are_whole_numbers():
    """예보 엔진은 외삽이라 4885.5 를 낸다 — '4,885.5명'은 말이 안 된다."""
    from algorithms.notifier import _fmt_num

    assert _fmt_num(4885.5, whole=True) == "4,886"
    assert _fmt_num(2290.7, whole=True) == "2,291"
    # 사람이 아닌 값은 소수점을 살린다(점수·비율)
    assert _fmt_num(78.7) == "78.7"
    assert _fmt_num(None) == "—"


# ── 7. 텔레그램 메시지가 특수 섹션을 싣는다 ─────────────────────────────────

def test_telegram_message_carries_the_daily_changing_parts():
    """예전 메시지는 순위표에서 나온 값만 보내 7일 내내 같았다."""
    from algorithms.notifier import format_daily_brief_message

    brief = {
        "headline": "테스트 헤드라인",
        "summary": "요약",
        "segments": [{"kind": "threat", "lower_third": f"위협{i}"} for i in range(5)],
        "special_sections": [{
            "id": "silence", "icon": "🔇", "title": "조용해진 곳",
            "lead": "37개 지표 중 1개가 절반 아래로 떨어졌습니다.",
            "rows": [{"metric": "naver_ebola_ratio", "label": "네이버 에볼라 검색",
                      "latest": 2.27, "history_avg": 7.05}],
        }],
    }
    msg = format_daily_brief_message(brief)

    assert "조용해진 곳" in msg
    assert "네이버 에볼라 검색" in msg          # 식별자가 아니라 사람 말로
    assert "naver_ebola_ratio" not in msg
    # 반복되는 위협 목록은 2건까지만 — 아래 특수 섹션이 묻히지 않게
    assert "위협0" in msg and "위협1" in msg
    assert "위협4" not in msg
    assert "외 3건 추적 중" in msg


# ── 8. 모든 섹션은 정직성 문구를 갖는다 ─────────────────────────────────────

def test_every_section_carries_its_limits():
    """★핵심★ 한 칸이라도 한계 표시가 비면 흔한 AI 대시보드와 구분되지 않는다.

    실제로 `조용해진 곳` 이 이걸 빼먹은 채 프로덕션에 나갔다(2026-08-26).
    "이 층은 실측이라 단서가 필요 없다"고 판단했는데 틀렸다 —
    `negative_space` 자기 주석이 오탐 사례를 셋이나 적어두고 있었다
    (브라질 뎅기 계절성 · OpenSky 희소표본 · 평균 2 미만 SNS 지표).
    """
    payload_silence = {"alerts": [{"metric": "naver_ebola_ratio", "latest": 2.27,
                                   "history_avg": 7.05, "drop_ratio": 0.32,
                                   "message": "⚠️ 신호 50% 감소"}],
                       "metrics_checked": 37}
    payload_polar = {"regions": [{"region": "siberia_yamal", "name": "야말",
                                  "thaw": {"permafrost_thaw_pressure": 78.7,
                                           "thaw_days_30d": 30, "heat_trend_c": 1.4},
                                  "news": {"sample_titles": []}}],
                     "grade": "watch",
                     # 실제 프로덕션 문구를 그대로 쓴다 — 짧은 더미로는 이 테스트가 무의미하다
                     "note": "이 층은 저확률·고충격 '관찰(watch)'이지 '경보(alert)'가 아니다 "
                             "— 경보 파이프라인과 섞지 않는다.",
                     "disclaimer": "thaw_days는 기후 정상값 대비 이상이 아니라 해빙 활동 프록시."}
    payload_forecast = {"score_7d": 58.0, "score_14d": 58.3, "tier_7d": "정상",
                        "tier_14d": "정상", "confidence": "medium", "top_alerts": []}
    payload_unexplained = {"alerts": [{"source": "x", "signal_date": "2026-08-12"}],
                           # 실제 프로덕션 caveat
                           "caveat": "조건1(병원방문 급증)은 증후군감시 데이터 소스가 없어 "
                                     "측정 불가 — 조건2·3은 추출 시점에 모델이 직접 판단한 "
                                     "known_disease 필드로 판정함."}

    with patch("algorithms.negative_space.scan_negative_space", return_value=payload_silence),          patch("algorithms.polar_signals.polar_watch_all", return_value=payload_polar),          patch("algorithms.forecast_engine.forecast_summary", return_value=payload_forecast),          patch("algorithms.unexplained.scan_unexplained", return_value=payload_unexplained):
        sections = bs.build_special_sections("ko")

    assert len(sections) == 4
    for sec in sections:
        assert sec.get("honesty"), f"{sec['id']} 섹션에 정직성 문구가 없다"
        assert len(sec["honesty"]) > 20, f"{sec['id']} 정직성 문구가 너무 짧다"


def test_silence_honesty_names_the_actual_false_positives():
    """빈말이 아니라 **실제로 확인된 오탐 사례**를 적는다 — 그게 신뢰의 근거다."""
    with patch("algorithms.negative_space.scan_negative_space",
               return_value={"alerts": [{"metric": "m", "latest": 1, "history_avg": 9}],
                             "metrics_checked": 37}):
        sec = bs.build_silence_section("ko")

    h = sec["honesty"]
    assert "경험 규칙" in h              # 검증된 임계값이 아니라고 밝힌다
    assert "계절성" in h                 # 실제 오탐 원인
    assert "확인해볼 것" in h            # 결론이 아니라 단서라고 못박는다

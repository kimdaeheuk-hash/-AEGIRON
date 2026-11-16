"""극지 관찰 요약 로그 — 점수 없는 관측지가 있어도 줄이 죽지 않는다 (2026-11-16 소킹 발견).

2026-11-15 10:00~익일 00:00 운영: `❌ 극지 관찰 실패: TypeError: must be real number, not NoneType`.
Open-Meteo 가 안 되자 일부 관측지 polar_watch_score 가 None 이 됐고, 로그의 `%.0f` 가 죽으면서
이미 계산된 층 전체가 '실패'로 버려졌다(소스 헬스 PolarWatch 중단 12시간 · 간헐 성공 42%).
"""
import collector


def _region(name, score, weather=True):
    return {"region": name, "name": name, "polar_watch_score": score,
            "thaw": {"data_available": weather}}


def test_none_score_does_not_crash_and_is_named():
    pw = {"grade": "watch", "regions": [_region("야말", 72.0), _region("그린란드", None, weather=False)]}
    line, ok = collector.polar_summary_line(pw)
    assert "야말(72)" in line and "그린란드(점수 없음)" in line
    assert "기상 자료 없음 1/2(판정 안 함)" in line
    assert ok is True  # 일부만 없으면 값은 살린다


def test_all_regions_without_weather_is_not_ok():
    pw = {"grade": None, "regions": [_region("a", None, False), _region("b", None, False)]}
    line, ok = collector.polar_summary_line(pw)
    assert ok is False and "기상 자료 없음 2/2" in line


def test_empty_regions():
    line, ok = collector.polar_summary_line({"regions": []})
    assert ok is False and "상위 없음" in line


def test_normal_line_unchanged_shape():
    pw = {"grade": "watch", "regions": [_region("시베리아 야말(러시아)", 72.0), _region("아이슬란드", 72.0)]}
    line, ok = collector.polar_summary_line(pw)
    assert line == "  극지 관찰: 2개 관측지 · 등급 watch · 상위 시베리아 야말(러시(72), 아이슬란드(72)"
    assert ok is True

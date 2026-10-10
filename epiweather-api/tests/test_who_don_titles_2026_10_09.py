"""WHO DON 제목 파서 개선 (2026-10-09, 소킹 일지 10-08).

## 관측
프로덕션 21:00 슬롯: `검토 100건 · 국가 못 읽음 7 · 기간 밖 45 · 제목 형식 모름 33` — 기간 안 55건 중 40건(73%)을
못 읽었다. 어떤 제목이 안 읽히는지 로그에 없어 추측만 가능했다.

## 고친 것
1. 구분자 형식 말고도 `… in 국가`, `질병, 국가`, `Disease Outbreak News:` 접두를 읽는다 — 단, 국가 문구가
   **사전에서 나라로 읽힐 때만** 쓴다. 안 읽히면 버린다(추측하지 않는다).
2. 못 읽은 제목의 예(사유별 3건, 90자)를 로그에 남긴다 — 다음 개선은 실제 제목을 보고 한다.
"""
from __future__ import annotations

import datetime as dt

from algorithms import who_don_declarations as don

TODAY = dt.date.today()


def _items(*titles):
    return {"value": [{"Title": t, "PublicationDate": (TODAY - dt.timedelta(days=3)).isoformat(), "DonId": f"D{i}"}
                      for i, t in enumerate(titles)]}


def _parsed(*titles):
    return don.parse_items(_items(*titles))


def _pairs(out):
    return [(d["disease"], d["iso3"]) for d in out["declarations"]]


def test_the_original_dash_format_is_unchanged():
    assert _pairs(_parsed("Cholera – Angola")) == [("Cholera", "AGO")]


def test_in_format_is_read_and_the_leading_noise_is_stripped():
    assert _pairs(_parsed("Outbreak of cholera in Angola")) == [("cholera", "AGO")]
    assert _pairs(_parsed("Human cases of avian influenza A(H5N1) in Cambodia")) == [
        ("avian influenza A(H5N1)", "KHM")]


def test_comma_format_is_read():
    assert _pairs(_parsed("Mpox, Sierra Leone")) == [("Mpox", "SLE")]


def test_the_disease_outbreak_news_prefix_is_dropped():
    assert _pairs(_parsed("Disease Outbreak News: Cholera - Angola")) == [("Cholera", "AGO")]


def test_titles_whose_place_is_not_a_country_are_still_skipped_not_guessed():
    out = _parsed("Mpox – African Region", "Cholera in Africa", "Global situation of avian influenza",
                  "Multi-country outbreak of mpox")
    assert out["declarations"] == []
    assert set(out["skipped"]) <= {"국가 못 읽음", "제목 형식 모름"} and sum(out["skipped"].values()) == 4


def test_the_dash_option_wins_when_both_would_read():
    """`Cholera in outbreak – Angola` 처럼 두 형식이 겹치면 구분자 쪽(더 믿을 만한 형식)을 쓴다."""
    out = _parsed("Imported cases in transit – Angola")
    assert _pairs(out) == [("Imported cases in transit", "AGO")]


def test_unreadable_titles_are_sampled_per_reason_with_a_cap():
    titles = [f"무관한 제목 번호 {i} " + "가" * 200 for i in range(7)]
    out = _parsed("Cholera – Angola", *titles)           # 하나는 읽혀야 한다(전부 못 읽으면 일부러 실패한다)
    ex = out["samples"]["제목 형식 모름"]
    assert len(ex) == don.SAMPLES_PER_REASON == 3
    assert all(len(t) <= don.SAMPLE_CHARS for t in ex)


def test_country_unreadable_titles_are_sampled_too():
    out = _parsed("Mpox – African Region")
    assert out["samples"]["국가 못 읽음"] == ["Mpox – African Region"]


def test_samples_line_names_the_reasons_and_is_silent_when_empty():
    assert don.samples_line({"예시": {}}) is None
    line = don.samples_line({"예시": {"제목 형식 모름": ["A 제목", "B 제목"], "국가 못 읽음": ["Mpox – African Region"]}})
    assert line.startswith("WHO DON 못 읽은 제목 예: ")
    assert "제목 형식 모름[A 제목 / B 제목]" in line and "국가 못 읽음[Mpox – African Region]" in line


def test_ingest_result_carries_the_samples(isolated_db):
    res = don.ingest_don(_items("Outbreak of cholera in Angola", "엉뚱한 제목"))
    assert res["등재"] == 1 and res["예시"] == {"제목 형식 모름": ["엉뚱한 제목"]}


def test_main_logs_the_samples_line():
    import ast
    import inspect
    import main
    fn = next(f for n, f in vars(main).items() if callable(f) and getattr(f, "__module__", "") == "main"
              and "ingest_don" in _src(f))
    names = {n.id for n in ast.walk(ast.parse(inspect.getsource(fn))) if isinstance(n, ast.Name)}
    assert "samples_line" in names


def _src(f):
    import inspect
    try:
        return inspect.getsource(f)
    except (OSError, TypeError):
        return ""

"""현지어 뉴스 RSS — 키워드 매칭·집계 로직 검증. 실제 네트워크 호출은
mock으로 대체(이 개발 환경은 외부 RSS 접근이 막혀 있고, 라이브 피드 상태에
테스트 결과가 좌우되면 안 됨)."""
from __future__ import annotations
import ast
import pathlib
from unittest.mock import patch, MagicMock

import requests

from algorithms import local_news as ln

from algorithms.local_news import (
    LOCAL_FEEDS, fetch_local_feed, fetch_all_local_news, _count_keyword_hits,
)

SAMPLE_RSS_WITH_HIT = """<?xml version="1.0"?>
<rss><channel>
<item><title>Ebola outbreak reported in region</title></item>
<item><title>Local weather update</title></item>
</channel></rss>"""


def test_count_keyword_hits_case_insensitive():
    assert _count_keyword_hits("Ebola Outbreak", ["ebola"]) == 1
    assert _count_keyword_hits("nothing relevant here", ["ebola", "cholera"]) == 0


def test_fetch_local_feed_counts_items_and_keyword_hits():
    with patch("algorithms.local_news.requests.get") as mock_get:
        mock_resp = MagicMock(status_code=200, text=SAMPLE_RSS_WITH_HIT)
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        result = fetch_local_feed("test_feed", "영어", "테스트지역", "http://example.com/rss", ["ebola"])

    assert result["status"] == "ok"
    assert result["item_count"] == 2
    assert result["keyword_hits"] == 1
    assert result["hit_ratio"] == 0.5


def test_fetch_local_feed_returns_error_status_on_failure():
    with patch("algorithms.local_news.requests.get", side_effect=ConnectionError("blocked")):
        result = fetch_local_feed("test_feed", "영어", "테스트지역", "http://example.com/rss", ["ebola"])
    assert result["status"] == "error"
    assert "error" in result


def test_all_feeds_have_language_region_and_nonempty_keywords():
    """전세계 확장(㉘) — 사실상 전 세계(160개국+) 커버, 각 피드 구조 온전·slug 유일."""
    assert len(LOCAL_FEEDS) >= 160
    slugs = [f[0] for f in LOCAL_FEEDS]
    assert len(slugs) == len(set(slugs))  # slug 중복 없음
    for slug, lang, region, url, keywords in LOCAL_FEEDS:
        assert slug and lang and region and url.startswith("https://news.google.com/")
        assert len(keywords) >= 5  # 현지어 + 공통 질병명 앵커


def test_previously_missing_high_risk_countries_now_covered():
    """이전 48개판에서 빠졌던 역학적 핵심국이 실제로 포함됐는지 회귀 방지 —
    시에라리온·라이베리아(에볼라 진원)·미국·UAE·아이티·남아공·말리·카자흐스탄 등."""
    slugs = {f[0] for f in LOCAL_FEEDS}
    for iso2 in ("sl", "lr", "us", "ae", "ht", "za", "ml", "kz", "la", "ma", "so", "ss"):
        assert f"gn_{iso2}" in slugs, f"{iso2} 누락"


def test_feeds_span_multiple_continents():
    """오지·발병 고위험 지역이 실제로 들어있는지(아프리카·중동·남아시아·중남미·태평양)."""
    regions = " ".join(f[2] for f in LOCAL_FEEDS)
    for continent in ("아프리카", "중동", "남아시아", "동남아", "남미", "태평양"):
        assert continent in regions, f"{continent} 커버리지 없음"


def test_universal_disease_terms_merged_into_every_feed():
    """모든 피드 키워드에 공통 질병명(교차언어 앵커)이 병합됐는지 — 현지어를
    다 번역하지 않아도 Ebola·Cholera 등이 현지어 기사에서 잡히게 하는 장치."""
    from algorithms.local_news import UNIVERSAL_DISEASE_TERMS
    for _, _, _, _, keywords in LOCAL_FEEDS:
        assert "ebola" in keywords and "cholera" in keywords
        assert set(UNIVERSAL_DISEASE_TERMS).issubset(set(keywords))


def test_fetch_all_local_news_aggregates_across_all_feeds():
    with patch("algorithms.local_news.requests.get") as mock_get:
        mock_resp = MagicMock(status_code=200, text=SAMPLE_RSS_WITH_HIT)
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        result = fetch_all_local_news()

    assert result["total_feeds"] == len(LOCAL_FEEDS)
    assert result["active_feeds"] == len(LOCAL_FEEDS)
    assert result["total_kw_hits"] > 0
    # _all_titles는 내부용이라 최종 응답에는 없어야 함
    assert all("_all_titles" not in f for f in result["feeds"])


# ── 프로브 (2026-10-02) — 11·12시 UTC 의 `HTTPError 503×179` ────────────────
def _http_error(status, retry_after=None):
    resp = MagicMock(status_code=status, headers=(
        {"Retry-After": retry_after} if retry_after is not None else {}))
    err = requests.exceptions.HTTPError(f"{status} Server Error", response=resp)
    return err


def _ok_resp():
    r = MagicMock(status_code=200, text=SAMPLE_RSS_WITH_HIT)
    r.raise_for_status = lambda: None
    return r


def _bad_resp(status, retry_after=None):
    r = MagicMock(status_code=status)
    r.raise_for_status = MagicMock(side_effect=_http_error(status, retry_after))
    return r


def test_error_feed_keeps_status_and_retry_after():
    with patch("algorithms.local_news.requests.get", return_value=_bad_resp(503, "120")):
        r = fetch_local_feed("x", "영어", "t", "http://e/rss", ["ebola"])
    assert r["status"] == "error"
    assert r["http_status"] == 503
    assert r["retry_after"] == "120"
    assert r["reason"] == "HTTPError 503"      # 기존 사유 문자열은 그대로


def test_probe_healthy_fetches_every_feed_once():
    sleeps = []
    with patch("algorithms.local_news.requests.get", return_value=_ok_resp()) as g:
        results, report = ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=sleeps.append)
    assert len(results) == len(LOCAL_FEEDS)
    assert [r["slug"] for r in results] == [f[0] for f in LOCAL_FEEDS]   # 순서 보존
    assert g.call_count == len(LOCAL_FEEDS)                              # 프로브 중복 호출 없음
    assert all(r["status"] == "ok" for r in results)
    assert report["attempts"] == 1 and not report["throttled"] and sleeps == []


def test_probe_recovers_after_transient_throttle():
    seq = [_bad_resp(503), _ok_resp()]
    sleeps = []

    def fake_get(url, **kw):
        # 프로브(첫 호출 둘)만 순서대로, 이후 일반 피드는 정상
        return seq.pop(0) if seq else _ok_resp()

    with patch("algorithms.local_news.requests.get", side_effect=fake_get):
        results, report = ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=sleeps.append)
    assert report["attempts"] == 2 and not report["throttled"]
    assert sleeps == [ln.PROBE_RETRY_WAITS[0]]
    assert all(r["status"] == "ok" for r in results)


def test_probe_still_throttled_skips_the_burst_and_says_so():
    sleeps = []
    with patch("algorithms.local_news.requests.get", return_value=_bad_resp(503)) as g:
        results, report = ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=sleeps.append)
    # 179건이 아니라 프로브 3번만 나갔다
    assert g.call_count == 1 + len(ln.PROBE_RETRY_WAITS)
    assert len(results) == len(LOCAL_FEEDS)
    assert all(r["status"] == "error" for r in results)
    skipped = [r for r in results if r["reason"] == ln.SKIPPED_REASON]
    assert len(skipped) == len(LOCAL_FEEDS) - 1
    assert report["throttled"] and report["skipped"] == len(skipped)
    assert report["attempts"] == 1 + len(ln.PROBE_RETRY_WAITS)
    assert sleeps == list(ln.PROBE_RETRY_WAITS)
    # 생략을 '503 이었다' 로 둔갑시키지 않는다 — 사유가 갈려 보여야 한다
    summary = ln.failure_summary(results)
    assert ln.SKIPPED_REASON in summary and "HTTPError 503×1" in summary


def test_probe_honors_retry_after_but_caps_it():
    sleeps = []
    with patch("algorithms.local_news.requests.get",
               return_value=_bad_resp(503, "3600")):
        ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=sleeps.append)
    assert sleeps == [ln.PROBE_MAX_WAIT] * len(ln.PROBE_RETRY_WAITS)

    sleeps.clear()
    with patch("algorithms.local_news.requests.get",
               return_value=_bad_resp(503, "Wed, 21 Oct 2026 07:28:00 GMT")):
        ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=sleeps.append)
    assert sleeps == list(ln.PROBE_RETRY_WAITS)      # 못 읽은 값은 기본 대기


def test_probe_failure_that_is_not_throttling_does_not_skip_anything():
    """연결 실패 같은 프로브 실패는 '막힘'이 아니다 — 나머지를 건너뛰면 멀쩡한
    178개를 우리가 버리는 셈이다."""
    calls = {"n": 0}

    def fake_get(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("reset")
        return _ok_resp()

    with patch("algorithms.local_news.requests.get", side_effect=fake_get):
        results, report = ln.fetch_feeds_with_probe(LOCAL_FEEDS, sleep=lambda s: None)
    assert not report["throttled"] and report["skipped"] == 0
    assert sum(r["status"] == "ok" for r in results) == len(LOCAL_FEEDS) - 1
    assert calls["n"] == len(LOCAL_FEEDS)


def test_fetch_all_local_news_goes_through_the_probe_and_reports_it():
    """전멸 주기에도 dict 가 정상 모양으로 오고, 소스 건강이 값없음으로 센다."""
    with patch("algorithms.local_news.requests.get", return_value=_bad_resp(503, "90")), \
         patch("algorithms.local_news.time.sleep"):
        out = fetch_all_local_news()
    assert out["total_feeds"] == len(LOCAL_FEEDS) and out["active_feeds"] == 0
    assert out["fetch_probe"]["throttled"] and out["fetch_probe"]["retry_after"] == "90"
    assert ln.SKIPPED_REASON in out["failure_summary"]


def test_wiring_collector_logs_probe_and_scan_calls_it():
    """만들어만 두고 아무도 안 부르는 층을 막는다 — AST 로 호출 자체를 고정."""
    root = pathlib.Path(ln.__file__).parent
    tree = ast.parse(pathlib.Path(ln.__file__).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "fetch_all_local_news")
    called = {c.func.id for c in ast.walk(fn)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert "fetch_feeds_with_probe" in called
    collector = (root.parent / "collector.py").read_text(encoding="utf-8")
    assert 'n.get("fetch_probe")' in collector

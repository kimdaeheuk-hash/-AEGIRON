"""현지어 뉴스 RSS — 키워드 매칭·집계 로직 검증. 실제 네트워크 호출은
mock으로 대체(이 개발 환경은 외부 RSS 접근이 막혀 있고, 라이브 피드 상태에
테스트 결과가 좌우되면 안 됨)."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

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
    """12개 피드(기존 7 + 신규 5) 전부 구조가 온전한지 잠금 테스트."""
    assert len(LOCAL_FEEDS) == 12
    for slug, lang, region, url, keywords in LOCAL_FEEDS:
        assert slug and lang and region and url.startswith("https://")
        assert len(keywords) >= 5


def test_fetch_all_local_news_aggregates_across_all_feeds():
    with patch("algorithms.local_news.requests.get") as mock_get:
        mock_resp = MagicMock(status_code=200, text=SAMPLE_RSS_WITH_HIT)
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        result = fetch_all_local_news()

    assert result["total_feeds"] == 12
    assert result["active_feeds"] == 12
    assert result["total_kw_hits"] > 0
    # _all_titles는 내부용이라 최종 응답에는 없어야 함
    assert all("_all_titles" not in f for f in result["feeds"])

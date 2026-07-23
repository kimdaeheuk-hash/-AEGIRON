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

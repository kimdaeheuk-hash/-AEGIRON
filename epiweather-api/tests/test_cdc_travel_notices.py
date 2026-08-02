"""CDC 여행 건강경보(신규 각도 탐색, 2026-07-27) — RSS 파싱·레벨 추출·정직성
플래그 확인. 실제 CDC 호출은 mock."""
from __future__ import annotations
from unittest.mock import patch, MagicMock

from algorithms.cdc_travel_notices import (
    fetch_travel_notices, travel_notices_summary, LEVEL_MEANING,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<title>Travel Notices</title>
<item>
  <title>Level 2 - Chikungunya in Costa Rica</title>
  <description><![CDATA[Outbreak of chikungunya.]]></description>
  <link>https://wwwnc.cdc.gov/travel/notices/level2/chikungunya-costa-rica</link>
  <pubDate>Thu, 16 Jul 2026 04:00:00 GMT</pubDate>
</item>
<item>
  <title>Level 3 - Ebola Bundibugyo Virus Disease in Parts of the Democratic Republic of the Congo</title>
  <description><![CDATA[Avoid nonessential travel.]]></description>
  <link>https://wwwnc.cdc.gov/travel/notices/level3/ebola-democratic-republic-of-the-congo</link>
  <pubDate>Wed, 15 Jul 2026 04:00:00 GMT</pubDate>
</item>
<item>
  <title>Level 1 - Global Dengue</title>
  <description><![CDATA[Practice usual precautions.]]></description>
  <link>https://wwwnc.cdc.gov/travel/notices/level1/global-dengue</link>
  <pubDate>Mon, 01 Jun 2026 04:00:00 GMT</pubDate>
</item>
</channel></rss>"""


def _fake_resp(text, status=200):
    m = MagicMock(status_code=status)
    m.content = text.encode("utf-8")
    m.raise_for_status = MagicMock() if status == 200 else MagicMock(side_effect=Exception("http error"))
    return m


def test_fetch_travel_notices_parses_level_and_headline():
    with patch("algorithms.cdc_travel_notices.requests.get", return_value=_fake_resp(SAMPLE_RSS)):
        notices = fetch_travel_notices()
    assert len(notices) == 3
    assert notices[0]["level"] == 2
    assert notices[0]["headline"] == "Chikungunya in Costa Rica"
    assert notices[1]["level"] == 3
    assert "Ebola" in notices[1]["headline"]


def test_fetch_travel_notices_network_error_returns_none():
    with patch("algorithms.cdc_travel_notices.requests.get", side_effect=Exception("blocked")):
        assert fetch_travel_notices() is None


def test_fetch_travel_notices_http_error_returns_none():
    with patch("algorithms.cdc_travel_notices.requests.get", return_value=_fake_resp("", status=500)):
        assert fetch_travel_notices() is None


def test_fetch_travel_notices_malformed_title_falls_back_to_full_title():
    rss = """<?xml version="1.0"?><rss><channel>
    <item><title>Special Event Alert - World Cup</title><description/><link/><pubDate/></item>
    </channel></rss>"""
    with patch("algorithms.cdc_travel_notices.requests.get", return_value=_fake_resp(rss)):
        notices = fetch_travel_notices()
    assert notices[0]["level"] is None
    assert notices[0]["headline"] == "Special Event Alert - World Cup"


def test_travel_notices_summary_counts_by_level():
    with patch("algorithms.cdc_travel_notices.requests.get", return_value=_fake_resp(SAMPLE_RSS)):
        result = travel_notices_summary()

    assert result["data_available"] is True
    assert result["total_notices"] == 3
    assert result["by_level"] == {1: 1, 2: 1, 3: 1, 4: 0}
    assert len(result["high_severity_notices"]) == 1  # level 3만
    assert result["high_severity_notices"][0]["level"] == 3
    assert result["levels_measured"] is True
    assert set(LEVEL_MEANING) == {1, 2, 3, 4}


def test_travel_notices_summary_unavailable_on_failure():
    with patch("algorithms.cdc_travel_notices.requests.get", side_effect=Exception("blocked")):
        result = travel_notices_summary()
    assert result["data_available"] is False
    assert "reason" in result

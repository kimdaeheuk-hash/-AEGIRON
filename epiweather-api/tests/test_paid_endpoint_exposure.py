"""유료 AI를 부르는 공개 엔드포인트가 돈을 새게 두지 않는지 (2026-08-19 전수점검).

전수점검에서 찾은 것: 인증 없는 GET 셋이 요청 한 번마다 유료 API를 호출했고
캐시도 요청제한도 없었다. /openapi.json이 인증 없이 열려 있어 엔드포인트 목록도
공개다. 누구든 반복 호출로 크레딧을 뺄 수 있었다 — 런칭 = 트래픽 = 발견이다.

  /api/global-watch     Perplexity + Tavily + Claude  (홈페이지 안 씀 → 잠금)
  /api/threats/semantic Claude                        (홈페이지 안 씀 → 잠금)
  /api/daily-brief      Claude                        (홈페이지 씀 → 캐시)
"""
from __future__ import annotations
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(isolated_db, monkeypatch):
    monkeypatch.setenv("EPIWEATHER_SCHEDULER", "off")
    monkeypatch.setenv("EPIWEATHER_API_KEY", "test-key-123")
    main._DAILY_BRIEF_CACHE.clear()
    return TestClient(main.app)


@pytest.mark.parametrize("path", ["/api/global-watch", "/api/threats/semantic"])
def test_paid_endpoints_reject_anonymous_callers(client, path):
    """★핵심★ 키 없이 부르면 유료 호출까지 가기 전에 막혀야 한다."""
    resp = client.get(path)
    assert resp.status_code in (401, 403), f"{path}가 아직 열려 있다: {resp.status_code}"


@pytest.mark.parametrize("path", ["/api/global-watch", "/api/threats/semantic"])
def test_paid_endpoints_still_work_with_key(client, path):
    resp = client.get(path, headers={"X-API-Key": "test-key-123"})
    assert resp.status_code == 200


def test_daily_brief_generates_only_once_per_day_lang_format(client):
    """★핵심★ 100번 불러도 Claude는 한 번만 — 방문자 수만큼 돈이 나가면 안 된다."""
    calls = []

    def fake_generate(lang="ko", api_key=None, fmt=None, **kw):
        calls.append((lang, fmt))
        return {"date": "2026-08-19", "lang": lang, "headline": "테스트"}

    with patch("algorithms.daily_brief.generate_daily_brief", side_effect=fake_generate):
        for _ in range(100):
            assert client.get("/api/daily-brief?lang=ko").status_code == 200

    assert len(calls) == 1, f"{len(calls)}번 생성됨 — 캐시가 안 먹었다"


def test_daily_brief_cache_separates_lang_and_format(client):
    """포맷을 바꿔 부르면 캐시를 우회하니, 조합별로 각각 캐시돼야 한다."""
    calls = []

    def fake_generate(lang="ko", api_key=None, fmt=None, **kw):
        calls.append((lang, fmt))
        return {"lang": lang, "fmt": fmt}

    with patch("algorithms.daily_brief.generate_daily_brief", side_effect=fake_generate):
        for _ in range(3):
            client.get("/api/daily-brief?lang=ko")
            client.get("/api/daily-brief?lang=en")
            client.get("/api/daily-brief?lang=ko&format=duo")

    assert len(calls) == 3                      # 조합 3개, 9번 요청했지만 생성은 3번
    assert set(calls) == {("ko", None), ("en", None), ("ko", "duo")}


def test_daily_brief_cache_drops_yesterday(client):
    """날짜가 바뀌면 어제 것은 버린다 — 캐시가 무한히 커지면 안 된다."""
    main._DAILY_BRIEF_CACHE[("2026-01-01", "ko", "auto")] = {"old": True}

    with patch("algorithms.daily_brief.generate_daily_brief",
               return_value={"headline": "오늘"}):
        client.get("/api/daily-brief?lang=ko")

    assert ("2026-01-01", "ko", "auto") not in main._DAILY_BRIEF_CACHE

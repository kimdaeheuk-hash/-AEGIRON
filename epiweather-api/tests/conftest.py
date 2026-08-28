"""pytest 설정 — main.py와 동일하게 epiweather-api 루트를 sys.path에 올려서
`import db`, `from algorithms.xxx import yyy` 스타일 임포트가 테스트에서도 되게 함.

## ★ 테스트는 바깥 인터넷에 나가지 않는다 (2026-08-28) ★

CI 가 **42분** 걸리는데 로컬은 3분이었다. 원인을 계측해보니:

    36개 테스트가 실제 외부 API 를 **814번** 호출
      → api.open-meteo.com · news.google.com · comtradeapi.un.org
    814회 × CI 평균 ~3초 ≈ 2,400초 ≈ 40분   (실측 CI pytest 단계: 2,523초)

UN comtrade 는 이 리포 절차 문서에도 "UN 에 18번 호출해서 처음엔 최대 90초" 라고
적혀 있는 느린 API 다. 그걸 테스트가 매번 진짜로 부르고 있었다.

**막아도 안전하다는 근거**: 개발 샌드박스는 외부 접속이 차단돼 이 호출이 전부
실패하는데 **954개가 전부 통과한다.** 즉 코드가 이미 네트워크 없이도 동작하도록
방어돼 있고, 테스트도 그 경로에서 통과한다. 아래 픽스처는 그 조건을 CI 에서도
**결정적으로** 만들 뿐이다.

부수 효과가 더 크다 — 남의 API 가 죽으면 우리 CI 가 빨개지던 것이 사라지고,
매 푸시마다 UN·오픈메테오에 수백 번씩 하던 호출도 사라진다.

바깥으로 나가야 하는 테스트가 생기면 `@pytest.mark.allow_network` 를 붙여라.
지금은 하나도 없다.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import requests  # noqa: E402
import db as dbmod  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allow_network: 이 테스트만 실제 외부 HTTP 를 허용한다(기본은 차단).",
    )


@pytest.fixture(autouse=True)
def _no_outbound_http(request, monkeypatch):
    """모킹되지 않은 실제 HTTP 호출을 차단한다.

    `requests.Session.send` 를 막는다 — 여기가 마지막 관문이라서, 테스트가
    `module.requests.get` 을 patch 해뒀으면 그쪽이 먼저 걸려 **영향이 없다.**
    즉 이 픽스처에 걸리는 건 **모킹을 빠뜨린 호출뿐**이다.

    차단은 `ConnectionError` 로 한다 — 호출부가 이미 그 경우를 다루고 있고
    (샌드박스에서 954개 통과가 그 증거), 새로운 예외 종류를 만들면 오히려
    `except requests.RequestException` 같은 기존 방어를 빠져나간다.
    """
    if request.node.get_closest_marker("allow_network"):
        return

    def _blocked(self, req, **kw):
        raise requests.exceptions.ConnectionError(
            f"테스트에서 실제 HTTP 를 막았다: {req.method} {req.url}\n"
            "  → 이 호출을 mock 하거나, 정말 필요하면 @pytest.mark.allow_network 를 붙여라.\n"
            "  (이유: tests/conftest.py 의 '테스트는 바깥 인터넷에 나가지 않는다')"
        )

    monkeypatch.setattr(requests.Session, "send", _blocked)


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """테스트마다 독립된 임시 SQLite를 쓰게 해서 실제 운영 DB를 건드리지 않음."""
    monkeypatch.setattr(dbmod, "DB_PATH", tmp_path / "test_epiweather.db")
    dbmod.init_db()
    yield dbmod

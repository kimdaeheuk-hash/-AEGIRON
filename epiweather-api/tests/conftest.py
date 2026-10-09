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


@pytest.fixture(autouse=True)
def _isolated_quality_state(tmp_path, monkeypatch):
    """품질 헬스 상태 파일을 테스트마다 격리한다 (2026-08-30).

    collector 를 돌리는 테스트(`test_health_summary_log.py`)가 `record_cycle` 을
    호출하면서 **실제 `data/quality_health.json` 에 썼다.** `data/` 가 gitignore
    라 커밋되지는 않지만, 남은 연속 위반 카운터가 다음 테스트의 `quality_report()`
    에 그대로 보여 **순서 의존**이 생긴다. 지금은 우연히 안 깨질 뿐이다.

    이 층은 "연속 몇 주기"를 파일에 누적하는 게 핵심이라 오염에 특히 취약하다 —
    그래서 옵트인이 아니라 autouse 로 막는다.
    """
    try:
        from algorithms import quality_health
    except Exception:
        return
    monkeypatch.setattr(
        quality_health, "QUALITY_FILE", tmp_path / "quality_health.json"
    )


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """테스트마다 독립된 임시 SQLite를 쓰게 해서 실제 운영 DB를 건드리지 않음."""
    monkeypatch.setattr(dbmod, "DB_PATH", tmp_path / "test_epiweather.db")
    dbmod.init_db()
    yield dbmod


# ── 능력 장부는 테스트가 절대 운영 파일에 쓰지 않는다 (2026-09-04) ──────
# capability_ledger 는 data/capability_health.json 에 "이 능력이 실제로 돌았다"를
# 남긴다. 그런데 계측 지점이 실제 호출 경로(nim_raw·텔레그램 전송)에 붙어 있어서,
# 그 경로를 지나는 테스트가 **운영 장부에 가짜 성공을 적었다.** 실측: 전체 스위트를
# 한 번 돌리면 nvidia_text 가 성공 12·실패 3, 엔드포인트 nim.internal.aegiron.gov
# 로 기록됐다 — 온프렘에 붙은 적도 없는데 주권 검증이 참으로 보일 수 있는 상태다.
#
# 이 장부의 존재 이유가 "설정이 아니라 관측으로 말하기" 인데 그 관측이 테스트로
# 오염되면 모듈 전체가 무의미해진다. 그래서 전역으로, 테스트마다 임시 파일에 쓴다.
@pytest.fixture(autouse=True)
def _isolate_capability_ledger(tmp_path, monkeypatch):
    from algorithms import capability_ledger
    monkeypatch.setattr(capability_ledger, "LEDGER_FILE",
                        tmp_path / "capability_health.json")
    yield


# 무역 스캔은 요청 사이에 간격을 두고(REQUEST_GAP_SEC), 429 에는 기다렸다 다시 묻는다. 스캔을
# 모의 요청으로 도는 시험이 그 시간을 **실제로** 기다리면 스위트가 4배 느려진다(실측 38초 →
# 159초). 기다림 자체를 검증하는 시험은 `_sleep` 을 직접 패치해 값을 본다.
@pytest.fixture(autouse=True)
def _no_real_sleep_in_trade_scan(monkeypatch):
    from algorithms import comtrade_signals
    monkeypatch.setattr(comtrade_signals, "_sleep", lambda sec: None)
    yield


# ★ 고위험 병원체 보도 감시(pathogen_sentinel)는 실제 네트워크를 부른다 ★ 경보 후보를 모으는 모든 시험이
# 그 호출을 만나므로, 기본은 '빈 피드'로 막고 캐시를 비운다. 이 층을 시험하는 파일은 `fetch_local_feed` 를
# 직접 패치해 제목을 준다.
@pytest.fixture(autouse=True)
def _no_real_network_in_pathogen_sentinel(monkeypatch):
    from algorithms import pathogen_sentinel
    pathogen_sentinel._CACHE.update(at=0.0, titles=None)
    pathogen_sentinel._FAIL.update(at=0.0, err=None)
    monkeypatch.setattr(pathogen_sentinel, "fetch_local_feed",
                        lambda *a, **k: {"status": "ok", "_all_titles": []})
    yield
    pathogen_sentinel._CACHE.update(at=0.0, titles=None)
    pathogen_sentinel._FAIL.update(at=0.0, err=None)

"""네팔은 '발병 보도가 시작된 뒤'에만 보이는 나라였다 (2026-08-28).

## 계기
캡틴이 네팔 홍수 소식을 물었다. 그래서 이 시스템이 네팔을 어디까지 아는지
층별로 짚어봤더니 이렇게 갈렸다:

| 층 | 상태 |
|---|---|
| 현지어 뉴스 피드 `gn_np` (네팔어) | 있었다 |
| `country_resolve` / `name_i18n` 의 NPL | 있었다 |
| `country_risk.COUNTRIES` (Tier-1) | **없었다** |
| `climate_signals.COUNTRY_COORDS` | **없었다** (14개국뿐) |

즉 네팔은 **누가 네팔 발병 기사를 쓰기 전까지는 위험 랭킹에 등장조차 하지
않는 상태**였다. Tier-2 자동편입 경로가 있긴 하지만 그건 `extracted_signals`
에 NPL 이 떠야 작동한다 — 그러려면 이미 보도가 나와 있어야 한다.

## 그리고 이건 절반짜리 수리다
네팔어 피드가 찾는 건 `महामारी`(전염병)·`रोग`(질병)·`डेंगु`(뎅기) 같은
**질병** 단어다. 홍수 기사는 여기 안 걸린다. 그래서 이 파일이 잠그는 건
"네팔이 지도에 있다" 까지고, "홍수를 보고 발병을 미리 본다" 는 아직 없다.
그 감시창(재난 → 발병 잠복기)은 별도 작업이다.

## 이 파일이 막는 회귀
사람이 손으로 채우는 표가 세 군데(백엔드 국가표·기후 좌표·프론트 좌표)로
흩어져 있다. 하나만 채우고 나머지를 잊으면 아무 에러 없이 조용히 반쪽이
된다 — 오늘 아침부터 계속 나온 그 모양이다.
"""
from __future__ import annotations

from pathlib import Path

from algorithms.climate_signals import COUNTRY_COORDS
from algorithms.country_risk import COUNTRIES
from algorithms.country_resolve import resolve_country
from algorithms import local_news


def test_nepal_is_tier1():
    """★핵심★ 보도가 나기 전에도 네팔이 위험 랭킹에 있어야 한다."""
    assert "NPL" in COUNTRIES, "네팔이 Tier-1 국가표에서 빠졌다"
    assert COUNTRIES["NPL"]["name"] == "네팔"


def test_nepal_border_mobility_is_the_highest():
    """인도-네팔 개방국경이 이 표에서 가장 높은 값인 건 의도한 것이다.

    실수로 넣은 값처럼 보여 누가 '평범하게' 낮추는 걸 막는다. 이 필드는
    country_indicators 로 갱신되지 않아 여기 적은 값이 그대로 계산에 쓰인다.
    """
    top = max(COUNTRIES.values(), key=lambda c: c["border_mobility"])
    assert top["name"] == "네팔"
    assert COUNTRIES["NPL"]["border_mobility"] >= COUNTRIES["SAU"]["border_mobility"]


def test_every_tier1_country_has_climate_coords():
    """백엔드 국가표와 기후 좌표가 어긋나면 그 나라 기후 신호가 조용히 빈다."""
    missing = [c for c in COUNTRIES if c not in COUNTRY_COORDS]
    assert not missing, f"기후 좌표 누락: {missing}"


def test_frontend_coords_match_backend_countries():
    """프론트 countryCoords.ts 는 손으로 따로 채운다 — 잊으면 지도에서만 사라진다.

    타입스크립트를 파싱하지 않고 ISO3 키가 글자로 있는지만 본다. 정교하진
    않지만 '추가하고 프론트를 잊었다' 는 실제 실수를 정확히 잡는다.
    """
    ts = Path(__file__).resolve().parents[2] / "epiweather-web/src/lib/countryCoords.ts"
    if not ts.exists():          # 백엔드만 체크아웃한 환경
        return
    text = ts.read_text(encoding="utf-8")
    missing = [c for c in COUNTRIES if f"{c}:" not in text]
    assert not missing, f"프론트 지도 좌표 누락: {missing}"


def test_nepal_name_resolves():
    assert resolve_country("네팔") == "NPL"
    assert resolve_country("Nepal") == "NPL"


def test_nepali_feed_looks_for_disease_not_disaster():
    """★이 한계를 문서가 아니라 테스트로 못박는다★

    네팔어 피드 키워드는 질병 단어뿐이다. 그러니 홍수 기사는 이 경로로
    절대 안 들어온다. 누가 '네팔은 이제 커버된다'고 믿는 걸 막는다.
    """
    feed = [f for f in local_news.LOCAL_FEEDS if f[0] == "gn_np"]
    assert feed, "네팔어 피드가 사라졌다"
    # 런타임 튜플은 (slug, 언어명, 지역, URL, 키워드) — 소스의 hl/gl 은
    # 모듈 로드 때 URL 로 접혀서 사라진다. 키워드는 항상 마지막이다.
    keywords = feed[0][-1]
    assert "महामारी" in keywords          # 전염병
    assert not any(k in ("बाढी", "flood", "홍수") for k in keywords), (
        "홍수 키워드가 생겼다면 이 테스트의 전제가 바뀐 것이다 — "
        "docs/매일_수집점검_절차.md 의 네팔 항목도 같이 고쳐라"
    )

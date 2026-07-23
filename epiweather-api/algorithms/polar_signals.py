"""극지·영구동토 관찰 층 — 인수인계서 확장(㉞).

사업주 통찰: 북극·남극 온난화로 얼음·동토가 녹으면서 '거기서도 뭔가 나타날
것'. 과학적으로 두 갈래로 실재한다:
  (a) 동토 해빙 → 고대 병원체 노출. 실증 사례: 2016 시베리아 야말 탄저병
      (폭염이 1941년경 감염 순록 사체를 드러냄, 순록 2,300+ 폐사·사망자 발생).
      되살아난 고대 바이러스(Pithovirus 3만년·Pandoravirus 4.8만년)도 확인됨.
  (b) 온난화 → 범위 이동 → 극지 신규 발병. 이미 진행 중: 2023~24 H5N1이
      남극권까지 도달해 스쿠아·물개 집단폐사.

★ 등급 원칙(중요) ★
  이건 '경보(alert)'가 아니라 '관찰(watch)' 층이다 — 저확률·고충격(long-tail).
  대부분의 동토 미생물은 사람을 감염 못 시키고, 이 위험은 토지이용 동인보다
  과대평가되는 경향도 있다. 그래서 watch_grade=True로 분리해, 경보 파이프라인
  (classify_tier)과 절대 섞지 않는다. "봐둬야 할 신호"이지 "울려야 할 경보"가 아님.

데이터: 이미 만든 기후 층(Open-Meteo, 동토 해빙 프록시) + 현지어 뉴스(Google
News, 탄저·순록폐사·permafrost·극지 H5N1 키워드) 재사용. 샌드박스는 외부 API
정책 차단이라 라이브 검증 불가 — mock 단위테스트, Railway에서 실동작.

★ 정직성 ★
  - thaw_days는 '최고기온 0°C 초과일 수'로 해빙 활동 프록시다. 여름엔 많은 게
    정상이라 '기후 정상값 대비 이상'이 아님(단기 온난화 추세와 함께 봐야 함).
  - 값은 발병 위험 측정치가 아니라 관찰용 선행 신호 추정(is_leading_indicator).
"""
from __future__ import annotations
import statistics

from .climate_signals import fetch_climate
from .local_news import fetch_local_feed, _gnews

# (region_key, 이름, lat, lng, 뉴스 hl, 뉴스 gl)
POLAR_REGIONS = [
    ("siberia_yamal", "시베리아 야말(러시아)", 66.5, 68.0, "ru", "RU"),
    ("alaska_north", "알래스카 노스슬로프(미국)", 70.2, -148.5, "en", "US"),
    ("canada_arctic", "캐나다 북극권", 68.5, -133.5, "en", "CA"),
    ("greenland", "그린란드", 72.0, -40.0, "en", "GL"),
    ("svalbard", "스발바르(노르웨이)", 78.2, 15.6, "no", "NO"),
    ("antarctic_peninsula", "남극 반도(H5N1 야생동물)", -63.0, -57.0, "en", "AQ"),
]

# 극지 감시 뉴스 검색어(언어별). 탄저·순록 폐사·영구동토·조류독감.
POLAR_NEWS_TERMS = {
    "ru": ["сибирская язва", "падёж оленей", "вечная мерзлота", "птичий грипп"],
    "en": ["anthrax", "reindeer die-off", "permafrost", "mass die-off", "bird flu"],
    "no": ["miltbrann", "reinsdyr", "permafrost", "fugleinfluensa"],
}
# 언어 불문 앵커(현지어 기사에도 Latin 표기로 자주 등장).
POLAR_ANCHOR_TERMS = ["anthrax", "permafrost", "reindeer", "h5n1", "bird flu",
                      "mass die-off", "seal", "penguin"]

THAW_FULL_DAYS = 30.0
HEAT_TREND_FULL_C = 3.0


def _thaw_pressure(thaw_days_30d: int, heat_trend_c: float) -> float:
    """해빙 활동(0°C 초과일 수)과 단기 온난화 추세를 합친 0~100 관찰 압력.
    기후 정상값 대비 이상이 아니라 '해빙 활동량' 프록시임을 유의."""
    thaw_c = max(0.0, min(thaw_days_30d / THAW_FULL_DAYS, 1.0))
    heat_c = max(0.0, min(heat_trend_c / HEAT_TREND_FULL_C, 1.0))
    return round(100 * (0.6 * thaw_c + 0.4 * heat_c), 1)


def _news_signal(hit_ratio: float | None) -> float | None:
    """뉴스 키워드 히트비율 → 0~100 관찰 신호(coarse). hit_ratio 0.33이면 만점."""
    if hit_ratio is None:
        return None
    return round(min(hit_ratio * 300, 100), 1)


def compute_region(region: tuple) -> dict:
    key, name, lat, lng, hl, gl = region

    # ① 동토 해빙 프록시(기후 층 재사용)
    raw = fetch_climate(lat, lng)
    if raw and len(raw["temps"]) >= 8:
        temps = raw["temps"]
        thaw_days = sum(1 for t in temps[-30:] if t > 0)
        recent, prior = temps[-7:], temps[:-7]
        heat_trend = round(statistics.mean(recent) - statistics.mean(prior), 1) if prior else 0.0
        thaw = {
            "data_available": True,
            "thaw_days_30d": thaw_days,
            "heat_trend_c": heat_trend,
            "permafrost_thaw_pressure": _thaw_pressure(thaw_days, heat_trend),
        }
    else:
        thaw = {"data_available": False}

    # ② 극지 질병 뉴스 관찰(현지어 뉴스 인프라 재사용)
    terms = POLAR_NEWS_TERMS.get(hl, POLAR_NEWS_TERMS["en"])
    url = _gnews(terms, hl, gl)
    keywords = terms + POLAR_ANCHOR_TERMS
    feed = fetch_local_feed(f"{key}_news", "polar", name, url, keywords)
    news = {
        "status": feed.get("status"),
        "keyword_hits": feed.get("keyword_hits"),
        "hit_ratio": feed.get("hit_ratio"),
        "signal": _news_signal(feed.get("hit_ratio")) if feed.get("status") == "ok" else None,
        "sample_titles": feed.get("sample_titles", []),
    }

    # ③ 관찰 점수(가용한 부분들의 평균) — 경보가 아니라 watch 등급
    parts = []
    if thaw.get("data_available"):
        parts.append(thaw["permafrost_thaw_pressure"])
    if news["signal"] is not None:
        parts.append(news["signal"])
    watch_score = round(statistics.mean(parts), 1) if parts else None

    return {
        "region": key,
        "name": name,
        "thaw": thaw,
        "news": news,
        "polar_watch_score": watch_score,
        "watch_grade": True,                 # 경보 아님 — classify_tier와 절대 안 섞음
        "is_leading_indicator": True,
        "low_probability_high_impact": True,
    }


def polar_watch_all() -> dict:
    """전 극지 관찰 지역의 선행 신호. 발병 '앞'을 보는 층의 극지판(㉛기후·㉜㉝토지이용과 짝)."""
    regions = [compute_region(r) for r in POLAR_REGIONS]
    scored = [r for r in regions if r["polar_watch_score"] is not None]
    scored.sort(key=lambda r: -r["polar_watch_score"])
    unscored = [r for r in regions if r["polar_watch_score"] is None]

    return {
        "regions": scored + unscored,
        "grade": "watch",
        "note": "이 층은 저확률·고충격 '관찰(watch)'이지 '경보(alert)'가 아니다 — 경보 파이프라인과 "
                "섞지 않는다. 값은 발병 위험 측정이 아니라 관찰용 선행 신호 추정.",
        "rationale": "동토 해빙→고대 병원체(2016 시베리아 탄저 실증)와 온난화→극지 신규 발병"
                     "(2023~24 H5N1 남극 도달)이라는 두 실재 경로를 관찰한다.",
        "disclaimer": "대부분의 동토 미생물은 사람을 감염 못 시키며, 이 위험은 토지이용 동인보다 "
                      "과대평가 경향도 있음. thaw_days는 기후 정상값 대비 이상이 아니라 해빙 활동 프록시.",
        "data_source": "Open-Meteo(기온) + Google News(극지 질병 뉴스)",
    }

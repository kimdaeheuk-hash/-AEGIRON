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
import hashlib
import statistics

from .climate_signals import fetch_climate
from .polar_baseline import month_baseline
from .polar_trend import month_trend
from .local_news import fetch_local_feed, _gnews, _scoped, MIN_ITEMS_FOR_ALERT

# (region_key, 이름, lat, lng, 뉴스 hl, 뉴스 gl)
# ★ 영토 단위 8곳 (2026-11-02, 6→8) ★ 한 점이 아니라 영토를 본다 — 이름에
# 관할을 붙인다. 아이슬란드는 영어 피드(en/IS)로 둔다: 아이슬란드어 검색어는
# 검증된 번역이 없어 영어 질의+영토 스코프가 정직한 차선이다.
POLAR_REGIONS = [
    ("siberia_yamal", "시베리아 야말(러시아)", 66.5, 68.0, "ru", "RU"),
    ("alaska_north", "알래스카 노스슬로프(미국)", 70.2, -148.5, "en", "US"),
    ("canada_arctic", "캐나다 북극권", 68.5, -133.5, "en", "CA"),
    ("greenland", "그린란드", 72.0, -40.0, "en", "GL"),
    ("svalbard", "스발바르(노르웨이)", 78.2, 15.6, "no", "NO"),
    ("antarctic_peninsula", "남극 반도(H5N1 야생동물)", -63.0, -57.0, "en", "AQ"),
    ("arctic_archipelago", "북극군도(레졸루트, 캐나다)", 74.7, -94.8, "en", "CA"),
    ("iceland", "아이슬란드", 65.0, -19.0, "en", "IS"),
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


def _news_signal(hit_ratio: float | None, item_count: int | None = None) -> float | None:
    """뉴스 키워드 히트비율 → 0~100 관찰 신호(coarse). hit_ratio 0.33이면 만점.

    표본이 `MIN_ITEMS_FOR_ALERT`(20건) 미만이면 None — 5건에 키워드 6종이
    잡혀 ratio 1.2 가 나오는 걸 신호로 읽으면 안 된다(`local_news` 와 같은 규칙).
    `item_count` 를 모르면(구 목·구 피드) 게이트를 못 거니 그대로 계산한다.
    """
    if hit_ratio is None:
        return None
    if item_count is not None and item_count < MIN_ITEMS_FOR_ALERT:
        return None
    return round(min(hit_ratio * 300, 100), 1)


def compute_region(region: tuple) -> dict:
    key, name, lat, lng, hl, gl = region

    # ★ 기준선·추세는 thaw 계산보다 먼저 (2026-11-02) ★ heat_trend 가
    # 기준선 편차를 재사용한다(아래 계절 보정). 자료가 모자라면 각자
    # available=False 로 모른다고 말한다.
    baseline = month_baseline(lat, lng)
    trend = month_trend(lat, lng)

    # ① 동토 해빙 프록시(기후 층 재사용)
    raw = fetch_climate(lat, lng)
    if raw and len(raw["temps"]) >= 8:
        temps = raw["temps"]
        thaw_days = sum(1 for t in temps[-30:] if t > 0)
        # ★ 계절을 빼고 더위를 잰다 (2026-11-02) ★ 예전엔 최근 7일과 그 앞
        # 최대 86일을 견줬는데, 봄·가을에는 계절이 오르는 기울기 자체가
        # '온난화'로 잡혔다. 같은 달 평년 대비 편차(기준선 재사용)는 계절이
        # 맞아서 그 오류가 없다. 기준선이 없으면 예전 방식으로 떨어진다.
        if baseline.get("available") and baseline.get("anomaly_c") is not None:
            heat_trend = baseline["anomaly_c"]
            heat_basis = "baseline_anomaly"
        else:
            recent, prior = temps[-7:], temps[:-7]
            heat_trend = (round(statistics.mean(recent) - statistics.mean(prior), 1)
                          if prior else 0.0)
            heat_basis = "trailing_window"
        thaw = {
            "data_available": True,
            "thaw_days_30d": thaw_days,
            "heat_trend_c": heat_trend,
            "heat_basis": heat_basis,
            "permafrost_thaw_pressure": _thaw_pressure(thaw_days, heat_trend),
        }
    else:
        thaw = {"data_available": False}

    # ② 극지 질병 뉴스 관찰(현지어 뉴스 인프라 재사용)
    terms = POLAR_NEWS_TERMS.get(hl, POLAR_NEWS_TERMS["en"])
    # ★ 스코프를 걸어야 그 영토 신호다 ★ GL/AQ 처럼 뉴스판이 없는 지역은
    # 스코프 없이 물으면 전역 뉴스가 그대로 온다(되돌림). `_scoped` 가
    # POLAR_TERMS의 극지 8종으로 질의에 영토 이름을 덧붙인다.
    url = _scoped(_gnews(terms, hl, gl), f"{key}_news")
    keywords = terms + POLAR_ANCHOR_TERMS
    feed = fetch_local_feed(f"{key}_news", "polar", name, url, keywords)
    item_count = feed.get("item_count")
    gated = (feed.get("hit_ratio") is not None and item_count is not None
             and item_count < MIN_ITEMS_FOR_ALERT)
    news = {
        "status": feed.get("status"),
        "keyword_hits": feed.get("keyword_hits"),
        "hit_ratio": feed.get("hit_ratio"),
        "item_count": item_count,
        "signal": _news_signal(feed.get("hit_ratio"), item_count) if feed.get("status") == "ok" else None,
        "sample_titles": feed.get("sample_titles", []),
        "_titles_hash": _titles_hash(feed.get("_all_titles")),
    }
    if gated:
        news["too_few_items"] = True

    # ③ 관찰 점수(가용한 부분들의 평균) — 경보가 아니라 watch 등급
    parts = []
    if thaw.get("data_available"):
        parts.append(thaw["permafrost_thaw_pressure"])
    if news["signal"] is not None:
        parts.append(news["signal"])
    watch_score = round(statistics.mean(parts), 1) if parts else None

    return {
        # ★ 기준선 (2026-09-01) ★ 절대값만으로는 많은 건지 적은 건지 알 수 없다.
        # "해빙 30일" 이 원래 그런 건지 이례적인 건지가 빠져 있었다.
        # 자료가 모자라면 available=False 로 **모른다고 말한다.**
        # ★ 기준선과 추세는 다른 질문이다 (2026-09-01) ★
        # 기준선: 올해가 평년보다 더웠나 (한 해가 튄 것일 수 있다)
        # 추세  : 몇 년째 어느 방향으로 가고 있나
        # 실측에서 알래스카·캐나다는 평년 대비 +1.9/+1.8℃ 인데 추세는 거의
        # 평평했다 — 기준선만 봤으면 여섯 곳 모두 덥다고 읽었을 것이다.
        "baseline": baseline,
        "trend": trend,
        "region": key,
        "name": name,
        "thaw": thaw,
        "news": news,
        "polar_watch_score": watch_score,
        "watch_grade": True,                 # 경보 아님 — classify_tier와 절대 안 섞음
        "is_leading_indicator": True,
        "low_probability_high_impact": True,
        "yamal_index": yamal_index(thaw, news),
    }


# 야말형 재발 조건 (2016 시베리아 탄저 실증: 폭염 + 해빙 + 순록 폐사 + 보도).
# 각 조건은 기존 조각 재사용(신규 비용 0). 점수는 충족률 — 위험 확률이 아니다.
YAMAL_HEAT_C = 2.0       # 기록적 폭염 프록시(평년 대비 편차)
YAMAL_THAW_DAYS = 20     # 30일 중 해빙일
YAMAL_NEWS_SIGNAL = 50.0  # 뉴스 관찰 신호


def yamal_index(thaw: dict, news: dict) -> dict:
    """야말형 재발 조건 충족도 0~100. 모르는 조건은 분모에서 뺀다."""
    met_state: list[tuple[str, bool]] = []
    unknown: list[str] = []
    if thaw.get("data_available"):
        met_state.append(("heat_anomaly", (thaw.get("heat_trend_c") or 0) >= YAMAL_HEAT_C))
        met_state.append(("thaw_days", (thaw.get("thaw_days_30d") or 0) >= YAMAL_THAW_DAYS))
    else:
        unknown.extend(["heat_anomaly", "thaw_days"])
    signal = news.get("signal")
    if signal is None:
        unknown.append("dieoff_news")
    else:
        met_state.append(("dieoff_news", signal >= YAMAL_NEWS_SIGNAL))
    met = [name for name, ok in met_state if ok]
    known = len(met_state)
    return {
        "score": round(100 * len(met) / known, 1) if known else None,
        "conditions_met": met,
        "conditions_unknown": unknown,
        "thresholds": {"heat_anomaly_c": YAMAL_HEAT_C,
                       "thaw_days_30d": YAMAL_THAW_DAYS,
                       "dieoff_news_signal": YAMAL_NEWS_SIGNAL},
        "basis": "2016 야말 탄저(폭염+해빙+순록폐사) 재발 조건 충족률. 점수는 위험 확률이 아니다.",
    }


def _h5n1_cross(regions: list[dict], aux: dict) -> dict:
    """남극 뉴스 신호 + WOAH H5N1 교차. 둘 다 있으면 주목, 하나면 관찰 유지."""
    ant = next((r for r in regions if r.get("region") == "antarctic_peninsula"), {})
    news_sig = (ant.get("news") or {}).get("signal")
    hits = aux.get("woah_h5n1_hits")
    return {"antarctic_news_signal": news_sig, "woah_h5n1_hits": hits,
            "both_present": news_sig is not None and hits is not None,
            "note": "남극 뉴스 + WOAH H5N1 교차. 둘 다 있으면 주목, 하나면 관찰 유지."}


def _duplicate_groups(regions: list[dict]) -> list[list[str]]:
    """같은 피드를 받은 지역 묶음 — 되돌림 대응. 점수 계산은 안 건드리고 표시만."""
    groups: list[tuple] = []
    for r in regions:
        g = tuple((r.get("news") or {}).get("duplicate_of") or ())
        if g and g not in groups:
            groups.append(g)
    return [list(g) for g in groups]


def _titles_hash(titles: list[str] | None) -> str | None:
    """피드 제목 목록의 지문. 3건 미만(머리글뿐)이면 판정 불가 → None.

    `local_news` 와 같은 방식(머리글 2줄 제외·정렬·md5)이라 되돌림 판정이
    두 층에서 같은 의미를 가진다.
    """
    if not titles or len(titles) < 3:
        return None
    joined = chr(10).join(sorted(titles[2:]))
    return hashlib.md5(joined.encode("utf-8", "ignore")).hexdigest()


def _mark_duplicates(regions: list[dict]) -> None:
    """같은 기사를 받은 지역끼리 `duplicate_of` 를 적는다(제자리 수정).

    스코프를 걸어도 되돌림은 요청마다 흔들린다(`local_news` 2026-08-31 실측).
    겹친 지역의 신호는 그 영토 신호가 아닐 수 있으니, 점수에 쓰기 전에
    읽는 쪽이 알 수 있게 표시한다. `_titles_hash` 는 내부용이라 여기서 뺀다.
    """
    by_hash: dict[str, list[str]] = {}
    for r in regions:
        h = (r.get("news") or {}).get("_titles_hash")
        if h:
            by_hash.setdefault(h, []).append(r["region"])
    duplicated = {key for g in by_hash.values() if len(g) > 1 for key in g}
    for r in regions:
        news = r.get("news") or {}
        news.pop("_titles_hash", None)
        if r["region"] in duplicated:
            news["duplicate_of"] = sorted(
                next(g for g in by_hash.values()
                     if len(g) > 1 and r["region"] in g))


def _h5n1_aux() -> dict:
    """동물 채널 H5N1 보조 신호. 남극 뉴스 피드가 죽어도 이쪽은 산다.

    같은 패키지 재사용이라 지연 임포트 — 순환 참조 방지 + 실패해도 극지
    전체가 죽지 않는다(보조는 보조다). 못 읽으면 hits None + 사유.
    """
    try:
        from .wahis import fetch_woah_h5n1
        hits, reason = fetch_woah_h5n1()
    except Exception as exc:                               # noqa: BLE001
        return {"woah_h5n1_hits": None, "reason": type(exc).__name__}
    return {"woah_h5n1_hits": hits,
            **({"reason": reason} if reason else {})}


def polar_watch_all() -> dict:
    """전 극지 관찰 지역의 선행 신호. 발병 '앞'을 보는 층의 극지판(㉛기후·㉜㉝토지이용과 짝)."""
    regions = [compute_region(r) for r in POLAR_REGIONS]
    _mark_duplicates(regions)
    scored = [r for r in regions if r["polar_watch_score"] is not None]
    scored.sort(key=lambda r: -r["polar_watch_score"])
    unscored = [r for r in regions if r["polar_watch_score"] is None]

    return {
        "regions": scored + unscored,
        "h5n1_aux": (_h5n1 := _h5n1_aux()),
        "grade": "watch",
        "note": "이 층은 저확률·고충격 '관찰(watch)'이지 '경보(alert)'가 아니다 — 경보 파이프라인과 "
                "섞지 않는다. 값은 발병 위험 측정이 아니라 관찰용 선행 신호 추정.",
        "rationale": "동토 해빙→고대 병원체(2016 시베리아 탄저 실증)와 온난화→극지 신규 발병"
                     "(2023~24 H5N1 남극 도달)이라는 두 실재 경로를 관찰한다.",
        "disclaimer": "대부분의 동토 미생물은 사람을 감염 못 시키며, 이 위험은 토지이용 동인보다 "
                      "과대평가 경향도 있음. 해빙일 수는 기후 정상값 대비 이상이 아니라 해빙 활동 프록시.",
        "h5n1_cross": _h5n1_cross(scored + unscored, _h5n1),
        "duplicate_groups": _duplicate_groups(scored + unscored),
        "data_source": "Open-Meteo(기온) + Google News(극지 질병 뉴스)",
    }

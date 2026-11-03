"""원격·의료취약지(오지) 관찰 층 — watch 등급 (2026-11-03).

## 왜 만들었나

언론 기반 감시(local_news)는 언론 없는 곳을 정의상 못 본다. 오지는
"처음부터 없던 보고"라 negative_space(있던 보고가 끊김)와도 다르다.
그래서 영토 레지스트리 + 프록시 융합(기후·뉴스) + 희소성 가드로 본다.

★ 정직성 ★
- 프록시는 프록시다. 기후 이상·뉴스 언급이 질병 신호가 아니다.
- 표본이 모자라면 판정 불가(undetermined) — 조용함을 안전으로 읽지 않는다.
- 영문 질의 + 영토 스코프(아이슬란드 선례): 검증 안 된 번역 질의보다 정직한 차선.
- 수집기 미편입(온디맨드) — 주기 비용 확정 전이라 엔드포인트 호출 시에만 계산.
"""
from __future__ import annotations

import concurrent.futures
import statistics

from .climate_signals import fetch_climate
from .local_news import MIN_ITEMS_FOR_ALERT, _gnews, _scoped, fetch_local_feed

# (key, 이름, iso3, lat, lng, gl) — 좌표는 대표 도시. 의료접근·통신 실측은
# 미연결이라 등급을 매기지 않는다(숫자 날조 금지).
REMOTE_TERRITORIES = [
    ("drc_east", "콩고민주공화국 동부(고마)", "COD", -1.68, 29.22, "CD"),
    ("south_sudan", "남수단(주바)", "SSD", 4.85, 31.58, "SS"),
    ("yemen", "예멘(사나)", "YEM", 15.35, 44.21, "YE"),
    ("car", "중앙아프리카공화국(방기)", "CAF", 4.39, 18.55, "CF"),
    ("somalia", "소말리아(모가디슈)", "SOM", 2.04, 45.34, "SO"),
    ("afghanistan", "아프가니스탄(카불)", "AFG", 34.53, 69.17, "AF"),
]

REMOTE_NEWS_TERMS = [
    "cholera", "measles", "ebola", "malaria", "outbreak",
    "die-off", "famine", "displaced", "epidemic",
]

MAX_WORKERS = 3
MIN_PROXY_COUNT = 2  # 이 개수 미만이면 판정 불가(희소성 가드)


def _climate_proxy(lat: float, lng: float) -> dict:
    """기온 이상 프록시 — 질병 신호가 아니라 환경 맥락."""
    try:
        raw = fetch_climate(lat, lng)
    except Exception:                                # noqa: BLE001
        return {"available": False, "reason": "기후 조회 실패"}
    if not raw or len(raw.get("temps", [])) < 8:
        return {"available": False, "reason": "기후 자료 부족"}
    temps = raw["temps"]
    recent, prior = temps[-7:], temps[:-7]
    anomaly = (round(statistics.mean(recent) - statistics.mean(prior), 1)
               if prior else 0.0)
    return {"available": True, "heat_anomaly_c": anomaly,
            "basis": "최근 7일 vs 직전 구간 평균 기온차"}


def _news_proxy(key: str, name: str, gl: str) -> dict:
    """질병·인도주의 뉴스 언급 — 보도량 신호지 발병 측정이 아니다."""
    try:
        url = _scoped(_gnews(REMOTE_NEWS_TERMS, "en", gl), f"{key}_remote")
        feed = fetch_local_feed(f"{key}_remote", "remote", name, url,
                                REMOTE_NEWS_TERMS)
    except Exception:                                # noqa: BLE001
        return {"available": False, "reason": "뉴스 조회 실패"}
    if feed.get("status") != "ok":
        return {"available": False, "reason": feed.get("status")}
    count = feed.get("item_count")
    if count is not None and count < MIN_ITEMS_FOR_ALERT:
        return {"available": False, "reason": f"표본 부족({count}건)",
                "undetermined": True}
    return {"available": True, "hit_ratio": feed.get("hit_ratio"),
            "item_count": count, "keyword_hits": feed.get("keyword_hits"),
            "sample_titles": feed.get("sample_titles", [])}


def assess_territory(key: str) -> dict:
    """영토 1곳 평가. 모르면 모른다고 말한다."""
    reg = next((r for r in REMOTE_TERRITORIES if r[0] == key), None)
    if reg is None:
        return {"key": key, "assessed": False, "reason": "미등록 영토"}
    _, name, iso3, lat, lng, gl = reg
    climate = _climate_proxy(lat, lng)
    news = _news_proxy(key, name, gl)
    proxies = {"climate": climate, "news": news}
    alive = sum(1 for p in proxies.values() if p.get("available"))
    if alive < MIN_PROXY_COUNT:
        return {"key": key, "name": name, "iso3": iso3, "assessed": False,
                "verdict": "undetermined", "proxies": proxies,
                "reason": f"가용 프록시 {alive}/{len(proxies)} — 판정 불가",
                "watch_grade": True}
    return {"key": key, "name": name, "iso3": iso3, "assessed": True,
            "verdict": "observed", "proxies": proxies,
            "note": "프록시 융합 관찰 — 발병 측정이 아님", "watch_grade": True}


def assess_all() -> list[dict]:
    """전 영토 병렬 평가(3워커). 하나가 느려도 나머지는 돈다."""
    keys = [r[0] for r in REMOTE_TERRITORIES]
    out: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(assess_territory, k): k for k in keys}
        for fut in concurrent.futures.as_completed(futs):
            try:
                out[futs[fut]] = fut.result()
            except Exception as exc:                 # noqa: BLE001
                k = futs[fut]
                out[k] = {"key": k, "assessed": False,
                          "reason": f"{type(exc).__name__}: {exc}"[:120]}
    return [out[k] for k in keys]

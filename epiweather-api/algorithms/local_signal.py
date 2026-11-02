"""Stage 1: 발원지 현지어 신호 — Wikipedia 다국어 조회량으로 실제 현지 관심도 측정.

문제: 한국 공개 API(네이버 등)는 한국 국내 신호만 본다 — 자카르타·우한 등
발원지 도시 "내부"에서 무슨 일이 일어나는지는 한국 데이터로 알 수 없음.
해결: Wikipedia는 언어별 조회량을 공개하므로, 발원지의 현지어 위키피디아에서
감염병 관련 문서 조회량이 평소보다 튀었는지(이상치) 보면 현지 관심도의
실제 대리 신호(proxy)가 된다. 키 불필요, 전 세계 공통.

출처: 기존 인수인계 자료(epiweather_master_connector.py)의 다국어 매핑을 재사용.
"""
from __future__ import annotations
import datetime as dt
import requests

UA = {"User-Agent": "EpiWeather-LocalSignal/1.0 (epidemic early warning)"}

# 기준 14일 조회수가 이 미만이면 비율을 내지 않는다. 3건→9건도 ratio 3.0
# ("급증")이 되는데, 그건 신호가 아니라 표본 부족이다. '모른다'와 '정상'은
# 다르므로(`local_news.MIN_ITEMS_FOR_ALERT` 와 같은 규칙) 판정 불가로 둔다.
MIN_BASELINE_VIEWS = 50

# 발원지 도시(common.py CITIES) → 현지어 위키피디아 + 감염병 관련 문서 제목
# ★ 새 도시 추가 규칙 ★ 문서 제목은 반드시 실존 확인 후 넣는다 —
# `https://{lang}.wikipedia.org/wiki/{제목}` 이 200 이어야 한다. 없는 제목은
# API 가 빈 items 를 돌려줘 '관심 없음'처럼 보이는데, 그건 측정이 아니라 오보다.
# 극지 도시(무르만스크·레이캬비크·트롬쇠 등)는 이 확인이 안 돼서 안 넣었다 —
# 확인되는 대로 추가한다.
CITY_WIKI = {
    "WUH": ("zh", ["流行性感冒", "传染病"]),          # 우한 → 중국어
    "JKT": ("id", ["Demam berdarah dengue", "Flu"]),  # 자카르타 → 인도네시아어
    "BKK": ("th", ["ไข้เลือดออก", "ไข้หวัดใหญ่"]),     # 방콕 → 태국어
    "HAN": ("vi", ["Sốt xuất huyết", "Cúm"]),         # 하노이 → 베트남어
    "DAC": ("bn", ["ডেঙ্গু জ্বর", "ম্যালেরিয়া"]),       # 다카 → 벵갈리어
    "FIH": ("fr", ["Maladie à virus Ebola", "Choléra"]),  # 킨샤사 → 프랑스어
    "LOS": ("ha", ["Cutar Ebola", "Zazzabi"]),        # 라고스 → 하우사어
    "MEX": ("es", ["Gripe", "Dengue"]),               # 멕시코시티 → 스페인어
}

# 일키 캐시 — 8도시 × 2문서 = 16요청을 매시간 반복하지 않는다. 위키 조회량은
# 일 단위 집계라 같은 날 안에서는 다시 받아도 같은 답이다. 프로세스 메모리라
# 재배포되면 다시 받는다(16건, 저렴). 테스트는 직접 비운다.
_SIGNAL_CACHE: dict = {"at": None, "data": None}


def _daily_views(lang: str, title: str, start: dt.date, end: dt.date) -> list[dict]:
    """한 번의 호출로 전체 구간을 가져와 일별 항목을 반환 (요청 수 절약 → 레이트리밋 회피)."""
    enc = requests.utils.quote(title, safe="")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{lang}.wikipedia/all-access/all-agents/{enc}/daily/"
        f"{start.strftime('%Y%m%d00')}/{end.strftime('%Y%m%d00')}"
    )
    r = requests.get(url, headers=UA, timeout=10)
    r.raise_for_status()
    return r.json().get("items", [])


def fetch_local_signal(origin_id: str) -> dict:
    """최근 14일 vs 이전 14일 조회량 비교로 이상치(anomaly) 비율 계산.
    제목당 1회 호출(42일 전체)로 가져와 구간을 나눠 계산 — Wikimedia API 레이트리밋 회피.
    """
    if origin_id not in CITY_WIKI:
        return {"available": False, "reason": f"{origin_id}에 대한 현지어 매핑 없음"}

    lang, titles = CITY_WIKI[origin_id]
    today = dt.date.today()
    # 동일 14일씩 두 구간(최근 vs 그 이전)을 한 번의 호출(28일)로 가져옴
    full_start, full_end = today - dt.timedelta(days=28), today - dt.timedelta(days=1)
    recent_cutoff = (today - dt.timedelta(days=14)).strftime("%Y%m%d")

    results = []
    for title in titles:
        try:
            items = _daily_views(lang, title, full_start, full_end)
            recent = sum(i["views"] for i in items if i["timestamp"][:8] >= recent_cutoff)
            base = sum(i["views"] for i in items if i["timestamp"][:8] < recent_cutoff)
            if base < MIN_BASELINE_VIEWS:
                results.append({"title": title, "recent_14d": recent,
                                "baseline_14d": base, "undetermined": True,
                                "reason": f"표본 부족 — 기준 14일 {base}건 "
                                          f"({MIN_BASELINE_VIEWS}건 미만)"})
                continue
            ratio = recent / base
            results.append({"title": title, "recent_14d": recent, "baseline_14d": base, "ratio": round(min(ratio, 99), 2)})
        except Exception as e:
            results.append({"title": title, "error": str(e)[:100]})

    valid = [r for r in results if "ratio" in r]
    if not valid:
        # 문서 전부 조회 실패(레이트리밋·네트워크 오류)거나 표본 부족이면
        # max_ratio를 1.0으로 기본값 처리하면 "✅ 평소 수준"으로 잘못 보고됨 —
        # 실제로는 데이터를 아예 못 받아온 것이라 "정상"과 구분해야 함.
        undetermined = sum(1 for r in results if r.get("undetermined"))
        return {
            "available": False,
            "lang": lang,
            "titles": results,
            "reason": ("모든 문서 표본 부족 — 기준 14일 조회수 "
                       f"{MIN_BASELINE_VIEWS}건 미만" if undetermined == len(results)
                       else "모든 문서 조회 실패 — 레이트리밋 또는 네트워크 오류"),
            "source": f"{lang}.wikipedia.org 실시간 조회량 (Wikimedia REST API)",
        }

    max_ratio = max(r["ratio"] for r in valid)

    return {
        "available": True,
        "lang": lang,
        "titles": results,
        "max_anomaly_ratio": max_ratio,
        "verdict": (
            "⚠ 평소보다 현지 관심도 급증" if max_ratio > 2.0 else
            "△ 약간 상승" if max_ratio > 1.3 else
            "✅ 평소 수준"
        ),
        "source": f"{lang}.wikipedia.org 실시간 조회량 (Wikimedia REST API)",
    }


def fetch_all_signals(today: dt.date | None = None) -> dict[str, dict]:
    """전 도시 신호. 같은 날 안에서는 캐시를 돌려준다(일키 캐시).

    수집기가 매시간 부른다. 도시는 독립이라 하나가 죽어도 나머지는 산다 —
    `fetch_local_signal` 이 도시 단위로 실패를 안고 오기 때문이다.
    """
    day = (today or dt.date.today()).isoformat()
    if _SIGNAL_CACHE["at"] == day and _SIGNAL_CACHE["data"] is not None:
        return _SIGNAL_CACHE["data"]
    data = {city: fetch_local_signal(city) for city in CITY_WIKI}
    _SIGNAL_CACHE.update(at=day, data=data)
    return data

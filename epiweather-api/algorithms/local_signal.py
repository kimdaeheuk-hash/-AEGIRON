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

# 발원지 도시(common.py CITIES) → 현지어 위키피디아 + 감염병 관련 문서 제목
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
            ratio = recent / base if base > 0 else (float("inf") if recent > 0 else 1.0)
            results.append({"title": title, "recent_14d": recent, "baseline_14d": base, "ratio": round(min(ratio, 99), 2)})
        except Exception as e:
            results.append({"title": title, "error": str(e)[:100]})

    valid = [r for r in results if "ratio" in r]
    max_ratio = max((r["ratio"] for r in valid), default=1.0)

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

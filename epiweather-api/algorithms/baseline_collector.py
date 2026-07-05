"""과거 기준선 데이터 수집 — Phase 2 ⑮.

이상 탐지는 "평소"를 알아야 한다. signals_log.jsonl이 막 쌓이기 시작했을 때는
역사적 기준선이 없어서 z-score 계산이 불안정하다.

이 모듈은:
  - Wikipedia 월별 조회수 최대 24개월치 (무료, 인증 불필요)
  - KDCA 법정감염병 최대 5년치 연간 데이터 (KDCA API 키 필요)
를 data/baseline_signals.jsonl에 저장한다.

signal_metrics.py의 load_records()가 이 파일을 먼저 읽어
GAI 계산에 필요한 역사적 기준선으로 쓴다.
"""
from __future__ import annotations
import json
import datetime as dt
import os
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASELINE_FILE = DATA_DIR / "baseline_signals.jsonl"
USER_AGENT = {"User-Agent": "EpiWeather-Baseline/1.0 (epiweather.kr)"}

WIKI_DISEASES = {
    "Ebola_virus_disease": "wiki_ebola_daily",
    "Influenza": "wiki_flu_daily",
    "Middle_East_respiratory_syndrome": "wiki_mers_daily",
    "Dengue_fever": "wiki_dengue_daily",
    "Cholera": "wiki_cholera_daily",
    "Marburg_virus_disease": "wiki_marburg_daily",
}


def fetch_wiki_monthly(article: str, months_back: int = 24) -> list[dict]:
    """Wikipedia 월별 조회수 최대 months_back개월 반환."""
    today = dt.date.today()
    end_dt   = today.replace(day=1) - dt.timedelta(days=1)
    start_dt = (end_dt.replace(day=1) - dt.timedelta(days=30 * months_back)).replace(day=1)
    start_str = start_dt.strftime("%Y%m%d")
    end_str   = end_dt.strftime("%Y%m%d")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{article}/monthly/{start_str}/{end_str}"
    )
    try:
        r = requests.get(url, headers=USER_AGENT, timeout=15)
        if r.status_code != 200:
            return []
        return r.json().get("items", [])
    except Exception:
        return []


def fetch_kdca_historical(api_key: str, years_back: int = 5) -> list[dict]:
    """KDCA 법정감염병 과거 N년치 연간 신고건수."""
    current_year = dt.date.today().year
    results = []
    for year in range(current_year - years_back, current_year):
        try:
            r = requests.get(
                "https://apis.data.go.kr/1790387/EIDAPIService/PeriodBasic",
                params={
                    "serviceKey": api_key, "resType": 2, "searchPeriodType": 1,
                    "searchStartYear": year, "searchEndYear": year,
                    "pageNo": 1, "numOfRows": 2000,
                },
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()["response"]["body"]
            items = body.get("items") or {}
            item_list = items.get("item") or []
            if isinstance(item_list, dict):
                item_list = [item_list]
        except Exception:
            continue
        for it in item_list:
            # 신규 추가 질병(예: 니파바이러스감염증)은 과거 연도에 아직 감시 대상이
            # 아니었으면 resultVal이 숫자가 아니라 "-"로 옴. int() 변환이 여기서
            # 터지면 그 뒤에 오는 나머지 질병(홍역·콜레라 등 실제 감시 대상 포함)까지
            # 해당 연도 전체가 통째로 유실돼 기준선(baseline)이 왜곡됨 — 항목별로
            # 개별 처리해 문제 있는 항목만 0으로 두고 나머지는 살린다.
            try:
                count = int(it.get("resultVal", 0))
            except (TypeError, ValueError):
                count = 0
            results.append({"year": year, "disease": it.get("icdNm"), "count": count})
    return results


def build_wiki_records(months_back: int = 24) -> list[dict]:
    """Wikipedia 히스토리를 signals_log 포맷 레코드로 변환."""
    records = []
    for article, metric_key in WIKI_DISEASES.items():
        items = fetch_wiki_monthly(article, months_back)
        for item in items:
            ts = item.get("timestamp", "")
            if len(ts) >= 8:
                date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
            else:
                continue
            avg_daily = round(item.get("views", 0) / 30, 1)
            records.append({
                "type": "free_sources",
                "_baseline": True,
                "_source": "wikipedia_monthly",
                "_logged_at": f"{date_str}T00:00:00",
                metric_key: avg_daily,
            })
    return records


def build_kdca_records(api_key: str, years_back: int = 5) -> list[dict]:
    """KDCA 히스토리를 signals_log 포맷 레코드로 변환."""
    rows = fetch_kdca_historical(api_key, years_back)
    by_year: dict[int, dict] = {}
    for row in rows:
        year = row["year"]
        disease = row["disease"]
        count = row["count"]
        by_year.setdefault(year, {}).setdefault(disease, {})
        by_year[year][disease][f"{year}년 연간"] = count

    records = []
    for year, kdca_map in sorted(by_year.items()):
        records.append({
            "type": "free_sources",
            "_baseline": True,
            "_source": "kdca_annual",
            "_logged_at": f"{year}-12-31T23:59:59",
            "kdca_weekly": kdca_map,
        })
    return records


def collect_baseline(months_back: int = 24, years_back: int = 5) -> dict:
    """
    Wikipedia + KDCA 기준선을 수집해 baseline_signals.jsonl에 저장.
    이미 저장된 파일이 있어도 덮어쓴다 (최신화).
    """
    DATA_DIR.mkdir(exist_ok=True)
    api_key = os.environ.get("KDCA_API_KEY")

    records = build_wiki_records(months_back)
    wiki_count = len(records)

    kdca_count = 0
    if api_key:
        kdca_records = build_kdca_records(api_key, years_back)
        records.extend(kdca_records)
        kdca_count = len(kdca_records)

    records.sort(key=lambda r: r.get("_logged_at", ""))

    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "baseline_file": str(BASELINE_FILE),
        "total_records": len(records),
        "wiki_records": wiki_count,
        "kdca_records": kdca_count,
        "kdca_skipped": kdca_count == 0 and api_key is None,
    }


def load_baseline_records() -> list[dict]:
    """저장된 기준선 레코드를 반환. 파일 없으면 빈 리스트."""
    if not BASELINE_FILE.exists():
        return []
    records = []
    with open(BASELINE_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records

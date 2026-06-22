"""역병예보 · 무인 신호 수집기 (스케줄러 전용)
==========================================
Windows 작업 스케줄러 등에서 무인 실행되는 스크립트. input() 없음 — 끝까지 실행 후 자동 종료.

실행 모드:
  python collector.py free   → 무료 소스만 (KDCA·네이버·WHO AFRO·Wikipedia·PubMed)
  python collector.py ai     → AI 갭필링 (Perplexity·Tavily·Claude, 비용 발생)
  python collector.py full   → 전부 다 (하루 1회 권장)

로그: data/signals_log.jsonl 에 한 줄씩 누적 저장 → /api/signals 에서 조회 가능.
키는 환경변수로만 주입 (.env 또는 시스템 환경변수). 하드코딩된 키 없음.
"""
from __future__ import annotations
import sys, os, json, time
import datetime as dt
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import requests

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
LOG_FILE = DATA_DIR / "signals_log.jsonl"
ERR_FILE = DATA_DIR / "error_log.txt"
USER_AGENT = {"User-Agent": "EpiWeather-Collector/1.0 (epiweather.kr)"}


def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}")


def log_error(context: str, e: Exception) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(ERR_FILE, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().isoformat()} | {context} | {str(e)[:200]}\n")


def append_signal(record: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    record["_logged_at"] = dt.datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# KDCA EIDAPIService(법정감염병 전수감시)는 일반 계절 인플루엔자(ILI 표본감시)는
# 포함하지 않는다 — 그건 별도 상품/키 승인이 필요함 (확인됨, 2026-06-22).
# 대신 이 API가 실제로 제공하는 제1·2급 법정감염병 중 조기경보 관심 질병만 추적.
KDCA_WATCH_DISEASES = [
    "중동호흡기증후군(MERS)", "중증급성호흡기증후군(SARS)", "에볼라바이러스병",
    "마버그열", "신종인플루엔자", "신종감염병증후군", "콜레라", "홍역", "페스트",
]


def fetch_kdca_weekly(api_key: str, weeks_back: int = 4) -> dict[str, dict[str, int]]:
    """관심 법정감염병의 최근 N주 주간 신고 건수. searchPeriodType=3(주간) 사용."""
    year = dt.date.today().year
    r = requests.get(
        "https://apis.data.go.kr/1790387/EIDAPIService/PeriodBasic",
        params={
            "serviceKey": api_key, "resType": 2, "searchPeriodType": 3,
            "searchStartYear": year, "searchEndYear": year,
            "pageNo": 1, "numOfRows": 2000,
        },
        timeout=15,
    )
    r.raise_for_status()
    items = r.json()["response"]["body"]["items"]["item"]

    cur_week = dt.date.today().isocalendar()[1]
    recent_weeks = {f"{year}년 {w:02d}주" for w in range(max(1, cur_week - weeks_back + 1), cur_week + 1)}

    out: dict[str, dict[str, int]] = {}
    for it in items:
        name = it["icdNm"]
        if name not in KDCA_WATCH_DISEASES or it["period"] not in recent_weeks:
            continue
        out.setdefault(name, {})[it["period"]] = int(it["resultVal"])
    return out


# ══════════════════════════════════════════════
# 무료 소스 수집 (매시간 실행 권장)
# ══════════════════════════════════════════════
def collect_free_sources() -> dict:
    log("=== 무료 소스 수집 시작 ===")
    result = {"type": "free_sources", "timestamp": dt.datetime.now().isoformat()}

    kdca_key = os.environ.get("KDCA_API_KEY")
    if kdca_key:
        try:
            result["kdca_weekly"] = fetch_kdca_weekly(kdca_key)
            total = sum(sum(weeks.values()) for weeks in result["kdca_weekly"].values())
            log(f"  KDCA(주간, 관심질병 {len(result['kdca_weekly'])}종): 최근 4주 합계 {total}건")
        except Exception as e:
            result["kdca_weekly"] = None
            log_error("KDCA", e)
    else:
        result["kdca_weekly"] = None
        log("  ⏭ KDCA_API_KEY 없음 — 건너뜀")

    naver_id = os.environ.get("NAVER_CLIENT_ID")
    naver_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if naver_id and naver_secret:
        try:
            r = requests.post(
                "https://openapi.naver.com/v1/datalab/search",
                json={
                    "startDate": (dt.date.today() - dt.timedelta(days=90)).strftime("%Y-%m-%d"),
                    "endDate": dt.date.today().strftime("%Y-%m-%d"),
                    "timeUnit": "week",
                    "keywordGroups": [
                        {"groupName": "독감", "keywords": ["독감", "인플루엔자", "해열제"]},
                        {"groupName": "에볼라", "keywords": ["에볼라", "바이러스감염"]},
                    ],
                },
                headers={
                    "X-Naver-Client-Id": naver_id,
                    "X-Naver-Client-Secret": naver_secret,
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            r.raise_for_status()
            groups = r.json().get("results", [])
            result["naver_flu_ratio"] = groups[0]["data"][-1]["ratio"] if groups else None
            result["naver_ebola_ratio"] = groups[1]["data"][-1]["ratio"] if len(groups) > 1 else None
            log(f"  네이버: 독감비율={result.get('naver_flu_ratio')} 에볼라비율={result.get('naver_ebola_ratio')}")
        except Exception as e:
            result["naver_flu_ratio"] = None
            log_error("Naver", e)
    else:
        result["naver_flu_ratio"] = None
        log("  ⏭ NAVER_CLIENT_ID/SECRET 없음 — 건너뜀")

    try:
        r = requests.get("https://www.afro.who.int/rss.xml", headers=USER_AGENT, timeout=15)
        r.raise_for_status()
        result["who_afro_items"] = r.text.count("<item>")
        log(f"  WHO AFRO: {result['who_afro_items']}건")
    except Exception as e:
        result["who_afro_items"] = None
        log_error("WHO_AFRO", e)

    try:
        end_s = dt.date.today().strftime("%Y%m%d00")
        start_s = (dt.date.today() - dt.timedelta(days=1)).strftime("%Y%m%d00")
        r = requests.get(
            "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"en.wikipedia/all-access/all-agents/2026_Central_Africa_Ebola_epidemic/daily/{start_s}/{end_s}",
            headers=USER_AGENT, timeout=15,
        )
        if r.status_code == 404:
            # 위키미디어 페이지뷰 집계는 보통 전날치가 다음날 정오 전후까지 늦게
            # 올라옴 — 그 전까지의 404는 정상적인 지연이라 에러로 기록하지 않음.
            result["wiki_ebola_daily"] = None
            log("  Wikipedia 에볼라: 아직 집계 안 됨 (정상 지연, 404)")
        else:
            r.raise_for_status()
            result["wiki_ebola_daily"] = sum(i["views"] for i in r.json().get("items", []))
            log(f"  Wikipedia 에볼라: {result['wiki_ebola_daily']}회/일")
    except Exception as e:
        result["wiki_ebola_daily"] = None
        log_error("Wikipedia_Ebola", e)

    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": "ebola 2026", "retmax": 1, "retmode": "json"},
            headers=USER_AGENT, timeout=15,
        )
        r.raise_for_status()
        result["pubmed_ebola_count"] = int(r.json()["esearchresult"]["count"])
        log(f"  PubMed 에볼라: {result['pubmed_ebola_count']}건")
    except Exception as e:
        result["pubmed_ebola_count"] = None
        log_error("PubMed", e)

    append_signal(result)
    log("=== 무료 소스 수집 완료 ===")
    return result


# ══════════════════════════════════════════════
# AI 갭필링 수집 (하루 2~4회 권장 — 비용 발생)
# ══════════════════════════════════════════════
def collect_ai_sources() -> dict:
    log("=== AI 갭필링 수집 시작 ===")
    from algorithms.global_watch import run_global_watch

    result = {"type": "ai_sources", "timestamp": dt.datetime.now().isoformat()}
    watch = run_global_watch()
    result.update(watch)
    for s in watch["signals"]:
        log(f"  {s['label']}: {(s['text'] or s['error'] or '결과 없음')[:80]}")

    append_signal(result)
    log("=== AI 갭필링 수집 완료 ===")
    return result


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "free"
    log(f"역병예보 자동감시 시작 (모드: {mode})")
    log(f"로그 파일: {LOG_FILE}")

    try:
        if mode == "free":
            collect_free_sources()
        elif mode == "ai":
            collect_ai_sources()
        elif mode == "full":
            collect_free_sources()
            time.sleep(3)
            collect_ai_sources()
        else:
            log(f"알 수 없는 모드: {mode} (free/ai/full 중 선택)")
    except Exception as e:
        log_error("main", e)
        log(f"치명적 오류: {e}")

    log("역병예보 자동감시 종료")


if __name__ == "__main__":
    main()

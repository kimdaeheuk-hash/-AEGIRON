"""역병예보 · 무인 신호 수집기 (스케줄러 전용)
==========================================
Windows 작업 스케줄러 등에서 무인 실행되는 스크립트. input() 없음 — 끝까지 실행 후 자동 종료.

실행 모드:
  python collector.py free   → 무료 소스만 (KDCA·네이버·WHO AFRO·WHO PAHO·CDC NWSS·CDC EID·CIDRAP·Wikipedia·PubMed·Polymarket)
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

# CIDRAP(미네소타대 감염병연구정책센터) — 공중보건 학계에서 WHO·CDC도 참고하는
# 전문가 큐레이션 매체. 질병별 RSS를 직접 운영해서 ProMED 유료화 이후 가장 쓸만한
# "전문가가 먼저 의심한다" 류 신호. 2026-06-24 라이브 확인.
CIDRAP_FEEDS = [
    ("ebola", "에볼라", "https://www.cidrap.umn.edu/news/64/rss"),
    ("mers", "MERS", "https://www.cidrap.umn.edu/news/84/rss"),
    ("avian_flu", "조류인플루엔자", "https://www.cidrap.umn.edu/news/49/rss"),
    ("cholera", "콜레라", "https://www.cidrap.umn.edu/news/58/rss"),
]

# Polymarket 팬데믹 예측시장 — 군중 베팅 가격이 곧 확률 추정치라 LLM 합성 없이
# 그대로 신호로 씀. slug는 폴리마켓 이벤트 URL의 마지막 경로.
POLYMARKET_WATCHLIST = [
    ("new-pandemic-in-2026", "신규 팬데믹(2026)"),
    ("ebola-pandemic-in-2026", "에볼라 팬데믹 전환"),
    ("ebola-case-in-the-us-by-june-30", "에볼라 미국 유입"),
    ("new-coronavirus-pandemic-in-2026", "코로나 변종 재유행"),
    ("measles-cases-in-us-in-2026", "홍역 미국 확산"),
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


def fetch_cidrap() -> dict[str, int | None]:
    """CIDRAP 질병별 RSS 건수. 피드 하나가 죽어도 나머지는 계속 수집."""
    out: dict[str, int | None] = {}
    for slug, label, url in CIDRAP_FEEDS:
        try:
            r = requests.get(url, headers=USER_AGENT, timeout=15)
            r.raise_for_status()
            out[slug] = r.text.count("<item>")
        except Exception:
            out[slug] = None
    return out


def fetch_polymarket_odds() -> dict[str, dict]:
    """워치리스트 팬데믹 예측시장의 현재가(Yes 확률)·거래량. 키 불필요, 완전 무료."""
    slugs = [slug for slug, _ in POLYMARKET_WATCHLIST]
    r = requests.get(
        "https://gamma-api.polymarket.com/events",
        params=[("slug", s) for s in slugs],
        headers=USER_AGENT,
        timeout=15,
    )
    r.raise_for_status()
    by_slug = {e["slug"]: e for e in r.json()}

    out: dict[str, dict] = {}
    for slug, label in POLYMARKET_WATCHLIST:
        event = by_slug.get(slug)
        if not event or not event.get("markets"):
            continue
        market = event["markets"][0]
        prices = json.loads(market["outcomePrices"])  # ["Yes가", "No가"]
        out[slug] = {
            "label": label,
            "yes_probability": float(prices[0]),
            "volume_24h": event.get("volume24hr"),
        }
    return out


POLYMARKET_HISTORY_FILE = DATA_DIR / "polymarket_history.json"

# 급변("쏠림") 판정 기준: 직전 회차 대비 확률이 3%p 이상 움직이거나
# 24시간 거래량이 2배 이상 뛰면 단순 정보가 아니라 "변화" 신호로 플래그.
PROB_SURGE_THRESHOLD = 0.03
VOLUME_SURGE_RATIO = 2.0


def detect_polymarket_surges(odds: dict[str, dict]) -> dict[str, dict]:
    """직전 회차 스냅샷과 비교해 각 시장에 prob_change·volume_ratio·surge_alert를 채워 넣는다."""
    DATA_DIR.mkdir(exist_ok=True)
    try:
        history = json.loads(POLYMARKET_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        history = {}

    for slug, entry in odds.items():
        prev = history.get(slug)
        entry["prob_change"] = None
        entry["volume_ratio"] = None
        entry["surge_alert"] = False

        if prev:
            prob_change = entry["yes_probability"] - prev["yes_probability"]
            entry["prob_change"] = round(prob_change, 4)

            ratio = None
            prev_vol = prev.get("volume_24h") or 0
            if prev_vol > 0 and entry.get("volume_24h") is not None:
                ratio = round(entry["volume_24h"] / prev_vol, 2)
                entry["volume_ratio"] = ratio

            entry["surge_alert"] = abs(prob_change) >= PROB_SURGE_THRESHOLD or (
                ratio is not None and ratio >= VOLUME_SURGE_RATIO
            )

        history[slug] = {"yes_probability": entry["yes_probability"], "volume_24h": entry.get("volume_24h")}

    POLYMARKET_HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return odds


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
        # WHO EMRO·SEARO·WPRO RSS는 전부 죽어있음(404·302→404, 2026-06-24 재확인) —
        # 그 지역은 global_watch.py의 AI 검색 갭필링으로 우회 중. PAHO(아메리카)만 살아있음.
        r = requests.get("https://www.paho.org/en/rss.xml", headers=USER_AGENT, timeout=15)
        r.raise_for_status()
        result["who_paho_items"] = r.text.count("<item>")
        log(f"  WHO PAHO: {result['who_paho_items']}건")
    except Exception as e:
        result["who_paho_items"] = None
        log_error("WHO_PAHO", e)

    try:
        # 원래 쓰려던 percentile 지표 데이터셋(2ew6-ywp6)은 2025-09-12 보관 처리되어
        # 더 안 올라옴 — CDC가 안내한 대체 원시샘플 데이터셋(j9g8-acpt)으로 서버단
        # 집계(최신일 보고 사이트 수·평균 SARS-CoV-2 농도) 조회.
        latest = requests.get(
            "https://data.cdc.gov/resource/j9g8-acpt.json",
            params={"$select": "sample_collect_date", "$order": "sample_collect_date DESC", "$limit": 1},
            headers=USER_AGENT, timeout=15,
        )
        latest.raise_for_status()
        latest_date = latest.json()[0]["sample_collect_date"][:10]

        agg = requests.get(
            "https://data.cdc.gov/resource/j9g8-acpt.json",
            params={"$select": "count(*) as n, avg(pcr_target_avg_conc) as avg_conc",
                    "$where": f"sample_collect_date='{latest_date}'"},
            headers=USER_AGENT, timeout=15,
        )
        agg.raise_for_status()
        row = agg.json()[0]
        result["cdc_nwss"] = {
            "date": latest_date,
            "site_count": int(row["n"]),
            "mean_concentration": round(float(row["avg_conc"]), 1) if row.get("avg_conc") else None,
        }
        log(f"  CDC NWSS(하수): {latest_date} 기준 {result['cdc_nwss']['site_count']}개 사이트, "
            f"평균농도 {result['cdc_nwss']['mean_concentration']}")
    except Exception as e:
        result["cdc_nwss"] = None
        log_error("CDC_NWSS", e)

    try:
        r = requests.get("https://wwwnc.cdc.gov/eid/rss/ahead-of-print.xml", headers=USER_AGENT, timeout=15)
        r.raise_for_status()
        result["cdc_eid_items"] = r.text.count("<item>")
        log(f"  CDC EID 저널: {result['cdc_eid_items']}건")
    except Exception as e:
        result["cdc_eid_items"] = None
        log_error("CDC_EID", e)

    try:
        result["cidrap"] = fetch_cidrap()
        labels = {slug: label for slug, label, _ in CIDRAP_FEEDS}
        summary = ", ".join(f"{labels[k]}={v}건" for k, v in result["cidrap"].items())
        log(f"  CIDRAP(미네소타대): {summary}")
    except Exception as e:
        result["cidrap"] = None
        log_error("CIDRAP", e)

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

    try:
        result["polymarket"] = detect_polymarket_surges(fetch_polymarket_odds())
        for slug, v in result["polymarket"].items():
            tag = "  🚨 급변" if v["surge_alert"] else " "
            change = f" (Δ{v['prob_change']*100:+.1f}%p)" if v["prob_change"] is not None else ""
            log(f"{tag} Polymarket {v['label']}: Yes {v['yes_probability']*100:.1f}%{change} "
                f"(24h거래량 {v['volume_24h']:.0f})")
    except Exception as e:
        result["polymarket"] = None
        log_error("Polymarket", e)

    append_signal(result)
    log("=== 무료 소스 수집 완료 ===")
    return result


def get_latest_polymarket_signals() -> dict | None:
    """가장 최근 free_sources 회차의 Polymarket 신호를 재사용 (재수집하면 히스토리 비교가 꼬임)."""
    if not LOG_FILE.exists():
        return None
    with open(LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("type") == "free_sources" and rec.get("polymarket"):
            return rec["polymarket"]
    return None


# ══════════════════════════════════════════════
# AI 갭필링 수집 (하루 2~4회 권장 — 비용 발생)
# ══════════════════════════════════════════════
def collect_ai_sources() -> dict:
    log("=== AI 갭필링 수집 시작 ===")
    from algorithms.global_watch import run_global_watch

    result = {"type": "ai_sources", "timestamp": dt.datetime.now().isoformat()}
    watch = run_global_watch(polymarket_signals=get_latest_polymarket_signals())
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

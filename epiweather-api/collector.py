"""역병예보 · 무인 신호 수집기 (스케줄러 전용)
==========================================
Windows 작업 스케줄러 등에서 무인 실행되는 스크립트. input() 없음 — 끝까지 실행 후 자동 종료.

실행 모드:
  python collector.py free   → 무료 소스만 (KDCA·네이버·WHO AFRO·WHO PAHO·CDC NWSS·CDC EID·
                                CIDRAP·홍콩CHP·일본IDWR·브라질InfoDengue·Wikipedia·PubMed·Polymarket)
  python collector.py ai     → AI 갭필링 (Perplexity·Tavily·Claude, 비용 발생)
  python collector.py full   → 전부 다 (하루 1회 권장)

로그: data/signals_log.jsonl 에 한 줄씩 누적 저장 → /api/signals 에서 조회 가능.
키는 환경변수로만 주입 (.env 또는 시스템 환경변수). 하드코딩된 키 없음.
"""
from __future__ import annotations
import sys, os, json, time, csv, io
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

# 홍콩 위생방호중심(CHP) — 중국령 커버리지 갭을 메움. publications 피드엔
# 조류인플루엔자 보고서·EV Scan(장바이러스)도 포함. 2026-06-24 라이브 확인.
HK_CHP_FEEDS = [
    ("cd_watch", "홍콩 CD Watch", "https://www.chp.gov.hk/rss/cdwatch_en_RSS.xml"),
    ("publications", "홍콩 정기간행물(조류인플루엔자 등)", "https://www.chp.gov.hk/rss/publication_en_RSS.xml"),
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

# 브라질 InfoDengue(UFMG·Fiocruz 대학 연구진 공동개발) — 도시별 댕기열을
# 자체 나우캐스팅 모델로 Rt·경보단계까지 계산해서 제공하는 연구급 API.
# IBGE 도시코드: 상파울루 3550308, 리우데자네이루 3304557.
INFODENGUE_CITIES = [
    (3550308, "상파울루"),
    (3304557, "리우데자네이루"),
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


def fetch_hk_chp() -> dict[str, int | None]:
    """홍콩 CHP RSS 건수. 피드 하나가 죽어도 나머지는 계속 수집."""
    out: dict[str, int | None] = {}
    for slug, label, url in HK_CHP_FEEDS:
        try:
            r = requests.get(url, headers=USER_AGENT, timeout=15)
            r.raise_for_status()
            out[slug] = r.text.count("<item>")
        except Exception:
            out[slug] = None
    return out


def fetch_japan_idwr() -> dict | None:
    """일본 표본감시(11개 질병) 전국 합계.

    KDCA EIDAPIService가 못 주는 ILI 표본감시와 같은 데이터 종류를 일본은
    매주 CSV로 직접 공개함 — Table 2의 "Total No." 행이 전국 합계라 도도부현별
    합산 없이 그대로 읽으면 됨. 게시 지연이 실측 약 2주라(2026-06-25 확인 시
    26·25주차는 아직 없고 24주차까지만 게시) 최대 3주 전까지 폴백.
    """
    year = dt.date.today().year
    cur_week = dt.date.today().isocalendar()[1]
    for week in range(cur_week, cur_week - 4, -1):
        url = f"https://id-info.jihs.go.jp/en/surveillance/idwr/rapid/{year}/{week:02d}/teiten{week:02d}.csv"
        try:
            r = requests.get(url, headers=USER_AGENT, timeout=15)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
            disease_row, total_row = rows[3], rows[5]
            totals: dict[str, int | None] = {}
            for i in range(1, len(disease_row), 2):
                name = disease_row[i].strip()
                if not name:
                    continue
                val = total_row[i].strip()
                totals[name] = int(val) if val.isdigit() else None
            return {"year": year, "week": week, "national_totals": totals}
        except Exception:
            continue
    return None


def fetch_infodengue() -> dict[str, dict | None]:
    """브라질 InfoDengue — 도시별 댕기열 Rt·경보단계·추정확진자(최근 4주 중 최신).
    한 도시 실패해도 나머지는 계속 수집."""
    year = dt.date.today().year
    cur_week = dt.date.today().isocalendar()[1]
    out: dict[str, dict | None] = {}
    for geocode, label in INFODENGUE_CITIES:
        try:
            r = requests.get(
                "https://info.dengue.mat.br/api/alertcity",
                params={
                    "geocode": geocode, "disease": "dengue", "format": "json",
                    "ew_start": max(1, cur_week - 4), "ew_end": cur_week,
                    "ey_start": year, "ey_end": year,
                },
                headers=USER_AGENT, timeout=15,
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                out[label] = None
                continue
            latest = rows[0]  # 최신순 정렬
            out[label] = {
                "week": latest["SE"],
                "casos": latest["casos"],
                "casos_estimados": latest["casos_est"],
                "rt": latest["Rt"],
                "nivel": latest["nivel"],
                "inc_per_100k": latest["p_inc100k"],
            }
        except Exception:
            out[label] = None
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
        if not event or not event.get("markets") or event.get("closed"):
            continue
        # 일부 이벤트는 단일 마켓이 아니라 임계값별 하위 마켓 여러 개가 묶인
        # 그룹 이벤트(예: 홍역 "500명 이상"·"1000명 이상"·... 10개). markets[0]을
        # 그대로 쓰면 API 응답 순서가 안정적이지 않아 매번 다른 임계값을 가리킬 수 있고,
        # 이미 결과가 확정된(closed) 하위 마켓(확률이 0%/100%로 고정)을 집어올 수도 있다.
        # → 아직 열려 있는 하위 마켓 중 24h 거래량이 가장 큰(가장 활발히 거래되는) 것을
        #   결정적으로 골라 대표 확률로 사용한다.
        open_markets = [m for m in event["markets"] if not m.get("closed")]
        if not open_markets:
            continue
        market = max(open_markets, key=lambda m: m.get("volume24hr") or 0)
        prices = json.loads(market["outcomePrices"])  # ["Yes가", "No가"]
        out[slug] = {
            "label": label,
            "tracked_market": market.get("question"),  # 그룹 이벤트에서 어떤 하위 임계값을 추적했는지 기록
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
        entry["market_switched"] = False

        if prev:
            # 그룹 이벤트는 회차마다 "가장 거래량 많은 하위 임계값"이 바뀔 수 있음 —
            # 그 경우 확률 차이는 실제 시장 변화가 아니라 다른 질문을 비교하는 것이라
            # surge_alert(진짜 급변)이 아니라 market_switched로 따로 표시한다.
            # tracked_market이 없던 과거 기록(오늘 이전)은 비교 불가라 스킵.
            prev_market = prev.get("tracked_market")
            if prev_market is not None and prev_market != entry.get("tracked_market"):
                entry["market_switched"] = True

            prob_change = entry["yes_probability"] - prev["yes_probability"]
            entry["prob_change"] = round(prob_change, 4)

            ratio = None
            prev_vol = prev.get("volume_24h") or 0
            if prev_vol > 0 and entry.get("volume_24h") is not None:
                ratio = round(entry["volume_24h"] / prev_vol, 2)
                entry["volume_ratio"] = ratio

            entry["surge_alert"] = not entry["market_switched"] and (
                abs(prob_change) >= PROB_SURGE_THRESHOLD or (
                    ratio is not None and ratio >= VOLUME_SURGE_RATIO
                )
            )

        history[slug] = {
            "yes_probability": entry["yes_probability"],
            "volume_24h": entry.get("volume_24h"),
            "tracked_market": entry.get("tracked_market"),
        }

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
        # 집계(최근 보고 사이트 수·평균 SARS-CoV-2 농도) 조회.
        #
        # sample_collect_date는 "채집일"이라 실험실 처리 지연으로 최신 며칠은
        # 극소수 사이트만 먼저 들어오고 나머지는 이후 며칠에 걸쳐 채워짐 — 그래서
        # "가장 최근 날짜" 단일일자만 집계하면 site_count=1, mean_concentration이
        # 그 한 사이트 값(종종 0)으로 왜곡됨(실측: 2026-06-25 단일일자 1개 사이트
        # 평균 0.0 vs 같은 날 포함 7일 창 181개 사이트 평균 8494.5). 최신 날짜를
        # 기준으로 7일 창으로 집계해 보고 지연을 흡수한다.
        latest = requests.get(
            "https://data.cdc.gov/resource/j9g8-acpt.json",
            params={"$select": "sample_collect_date", "$order": "sample_collect_date DESC", "$limit": 1},
            headers=USER_AGENT, timeout=15,
        )
        latest.raise_for_status()
        latest_date = dt.date.fromisoformat(latest.json()[0]["sample_collect_date"][:10])
        window_start = latest_date - dt.timedelta(days=6)

        agg = requests.get(
            "https://data.cdc.gov/resource/j9g8-acpt.json",
            params={"$select": "count(*) as n, avg(pcr_target_avg_conc) as avg_conc",
                    "$where": f"sample_collect_date >= '{window_start}' and sample_collect_date <= '{latest_date}'"},
            headers=USER_AGENT, timeout=15,
        )
        agg.raise_for_status()
        row = agg.json()[0]
        result["cdc_nwss"] = {
            "date": f"{window_start}~{latest_date}",
            "site_count": int(row["n"]),
            "mean_concentration": round(float(row["avg_conc"]), 1) if row.get("avg_conc") else None,
        }
        log(f"  CDC NWSS(하수): {window_start}~{latest_date} 기준 {result['cdc_nwss']['site_count']}개 사이트, "
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
        result["hk_chp"] = fetch_hk_chp()
        labels = {slug: label for slug, label, _ in HK_CHP_FEEDS}
        summary = ", ".join(f"{labels[k]}={v}건" for k, v in result["hk_chp"].items())
        log(f"  {summary}")
    except Exception as e:
        result["hk_chp"] = None
        log_error("HK_CHP", e)

    try:
        result["japan_idwr"] = fetch_japan_idwr()
        if result["japan_idwr"]:
            j = result["japan_idwr"]
            flu = j["national_totals"].get("Influenza(excld. avian influenza and pandemic influenza)")
            log(f"  일본 IDWR({j['year']}년 {j['week']}주): 독감 전국 {flu}건 등 11종 표본감시")
        else:
            log("  ⏭ 일본 IDWR: 이번 주·전주 모두 미게시")
    except Exception as e:
        result["japan_idwr"] = None
        log_error("Japan_IDWR", e)

    try:
        result["infodengue"] = fetch_infodengue()
        summary = ", ".join(
            f"{label}=Rt{v['rt']:.2f}(경보{v['nivel']})" if v else f"{label}=실패"
            for label, v in result["infodengue"].items()
        )
        log(f"  InfoDengue(브라질): {summary}")
    except Exception as e:
        result["infodengue"] = None
        log_error("InfoDengue", e)

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
            volume = f"{v['volume_24h']:.0f}" if v["volume_24h"] is not None else "—"
            log(f"{tag} Polymarket {v['label']}: Yes {v['yes_probability']*100:.1f}%{change} "
                f"(24h거래량 {volume})")
    except Exception as e:
        result["polymarket"] = None
        log_error("Polymarket", e)

    try:
        from algorithms.genomic_variants import get_genomic_variant_signals
        result["genomic_variants"] = get_genomic_variant_signals()
        for slug, v in result["genomic_variants"].items():
            if not v.get("available"):
                log(f"  ⏭ Nextstrain {v['label']}: {v.get('reason')}")
                continue
            if v.get("dominant_share") is None:
                log(f"  ⏭ Nextstrain {v['label']}: {v.get('note') or '최근 구간 데이터 없음'}")
                continue
            new_tag = f" 🆕신규계통{v['new_clade_count']}건" if v.get("new_clade_count") else ""
            log(f"  Nextstrain {v['label']}: 우세계통 {v['dominant_clade']}"
                f"({v['dominant_share']*100:.0f}%, n={v['n_recent_sequences']}){new_tag}")
    except Exception as e:
        result["genomic_variants"] = None
        log_error("GenomicVariants", e)

    try:
        from algorithms.social_signal import get_social_signal
        result["social_signal"] = get_social_signal()
        for tag, v in result["social_signal"].items():
            if not v.get("available"):
                log(f"  ⏭ Mastodon #{tag}: {v.get('reason')}")
                continue
            surge_tag = "  🚨 급변" if v["surge_alert"] else " "
            capped = "+" if v.get("sample_capped") else ""
            change = f" (x{v['count_change_ratio']})" if v["count_change_ratio"] is not None else ""
            log(f"{surge_tag} Mastodon #{tag}({v['label']}): 최근{v['window_hours']//24}일 "
                f"{v['count_recent']}{capped}명(원문 {v['count_posts_raw']}건){change}")
    except Exception as e:
        result["social_signal"] = None
        log_error("SocialSignal", e)

    try:
        from algorithms.mobility import get_mobility_score, WATCH_AIRPORTS
        result["mobility"] = get_mobility_score()
        m = result["mobility"]
        if m.get("mobility_rate_limited"):
            log(f"  ⏭ 이동성(OpenSky): 레이트리밋({m['mobility_airports_ok']}/{len(WATCH_AIRPORTS)}개만 조회)")
        else:
            log(f"  이동성(OpenSky): {m['mobility_airports_ok']}개 공항 확인, "
                f"1h 항공편 합계 {m['mobility_total_flights']}")
    except Exception as e:
        result["mobility"] = None
        log_error("Mobility", e)

    try:
        from algorithms.local_news import fetch_all_local_news
        cerebras_key = os.environ.get("CEREBRAS_API_KEY")
        result["local_news"] = fetch_all_local_news(cerebras_key=cerebras_key)
        n = result["local_news"]
        classified = sum(1 for f in n["feeds"] if "llm_hit_ratio" in f)
        tag = f", LLM 재분류 {classified}개 피드" if classified else ""
        log(f"  현지어 뉴스: {n['active_feeds']}/{n['total_feeds']}개 피드, "
            f"키워드 히트 {n['total_kw_hits']}건, 고경보 {n['high_alert_feeds']}개{tag}")
    except Exception as e:
        result["local_news"] = None
        log_error("LocalNews", e)

    try:
        from algorithms.supply_chain import get_supply_signal
        result["supply_chain"] = get_supply_signal()
        s = result["supply_chain"]
        if s.get("status") == "no_key":
            log(f"  ⏭ 공급망 신호: {s.get('note')}")
        else:
            log(f"  공급망 신호: 이상급증 {s['supply_alert_count']}개 품목, "
                f"총 비율합 {s['total_supply_ratio']}")
    except Exception as e:
        result["supply_chain"] = None
        log_error("SupplyChain", e)

    try:
        from algorithms.extra_sources import get_extra_signals
        result["extra_sources"] = get_extra_signals()
        e_ = result["extra_sources"]
        log(f"  추가소스: medRxiv 감염병 프리프린트 {e_['medrxiv']['medrxiv_epi_papers']}건")
    except Exception as e:
        result["extra_sources"] = None
        log_error("ExtraSources", e)

    try:
        from algorithms.wahis import get_animal_signal
        result["wahis"] = get_animal_signal()
        w = result["wahis"]
        log(f"  WAHIS 동물신호: 30일 발병 {w['outbreaks_30d']}건, "
            f"감시질병 활성 {w['watch_hits']}종, WOAH RSS {w['woah_rss_items']}건")
    except Exception as e:
        result["wahis"] = None
        log_error("WAHIS", e)

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            from algorithms.groq_watch import fetch_groq_pulse
            result["groq_pulse"] = fetch_groq_pulse(groq_key)
            g = result["groq_pulse"]
            if g is None:
                log("  ⏭ Groq 웹서치: 응답 파싱 실패")
            elif g["has_new_signal"]:
                log(f"  Groq 웹서치({g.get('urgency')}): {g.get('summary')}")
            else:
                log("  Groq 웹서치: 새 신호 없음")
        except Exception as e:
            result["groq_pulse"] = None
            log_error("GroqWatch", e)
    else:
        result["groq_pulse"] = None
        log("  ⏭ GROQ_API_KEY 없음 — Groq 웹서치 건너뜀")

    append_signal(result)

    try:
        from algorithms.sentinel import scan_spikes
        spikes = scan_spikes()
        if spikes:
            log(f"  🚨 Sentinel: 기준선 대비 2배 이상 급등 {len(spikes)}건 감지 → 검증 대기열 등록")
            for s in spikes:
                log(f"     - {s['layer']}/{s['metric']}: x{s['spike_ratio']} "
                    f"(최근값 {s['latest_val']} vs 기준선 {s['baseline_avg']})")
        else:
            log("  Sentinel: 급등 신호 없음")
    except Exception as e:
        log_error("Sentinel", e)

    try:
        from algorithms.country_risk import log_notable_predictions
        import db
        db.init_db()
        logged = log_notable_predictions()
        if logged:
            log(f"  📋 예측 기록: {len(logged)}개국 주의 이상 등급 → predictions 테이블에 자동 기록")
            for p in logged:
                log(f"     - {p['country']}: 위험도 {p['risk_score']}점")
        else:
            log("  예측 기록: 새로 기록할 주의 이상 국가 없음")
    except Exception as e:
        log_error("PredictionLog", e)

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

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if anthropic_key:
        try:
            from algorithms.nlp_extract import extract_from_global_watch
            import db
            db.init_db()
            extracted = extract_from_global_watch(watch, api_key=anthropic_key)
            for e in extracted:
                db.create_extracted_signal(**e)
            log(f"  NLP 구조화 추출: {len(extracted)}건 저장")
        except Exception as e:
            log_error("NLP_Extract", e)

        try:
            from algorithms.unexplained import run_unexplained_watch
            import db
            db.init_db()
            unexplained = run_unexplained_watch(
                perplexity_key=perplexity_key, tavily_key=tavily_key, anthropic_key=anthropic_key
            )
            if unexplained:
                flagged = unexplained.pop("is_unexplained")
                unexplained.pop("search_source", None)
                db.create_extracted_signal(**unexplained)
                log(f"  설명불가 신호 감시: {'🔴 설명 불가 — 즉시경보' if flagged else '기존 질병 패턴과 일치, 정상'}")
            else:
                log("  ⏭ 설명불가 신호 감시: 새 신호 없음(검색/추출 실패, 배경정보 노이즈, "
                    "또는 최근 21일 내 동일 사건 재탐지 중 하나)")
        except Exception as e:
            log_error("Unexplained_Watch", e)
    else:
        log("  ⏭ ANTHROPIC_API_KEY 없음 — NLP 구조화 추출·설명불가 감시 건너뜀")

    if perplexity_key or tavily_key:
        try:
            from algorithms.verification import verify_pending
            import db
            db.init_db()
            v = verify_pending()
            if "skipped" in v:
                log(f"  ⏭ Sentinel 검증: {v.get('note')}")
            elif v.get("verified"):
                log(f"  Sentinel 검증: {v['verified']}건 처리 "
                    f"(확인 {v['confirmed']}건 / 기각 {v['dismissed']}건, {v['note']} 사용)")
            else:
                log("  Sentinel 검증: 대기 중인 항목 없음")
        except Exception as e:
            log_error("Verification", e)
    else:
        log("  ⏭ PERPLEXITY_API_KEY/TAVILY_API_KEY 없음 — Sentinel 검증 건너뜀")

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

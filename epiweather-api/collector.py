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
    """에러를 파일에 남기고 **stdout에도 반드시 찍는다**.

    예전엔 파일에만 썼다. 그래서 KDCA가 나흘·93회 연속으로 죽는 동안 Railway 배포
    로그는 완벽하게 깨끗했고, 로그를 아무리 들여다봐도 원인이 안 보였다(2026-08-13~17).
    에러가 파일 안에만 있으면 서버에 들어갈 수 있는 사람만 볼 수 있는데, 그건
    '조용한 실패'를 막겠다는 이 시스템의 설계 목적과 정면으로 어긋난다.
    """
    line = f"{dt.datetime.now().isoformat()} | {context} | {str(e)[:200]}"
    print(f"  ❌ [{context}] {type(e).__name__}: {str(e)[:200]}", flush=True)
    DATA_DIR.mkdir(exist_ok=True)
    with open(ERR_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def mark_no_data(result: dict, key: str) -> None:
    """'수집은 정상인데 이번 주기엔 쓸 값이 없다'고 표시한다(source_health가 읽음).

    실패와 구분하려는 것이다. 위키미디어 페이지뷰의 404는 집계 지연이라 정상이고,
    OpenSky는 껍데기만 올 때가 있다 — 둘 다 '고장'이 아니라 '값 없음'이다.
    이걸 실패로 세면 상시 degraded에 앉아 매일 경보가 울리고, 사람은 경보를 무시하게
    된다. 반대로 성공으로 세면 죽은 소스가 살아있다고 보고된다. 둘 다 거짓이다.

    ⚠️ '값 없음'은 원인을 안 밝혀도 된다는 뜻이 **아니다.** OpenSky가 왜 껍데기만
    오는지를 "클라우드 IP 차단"이라고 여기 단정해뒀다가, 2026-08-17~28 열흘 동안
    실제 원인을 확인할 방법이 없었다. 값 없음으로 표시하는 쪽은 사유를 함께
    로그에 남길 책임이 있다.
    """
    result.setdefault("_no_data_keys", [])
    if key not in result["_no_data_keys"]:
        result["_no_data_keys"].append(key)


def _fmt_failure_reasons(reasons: dict[str, int] | None) -> str:
    """{"http_403": 11} → "http_403×11". 사유가 없으면 그 사실을 명시한다.

    ★ skipped_* 는 언제나 맨 뒤로 보낸다 ★
    조기 중단이 걸리면 첫 공항 하나가 진짜 사유를 갖고 나머지 열 개가
    skipped_* 가 된다. 개수 순으로만 정렬하면 **파생 결과(×10)가 진짜 원인(×1)을
    가리고 맨 앞에 선다.** 원인이 먼저 읽혀야 한다.

    '사유 없음'도 정보다 — 실패 사유가 하나도 안 잡혔다는 건 실패 경로가 아직
    어딘가에서 조용히 삼켜지고 있다는 뜻이라, 그때는 그것부터 찾아야 한다.
    """
    if not reasons:
        return "사유 없음(실패 경로가 아직 조용하다)"
    return ", ".join(
        f"{k}×{v}"
        for k, v in sorted(
            reasons.items(),
            key=lambda kv: (kv[0].startswith("skipped_"), -kv[1], kv[0]),
        )
    )


def append_signal(record: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    record["_logged_at"] = dt.datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# KDCA EIDAPIService(법정감염병 전수감시)는 일반 계절 인플루엔자(ILI 표본감시)는
# 포함하지 않는다 — 그건 별도 상품/키 승인이 필요함 (확인됨, 2026-06-22).
# 대신 이 API가 실제로 제공하는 제1·2급 법정감염병 중 조기경보 관심 질병만 추적.
# 국내 법정감염병 — 이제 '전부' 수집하고 질병별로 개별 급증을 본다(kdca_anomaly).
# 아래 KDCA_NOTABLE(위험군)은 '집계 총합(kdca_weekly_total)'에 넣는 대상일 뿐이다 —
# 상재성 고volume 질병(수두·결핵 등)이 총합을 오염시켜 신종 신호를 파묻지 않게.
# 위험군 밖 질병도 전부 수집돼 개별 급증으로 감시된다(레지오넬라처럼 놓치지 않음).
# baseline_collector·기존 참조 호환을 위해 KDCA_WATCH_DISEASES 이름을 유지(=위험군).
from algorithms.kdca_anomaly import KDCA_NOTABLE, disease_spikes, parse_kdca_count
KDCA_WATCH_DISEASES = KDCA_NOTABLE

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

    # ★ 전부 수집 ★ 예전엔 감시목록(allowlist)에 있는 것만 받아 레지오넬라 같은 국내
    # 발생을 통째로 놓쳤다. 이제 신고된 '모든' 법정감염병을 질병별로 받는다 —
    # 목록에 손으로 안 넣어도, 신규 질병이 떠도 자동으로 잡힌다. 위험 판정은
    # 질병별 개별 급증(kdca_anomaly.disease_spikes)이 하고, 집계 총합만 위험군으로 건다.
    out: dict[str, dict[str, int]] = {}
    for it in items:
        if it["period"] not in recent_weeks:
            continue
        # 건수 파싱은 항목별로 따로 — 한 질병의 값이 이상해도(쉼표·"-") 나머지
        # 질병은 살린다. 못 읽은 항목은 아예 안 넣는다(0으로 지어내지 않음).
        count = parse_kdca_count(it.get("resultVal"))
        if count is None:
            continue
        out.setdefault(it["icdNm"], {})[it["period"]] = count
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
                # isdigit()은 "1,384" 같은 천단위 쉼표에 False를 준다 — 그러면
                # 1000건 넘는 질병만 조용히 None(결측)이 돼서, 유행이 커질수록
                # 데이터가 사라지는 최악의 방향으로 틀린다. 에러도 안 난다.
                totals[name] = parse_kdca_count(total_row[i])
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
# 소스헬스(㉔)용: 소스이름 → collect_free_sources() result에서 그 소스가 채우는 키.
# 값이 None이면 그 주기에 수집 실패로 판정. 키 없는 소스가 없도록 result 할당과
# 1:1로 유지할 것(새 소스 추가 시 여기도 추가).
FREE_SOURCE_HEALTH_KEYS = {
    "KDCA": "kdca_weekly", "Naver": "naver_flu_ratio", "WHO_AFRO": "who_afro_items",
    "WHO_PAHO": "who_paho_items", "CDC_NWSS": "cdc_nwss", "CDC_EID": "cdc_eid_items",
    "CIDRAP": "cidrap", "HK_CHP": "hk_chp", "Japan_IDWR": "japan_idwr",
    "InfoDengue": "infodengue", "Wikipedia_Ebola": "wiki_ebola_daily",
    "PubMed": "pubmed_ebola_count", "Polymarket": "polymarket",
    "GenomicVariants": "genomic_variants", "SocialSignal": "social_signal",
    "Mobility": "mobility", "LocalNews": "local_news", "SupplyChain": "supply_chain",
    "ExtraSources": "extra_sources", "WAHIS": "wahis", "GroqWatch": "groq_pulse",
    # NewsWatch — GroqWatch 를 대체해 정식 소스가 됐다(2026-09-01). 나란히 돌린
    # 나흘간 GroqWatch 0% 대 NewsWatch 100% 였다. 실험층일 때는 죽어도 아무도
    # 몰랐는데, 이제 이 층이 죽으면 소스 헬스에서 보인다.
    "NewsWatch": "news_pulse",
    # 재난 감시창(2026-08-28). NewsWatch 와 달리 **실험층이 아니라서** 여기 넣는다 —
    # 이 층이 죽으면 현지어 뉴스가 평시 문턱으로 조용히 돌아가므로, 죽은 걸
    # 아는 게 중요하다. GDACS 가 Railway 에서 막히면(OpenSky 처럼) 여기서 보인다.
    "DisasterWatch": "disaster_watch",
    # 극지 관찰층(2026-09-01 수집 편입). 그전까지는 /api/polar-watch 를 **부를 때만**
    # 계산됐다 — 기능은 있는데 감시는 안 하고 있었다. 쌓이는 게 없어 추세를 못 보고,
    # Open-Meteo 나 러시아어 뉴스가 막혀도 어디에도 안 잡혔다.
    #
    # ★ 하루 한 번이 아니라 매시간인 이유 ★ 소스 헬스는 **매 주기 기록**을 전제로
    # 돈다. 하루 한 번만 돌면 나머지 23주기가 값없음으로 쌓여 거짓 경보가 된다.
    # 호출량은 6개 관측지 × (기후+뉴스) = 12건으로, 이미 매시간 179개 피드를
    # 받는 현지어 뉴스에 비하면 무시할 수준이다.
    "PolarWatch": "polar_watch",
    # 발할라 관찰층(2026-09-03 수집 편입). 그전까지는 엔드포인트를 **부를 때만**
    # 계산됐다 — 극지층과 같은 문제였다. 쌓이는 게 없으니 어제와 비교할 수 없고,
    # 나라장터나 ClinicalTrials 가 막혀도 어디에도 안 잡혔다.
    #
    # ★ 무거운 조각이 주기마다 안 돌아도 이 키는 매 주기 채워진다 ★ 가벼운
    # 조각(준비태세·백신 공급)이 로컬이라 항상 값이 있기 때문이다. 그래서
    # 6시간·24시간 주기를 쓰면서도 헬스에 거짓 값없음이 쌓이지 않는다.
    "Valhalla": "valhalla",
}


def collect_free_sources() -> dict:
    log("=== 무료 소스 수집 시작 ===")
    result = {"type": "free_sources", "timestamp": dt.datetime.now().isoformat()}

    kdca_key = os.environ.get("KDCA_API_KEY")
    if kdca_key:
        try:
            result["kdca_weekly"] = fetch_kdca_weekly(kdca_key)
            # 질병별 개별 급증 — 전체 총합이 평온해도 단일 질병 급증을 잡는다.
            result["kdca_disease_spikes"] = disease_spikes(result["kdca_weekly"])
            n_dis = len(result["kdca_weekly"])
            spikes = result["kdca_disease_spikes"]
            top = (f" · 급증 {len(spikes)}종(최상위 {spikes[0]['disease']})"
                   if spikes else " · 급증 없음")
            log(f"  KDCA(주간, 전 법정감염병 {n_dis}종 수집){top}")
        except Exception as e:
            result["kdca_weekly"] = None
            result["kdca_disease_spikes"] = None
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
            # 소스헬스에도 '실패'가 아니라 '값 없음'으로 넘긴다. 예전엔 여기서 None만
            # 넘어가 실패로 집계돼(성공 90 대 실패 139) 상시 degraded에 앉아 있었다.
            result["wiki_ebola_daily"] = None
            mark_no_data(result, "wiki_ebola_daily")
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

    # ★ 추적에서 뺀 소스는 부르지도 않는다 (2026-08-28) ★
    # 닿지 않는 게 확인된 곳이라 매 주기 20초(토큰 10초 + 첫 공항 10초)를 통째로
    # 버리게 되고, 뒤에 오는 소스가 전부 그만큼 밀린다. 뺀 사실은 로그 한 줄과
    # /api/status 의 retired_sources 에 남는다 — 조용히 사라지지는 않는다.
    # `/api/mobility` 는 살려뒀다. 부활 여부는 그걸 직접 불러 확인한다.
    from algorithms.source_health import is_retired
    if is_retired("Mobility"):
        result["mobility"] = None
        log("  ⏹ 이동성(OpenSky): 추적 제외됨 — 호출 안 함 "
            "(사유는 /api/status 의 retired_sources)")
    else:
        try:
            from algorithms.mobility import get_mobility_score, WATCH_AIRPORTS
            result["mobility"] = get_mobility_score()
            m = result["mobility"]
            if m.get("mobility_rate_limited"):
                log(f"  ⏭ 이동성(OpenSky): 레이트리밋({m['mobility_airports_ok']}/{len(WATCH_AIRPORTS)}개만 조회)")
            else:
                log(f"  이동성(OpenSky): {m['mobility_airports_ok']}개 공항 확인, "
                    f"1h 항공편 합계 {m['mobility_total_flights']}")
            # 공항을 하나도 못 봤으면 dict는 왔어도 알맹이가 없는 것 — 성공으로
            # 세면 죽은 소스가 살아있다고 보고된다.
            if not m.get("mobility_airports_ok"):
                # ★ 전멸했으면 반드시 '왜'를 함께 남긴다(2026-08-28) ★
                # 예전엔 위의 "0개 공항 확인" 한 줄이 전부였다. 그래서 2026-08-17
                # 부터 열흘 넘게 죽어 있는 동안 인증 거부인지 IP 차단인지 알 수
                # 없었고, "클라우드 IP가 막혀서" 라는 **검증된 적 없는 추측**이 이
                # 자리 주석에 적혀 있어 아무도 다시 보지 않았다. 실제 사유를 찍는다.
                log(f"  ⏭ 이동성(OpenSky) 전멸 — 인증={m.get('mobility_auth_status')} "
                    f"· 사유={_fmt_failure_reasons(m.get('mobility_failure_reasons'))}")
                mark_no_data(result, "mobility")
        except Exception as e:
            result["mobility"] = None
            log_error("Mobility", e)

    # ── 재난 → 발병 감시창 (2026-08-28) ────────────────────────────────
    # ★ 현지어 뉴스보다 **먼저** 돌아야 한다 ★ 감시창이 그 뉴스의 고경보
    # 문턱을 낮추는 입력이기 때문이다. 순서가 뒤집히면 창은 열리는데 그 주기의
    # 뉴스에는 반영이 안 돼, 한 시간 늦게 반응하는 층이 된다.
    try:
        from algorithms.disaster_watch import collect_disaster_watch
        result["disaster_watch"] = collect_disaster_watch()
        d = result["disaster_watch"]
        log(f"  재난 감시창: GDACS {d['fetched']}건 수신(신규 {d['new']}) · "
            f"감시 중 {d['watched_country_count']}개국 · 누적 {d['stored']}건")
        for c in d["countries"][:5]:
            w = c["open_windows"][0]
            log(f"    ⚠ {c['country'] or c['country_iso3']}: "
                f"{w['disaster_type']} 후 {w['days_since_disaster']}일 — "
                f"{'·'.join(c['diseases'])} 감시창")
    except Exception as e:
        result["disaster_watch"] = None
        # 감시창이 죽으면 현지어 뉴스는 **평시 문턱으로 돈다.** 조용히 그러면
        # 안 된다 — 개선이 꺼진 채 도는 게 오늘 하루 내내 나온 실패 모양이다.
        log(f"  ❌ 재난 감시창 실패 — 현지어 뉴스는 평시 문턱으로 돈다: "
            f"{type(e).__name__}: {e}")
        log_error("DisasterWatch", e)

    try:
        from algorithms.local_news import fetch_all_local_news
        from algorithms.disaster_watch import open_windows
        cerebras_key = os.environ.get("CEREBRAS_API_KEY")
        # Cerebras 무료 쿼터가 끝나(402) 재분류가 통째로 멈췄다(2026-08-28).
        # 같은 계정의 Groq 로 자동 대체한다 — 오늘 로그로 살아있음이 확인된 경로다.
        result["local_news"] = fetch_all_local_news(
            cerebras_key=cerebras_key, groq_key=os.environ.get("GROQ_API_KEY"),
            watch_windows=open_windows(),
        )
        n = result["local_news"]
        classified = n.get("llm_classified_feeds", 0)
        # 잘린 응답으로 절반만 답받았으면 그것도 같은 줄에 적는다 — 감시창 승격을
        # 고경보와 같은 줄에 붙인 것과 같은 이유다. 따로 두면 "12개 피드" 만 읽고
        # 커버가 반토막인 걸 모른 채 지나간다.
        answered, sent = n.get("llm_answered_titles"), n.get("llm_sent_titles")
        tag = ""
        if classified:
            tag = f", LLM 재분류 {classified}개 피드"
            if answered is not None and sent and answered < sent:
                tag += f"(제목 {answered}/{sent} — 응답 잘림)"
        # 감시창이 몇 개를 끌어올렸는지는 **고경보 수와 같은 줄에** 있어야 한다.
        # 따로 찍으면 "고경보 43개" 만 읽고 문턱이 달라진 걸 모른 채 지나간다.
        promoted = n.get("watch_promoted_feeds", 0)
        # ★ 어느 나라가 올라왔는지까지 찍는다 (2026-08-31) ★
        # 예전엔 "감시창 승격 5개" 라고만 나왔다. 그런데 아침 점검에서 정말
        # 알아야 하는 건 개수가 아니라 **어디냐** 다 — 네팔이 올라왔는지
        # 아닌지를 로그만 보고 알 수 없으면 매번 API를 따로 뒤져야 한다.
        # ★ 창 밖 신호는 따로 찍는다 (2026-09-01) ★
        # 실측: 네팔에 홍수 감시창(콜레라·렙토스피라)이 열린 채로 조류독감이
        # 번지고 있었다. 승격 개수만 찍으면 "콜레라가 오고 있다" 로 읽힌다.
        # 예상한 게 온 것과 다른 게 온 것은 대응이 다르다.
        off = n.get("off_window_signals") or []
        if off:
            log("  ⚠ 창 밖 신호 %d건 — 감시창이 열린 나라인데 창 안 질병이 안 보인다:" % len(off))
            for o in off[:5]:
                log("      %s(%s) ratio=%s · 창은 %s 를 보는 중"
                    % (o["slug"], o["country_iso3"], o["hit_ratio"], "·".join(o["expected"])))
        where = n.get("watch_promoted_countries") or []
        where_tag = f"[{'·'.join(where[:8])}{'…' if len(where) > 8 else ''}]" if where else ""
        watch_tag = (f", 감시창 승격 {promoted}개{where_tag}"
                     f"(문턱 {n['alert_threshold']}→{n['watch_alert_threshold']})"
                     if promoted else "")
        # ★ "179/179개 피드" 는 179개국을 본다는 뜻이 아니다 (2026-08-31) ★
        # 실측에서 179개 중 102개가 서로 완전히 같은 기사를 받고 있었다. 구글이
        # 자체 뉴스판 없는 나라에 언어 기본판을 되돌려 주기 때문이다. 되돌림은
        # 요청마다 흔들리므로 매 수집에서 판정하고, 그 결과를 같은 줄에 남긴다.
        # 표본 부족도 같이 적는다 — '판정 못 했다'와 '조용하다'는 다르다.
        dup, few = n.get("duplicated_feeds", 0), len(n.get("too_few_items_feeds") or [])
        quality_tag = ""
        if dup:
            quality_tag += f", 겹친 피드 {dup}개(경보 제외)"
        if few:
            quality_tag += f", 표본부족 {few}개(판정 안 함)"
        log(f"  현지어 뉴스: {n['active_feeds']}/{n['total_feeds']}개 피드"
            f"(고유 {n.get('distinct_feed_sets', '?')}묶음), "
            f"키워드 히트 {n['total_kw_hits']}건, 고경보 {n['high_alert_feeds']}개"
            f"{tag}{watch_tag}{quality_tag}")
        # ★ 재분류가 안 됐으면 그 사실과 사유를 반드시 찍는다 (2026-08-28) ★
        # 예전엔 실패하면 위의 tag 가 **조용히 빈 문자열이 될 뿐**이었다. 줄 모양이
        # 거의 같아서 아무도 눈치채지 못했고, 실측상 최소 29시간(2026-08-27 06:00
        # UTC 이전부터) 고경보가 키워드 기준으로 나오고 있었다. 그 키워드 방식이
        # 바로 재분류를 만든 이유였는데(오탐 많음) 개선이 꺼진 줄 몰랐던 것이다.
        if not classified:
            log(f"  ❌ 현지어 뉴스 LLM 재분류 실패 — 고경보 {n['high_alert_feeds']}개는 "
                f"**키워드 기준**(오탐 많음)이다: {n.get('llm_failure_reason')}")
        # 179개 피드가 전멸해도 dict는 정상 모양으로 오기 때문에, 예전엔 소스가
        # 살아있다고 기록됐다. '히트 0건'과 '한 곳도 못 읽음'은 다른 사실이다.
        if not n["active_feeds"]:
            mark_no_data(result, "local_news")
    except Exception as e:
        result["local_news"] = None
        log_error("LocalNews", e)

    try:
        from algorithms.supply_chain import get_supply_signal
        result["supply_chain"] = get_supply_signal()
        # 자식이 전부 실패했는데 부모가 ok를 돌려주면, 전면 장애가 '이상 없음'과
        # 똑같이 보인다. 모듈이 스스로 no_data라고 말하면 그대로 소스헬스에 넘긴다.
        if (result["supply_chain"] or {}).get("status") == "no_data":
            mark_no_data(result, "supply_chain")
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

    # ★ 은퇴한 소스는 부르지도 않는다 (2026-09-01) ★
    # 추적에서만 빼면 호출은 계속되고, GroqWatch 의 경우 그게 실제로 해로웠다 —
    # NewsWatch 가 같은 GROQ_API_KEY 로 도는데 GroqWatch 가 매시간 4,000 토큰씩
    # 분당 한도 8,000 에서 태우고 실패했다. 죽은 소스가 산 소스의 예산을 먹는다.
    from algorithms.source_health import RETIRED_SOURCES
    groq_key = os.environ.get("GROQ_API_KEY")
    if is_retired("GroqWatch"):
        result["groq_pulse"] = None
        log(f"  ⏭ GroqWatch 은퇴 — 호출하지 않음 ({RETIRED_SOURCES['GroqWatch'][:40]}…)")
    elif groq_key:
        from algorithms.groq_watch import fetch_groq_pulse, TierLimitReached
        try:
            result["groq_pulse"] = fetch_groq_pulse(groq_key)
            g = result["groq_pulse"]
            if g is None:
                # 이제 실패는 예외로 올라와 아래 except 가 log_error 로 기록한다.
                # 여기 걸리는 건 예외 없이 None 이 온 예상 밖의 경우뿐이다.
                log("  ❌ Groq 웹서치: 예외 없이 빈 응답")
            else:
                # 한도 8,000 대비 얼마나 썼는지 매 주기 남긴다 — 다음에 413·429 가
                # 나도 추측하지 않게(2026-08-26 실측에서 얻은 교훈).
                if g.get("tokens_used"):
                    log(f"  ⚙ Groq 토큰 {g['tokens_used']}/8000 (프롬프트 {g.get('tokens_prompt')})")
                if g["has_new_signal"]:
                    log(f"  Groq 웹서치({g.get('urgency')}): {g.get('summary')}")
                else:
                    log("  Groq 웹서치: 새 신호 없음")
        except TierLimitReached as e:
            # 413(요청이 큼)·429(분당 토큰 초과) 둘 다 무료 티어 한도다 —
            # 소스 고장도 우리 버그도 아니다. 실패로 세면 상시 degraded 에 앉아
            # 매일 울리고 사람이 경보를 무시하게 된다.
            # 값없음으로 기록하되, 72시간을 넘기면 그때는 울린다(NO_DATA_ALARM_HOURS).
            result["groq_pulse"] = None
            mark_no_data(result, "groq_pulse")
            log(f"  ⏭ Groq 웹서치: 무료 티어 한도 — 값없음으로 기록 ({type(e).__name__})")
        except Exception as e:
            result["groq_pulse"] = None
            # ❌ 로 찍는다. 예전엔 실패가 ⏭ 로 찍혀서 절차 문서의
            # "⏭ 는 소프트 스킵이라 문제 아니다" 규칙에 걸러졌다.
            log(f"  ❌ Groq 웹서치 실패: {type(e).__name__}: {e}")
            log_error("GroqWatch", e)
    else:
        result["groq_pulse"] = None
        log("  ⏭ GROQ_API_KEY 없음 — Groq 웹서치 건너뜀")

    # ── 극지 관찰층 (2026-09-01 수집 편입) ─────────────────────────────
    # ★ 경보가 아니라 관찰이다 ★ watch_grade=True 로 경보 파이프라인과 분리돼
    # 있다. 여기서 수집하는 이유는 울리기 위해서가 아니라 **쌓기 위해서**다 —
    # 동토 해빙은 추세가 핵심인데, 부를 때만 계산하면 매번 그 순간만 보게 된다.
    try:
        from algorithms.polar_signals import polar_watch_all
        result["polar_watch"] = polar_watch_all()
        pw = result["polar_watch"]
        regions = pw.get("regions") or []
        top = sorted(regions, key=lambda r: -(r.get("polar_watch_score") or 0))[:3]
        log("  극지 관찰: %d개 관측지 · 등급 %s · 상위 %s"
            % (len(regions), pw.get("grade"),
               ", ".join("%s(%.0f)" % (r["name"][:10], r["polar_watch_score"]) for r in top)))
    except Exception as e:
        result["polar_watch"] = None
        log(f"  ❌ 극지 관찰 실패: {type(e).__name__}: {e}")
        log_error("PolarWatch", e)

    # ── 발할라 관찰층 (2026-09-03 수집 편입) ───────────────────────────
    # ★ 점검에서 드러난 것 ★ 발할라는 **부를 때만** 계산됐다. 극지층이
    # 2026-09-01 에 겪은 것과 똑같다 — 기능은 있는데 감시는 안 하고 있었다.
    # 어제 백신 공급이 어땠는지 오늘 비교할 수가 없었다.
    #
    # ★ 조각마다 주기가 다르다 ★ 준비태세·백신 공급은 로컬이라 매 주기 채우고,
    # 조달(나라장터 66회·47초)은 6시간, 임상 파이프라인은 24시간마다 새로 받는다.
    # 그래도 `valhalla` 키는 매 주기 채워지므로 소스 헬스가 정상으로 돈다 —
    # 무거운 걸 하루 한 번만 돌리면 나머지 23주기가 값없음으로 쌓여 거짓 경보가
    # 된다(극지층 주석의 그 함정).
    try:
        from algorithms.valhalla_watch import valhalla_snapshot
        result["valhalla"] = valhalla_snapshot()
        v = result["valhalla"]
        proc = v.get("procurement") or {}
        ready = v.get("readiness") or {}
        log("  발할라: 조달 %s건(%s) · 백신 단일공급원 %s종 · 대응제 %s건%s"
            % ((proc.get("value") or {}).get("bid_count", "?"),
               "갱신" if proc.get("refreshed") else "%s시간 전 값" % proc.get("age_hours"),
               (v.get("vaccine_chokepoints") or {}).get("single_source_count", "?"),
               ready.get("countermeasure_count", "?"),
               " · 판정불가 %s" % ready["unrated"] if ready.get("unrated") else ""))
        # 무거운 조각이 오래 굳어 있으면 조용히 지나가지 않는다.
        # ★ 판정은 valhalla_watch.stale_parts 가 한다 ★ 여기서 직접 짜다가
        # `part.get("reason", "")` 로 터졌다(2026-09-03) — 키가 있는데 값이 None
        # 이면 .get 의 기본값이 안 먹는다.
        from algorithms.valhalla_watch import stale_parts
        _KO = {"procurement": "조달", "pipeline": "파이프라인"}
        for key, part in stale_parts(v):
            log("  ⚠ 발할라 %s %s (%s시간 전 값 사용)"
                % (_KO.get(key, key), part["reason"], part.get("age_hours")))
        # 정적 축(백신 공급·국가 역량)이 묵었으면 매 주기 보이게 한다.
        # /api/status 에만 있으면 아무도 매시간 들여다보지 않는다.
        refs = v.get("reference_snapshots") or {}
        for name in refs.get("stale") or []:
            log("  ⚠ 발할라 기준 스냅샷 '%s' 묵음 (%s일 전) — 주간작업이 갱신 시도"
                % (name, (refs.get("ages_days") or {}).get(name)))
    except Exception as e:
        result["valhalla"] = None
        log(f"  ❌ 발할라 관찰 실패: {type(e).__name__}: {e}")
        log_error("Valhalla", e)

    # ── NewsWatch — GroqWatch 무료 대체 후보를 **나란히** 돌린다 (2026-08-28) ──
    # GroqWatch 가 주기의 57% 를 티어 한도로 실패하는데 유료 전환은 선택지가
    # 아니다. 그래서 검색(Google News RSS·무료)과 요약(Cerebras·하루 100만 토큰)을
    # 분리한 층을 만들었다 — 주입되는 검색량을 **우리가 통제**하는 게 요점이다.
    #
    # ★ 아직 대체가 아니라 대조다 ★ Google News RSS 는 compound-mini 의 웹서치보다
    # 얕다. 같은 주기에 둘 다 찍어놓고 무엇을 놓치는지 눈으로 보고 나서 정한다.
    # 소스 헬스(FREE_SOURCE_HEALTH_KEYS)에는 **일부러 안 넣었다** — 실험 중인 층이
    # 실패할 때 경보가 울리면 진짜 사고와 섞인다.
    #
    # 2026-08-28 오후: Cerebras 가 402(무료 한도 소진)로 죽어 이 층이 **매 주기
    # 통째로 실패**하고 있었다(`❌ NewsWatch 실패: HTTPError: 402 …`). 현지어
    # 뉴스 재분류에 붙인 Groq 폴백을 여기에도 연결한다 — 그래서 키 조건도
    # 'Cerebras 가 있으면' 이 아니라 '둘 중 하나라도 있으면' 으로 바뀐다.
    cerebras_key_watch = os.environ.get("CEREBRAS_API_KEY")
    groq_key_watch = os.environ.get("GROQ_API_KEY")
    if cerebras_key_watch or groq_key_watch:
        try:
            from algorithms.news_watch import fetch_news_pulse
            result["news_pulse"] = fetch_news_pulse(cerebras_key_watch, groq_key_watch)
            n = result["news_pulse"]
            log(f"  ⚙ NewsWatch[{n.get('source')}] 토큰 {n.get('tokens_used')} "
                f"(프롬프트 {n.get('tokens_prompt')}) · 제목 "
                f"{n.get('headline_count')}/{n.get('headlines_found')}개")
            if n["has_new_signal"]:
                log(f"  NewsWatch({n.get('urgency')}): {n.get('summary')}")
            else:
                log("  NewsWatch: 새 신호 없음")
        except Exception as e:
            result["news_pulse"] = None
            # 2026-09-01 부터 정식 소스다 — 소스 헬스에 실패로 기록된다.
            log(f"  ❌ NewsWatch 실패: {type(e).__name__}: {e}")
            log_error("NewsWatch", e)
    else:
        result["news_pulse"] = None
        log("  ⏭ CEREBRAS_API_KEY·GROQ_API_KEY 둘 다 없음 — NewsWatch 건너뜀")

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

    # ── 선행성 원장 (2026-09-03 편입) ─────────────────────────────────────
    # ★ 왜 여기서 쓰는가 ★ 지금까지는 **선언이 난 뒤에** extracted_signals 를
    # 거꾸로 뒤져 "그때 갖고 있었나" 를 따졌다. 그러다 에볼라 DRC 2026 에서
    # 선언 42~85일 **뒤에** 적재한 신호로 "선언보다 5일 먼저" 를 계산하는 사고가
    # 났다. 순서를 뒤집는다 — 문턱을 넘는 순간 그 자리에서 적고, 선언은 그
    # 뒤에 온다. 그러면 crossed_at 이 선언보다 앞선다는 사실 자체가 증거다.
    try:
        from algorithms.lead_time_ledger import (
            ledger_record, resolve_ledger, scan_and_record,
        )
        import db
        db.init_db()
        opened = scan_and_record()
        for entry in opened:
            log("  🔖 선행성 원장: %s / %s 문턱 통과(심각도 %.1f) — 선언 전 기록"
                % (entry["disease"], entry["country_iso3"] or "국가미상", entry["severity"]))
        outcome = resolve_ledger()
        for hit in outcome["closed_declared"]:
            # ★ 이 줄이 제품의 논지가 처음으로 실측되는 자리다 ★
            log("  ★ 선행일수 실측: %s — 공식 선언보다 %+d일 (%s)"
                % (hit["disease"], hit["lead_days"], hit["event_id"]))
        if outcome["closed_no_declaration"]:
            # 빗나간 것도 말한다. 안 그러면 정밀도만 있는 성적표가 된다.
            log("  선행성 원장: 기한 내 선언 없음 %d건(오경보로 닫음)"
                % outcome["closed_no_declaration"])
        record = ledger_record()
        log("  선행성 원장: 실측 %d건 · 오경보 %d건 · 추적 중 %d건"
            % (record["measured_events"], record["false_alarms"],
               record["open_crossings"]))
    except Exception as e:
        log(f"  ❌ 선행성 원장 실패: {type(e).__name__}: {e}")
        log_error("LeadTimeLedger", e)

    # 소스별 헬스 기록(㉔) — result의 각 키가 None이면 이번 주기 수집 실패로
    # 판정. 주기당 소스별 정확히 1회만 기록해 "어느 소스가 며칠째 죽었는지"를
    # /api/status에서 눈에 보이게 한다(조용한 실패 제거).
    try:
        from algorithms.source_health import record_cycle, pending_notifications, mark_notified
        record_cycle(result, FREE_SOURCE_HEALTH_KEYS)

        # 통보는 '경계를 넘는 순간' 1회가 아니라 죽어있는 동안 계속 낸다.
        # 예전 방식은 3회째에 딱 한 번 울리고 끝이라, KDCA가 나흘·93회를 죽어도
        # 알림은 나흘 전 1건뿐이었다(2026-08-13). 아래 pending_notifications가
        # 24시간마다 다시 울리고, 살아나면 복구도 알린다.
        pending = pending_notifications()
        for d in pending["degraded"]:
            log(f"  ⚠️ 소스 중단: {d['source']} ({d['status']}, 연속 실패 {d['consecutive_failures']}회)")
        for s in pending["recovered"]:
            log(f"  ✅ 소스 복구: {s}")
        from algorithms.notifier import notify_source_health
        if notify_source_health(pending):
            # 전송에 성공했을 때만 도장 — 실패한 통보를 '했다'고 적으면
            # 다음 주기에 조용해져서 알림 자체를 잃는다.
            mark_notified([d["source"] for d in pending["degraded"]] + pending["recovered"])
    except Exception as e:
        log_error("SourceHealth", e)

    # ★ 매 주기 건강 요약 한 줄 ★
    # 위 pending_notifications는 '새로 죽었거나 24시간이 지난' 것만 찍는다.
    # 그래서 평소 주기엔 건강 정보가 로그에 전혀 안 남고, /api/status를 못 부르는
    # 환경(점검 세션의 egress 정책 등)에서는 "소스가 조용히 늙고 있는 상태"를
    # 확인할 방법이 사라진다 — 8/13 사고를 나흘 끌었던 바로 그 사각지대다.
    # 로그만으로도 판단이 서게 매 주기 한 줄로 남긴다.
    try:
        from algorithms.source_health import source_health_report
        rep = source_health_report()
        stale = [
            f"{s['source']}({s['staleness_hours']}h)"
            for s in rep["sources"]
            if s["status"] == "ok" and (s["staleness_hours"] or 0) > 3
        ]

        def _brief(names: list, cap: int = 5) -> str:
            """이름을 나열하되 길어지면 줄인다 — 한 줄 요약이 화면을 넘기면
            사람이 안 읽고, 안 읽히는 로그는 없는 것과 같다."""
            if len(names) <= cap:
                return ", ".join(map(str, names))
            return ", ".join(map(str, names[:cap])) + f" 외 {len(names) - cap}개"

        # 문제가 있는 항목만 붙인다. 예전 초안은 '중단 없음 · 값없음 없음 ·
        # 늙는중 없음'처럼 빈 항목을 다 나열해서, 정작 문제가 생겼을 때 눈에
        # 안 띄었다. 평소엔 짧게, 문제가 생기면 길어지는 쪽이 맞다.
        parts = [f"정상 {rep['healthy_count']}/{rep['total_tracked']}"]
        if rep["degraded_sources"]:
            parts.append(f"중단 {_brief(rep['degraded_sources'])}")
        if rep.get("no_data_sources"):
            parts.append(f"값없음 {_brief(rep['no_data_sources'])}")
        # 며칠째 값없음은 따로 시간까지 찍는다. "값없음 Mobility" 만 보면
        # 상시 항목처럼 읽혀서 8일이 지나도 아무도 몰랐다(2026-08-25).
        if rep.get("long_no_data_sources"):
            aged = ", ".join(
                f"{x['source']}({x['staleness_hours']:.0f}h)"
                for x in rep["long_no_data_sources"]
            )
            parts.append(f"❌ 장기 값없음 {aged}")
        # ★ 가끔만 성공하는 소스 ★ 성공률까지 찍는다 — "값없음 GroqWatch" 만
        # 보면 상시 항목처럼 읽혀서, 실제로 7% 성공률인 걸 몇 주째 아무도 몰랐다.
        if rep.get("flaky_sources"):
            spotty = ", ".join(
                f"{x['source']}({x['recent_success_rate']:.0%}/{x['window']}주기)"
                for x in rep["flaky_sources"]
            )
            parts.append(f"❌ 간헐 성공 {spotty}")
        if stale:
            parts.append(f"늙는중 {_brief(stale)}")
        if len(parts) == 1:
            parts.append("문제 없음")
        log("  📊 소스 건강: " + " · ".join(parts))
    except Exception as e:
        log_error("HealthSummary", e)

    # ★ 품질 불변식 — 소스가 살아있는 것과 값이 온전한 것은 다르다 (2026-08-30) ★
    # 위의 소스 건강은 "값이 왔는가"만 본다. 2026-08 한 달의 사고 6건은 **전부 그
    # 검사를 통과하면서** 일어났다 — local_news 는 정상적으로 값을 돌려주는데 그
    # 값이 LLM 재분류를 거치지 않은 키워드 결과였던 게 대표적이다(8/28·8/30).
    # 소스 헬스가 구조적으로 못 보는 층이라 따로 센다.
    try:
        from algorithms.quality_health import (
            record_cycle as record_quality, summary_line,
            pending_notifications as quality_pending, mark_notified as quality_notified,
        )
        record_quality(result)
        log("  " + summary_line())

        pending = quality_pending()
        for d in pending["degraded"]:
            span = f"{d['consecutive_violations']}주기째"
            if d.get("violated_hours") is not None:
                span += f"/{d['violated_hours']:.0f}시간"
            log(f"  ⚠️ 품질 저하: {d['label']} {span} — {d['why']}")
        for label in pending["recovered"]:
            log(f"  ✅ 품질 회복: {label}")

        from algorithms.notifier import notify_source_health
        # 소스 알림과 같은 통로를 쓰되 모양을 맞춰 넘긴다. 통로를 새로 파면
        # 한쪽만 고장 나도 아무도 모르는 자리가 하나 더 생긴다.
        if pending["degraded"] or pending["recovered"]:
            shaped = {
                "degraded": [
                    {"source": f"품질:{d['label']}", "status": "degraded",
                     "staleness_hours": d.get("violated_hours"),
                     "consecutive_failures": d["consecutive_violations"]}
                    for d in pending["degraded"]
                ],
                "recovered": [f"품질:{label}" for label in pending["recovered"]],
            }
            if notify_source_health(shaped):
                quality_notified(
                    [d["key"] for d in pending["degraded"]] + pending["recovered"]
                )
    except Exception as e:
        # 라벨을 SourceHealth 와 갈라둔다 — 섞이면 '어느 층이 고장났나'를
        # 다시 추측하게 된다. 이 리포가 네 번 당한 게 정확히 그것이다.
        log_error("QualityHealth", e)

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
    # 게이트를 ANTHROPIC_API_KEY 유무로만 잡으면, NIM 키만 넣은 환경에서
    # 추출·설명불가 감시가 통째로 건너뛰어진다(운영에서 실제로 그랬다).
    from algorithms.aegiron_model import extraction_available
    if extraction_available(anthropic_key):
        try:
            from algorithms.nlp_extract import extract_from_global_watch_detailed
            import db
            db.init_db()
            out = extract_from_global_watch_detailed(watch, api_key=anthropic_key)
            for e in out["records"]:
                db.create_extracted_signal(**e)
            # 어느 모델이 뽑았는지 매 사이클 남긴다 — NIM을 켰는데 계속
            # external_llm_fallback이면 NIM이 실패 중인 것이고, 그건 조용히
            # 넘어가면 안 된다(키만 넣고 안 쓰이던 상태가 그렇게 몇 주 갔다).
            by_provider = ", ".join(f"{k}={v}" for k, v in sorted(out["providers"].items()))
            detail = [f"{len(out['records'])}건 저장"]
            if by_provider:
                detail.append(by_provider)
            if out["skipped_duplicate"]:
                detail.append(f"중복건너뜀 {out['skipped_duplicate']}")
            if out["failed"]:
                detail.append(f"추출실패 {out['failed']}")
            if out["blocked"]:
                detail.append(f"주권차단 {out['blocked']}")
            log(f"  NLP 구조화 추출: {' · '.join(detail)}")
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
        log("  ⏭ 추출 백엔드 없음(NIM·로컬모델·ANTHROPIC_API_KEY 전부 미설정) "
            "— NLP 구조화 추출·설명불가 감시 건너뜀")

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

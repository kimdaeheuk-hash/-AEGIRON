"""collector.py가 쌓은 signals_log.jsonl에서 신호원별 시계열을 뽑아내는 공통 정의.

gai.py(①GAI 점수)와 negative_space.py(⑤부정적 공간 감시)가 같은 신호원
목록·계층 배정을 공유해야 해서 분리함 — 신호원이 늘어나도 한 곳만 고치면 됨.

층 배정 근거는 gai.py 모듈 docstring 참고.
"""
from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = DATA_DIR / "signals_log.jsonl"

MIN_HISTORY = 3  # 통계 계산에 필요한 최소 과거 관측치 수

# ── 표본이 아니라 '서로 다른 값'을 센다 ────────────────────────────
#
# ★ 실측 사고 (2026-09-20 01:02) ★
# naver_covid_ratio 를 09-19 03:26 에 붙였다. 도입 PR 에 이렇게 적었다 —
# "신규 지표는 관측 4개 미만이면 판정을 보류하므로 초기 지수 왜곡은 없다".
# **그 보호가 작동하지 않았다.** 22시간 뒤 이 축이 critical 경보를 냈다.
#
#     과거 = 44.89879 × 21개   (도입 후 매시간 같은 값)
#     최신 = 50.87138
#     → pstdev 1.24 → z ≈ 4.6 → 상한 3 → raw 100 → trusted 90 = critical
#
# MIN_HISTORY=3 은 **'한 주기에 한 관측'** 을 전제로 쓴 값이다. 그런데 네이버는
# 주 단위로 값이 바뀌는데 수집은 시간마다 한다 — 같은 주 값이 168번 복제된다.
# 그래서 "과거 관측 4개"가 실제로는 **"과거 관측 1개를 4번 본 것"** 이었다.
# 표본을 세는 것과 관측을 세는 것이 같다는 전제가 수집 주기 때문에 깨진 것이고,
# 깨진 자리에서 z-score 는 조용히 무의미해진다(분모가 '값이 얼마나 변하는가'가
# 아니라 '값이 언제 바뀌었나'를 재게 된다).
#
# 서로 다른 값이 이만큼 쌓이기 전에는 판정하지 않는다. 2개 값으로 낸 "3σ"는
# 숫자이지 근거가 아니다 — 그걸 90점으로 내보내는 건 이 리포가 반복해서
# 고쳐온 '상태 필드가 관측보다 많이 주장하는' 바로 그 짓이다.
#
# ★ 대가를 분명히 적는다 ★ 주 단위 지표는 서로 다른 값 3개가 모이는 데
# 3주가 걸린다. 조기경보에서 3주는 긴 시간이다. 그래도 '모르는 것을 모른다고
# 하는 쪽'을 택했다(캡틴 결정, 2026-09-20). 이걸 줄이려면 수집 주기를 낮추는
# 게 아니라 **원천이 실제로 갱신되는 주기에 맞춰 관측을 세는 것**이 답이다.
MIN_DISTINCT_HISTORY = 3


def has_enough_distinct_history(history) -> bool:
    """z-score 를 낼 만큼 과거가 '변해왔는가'. 표본 수는 MIN_HISTORY 가 본다.

    두 문턱이 따로 있는 이유: 표본이 적은 것(아직 안 쌓임)과 표본은 많은데
    전부 같은 값인 것(수집 주기가 원천보다 빠름)은 다른 상태다. 둘 다 판정을
    막지만, 로그·코드에서 어느 쪽인지 구분할 수 있어야 한다.
    """
    return len(set(history)) >= MIN_DISTINCT_HISTORY


# ── 경보로 올리기 전에 요구하는 최소 절대값 ────────────────────────
#
# ★ 실측 사고 (2026-09-19 05:47) ★
# 아이기론이 처음으로 사람에게 보낸 경보가 이것이었다:
#
#     🟠 비공식신호 · genomic_new_clades_covid — 85.0점
#
# 그 85점을 만든 관측값은 **신규 계통 1건**이었다(로그: 우세계통 25C (XFG)
# (50%, n=559) 🆕신규계통1건). 85.0 ÷ 0.85(academic 신뢰도) = raw 100 =
# z-score 상한이다. 평소 0 인 카운트 지표는 **1 만 나와도 최대 이상도**가 나온다.
# 과거가 거의 다 0 이면 표준편차가 작아서, 0→1 이 곧 3σ 다.
#
# 산술은 맞다. 통계적으로 1 은 정말로 이상값이다. 틀린 건 그 다음 문장이다 —
# "그러므로 사람을 깨울 일이다". 전 세계 공개 시퀀스 빌드에서 새 계통 하나가
# 보이는 건 SARS-CoV-2 에서 늘 있는 일이고, 그걸 매번 high 경보로 올리면
# 경보 피로가 쌓여 **진짜를 놓치는 경로**가 된다(alerts.py 모듈 docstring 참고).
#
# ★ 그래서 지수(GAI)는 안 건드린다 ★
# 이상도는 측정값이다. 1 이 이상값인 건 사실이고, 그 사실을 0 으로 고쳐 쓰면
# 그게 바로 이 리포가 금지하는 "상태 필드가 관측보다 적게/많게 주장하는" 짓이다.
# 문턱은 **경보 승격 자리에만** 둔다 — 측정은 그대로, 판단만 명시적으로.
# 선례: kdca_anomaly.SPIKE_MIN_COUNT = 5 (비율만 보면 2건→4건도 2배다).
#
# ★ 여기 지표를 늘릴 땐 근거가 있어야 한다 ★
# 아래 셋은 같은 함수(genomic_variants.analyze_build)가 같은 모양으로 만드는
# 0 근처 카운트라 함께 넣었다. 다른 지표를 추가하려면 "그 지표가 평소 0 이고
# 1 에 최대 이상도가 났다"는 관측을 먼저 확인해라 — 짐작으로 문턱을 씌우면
# 진짜 신호를 조용히 죽이게 된다. 그건 지금 고치는 것보다 나쁜 고장이다.
ALERT_MIN_COUNT: dict[str, float] = {
    "genomic_new_clades_covid": 2,
    "genomic_new_clades_mpox": 2,
    "genomic_new_clades_rsv": 2,
}


def meets_alert_minimum(metric_id: str, latest: float | None) -> bool:
    """이 지표를 경보 후보로 올려도 되는 관측값인가.

    문턱이 없는 지표는 언제나 True — 이 표는 '막는 목록'이지 '허용 목록'이 아니다.
    새 지표가 추가될 때 여기 없다고 조용히 막히면 안 된다.

    latest 가 None 이면 False 다. 값을 못 본 상태에서 '문턱을 넘었다'고 할 수는
    없다 — 모르는 것을 통과로 세지 않는다(이 리포의 세 갈래 원칙과 같은 방향).
    """
    minimum = ALERT_MIN_COUNT.get(metric_id)
    if minimum is None:
        return True
    return latest is not None and latest >= minimum



def _kdca_latest_total(rec: dict) -> float | None:
    # 이제 kdca_weekly엔 전 법정감염병이 들어온다. 총합에 상재성 질병(수두·결핵 등)을
    # 다 넣으면 신종 신호가 파묻히므로, 집계는 '위험군만' 합산한다(kdca_anomaly).
    from .kdca_anomaly import notable_latest_total
    return notable_latest_total(rec.get("kdca_weekly"))


def _kdca_max_disease_spike(rec: dict) -> float | None:
    # 질병별 개별 급증 중 가장 강한 것. 전체 총합이 평온해도 단일 질병 급증(레지오넬라
    # 등)이 여기서 신호로 뜬다 — '전부 감시 + 개별 판단'의 핵심 지표.
    from .kdca_anomaly import max_spike_signal
    return max_spike_signal(rec.get("kdca_disease_spikes"))


def _japan_idwr_total(rec: dict) -> float | None:
    j = rec.get("japan_idwr")
    totals = (j or {}).get("national_totals") or {}
    vals = [v for v in totals.values() if v is not None]
    return sum(vals) if vals else None


def _hk_chp_total(rec: dict) -> float | None:
    hk = rec.get("hk_chp")
    vals = [v for v in (hk or {}).values() if v is not None]
    return sum(vals) if vals else None


def _infodengue_total(rec: dict) -> float | None:
    inf = rec.get("infodengue")
    vals = [city["casos"] for city in (inf or {}).values() if city]
    return sum(vals) if vals else None


def _cidrap_field(slug: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("cidrap") or {}).get(slug)
    return fn


def _cdc_nwss_conc(rec: dict) -> float | None:
    return (rec.get("cdc_nwss") or {}).get("mean_concentration")


def _polymarket_prob(slug: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("polymarket") or {}).get(slug, {}).get("yes_probability")
    return fn


def _genomic_field(slug: str, field: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("genomic_variants") or {}).get(slug, {}).get(field)
    return fn


_GROQ_URGENCY_SCORE = {"low": 1, "medium": 2, "high": 3}


def _groq_pulse_score(rec: dict) -> float | None:
    g = rec.get("groq_pulse")
    if not g:
        return None
    if not g.get("has_new_signal"):
        return 0
    return _GROQ_URGENCY_SCORE.get(g.get("urgency"), 1)


def _local_news_kw_hits(rec: dict) -> float | None:
    """★ '한 곳도 못 읽음'과 '히트 0건'은 다른 사실이다 ★ (2026-09-19)

    실측 사고. 11:03 에 critical 경보가 캡틴 폰으로 나갔다. 같은 사이클 로그:

        [11:01:49] 현지어 뉴스: 0/179개 피드(고유 0묶음), 키워드 히트 0건
        [11:03:14] 📊 소스 건강: 정상 22/23 · 값없음 LocalNews

    179개 피드가 전멸했는데도 fetch_all_local_news 는 **정상 모양의 dict**를
    돌려준다 — total_kw_hits 가 0 으로. collector.py:798 은 이미 그걸 알고
    active_feeds 가 0 이면 mark_no_data 를 찍는다(그래서 소스 건강에 '값없음'이
    떴다). 그런데 **지표 추출기가 그 구분을 안 봤다.** 0 을 그대로 읽었다.

    그 0 이 negative_space 로 간다. 과거 평균 1,600건대 대비 latest=0 →
    drop_ratio 0.0 → severity (1-0)*100 = 100점 → critical. 부정적 공간 감시가
    "보고 체계가 무너졌다"고 판정한 것이다 — 무너진 건 우리 수집기인데.

    2014년 기니 에볼라를 잡으라고 만든 층이 **우리 스크레이퍼 장애**에 울렸다.
    그리고 그건 이 리포가 반복해서 고쳐온 바로 그 모양이다:

        naver_trends: "그룹 부재 ≠ 검색량 0 … '네이버가 죽었다'가
                       '아무도 안 찾는다'로 둔갑한다"
        mark_no_data: "실패로 세면 상시 degraded, 성공으로 세면 죽은 소스가
                       살아있다고 보고된다. 둘 다 거짓이다"

    한 곳도 못 읽었으면 판정하지 않는다(None). 0 은 '아무도 그 말을 안 했다'는
    관측일 때만 쓴다.
    """
    news = rec.get("local_news")
    if not news:
        return None
    if not news.get("active_feeds"):
        return None
    return news.get("total_kw_hits")


def _local_news_llm_relevant(rec: dict) -> float | None:
    """Cerebras 재분류가 켜져있을 때만 값이 나옴(꺼져있으면 None — 0과 구분)."""
    feeds = (rec.get("local_news") or {}).get("feeds") or []
    classified = [f for f in feeds if "llm_relevant_count" in f]
    if not classified:
        return None
    return sum(f["llm_relevant_count"] for f in classified)


def _social_count(tag: str):
    def fn(rec: dict) -> float | None:
        entry = (rec.get("social_signal") or {}).get(tag)
        if not entry or not entry.get("available"):
            return None
        return entry.get("count_recent")
    return fn


def _ai_anchor_field(field: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("anchors") or {}).get("africa_cdc", {}).get(field)
    return fn


# (metric_id, collector.py record type, 레코드 → 값 추출 함수, 신뢰도 카테고리)
LAYERS = {
    "official": {
        "label": "공식신호", "weight": 0.15,
        "metrics": [
            ("kdca_weekly_total", "free_sources", _kdca_latest_total, "government"),
            ("kdca_disease_spike_max", "free_sources", _kdca_max_disease_spike, "government"),
            ("who_afro_items", "free_sources", lambda r: r.get("who_afro_items"), "who"),
            ("who_paho_items", "free_sources", lambda r: r.get("who_paho_items"), "who"),
            ("cdc_eid_items", "free_sources", lambda r: r.get("cdc_eid_items"), "cdc"),
            ("hk_chp_total", "free_sources", _hk_chp_total, "government"),
            ("japan_idwr_total", "free_sources", _japan_idwr_total, "government"),
            ("infodengue_casos_total", "free_sources", _infodengue_total, "academic"),
        ],
    },
    "informal": {
        "label": "비공식신호", "weight": 0.20,
        "metrics": [
            ("cidrap_ebola", "free_sources", _cidrap_field("ebola"), "academic"),
            ("cidrap_mers", "free_sources", _cidrap_field("mers"), "academic"),
            ("cidrap_cholera", "free_sources", _cidrap_field("cholera"), "academic"),
            ("africa_cdc_confirmed", "ai_sources", _ai_anchor_field("confirmed_cases"), "ai_extracted"),
            ("africa_cdc_deaths", "ai_sources", _ai_anchor_field("deaths"), "ai_extracted"),
            ("local_news_kw_hits", "free_sources", _local_news_kw_hits, "behavioral_api"),
            ("local_news_llm_relevant", "free_sources", _local_news_llm_relevant, "ai_extracted"),
            ("genomic_new_clades_covid", "free_sources", _genomic_field("ncov_open_global_6m", "new_clade_count"), "academic"),
            ("genomic_new_clades_mpox", "free_sources", _genomic_field("mpox", "new_clade_count"), "academic"),
            ("genomic_new_clades_rsv", "free_sources", _genomic_field("rsv_a_genome", "new_clade_count"), "academic"),
            ("groq_pulse_urgency", "free_sources", _groq_pulse_score, "ai_extracted"),
        ],
    },
    "behavioral": {
        "label": "행동신호", "weight": 0.25,
        "metrics": [
            ("naver_flu_ratio", "free_sources", lambda r: r.get("naver_flu_ratio"), "behavioral_api"),
            ("naver_ebola_ratio", "free_sources", lambda r: r.get("naver_ebola_ratio"), "behavioral_api"),
            # 2026-09-19 신설. 국내 코로나 축이 통째로 없어서 "국내 유행 중인가"에
            # 답할 소스가 하나도 없었다(KDCA 전수감시 API 는 표본감시 질병을 안 준다).
            # ★ 다른 네이버 축과 값을 비교하지 마라 ★ 별도 요청이라 척도가 다르다.
            # z-score 는 자기 과거와만 비교하므로 문제되지 않는다.
            ("naver_covid_ratio", "free_sources", lambda r: r.get("naver_covid_ratio"), "behavioral_api"),
            ("social_ebola", "free_sources", _social_count("ebola"), "behavioral_api"),
            ("social_mpox", "free_sources", _social_count("mpox"), "behavioral_api"),
            ("social_birdflu", "free_sources", _social_count("birdflu"), "behavioral_api"),
            ("social_h5n1", "free_sources", _social_count("h5n1"), "behavioral_api"),
            ("social_cholera", "free_sources", _social_count("cholera"), "behavioral_api"),
            ("social_measles", "free_sources", _social_count("measles"), "behavioral_api"),
            ("social_dengue", "free_sources", _social_count("dengue"), "behavioral_api"),
            ("social_marburg", "free_sources", _social_count("marburg"), "behavioral_api"),
            ("wiki_ebola_daily", "free_sources", lambda r: r.get("wiki_ebola_daily"), "behavioral_api"),
            ("pubmed_ebola_count", "free_sources", lambda r: r.get("pubmed_ebola_count"), "behavioral_api"),
            ("supply_total_ratio", "free_sources", lambda r: (r.get("supply_chain") or {}).get("total_supply_ratio"), "behavioral_api"),
            ("supply_alert_count", "free_sources", lambda r: (r.get("supply_chain") or {}).get("supply_alert_count"), "behavioral_api"),
            ("mobility_total_flights", "free_sources", lambda r: (r.get("mobility") or {}).get("mobility_total_flights"), "behavioral_api"),
            ("medrxiv_epi_papers", "free_sources", lambda r: (r.get("extra_sources") or {}).get("medrxiv", {}).get("medrxiv_epi_papers"), "academic"),
        ],
    },
    "environmental": {
        "label": "환경신호", "weight": 0.15,
        "metrics": [
            ("cdc_nwss_concentration", "free_sources", _cdc_nwss_conc, "cdc"),
        ],
    },
    "animal": {
        "label": "동물신호", "weight": 0.15,
        "metrics": [
            ("cidrap_avian_flu", "free_sources", _cidrap_field("avian_flu"), "academic"),
            ("wahis_outbreaks_30d", "free_sources", lambda r: (r.get("wahis") or {}).get("outbreaks_30d"), "government"),
            ("wahis_watch_hits", "free_sources", lambda r: (r.get("wahis") or {}).get("watch_hits"), "government"),
        ],
    },
    "unexplained": {
        "label": "설명불가", "weight": 0.10,
        "metrics": [
            ("polymarket_new_pandemic", "free_sources", _polymarket_prob("new-pandemic-in-2026"), "prediction_market"),
        ],
    },
}


def load_records() -> list[dict]:
    """
    기준선 파일(baseline_signals.jsonl) + 실시간 수집 파일(signals_log.jsonl)을
    시간순으로 합쳐서 반환. 기준선이 먼저, 실시간이 뒤에 오므로 z-score 계산 시
    역사적 컨텍스트를 확보할 수 있다.
    """
    baseline_file = DATA_DIR / "baseline_signals.jsonl"
    records = []
    for path in (baseline_file, LOG_FILE):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def iter_metric_series(records: list[dict]):
    """LAYERS에 정의된 모든 신호원을 순회하며 (layer_key, metric_id, trust_category, series)를 내놓는다."""
    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, trust_category in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            yield layer_key, metric_id, trust_category, series

"""Global Anomaly Index — collector.py가 쌓은 누적 신호를 6계층 가중합산.

인수인계서 Part5 ①②: 신호원마다 "오늘값 vs 과거평균" 이상도를 구하고,
6계층(공식·비공식·행동·환경·동물·설명불가)으로 묶어 가중합산한 단일 점수.

층 배정은 인수인계서가 신호원 목록까지 정해주지 않아서 다음 기준으로 직접 매핑함:
  공식    — 정부기관이 직접 운영하는 API/RSS (KDCA, WHO, CDC EID, 홍콩 CHP, 일본 IDWR, 브라질 InfoDengue)
  비공식  — 학계 큐레이션 매체(CIDRAP) + AI가 검색해 추출한 수치(Africa CDC 앵커, 직접 API 아님)
  행동    — 검색·열람 행태(네이버 검색비율, Wikipedia 조회량, PubMed 논문수)
  환경    — 하수역학(CDC NWSS) — 사람 보고가 아니라 환경 샘플이라 공식신호와 분리
  동물    — CIDRAP 조류인플루엔자 피드를 동물발 신호의 대체재로 사용(전용 동물감시 소스 없음)
  설명불가 — Polymarket "신규 팬데믹" 시장가 — 특정 질병명에 묶이지 않은 군중의 위험인식
"""
from __future__ import annotations
import json
import statistics
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = DATA_DIR / "signals_log.jsonl"

MIN_HISTORY = 3  # 이상도 계산에 필요한 최소 과거 관측치 수
MIN_RELIABLE_SAMPLES = 14  # 이 미만이면 caveat 표시


def _kdca_latest_total(rec: dict) -> float | None:
    kw = rec.get("kdca_weekly")
    if not kw:
        return None
    weeks = {w for weekmap in kw.values() for w in weekmap}
    if not weeks:
        return None
    latest_week = max(weeks)
    return sum(weekmap.get(latest_week, 0) for weekmap in kw.values())


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


def _ai_anchor_field(field: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("anchors") or {}).get("africa_cdc", {}).get(field)
    return fn


# (metric_id, collector.py record type, 레코드 → 값 추출 함수)
LAYERS = {
    "official": {
        "label": "공식신호", "weight": 0.15,
        "metrics": [
            ("kdca_weekly_total", "free_sources", _kdca_latest_total),
            ("who_afro_items", "free_sources", lambda r: r.get("who_afro_items")),
            ("who_paho_items", "free_sources", lambda r: r.get("who_paho_items")),
            ("cdc_eid_items", "free_sources", lambda r: r.get("cdc_eid_items")),
            ("hk_chp_total", "free_sources", _hk_chp_total),
            ("japan_idwr_total", "free_sources", _japan_idwr_total),
            ("infodengue_casos_total", "free_sources", _infodengue_total),
        ],
    },
    "informal": {
        "label": "비공식신호", "weight": 0.20,
        "metrics": [
            ("cidrap_ebola", "free_sources", _cidrap_field("ebola")),
            ("cidrap_mers", "free_sources", _cidrap_field("mers")),
            ("cidrap_cholera", "free_sources", _cidrap_field("cholera")),
            ("africa_cdc_confirmed", "ai_sources", _ai_anchor_field("confirmed_cases")),
            ("africa_cdc_deaths", "ai_sources", _ai_anchor_field("deaths")),
        ],
    },
    "behavioral": {
        "label": "행동신호", "weight": 0.25,
        "metrics": [
            ("naver_flu_ratio", "free_sources", lambda r: r.get("naver_flu_ratio")),
            ("naver_ebola_ratio", "free_sources", lambda r: r.get("naver_ebola_ratio")),
            ("wiki_ebola_daily", "free_sources", lambda r: r.get("wiki_ebola_daily")),
            ("pubmed_ebola_count", "free_sources", lambda r: r.get("pubmed_ebola_count")),
        ],
    },
    "environmental": {
        "label": "환경신호", "weight": 0.15,
        "metrics": [
            ("cdc_nwss_concentration", "free_sources", _cdc_nwss_conc),
        ],
    },
    "animal": {
        "label": "동물신호", "weight": 0.15,
        "metrics": [
            ("cidrap_avian_flu", "free_sources", _cidrap_field("avian_flu")),
        ],
    },
    "unexplained": {
        "label": "설명불가", "weight": 0.10,
        "metrics": [
            ("polymarket_new_pandemic", "free_sources", _polymarket_prob("new-pandemic-in-2026")),
        ],
    },
}


def load_records() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    records = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _anomaly_score(series: list[float | None]) -> float | None:
    """최신값의 과거 대비 이상도. z-score를 [0,3]에 클램프해 0~100으로 환산.

    음수 방향(평소보다 낮음)은 0점 — 신호 감소는 '부정적 공간 감시'가 다룰 영역이라
    여기서는 증가만 이상으로 본다(인수인계서 Part5 ① 개별 공식과 동일한 전제).
    """
    cleaned = [v for v in series if v is not None]
    if len(cleaned) < MIN_HISTORY + 1:
        return None
    *history, latest = cleaned
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    if stdev == 0:
        return 0.0
    z = (latest - mean) / stdev
    return round(max(0.0, min(z, 3.0)) / 3.0 * 100, 1)


def _tier(gai: float | None) -> str | None:
    if gai is None:
        return None
    if gai >= 90:
        return "🔴 위험"
    if gai >= 80:
        return "🟠 경보"
    if gai >= 70:
        return "🟡 주의"
    return "🟢 정상"


def compute_gai() -> dict:
    records = load_records()
    n_free = sum(1 for r in records if r.get("type") == "free_sources")
    n_ai = sum(1 for r in records if r.get("type") == "ai_sources")

    layer_results = {}
    for key, cfg in LAYERS.items():
        metric_scores = []
        for metric_id, rtype, extractor in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            score = _anomaly_score(series)
            if score is not None:
                metric_scores.append({"metric": metric_id, "score": score})
        layer_score = (
            round(statistics.mean(m["score"] for m in metric_scores), 1)
            if metric_scores else None
        )
        layer_results[key] = {
            "label": cfg["label"],
            "weight": cfg["weight"],
            "score": layer_score,
            "metrics": metric_scores,
        }

    available = {k: v for k, v in layer_results.items() if v["score"] is not None}
    if available:
        weight_sum = sum(v["weight"] for v in available.values())
        gai = round(sum(v["score"] * v["weight"] for v in available.values()) / weight_sum, 1)
    else:
        gai = None

    result = {
        "gai": gai,
        "tier": _tier(gai),
        "layers": layer_results,
        "sample_size": {"free_sources": n_free, "ai_sources": n_ai},
    }
    if n_free < MIN_RELIABLE_SAMPLES:
        result["caveat"] = (
            f"누적 샘플 {n_free}건(free_sources) — {MIN_RELIABLE_SAMPLES}건 미만이라 "
            "이상도 통계의 신뢰도가 낮음. 수집기가 더 쌓일수록 정확해짐."
        )
    return result

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


# (metric_id, collector.py record type, 레코드 → 값 추출 함수, 신뢰도 카테고리)
LAYERS = {
    "official": {
        "label": "공식신호", "weight": 0.15,
        "metrics": [
            ("kdca_weekly_total", "free_sources", _kdca_latest_total, "government"),
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
        ],
    },
    "behavioral": {
        "label": "행동신호", "weight": 0.25,
        "metrics": [
            ("naver_flu_ratio", "free_sources", lambda r: r.get("naver_flu_ratio"), "behavioral_api"),
            ("naver_ebola_ratio", "free_sources", lambda r: r.get("naver_ebola_ratio"), "behavioral_api"),
            ("wiki_ebola_daily", "free_sources", lambda r: r.get("wiki_ebola_daily"), "behavioral_api"),
            ("pubmed_ebola_count", "free_sources", lambda r: r.get("pubmed_ebola_count"), "behavioral_api"),
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


def iter_metric_series(records: list[dict]):
    """LAYERS에 정의된 모든 신호원을 순회하며 (layer_key, metric_id, trust_category, series)를 내놓는다."""
    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, trust_category in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            yield layer_key, metric_id, trust_category, series

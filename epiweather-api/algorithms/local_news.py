"""현지어 뉴스 — Phase 2 ⑰ → 전세계 확장(㉘).

영어 번역 전에 현지어로 최초 보도를 잡는 게 목표. EIOS/EMM(WHO+JRC)이 20k
사이트·80개 언어를 자체 크롤링하는 것과 정면 경쟁하는 대신, 후발주자 이점을
쓴다: Google News RSS가 나라·언어별로 이미 현지 여러 매체를 집계해주므로,
국가+언어+질병 쿼리로 전세계 50여 개국을 단일 신뢰 도메인에서 커버한다.
(BBC 같은 단일 매체 피드보다 국가당 소스 폭이 훨씬 넓어 EMM 방식에 더 가깝다.)

감지 방식:
  각 국가 Google News RSS에서 최근 항목 수 + 감염병 키워드 히트 수를 반환.
  키워드 = 현지어 일반어(질병/유행/열 등) + 전세계 공통 질병명(Latin 표기).
  질병명(Ebola·Cholera·Dengue·Mpox·H5N1 등)은 현지어 기사에서도 Latin 그대로
  쓰이는 경우가 많아, 언어를 다 번역하지 않아도 교차언어로 잡히는 앵커 역할.
  최종 고경보 판정은 Cerebras LLM 분류(llm_hit_ratio)가 우선 — 키워드는 폴백.

정직성 유의:
  - 현지어 일반어 키워드는 원어민 검수를 거치지 않은 초안이라 오탐이 나오면
    계속 다듬어야 함(기존 피드들도 그랬음). LLM 분류가 정밀도를 보완.
  - 이 개발 환경(샌드박스)은 외부 RSS 접근이 정책상 막혀 있어 라이브 검증
    불가 — 단위테스트는 mock으로 하고, Railway 운영환경에서 실제 수집됨.
  - 소스가 죽으면 status="error"로 표시되고 active_feeds에서 빠짐(조용히 멈추지
    않음). 피드 수가 많아져 순차 수집은 느리므로 병렬(ThreadPool)로 가져온다.
"""
from __future__ import annotations
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

USER_AGENT = {"User-Agent": "EpiWeather-LocalNews/1.0 (epiweather.kr)"}
TIMEOUT = 15
MAX_WORKERS = 12  # 전세계 피드를 병렬 수집(순차면 국가 수 × 15초라 너무 느림)

# 전세계 공통 질병명 — 현지어 기사에도 Latin 표기로 자주 등장하는 앵커.
# _count_keyword_hits가 소문자 비교라 어떤 문자체계의 기사든 이 이름이 있으면 잡힘.
UNIVERSAL_DISEASE_TERMS = [
    "ebola", "marburg", "nipah", "lassa", "h5n1", "h5n2", "h7n9", "mers", "sars",
    "cholera", "dengue", "zika", "chikungunya", "mpox", "monkeypox", "measles",
    "polio", "covid", "coronavirus", "influenza", "malaria", "plague", "yellow fever",
    "anthrax", "diphtheria",
]
# URL 쿼리에 넣을 공통어(너무 길면 안 되므로 핵심만) — 현지 일반어와 OR로 묶음.
_UNIVERSAL_QUERY_TERMS = [
    "outbreak", "epidemic", "ebola", "cholera", "dengue", "mpox", "measles",
    "bird flu", "coronavirus",
]


def _gnews(local_terms: list[str], hl: str, gl: str) -> str:
    """Google News RSS 검색 URL 생성. hl=인터페이스언어, gl=국가.
    현지 일반어 + 공통어를 OR로 묶어 해당 국가의 감염병 보도만 모은다."""
    query = " OR ".join(local_terms + _UNIVERSAL_QUERY_TERMS)
    ceid = f"{gl}:{hl.split('-')[0]}"
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"


# (slug, 언어, 지역, hl, gl, 현지어 일반 감염병어)
# 오지·발병 고위험·인구밀집 지역을 폭넓게 — 아프리카 다수, 중동, 남·동남아,
# 중남미, 태평양, 유라시아. 현지어를 못 채운 곳은 공통 질병명 앵커가 커버.
_WORLD_SOURCES: list[tuple[str, str, str, str, str, list[str]]] = [
    # ── 아프리카 ──────────────────────────────────────────────
    ("gn_et", "암하라어", "동아프리카(에티오피아)", "am", "ET", ["በሽታ", "ወረርሽኝ", "ቫይረስ"]),
    ("gn_ng", "영어/하우사", "서아프리카(나이지리아)", "en-NG", "NG", ["outbreak", "lassa"]),
    ("gn_cd", "프랑스어", "중앙아프리카(DRC)", "fr", "CD", ["épidémie", "maladie", "fièvre"]),
    ("gn_ug", "영어", "동아프리카(우간다)", "en-UG", "UG", ["outbreak", "ebola"]),
    ("gn_ke", "스와힐리어", "동아프리카(케냐)", "sw", "KE", ["ugonjwa", "mlipuko", "homa"]),
    ("gn_tz", "스와힐리어", "동아프리카(탄자니아)", "sw", "TZ", ["ugonjwa", "mlipuko"]),
    ("gn_sd", "아랍어", "동북아프리카(수단)", "ar", "SD", ["وباء", "حمى", "كوليرا"]),
    ("gn_gh", "영어", "서아프리카(가나)", "en-GH", "GH", ["outbreak", "cholera"]),
    ("gn_sn", "프랑스어", "서아프리카(세네갈)", "fr", "SN", ["épidémie", "fièvre"]),
    ("gn_cm", "프랑스어", "중앙아프리카(카메룬)", "fr", "CM", ["épidémie", "choléra"]),
    ("gn_mg", "프랑스어", "인도양(마다가스카르)", "fr", "MG", ["épidémie", "peste", "fièvre"]),
    ("gn_mz", "포르투갈어", "남부아프리카(모잠비크)", "pt-PT", "MZ", ["surto", "cólera"]),
    ("gn_rw", "프랑스어", "동아프리카(르완다)", "fr", "RW", ["épidémie", "maladie"]),
    ("gn_gn", "프랑스어", "서아프리카(기니)", "fr", "GN", ["épidémie", "ebola", "fièvre"]),
    # ── 중동 ─────────────────────────────────────────────────
    ("gn_sa", "아랍어", "중동(사우디)", "ar", "SA", ["وباء", "فيروس", "ميرس"]),
    ("gn_ye", "아랍어", "중동(예멘)", "ar", "YE", ["وباء", "كوليرا", "حمى"]),
    ("gn_ir", "페르시아어", "중동(이란)", "fa", "IR", ["بیماری", "شیوع", "ویروس"]),
    ("gn_iq", "아랍어", "중동(이라크)", "ar", "IQ", ["وباء", "فيروس"]),
    ("gn_eg", "아랍어", "북아프리카(이집트)", "ar", "EG", ["وباء", "فيروس", "حمى"]),
    # ── 남아시아 ──────────────────────────────────────────────
    ("gn_in_hi", "힌디어", "남아시아(인도)", "hi", "IN", ["प्रकोप", "वायरस", "बुखार", "डेंगू"]),
    ("gn_in_en", "영어", "남아시아(인도)", "en-IN", "IN", ["outbreak", "dengue", "nipah"]),
    ("gn_pk", "우르두어", "남아시아(파키스탄)", "ur", "PK", ["وبا", "بیماری", "وائرس"]),
    ("gn_bd", "벵골어", "남아시아(방글라데시)", "bn", "BD", ["রোগ", "প্রাদুর্ভাব", "ডেঙ্গু"]),
    ("gn_np", "네팔어", "남아시아(네팔)", "ne", "NP", ["महामारी", "रोग", "डेंगु"]),
    ("gn_lk", "싱할라어", "남아시아(스리랑카)", "si", "LK", ["රෝගය", "වසංගතය", "ඩෙංගු"]),
    ("gn_af", "페르시아어(다리)", "중앙아시아(아프가니스탄)", "fa", "AF", ["بیماری", "شیوع"]),
    # ── 동남·동아시아 ────────────────────────────────────────
    ("gn_th", "태국어", "동남아(태국)", "th", "TH", ["โรค", "ระบาด", "ไข้เลือดออก", "ไข้หวัดนก"]),
    ("gn_vn", "베트남어", "동남아(베트남)", "vi", "VN", ["dịch bệnh", "sốt xuất huyết", "cúm gia cầm"]),
    ("gn_id", "인도네시아어", "동남아(인니)", "id", "ID", ["wabah", "penyakit", "demam", "flu burung"]),
    ("gn_ph", "영어", "동남아(필리핀)", "en-PH", "PH", ["outbreak", "dengue", "measles"]),
    ("gn_mm", "버마어", "동남아(미얀마)", "my", "MM", ["ရောဂါ", "ကူးစက်"]),
    ("gn_kh", "크메르어", "동남아(캄보디아)", "km", "KH", ["ជំងឺ", "រាតត្បាត"]),
    ("gn_my", "말레이어", "동남아(말레이시아)", "ms", "MY", ["wabak", "penyakit", "demam"]),
    ("gn_cn", "중국어(간체)", "동아시아(중국)", "zh-CN", "CN", ["疫情", "病毒", "禽流感", "登革热"]),
    ("gn_hk", "중국어(번체)", "동아시아(홍콩)", "zh-HK", "HK", ["疫情", "病毒", "流感"]),
    ("gn_jp", "일본어", "동아시아(일본)", "ja", "JP", ["感染", "流行", "ウイルス", "発熱"]),
    ("gn_kr", "한국어", "동아시아(한국)", "ko", "KR", ["감염", "유행", "바이러스", "발열"]),
    # ── 중남미 ────────────────────────────────────────────────
    ("gn_br", "포르투갈어", "남미(브라질)", "pt-BR", "BR", ["surto", "epidemia", "dengue", "febre"]),
    ("gn_mx", "스페인어", "중미(멕시코)", "es-419", "MX", ["brote", "dengue", "sarampión"]),
    ("gn_pe", "스페인어", "남미(페루)", "es-419", "PE", ["brote", "dengue", "fiebre"]),
    ("gn_co", "스페인어", "남미(콜롬비아)", "es-419", "CO", ["brote", "dengue", "fiebre amarilla"]),
    ("gn_ar", "스페인어", "남미(아르헨티나)", "es-419", "AR", ["brote", "dengue"]),
    ("gn_bo", "스페인어", "남미(볼리비아)", "es-419", "BO", ["brote", "dengue"]),
    ("gn_ve", "스페인어", "남미(베네수엘라)", "es-419", "VE", ["brote", "malaria", "difteria"]),
    # ── 태평양·유라시아 ──────────────────────────────────────
    ("gn_pg", "영어", "태평양(파푸아뉴기니)", "en-PG", "PG", ["outbreak", "measles", "polio"]),
    ("gn_ru", "러시아어", "유라시아(러시아)", "ru", "RU", ["вспышка", "вирус", "эпидемия"]),
    ("gn_ua", "우크라이나어", "유럽(우크라이나)", "uk", "UA", ["спалах", "вірус", "епідемія"]),
    ("gn_tr", "터키어", "유럽·중동(튀르키예)", "tr", "TR", ["salgın", "virüs", "hastalık"]),
]

# (slug, 언어, 지역, RSS URL, 감염병 키워드[현지어+공통 질병명])
LOCAL_FEEDS: list[tuple[str, str, str, str, list[str]]] = [
    (slug, lang, region, _gnews(local_terms, hl, gl), local_terms + UNIVERSAL_DISEASE_TERMS)
    for (slug, lang, region, hl, gl, local_terms) in _WORLD_SOURCES
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def fetch_local_feed(slug: str, lang: str, region: str, url: str, keywords: list[str]) -> dict:
    """단일 RSS 피드에서 항목 수 + 키워드 히트 수 반환. _all_titles는 내부용
    (Cerebras 배치 분류에 씀 — fetch_all_local_news가 최종 응답에서 제거함)."""
    try:
        resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        resp.raise_for_status()
        text = resp.text
        item_count = text.count("<item>")
        keyword_hits = _count_keyword_hits(text, keywords)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text)
        all_titles = [t[0] or t[1] for t in titles if t[0] or t[1]]

        return {
            "slug":          slug,
            "lang":          lang,
            "region":        region,
            "item_count":    item_count,
            "keyword_hits":  keyword_hits,
            "hit_ratio":     round(keyword_hits / max(item_count, 1), 3),
            "sample_titles": all_titles[:5],
            "status":        "ok",
            "_all_titles":   all_titles,
        }
    except Exception as e:
        return {
            "slug":   slug,
            "lang":   lang,
            "region": region,
            "status": "error",
            "error":  str(e)[:100],
        }


def fetch_all_local_news(cerebras_key: str | None = None) -> dict:
    """
    모든 현지어 RSS를 병렬 수집해 언어/지역별 요약 반환.
    keyword_hits가 높을수록 현지에서 감염병 관련 보도가 많다는 신호.
    cerebras_key가 있으면 llm_hit_ratio(제목 배치 분류 기반)를 우선 써서
    고경보 판정 — 키워드 매칭보다 오탐이 적음.

    전세계 50여 개 피드를 순차로 가져오면 국가 수 × 타임아웃이라 너무 느려서
    ThreadPool로 병렬 수집한다. 죽은 소스는 status="error"로 남아 active_feeds에서
    빠지므로 '조용한 실패'가 아니라 눈에 보인다.
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(lambda feed: fetch_local_feed(*feed), LOCAL_FEEDS))

    if cerebras_key:
        from .cerebras_classify import classify_multi_feed
        classify_multi_feed(results, cerebras_key)

    total_hits = 0
    for r in results:
        total_hits += r.get("keyword_hits", 0)
        r.pop("_all_titles", None)

    active_feeds = [r for r in results if r.get("status") == "ok"]
    high_alert = [
        r for r in active_feeds
        if r.get("llm_hit_ratio", r.get("hit_ratio", 0)) >= 0.15
    ]

    return {
        "total_feeds":     len(LOCAL_FEEDS),
        "active_feeds":    len(active_feeds),
        "total_kw_hits":   total_hits,
        "high_alert_feeds": len(high_alert),
        "high_alert":      high_alert,
        "feeds":           results,
    }


def get_local_news_score() -> dict[str, Any]:
    """
    GAI 비공식신호 층에 넣을 단일 점수.
    hit_ratio 평균이 높을수록 현지에서 감염병 관련 보도가 활발하다는 의미.
    """
    result = fetch_all_local_news()
    active = [r for r in result["feeds"] if r.get("status") == "ok" and "hit_ratio" in r]
    avg_ratio = sum(r["hit_ratio"] for r in active) / max(len(active), 1) if active else 0.0
    return {
        "local_news_hit_ratio": round(avg_ratio, 4),
        "total_kw_hits":        result["total_kw_hits"],
        "high_alert_count":     result["high_alert_feeds"],
        "countries_covered":    len(LOCAL_FEEDS),
    }

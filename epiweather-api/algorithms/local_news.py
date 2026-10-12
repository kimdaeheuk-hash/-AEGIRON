"""현지어 뉴스 — Phase 2 ⑰ → 전세계 확장(㉘).

영어 번역 전에 현지어로 최초 보도를 잡는 게 목표. EIOS/EMM(WHO+JRC)이 20k
사이트·80개 언어를 자체 크롤링하는 것과 정면 경쟁하는 대신, 후발주자 이점을
쓴다: Google News RSS가 나라·언어별로 이미 현지 여러 매체를 집계해주므로,
국가+언어+질병 쿼리로 사실상 전세계 모든 나라(~180개국)를 단일 신뢰 도메인에서
커버한다. (BBC 같은 단일 매체 피드보다 국가당 소스 폭이 훨씬 넓어 EMM 방식에
더 가깝다.) '저위험이라 뺀다'는 큐레이션은 하지 않는다 — 팬데믹은 어디서든
시작될 수 있고, 조용한 나라는 하류 LLM 분류기·경보 임계값이 알아서 dormant로
두므로 저위험국을 넣어도 노이즈가 아니라 그냥 잠잠할 뿐이다.

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
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

USER_AGENT = {"User-Agent": "EpiWeather-LocalNews/1.0 (epiweather.kr)"}
TIMEOUT = 15
MAX_WORKERS = 20  # 전세계 ~180개 피드를 병렬 수집(순차면 국가 수 × 15초라 불가능)

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

# ── 나머지 전세계(롱테일) ─────────────────────────────────────
# 위 큐레이션 국가 외 모든 나라. "저위험이라 뺀다"는 판단은 하지 않는다 —
# 팬데믹은 어디서든 시작될 수 있고(코로나도 '저위험'으로 분류됐을 곳에서 나옴),
# 조용한 나라는 하류 LLM 분류기·경보 임계값이 알아서 dormant로 두므로 노이즈가
# 아니다. 현지어 일반어는 생략하고 공통 질병명(Latin 앵커)으로 커버 — 질병명은
# 현지어 기사에도 Latin 표기로 자주 등장한다. hl은 각국 주 언어(불확실하면 en).
def _x(iso2: str, name: str, region: str, hl: str) -> tuple[str, str, str, str, str, list[str]]:
    return (f"gn_{iso2.lower()}", name, region, hl, iso2.upper(), [])


_WORLD_SOURCES_EXTRA: list[tuple[str, str, str, str, str, list[str]]] = [
    # 아프리카 (큐레이션 14개국 외 전부)
    _x("DZ", "알제리", "북아프리카", "ar"), _x("AO", "앙골라", "남부아프리카", "pt-PT"),
    _x("BJ", "베냉", "서아프리카", "fr"), _x("BW", "보츠와나", "남부아프리카", "en"),
    _x("BF", "부르키나파소", "사헬", "fr"), _x("BI", "부룬디", "동아프리카", "fr"),
    _x("CV", "카보베르데", "서아프리카", "pt-PT"), _x("CF", "중앙아프리카공화국", "중앙아프리카", "fr"),
    _x("TD", "차드", "사헬", "fr"), _x("KM", "코모로", "인도양", "fr"),
    _x("CG", "콩고공화국", "중앙아프리카", "fr"), _x("CI", "코트디부아르", "서아프리카", "fr"),
    _x("DJ", "지부티", "동북아프리카", "fr"), _x("GQ", "적도기니", "중앙아프리카", "es-419"),
    _x("ER", "에리트레아", "동북아프리카", "en"), _x("SZ", "에스와티니", "남부아프리카", "en"),
    _x("GA", "가봉", "중앙아프리카", "fr"), _x("GM", "감비아", "서아프리카", "en"),
    _x("GW", "기니비사우", "서아프리카", "pt-PT"), _x("LS", "레소토", "남부아프리카", "en"),
    _x("LR", "라이베리아", "서아프리카(에볼라 진원권)", "en"), _x("LY", "리비아", "북아프리카", "ar"),
    _x("MW", "말라위", "남부아프리카", "en"), _x("ML", "말리", "사헬", "fr"),
    _x("MR", "모리타니", "사헬", "ar"), _x("MU", "모리셔스", "인도양", "en"),
    _x("MA", "모로코", "북아프리카", "ar"), _x("NA", "나미비아", "남부아프리카", "en"),
    _x("NE", "니제르", "사헬", "fr"), _x("ST", "상투메프린시페", "중앙아프리카", "pt-PT"),
    _x("SC", "세이셸", "인도양", "en"), _x("SL", "시에라리온", "서아프리카(에볼라 진원권)", "en"),
    _x("SO", "소말리아", "동북아프리카", "en"), _x("ZA", "남아프리카공화국", "남부아프리카(허브)", "en"),
    _x("SS", "남수단", "동북아프리카", "en"), _x("TG", "토고", "서아프리카", "fr"),
    _x("TN", "튀니지", "북아프리카", "ar"), _x("ZM", "잠비아", "남부아프리카", "en"),
    _x("ZW", "짐바브웨", "남부아프리카", "en"),
    # 중동·걸프 (큐레이션 5개국 외)
    _x("AE", "UAE", "중동(두바이 허브)", "ar"), _x("QA", "카타르", "중동", "ar"),
    _x("KW", "쿠웨이트", "중동", "ar"), _x("OM", "오만", "중동", "ar"),
    _x("BH", "바레인", "중동", "ar"), _x("JO", "요르단", "중동", "ar"),
    _x("LB", "레바논", "중동", "ar"), _x("SY", "시리아", "중동", "ar"),
    _x("IL", "이스라엘", "중동", "he"), _x("PS", "팔레스타인", "중동", "ar"),
    # 중앙·남아시아 (큐레이션 7개국 외)
    _x("BT", "부탄", "남아시아", "en"), _x("MV", "몰디브", "남아시아", "en"),
    _x("KZ", "카자흐스탄", "중앙아시아", "ru"), _x("UZ", "우즈베키스탄", "중앙아시아", "ru"),
    _x("TM", "투르크메니스탄", "중앙아시아", "ru"), _x("TJ", "타지키스탄", "중앙아시아", "ru"),
    _x("KG", "키르기스스탄", "중앙아시아", "ru"), _x("MN", "몽골", "동북아시아(페스트)", "en"),
    # 동·동남아시아 (큐레이션 11개국 외)
    _x("TW", "대만", "동아시아", "zh-TW"), _x("LA", "라오스", "동남아", "lo"),
    _x("SG", "싱가포르", "동남아(허브)", "en"), _x("BN", "브루나이", "동남아", "ms"),
    _x("TL", "동티모르", "동남아", "pt-PT"),
    # 오세아니아 (큐레이션 1개국 외)
    _x("AU", "호주", "오세아니아", "en"), _x("NZ", "뉴질랜드", "오세아니아", "en"),
    _x("FJ", "피지", "태평양", "en"), _x("SB", "솔로몬제도", "태평양", "en"),
    _x("VU", "바누아투", "태평양", "en"), _x("WS", "사모아", "태평양", "en"),
    _x("TO", "통가", "태평양", "en"),
    # 유럽 (큐레이션 2개국 외)
    _x("GB", "영국", "유럽(감시허브)", "en"), _x("IE", "아일랜드", "유럽", "en"),
    _x("FR", "프랑스", "유럽", "fr"), _x("DE", "독일", "유럽", "de"),
    _x("ES", "스페인", "유럽", "es"), _x("IT", "이탈리아", "유럽", "it"),
    _x("PT", "포르투갈", "유럽", "pt-PT"), _x("NL", "네덜란드", "유럽", "nl"),
    _x("BE", "벨기에", "유럽", "fr"), _x("CH", "스위스", "유럽", "de"),
    _x("AT", "오스트리아", "유럽", "de"), _x("SE", "스웨덴", "유럽", "sv"),
    _x("NO", "노르웨이", "유럽", "no"), _x("DK", "덴마크", "유럽", "da"),
    _x("FI", "핀란드", "유럽", "fi"), _x("PL", "폴란드", "유럽", "pl"),
    _x("CZ", "체코", "유럽", "cs"), _x("SK", "슬로바키아", "유럽", "sk"),
    _x("HU", "헝가리", "유럽", "hu"), _x("RO", "루마니아", "유럽", "ro"),
    _x("BG", "불가리아", "유럽", "bg"), _x("GR", "그리스", "유럽", "el"),
    _x("RS", "세르비아", "유럽", "sr"), _x("HR", "크로아티아", "유럽", "hr"),
    _x("BA", "보스니아", "유럽", "bs"), _x("AL", "알바니아", "유럽", "sq"),
    _x("MK", "북마케도니아", "유럽", "mk"), _x("SI", "슬로베니아", "유럽", "sl"),
    _x("LT", "리투아니아", "유럽", "lt"), _x("LV", "라트비아", "유럽", "lv"),
    _x("EE", "에스토니아", "유럽", "et"), _x("BY", "벨라루스", "유럽", "ru"),
    _x("MD", "몰도바", "유럽", "ro"), _x("GE", "조지아", "유럽·서아시아", "en"),
    _x("AM", "아르메니아", "서아시아", "en"), _x("AZ", "아제르바이잔", "서아시아", "az"),
    _x("IS", "아이슬란드", "유럽", "is"), _x("CY", "키프로스", "유럽", "el"),
    _x("LU", "룩셈부르크", "유럽", "fr"), _x("MT", "몰타", "유럽", "en"),
    # 북미 (큐레이션 1개국 외)
    _x("US", "미국", "북미(최대허브)", "en"), _x("CA", "캐나다", "북미", "en"),
    # 중미·카리브
    _x("GT", "과테말라", "중미", "es-419"), _x("BZ", "벨리즈", "중미", "en"),
    _x("SV", "엘살바도르", "중미", "es-419"), _x("HN", "온두라스", "중미", "es-419"),
    _x("NI", "니카라과", "중미", "es-419"), _x("CR", "코스타리카", "중미", "es-419"),
    _x("PA", "파나마", "중미", "es-419"), _x("CU", "쿠바", "카리브", "es-419"),
    _x("DO", "도미니카공화국", "카리브", "es-419"), _x("HT", "아이티", "카리브(콜레라)", "fr"),
    _x("JM", "자메이카", "카리브", "en"), _x("TT", "트리니다드토바고", "카리브", "en"),
    _x("BS", "바하마", "카리브", "en"), _x("BB", "바베이도스", "카리브", "en"),
    # 남미 (큐레이션 7개국 외)
    _x("CL", "칠레", "남미", "es-419"), _x("EC", "에콰도르", "남미", "es-419"),
    _x("PY", "파라과이", "남미", "es-419"), _x("UY", "우루과이", "남미", "es-419"),
    _x("GY", "가이아나", "남미", "en"), _x("SR", "수리남", "남미", "nl"),
]

# (slug, 언어, 지역, RSS URL, 감염병 키워드[현지어+공통 질병명])
# ── 구글이 나라를 무시하고 언어 기본판을 주는 피드들 (2026-08-31 실측) ──────
#
# ★ 179개 피드 중 102개가 서로 완전히 같은 기사를 받고 있었다 ★
# 구글 뉴스는 **자체 뉴스판이 없는 나라**에 gl/ceid 를 줘도 언어 기본판으로
# 되돌려 준다. 그래서 잠비아·미국·사모아가 글자 하나까지 똑같은 기사 100건을
# 받았다. 되돌림 묶음은 12개였고 가장 큰 것이 36개국짜리 범용 영어 묶음이다.
#
# 이게 왜 심각한가:
#   * 소말리아·남수단·잠비아 같은 **발병 위험국의 현지 신호를 아예 못 본다.**
#     대신 호주 조류독감 기사를 본다.
#   * 그 묶음이 문턱을 넘으면 **36개국이 한꺼번에 경보**가 뜬다. 나라별 신호가
#     아닌데 나라별로 보인다.
#
# 고치는 방법: 질의에 그 나라 이름을 넣는다. 실측으로 되돌림이 **0개**가 됐고,
# 안 보이던 신호가 드러났다 — 잠비아 탄저 의심 684건, 캄보디아 H5N1 사람 감염.
#
# 이름은 **그 피드의 언어로** 적는다. 영어 이름보다 기사가 더 많이 잡힌다
# (실측: 차드 Tchad 28건 vs Chad 14건, 모로코 المغرب 15건 vs Morocco 6건).
COUNTRY_TERMS: dict[str, str] = {
    # 범용 영어 되돌림 (36)
    "gn_al": "Albania", "gn_am": "Armenia", "gn_ba": "Bosnia", "gn_bb": "Barbados",
    "gn_bs": "Bahamas", "gn_bt": "Bhutan", "gn_bz": "Belize", "gn_er": "Eritrea",
    "gn_fj": "Fiji", "gn_ge": "Georgia", "gn_gm": "Gambia", "gn_gy": "Guyana",
    "gn_hr": "Croatia", "gn_is": "Iceland", "gn_jm": "Jamaica", "gn_la": "Laos",
    "gn_lr": "Liberia", "gn_ls": "Lesotho", "gn_mk": "Macedonia", "gn_mn": "Mongolia",
    "gn_mt": "Malta", "gn_mu": "Mauritius", "gn_mv": "Maldives", "gn_mw": "Malawi",
    "gn_sb": '"Solomon Islands"', "gn_sc": "Seychelles", "gn_sl": '"Sierra Leone"',
    "gn_so": "Somalia", "gn_ss": '"South Sudan"', "gn_sz": "Eswatini",
    "gn_to": "Tonga", "gn_tt": "Trinidad", "gn_us": '"United States"',
    "gn_vu": "Vanuatu", "gn_ws": "Samoa", "gn_zm": "Zambia",
    # 프랑스어 (15)
    "gn_bf": '"Burkina Faso"', "gn_bi": "Burundi", "gn_bj": "Bénin",
    "gn_cf": "Centrafrique", "gn_cg": "Congo-Brazzaville", "gn_ci": "\"Côte d'Ivoire\"",
    "gn_dj": "Djibouti", "gn_ga": "Gabon", "gn_ht": "Haïti", "gn_km": "Comores",
    "gn_lu": "Luxembourg", "gn_ml": "Mali", "gn_ne": "Niger", "gn_td": "Tchad",
    "gn_tg": "Togo",
    # 아랍어 (16)
    "gn_ae": "الإمارات", "gn_bh": "البحرين", "gn_dz": "الجزائر", "gn_jo": "الأردن",
    "gn_kw": "الكويت", "gn_lb": "لبنان", "gn_ly": "ليبيا", "gn_ma": "المغرب",
    "gn_mr": "موريتانيا", "gn_om": "عُمان", "gn_ps": "فلسطين", "gn_qa": "قطر",
    "gn_sy": "سوريا", "gn_tn": "تونس", "gn_sd": "السودان", "gn_ye": "اليمن",
    # 스페인어 (11)
    "gn_cr": '"Costa Rica"', "gn_do": '"República Dominicana"', "gn_ec": "Ecuador",
    "gn_gq": '"Guinea Ecuatorial"', "gn_gt": "Guatemala", "gn_hn": "Honduras",
    "gn_ni": "Nicaragua", "gn_pa": "Panamá", "gn_py": "Paraguay",
    "gn_sv": '"El Salvador"', "gn_uy": "Uruguay",
    # 러시아어권 (7)
    "gn_az": "Азербайджан", "gn_by": "Беларусь", "gn_kg": "Кыргызстан",
    "gn_kz": "Казахстан", "gn_tj": "Таджикистан", "gn_tm": "Туркменистан",
    "gn_uz": "Узбекистан",
    # 포르투갈어 (6)
    "gn_ao": "Angola", "gn_cv": '"Cabo Verde"', "gn_gw": '"Guiné-Bissau"',
    "gn_pt": "Portugal", "gn_st": '"São Tomé"', "gn_tl": '"Timor-Leste"',
    # 나머지 소묶음 (11)
    "gn_af": "افغانستان", "gn_lk": '"Sri Lanka"', "gn_np": "नेपाल",
    "gn_cy": "Κύπρος", "gn_gr": "Ελλάδα", "gn_ir": "ایران", "gn_kh": "Cambodia",
    "gn_md": "Moldova", "gn_ro": "România", "gn_nl": "Nederland", "gn_sr": "Suriname",
}


def _scoped(url: str, slug: str) -> str:
    """되돌림 피드면 질의에 나라 이름을 덧붙인다. 아니면 그대로."""
    term = COUNTRY_TERMS.get(slug)
    if not term:
        return url
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
    p = urlparse(url)
    q = parse_qs(p.query)
    q["q"] = ["(%s) %s" % (q["q"][0], term)]
    return urlunparse(p._replace(
        query=urlencode({k: v[0] for k, v in q.items()}, quote_via=quote)))


LOCAL_FEEDS: list[tuple[str, str, str, str, list[str]]] = [
    (slug, lang, region, _scoped(_gnews(local_terms, hl, gl), slug),
     local_terms + UNIVERSAL_DISEASE_TERMS)
    for (slug, lang, region, hl, gl, local_terms) in (_WORLD_SOURCES + _WORLD_SOURCES_EXTRA)
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def failure_summary(feeds: list[dict]) -> str | None:
    """실패한 피드 사유를 한 줄로. 실패가 없으면 None (없는 것을 지어내지 않는다).

    ★ 왜 이게 필요했나 ★ 2026-09-19 11:00, 179개 피드가 한꺼번에 죽었다.
    로그에 찍힌 건 이것뿐이었다:

        현지어 뉴스: 0/179개 피드(고유 0묶음), 키워드 히트 0건, 고경보 0개

    사유는 **이미 있었다** — fetch_local_feed 가 피드마다 error 를 담아 돌려주고
    그게 수집 결과에 그대로 실려 있었다. 아무도 읽지 않았을 뿐이다. 같은 주기의
    NewsWatch 는 같은 원인(Google News RSS 503)을 로그에 찍었는데, 이쪽은
    조용했다. 그래서 '우리 수집기 장애'가 '세상이 조용하다'로 읽혔다.

    (이 리포에서 세 번째다 — 추출 실패 사유, TED 400, 그리고 이것.)
    """
    from .common import tally
    reasons = [f.get("reason") or f.get("error") or "Unknown"
               for f in feeds if f.get("status") == "error"]
    return tally(reasons) if reasons else None


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
        from .common import brief_reason
        return {
            "slug":   slug,
            "lang":   lang,
            "region": region,
            "status": "error",
            "error":  str(e)[:100],
            # ★ 짧은 사유를 따로 남긴다 ★ 179개 피드가 한꺼번에 죽으면 긴 문장
            # 179줄은 로그에서 못 읽는다. brief_reason 은 상태코드를 붙여주므로
            # (HTTPError 503) 집계했을 때 한 줄로 원인이 드러난다.
            "reason": brief_reason(e),
            # ★ 조절(503/429)인지 가르는 값과 서버가 말한 대기 시간 ★
            # reason 문자열을 파싱해 503 을 찾으면 문구가 바뀔 때 조용히 깨진다.
            "http_status": getattr(getattr(e, "response", None), "status_code", None),
            "retry_after": (getattr(getattr(e, "response", None), "headers", None) or {})
                           .get("Retry-After"),
        }


# ── 고경보 문턱 ────────────────────────────────────────────────────────
# 평시 문턱. 이 값은 2026-07-08 부터 쓰던 것 그대로다.
ALERT_THRESHOLD = 0.15
# ★ 재난 감시창이 열린 나라만 이 문턱을 쓴다 (2026-08-28) ★
# 감시창의 요점이 여기다. 재난 뒤 잠복 구간에 있는 나라는 **같은 양의 보도라도
# 더 의미가 크다.** 평시라면 넘기던 0.10 을 그 나라에서는 넘기지 않는다.
#
# 왜 0.15 → 0.08 인가: 임의로 정한 값이다. '조금 낮춘다'는 것 외에 실증
# 근거가 없다 — 응답의 `threshold_calibrated=False` 로 그 사실을 명시한다.
# 우리 과거 데이터로 재보정하기 전까지 이 숫자를 근거처럼 인용하지 마라.
WATCH_ALERT_THRESHOLD = 0.08

# ── 국가 한정 피드용 문턱 (2026-08-31) ──────────────────────────────────────
# 질의에 나라 이름을 넣으면 기사 수가 줄고(중앙값 100 → 46) `hit_ratio` 가
# 구조적으로 올라간다. `_count_keyword_hits` 가 **키워드 종류 수**를 세기
# 때문에 분모만 작아지는 셈이다. 실측으로 102개 중 73개(72%)가 0.15 를 넘었다
# — 그대로 두면 경보가 쏟아진다.
#
# ★ 0.20 은 찍은 값이 아니라 '지금 경보량을 유지하는' 값이다 ★
# 표본 20건 이상인 81개 피드에서 문턱별 경보 비율을 재보니:
#     0.15 → 64%   0.20 → 28%   0.25 → 16%   0.30 → 7%
# 현재 전체 179개 중 고경보가 약 50개(28%)다. 0.20 이 그 운영점을 그대로
# 유지한다. 역학적 근거가 아니라 **운영점 일치**이므로 threshold_calibrated 는
# 여전히 False 다 — 이 숫자를 근거처럼 인용하지 마라.
SCOPED_ALERT_THRESHOLD = 0.20
SCOPED_WATCH_ALERT_THRESHOLD = 0.11   # 0.20 × (0.08/0.15), 감시창 완화 비율 유지

# ★ 표본이 적으면 판정하지 않는다 ★
# 국가 한정을 걸면 기사 5건에 키워드 6종이 잡혀 ratio 1.2 가 나오기도 한다.
# 그건 신호가 아니라 표본 부족이다. '모른다'와 '괜찮다'는 다르므로 고경보로
# 올리지도, 정상으로 세지도 않고 따로 보고한다(too_few_items).
MIN_ITEMS_FOR_ALERT = 20


def _feed_iso3(slug: str) -> str | None:
    """피드 슬러그(`gn_np`) → ISO3(`NPL`). 모르면 추측하지 않고 None.

    ★ 한 나라에 피드가 둘일 수 있다 ★ 인도는 힌디어·영어 두 개라
    `gn_in_hi`·`gn_in_en` 이다. `slug[3:]` 을 그대로 쓰면 `in_hi` 가 돼
    **인도만 감시창이 영영 적용되지 않는다** — 홍수 다발국인데. 그래서
    `gn_` 뒤 두 글자만 본다. (2026-08-28 에 테스트가 실제로 잡아낸 버그다.)
    """
    from .country_resolve import iso2_to_iso3
    if not slug.startswith("gn_"):
        return None
    return iso2_to_iso3(slug[3:5])


# ── 프로브: 179건을 쏘기 전에 Google 이 받아주는지 한 건으로 본다 (2026-10-02) ──
# 실측: 09-19 11:00 의 179개 전멸 이후 09-25~10-01 7일 내내 **정확히 11시·12시
# UTC 에만** `HTTPError 503×179` 가 났다(14/14 주기, 부분 실패는 한 번도 없음).
# 같은 두 시각에 NewsWatch 의 단건 요청(11:03·12:03)도 503 이었다. 179건은 75초
# 동안 **한 건도 성공하지 못했으므로 그 주기의 첫 요청부터 막혀 있었다** — 이번
# 주기의 폭주가 막힘을 만든 건 아니다(앞 주기는 한 시간 전). 그 이상은 **모른다**:
# 레이트리밋인지 점검인지, 그 시간대 egress 쪽 문제인지 가려내는 값이 없다.
# 503 에 `Retry-After` 가 오는지조차 로그에 안 남아 있었다.
#
# 그래서 이 수정이 하는 일은 셋뿐이다:
#   ① 막힌 걸 알면서 179건을 더 쏘지 않는다(막힘이 호출량 탓이면 악화를 막고,
#      아니어도 75초짜리 헛호출을 아낀다).
#   ② 짧게 두 번 더 물어(기본 15+30초, Retry-After 가 오면 그 값·회당 최대 60초) 일시적이면 그 주기에 건진다.
#   ③ 서버가 `Retry-After` 를 보내면 그 값을 로그까지 가져온다 — 다음 점검이
#      막힘이 몇 분짜리인지 추측이 아니라 값으로 읽게.
# 막힘이 풀리도록 만드는 수정이 아니다. 풀리는 시각은 Google 이 정한다.
PROBE_FEED_SLUG = "gn_us"
PROBE_RETRY_WAITS = (15, 30)      # 초. 프로브가 조절당하면 이만큼 쉬고 다시 묻는다
PROBE_MAX_WAIT = 60               # Retry-After 가 길어도 한 번에 이 이상은 안 쉰다
SKIPPED_REASON = "호출생략(프로브 조절됨)"
_THROTTLE_STATUS = (429, 503)


def _is_throttled(feed: dict) -> bool:
    return feed.get("status") == "error" and feed.get("http_status") in _THROTTLE_STATUS


def _wait_seconds(feed: dict, default: int) -> int:
    """서버가 `Retry-After`(초)를 보냈으면 그 값, 아니면 기본값. 상한을 둔다.
    HTTP-date 꼴이거나 숫자가 아니면 기본값 — 못 읽은 값을 지어내지 않는다."""
    raw = feed.get("retry_after")
    try:
        return max(1, min(int(raw), PROBE_MAX_WAIT))
    except (TypeError, ValueError):
        return default


def fetch_feeds_with_probe(feeds: list[tuple], sleep=None) -> tuple[list[dict], dict]:
    """(피드 결과들, 프로브 보고). 결과 순서·개수는 `feeds` 와 같다.

    프로브가 조절(503/429)당하면 대기·재시도 뒤에도 막혀 있을 때만 나머지를
    **호출하지 않고** `호출생략` 사유로 채운다. 그 피드들은 status="error" 라
    active_feeds 에서 빠지고 소스 건강이 값없음으로 센다 — 기존 전멸과 같은 취급.
    프로브가 조절이 아닌 이유(연결 실패 등)로 죽으면 막힘이 아니므로 그대로 전부 시도한다.
    """
    # 기본값을 정의 시점에 묶지 않는다(`sleep=time.sleep`) — 그러면 시험의
    # patch 가 안 먹어 진짜로 45초를 쉰다.
    sleep = sleep or time.sleep
    probe_idx = next((i for i, f in enumerate(feeds) if f[0] == PROBE_FEED_SLUG), 0)
    probe = fetch_local_feed(*feeds[probe_idx])
    attempts, waited = 1, 0
    for default_wait in PROBE_RETRY_WAITS:
        if not _is_throttled(probe):
            break
        wait = _wait_seconds(probe, default_wait)
        sleep(wait)
        waited += wait
        probe = fetch_local_feed(*feeds[probe_idx])
        attempts += 1

    throttled = _is_throttled(probe)
    report = {
        "attempts": attempts,
        "waited_sec": waited,
        "throttled": throttled,
        "http_status": probe.get("http_status") if throttled else None,
        "retry_after": probe.get("retry_after") if throttled else None,
        "skipped": 0,
    }
    others = [f for i, f in enumerate(feeds) if i != probe_idx]
    if throttled:
        rest = [{"slug": f[0], "lang": f[1], "region": f[2], "status": "error",
                 "error": "프로브가 조절당해 호출하지 않음", "reason": SKIPPED_REASON,
                 "http_status": None, "retry_after": None} for f in others]
        report["skipped"] = len(rest)
    else:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            rest = list(executor.map(lambda feed: fetch_local_feed(*feed), others))

    results: list[dict] = []
    it = iter(rest)
    for i in range(len(feeds)):
        results.append(probe if i == probe_idx else next(it))
    return results, report


def fetch_all_local_news(cerebras_key: str | None = None,
                         groq_key: str | None = None,
                         watch_windows: dict[str, list[dict]] | None = None) -> dict:
    """
    모든 현지어 RSS를 병렬 수집해 언어/지역별 요약 반환.
    keyword_hits가 높을수록 현지에서 감염병 관련 보도가 많다는 신호.
    cerebras_key가 있으면 llm_hit_ratio(제목 배치 분류 기반)를 우선 써서
    고경보 판정 — 키워드 매칭보다 오탐이 적음.

    전세계 50여 개 피드를 순차로 가져오면 국가 수 × 타임아웃이라 너무 느려서
    ThreadPool로 병렬 수집한다. 죽은 소스는 status="error"로 남아 active_feeds에서
    빠지므로 '조용한 실패'가 아니라 눈에 보인다.
    """
    results, fetch_probe = fetch_feeds_with_probe(LOCAL_FEEDS)

    # ★ LLM 재분류가 실제로 됐는지를 반환값에 싣는다 (2026-08-28) ★
    # 예전엔 실패해도 아무 흔적이 없었다. 그러면 아래 고경보 판정이
    # `llm_hit_ratio` 를 못 찾아 **조용히 키워드 기준으로 떨어지는데**, 그
    # 키워드 방식이 바로 이 재분류를 만든 이유였다(오탐이 많다, 2026-07-08).
    # 개선이 꺼진 채 도는 걸 아무도 모르는 상태였다 — 실측 최소 29시간.
    llm_reason: str | None = None
    if cerebras_key or groq_key:
        from .cerebras_classify import classify_multi_feed
        llm_reason = classify_multi_feed(results, cerebras_key or "", groq_key)
    else:
        llm_reason = "CEREBRAS_API_KEY·GROQ_API_KEY 둘 다 없음"

    # ── 되돌림(중복) 감지 — 제목을 버리기 전에 해야 한다 ────────────────
    # ★ 이건 상시로 돌아야 한다 ★ 되돌림은 고정이 아니라 **요청마다 흔들린다.**
    # 실측(2026-08-31)에서 네팔이 한 번은 고유였다가 다음 번엔 아프가니스탄·
    # 스리랑카와 같은 기사를 받았다. 한 번 조사해서 목록을 박아두면 놓친다.
    #
    # 겹친 피드는 고경보로 올리지 않는다 — 그 나라 신호가 아닌 것을 그 나라
    # 이름으로 경보하면 **없는 발병을 있다고 말하는 것**이 된다.
    import hashlib
    _by_titles: dict[str, list[str]] = {}
    for r in results:
        titles = r.get("_all_titles") or []
        if len(titles) < 3:            # 머리글뿐이면 판정 불가
            continue
        joined = chr(10).join(sorted(titles[2:]))
        key = hashlib.md5(joined.encode("utf-8", "ignore")).hexdigest()
        _by_titles.setdefault(key, []).append(r["slug"])
    duplicate_groups = [sorted(v) for v in _by_titles.values() if len(v) > 1]
    duplicated = {slug for g in duplicate_groups for slug in g}
    for r in results:
        if r["slug"] in duplicated:
            r["duplicate_of"] = sorted(
                next(g for g in duplicate_groups if r["slug"] in g)) 

    # ── 창 안 질병이 실제로 보이는가 (2026-09-01) ────────────────────────
    # ★ 제목을 버리기 전에 해야 한다 ★
    #
    # 실측: 네팔에 홍수 감시창(콜레라·렙토스피라)이 6일째 열려 있는데, 정작
    # 그 나라에서 번지고 있던 것은 **조류독감**이었다(보건부 전국 경보·중앙동물원
    # 폐쇄·여러 지역 살처분). 문턱은 나라 전체에 걸리므로 신호 자체는 잡혔지만,
    # 보고서에는 "감시창 승격 — 렙토스피라증·콜레라" 라고 찍혔다.
    #
    # **잡은 것과 이름표가 달랐다.** 그걸 그대로 두면 읽는 사람은 콜레라가
    # 오고 있다고 이해한다. 창 안 신호와 창 밖 신호는 뜻이 완전히 다르다:
    #
    #     창 안  — 예상한 병이 실제로 오고 있다 (감시창이 맞아가는 중)
    #     창 밖  — 다른 병이 오고 있다 (재난과 무관하거나, 우리가 모르는 경로)
    #
    # 조류독감을 홍수 규칙에 넣는 것은 답이 아니다. 홍수가 조류독감을 만들지는
    # 않으므로, 인과 없는 규칙을 넣으면 그 표 전체의 신뢰가 무너진다.
    # 대신 **무엇이 잡혔는지를 정직하게 갈라 적는다.**
    _windows_pre = watch_windows or {}
    for r in results:
        iso3 = _feed_iso3(r.get("slug", ""))
        if not iso3 or iso3 not in _windows_pre:
            continue
        blob = " ".join(r.get("_all_titles") or []).lower()
        # ★ 판단할 수 있는 창만 판단한다 ★
        # 키워드가 없는 창은 "다른 병이 왔다" 가 아니라 **모른다** 이다.
        # 모르는 것을 창 밖으로 단정하면 없는 경보를 만들어낸다.
        checkable = [w for w in _windows_pre[iso3] if w.get("keywords")]
        r["_window_checkable"] = bool(checkable)
        r["_diseases_seen"] = sorted({
            w["disease"] for w in checkable
            if any(k.lower() in blob for k in w["keywords"])
        })

    total_hits = 0
    for r in results:
        total_hits += r.get("keyword_hits", 0)
        r.pop("_all_titles", None)

    active_feeds = [r for r in results if r.get("status") == "ok"]

    # ── 재난 감시창이 열린 나라는 문턱을 낮춘다 (2026-08-28) ──────────────
    # 재난이 나면 그 나라 발병 보도는 '평시의 같은 양' 보다 무겁게 봐야 한다.
    # 어느 피드가 왜 낮은 문턱으로 걸렸는지는 피드에 그대로 실어 둔다 —
    # 문턱이 조용히 달라지면 고경보 수를 아무도 해석할 수 없게 된다.
    windows = watch_windows or {}
    watch_promoted = 0
    for r in active_feeds:
        iso3 = _feed_iso3(r.get("slug", ""))
        if iso3 and iso3 in windows:
            seen = r.pop("_diseases_seen", [])
            checkable = r.pop("_window_checkable", False)
            r["watch_window"] = {
                "country_iso3": iso3,
                "diseases": sorted({w["disease"] for w in windows[iso3]}),
                "disasters": sorted({w["disaster_type"] for w in windows[iso3]}),
                "min_days_since_disaster": min(w["days_since_disaster"] for w in windows[iso3]),
                # 창에 든 질병 중 **실제로 보도에 나타난** 것.
                "diseases_seen": seen,
                # 창은 열렸는데 창 안 질병이 하나도 안 보인다 = 다른 게 오고 있다.
                # 키워드가 없어 대조할 수 없으면 **모른다** 이지 창 밖이 아니다.
                "off_window": checkable and not seen,
                "window_checkable": checkable,
            }

    high_alert = []
    too_few_items: list[str] = []
    # ★ 몇 개인지만으로는 부족하다 ★ 조기경보에서 "5개가 올라왔다"보다
    # "네팔·중국이 올라왔다"가 훨씬 쓸모 있는 정보다. 어느 나라인지 안 남기면
    # 로그를 보는 사람이 매번 API를 따로 뒤져야 한다 — GroqWatch 가
    # "0개 공항 확인" 한 줄만 남겨서 열흘을 헤맸던 것과 같은 모양이다.
    watch_promoted_countries: list[str] = []
    # 창이 열린 나라에서 고경보가 났는데 창 안 질병은 안 보이는 경우.
    # "예상한 게 왔다" 와 "다른 게 왔다" 를 한 덩어리로 두면 둘 다 못 읽는다.
    off_window_signals: list[dict] = []
    for r in active_feeds:
        ratio = r.get("llm_hit_ratio", r.get("hit_ratio", 0))
        watched = "watch_window" in r
        scoped = r["slug"] in COUNTRY_TERMS
        r["country_scoped"] = scoped

        # ① 다른 피드와 같은 기사를 받고 있으면 그 나라 신호가 아니다
        if "duplicate_of" in r:
            continue
        # ② 표본이 너무 적으면 판정하지 않는다
        if r.get("item_count", 0) < MIN_ITEMS_FOR_ALERT:
            too_few_items.append(r["slug"])
            continue

        normal = SCOPED_ALERT_THRESHOLD if scoped else ALERT_THRESHOLD
        threshold = ((SCOPED_WATCH_ALERT_THRESHOLD if scoped else WATCH_ALERT_THRESHOLD)
                     if watched else normal)
        if ratio < threshold:
            continue
        if watched and ratio < normal:
            # 평시 문턱이었으면 안 걸렸을 피드 — 감시창 때문에 올라온 것이다.
            r["alert_basis"] = "disaster_watch_window"
            watch_promoted += 1
            iso = r["watch_window"]["country_iso3"]
            if iso not in watch_promoted_countries:
                watch_promoted_countries.append(iso)
        if watched and r["watch_window"]["off_window"]:
            # 고경보로 올라온 피드인데 창 안 질병이 안 보인다 → 창 밖 신호다.
            off_window_signals.append({
                "slug": r["slug"],
                "country_iso3": r["watch_window"]["country_iso3"],
                "expected": r["watch_window"]["diseases"],
                "hit_ratio": r.get("llm_hit_ratio", r.get("hit_ratio")),
            })
        high_alert.append(r)

    classified = sum(1 for r in results if "llm_hit_ratio" in r)

    # ★ 부분 성공을 성공으로만 적지 않는다 (2026-08-30) ★
    # 응답이 잘려도 답받은 데까지는 쓴다. 그건 0개보다 낫지만, 커버가 반토막
    # 났다는 사실 자체는 보여야 한다 — 안 보이면 "12개 피드" 가 몇 주씩 이어져도
    # 아무도 이상하다고 못 느낀다.
    answered = next((r.get("llm_answered_titles") for r in results
                     if r.get("llm_answered_titles") is not None), None)
    sent = next((r.get("llm_sent_titles") for r in results
                 if r.get("llm_sent_titles") is not None), None)

    return {
        "total_feeds":     len(LOCAL_FEEDS),
        "active_feeds":    len(active_feeds),
        # ↓ 왜 죽었는지. 피드마다 reason 은 이미 있었지만 아무도 안 읽었다 —
        #   2026-09-19 에 179개가 전멸했을 때 로그엔 "0/179" 만 찍혔다.
        "failure_summary": failure_summary(results),
        # ↓ 프로브 시도 횟수·조절 여부·Retry-After. 막힘이 몇 분짜리인지 읽는 자리.
        "fetch_probe":     fetch_probe,
        "total_kw_hits":   total_hits,
        "high_alert_feeds": len(high_alert),
        "high_alert":      high_alert,
        "feeds":           results,
        # ↓ 고경보가 무엇을 기준으로 나온 값인지 — 숨기지 않는다
        "llm_classified_feeds": classified,
        "llm_failure_reason":   llm_reason if classified == 0 else None,
        "high_alert_basis":     "llm" if classified else "keyword",
        # ↓ 보낸 제목 중 몇 개를 실제로 답받았는지. 둘이 다르면 응답이 잘린 것이다.
        "llm_answered_titles":  answered,
        "llm_sent_titles":      sent,
        "llm_provider":         next(
            (r.get("llm_provider") for r in results if r.get("llm_provider")), None),
        # ↓ 쓴 토큰. NewsWatch 와 같은 GROQ_API_KEY·같은 분당 한도를 나눠 쓰는데
        #   이쪽만 숫자가 없어서 한도 여유를 읽을 수 없었다. 서버가 usage 를
        #   안 주면 None 이다 — 0 이 아니다.
        "llm_total_tokens":     next(
            (r.get("llm_total_tokens") for r in results
             if isinstance(r.get("llm_total_tokens"), int)), None),
        "llm_prompt_tokens":    next(
            (r.get("llm_prompt_tokens") for r in results
             if isinstance(r.get("llm_prompt_tokens"), int)), None),
        # ↓ 감시창이 실제로 무엇을 바꿨는지. 0 이면 '창은 열렸지만 아무것도
        #   끌어올리지 못했다' 는 뜻이고, 그것도 알 가치가 있는 사실이다.
        # ── 되돌림·표본 상태 (2026-08-31) ─────────────────────────────
        # 예전엔 "179/179개 피드" 라고만 보고해서 179개국을 보는 것처럼 읽혔다.
        # 실제로는 절반 넘게 같은 기사를 받고 있었다.
        "duplicate_feed_groups":  duplicate_groups,
        "duplicated_feeds":       len(duplicated),
        "distinct_feed_sets":     len(_by_titles),
        "country_scoped_feeds":   len(COUNTRY_TERMS),
        "too_few_items_feeds":    sorted(too_few_items),
        "min_items_for_alert":    MIN_ITEMS_FOR_ALERT,
        "scoped_alert_threshold": SCOPED_ALERT_THRESHOLD,
        "watch_window_countries": len(windows),
        "watch_promoted_feeds":   watch_promoted,
        # ↓ 어느 나라가 감시창 덕에 올라왔는지. 수집 로그가 이걸 그대로 찍는다.
        "watch_promoted_countries": sorted(watch_promoted_countries),
        # ★ 창 밖 신호 ★ 감시창이 열린 나라인데 창 안 질병은 안 보이고 다른
        # 것이 올라온 경우. 실측(2026-09-01): 네팔 홍수 창(콜레라·렙토스피라)이
        # 열린 채로 조류독감이 번지고 있었다. 감시창이 틀린 게 아니라 **다른
        # 것이 온 것**이고, 그 사실 자체가 봐야 할 신호다.
        "off_window_signals": off_window_signals,
        "alert_threshold":        ALERT_THRESHOLD,
        "watch_alert_threshold":  WATCH_ALERT_THRESHOLD,
        # 낮춘 문턱(0.08)은 임의값이다 — 근거처럼 인용되지 않게 못박는다.
        "threshold_calibrated":   False,
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

"""병명·국가명의 언어별 표기.

왜 필요한가(실측 2026-08-06): 브리핑을 영어·프랑스어로 생성해도 **병명과 국가명은
한국어로 남았다.** 실제 출력이 이랬다:
    "watching 오즈 바이러스 signal in 한국"
    "surveillance du signal de 원인 미상의 폐렴·중증 호흡기 질환 en 한국"
문장만 번역하고 그 안에 박히는 고유명사를 놔두면, 읽는 사람에게는 번역이 안 된
것과 같다. 신호 원문이 한국어 소스에서 오기 때문에 생기는 문제라 여기서 표기만
바꾼다 — 데이터를 고치는 게 아니라 표시를 고치는 것이다.

★ 정직성 ★
사전에 없는 이름은 **원문을 그대로 둔다.** 어설프게 옮기면 '에볼라(Bundibugyo)'가
다른 병으로 읽히는 식의 사고가 난다. 원문이 남아 있으면 최소한 검색은 되고,
번역이 빠졌다는 사실도 눈에 보인다.
"""
from __future__ import annotations

import re

# ── 병명 ──────────────────────────────────────────────────────────
# 키는 소문자·공백 정규화한 표기. 한 질병의 여러 표기를 같은 항목으로 모은다.
# (실측에서 '에볼라', 'Ebola', '이볼라', '에볼라 출혈열'이 모두 등장했다.)
_DISEASE: dict[str, dict[str, str]] = {
    "에볼라": {"ko": "에볼라", "en": "Ebola", "fr": "Ebola"},
    "이볼라": {"ko": "에볼라", "en": "Ebola", "fr": "Ebola"},
    "ebola": {"ko": "에볼라", "en": "Ebola", "fr": "Ebola"},
    "에볼라 출혈열": {"ko": "에볼라 출혈열", "en": "Ebola haemorrhagic fever",
                 "fr": "fièvre hémorragique Ebola"},
    "마르부르크": {"ko": "마르부르크", "en": "Marburg", "fr": "Marburg"},
    "marburg": {"ko": "마르부르크", "en": "Marburg", "fr": "Marburg"},
    "니파바이러스": {"ko": "니파바이러스", "en": "Nipah virus", "fr": "virus Nipah"},
    "니파": {"ko": "니파바이러스", "en": "Nipah virus", "fr": "virus Nipah"},
    "nipah": {"ko": "니파바이러스", "en": "Nipah virus", "fr": "virus Nipah"},
    "라싸열": {"ko": "라싸열", "en": "Lassa fever", "fr": "fièvre de Lassa"},
    "lassa fever": {"ko": "라싸열", "en": "Lassa fever", "fr": "fièvre de Lassa"},
    "엠폭스": {"ko": "엠폭스", "en": "mpox", "fr": "mpox"},
    "mpox": {"ko": "엠폭스", "en": "mpox", "fr": "mpox"},
    "monkeypox": {"ko": "엠폭스", "en": "mpox", "fr": "mpox"},
    "홍역": {"ko": "홍역", "en": "measles", "fr": "rougeole"},
    "measles": {"ko": "홍역", "en": "measles", "fr": "rougeole"},
    "콜레라": {"ko": "콜레라", "en": "cholera", "fr": "choléra"},
    "cholera": {"ko": "콜레라", "en": "cholera", "fr": "choléra"},
    "뎅기열": {"ko": "뎅기열", "en": "dengue", "fr": "dengue"},
    "뎅기": {"ko": "뎅기열", "en": "dengue", "fr": "dengue"},
    "dengue": {"ko": "뎅기열", "en": "dengue", "fr": "dengue"},
    "말라리아": {"ko": "말라리아", "en": "malaria", "fr": "paludisme"},
    "malaria": {"ko": "말라리아", "en": "malaria", "fr": "paludisme"},
    "mers": {"ko": "메르스", "en": "MERS", "fr": "MERS"},
    "메르스": {"ko": "메르스", "en": "MERS", "fr": "MERS"},
    "covid-19": {"ko": "코로나19", "en": "COVID-19", "fr": "COVID-19"},
    "코로나19": {"ko": "코로나19", "en": "COVID-19", "fr": "COVID-19"},
    "한타바이러스": {"ko": "한타바이러스", "en": "hantavirus", "fr": "hantavirus"},
    "hantavirus": {"ko": "한타바이러스", "en": "hantavirus", "fr": "hantavirus"},
    "안데스바이러스": {"ko": "안데스바이러스", "en": "Andes virus", "fr": "virus Andes"},
    "오즈 바이러스": {"ko": "오즈 바이러스", "en": "Oz virus", "fr": "virus Oz"},
    "황열": {"ko": "황열", "en": "yellow fever", "fr": "fièvre jaune"},
    "yellow fever": {"ko": "황열", "en": "yellow fever", "fr": "fièvre jaune"},
    "디프테리아": {"ko": "디프테리아", "en": "diphtheria", "fr": "diphtérie"},
    "수막염": {"ko": "수막염", "en": "meningitis", "fr": "méningite"},
    "소아마비": {"ko": "소아마비", "en": "polio", "fr": "poliomyélite"},
    "결핵": {"ko": "결핵", "en": "tuberculosis", "fr": "tuberculose"},
    "조류인플루엔자": {"ko": "조류인플루엔자", "en": "avian influenza", "fr": "grippe aviaire"},
    "h5n1": {"ko": "H5N1", "en": "H5N1", "fr": "H5N1"},
    "치쿤구니야": {"ko": "치쿤구니야", "en": "chikungunya", "fr": "chikungunya"},
    "지카": {"ko": "지카", "en": "Zika", "fr": "Zika"},
}

# 원인 불명 계열 — 표기가 매번 달라 정확일치가 안 되므로 패턴으로 잡는다.
_UNKNOWN_PATTERN = re.compile(r"원인\s*(불명|미상)|unspecified|unknown|미상")
_UNKNOWN = {
    "ko": "원인불명 질환",
    "en": "disease of unknown cause",
    "fr": "maladie d’origine inconnue",
}

# 에볼라 하위 계통(붕디부교 등)은 괄호 안 표기가 제각각이라 별도로 잡는다.
_BUNDIBUGYO = re.compile(r"bundibugyo|붕디부[고교]", re.I)
_BUNDIBUGYO_NAME = {
    "ko": "에볼라(붕디부교형)",
    "en": "Ebola (Bundibugyo)",
    "fr": "Ebola (Bundibugyo)",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def disease_name(raw: str | None, lang: str) -> str | None:
    """병명을 해당 언어 표기로. 모르는 이름은 **원문 그대로** 돌려준다."""
    if not raw:
        return raw
    if _BUNDIBUGYO.search(raw):
        return _BUNDIBUGYO_NAME.get(lang, raw)
    key = _norm(raw)
    hit = _DISEASE.get(key)
    if hit:
        return hit.get(lang, raw)
    if _UNKNOWN_PATTERN.search(key):
        return _UNKNOWN.get(lang, raw)
    # 부분일치 — "에볼라(Bundibugyo virus)"처럼 꼬리가 붙은 경우.
    for name, table in _DISEASE.items():
        if len(name) >= 3 and name in key:
            return table.get(lang, raw)
    return raw


# ── 국가명 ────────────────────────────────────────────────────────
# 아이기론이 실제로 다루는 지역 위주. 프랑스어를 넣은 이유가 불어권 아프리카라
# 그쪽을 먼저 채웠다. 없는 나라는 World Bank 영문명으로 폴백한다.
_COUNTRY: dict[str, dict[str, str]] = {
    "COD": {"ko": "콩고민주공화국", "en": "DR Congo", "fr": "RD Congo"},
    "COG": {"ko": "콩고공화국", "en": "Republic of the Congo", "fr": "République du Congo"},
    "UGA": {"ko": "우간다", "en": "Uganda", "fr": "Ouganda"},
    "KEN": {"ko": "케냐", "en": "Kenya", "fr": "Kenya"},
    "TZA": {"ko": "탄자니아", "en": "Tanzania", "fr": "Tanzanie"},
    "RWA": {"ko": "르완다", "en": "Rwanda", "fr": "Rwanda"},
    "BDI": {"ko": "부룬디", "en": "Burundi", "fr": "Burundi"},
    "ETH": {"ko": "에티오피아", "en": "Ethiopia", "fr": "Éthiopie"},
    "SOM": {"ko": "소말리아", "en": "Somalia", "fr": "Somalie"},
    "SSD": {"ko": "남수단", "en": "South Sudan", "fr": "Soudan du Sud"},
    "SDN": {"ko": "수단", "en": "Sudan", "fr": "Soudan"},
    "TCD": {"ko": "차드", "en": "Chad", "fr": "Tchad"},
    "NER": {"ko": "니제르", "en": "Niger", "fr": "Niger"},
    "NGA": {"ko": "나이지리아", "en": "Nigeria", "fr": "Nigéria"},
    "GHA": {"ko": "가나", "en": "Ghana", "fr": "Ghana"},
    "GIN": {"ko": "기니", "en": "Guinea", "fr": "Guinée"},
    "GNB": {"ko": "기니비사우", "en": "Guinea-Bissau", "fr": "Guinée-Bissau"},
    "GNQ": {"ko": "적도기니", "en": "Equatorial Guinea", "fr": "Guinée équatoriale"},
    "LBR": {"ko": "라이베리아", "en": "Liberia", "fr": "Liberia"},
    "SLE": {"ko": "시에라리온", "en": "Sierra Leone", "fr": "Sierra Leone"},
    "SEN": {"ko": "세네갈", "en": "Senegal", "fr": "Sénégal"},
    "MLI": {"ko": "말리", "en": "Mali", "fr": "Mali"},
    "BFA": {"ko": "부르키나파소", "en": "Burkina Faso", "fr": "Burkina Faso"},
    "CIV": {"ko": "코트디부아르", "en": "Côte d’Ivoire", "fr": "Côte d’Ivoire"},
    "TGO": {"ko": "토고", "en": "Togo", "fr": "Togo"},
    "BEN": {"ko": "베냉", "en": "Benin", "fr": "Bénin"},
    "CMR": {"ko": "카메룬", "en": "Cameroon", "fr": "Cameroun"},
    "CAF": {"ko": "중앙아프리카공화국", "en": "Central African Republic",
            "fr": "République centrafricaine"},
    "GAB": {"ko": "가봉", "en": "Gabon", "fr": "Gabon"},
    "AGO": {"ko": "앙골라", "en": "Angola", "fr": "Angola"},
    "ZMB": {"ko": "잠비아", "en": "Zambia", "fr": "Zambie"},
    "ZWE": {"ko": "짐바브웨", "en": "Zimbabwe", "fr": "Zimbabwe"},
    "MWI": {"ko": "말라위", "en": "Malawi", "fr": "Malawi"},
    "MOZ": {"ko": "모잠비크", "en": "Mozambique", "fr": "Mozambique"},
    "ZAF": {"ko": "남아프리카공화국", "en": "South Africa", "fr": "Afrique du Sud"},
    "MDG": {"ko": "마다가스카르", "en": "Madagascar", "fr": "Madagascar"},
    "EGY": {"ko": "이집트", "en": "Egypt", "fr": "Égypte"},
    "MAR": {"ko": "모로코", "en": "Morocco", "fr": "Maroc"},
    "DZA": {"ko": "알제리", "en": "Algeria", "fr": "Algérie"},
    "TUN": {"ko": "튀니지", "en": "Tunisia", "fr": "Tunisie"},
    "LBY": {"ko": "리비아", "en": "Libya", "fr": "Libye"},
    "KOR": {"ko": "한국", "en": "South Korea", "fr": "Corée du Sud"},
    "PRK": {"ko": "북한", "en": "North Korea", "fr": "Corée du Nord"},
    "JPN": {"ko": "일본", "en": "Japan", "fr": "Japon"},
    "HKG": {"ko": "홍콩", "en": "Hong Kong", "fr": "Hong Kong"},
    "TWN": {"ko": "대만", "en": "Taiwan", "fr": "Taïwan"},
    "SGP": {"ko": "싱가포르", "en": "Singapore", "fr": "Singapour"},
    "MYS": {"ko": "말레이시아", "en": "Malaysia", "fr": "Malaisie"},
    "MMR": {"ko": "미얀마", "en": "Myanmar", "fr": "Birmanie"},
    "LAO": {"ko": "라오스", "en": "Laos", "fr": "Laos"},
    "NPL": {"ko": "네팔", "en": "Nepal", "fr": "Népal"},
    "LKA": {"ko": "스리랑카", "en": "Sri Lanka", "fr": "Sri Lanka"},
    "AFG": {"ko": "아프가니스탄", "en": "Afghanistan", "fr": "Afghanistan"},
    "ARE": {"ko": "아랍에미리트", "en": "United Arab Emirates", "fr": "Émirats arabes unis"},
    "PER": {"ko": "페루", "en": "Peru", "fr": "Pérou"},
    "COL": {"ko": "콜롬비아", "en": "Colombia", "fr": "Colombie"},
    "MEX": {"ko": "멕시코", "en": "Mexico", "fr": "Mexique"},
    "ERI": {"ko": "에리트레아", "en": "Eritrea", "fr": "Érythrée"},
    "DJI": {"ko": "지부티", "en": "Djibouti", "fr": "Djibouti"},
    "MRT": {"ko": "모리타니", "en": "Mauritania", "fr": "Mauritanie"},
    "NAM": {"ko": "나미비아", "en": "Namibia", "fr": "Namibie"},
    "BWA": {"ko": "보츠와나", "en": "Botswana", "fr": "Botswana"},
    "GMB": {"ko": "감비아", "en": "Gambia", "fr": "Gambie"},
    "CHN": {"ko": "중국", "en": "China", "fr": "Chine"},
    "IND": {"ko": "인도", "en": "India", "fr": "Inde"},
    "PAK": {"ko": "파키스탄", "en": "Pakistan", "fr": "Pakistan"},
    "BGD": {"ko": "방글라데시", "en": "Bangladesh", "fr": "Bangladesh"},
    "VNM": {"ko": "베트남", "en": "Vietnam", "fr": "Viêt Nam"},
    "KHM": {"ko": "캄보디아", "en": "Cambodia", "fr": "Cambodge"},
    "PHL": {"ko": "필리핀", "en": "Philippines", "fr": "Philippines"},
    "IDN": {"ko": "인도네시아", "en": "Indonesia", "fr": "Indonésie"},
    "THA": {"ko": "태국", "en": "Thailand", "fr": "Thaïlande"},
    "SAU": {"ko": "사우디아라비아", "en": "Saudi Arabia", "fr": "Arabie saoudite"},
    "YEM": {"ko": "예멘", "en": "Yemen", "fr": "Yémen"},
    "IRQ": {"ko": "이라크", "en": "Iraq", "fr": "Irak"},
    "IRN": {"ko": "이란", "en": "Iran", "fr": "Iran"},
    "BRA": {"ko": "브라질", "en": "Brazil", "fr": "Brésil"},
    "ARG": {"ko": "아르헨티나", "en": "Argentina", "fr": "Argentine"},
    "HTI": {"ko": "아이티", "en": "Haiti", "fr": "Haïti"},
    "USA": {"ko": "미국", "en": "United States", "fr": "États-Unis"},
    "GBR": {"ko": "영국", "en": "United Kingdom", "fr": "Royaume-Uni"},
    "FRA": {"ko": "프랑스", "en": "France", "fr": "France"},
    "DEU": {"ko": "독일", "en": "Germany", "fr": "Allemagne"},
    "WSM": {"ko": "사모아", "en": "Samoa", "fr": "Samoa"},
    "PNG": {"ko": "파푸아뉴기니", "en": "Papua New Guinea", "fr": "Papouasie-Nouvelle-Guinée"},
}


def country_name(iso3: str | None, lang: str, fallback: str | None = None) -> str:
    """ISO3 → 해당 언어 국가명. 사전에 없으면 World Bank 영문명, 그것도 없으면 코드."""
    if not iso3:
        return fallback or ""
    hit = _COUNTRY.get(iso3.upper())
    if hit and lang in hit:
        return hit[lang]
    if fallback:
        return fallback
    try:
        from .world_countries import load_world_countries
        ref = load_world_countries().get(iso3.upper())
        if ref and ref.get("name"):
            return ref["name"]
    except Exception:
        pass
    return iso3


def country_lookup(codes: list[str], lang: str, fallback: dict[str, str] | None = None) -> dict[str, str]:
    """ISO3 목록 → {코드: 언어별 이름}. daily_brief의 name_lookup을 대체한다."""
    fb = fallback or {}
    return {c: country_name(c, lang, fb.get(c)) for c in codes}


# ── 경보 라벨 ─────────────────────────────────────────────────────
# 경보 라벨은 `{신호층 이름} · {지표ID}` 꼴로 조립돼 티커에 그대로 실린다
# (예: "행동신호 · social_birdflu", "행동신호 · social_dengue 보고 급감").
# 지표ID는 이미 영문 기술 식별자라 그대로 두고, **한국어인 앞부분만** 옮긴다.
# 층 이름은 signal_metrics의 6개가 전부다.
_LAYER = {
    "공식신호": {"en": "Official signal", "fr": "Signal officiel"},
    "비공식신호": {"en": "Unofficial signal", "fr": "Signal non officiel"},
    "행동신호": {"en": "Behavioural signal", "fr": "Signal comportemental"},
    "환경신호": {"en": "Environmental signal", "fr": "Signal environnemental"},
    "동물신호": {"en": "Animal signal", "fr": "Signal animal"},
    "설명불가": {"en": "Unexplained", "fr": "Inexpliqué"},
    "설명불가 신호": {"en": "Unexplained signal", "fr": "Signal inexpliqué"},
}
# 라벨에 붙는 꼬리말·자리표시자.
_LABEL_PHRASE = {
    # 긴 조각을 먼저 등록해도 alert_label이 길이순으로 정렬해 치환하므로 순서는
    # 무관하다. 다만 '품목'처럼 짧은 조각이 긴 문구 안에 들어있으면 긴 것이
    # 먼저 치환돼야 하므로, 새 조각을 넣을 때 부분문자열 관계를 확인할 것.
    "의료물자 수입 동시 급증": {
        "en": "medical supply imports surging together",
        "fr": "importations de matériel médical en hausse simultanée",
    },
    "보고 급감": {"en": "reporting drop", "fr": "chute des déclarations"},
    "종합": {"en": "composite", "fr": "composite"},
    "지역불명": {"en": "location unknown", "fr": "localisation inconnue"},
    "질병불명": {"en": "disease unknown", "fr": "maladie inconnue"},
    "품목": {"en": "products", "fr": "produits"},
}


def alert_label(raw: str | None, lang: str) -> str | None:
    """경보 라벨의 한국어 조각을 요청 언어로. 모르는 조각은 그대로 둔다.

    라벨은 여러 모듈이 조립해 DB에도 저장되는 값이라 원본을 바꾸지 않는다 —
    표시 시점에만 옮긴다. 안 그러면 티커만 한국어로 남는다(실측으로 확인).
    """
    if not raw or lang == "ko":
        return raw
    out = raw
    # 긴 것부터 — '설명불가 신호'가 '설명불가'로 먼저 잘리지 않게.
    for ko, table in sorted(_LAYER.items(), key=lambda kv: -len(kv[0])):
        if ko in out:
            out = out.replace(ko, table.get(lang, ko))
    for ko, table in sorted(_LABEL_PHRASE.items(), key=lambda kv: -len(kv[0])):
        if ko in out:
            out = out.replace(ko, table.get(lang, ko))
    return out

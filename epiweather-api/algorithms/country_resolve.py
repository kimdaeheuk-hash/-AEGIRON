"""location 자유문장 → ISO3 국가코드 **목록**.

왜 필요한가(실측): extracted_signals 369건 중 151건이 country_iso3 없이 저장돼 있고,
2024년 이후 신호 157건 중 **150건**이 그렇다. Tier-2 학습셋은 country_iso3가 있는
신호만 쓰므로, 최근 3년 커버리지가 사실상 0이 됐다 — 전향적 평가에서 가장 최근
폴드(2023-08~2026-05)의 양성 13건이 **전부 신호창이 빈 채로** 채점돼 재현율 0.000이
나온 원인이다. 판별력 문제로 보이던 것의 상당 부분이 실은 이 해석 실패였다.

원인 두 가지:
① bulletin_ingest.iso3_for가 `[^a-z ]`를 전부 지운다 — 한글 국가명은 빈 문자열이 돼
   무조건 None이 된다("우간다" 78건, "콩고민주공화국" 58건이 이렇게 날아갔다).
② location이 다국가 문자열이다("콩고민주공화국, 우간다" 51건). nlp_extract는 ISO3를
   하나만 받도록 돼 있어 다중언급을 방어적으로 null 처리한다(nlp_extract.py:74).
   국경을 넘는 발병에서 두 나라 모두 증거인데 둘 다 잃는다.

★ 정직성 ★
- **추측하지 않는다.** 사전에 없으면 None/빈 목록이다. 잘못 붙인 국가코드는
  없는 것보다 나쁘다 — 그 나라에 없던 발병 신호를 만들어내기 때문이다.
- 국가가 아닌 것(크루즈선·'전 세계'·'서태평양'·'아프리카')은 **명시적으로 차단**한다.
  지역·선박을 국가로 승격시키면 가짜 커버리지가 생긴다.
- 긴 이름 우선 매칭 — '남수단'이 '수단'으로, '콩고민주공화국'이 '콩고'로 잘못
  떨어지지 않게 매칭한 구간을 소비한다.
"""
from __future__ import annotations
import re

# 한글 표기 → ISO3. 실제 수집 데이터에 나타난 표기를 근거로 넣고, 흔한 변형을 더한다.
_KO: dict[str, str] = {
    "콩고민주공화국": "COD", "콩고 민주공화국": "COD", "민주콩고": "COD",
    "콩고민주공화국(drc)": "COD", "콩고민주공화국(민주콩고)": "COD",
    "콩고공화국": "COG",
    "우간다": "UGA", "케냐": "KEN", "탄자니아": "TZA", "르완다": "RWA",
    "부룬디": "BDI", "에티오피아": "ETH", "소말리아": "SOM", "지부티": "DJI",
    "남수단": "SSD", "수단": "SDN", "차드": "TCD", "니제르": "NER",
    "나이지리아": "NGA", "가나": "GHA", "기니": "GIN", "기니비사우": "GNB",
    "적도기니": "GNQ", "라이베리아": "LBR", "시에라리온": "SLE", "세네갈": "SEN",
    "말리": "MLI", "부르키나파소": "BFA", "코트디부아르": "CIV", "토고": "TGO",
    "베냉": "BEN", "카메룬": "CMR", "중앙아프리카공화국": "CAF", "가봉": "GAB",
    "앙골라": "AGO", "잠비아": "ZMB", "짐바브웨": "ZWE", "말라위": "MWI",
    "모잠비크": "MOZ", "남아프리카공화국": "ZAF", "보츠와나": "BWA",
    "나미비아": "NAM", "마다가스카르": "MDG", "이집트": "EGY", "모로코": "MAR",
    "알제리": "DZA", "튀니지": "TUN", "리비아": "LBY",
    "대한민국": "KOR", "한국": "KOR", "북한": "PRK", "일본": "JPN",
    "중국": "CHN", "대만": "TWN", "홍콩": "HKG", "몽골": "MNG",
    "베트남": "VNM", "캄보디아": "KHM", "라오스": "LAO", "태국": "THA",
    "미얀마": "MMR", "말레이시아": "MYS", "싱가포르": "SGP",
    "인도네시아": "IDN", "필리핀": "PHL", "브루나이": "BRN",
    "인도": "IND", "파키스탄": "PAK", "방글라데시": "BGD", "네팔": "NPL",
    "스리랑카": "LKA", "아프가니스탄": "AFG",
    "사우디아라비아": "SAU", "아랍에미리트": "ARE", "카타르": "QAT",
    "쿠웨이트": "KWT", "오만": "OMN", "예멘": "YEM", "이라크": "IRQ",
    "이란": "IRN", "요르단": "JOR", "레바논": "LBN", "시리아": "SYR",
    "이스라엘": "ISR", "튀르키예": "TUR", "터키": "TUR",
    "미국": "USA", "캐나다": "CAN", "멕시코": "MEX", "브라질": "BRA",
    "아르헨티나": "ARG", "칠레": "CHL", "페루": "PER", "콜롬비아": "COL",
    "볼리비아": "BOL", "에콰도르": "ECU", "베네수엘라": "VEN",
    "아이티": "HTI", "도미니카공화국": "DOM", "도미니카 공화국": "DOM",
    "쿠바": "CUB", "자메이카": "JAM",
    "영국": "GBR", "프랑스": "FRA", "독일": "DEU", "이탈리아": "ITA",
    "스페인": "ESP", "포르투갈": "PRT", "네덜란드": "NLD", "벨기에": "BEL",
    "스위스": "CHE", "오스트리아": "AUT", "스웨덴": "SWE", "노르웨이": "NOR",
    "덴마크": "DNK", "핀란드": "FIN", "폴란드": "POL", "러시아": "RUS",
    "우크라이나": "UKR", "그리스": "GRC",
    "호주": "AUS", "뉴질랜드": "NZL", "파푸아뉴기니": "PNG", "피지": "FJI",
    "사모아": "WSM", "통가": "TON", "바누아투": "VUT",
}

# 영문 표기 → ISO3. bulletin_ingest._ISO3와 겹치지만 여기서 단일 출처로 관리한다.
_EN: dict[str, str] = {
    "democratic republic of the congo": "COD", "democratic republic of congo": "COD",
    "dr congo": "COD", "drc": "COD", "congo dem rep": "COD",
    "republic of congo": "COG", "congo": "COG",
    "uganda": "UGA", "kenya": "KEN", "tanzania": "TZA",
    "united republic of tanzania": "TZA", "rwanda": "RWA", "burundi": "BDI",
    "ethiopia": "ETH", "somalia": "SOM", "djibouti": "DJI",
    "south sudan": "SSD", "sudan": "SDN", "chad": "TCD", "niger": "NER",
    "nigeria": "NGA", "ghana": "GHA", "guinea bissau": "GNB", "guinea": "GIN",
    "equatorial guinea": "GNQ", "liberia": "LBR", "sierra leone": "SLE",
    "senegal": "SEN", "mali": "MLI", "burkina faso": "BFA", "burkina": "BFA",
    "cote d ivoire": "CIV", "ivory coast": "CIV", "togo": "TGO", "benin": "BEN",
    "cameroon": "CMR", "central african republic": "CAF", "gabon": "GAB",
    "angola": "AGO", "zambia": "ZMB", "zimbabwe": "ZWE", "malawi": "MWI",
    "mozambique": "MOZ", "south africa": "ZAF", "botswana": "BWA",
    "namibia": "NAM", "madagascar": "MDG", "egypt": "EGY", "morocco": "MAR",
    "algeria": "DZA", "tunisia": "TUN", "libya": "LBY", "mauritania": "MRT",
    "mauritius": "MUS", "seychelles": "SYC", "comoros": "COM", "eritrea": "ERI",
    "eswatini": "SWZ", "lesotho": "LSO", "gambia": "GMB", "cabo verde": "CPV",
    "sao tome and principe": "STP",
    "south korea": "KOR", "republic of korea": "KOR", "korea": "KOR",
    "north korea": "PRK", "japan": "JPN", "china": "CHN", "taiwan": "TWN",
    "hong kong": "HKG", "mongolia": "MNG", "viet nam": "VNM", "vietnam": "VNM",
    "cambodia": "KHM", "laos": "LAO", "thailand": "THA", "myanmar": "MMR",
    "malaysia": "MYS", "singapore": "SGP", "indonesia": "IDN",
    "philippines": "PHL", "brunei": "BRN",
    "india": "IND", "pakistan": "PAK", "bangladesh": "BGD", "nepal": "NPL",
    "sri lanka": "LKA", "afghanistan": "AFG",
    "saudi arabia": "SAU", "united arab emirates": "ARE", "qatar": "QAT",
    "kuwait": "KWT", "oman": "OMN", "yemen": "YEM", "iraq": "IRQ",
    "iran": "IRN", "jordan": "JOR", "lebanon": "LBN", "syria": "SYR",
    "israel": "ISR", "turkiye": "TUR", "turkey": "TUR",
    "united states": "USA", "usa": "USA", "canada": "CAN", "mexico": "MEX",
    "brazil": "BRA", "argentina": "ARG", "chile": "CHL", "peru": "PER",
    "colombia": "COL", "bolivia": "BOL", "ecuador": "ECU", "venezuela": "VEN",
    "haiti": "HTI", "dominican republic": "DOM", "cuba": "CUB", "jamaica": "JAM",
    "united kingdom": "GBR", "uk": "GBR", "england": "GBR", "france": "FRA",
    "germany": "DEU", "italy": "ITA", "spain": "ESP", "portugal": "PRT",
    "netherlands": "NLD", "belgium": "BEL", "switzerland": "CHE",
    "austria": "AUT", "sweden": "SWE", "norway": "NOR", "denmark": "DNK",
    "finland": "FIN", "poland": "POL", "russia": "RUS", "ukraine": "UKR",
    "greece": "GRC",
    "australia": "AUS", "new zealand": "NZL", "papua new guinea": "PNG",
    "fiji": "FJI", "samoa": "WSM", "tonga": "TON", "vanuatu": "VUT",
}

# 국가가 아닌 것 — 여기 걸리면 그 조각은 통째로 버린다. 지역·선박·다국가 요약을
# 국가로 승격시키면 있지도 않은 커버리지가 생긴다("전 세계"를 어느 나라로 볼 것인가).
_NOT_A_COUNTRY = re.compile(
    r"크루즈|선박|여객선|cruise|ship|vessel|"
    r"전\s*세계|전세계|worldwide|global|전지구|"
    r"아프리카(?!\s*공화국)|africa(?!n\s+republic)|"
    r"서태평양|서부태평양|남태평양|태평양|western\s+pacific|pacific|"
    r"유럽|europe|아시아|asia|중동|middle\s+east|아메리카|americas|"
    r"대서양|atlantic|인도양|"
    r"who\s|국제|international|"
    r"\d+\s*개국|multiple\s+countries|several\s+countries",
    re.I,
)

# 조각 분리자 — 쉼표·슬래시·가운뎃점·괄호·'및/과/와/그리고/and'
_SPLIT = re.compile(r"[,/·;()]|\band\b|및|그리고|\s와\s|\s과\s", re.I)


def _normalize_en(text: str) -> str:
    t = re.sub(r"[^a-z ]+", " ", text.lower())
    return re.sub(r"\s+", " ", t).strip()


def _match_fragment(frag: str) -> str | None:
    """한 조각에서 국가 하나. 못 찾으면 None(추측 금지)."""
    frag = frag.strip()
    if not frag or _NOT_A_COUNTRY.search(frag):
        return None

    # 한글: 긴 이름 우선 — '남수단'이 '수단'으로 떨어지지 않게.
    # 공백을 뗀 형태도 함께 본다 — 실측에 '사우디 아라비아', '콩고 민주공화국'처럼
    # 띄어쓰기가 흔들리는 표기가 섞여 들어온다.
    lowered = frag.lower()
    nospace = re.sub(r"\s+", "", lowered)
    ko_hits = sorted((k for k in _KO if k in lowered or k.replace(" ", "") in nospace),
                     key=len, reverse=True)
    if ko_hits:
        return _KO[ko_hits[0]]

    # 영문: 정확일치 → 긴 부분일치. 짧은 키(uk, drc 등)는 단어경계로만 인정한다.
    key = _normalize_en(frag)
    if not key:
        return None
    if key in _EN:
        return _EN[key]
    long_hits = sorted((k for k in _EN if len(k) >= 6 and k in key), key=len, reverse=True)
    if long_hits:
        return _EN[long_hits[0]]
    for k in sorted((k for k in _EN if len(k) < 6), key=len, reverse=True):
        if re.search(rf"\b{re.escape(k)}\b", key):
            return _EN[k]
    return None


def resolve_countries(location: str | None) -> list[str]:
    """location 자유문장 → 언급된 모든 ISO3(등장 순서, 중복 제거).

    다국가를 살리는 이유: 국경을 넘는 발병에서 "콩고민주공화국, 우간다"는 두 나라
    모두에 대한 증거다. 하나만 남기면 나머지 나라의 조기신호를 통째로 잃는다."""
    if not location:
        return []
    out: list[str] = []
    for frag in _SPLIT.split(str(location)):
        iso = _match_fragment(frag)
        if iso and iso not in out:
            out.append(iso)
    return out


def resolve_country(location: str | None) -> str | None:
    """대표 국가 하나(첫 번째). 단일 컬럼(country_iso3)에 넣을 때 쓴다."""
    found = resolve_countries(location)
    return found[0] if found else None


def signal_countries(signal: dict) -> list[str]:
    """신호 레코드가 가리키는 국가 목록.

    저장된 country_iso3를 우선하되, location에서 추가로 읽히는 나라를 합친다 —
    기존 레코드는 국가가 하나만 박혀 있어 국경을 넘는 발병의 반대편을 잃고 있다."""
    out: list[str] = []
    stored = signal.get("country_iso3")
    if isinstance(stored, str) and len(stored) == 3 and stored.isalpha():
        out.append(stored.upper())
    for iso in resolve_countries(signal.get("location")):
        if iso not in out:
            out.append(iso)
    return out

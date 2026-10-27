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

# ISO3 → 한글 표기(표시용). _KO 에서 **처음 나온 표기**가 표준형이다(대한민국·튀르키예·
# 콩고민주공화국 — 변형은 뒤에 적혀 있다). 보고서처럼 사람이 읽는 화면이 영문 이름
# ('Russian Federation')과 한글 이름을 섞어 쓰지 않게 한다(2026-10-19).
_ISO3_TO_KO: dict[str, str] = {}
for _name, _iso3 in _KO.items():
    _ISO3_TO_KO.setdefault(_iso3, _name)


def korean_name(iso3: str | None) -> str | None:
    """ISO3 → 한글 국가명. 표에 없으면 None — 지어내지 않고 호출부가 원래 이름을 쓴다."""
    return _ISO3_TO_KO.get(iso3) if iso3 else None


# 영문 표기 → ISO3. bulletin_ingest._ISO3와 겹치지만 여기서 단일 출처로 관리한다.
_EN: dict[str, str] = {
    "democratic republic of the congo": "COD", "democratic republic of congo": "COD",
    "dr congo": "COD", "drc": "COD", "congo dem rep": "COD",
    "republic of congo": "COG", "congo": "COG",
    # ★ 괄호로 두 콩고를 가르는 표기 ★ 조각 분리자가 괄호에서 먼저 쪼개는 바람에
    # "Congo (Kinshasa)" 가 앞 조각 "Congo" 만 보고 COG(콩고공화국)로 갔다.
    # 킨샤사는 COD(콩고민주공화국) 수도다 — 에볼라 발원지를 이웃 나라로 붙이던 셈.
    # 아래 두 줄은 쪼개기 **전에** 전체 문자열로 정확히 맞춰본다(resolve_countries).
    "congo kinshasa": "COD", "congo brazzaville": "COG",
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
    # ★ (?<!south ) 가 없으면 South Africa 가 통째로 버려진다 (2026-08-31 실측) ★
    # 한글 '남아프리카공화국'은 뒤의 '공화국' 덕에 살아남는데 영문 'South Africa'는
    # 대륙 언급으로 오인돼 조용히 사라졌다. 영문 기사·WHO 문서가 주 입력인데
    # 남아공이 안 잡히면 조기경보에 큰 구멍이다.
    # 'southern africa'(지역 표현)는 그대로 막힌다 — 앞 6글자가 'thern '이 아니라
    # 'south '일 때만 예외로 둔다.
    r"아프리카(?!\s*공화국)|(?<!south )africa(?!n\s+republic)|"
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


# 괄호로 나라를 가르는 표기 — 쪼개면 뜻이 바뀌므로 미리 표준 이름으로 바꾼다.
# ★ 실측 (2026-08-31) ★ 항공 노선 데이터의 국가명이 "Congo (Kinshasa)" 였는데
# 앞 조각 "Congo" 만 보고 COG(콩고공화국)로 갔다. 킨샤사는 COD(콩고민주공화국)
# 수도다 — 에볼라 발원지를 이웃 나라에 붙이고 있었던 셈이다.
_PAREN_FORMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"congo\s*\(\s*kinshasa\s*\)", re.I),     "DR Congo"),
    (re.compile(r"congo\s*\(\s*brazzaville\s*\)", re.I),  "Republic of Congo"),
)


def _expand_paren_forms(text: str) -> str:
    for pattern, canonical in _PAREN_FORMS:
        text = pattern.sub(canonical, text)
    return text


def resolve_countries(location: str | None) -> list[str]:
    """location 자유문장 → 언급된 모든 ISO3(등장 순서, 중복 제거).

    다국가를 살리는 이유: 국경을 넘는 발병에서 "콩고민주공화국, 우간다"는 두 나라
    모두에 대한 증거다. 하나만 남기면 나머지 나라의 조기신호를 통째로 잃는다."""
    if not location:
        return []

    # 괄호 표기를 먼저 표준 이름으로 바꾼다 — 아래에서 괄호를 분리자로 쪼개기 때문에
    # 그냥 두면 "Congo (Kinshasa)" 가 앞 조각 "Congo" 만 남아 뜻이 뒤집힌다.
    text = _expand_paren_forms(str(location))

    out: list[str] = []
    for frag in _SPLIT.split(text):
        iso = _match_fragment(frag)
        if iso and iso not in out:
            out.append(iso)
    return out


def countries_in_text(text: str | None) -> list[str]:
    """긴 글(발표 본문 같은) 안의 나라를 **모두** 등장 순서로 찾는다.

    `resolve_countries` 는 위치 칸용이다 — 쉼표 등으로 조각낸 뒤 조각마다 나라 **하나**만 고르고, 크루즈·선박 같은
    말이 든 조각은 통째로 버린다. 문장에는 맞지 않는다: "아르헨티나 보건부가 크루즈선 집단발병을 알렸다" 에서
    아르헨티나가 사라진다(2026-10-25 시험에서 확인). 여기서는 사전의 영문·한글 이름을 단어 경계로 모두 찾고,
    긴 이름이 먼저 자리를 차지한다(`South Sudan` 이 `Sudan` 으로, `Niger` 가 `Nigeria` 안에서 잡히지 않게)."""
    out: list[str] = []
    for _, _, iso, _ in country_mentions(text):
        if iso not in out:
            out.append(iso)
    return out


def country_mentions(text: str | None) -> list[tuple[int, int, str, str]]:
    """countries_in_text 의 근거 — 찾은 자리마다 (시작, 끝, ISO3, 찾은 글자열), 등장 순서.

    위치는 괄호 표기를 펼치고 소문자·하이픈을 띄어쓰기로 바꾼 글 기준이다(괄호 표기가 있으면 원문과 몇 글자 어긋날 수
    있다). 원문에서 자리를 찾을 땐 찾은 글자열로 다시 찾는다(who_don_declarations.evidence_window)."""
    if not text:
        return []
    found: list[tuple[int, int, str, str]] = []
    taken: list[tuple[int, int]] = []

    # 하이픈은 띄어쓰기로 — `Guinea-Bissau` 가 사전의 `guinea bissau` 로 읽히게. 글자 수는 그대로라 위치가 안 흔들린다.
    lowered = re.sub(r"[-–—]", " ", _expand_paren_forms(text).lower())

    def claim(start: int, end: int, iso: str) -> None:
        if any(start < b and a < end for a, b in taken):
            return
        taken.append((start, end))
        found.append((start, end, iso, lowered[start:end]))

    for key in sorted(_EN, key=len, reverse=True):
        pattern = r"\b" + r"\s+".join(re.escape(w) for w in key.split()) + r"\b"
        for m in re.finditer(pattern, lowered):
            claim(m.start(), m.end(), _EN[key])
    for key in sorted(_KO, key=len, reverse=True):
        for m in re.finditer(re.escape(key), lowered):
            claim(m.start(), m.end(), _KO[key])
    return sorted(found)


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


# ── ISO 3166-1 alpha-2 → alpha-3 (2026-08-28) ──────────────────────────
# 왜 여기 있나: 현지어 뉴스 피드 슬러그가 `gn_np` 처럼 **alpha-2** 인데,
# 이 시스템의 나머지 전부(country_risk·GDACS·extracted_signals)는 alpha-3 다.
# 재난 감시창(disaster_watch)이 "GDACS 가 NPL 에 홍수를 알렸다 → gn_np 피드를
# 더 예민하게 본다" 를 하려면 이 다리가 있어야 한다.
#
# ★ 네트워크에 안 묶는다 ★ world_countries 캐시(World Bank)에도 iso2 가 있지만
# 그건 네트워크로 채워지는 캐시라, 캐시가 비면 감시창이 조용히 반쪽이 된다.
# climate_signals 가 좌표를 self-contained 하게 둔 것과 같은 이유다.
#
# 수록 범위는 local_news.LOCAL_FEEDS 가 실제로 쓰는 178개 alpha-2 전부.
# `test_disaster_watch.py` 가 (1) 피드 전수 커버와 (2) 위 _KO 표와의 교차대조로
# 이 표의 오타를 잡는다 — 손으로 넣은 표는 반드시 다른 근거로 대조해야 한다.
_ISO2_TO_ISO3: dict[str, str] = {
    "AE": "ARE", "AF": "AFG", "AL": "ALB", "AM": "ARM", "AO": "AGO",
    "AR": "ARG", "AT": "AUT", "AU": "AUS", "AZ": "AZE",
    "BA": "BIH", "BB": "BRB", "BD": "BGD", "BE": "BEL", "BF": "BFA",
    "BG": "BGR", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BN": "BRN",
    "BO": "BOL", "BR": "BRA", "BS": "BHS", "BT": "BTN", "BW": "BWA",
    "BY": "BLR", "BZ": "BLZ",
    "CA": "CAN", "CD": "COD", "CF": "CAF", "CG": "COG", "CH": "CHE",
    "CI": "CIV", "CL": "CHL", "CM": "CMR", "CN": "CHN", "CO": "COL",
    "CR": "CRI", "CU": "CUB", "CV": "CPV", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DJ": "DJI", "DK": "DNK", "DO": "DOM", "DZ": "DZA",
    "EC": "ECU", "EE": "EST", "EG": "EGY", "ER": "ERI", "ES": "ESP",
    "ET": "ETH",
    "FI": "FIN", "FJ": "FJI", "FR": "FRA",
    "GA": "GAB", "GB": "GBR", "GE": "GEO", "GH": "GHA", "GM": "GMB",
    "GN": "GIN", "GQ": "GNQ", "GR": "GRC", "GT": "GTM", "GW": "GNB",
    "GY": "GUY",
    "HK": "HKG", "HN": "HND", "HR": "HRV", "HT": "HTI", "HU": "HUN",
    "ID": "IDN", "IE": "IRL", "IL": "ISR", "IN": "IND", "IQ": "IRQ",
    "IR": "IRN", "IS": "ISL", "IT": "ITA",
    "JM": "JAM", "JO": "JOR", "JP": "JPN",
    "KE": "KEN", "KG": "KGZ", "KH": "KHM", "KM": "COM", "KR": "KOR",
    "KW": "KWT", "KZ": "KAZ",
    "LA": "LAO", "LB": "LBN", "LK": "LKA", "LR": "LBR", "LS": "LSO",
    "LT": "LTU", "LU": "LUX", "LV": "LVA", "LY": "LBY",
    "MA": "MAR", "MD": "MDA", "MG": "MDG", "MK": "MKD", "ML": "MLI",
    "MM": "MMR", "MN": "MNG", "MR": "MRT", "MT": "MLT", "MU": "MUS",
    "MV": "MDV", "MW": "MWI", "MX": "MEX", "MY": "MYS", "MZ": "MOZ",
    "NA": "NAM", "NE": "NER", "NG": "NGA", "NI": "NIC", "NL": "NLD",
    "NO": "NOR", "NP": "NPL", "NZ": "NZL",
    "OM": "OMN",
    "PA": "PAN", "PE": "PER", "PG": "PNG", "PH": "PHL", "PK": "PAK",
    "PL": "POL", "PS": "PSE", "PT": "PRT", "PY": "PRY",
    "QA": "QAT",
    "RO": "ROU", "RS": "SRB", "RU": "RUS", "RW": "RWA",
    "SA": "SAU", "SB": "SLB", "SC": "SYC", "SD": "SDN", "SE": "SWE",
    "SG": "SGP", "SI": "SVN", "SK": "SVK", "SL": "SLE", "SN": "SEN",
    "SO": "SOM", "SR": "SUR", "SS": "SSD", "ST": "STP", "SV": "SLV",
    "SY": "SYR", "SZ": "SWZ",
    "TD": "TCD", "TG": "TGO", "TH": "THA", "TJ": "TJK", "TL": "TLS",
    "TM": "TKM", "TN": "TUN", "TO": "TON", "TR": "TUR", "TT": "TTO",
    "TW": "TWN", "TZ": "TZA",
    "UA": "UKR", "UG": "UGA", "US": "USA", "UY": "URY", "UZ": "UZB",
    "VE": "VEN", "VN": "VNM", "VU": "VUT",
    "WS": "WSM",
    "YE": "YEM",
    "ZA": "ZAF", "ZM": "ZMB", "ZW": "ZWE",
}


def iso2_to_iso3(code: str | None) -> str | None:
    """alpha-2 → alpha-3. 모르는 코드는 **추측하지 않고 None** 이다.

    이 모듈의 원칙 그대로다 — 잘못 붙인 국가코드는 없는 것보다 나쁘다.
    감시창에서 코드를 잘못 붙이면 사고가 안 난 나라에 감시창이 열린다.
    """
    if not code or not isinstance(code, str):
        return None
    return _ISO2_TO_ISO3.get(code.strip().upper())

"""국가 간 육로 국경 인접표 — 전 세계 (2026-08-31).

## 왜 필요한가

디지털 트윈이 항공 노선만 갖고 있어서 **이웃 나라에도 허브를 돌아서 갔다.**
실측(2026-08-27): 킨샤사(콩고) 발원인데 캄팔라(우간다)가 두바이를 거쳐
**127일째** 감염됐다 — 페르시아만이 이웃 나라보다 61일 빨랐다.

실제 발병은 국경을 걸어서 넘는다. 2014 서아프리카 에볼라(기니→라이베리아→
시에라리온), 2018 북키부 에볼라(콩고→우간다), 콜레라·홍역 모두 육로가 주경로다.

## 데이터 성격

**국경 인접은 지리적 사실이다.** 수도 좌표로 거리를 재서 추정하면 안 된다 —
한국과 일본은 가깝지만 육로가 없고, 러시아는 14개국과 접한다. 그래서 실제
국경을 적는다.

**인구는 근사값이다.** World Bank 총인구(SP.POP.TOTL)를 아직 붙이지 않아
2024년 전후 개략치를 쓴다. SEIR 규모 계산용이며 정밀 수치가 아니다.
`POPULATION_IS_APPROXIMATE = True` 로 표시하고, 지표 파이프라인에 인구를
추가하면 그때 교체한다.

## 범위

육로 국경이 있는 나라만 담는다. 섬나라(일본·필리핀·마다가스카르 등)는
육로 이웃이 없으므로 여기 없고, 항공으로만 연결된다 — 빠뜨린 게 아니다.
한국은 휴전선 때문에 사실상 섬으로 취급한다(북한과의 통행이 없다).
"""
from __future__ import annotations

POPULATION_IS_APPROXIMATE = True

# ── 육로 국경 (ISO3 → 접한 나라들) ──────────────────────────────────────────
# 양방향이다. 한쪽에만 적어도 로드 시 대칭으로 채운다(_symmetrize).
_BORDERS_RAW: dict[str, tuple[str, ...]] = {
    # ── 아프리카 ─────────────────────────────────────────────────────────
    "DZA": ("MAR", "TUN", "LBY", "NER", "MLI", "MRT", "ESH"),        # 알제리
    "AGO": ("COD", "COG", "ZMB", "NAM"),                              # 앙골라
    "BEN": ("TGO", "BFA", "NER", "NGA"),
    "BWA": ("ZAF", "NAM", "ZWE", "ZMB"),
    "BFA": ("MLI", "NER", "BEN", "TGO", "GHA", "CIV"),
    "BDI": ("RWA", "TZA", "COD"),
    "CMR": ("NGA", "TCD", "CAF", "COG", "GAB", "GNQ"),
    "CAF": ("TCD", "SDN", "SSD", "COD", "COG", "CMR"),
    "TCD": ("LBY", "SDN", "CAF", "CMR", "NGA", "NER"),
    "COD": ("COG", "CAF", "SSD", "UGA", "RWA", "BDI", "TZA", "ZMB", "AGO"),  # 콩고민주공화국
    "COG": ("GAB", "CMR", "CAF", "COD", "AGO"),
    "CIV": ("LBR", "GIN", "MLI", "BFA", "GHA"),
    "DJI": ("ERI", "ETH", "SOM"),
    "EGY": ("LBY", "SDN", "ISR", "PSE"),
    "GNQ": ("CMR", "GAB"),
    "ERI": ("SDN", "ETH", "DJI"),
    "SWZ": ("ZAF", "MOZ"),
    "ETH": ("ERI", "DJI", "SOM", "KEN", "SSD", "SDN"),
    "GAB": ("GNQ", "CMR", "COG"),
    "GMB": ("SEN",),
    "GHA": ("CIV", "BFA", "TGO"),
    "GIN": ("GNB", "SEN", "MLI", "CIV", "LBR", "SLE"),
    "GNB": ("SEN", "GIN"),
    "KEN": ("ETH", "SOM", "TZA", "UGA", "SSD"),
    "LSO": ("ZAF",),
    "LBR": ("SLE", "GIN", "CIV"),
    "LBY": ("TUN", "DZA", "NER", "TCD", "SDN", "EGY"),
    "MWI": ("TZA", "MOZ", "ZMB"),
    "MLI": ("DZA", "NER", "BFA", "CIV", "GIN", "SEN", "MRT"),
    "MRT": ("ESH", "DZA", "MLI", "SEN"),
    "MAR": ("ESH", "DZA"),
    "MOZ": ("TZA", "MWI", "ZMB", "ZWE", "ZAF", "SWZ"),
    "NAM": ("AGO", "ZMB", "BWA", "ZAF"),
    "NER": ("LBY", "TCD", "NGA", "BEN", "BFA", "MLI", "DZA"),
    "NGA": ("BEN", "NER", "TCD", "CMR"),
    "RWA": ("UGA", "TZA", "BDI", "COD"),
    "SEN": ("MRT", "MLI", "GIN", "GNB", "GMB"),
    "SLE": ("GIN", "LBR"),
    "SOM": ("DJI", "ETH", "KEN"),
    "ZAF": ("NAM", "BWA", "ZWE", "MOZ", "SWZ", "LSO"),
    "SSD": ("SDN", "ETH", "KEN", "UGA", "COD", "CAF"),
    "SDN": ("EGY", "LBY", "TCD", "CAF", "SSD", "ETH", "ERI"),
    "TZA": ("KEN", "UGA", "RWA", "BDI", "COD", "ZMB", "MWI", "MOZ"),
    "TGO": ("GHA", "BFA", "BEN"),
    "TUN": ("DZA", "LBY"),
    "UGA": ("SSD", "KEN", "TZA", "RWA", "COD"),
    "ZMB": ("COD", "TZA", "MWI", "MOZ", "ZWE", "BWA", "NAM", "AGO"),
    "ZWE": ("ZAF", "BWA", "ZMB", "MOZ"),

    # ── 중동 ─────────────────────────────────────────────────────────────
    "SAU": ("JOR", "IRQ", "KWT", "QAT", "ARE", "OMN", "YEM"),
    "ARE": ("SAU", "OMN"),
    "OMN": ("ARE", "SAU", "YEM"),
    "YEM": ("SAU", "OMN"),
    "QAT": ("SAU",),
    "KWT": ("IRQ", "SAU"),
    "IRQ": ("TUR", "IRN", "KWT", "SAU", "JOR", "SYR"),
    "IRN": ("IRQ", "TUR", "ARM", "AZE", "TKM", "AFG", "PAK"),
    "JOR": ("SYR", "IRQ", "SAU", "ISR", "PSE"),
    "SYR": ("TUR", "IRQ", "JOR", "ISR", "LBN"),
    "LBN": ("SYR", "ISR"),
    "ISR": ("LBN", "SYR", "JOR", "EGY", "PSE"),
    "PSE": ("ISR", "JOR", "EGY"),
    "TUR": ("GRC", "BGR", "GEO", "ARM", "AZE", "IRN", "IRQ", "SYR"),

    # ── 중앙·남아시아 ────────────────────────────────────────────────────
    "AFG": ("IRN", "PAK", "TKM", "UZB", "TJK", "CHN"),
    "PAK": ("IRN", "AFG", "CHN", "IND"),
    "IND": ("PAK", "CHN", "NPL", "BTN", "BGD", "MMR"),
    "NPL": ("IND", "CHN"),
    "BTN": ("IND", "CHN"),
    "BGD": ("IND", "MMR"),
    "LKA": (),                                    # 섬 — 육로 없음
    "KAZ": ("RUS", "CHN", "KGZ", "UZB", "TKM"),
    "UZB": ("KAZ", "KGZ", "TJK", "AFG", "TKM"),
    "TKM": ("KAZ", "UZB", "AFG", "IRN"),
    "KGZ": ("KAZ", "UZB", "TJK", "CHN"),
    "TJK": ("UZB", "KGZ", "CHN", "AFG"),

    # ── 동·동남아시아 ────────────────────────────────────────────────────
    "CHN": ("RUS", "MNG", "PRK", "VNM", "LAO", "MMR", "IND", "BTN", "NPL",
            "PAK", "AFG", "TJK", "KGZ", "KAZ"),
    "MNG": ("RUS", "CHN"),
    "PRK": ("CHN", "RUS", "KOR"),                 # 북한
    "MMR": ("BGD", "IND", "CHN", "LAO", "THA"),
    "THA": ("MMR", "LAO", "KHM", "MYS"),
    "LAO": ("CHN", "MMR", "THA", "KHM", "VNM"),
    "KHM": ("THA", "LAO", "VNM"),
    "VNM": ("CHN", "LAO", "KHM"),
    "MYS": ("THA", "IDN", "BRN"),
    "IDN": ("MYS", "PNG", "TLS"),
    "BRN": ("MYS",),
    "TLS": ("IDN",),
    "PNG": ("IDN",),

    # ── 유럽 ─────────────────────────────────────────────────────────────
    "RUS": ("NOR", "FIN", "EST", "LVA", "LTU", "POL", "BLR", "UKR", "GEO",
            "AZE", "KAZ", "CHN", "MNG", "PRK"),
    "UKR": ("RUS", "BLR", "POL", "SVK", "HUN", "ROU", "MDA"),
    "BLR": ("RUS", "UKR", "POL", "LTU", "LVA"),
    "POL": ("DEU", "CZE", "SVK", "UKR", "BLR", "LTU", "RUS"),
    "DEU": ("DNK", "POL", "CZE", "AUT", "CHE", "FRA", "LUX", "BEL", "NLD"),
    "FRA": ("BEL", "LUX", "DEU", "CHE", "ITA", "ESP", "AND", "MCO"),
    "ESP": ("PRT", "FRA", "AND", "MAR"),          # 세우타·멜리야로 모로코와 접함
    "PRT": ("ESP",),
    "ITA": ("FRA", "CHE", "AUT", "SVN", "SMR", "VAT"),
    "CHE": ("FRA", "DEU", "AUT", "ITA", "LIE"),
    "AUT": ("DEU", "CZE", "SVK", "HUN", "SVN", "ITA", "CHE", "LIE"),
    "CZE": ("DEU", "POL", "SVK", "AUT"),
    "SVK": ("CZE", "POL", "UKR", "HUN", "AUT"),
    "HUN": ("SVK", "UKR", "ROU", "SRB", "HRV", "SVN", "AUT"),
    "ROU": ("UKR", "MDA", "BGR", "SRB", "HUN"),
    "BGR": ("ROU", "SRB", "MKD", "GRC", "TUR"),
    "GRC": ("ALB", "MKD", "BGR", "TUR"),
    "SRB": ("HUN", "ROU", "BGR", "MKD", "ALB", "MNE", "BIH", "HRV"),
    "HRV": ("SVN", "HUN", "SRB", "BIH", "MNE"),
    "BIH": ("HRV", "SRB", "MNE"),
    "MNE": ("HRV", "BIH", "SRB", "ALB"),
    "MKD": ("SRB", "BGR", "GRC", "ALB"),
    "ALB": ("MNE", "SRB", "MKD", "GRC"),
    "SVN": ("AUT", "HUN", "HRV", "ITA"),
    "MDA": ("ROU", "UKR"),
    "NOR": ("SWE", "FIN", "RUS"),
    "SWE": ("NOR", "FIN"),
    "FIN": ("SWE", "NOR", "RUS"),
    "EST": ("RUS", "LVA"),
    "LVA": ("EST", "RUS", "BLR", "LTU"),
    "LTU": ("LVA", "BLR", "POL", "RUS"),
    "NLD": ("DEU", "BEL"),
    "BEL": ("NLD", "DEU", "LUX", "FRA"),
    "LUX": ("BEL", "DEU", "FRA"),
    "DNK": ("DEU",),
    "IRL": ("GBR",),
    "GBR": ("IRL",),
    "AND": ("ESP", "FRA"),
    "MCO": ("FRA",),
    "LIE": ("CHE", "AUT"),
    "SMR": ("ITA",),
    "VAT": ("ITA",),
    "GEO": ("RUS", "TUR", "ARM", "AZE"),
    "ARM": ("GEO", "AZE", "IRN", "TUR"),
    "AZE": ("RUS", "GEO", "ARM", "IRN", "TUR"),

    # ── 북·중미 ──────────────────────────────────────────────────────────
    "USA": ("CAN", "MEX"),
    "CAN": ("USA",),
    "MEX": ("USA", "GTM", "BLZ"),
    "GTM": ("MEX", "BLZ", "HND", "SLV"),
    "BLZ": ("MEX", "GTM"),
    "HND": ("GTM", "SLV", "NIC"),
    "SLV": ("GTM", "HND"),
    "NIC": ("HND", "CRI"),
    "CRI": ("NIC", "PAN"),
    "PAN": ("CRI", "COL"),
    "HTI": ("DOM",),
    "DOM": ("HTI",),

    # ── 남미 ─────────────────────────────────────────────────────────────
    "COL": ("PAN", "VEN", "BRA", "PER", "ECU"),
    "VEN": ("COL", "BRA", "GUY"),
    "GUY": ("VEN", "BRA", "SUR"),
    "SUR": ("GUY", "BRA", "GUF"),
    "BRA": ("URY", "ARG", "PRY", "BOL", "PER", "COL", "VEN", "GUY", "SUR", "GUF"),
    "ECU": ("COL", "PER"),
    "PER": ("ECU", "COL", "BRA", "BOL", "CHL"),
    "BOL": ("BRA", "PER", "CHL", "ARG", "PRY"),
    "CHL": ("PER", "BOL", "ARG"),
    "ARG": ("CHL", "BOL", "PRY", "BRA", "URY"),
    "PRY": ("BOL", "BRA", "ARG"),
    "URY": ("BRA", "ARG"),
}


def _symmetrize(raw: dict[str, tuple[str, ...]]) -> dict[str, frozenset[str]]:
    """한쪽에만 적힌 국경도 양방향으로 채운다.

    손으로 적는 표라 한쪽을 빠뜨리기 쉽다. 대칭화하지 않으면
    "A는 B와 접하는데 B는 A와 안 접한다"는 상태가 조용히 생긴다.
    """
    out: dict[str, set[str]] = {iso: set(nb) for iso, nb in raw.items()}
    for iso, neighbours in raw.items():
        for nb in neighbours:
            out.setdefault(nb, set()).add(iso)
    # 자기 자신은 이웃이 아니다
    for iso in out:
        out[iso].discard(iso)
    return {iso: frozenset(nb) for iso, nb in out.items()}


LAND_BORDERS: dict[str, frozenset[str]] = _symmetrize(_BORDERS_RAW)


# ── 통행이 없는 국경 ────────────────────────────────────────────────────────
# 국경은 지리적 사실이라 지우지 않는다. 다만 **사람이 못 건너는 국경**이 있다.
# 지리를 고쳐서 없앤 것처럼 만들면 나중에 왜 빠졌는지 아무도 모른다 —
# 그래서 국경은 남겨두고 통행량만 0으로 둔다.
# ★ 이건 2026-08 시점의 상태다 ★ 국경 개폐는 정치로 바뀐다. 지리와 달리
# 시간이 지나면 틀려지므로, 확실히 닫혀 있고 오래 유지된 것만 넣는다.
CLOSED_BORDERS: frozenset[tuple[str, str]] = frozenset({
    ("KOR", "PRK"),   # 휴전선 — 민간 왕래 없음
    ("CHN", "IND"),   # 히말라야 — 분쟁 국경, 민간 통행로 없음
    ("IND", "PAK"),   # 와가 통로 하나뿐, 일반 왕래로 볼 수 없는 수준
})


def is_open(a: str, b: str) -> bool:
    """이 국경으로 사람이 오갈 수 있는가."""
    pair = (a, b) if a < b else (b, a)
    return pair not in CLOSED_BORDERS


def open_neighbours(iso3: str) -> frozenset[str]:
    """통행 가능한 이웃만. 시뮬레이션은 이걸 쓴다."""
    return frozenset(n for n in neighbours(iso3) if is_open(iso3, n))


def neighbours(iso3: str) -> frozenset[str]:
    """육로로 접한 나라들. 섬나라·미등재국은 빈 집합."""
    return LAND_BORDERS.get(iso3, frozenset())


def border_pairs() -> list[tuple[str, str]]:
    """중복 없는 국경 쌍 목록 (A<B 순서로 정규화)."""
    seen: set[tuple[str, str]] = set()
    for iso, nbs in LAND_BORDERS.items():
        for nb in nbs:
            seen.add((iso, nb) if iso < nb else (nb, iso))
    return sorted(seen)


# ── 인구 (근사값) ───────────────────────────────────────────────────────────
# ★ World Bank 총인구를 아직 안 붙였다 ★ 2024년 전후 개략치이며 SEIR 규모
# 계산용이다. 정밀 인구 통계가 아니므로 화면에 "인구 N명"으로 인용하지 말 것.
POPULATION: dict[str, int] = {
    # 아프리카
    "DZA": 46_000_000, "AGO": 36_000_000, "BEN": 14_000_000, "BWA": 2_600_000,
    "BFA": 23_000_000, "BDI": 13_000_000, "CMR": 28_000_000, "CAF": 5_700_000,
    "TCD": 18_000_000, "COD": 102_000_000, "COG": 6_100_000, "CIV": 29_000_000,
    "DJI": 1_100_000, "EGY": 113_000_000, "GNQ": 1_700_000, "ERI": 3_700_000,
    "SWZ": 1_200_000, "ETH": 126_000_000, "GAB": 2_400_000, "GMB": 2_800_000,
    "GHA": 34_000_000, "GIN": 14_000_000, "GNB": 2_200_000, "KEN": 55_000_000,
    "LSO": 2_300_000, "LBR": 5_400_000, "LBY": 6_900_000, "MWI": 21_000_000,
    "MLI": 23_000_000, "MRT": 4_900_000, "MAR": 37_000_000, "MOZ": 33_000_000,
    "NAM": 2_600_000, "NER": 26_000_000, "NGA": 223_000_000, "RWA": 14_000_000,
    "SEN": 17_000_000, "SLE": 8_600_000, "SOM": 18_000_000, "ZAF": 60_000_000,
    "SSD": 11_000_000, "SDN": 48_000_000, "TZA": 67_000_000, "TGO": 9_100_000,
    "TUN": 12_000_000, "UGA": 48_000_000, "ZMB": 20_000_000, "ZWE": 16_000_000,
    "ESH": 600_000,
    # 중동
    "SAU": 36_000_000, "ARE": 9_500_000, "OMN": 4_600_000, "YEM": 34_000_000,
    "QAT": 2_700_000, "KWT": 4_300_000, "IRQ": 45_000_000, "IRN": 89_000_000,
    "JOR": 11_000_000, "SYR": 23_000_000, "LBN": 5_400_000, "ISR": 9_700_000,
    "PSE": 5_400_000, "TUR": 85_000_000,
    # 중앙·남아시아
    "AFG": 42_000_000, "PAK": 240_000_000, "IND": 1_428_000_000, "NPL": 31_000_000,
    "BTN": 800_000, "BGD": 173_000_000, "LKA": 22_000_000, "KAZ": 20_000_000,
    "UZB": 35_000_000, "TKM": 7_100_000, "KGZ": 7_000_000, "TJK": 10_000_000,
    # 동·동남아시아
    "CHN": 1_411_000_000, "MNG": 3_400_000, "PRK": 26_000_000, "KOR": 52_000_000,
    "MMR": 54_000_000, "THA": 72_000_000, "LAO": 7_600_000, "KHM": 17_000_000,
    "VNM": 98_000_000, "MYS": 34_000_000, "IDN": 278_000_000, "BRN": 450_000,
    "TLS": 1_400_000, "PNG": 10_000_000,
    # 유럽
    "RUS": 144_000_000, "UKR": 38_000_000, "BLR": 9_200_000, "POL": 37_000_000,
    "DEU": 84_000_000, "FRA": 68_000_000, "ESP": 48_000_000, "PRT": 10_000_000,
    "ITA": 59_000_000, "CHE": 8_800_000, "AUT": 9_100_000, "CZE": 11_000_000,
    "SVK": 5_400_000, "HUN": 9_600_000, "ROU": 19_000_000, "BGR": 6_500_000,
    "GRC": 10_000_000, "SRB": 6_600_000, "HRV": 3_900_000, "BIH": 3_200_000,
    "MNE": 620_000, "MKD": 1_800_000, "ALB": 2_700_000, "SVN": 2_100_000,
    "MDA": 2_500_000, "NOR": 5_500_000, "SWE": 10_000_000, "FIN": 5_600_000,
    "EST": 1_400_000, "LVA": 1_800_000, "LTU": 2_800_000, "NLD": 18_000_000,
    "BEL": 12_000_000, "LUX": 660_000, "DNK": 5_900_000, "IRL": 5_200_000,
    "GBR": 68_000_000, "AND": 80_000, "MCO": 36_000, "LIE": 39_000,
    "SMR": 34_000, "VAT": 800, "GEO": 3_700_000, "ARM": 2_800_000, "AZE": 10_000_000,
    # 북·중미
    "USA": 335_000_000, "CAN": 40_000_000, "MEX": 128_000_000, "GTM": 18_000_000,
    "BLZ": 410_000, "HND": 10_000_000, "SLV": 6_400_000, "NIC": 7_000_000,
    "CRI": 5_200_000, "PAN": 4_500_000, "HTI": 12_000_000, "DOM": 11_000_000,
    # 남미
    "COL": 52_000_000, "VEN": 28_000_000, "GUY": 810_000, "SUR": 620_000,
    "GUF": 300_000, "BRA": 216_000_000, "ECU": 18_000_000, "PER": 34_000_000,
    "BOL": 12_000_000, "CHL": 19_000_000, "ARG": 46_000_000, "PRY": 6_900_000,
    "URY": 3_400_000,
}


def population(iso3: str) -> int | None:
    """근사 인구. 모르는 나라는 None — 0으로 채우지 않는다."""
    return POPULATION.get(iso3)

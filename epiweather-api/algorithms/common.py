"""공통 상수·데이터 — 원본 HTML 프로토타입과 동일한 값을 Python으로 이식."""
from __future__ import annotations
import math

# ── 위협 시나리오 ─────────────────────────────────────────────
THREAT = {
    "flu":    {"R0": 2.2, "cfr": 0.010, "nm": "계절 유행"},
    "novel":  {"R0": 2.8, "cfr": 0.018, "nm": "신종 감염병"},
    "severe": {"R0": 3.4, "cfr": 0.028, "nm": "고위험 신종"},
}

PRESETS = {
    "none":   {"quar": 0,   "dist": 0,   "vax": 0,   "vaxsp": 0,     "anti": 0,   "vuln": 0   },
    "mild":   {"quar": .15, "dist": .18, "vax": .35, "vaxsp": .005,  "anti": .3,  "vuln": .4  },
    "strong": {"quar": .30, "dist": .32, "vax": .55, "vaxsp": .008,  "anti": .55, "vuln": .7  },
}

CHANNELS = [
    {"nm": "검색·SNS", "ic": "🔍", "col": "#a78bfa"},
    {"nm": "OTC 판매",  "ic": "💊", "col": "#fbbf24"},
    {"nm": "하수 신호", "ic": "🚰", "col": "#38bdf8"},
    {"nm": "동물 예찰", "ic": "🐦", "col": "#f472b6"},
    {"nm": "이동 변화", "ic": "🚇", "col": "#34d399"},
    {"nm": "1339 통화", "ic": "📞", "col": "#fb923c"},
]

CIVIC = [
    {"id": "citi",  "nm": "시민 자가증상", "sub": "CITIZEN",    "ic": "🤒", "col": "#a78bfa", "lead": 14, "q": .55, "v": .85},
    {"id": "sewer", "nm": "하수 역학",     "sub": "WASTEWATER", "ic": "🚰", "col": "#38bdf8", "lead": 11, "q": .92, "v": .72},
    {"id": "otc",   "nm": "약국 OTC",      "sub": "PHARMACY",   "ic": "💊", "col": "#fbbf24", "lead": 8,  "q": .78, "v": .95},
    {"id": "kit",   "nm": "민간 진단키트", "sub": "KIT",        "ic": "🧪", "col": "#f472b6", "lead": 6,  "q": .81, "v": .60},
    {"id": "lab",   "nm": "민간 검사소",   "sub": "LAB",        "ic": "🔬", "col": "#34d399", "lead": 5,  "q": .95, "v": .45},
]

CITIES = [
    {"id": "WUH", "nm": "우한",       "lon": 114.3, "lat": 30.6,  "er": .85, "pax": .55, "hrs": 5,  "note": "인수공통·고밀도"},
    {"id": "JKT", "nm": "자카르타",   "lon": 106.8, "lat": -6.2,  "er": .70, "pax": .45, "hrs": 7,  "note": "가금·열대"},
    {"id": "BKK", "nm": "방콕",       "lon": 100.5, "lat": 13.7,  "er": .55, "pax": .80, "hrs": 6,  "note": "관광허브·고여객"},
    {"id": "HAN", "nm": "하노이",     "lon": 105.8, "lat": 21.0,  "er": .60, "pax": .65, "hrs": 5,  "note": "가금·접경"},
    {"id": "DAC", "nm": "다카",       "lon": 90.4,  "lat": 23.8,  "er": .65, "pax": .25, "hrs": 7,  "note": "니파위험"},
    {"id": "FIH", "nm": "킨샤사",     "lon": 15.3,  "lat": -4.3,  "er": .90, "pax": .05, "hrs": 20, "note": "출혈열·취약"},
    {"id": "LOS", "nm": "라고스",     "lon": 3.4,   "lat": 6.5,   "er": .80, "pax": .08, "hrs": 18, "note": "인수공통"},
    {"id": "MEX", "nm": "멕시코시티", "lon": -99.1, "lat": 19.4,  "er": .60, "pax": .12, "hrs": 14, "note": "신종플루 전례"},
]
CITY_MAP = {c["id"]: c for c in CITIES}

REGIONS = [
    {"id": "IC", "nm": "인천", "c": 2, "r": 1, "pop": 3.0,  "eld": 16},
    {"id": "SU", "nm": "서울", "c": 3, "r": 1, "pop": 9.4,  "eld": 18},
    {"id": "GG", "nm": "경기", "c": 4, "r": 1, "pop": 13.6, "eld": 15},
    {"id": "GW", "nm": "강원", "c": 5, "r": 1, "pop": 1.5,  "eld": 24},
    {"id": "CN", "nm": "충남", "c": 2, "r": 2, "pop": 2.1,  "eld": 21},
    {"id": "CB", "nm": "충북", "c": 4, "r": 2, "pop": 1.6,  "eld": 20},
    {"id": "DG", "nm": "대구", "c": 5, "r": 3, "pop": 2.4,  "eld": 19},
    {"id": "JB", "nm": "전북", "c": 2, "r": 3, "pop": 1.8,  "eld": 23},
    {"id": "GN", "nm": "경남", "c": 4, "r": 4, "pop": 3.3,  "eld": 19},
    {"id": "JN", "nm": "전남", "c": 2, "r": 5, "pop": 1.8,  "eld": 26},
    {"id": "BS", "nm": "부산", "c": 5, "r": 5, "pop": 3.3,  "eld": 22},
    {"id": "JJ", "nm": "제주", "c": 3, "r": 7, "pop": .67,  "eld": 17},
]
REGION_MAP = {r["id"]: r for r in REGIONS}

MOBILITY: dict[str, dict[str, float]] = {
    "IC": {"SU":.9,"GG":.8,"CN":.4,"JJ":.5,"BS":.4,"DG":.3,"CB":.3},
    "SU": {"IC":.9,"GG":.95,"CN":.5,"DG":.5,"BS":.5,"JJ":.4,"GW":.5,"CB":.5},
    "GG": {"SU":.95,"IC":.8,"CN":.6,"DG":.5,"BS":.4,"JJ":.3,"GW":.6,"CB":.6},
    "GW": {"SU":.5,"GG":.6,"CB":.4,"DG":.3},
    "CN": {"GG":.6,"SU":.5,"IC":.4,"JB":.5,"CB":.5,"DG":.3},
    "CB": {"GG":.6,"SU":.5,"CN":.5,"DG":.5,"GW":.4},
    "DG": {"SU":.5,"GG":.5,"BS":.7,"CB":.5,"GN":.6,"CN":.3},
    "JB": {"CN":.5,"GN":.5,"JN":.6,"GG":.3},
    "GN": {"DG":.6,"BS":.7,"JB":.5,"JN":.4,"SU":.4},
    "JN": {"JB":.6,"GN":.4,"JJ":.4,"SU":.3},
    "BS": {"DG":.7,"GN":.7,"SU":.5,"JJ":.45,"GG":.4},
    "JJ": {"IC":.5,"SU":.4,"BS":.45,"JN":.4,"GG":.3},
}

ENTRY_PORTS = [
    {"id": "ICN", "nm": "인천국제공항", "eng": "ICN·수도권", "base": .82},
    {"id": "GMP", "nm": "김포·기타",    "eng": "GMP",        "base": .06},
    {"id": "PUS", "nm": "부산",         "eng": "PUS·영남",   "base": .08},
    {"id": "CJU", "nm": "제주",         "eng": "CJU",        "base": .04},
]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ── LCG 랜덤 (seed 기반 결정론적) ───────────────────────────
class LCG:
    def __init__(self, seed: int = 42):
        self.state = seed

    def next(self) -> float:
        self.state = (self.state * 1103515245 + 12345) & 0x7fffffff
        return self.state / 0x7fffffff

    def gauss(self) -> float:
        u = max(self.next(), 1e-9)
        return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * self.next())


# ── 통계 함수 ─────────────────────────────────────────────────
def _erf(x: float) -> float:
    a1,a2,a3,a4,a5,p = .254829592,-.284496736,1.421413741,-1.453152027,1.061405429,.3275911
    s = -1 if x < 0 else 1
    x = abs(x)
    t = 1 / (1 + p * x)
    return s * (1 - (((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*math.exp(-x*x))


def p_one_tail(z: float) -> float:
    return max(0.0005, 1 - 0.5 * (1 + _erf(z / math.sqrt(2))))


def chi_cdf(x: float, k: int) -> float:
    if x <= 0:
        return 0.0
    s, t = 0.0, math.exp(-x / 2)
    for i in range(k // 2):
        s += t
        t *= x / (2 * (i + 1))
    return 1 - s


def fisher_combined_p(zs: list[float]) -> float:
    """피셔 결합 p-value (Farrington 원리)."""
    ps = [p_one_tail(max(0.0, z)) for z in zs]
    chi = -2 * sum(math.log(p) for p in ps)
    return 1 - chi_cdf(chi, 2 * len(ps))

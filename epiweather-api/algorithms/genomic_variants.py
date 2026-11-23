"""Nextstrain 실시간 유전체 계통(clade) 추적 — Phase 4 ㉑.

병원체가 변이할 때 가장 먼저 드러나는 신호는 확진자 수가 아니라 유전체
계통(clade) 구성비 변화다 — 새 계통이 등장하거나 기존 계통을 빠르게
대체하면 그게 확산력·면역회피 변화의 선행 지표. Nextstrain(nextstrain.org)이
공개 시퀀스(GenBank/GISAID 오픈 데이터)를 매일 재분석해 계통분류 트리를
무료·인증 없이 공개하므로 이를 그대로 신호로 씀.

주의 — 빌드마다 갱신 주기가 다르다: 실측 확인(2026-07-06) 결과 ncov/open,
mpox, rsv 빌드는 최근(최대 며칠 전)까지 갱신되고 있었지만, 계절독감
H3N2/H1N1 "2y" 빌드는 2024-04-23 이후 갱신이 멈춰있었다 — 이걸 그대로 쓰면
"실시간 변이 추적"이라는 전제가 깨지고 죽은 신호를 정상처럼 보고하게 된다
(오늘 CDC NWSS·WOAH RSS에서 고친 것과 같은 패턴). 그래서 감시 대상에서
독감은 제외하고, 매 수집마다 meta.updated 신선도를 확인해 STALE_DAYS를
넘기면 available=False로 명시한다.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import os

import requests

CHARON_URL = "https://nextstrain.org/charon/getDataset"
USER_AGENT = {"User-Agent": "EpiWeather-Genomic/1.0 (epiweather.kr)"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# 빌드 하나당 상한. Nextstrain 트리 JSON은 수MB라 30초로 빠듯한 경우가 있어
# 45초로 올린다 — 병렬화 후 합계 대기 상한은 45초(직렬 90초+에서 단축).
TIMEOUT = _env_float("AEGIRON_VARIANT_TIMEOUT_S", 45.0)
MAX_WORKERS = _env_int("AEGIRON_VARIANT_WORKERS", 3)

# 엠폭스(/mpox)·RSV-A(/rsv/a/genome)는 2026-11-22 개편 2차에서 뺐다 — 11-21~22 운영 로그에서
# 매시 '최근 구간 시퀀스 없음'으로 한 번도 값이 안 나왔다. 다시 보려면 AEGIRON_VARIANT_BUILDS 로 넣는다.
WATCHLIST = [
    ("/ncov/open/global/6m", "SARS-CoV-2(공개시퀀스)"),
]


def _watchlist() -> list[tuple[str, str]]:
    """감시 빌드 목록. AEGIRON_VARIANT_BUILDS="/a|A,/b|B" 형식으로 교체 가능.
    파싱 실패·빈값은 조용히 기본 목록으로 되돌린다(수집이 멈추면 안 되므로)."""
    raw = (os.environ.get("AEGIRON_VARIANT_BUILDS") or "").strip()
    if not raw:
        return WATCHLIST
    items: list[tuple[str, str]] = []
    for chunk in raw.split(","):
        if "|" not in chunk:
            return WATCHLIST
        prefix, label = chunk.split("|", 1)
        prefix, label = prefix.strip(), label.strip()
        if not prefix.startswith("/") or not label:
            return WATCHLIST
        items.append((prefix, label))
    return items or WATCHLIST

STALE_DAYS = 30           # 이보다 오래 안 갱신되면 빌드 정지로 간주

# ── 성장 신호 (2026-11-23) ─────────────────────────────────────────
# "우세가 바뀐 뒤 기록"(후행)이 아니라 "커지고 있는 계통"(선행)을 본다. 연구 근거: 계통별
# 개수만 쓰는 단순 증가율 모델(다항 로지스틱)도 단기 예측에 쓸모 있었고(6개국 비교, PMC10705624),
# 성장률 차이 신호가 우세 43~65일 전에 잡혔다는 보고가 있다(arXiv 2605.30382, 심사 전).
# 여기서는 가장 단순한 형태만 쓴다: 직전 4주 대비 최근 4주 구성비의 로그 변화를 주당 성장률로.
# 측정이 아니라 **추정**이다 — 표본 수·제출 지연에 따라 흔들린다(그래서 문턱 미달은 판정 안 함).
GROWTH_WINDOW_DAYS = 28        # 최근 구간 = 지난 28일, 비교 구간 = 그 앞 28일
GROWTH_MIN_TOTAL = 50          # 두 구간 각각 전체 시퀀스가 이보다 적으면 판정 안 함
GROWTH_MIN_CLADE_RECENT = 10   # 최근 구간에서 이보다 적은 계통은 목록에 안 올린다(소표본 튐)
GROWTH_PSEUDOCOUNT = 0.5       # 비교 구간에 0건인 계통의 로그 발산 방지
GROWTH_TOP_N = 5
RECENT_WINDOW_DAYS = 60   # "최근" 구간
PRIOR_WINDOW_DAYS = 60    # 그 직전 비교 구간


def _year_frac(days_ago: float) -> float:
    """오늘로부터 days_ago일 전 날짜를 Nextstrain의 소수년(num_date) 단위로 환산."""
    target = dt.date.today() - dt.timedelta(days=days_ago)
    year_start = dt.date(target.year, 1, 1)
    year_len = (dt.date(target.year + 1, 1, 1) - year_start).days
    return target.year + (target - year_start).days / year_len


def _fetch_dataset(prefix: str) -> dict | None:
    try:
        r = requests.get(CHARON_URL, params={"prefix": prefix}, headers=USER_AGENT, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _iter_tip_clades(node: dict):
    """리프(말단 시퀀스) 노드만 순회해 (clade, num_date)를 낸다. 내부 노드는 조상 추정치라 제외."""
    children = node.get("children")
    if not children:
        attrs = node.get("node_attrs", {})
        clade = (attrs.get("clade_membership") or {}).get("value")
        num_date = (attrs.get("num_date") or {}).get("value")
        if clade is not None and num_date is not None:
            yield clade, num_date
        return
    for child in children:
        yield from _iter_tip_clades(child)


def analyze_build(prefix: str, label: str) -> dict:
    """빌드 하나를 분석해 최근 구간 계통 구성·신규 계통 출현 여부를 반환."""
    data = _fetch_dataset(prefix)
    if not data:
        return {"label": label, "available": False, "reason": "Nextstrain API 응답 실패"}

    updated_str = data.get("meta", {}).get("updated")
    try:
        updated_date = dt.date.fromisoformat(updated_str) if updated_str else None
    except ValueError:
        updated_date = None
    if updated_date is None or (dt.date.today() - updated_date).days > STALE_DAYS:
        return {
            "label": label, "available": False,
            "reason": f"빌드 갱신 정지 의심(마지막 갱신 {updated_str})",
            "build_updated": updated_str,
        }

    tips = list(_iter_tip_clades(data.get("tree", {})))
    recent_cutoff = _year_frac(RECENT_WINDOW_DAYS)
    prior_cutoff = _year_frac(RECENT_WINDOW_DAYS + PRIOR_WINDOW_DAYS)

    recent = [c for c, d in tips if d >= recent_cutoff]
    prior = [c for c, d in tips if prior_cutoff <= d < recent_cutoff]
    prior_clades = set(prior)

    recent_counts: dict[str, int] = {}
    for c in recent:
        recent_counts[c] = recent_counts.get(c, 0) + 1

    dominant_clade, dominant_count = (
        max(recent_counts.items(), key=lambda kv: kv[1]) if recent_counts else (None, 0)
    )

    # 최근 구간이나 이전 구간 중 하나라도 시퀀스가 없으면(제출 지연·희소 병원체)
    # "신규 계통 0건"이라고 단정할 수 없음 — None으로 남겨 "미확인"과 "확인된
    # 신규 없음"을 구분한다. mpox·RSV처럼 제출 주기가 느린 병원체는 최근 60일
    # 구간이 통째로 비어있는 경우가 실제로 있었음(실측 확인).
    if prior_clades and recent_counts:
        new_clades = sorted(set(recent_counts) - prior_clades)
        new_clade_count = len(new_clades)
    else:
        new_clades = []
        new_clade_count = None

    return {
        "label": label,
        "available": True,
        "build_updated": updated_str,
        "n_recent_sequences": len(recent),
        "n_prior_sequences": len(prior),
        "dominant_clade": dominant_clade,
        "dominant_share": round(dominant_count / len(recent), 3) if recent else None,
        "new_clades": new_clades[:5],
        "new_clade_count": new_clade_count,
        "note": None if recent else "최근 구간 시퀀스 없음(제출 지연 가능)",
        "growth": growth_signal(tips),
    }


def growth_signal(tips: list[tuple[str, float]], today: dt.date | None = None) -> dict:
    """계통별 주당 상대 성장률(구성비 로그 변화 / 4주). 커지는 계통을 성장률 순으로.

    성장률 g 는 '전체 중 그 계통의 비율'이 한 주에 몇 배가 되는가의 로그다. 비율이 두 배가
    되는 데 걸리는 날 수(ln2/g×7)를 함께 낸다. 두 구간 중 하나라도 표본이 문턱보다 적으면
    목록을 만들지 않고 이유를 적는다 — '커지는 계통 없음'과 '못 봄'을 섞지 않는다."""
    import math
    today = today or dt.date.today()

    def frac(days_ago: float) -> float:
        target = today - dt.timedelta(days=days_ago)
        y0 = dt.date(target.year, 1, 1)
        return target.year + (target - y0).days / (dt.date(target.year + 1, 1, 1) - y0).days

    recent_cut, prior_cut = frac(GROWTH_WINDOW_DAYS), frac(2 * GROWTH_WINDOW_DAYS)
    recent: dict[str, int] = {}
    prior: dict[str, int] = {}
    for clade, d in tips:
        if d >= recent_cut:
            recent[clade] = recent.get(clade, 0) + 1
        elif d >= prior_cut:
            prior[clade] = prior.get(clade, 0) + 1
    n_recent, n_prior = sum(recent.values()), sum(prior.values())
    base = {"method": "구성비 로그 변화(최근 4주 vs 직전 4주) — 추정",
            "window_days": GROWTH_WINDOW_DAYS, "n_recent": n_recent, "n_prior": n_prior}
    if n_recent < GROWTH_MIN_TOTAL or n_prior < GROWTH_MIN_TOTAL:
        return {**base, "determined": False, "growing": [],
                "reason": f"표본 부족(최근 {n_recent} · 직전 {n_prior}, 각 {GROWTH_MIN_TOTAL} 이상 필요)"}
    weeks = GROWTH_WINDOW_DAYS / 7
    rows = []
    for clade, rc in recent.items():
        if rc < GROWTH_MIN_CLADE_RECENT:
            continue
        pc = prior.get(clade, 0)
        s_r = rc / n_recent
        s_p = (pc + GROWTH_PSEUDOCOUNT) / (n_prior + GROWTH_PSEUDOCOUNT)
        g = math.log(s_r / s_p) / weeks
        if g <= 0:
            continue
        rows.append({
            "clade": clade, "recent_count": rc, "prior_count": pc,
            "share_recent": round(s_r, 3), "share_prior": round(pc / n_prior, 3),
            "weekly_growth": round(g, 3),
            "share_doubling_days": round(math.log(2) / g * 7, 1),
            "new_in_window": pc == 0,
        })
    rows.sort(key=lambda r: -r["weekly_growth"])
    return {**base, "determined": True, "growing": rows[:GROWTH_TOP_N], "reason": None}


GROWTH_CACHE_KEY = "variant_growth"


def growth_snapshot(signals: dict) -> dict:
    """수집 결과 → API 용 성장 신호 묶음(빌드별). 빌드를 못 읽었으면 그 이유를 그대로."""
    builds = []
    for slug, v in (signals or {}).items():
        if not v.get("available"):
            builds.append({"build": slug, "label": v.get("label"), "determined": False,
                           "reason": v.get("reason") or "빌드 조회 실패", "growing": []})
            continue
        g = v.get("growth") or {}
        builds.append({"build": slug, "label": v.get("label"), "build_updated": v.get("build_updated"),
                       **g})
    return {"computed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "builds": builds}


def growth_line(v: dict) -> str:
    """로그 한 줄: 📈 성장 신호 SARS-CoV-2: XFG.3 주당 +0.21(비율 2배 23일, 12%←4%) · …"""
    g = v.get("growth") or {}
    label = v.get("label")
    if not g:
        return f"📈 성장 신호 {label}: 계산 안 됨"
    if not g.get("determined"):
        return f"📈 성장 신호 {label}: 판정 안 함 — {g.get('reason')}"
    rows = g.get("growing") or []
    if not rows:
        return f"📈 성장 신호 {label}: 커지는 계통 없음(최근 {g['n_recent']} · 직전 {g['n_prior']})"
    parts = [f"{r['clade']} 주당 +{r['weekly_growth']}(비율 2배 {r['share_doubling_days']}일, "
             f"{r['share_recent']*100:.0f}%←{r['share_prior']*100:.0f}%)" for r in rows[:3]]
    return f"📈 성장 신호 {label}: " + " · ".join(parts)


def _safe_analyze(prefix: str, label: str) -> dict:
    try:
        return analyze_build(prefix, label)
    except Exception as e:
        return {"label": label, "available": False, "reason": str(e)[:150]}


def get_genomic_variant_signals() -> dict:
    """감시 목록 전체를 병렬 분석. 빌드 하나가 실패·지연돼도 나머지는 계속 수집.
    스레드풀이라 requests 블로킹이 겹치지 않고, 결과 키 집합은 직렬 때와 동일."""
    watch = _watchlist()
    out: dict[str, dict] = {}
    workers = min(max(1, MAX_WORKERS), max(1, len(watch)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_safe_analyze, prefix, label): prefix
                for prefix, label in watch}
        for fut in concurrent.futures.as_completed(futs):
            slug = futs[fut].strip("/").replace("/", "_")
            out[slug] = fut.result()
    return out

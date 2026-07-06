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
import datetime as dt

import requests

CHARON_URL = "https://nextstrain.org/charon/getDataset"
USER_AGENT = {"User-Agent": "EpiWeather-Genomic/1.0 (epiweather.kr)"}
TIMEOUT = 30

WATCHLIST = [
    ("/ncov/open/global/6m", "SARS-CoV-2(공개시퀀스)"),
    ("/mpox", "엠폭스"),
    ("/rsv/a/genome", "RSV-A"),
]

STALE_DAYS = 30           # 이보다 오래 안 갱신되면 빌드 정지로 간주
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
    }


def get_genomic_variant_signals() -> dict:
    """감시 목록 전체를 분석. 빌드 하나가 실패해도 나머지는 계속 수집."""
    out: dict[str, dict] = {}
    for prefix, label in WATCHLIST:
        slug = prefix.strip("/").replace("/", "_")
        try:
            out[slug] = analyze_build(prefix, label)
        except Exception as e:
            out[slug] = {"label": label, "available": False, "reason": str(e)[:150]}
    return out

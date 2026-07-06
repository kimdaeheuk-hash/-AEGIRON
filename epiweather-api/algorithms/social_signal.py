"""Mastodon 실시간 SNS 신호 — Phase 4 ㉒.

기존 "검색·행동" 신호(네이버 DataLab, Google Trends, 현지어 뉴스 RSS)는
전부 검색행태나 편집된 뉴스지, 개인이 실시간으로 올리는 SNS 게시물 자체는
아니었음. 실측 확인(2026-07-06) 결과:
  - 트위터/X: 검색 가능한 무료 티어가 사실상 없음(유료 API만)
  - 레딧 공개 JSON(reddit.com/search.json): 최근 403으로 막혀있음(인증 요구)
  - Mastodon 해시태그 타임라인(/api/v1/timelines/tag/:tag): 완전 공개,
    인증 불필요, 실시간(수 시간 전 게시물까지 확인됨) — 유일하게 접근 가능한
    무료 실시간 SNS 소스라 이걸 채택.

한계: mastodon.social 단일 인스턴스만 봄(연합 전체 검색은 별도 인프라 필요) —
즉 SNS 전체가 아니라 그 표본. 니치 질병 해시태그는 게시량이 적어서(실측:
40건 채우는 데 며칠~몇 달 소요) 1시간 단위가 아니라 7일 누적 건수로
집계하고, 직전 수집 회차 대비 배율로 급변을 본다(Polymarket 급변 판정과
동일한 방식).
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "social_signal_history.json"

INSTANCE = "https://mastodon.social"
USER_AGENT = {"User-Agent": "EpiWeather-Social/1.0 (epiweather.kr)"}
TIMEOUT = 15
FETCH_LIMIT = 40       # 해시태그 타임라인 1회 호출 최대치
WINDOW_HOURS = 24 * 7  # 니치 태그가 많아 시간 단위보다 주간 누적이 안정적

SURGE_RATIO = 2.0  # 직전 회차 대비 이 배율 이상이면 급변으로 표시

HASHTAG_WATCHLIST = [
    ("ebola", "에볼라"),
    ("mpox", "엠폭스"),
    ("birdflu", "조류인플루엔자"),
    ("h5n1", "H5N1"),
    ("cholera", "콜레라"),
    ("measles", "홍역"),
    ("dengue", "뎅기열"),
    ("marburg", "마버그열"),
]


def _parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _fetch_tag_posts(tag: str) -> list[dict] | None:
    """해시태그 최근 게시물. 실패하면 None(= '집계 실패', 0건과 구분)."""
    try:
        r = requests.get(
            f"{INSTANCE}/api/v1/timelines/tag/{tag}",
            params={"limit": FETCH_LIMIT},
            headers=USER_AGENT, timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _analyze_tag(tag: str, label: str) -> dict:
    posts = _fetch_tag_posts(tag)
    if posts is None:
        return {"label": label, "available": False, "reason": "Mastodon API 응답 실패"}

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=WINDOW_HOURS)
    recent = [p for p in posts if _parse_ts(p["created_at"]) >= cutoff]

    # 반환된 게시물(최대 FETCH_LIMIT개)이 전부 윈도우 안에 들어오면 실제 건수가
    # 더 많을 수 있음 — 표본이 상한에 걸렸다는 걸 명시(실측: 저활동 태그도
    # 40건이 며칠~몇 달 치라 이 케이스가 실제로 발생함).
    sample_capped = len(posts) == FETCH_LIMIT and len(recent) == FETCH_LIMIT

    # 노이즈 필터: 계정 하나가 관련없는 게시물에도 태그 여러 개를 통째로 붙여
    # 반복 게시하면 원문 건수가 그 계정 하나만으로 부풀려짐(실측: #birdflu 40건
    # 중 6건이 계정 하나의 반복 태그 도배였음). 계정당 1회만 세어서 "실제로
    # 몇 명이 언급했는가"를 신호로 쓴다.
    unique_accounts = {p.get("account", {}).get("id") for p in recent}
    unique_accounts.discard(None)

    return {
        "label": label,
        "available": True,
        "count_recent": len(unique_accounts),
        "count_posts_raw": len(recent),
        "window_hours": WINDOW_HOURS,
        "sample_capped": sample_capped,
    }


def _load_history() -> dict:
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_history(history: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def get_social_signal() -> dict:
    """감시 해시태그 전체를 분석하고 직전 회차 대비 급변 여부를 채워 반환.
    태그 하나가 실패해도 나머지는 계속 수집."""
    history = _load_history()
    out: dict[str, dict] = {}

    for tag, label in HASHTAG_WATCHLIST:
        try:
            entry = _analyze_tag(tag, label)
        except Exception as e:
            entry = {"label": label, "available": False, "reason": str(e)[:150]}

        entry["count_change_ratio"] = None
        entry["surge_alert"] = False
        if entry.get("available"):
            prev = history.get(tag)
            if prev and prev.get("count_recent", 0) > 0:
                ratio = round(entry["count_recent"] / prev["count_recent"], 2)
                entry["count_change_ratio"] = ratio
                entry["surge_alert"] = ratio >= SURGE_RATIO
            history[tag] = {"count_recent": entry["count_recent"]}

        out[tag] = entry

    _save_history(history)
    return out

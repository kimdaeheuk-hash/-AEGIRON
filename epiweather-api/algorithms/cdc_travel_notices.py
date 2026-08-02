"""CDC 여행 건강경보 — 신규 선행지표 각도 탐색(2026-07-27) 중 발견한, 가입·키
없이 즉시 쓸 수 있는 공식 무료 RSS.

CDC Travelers' Health가 국가별 여행 위험을 공식 4단계(Level 1~4)로 매겨
공개한다. 감염병 발생 시 CDC가 등급을 올리는데, 이건 국내 KDCA·WHO 공식
발표와는 별개로 "여행객 안전"이라는 다른 관점에서 CDC 전문가가 판단한
경보라 — 우리 항공사 고객 프로파일(customer_profiles.py)과 특히 잘 맞는다.

★ 정직성 경계선 ★
- 등급(level)은 CDC가 공식으로 매긴 실측 분류다.
- 다만 이 피드는 감염병 전용이 아니다(자연재해·대규모 행사 등도 포함) —
  disease_only 필터 없이 원문 그대로 노출하고, 이 사실을 note로 명시한다.
- 키 불필요. 실패 시 조용히 죽지 않고 data_available=False로 표시.
"""
from __future__ import annotations
import re

import requests
import xml.etree.ElementTree as ET

RSS_URL = "https://wwwnc.cdc.gov/travel/rss/notices.xml"
TIMEOUT = 15
USER_AGENT = {"User-Agent": "Mozilla/5.0 (AEGIRON/1.0; +epiweather.kr)"}

_LEVEL_RE = re.compile(r"^Level\s+(\d)\s*-\s*(.+)$", re.IGNORECASE)

LEVEL_MEANING = {
    1: "일반적 예방수칙 준수(Practice Usual Precautions)",
    2: "강화된 예방수칙 실천(Practice Enhanced Precautions)",
    3: "불필요한 여행 자제 권고(Reconsider Nonessential Travel)",
    4: "여행 자제(Avoid All Travel)",
}


def fetch_travel_notices() -> list[dict] | None:
    """CDC 여행 건강경보 전체 목록(최신순, RSS 원본 순서). 실패 시 None."""
    try:
        resp = requests.get(RSS_URL, timeout=TIMEOUT, headers=USER_AGENT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall("./channel/item")
    except Exception:
        return None

    notices = []
    for it in items:
        title = (it.findtext("title") or "").strip()
        m = _LEVEL_RE.match(title)
        level = int(m.group(1)) if m else None
        headline = m.group(2).strip() if m else title
        notices.append({
            "level": level,
            "headline": headline,
            "description": (it.findtext("description") or "").strip(),
            "link": it.findtext("link"),
            "pub_date": it.findtext("pubDate"),
        })
    return notices


def travel_notices_summary() -> dict:
    """레벨별 집계 + 고위험(3·4단계) 목록. RSS 조회 실패 시 정직하게 unavailable."""
    notices = fetch_travel_notices()
    if notices is None:
        return {
            "data_available": False,
            "reason": "CDC RSS 조회 실패(네트워크 등) — 값 없음",
        }

    by_level = {1: 0, 2: 0, 3: 0, 4: 0}
    for n in notices:
        if n["level"] in by_level:
            by_level[n["level"]] += 1

    high_severity = [n for n in notices if (n["level"] or 0) >= 3]

    return {
        "data_available": True,
        "total_notices": len(notices),
        "by_level": by_level,
        "level_meaning": LEVEL_MEANING,
        "high_severity_notices": high_severity,
        "all_notices": notices,
        "levels_measured": True,               # CDC가 매긴 등급 자체는 실측
        "data_source": "CDC Travelers' Health (무료, 키 불필요)",
        "note": "레벨은 CDC 공식 여행위험 등급(1~4)이나, 이 피드엔 감염병 외 "
                "자연재해·대규모 행사 등도 섞여 있을 수 있음(원문 그대로 노출).",
    }

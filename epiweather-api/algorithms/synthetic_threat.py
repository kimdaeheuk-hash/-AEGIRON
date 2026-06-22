"""0단계 합성위협 탐지 — 유전체+역학+인텔 신호 종합을 Claude로 분석.

브라우저에서 Anthropic API를 직접 호출하면 키가 노출되므로,
프론트엔드 epiweather-stage0-v3.html의 AI 분석 로직을 서버 경유로 재구성.
bioRxiv API도 브라우저에서 직접 호출 시 CORS로 차단되므로 같은 이유로 서버 경유.
"""
from __future__ import annotations
import os
import re
import requests
import xml.etree.ElementTree as ET

BIORXIV_FALLBACK = [
    {"doi": "10.1101/2025.09.12.675911", "title": "First AI-generated viral genomes capable of replication", "authors": "King SH, Hie B", "date": "2025-09", "source": "FALLBACK"},
    {"doi": "10.1101/2025.00000", "title": "Foundation models for pathogen genome generation", "authors": "—", "date": "2025", "source": "FALLBACK"},
]

WHO_FALLBACK = [
    {"title": "Unusual cluster of pneumonia - Republic of Korea", "date": "2026-05", "risk": 55, "source": "FALLBACK"},
    {"title": "Novel influenza A variant - Southeast Asia", "date": "2026-04", "risk": 35, "source": "FALLBACK"},
    {"title": "Ebola outbreak update - Central Africa", "date": "2026-03", "risk": 42, "source": "FALLBACK"},
]

# WHO 전용 "Disease Outbreak News" RSS는 운영 중단됨 (404) — WHO 일반 뉴스 피드에서
# 발생/전염병 관련 키워드로 필터링. risk는 WHO가 매기는 공식 등급이 아니라
# 제목의 위험 키워드 기반 휴리스틱 점수임을 명시.
OUTBREAK_KEYWORDS = [
    "outbreak", "ebola", "marburg", "cholera", "mers", "mpox", "monkeypox",
    "avian influenza", "h5n1", "h9n2", "measles", "plague", "polio", "pheic",
    "public health emergency", "filovirus", "dengue", "yellow fever",
]
HIGH_RISK_KEYWORDS = ["pheic", "public health emergency", "ebola", "marburg", "filovirus"]


def fetch_who() -> list[dict]:
    """WHO 발생 동향 — 전용 DON RSS가 폐지되어 WHO 일반 뉴스 피드를 발생 키워드로 필터링."""
    try:
        r = requests.get(
            "https://www.who.int/rss-feeds/news-english.xml",
            timeout=10, headers={"User-Agent": "Mozilla/5.0 (EpiWeather/1.0)"},
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall("./channel/item")

        results = []
        for it in items:
            title = (it.findtext("title") or "").strip()
            low = title.lower()
            if not any(k in low for k in OUTBREAK_KEYWORDS):
                continue
            pub_date = (it.findtext("pubDate") or "")[:16]
            risk = 65 if any(k in low for k in HIGH_RISK_KEYWORDS) else 40
            results.append({
                "title": title, "date": pub_date,
                "link": it.findtext("link"), "risk": risk, "source": "WHO_REAL",
            })
        return results[:5] if results else WHO_FALLBACK
    except Exception:
        return WHO_FALLBACK


def fetch_biorxiv() -> list[dict]:
    """bioRxiv 프리프린트 검색.

    api.biorxiv.org의 공개 API는 키워드 검색을 지원하지 않는다 (날짜구간/DOI 조회만 가능) —
    원본 프로토타입의 호출은 애초에 잘못된 사용법이라 항상 403이 났다.
    대신 Europe PMC가 bioRxiv 프리프린트를 색인해 전문 검색을 제공하므로 이를 사용.
    """
    try:
        r = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": 'synthetic biology pathogen biosecurity AND SRC:PPR AND PUBLISHER:"bioRxiv"',
                "format": "json", "pageSize": 4, "sort": "P_PDATE_D desc",
            },
            timeout=10,
        )
        r.raise_for_status()
        items = r.json().get("resultList", {}).get("result") or []
        if not items:
            return BIORXIV_FALLBACK
        return [
            {
                "doi": p.get("doi"), "title": p.get("title") or "—",
                "authors": p.get("authorString") or "—",
                "date": p.get("firstPublicationDate") or "",
                "source": "bioRxiv_REAL",
            }
            for p in items
        ]
    except Exception:
        return BIORXIV_FALLBACK


def analyze_synthetic_threat(summary: dict, api_key: str | None = None) -> str:
    """설계-탐지 이중성 관점에서 0단계 스캔 결과를 4문항으로 분석."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY 환경변수 또는 api_key 파라미터 필요")

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = f"""바이오안보 전문가로서 아래 0단계 합성위협 탐지 결과를 분석하라.

데이터: {summary}

설계-탐지 이중성(바이러스를 설계할 줄 알아야 탐지할 수 있다)을 기반으로 한국어로 답하라. 각 2문장. 과장 없이.
1) 유전체 신호(CAI·CpG·엔트로피)가 자연 진화와 다른 점
2) 역학 패턴의 자연 여부
3) 종합 점수의 의미와 불확실성
4) 즉시 조치 2가지
번호로만."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        return (
            "Claude가 이 요청을 바이오안보 민감 주제로 분류해 응답을 거부했습니다 "
            "(실제 GenBank 접근번호를 '합성 기원 의심' 맥락에서 분석하는 요청은 "
            "이중용도 우려로 차단되는 경우가 있습니다). "
            "위의 Fisher's 통계 판정과 의사결정 트리 결과는 LLM 없이 계산된 것이므로 그대로 유효합니다."
        )
    return "".join(b.text for b in response.content if b.type == "text").strip()

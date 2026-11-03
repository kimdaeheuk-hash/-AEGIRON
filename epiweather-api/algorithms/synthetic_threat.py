"""0단계 합성위협 탐지 — 유전체+역학+인텔 신호 종합을 AI로 분석(Meta 우선·Claude 폴백).

브라우저에서 Anthropic API를 직접 호출하면 키가 노출되므로,
프론트엔드 epiweather-stage0-v3.html의 AI 분석 로직을 서버 경유로 재구성.
bioRxiv API도 브라우저에서 직접 호출 시 CORS로 차단되므로 같은 이유로 서버 경유.
"""
from __future__ import annotations
import os
import re
import requests
import xml.etree.ElementTree as ET
from . import meta_api as _meta

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


_CLAUDE_MODEL = "claude-sonnet-4-6"
# Meta 상한 4000 — 답은 4문항 단문(약 400토큰)이나 추론 모델은 생각을 먼저 쓴다
# (실전 프롬프트에 생각 2793 실측, ai_inference와 같은 관측). 800이면
# 생각이 상한을 다 먹어 답이 null로 온다. 실측 후 조정.
_META_ANALYZE_MAX_TOKENS = 4000
_META_TIMEOUT_SEC = 60

_REFUSAL_MESSAGE = (
    "Claude가 이 요청을 바이오안보 민감 주제로 분류해 응답을 거부했습니다 "
    "(실제 GenBank 접근번호를 '합성 기원 의심' 맥락에서 분석하는 요청은 "
    "이중용도 우려로 차단되는 경우가 있습니다). "
    "위의 Fisher's 통계 판정과 의사결정 트리 결과는 LLM 없이 계산된 것이므로 그대로 유효합니다."
)


def _require_local() -> bool:
    """주권 전용 모드 — ai_inference._require_local과 같은 읽기."""
    return os.environ.get("AEGIRON_REQUIRE_LOCAL", "off").lower() in ("on", "1", "true")


def _call_meta_analyze(system_text: str, user_text: str) -> str:
    """Meta 1회 호출(분석 본문). 실패는 예외 — 호출자가 Claude 폴백을 탄다."""
    base = _meta.base_url()
    if _require_local() and not _meta.is_host_sovereign(base):
        raise RuntimeError(
            f"주권 경로만 허용(AEGIRON_REQUIRE_LOCAL=on) — Meta 호스팅({base}) 차단")
    resp = requests.post(
        _meta.chat_url(),
        headers={"Authorization": f"Bearer {_meta.meta_key()}",
                 "Content-Type": "application/json"},
        json={
            "model": _meta.model(),
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": _META_ANALYZE_MAX_TOKENS,
        },
        timeout=_META_TIMEOUT_SEC,
    )
    try:
        resp.raise_for_status()
    except Exception:
        try:
            detail = (resp.text or "")[:500]
        except Exception:
            detail = ""
        err = RuntimeError(
            f"Meta HTTP {getattr(resp, 'status_code', '?')}: {detail}")
        _meta.record_layer_call(base, ok=False, error=str(err))
        raise err
    try:
        body = resp.json()
        content = (body["choices"][0].get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Meta 응답 본문 없음(HTTP 200이어도 성공이 아니다)")
        _meta.record_layer_call(base, ok=True)
        return content.strip()
    except Exception as e:
        _meta.record_layer_call(base, ok=False, error=f"{type(e).__name__}: {e}")
        raise


def _call_claude_analyze(system_text: str, user_text: str, key: str) -> tuple[str, bool]:
    """Claude 1회 호출. (본문, 거부 여부) — 거부는 실패가 아니라 응답이다."""
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=800,
        system=system_text,
        messages=[{"role": "user", "content": user_text}],
    )
    if response.stop_reason == "refusal":
        return _REFUSAL_MESSAGE, True
    return ("".join(b.text for b in response.content if b.type == "text").strip(), False)


def analyze_synthetic_threat(summary: dict, api_key: str | None = None) -> dict:
    """설계-탐지 이중성 관점에서 0단계 스캔 결과를 4문항으로 분석 — Meta 우선·Claude 폴백.

    summary에 'sequence'가 있으면 유전체 신호를 '실제로 계산'해(genome_signals)
    프롬프트에 넣는다 — LLM이 지어낸 숫자가 아니라 실측 지표를 해설하게 한다.
    반환 {"analysis", "llm_provider", "llm_model", "meta_error"} — 누가 썼는지를 남긴다.
    과업 프롬프트(4문항)는 양 경로 동일. Meta 필터 오탐 시 Claude가 잇는다.
    """
    from .ai_inference import BENIGN_USE_PREAMBLE

    claude_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    meta_key = _meta.meta_key()
    if not meta_key and not claude_key:
        raise ValueError("META_MODEL_API_KEY(또는 MODEL_API_KEY)·ANTHROPIC_API_KEY가 모두 없다")

    # 서열이 있으면 CAI·CpG·엔트로피를 실제로 계산해 붙인다(장난감→실측).
    summary = dict(summary)
    seq = summary.pop("sequence", None)
    if seq:
        from .genome_signals import screen_sequence
        summary["genome_signals_computed"] = screen_sequence(seq)

    system_text = (BENIGN_USE_PREAMBLE + "당신은 바이오안보 방어 자문가다. "
                   "과장 없이 한국어로 답하라.")
    user_text = f"""바이오안보 전문가로서 아래 0단계 합성위협 탐지 결과를 분석하라.

데이터: {summary}

설계-탐지 이중성(바이러스를 설계할 줄 알아야 탐지할 수 있다)을 기반으로 한국어로 답하라. 각 2문장. 과장 없이.
1) 유전체 신호(CAI·CpG·엔트로피)가 자연 진화와 다른 점
2) 역학 패턴의 자연 여부
3) 종합 점수의 의미와 불확실성
4) 즉시 조치 2가지
번호로만."""

    meta_error: str | None = None
    if meta_key:
        try:
            return {"analysis": _call_meta_analyze(system_text, user_text),
                    "llm_provider": "meta_model_api", "llm_model": _meta.model(),
                    "meta_error": None}
        except Exception as e:
            meta_error = f"{type(e).__name__}: {e}"
    if not claude_key:
        raise RuntimeError(f"Meta 실패 후 Claude 폴백 불가(키 없음): {meta_error}")
    text, _refused = _call_claude_analyze(system_text, user_text, claude_key)
    return {"analysis": text, "llm_provider": "anthropic",
            "llm_model": _CLAUDE_MODEL, "meta_error": meta_error}

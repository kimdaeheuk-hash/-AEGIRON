"""무료 웹서치 신호 — GroqWatch 대체 후보 (2026-08-28).

## 왜 만드는가

GroqWatch(`groq_watch.py`)가 **주기의 57% 를 실패**한다(2026-08-28 실측: 관측된
23개 주기 중 13개가 값없음). 뿌리는 티어 예산이다:

    프롬프트 3,831~4,993 토큰 중 **우리 지시문은 150 토큰 남짓**
    나머지 96% 는 compound-mini 가 **서버 쪽에서 제멋대로 끌어와 붙인 검색결과**
    분당 한도 8,000 → 한 번 호출이 예산의 60~71% 를 먹는다

★ 문제는 "토큰이 많다" 가 아니라 **"우리가 통제할 수 없다"** 는 것이다 ★
그래서 지금까지의 우회가 전부 실패했다 — 질의를 좁혀도(2026-08-26 실측),
재시도해도(오히려 429 를 자초), 주기를 늘려도(413 은 요청 '크기' 문제라 무관)
**주입되는 양은 우리 손 밖**이었다.

## 그래서 검색과 요약을 분리한다

    지금:  Groq compound-mini = 검색 + 요약   (검색량 통제 불가, 분당 8,000)
    여기:  Google News RSS    = 검색          (무료, API 키 불필요)
           Cerebras           = 요약          (하루 100만 토큰 무료)

둘 다 **이 리포에서 이미 매시간 도는 검증된 부품**이라 새로 검증할 게 적다:
  - `local_news._gnews()` / `fetch_local_feed()` — 179개 피드가 매시간 이걸로 돈다
  - `cerebras_classify` — 179개 피드 제목을 한 번의 호출로 배치 분류, 매 주기 성공

Cerebras 의 `gpt-oss-120b` 는 **compound-mini 가 내부적으로 쓰는 바로 그 모델**이다.
품질이 떨어지는 게 아니라 **웹서치가 안 붙어서 폭발하지 않을 뿐**이다.

## 예산 (실측 기반 추정)

    한 번 호출: 제목 40개 × ~15토큰 + 지시문 ~200 ≈ 800 토큰
    하루 24회 = 약 19,200 토큰 → Cerebras 하루 한도 100만의 **약 2%**

## ⚠️ 아직 확인 안 된 것 — 이건 실험이다

Google News RSS 는 compound-mini 의 웹서치보다 **얕다.** GroqWatch 가 잡던 것을
이쪽도 잡는지는 **나란히 돌려봐야 안다.** 그래서 이 모듈은 당장 GroqWatch 를
대체하지 않는다 — 같은 주기에 둘 다 돌려 로그로 대조한다.
소스 헬스(FREE_SOURCE_HEALTH_KEYS)에도 아직 넣지 않는다. 넣으면 실험 중인 층이
실패할 때 경보가 울려 진짜 사고와 섞인다.

*"모킹 테스트는 내 가설을 검증하지 실제를 검증하지 않는다"*(2026-08-26 교훈).
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse

import requests

from .cerebras_classify import CEREBRAS_URL, MODEL, TIMEOUT as CEREBRAS_TIMEOUT
from .local_news import fetch_local_feed

# 전 세계 영어권 대상 질의. 국가별 현지어 피드(local_news)가 이미 179개 돌고
# 있으므로, 이 층은 그 그물에 안 걸리는 **전 지구 규모 보도**를 노린다.
GLOBAL_TERMS = [
    "outbreak", "epidemic", "disease outbreak", "ebola", "cholera",
    "dengue", "mpox", "measles", "bird flu", "H5N1", "marburg",
]
# `when:1d` 는 Google News 검색 연산자(최근 1일). 혹시 무시되더라도 RSS 자체가
# 최신순이라 조용히 나빠질 뿐 깨지지는 않는다 — 대조 주기에 결과 개수로 확인한다.
RECENCY = "when:1d"

# ★ 토큰을 우리가 통제하는 지점이 여기다 ★ GroqWatch 는 이 손잡이가 없었다.
MAX_HEADLINES = 40
MAX_TITLE_CHARS = 200

VALID_URGENCY = {"low", "medium", "high"}

PROMPT = """오늘은 {today}야. 아래는 최근 24시간 전 세계 뉴스 검색으로 모은
감염병 관련 기사 제목 목록이다(중복·무관 기사가 섞여 있을 수 있다).

이 중 **실제로 진행 중인 발병·확산·집단감염 보도**가 있는지 판단해라.
여행경보·보건정책 발표·연구비 지원·과거사건 회고·백신 승인 같은 것은 아니다.

반드시 아래 JSON 형식으로만 답해(다른 텍스트·설명 절대 금지):
{{"has_new_signal": true 또는 false, "summary": "한국어 2문장 이내 요약 또는 null", "diseases": ["질병명"], "urgency": "low", "medium", "high" 중 하나}}

제목 목록:
{headlines}"""


class NewsWatchError(RuntimeError):
    """이 층의 실패. **종류를 반드시 들고 다닌다.**

    2026-08-25 groq_watch·2026-08-28 mobility 에서 같은 교훈을 두 번 얻었다 —
    실패했다는 사실만 남기고 왜 실패했는지를 버리면 고칠 수 없다.
    """


class CerebrasRateLimited(NewsWatchError):
    """429 — Cerebras 쪽 한도(실측: 분당 요청 5회). 우리 버그가 아니다.

    local_news 가 같은 주기에 1회를 쓰므로 이 층까지 2회다. 여유가 크지만,
    수동 호출이 겹치면 걸릴 수 있어 종류를 따로 세운다.
    """


def _global_gnews_url() -> str:
    """전 지구 규모 Google News RSS 검색 URL.

    `local_news._gnews()` 는 국가별(hl/gl)이라 그대로 쓰지 않고, 같은 방식으로
    전 세계 영어권을 노린다. 질의 구조는 동일하다(OR 로 묶기).
    """
    query = f"({' OR '.join(GLOBAL_TERMS)}) {RECENCY}"
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def fetch_headlines() -> list[str]:
    """전 지구 규모 검색 결과 제목. 실패하면 종류를 담아 올린다.

    RSS 파싱은 `local_news.fetch_local_feed` 를 그대로 쓴다 — CDATA 처리까지
    이미 179개 피드로 검증된 코드다. 여기서 다시 짜면 같은 버그를 새로 만든다.
    """
    feed = fetch_local_feed(
        "global_watch", "en", "global", _global_gnews_url(), GLOBAL_TERMS
    )
    if feed.get("status") == "error":
        raise NewsWatchError(
            f"Google News RSS 수집 실패: {str(feed.get('error'))[:200]}"
        )
    titles = feed.get("_all_titles") or []
    # ★ 첫 항목은 기사가 아니라 채널 제목(= 우리 검색어)이다 ★
    # 안 버리면 검색어가 기사 제목 자리에 실린다. 2026-08-26 에 브리핑에서 실제로
    # 그럴 뻔했다 — `"сибирская язва OR падёж оленей OR…"` 가 헤드라인이 될 뻔했다.
    # RSS 채널 제목은 `"<질의>" - Google News` 꼴이라 그 둘 중 하나로 걸러낸다.
    titles = [
        t for t in titles
        if "Google News" not in t and " OR " not in t
    ]
    return [t[:MAX_TITLE_CHARS] for t in titles[:MAX_HEADLINES]]


def _cerebras_json(prompt: str, api_key: str) -> tuple[dict, dict]:
    """Cerebras 호출 1회 → (파싱된 dict, usage). 실패는 종류를 담아 올린다."""
    r = requests.post(
        CEREBRAS_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        timeout=CEREBRAS_TIMEOUT,
    )
    if r.status_code == 429:
        raise CerebrasRateLimited(f"Cerebras 분당 요청 한도(429): {r.text[:200]}")
    r.raise_for_status()

    # ── 실패 지점을 셋으로 나눈다 (groq_watch 와 같은 원칙) ──────────────
    try:
        payload = r.json()
    except Exception as e:
        raise NewsWatchError(
            f"Cerebras 의 HTTP 응답이 JSON 이 아님({type(e).__name__}): {r.text[:200]}"
        ) from e
    try:
        raw = payload["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise NewsWatchError(
            f"Cerebras 응답에 content 가 없음({type(e).__name__}): {str(payload)[:200]}"
        ) from e

    raw = raw.strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    try:
        data = json.loads(raw)
    except Exception as e:
        raise NewsWatchError(
            f"Cerebras 가 돌려준 content 를 JSON 으로 읽지 못함({type(e).__name__}): {raw[:200]}"
        ) from e
    if not isinstance(data, dict):
        raise NewsWatchError(f"Cerebras 응답이 객체가 아님: {type(data).__name__}")
    return data, (payload.get("usage") or {})


def fetch_news_pulse(api_key: str) -> dict:
    """Google News RSS 검색 + Cerebras 요약 1건.

    반환 형태는 `groq_watch.fetch_groq_pulse` 와 **의도적으로 동일**하다 —
    대조가 끝나고 갈아끼울 때 소비하는 쪽(signal_metrics·negative_space·
    brief_sections)을 건드리지 않아도 되게.

    실패하면 **예외를 올린다.** None 을 돌려주지 않는다(2026-08-25 교훈).
    """
    headlines = fetch_headlines()
    if not headlines:
        # 제목이 0개인 것은 '고장' 이 아니라 '이번엔 걸린 게 없음' 일 수 있다.
        # 다만 구분이 안 되면 안 되므로 headline_count 로 드러낸다.
        return {
            "has_new_signal": False, "summary": None, "diseases": [], "urgency": None,
            "tokens_used": None, "tokens_prompt": None,
            "headline_count": 0, "source": "google_news+cerebras",
        }

    today = dt.date.today().isoformat()
    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(headlines))
    data, usage = _cerebras_json(
        PROMPT.format(today=today, headlines=numbered), api_key
    )

    urgency = data.get("urgency")
    if urgency not in VALID_URGENCY:
        urgency = None
    diseases = data.get("diseases") or []
    if isinstance(diseases, str):
        diseases = [diseases]

    return {
        "has_new_signal": bool(data.get("has_new_signal", False)),
        "summary": data.get("summary"),
        "diseases": diseases,
        "urgency": urgency,
        "tokens_used": usage.get("total_tokens"),
        "tokens_prompt": usage.get("prompt_tokens"),
        # ↓ GroqWatch 에는 없던 것 — 얼마나 얕은지/깊은지 대조할 근거
        "headline_count": len(headlines),
        "source": "google_news+cerebras",
    }

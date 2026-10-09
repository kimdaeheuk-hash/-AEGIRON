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
import os
import urllib.parse

import requests

from .cerebras_classify import (
    CEREBRAS_URL, GROQ_MODELS, GROQ_URL, MODEL, TIMEOUT as CEREBRAS_TIMEOUT,
    WORST_CHARS_PER_TOKEN,
)
from .local_news import fetch_local_feed
from .news_fallback import NewsFallbackError, tavily_headlines

# 전 세계 영어권 대상 질의. 국가별 현지어 피드(local_news)가 이미 179개 돌고
# 있으므로, 이 층은 그 그물에 안 걸리는 **전 지구 규모 보도**를 노린다.
GLOBAL_TERMS = [
    "outbreak", "epidemic", "disease outbreak", "ebola", "cholera",
    "dengue", "mpox", "measles", "bird flu", "H5N1", "marburg",
    # ★ 고위험 병원체 (2026-10-07) ★ 이르쿠츠크 항페스트 연구소 연구원 사망(10-02 첫 보도)을
    # 이 층은 사흘 뒤(10-05 01:02 UTC)에야 언급했다. 위 질의에 `plague` 가 없어서 일반어
    # `outbreak` 에 우연히 걸린 것이다. 페스트·탄저는 사건 하나가 곧 뉴스가 되는 병원체라
    # 카운트가 쌓이기를 기다리는 지표로는 못 잡는다. ⚠️ 이 층은 **경보 점수에 연결돼 있지 않다**
    # (`news_pulse` 를 읽는 소비자가 없다 — `groq_pulse_urgency` 는 은퇴한 `groq_pulse` 키를 읽는다).
    # 그래서 이 보강은 '더 빨리 언급된다' 이지 '경보가 된다' 가 아니다. 연결은 별도 결정이다.
    "plague", "anthrax",
]
# Google 이 막혔을 때만 쓰는 Tavily 대체 질의(2026-10-09). Google 연산자(OR·when:)는 평문에서 의미가 없다.
FALLBACK_QUERY = "disease outbreak epidemic ebola cholera dengue mpox measles bird flu H5N1 marburg plague anthrax"
FALLBACK_KEY_ENV = "TAVILY_API_KEY"
GOOGLE_NEWS, TAVILY_NEWS = "google_news", "tavily_news"
# 가장 최근 `fetch_headlines()` 에 답한 공급자. `fetch_news_pulse` 가 `source` 에 싣는다 —
# 폴백이 조용히 도는 걸 막는다(모델 폴백이 `source` 에 이름을 남기는 것과 같은 이유).
_STATE: dict = {"provider": GOOGLE_NEWS}

# `when:1d` 는 Google News 검색 연산자(최근 1일). 혹시 무시되더라도 RSS 자체가
# 최신순이라 조용히 나빠질 뿐 깨지지는 않는다 — 대조 주기에 결과 개수로 확인한다.
RECENCY = "when:1d"

# ★ 토큰을 우리가 통제하는 지점이 여기다 ★ GroqWatch 는 이 손잡이가 없었다.
MAX_HEADLINES = 40
MAX_TITLE_CHARS = 200

# ── Groq 폴백 예산 (2026-08-28) ────────────────────────────────────────
# Cerebras 가 402 로 죽어 이 층이 매 주기 실패하고 있었다. cerebras_classify 가
# 쓰는 Groq 폴백을 여기에도 붙이는데, **예산을 그대로 쓰면 안 된다** —
# 로그 실측: 현지어 뉴스 재분류 11:57:44, NewsWatch 11:57:52. **8초 차이**다.
# 즉 둘이 같은 분당 한도(TPM 8,000) 창을 나눠 쓴다. 재분류 쪽이 본진이므로
# 이 층은 작은 몫만 가져간다.
GROQ_TOKEN_SLICE = 2000
GROQ_MAX_HEADLINES = 20
GROQ_TITLE_CHARS = 90
PROMPT_OVERHEAD_TOKENS = 400   # 지시문 + JSON 형식 안내 몫(넉넉히)

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


def _fetch_headlines_google() -> list[str]:
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
    return [t for t in titles if "Google News" not in t and " OR " not in t]


def fetch_headlines() -> list[str]:
    """전 지구 규모 검색 결과 제목. 실패하면 종류를 담아 올린다.

    RSS 파싱은 `local_news.fetch_local_feed` 를 그대로 쓴다 — CDATA 처리까지
    이미 179개 피드로 검증된 코드다. 여기서 다시 짜면 같은 버그를 새로 만든다.

    Google 이 실패하면 Tavily 로 한 번 넘어간다(`TAVILY_API_KEY` 가 있을 때, 2026-10-09 —
    10-08 15:00 UTC 부터 Google 503 으로 이 층이 9주기 연속 `중단` 이었다). 누가 답했는지는
    `_STATE["provider"]` → `fetch_news_pulse` 의 `source` 가 남긴다. 이 층은 경보 점수에 연결돼
    있지 않아(위 GLOBAL_TERMS 주석) 대체 경로가 더 얕아도 거짓 경보로 번지지 않는다.
    """
    _STATE["provider"] = GOOGLE_NEWS
    try:
        titles = _fetch_headlines_google()
    except NewsWatchError as google_err:
        key = os.environ.get(FALLBACK_KEY_ENV)
        if not key:
            raise NewsWatchError(f"{google_err} · 대체 공급자 없음({FALLBACK_KEY_ENV} 미설정)") from google_err
        try:
            titles = tavily_headlines(FALLBACK_QUERY, key)
        except NewsFallbackError as fb_err:
            g = str(google_err).removeprefix("Google News RSS 수집 실패: ")[:40]
            raise NewsWatchError(f"Google News RSS 수집 실패: {g} · 대체 {fb_err}") from fb_err
        _STATE["provider"] = TAVILY_NEWS
    return [t[:MAX_TITLE_CHARS] for t in titles[:MAX_HEADLINES]]


def groq_headlines(headlines: list[str]) -> list[str]:
    """Groq 폴백용으로 제목 목록을 예산 안까지 깎는다.

    ★ 이 함수가 지키는 약속 ★ 결과 프롬프트가 `GROQ_TOKEN_SLICE` 를 넘지 않는다.
    글자수→토큰 환산은 `cerebras_classify.WORST_CHARS_PER_TOKEN` 을 그대로 쓴다
    (영어는 실제로 4자/토큰쯤이지만, 제목에 현지어가 섞이면 1.2 에 가까워진다 —
    2026-08-28 에 4자/토큰으로 잡았다가 예산의 3배를 쐈다).
    """
    trimmed = [t[:GROQ_TITLE_CHARS] for t in headlines[:GROQ_MAX_HEADLINES]]
    budget_chars = int((GROQ_TOKEN_SLICE - PROMPT_OVERHEAD_TOKENS) * WORST_CHARS_PER_TOKEN)
    out: list[str] = []
    used = 0
    for t in trimmed:
        cost = len(t) + 4          # "12: " 번호 접두 + 줄바꿈
        if used + cost > budget_chars:
            break
        out.append(t)
        used += cost
    return out


def _llm_json(prompt: str, url: str, model: str, api_key: str) -> tuple[dict, dict]:
    """LLM 호출 1회 → (파싱된 dict, usage). 실패는 종류를 담아 올린다.

    Cerebras 와 Groq 는 둘 다 OpenAI 호환 스키마라 URL·모델만 갈아끼우면 된다.
    """
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        timeout=CEREBRAS_TIMEOUT,
    )
    if r.status_code == 429:
        raise CerebrasRateLimited(f"분당 요청 한도(429) {url}: {r.text[:200]}")
    r.raise_for_status()

    # ── 실패 지점을 셋으로 나눈다 (groq_watch 와 같은 원칙) ──────────────
    try:
        payload = r.json()
    except Exception as e:
        raise NewsWatchError(
            f"{model} 의 HTTP 응답이 JSON 이 아님({type(e).__name__}): {r.text[:200]}"
        ) from e
    try:
        raw = payload["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise NewsWatchError(
            f"{model} 응답에 content 가 없음({type(e).__name__}): {str(payload)[:200]}"
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
            f"{model} 이 돌려준 content 를 JSON 으로 읽지 못함({type(e).__name__}): {raw[:200]}"
        ) from e
    if not isinstance(data, dict):
        raise NewsWatchError(f"{model} 응답이 객체가 아님: {type(data).__name__}")
    return data, (payload.get("usage") or {})


def latest_pulse(max_age_hours: float = 3.0, now: dt.datetime | None = None,
                 log_file=None, tail_bytes: int = 3_000_000) -> dict | None:
    """수집 기록(signals_log.jsonl)에서 **가장 최근의 NewsWatch 결과**. 없거나 오래됐으면 None.

    브리핑이 읽는다. 네트워크를 부르지 않는다 — 수집 주기가 이미 남겨 둔 값을 읽을 뿐이다.
    오래된 요약을 '지금'처럼 보이지 않게 `max_age_hours` 를 넘기면 None(= 섹션을 빼고 말없이 둔다).
    파일 끝에서 `tail_bytes` 만 읽는다(기록은 수 MB 라 통째로 읽지 않는다).
    """
    import json
    from pathlib import Path

    from .signal_metrics import LOG_FILE

    path = Path(log_file) if log_file else LOG_FILE
    if not path.exists():
        return None
    now = now or dt.datetime.now()
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - tail_bytes))
        chunk = f.read().decode("utf-8", errors="ignore")
    lines = chunk.splitlines()
    if size > tail_bytes:
        lines = lines[1:]                      # 잘린 첫 줄은 버린다
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pulse = rec.get("news_pulse") if isinstance(rec, dict) else None
        if not isinstance(pulse, dict):
            continue
        try:
            at = dt.datetime.fromisoformat(str(rec.get("timestamp")))
        except ValueError:
            return None
        if at.tzinfo is not None:
            at = at.replace(tzinfo=None)
        if (now - at).total_seconds() > max_age_hours * 3600:
            return None                        # 가장 최근 값도 낡았다 — 현재형으로 내놓지 않는다
        if not pulse.get("has_new_signal") or not pulse.get("summary"):
            return None
        return {**pulse, "observed_at": at.isoformat()}
    return None


def fetch_news_pulse(api_key: str | None, groq_key: str | None = None) -> dict:
    """Google News RSS 검색 + LLM 요약 1건.

    반환 형태는 `groq_watch.fetch_groq_pulse` 와 **의도적으로 동일**하다 —
    대조가 끝나고 갈아끼울 때 소비하는 쪽(signal_metrics·negative_space·
    brief_sections)을 건드리지 않아도 되게.

    실패하면 **예외를 올린다.** None 을 돌려주지 않는다(2026-08-25 교훈).
    """
    _STATE["provider"] = GOOGLE_NEWS      # fetch_headlines 가 대체로 넘어가면 거기서 바꾼다
    headlines = fetch_headlines()
    headline_provider = _STATE["provider"]
    if not headlines:
        # 제목이 0개인 것은 '고장' 이 아니라 '이번엔 걸린 게 없음' 일 수 있다.
        # 다만 구분이 안 되면 안 되므로 headline_count 로 드러낸다.
        return {
            "has_new_signal": False, "summary": None, "diseases": [], "urgency": None,
            "tokens_used": None, "tokens_prompt": None,
            # LLM 을 아예 안 불렀으니 모델 이름을 붙이지 않는다.
            "headline_count": 0, "headlines_found": 0, "source": headline_provider,
        }

    today = dt.date.today().isoformat()

    # ── 시도 순서: Cerebras → Groq 후보들 (2026-08-28) ──────────────────
    # Cerebras 는 402(무료 한도 소진)로 죽어 있다. 그런데 이 층은 **실패를
    # 예외로 올리는 게 계약**이라, 폴백이 없으면 매 주기 통째로 값이 빈다.
    # 로그로 확인된 사실이다 — `❌ NewsWatch 실패: HTTPError: 402 …` 가 계속.
    #
    # Groq 시도는 **제목을 깎아서** 보낸다. 같은 분(minute)에 현지어 뉴스
    # 재분류가 이미 TPM 예산을 쓰기 때문이다(`GROQ_TOKEN_SLICE` 주석 참조).
    attempts: list[tuple[str, str, str, str, list[str]]] = []
    if api_key:
        attempts.append(("cerebras", CEREBRAS_URL, MODEL, api_key, headlines))
    if groq_key:
        short = groq_headlines(headlines)
        attempts += [(f"groq({m})", GROQ_URL, m, groq_key, short) for m in GROQ_MODELS]
    if not attempts:
        raise NewsWatchError("CEREBRAS_API_KEY·GROQ_API_KEY 둘 다 없음")

    data = usage = None
    provider, used_headlines = None, headlines
    failures: list[str] = []
    errors: list[Exception] = []
    for name, url, model, key, hl in attempts:
        numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(hl))
        try:
            data, usage = _llm_json(PROMPT.format(today=today, headlines=numbered),
                                    url, model, key)
        except Exception as e:
            errors.append(e)
            failures.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
            # 404 는 '그 계정에 그 모델이 없다' 이므로 다음 후보로 넘어갈 값어치가
            # 있다. 402·429 는 계정·한도 문제라 다음 Groq 모델도 똑같이 막힌다 —
            # 한도만 더 태울 뿐이라 거기서 멈춘다(cerebras_classify 와 같은 규칙).
            if name.startswith("groq(") and "404" not in str(e):
                break
            continue
        provider, used_headlines = name, hl
        break

    if data is None:
        # ★ 후보가 하나뿐이었으면 원래 예외를 그대로 올린다 ★
        # 이 층의 실패 종류(CerebrasRateLimited·HTTPError…)를 collector 가
        # 타입 이름으로 로그에 찍는다. 통째로 감싸면 그 구분이 사라진다.
        if len(errors) == 1:
            raise errors[0]
        raise NewsWatchError("모든 LLM 실패 — " + " | ".join(failures)) from errors[0]

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
        # Groq 폴백은 제목을 깎아 보내므로 **실제로 모델이 본 개수**를 적는다.
        # 검색된 개수를 적으면 대조가 거짓말이 된다.
        "headline_count": len(used_headlines),
        "headlines_found": len(headlines),
        # 어느 모델이 답했는지 남긴다 — 폴백이 조용히 도는 걸 막는다.
        "source": f"{headline_provider}+{provider}",
    }

"""Cerebras 초고속 뉴스 제목 분류 — Phase 4 ㉔.

local_news.py의 기존 방식은 RSS 원문 전체에서 키워드(예: "ugonjwa"=병)가
한 번이라도 나오면 무조건 히트로 세는 단순 카운트라 오탐이 많다 — 여행경보·
보건정책·연구비 지원 기사도 "병" 관련 단어를 쓰기 때문. Cerebras(신용카드
없이 가입, 하루 100만 토큰 무료, 초고속 추론)로 제목들을 배치 분류해서
"실제 발병·집단감염 보도"만 골라내 정확도를 높인다.

Cerebras는 Groq의 compound 계열과 달리 자체 웹서치가 없는 순수 추론
엔진이라, 이미 갖고 있는 텍스트(RSS 제목)를 분류하는 이 용도에 맞춤.

## ★ 2026-08-28 — Cerebras 무료 쿼터가 끝났다. Groq 로 넘어간다 ★

실측(프로덕션 로그):

    ❌ 현지어 뉴스 LLM 재분류 실패 … 결제 필요(402):
       {"message":"Payment required to access this resource. Visit your billing
        tab.","type":"payment_required_error","param":"quota"}

`Cerebras(하루 100만 토큰 무료)` 라는 위의 2026-07-08 설명은 **더 이상 사실이
아니다.** 유료 전환은 선택지가 아니므로 같은 계정에 이미 있는 **Groq 로 대체**한다.

**Groq 가 살아 있다는 건 오늘 로그로 확인됐다** — GroqWatch 가 `⚙ Groq 토큰
3990/8000` 처럼 매 주기 성공한다. 다만 **분당 한도가 8,000 토큰**이라
179개 피드 전량은 못 넣는다. 그래서 넣지 않는다:

## 넣을 필요가 없다 — LLM 이 답을 바꿀 수 있는 피드만 본다

고경보 판정은 `hit_ratio >= 0.15` 다. LLM 재분류의 값어치는 **키워드 오탐을
걷어내는 것**이므로, 임계 근처·위의 피드만 보면 결과가 같다. 임계에서 한참
아래인 피드는 LLM 이 무슨 말을 해도 고경보가 안 된다.

    CANDIDATE_RATIO   임계보다 조금 아래까지 후보로 잡는다
    MAX_TITLES_PER_FEED · MAX_TOTAL_TITLES   프롬프트 크기를 우리가 통제한다

이 상한이 요점이다. 예전엔 `_all_titles` 를 **무제한**으로 밀어 넣었다 —
그래서 하루 100만 토큰짜리 계정이 필요했다.
(NewsWatch 에서 배운 것과 같다: 통제할 수 없는 프롬프트가 문제였다.)
"""
from __future__ import annotations
import json

import requests

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
# 실측 확인(2026-07-08): 이 계정에서 /v1/models로 실제 제공되는 모델은
# gpt-oss-120b · gemma-4-31b · zai-glm-4.7 뿐 — llama 계열은 없음.
MODEL = "gpt-oss-120b"
TIMEOUT = 30

# ── Groq 대체 경로 (2026-08-28) ──────────────────────────────────────
# 웹서치가 붙는 compound 계열이 아니라 **순수 추론 모델**을 쓴다. GroqWatch 를
# 터뜨린 413/429 는 compound-mini 가 서버 쪽에서 끌어온 검색결과 때문이었고,
# 여기서는 우리가 준 제목만 들어가므로 그 문제가 없다.
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
# 실측(2026-08-26, 429 응답 원문): 무료 티어 TPM 8,000.
# 같은 주기에 GroqWatch 가 4,000~5,700 을 쓰지만 그건 1분 뒤 다른 분(minute)이라
# 겹치지 않는다. 그래도 여유를 두고 상한을 잡는다.
GROQ_TPM_BUDGET = 8000
PROMPT_TOKEN_MARGIN = 2000      # 지시문 + 응답 + 안전 여유

# ── 프롬프트 크기를 우리가 통제하는 지점 ─────────────────────────────
# ⚠️ 토큰 계산에서 한 번 틀렸다(2026-08-28): 영어 기준 "4자 = 1토큰"으로 잡았다가
# 상한이 예산의 3배가 됐다. **이 시스템의 제목은 대부분 영어가 아니다** —
# 한국어·네팔어(데바나가리)·아랍어는 대략 **1~1.5자당 1토큰**이다.
# 그래서 가장 나쁜 쪽(1.2자/토큰)으로 잡는다. 테스트가 이 가정을 고정한다.
WORST_CHARS_PER_TOKEN = 1.2
CANDIDATE_RATIO = 0.10          # 고경보 임계(0.15)보다 조금 아래까지 후보
MAX_TITLES_PER_FEED = 5
MAX_TOTAL_TITLES = 60
TITLE_MAX_CHARS = 90            # 헤드라인의 요지는 앞쪽에 있다

# ⚠️ 이 상한이면 한 주기에 **상위 12개 안팎의 피드**만 재분류된다(오늘 고경보는
# 43개). 비율이 높은 것부터 들어가므로 "가장 의심스러운 것"은 덮지만, **전량
# 커버는 아니다.** 나머지는 키워드 값이 그대로 쓰인다(그게 지금 상태이므로
# 나빠지는 건 없다). 커버가 얇으면 여러 번 나눠 부르는 걸 다음 건으로 본다 —
# 무료 티어는 분당 한도라 그러려면 주기 중간에 기다려야 해서 값이 큰 변경이다.
# 실제로 몇 개가 분류됐는지는 수집 로그의 `LLM 재분류 N개 피드` 로 나온다.

PROMPT_TEMPLATE = """다음은 {lang} 뉴스 제목 목록이다(0번부터 번호 매김). 각 제목이
"실제로 진행 중인 감염병 발병·확산·집단감염 관련 보도"인지 판단해라.
여행경보·보건정책 발표·연구비 지원·과거사건 회고·무관한 일반 기사는 전부 아니오.

반드시 JSON 배열만 출력해(다른 텍스트·설명 절대 금지):
[{{"i": 0, "relevant": true 또는 false}}, ...]

제목 목록:
{titles}"""


def classify_headlines(titles: list[str], lang: str, api_key: str) -> list[bool] | None:
    """제목별 실제 발병 보도 여부 배치 판정. 실패하면 None(호출측이 키워드 매칭으로 폴백)."""
    if not titles:
        return []
    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(titles))
    try:
        r = requests.post(
            CEREBRAS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(lang=lang, titles=numbered),
                }],
                "temperature": 0.1,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
    except Exception:
        return None

    results = [False] * len(titles)
    for item in data:
        if not isinstance(item, dict):
            continue
        i = item.get("i")
        if isinstance(i, int) and 0 <= i < len(titles):
            results[i] = bool(item.get("relevant"))
    return results


MULTI_PROMPT_TEMPLATE = """다음은 여러 나라 뉴스 제목 목록이다(0번부터 전체 번호 매김,
대괄호 안은 언어). 각 제목이 "실제로 진행 중인 감염병 발병·확산·집단감염 관련
보도"인지 판단해라. 여행경보·보건정책 발표·연구비 지원·과거사건 회고·무관한
일반 기사는 전부 아니오.

반드시 JSON 배열만 출력해(다른 텍스트·설명 절대 금지):
[{{"i": 0, "relevant": true 또는 false}}, ...]

제목 목록:
{titles}"""


class CerebrasUnavailable(RuntimeError):
    """Cerebras 를 쓸 수 없다 — **왜인지를 반드시 들고 다닌다.**

    ★ 2026-08-28 사고 ★ 이 모듈은 실패를 통째로 삼켰다:

        except Exception:
            return          # 로그 한 줄도 안 남긴다

    그러면 `llm_hit_ratio` 가 안 채워지고, local_news 의 고경보 판정이
    `r.get("llm_hit_ratio", r.get("hit_ratio", 0))` 를 통해 **조용히 키워드
    매칭으로 떨어진다.** 그 키워드 방식이 바로 이 모듈을 만든 이유였다 —
    "여행경보·보건정책·연구비 지원 기사도 '병' 관련 단어를 쓴다"(2026-07-08).
    즉 **개선이 꺼진 채로 돌아가는데 아무도 모르는 상태**가 된다.

    실측: 계정이 `402 Payment Required` 를 돌려주고 있었고, Railway 로그를
    2026-08-27 06:00 UTC 까지 거슬러도 `LLM 재분류` 태그가 한 번도 없다.
    **최소 29시간** 키워드 기준으로 돌았고, 시작 시점은 로그 보존 한계로
    더 올라가지 못한다.

    (오늘 같은 구조를 네 번째로 만났다 — GroqWatch · Mobility · 은퇴 소스 · 여기.)
    """


class CerebrasPaymentRequired(CerebrasUnavailable):
    """402 — 무료 티어가 끝났거나 결제가 필요하다. 우리 버그가 아니다.

    소스 고장과 구분되어야 한다: 수집 자체는 멀쩡히 돌고, 분류 품질만 떨어진다.
    """


class CerebrasRateLimited(CerebrasUnavailable):
    """429 — 분당 요청 한도(실측: 5회/분)."""


def select_entries(feeds: list[dict]) -> list[tuple[int, str]]:
    """분류할 (feed 인덱스, 제목) 목록 — **상한이 걸린 채로** 고른다.

    ★ 여기가 프롬프트 크기를 우리가 통제하는 지점이다 (2026-08-28) ★
    예전엔 179개 피드의 `_all_titles` 를 **무제한**으로 밀어 넣었다. 그래서
    "하루 100만 토큰" 짜리 계정이 필요했고, 그 무료 티어가 끝나자 통째로 멈췄다.

    고경보 판정은 `hit_ratio >= 0.15` 이고, LLM 재분류의 값어치는 **키워드 오탐을
    걷어내는 것**이다. 그러니 임계 근처·위의 피드만 보면 결과가 같다 — 임계에서
    한참 아래인 피드는 LLM 이 무슨 말을 해도 고경보가 되지 않는다.
    비율이 높은 피드부터 채워서, 상한에 걸리면 **가장 중요한 것부터** 들어간다.
    """
    candidates = [
        (fi, feed) for fi, feed in enumerate(feeds)
        if feed.get("status") == "ok"
        and (feed.get("hit_ratio") or 0) >= CANDIDATE_RATIO
        and feed.get("_all_titles")
    ]
    candidates.sort(key=lambda x: x[1].get("hit_ratio") or 0, reverse=True)

    entries: list[tuple[int, str]] = []
    for fi, feed in candidates:
        for t in (feed.get("_all_titles") or [])[:MAX_TITLES_PER_FEED]:
            if len(entries) >= MAX_TOTAL_TITLES:
                return entries
            entries.append((fi, t[:TITLE_MAX_CHARS]))
    return entries


def _post(url: str, model: str, api_key: str, prompt: str) -> "requests.Response":
    return requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        timeout=TIMEOUT,
    )


def classify_multi_feed(
    feeds: list[dict], api_key: str, groq_key: str | None = None
) -> str | None:
    """후보 피드의 제목을 한 번의 호출로 배치 분류해 각 feed dict에
    llm_relevant_count/llm_hit_ratio/llm_relevant_titles를 채워 넣는다(in-place).

    반환: 성공이면 None, 실패면 **사유 문자열**(호출부가 로그로 올린다).
    예전엔 `except Exception: return` 이라 실패가 흔적 없이 사라졌다.

    ★ 제공자 순서: Cerebras → Groq (2026-08-28) ★
    Cerebras 무료 쿼터가 끝나(402) 통째로 멈췄다. 같은 계정에 이미 있고 **오늘
    로그로 살아있음이 확인된** Groq 로 넘어간다. Cerebras 를 먼저 시도하는 이유는
    쿼터가 복구되면 자동으로 돌아오게 하려는 것이다 — 사람이 다시 손댈 필요가 없다.

    피드별로 따로 호출하면 분당 요청 제한(실측: 5회/분)에 금방 걸려 뒤쪽 피드가
    조용히 빠지므로, 전부 하나로 합쳐서 호출 1회로 끝낸다."""
    entries = select_entries(feeds)
    if not entries:
        return "분류할 후보 제목이 없음(전 피드가 임계 한참 아래)"

    numbered = "\n".join(f"{gi}: [{feeds[fi]['lang']}] {t}" for gi, (fi, t) in enumerate(entries))
    prompt = MULTI_PROMPT_TEMPLATE.format(titles=numbered)

    # Cerebras 먼저, 실패하면 Groq. **두 사유를 모두 들고 간다** — 하나만 남기면
    # "어느 쪽이 왜 안 됐는지" 를 또 추측하게 된다.
    attempts: list[tuple[str, str, str, str]] = [("Cerebras", CEREBRAS_URL, MODEL, api_key)]
    if groq_key:
        attempts.append(("Groq", GROQ_URL, GROQ_MODEL, groq_key))

    reasons: list[str] = []
    for name, url, model, key in attempts:
        if not key:
            reasons.append(f"{name}: 키 없음")
            continue
        reason = _try_classify(feeds, entries, url, model, key, prompt)
        if reason is None:
            return None                      # 성공
        reasons.append(f"{name}: {reason}")
    return " | ".join(reasons)


def _try_classify(feeds, entries, url: str, model: str, api_key: str,
                  prompt: str) -> str | None:
    """제공자 하나로 시도. 성공이면 None, 실패면 사유."""
    try:
        r = _post(url, model, api_key, prompt)
        # ── 실패 종류를 갈라서 남긴다 ────────────────────────────────────
        # 402(결제)·429(한도)·5xx(장애)·형식 문제는 조치가 전혀 다르다.
        # 예전엔 넷이 전부 같은 침묵이었다.
        if r.status_code == 402:
            return f"결제 필요(402) — 무료 티어가 끝났을 수 있다: {r.text[:150]}"
        if r.status_code == 429:
            return f"분당 요청 한도(429): {r.text[:150]}"
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return f"응답이 배열이 아님({type(data).__name__}): {raw[:150]}"
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:180]}"

    relevant_flags = [False] * len(entries)
    for item in data:
        if not isinstance(item, dict):
            continue
        gi = item.get("i")
        if isinstance(gi, int) and 0 <= gi < len(entries):
            relevant_flags[gi] = bool(item.get("relevant"))

    per_feed_titles: dict[int, list[str]] = {}
    per_feed_relevant: dict[int, list[str]] = {}
    for (fi, t), is_rel in zip(entries, relevant_flags):
        per_feed_titles.setdefault(fi, []).append(t)
        if is_rel:
            per_feed_relevant.setdefault(fi, []).append(t)

    for fi, feed in enumerate(feeds):
        titles = per_feed_titles.get(fi)
        if not titles:
            # 후보에 안 든 피드다 — 임계에서 한참 아래라 LLM 이 봐도 결과가
            # 안 바뀐다. llm_hit_ratio 를 안 채우므로 키워드 값이 그대로 쓰인다.
            continue
        relevant = per_feed_relevant.get(fi, [])
        feed["llm_relevant_count"] = len(relevant)
        feed["llm_hit_ratio"] = round(len(relevant) / max(len(titles), 1), 3)
        feed["llm_relevant_titles"] = relevant[:5]
    return None

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

# ★ 모델 ID 를 찍지 않는다 — 후보를 순서대로 시도하고 어느 게 됐는지 로그로 남긴다 ★
# 2026-08-28 에 `llama-3.3-70b-versatile` 로 찍었다가 프로덕션에서 404 가 났다.
# 이 세션은 Groq 가 프록시에 막혀 /v1/models 를 볼 수 없으므로, **검증할 수 없는
# 것을 하나로 단정하는 대신** 후보를 두고 프로덕션이 답하게 한다.
#
# 첫 후보는 추측이 아니라 근거가 있다 — `groq_watch.py` 에 기록된 이 계정의
# 실제 429 응답 원문이 모델 ID 를 그대로 알려준다:
#     Rate limit reached for model `openai/gpt-oss-120b`
# 게다가 Cerebras 가 쓰던 것과 같은 모델이라 분류 품질도 같은 자리에서 출발한다.
GROQ_MODELS = [
    "openai/gpt-oss-120b",      # 위 429 원문으로 이 계정에 있음이 확인된 것
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",  # 2026-08-28 에 404 났던 것 — 마지막에 둔다
]
# 실측(2026-08-26, 429 응답 원문): 무료 티어 TPM 8,000.
# 같은 주기에 GroqWatch 가 4,000~5,700 을 쓰지만 그건 1분 뒤 다른 분(minute)이라
# 겹치지 않는다. 그래도 여유를 두고 상한을 잡는다.
GROQ_TPM_BUDGET = 8000
PROMPT_TOKEN_MARGIN = 2000      # 지시문 + 응답 + 안전 여유

# ── ★ 2026-08-30 — 실패가 402·429 가 아니라 전부 JSONDecodeError 였다 ★ ────
# 08-29 실측(프로덕션 로그, UTC 00~23시 24주기):
#
#     성공 10주기 / 실패 14주기(58%)  · 18~23시는 6주기 연속 실패
#     실패 14회의 사유가 **전부** Cerebras 402 + Groq JSONDecodeError.
#     429 도 402 도 Groq 쪽에서는 한 번도 없었다.
#
# 즉 **한도 문제가 아니라 응답을 못 읽은 것**이다. 파싱 실패 지점이
# char 0 · 2 · 33 · 167 · 205 · 405 · 756 · 1079 · 1360 · 1552 · 1612 로
# 제각각인데, 이건 "형식이 틀렸다" 가 아니라 **매번 다른 길이에서 잘렸다** 는
# 모양이다.
#
# 대조가 원인을 좁혀준다: NewsWatch 는 **같은 모델·같은 파라미터**로 같은 24주기
# 중 22번 성공했다. 다른 건 출력 길이뿐이다 — NewsWatch 는 두 문장, 이쪽은
# 60개짜리 JSON 배열. 그래서 출력을 줄이고, 상한을 우리가 쥐고, 잘려도 건진다.
#
# ⚠️ 다만 "잘림" 과 "애초에 JSON 이 아님" 은 **아직 갈리지 않았다.** 코드가
#    finish_reason 을 한 번도 안 찍었기 때문이다(이 커밋에서 찍게 했다).
#    다음 점검 한 번이면 갈린다 — 단정하지 말고 로그를 읽어라.

# 응답 상한을 우리가 명시한다. 예전엔 안 줘서 제공자 기본값에 맡겼고, 그 기본값이
# 얼마인지 아무도 모른 채 잘림을 당했다. 프롬프트 예산(6,000)과 합쳐 TPM 8,000
# 안에 들도록 1,500 으로 잡는다.
MAX_COMPLETION_TOKENS = 1500

# gpt-oss 계열은 **추론 토큰을 완성 토큰과 같은 예산에서 먼저 쓴다.** 60개를
# 분류하며 추론이 예산을 다 먹으면 정작 배열이 못 나온다. 'low' 로 낮춰 예산을
# 배열 쪽에 돌린다.
#
# ⚠️ 이 파라미터가 이 계정·이 모델에서 받아들여지는지는 **여기서 검증할 수 없다**
#    (샌드박스가 프록시에 막혀 Groq 에 못 닿는다). 그래서 단정하지 않는다 —
#    400 이 오면 빼고 한 번 더 보내고 어느 쪽이 먹었는지 남긴다. 모델 ID 를
#    찍었다가 404 를 맞은 2026-08-28 의 교훈이 그대로 적용된다.
REASONING_EFFORT = "low"

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
    """제목별 실제 발병 보도 여부 배치 판정. 실패하면 None(호출측이 키워드 매칭으로 폴백).

    ⚠️ **현재 아무도 안 부른다**(2026-08-30 확인 — 실사용 경로는 `classify_multi_feed`).
    그래서 아래 `except Exception: return None` 과 상한 없는 요청을 2026-08-30
    수리에서 손대지 않았다. **살려 쓸 일이 생기면 먼저 고쳐라** — 이 모듈이
    네 번이나 사고를 낸 바로 그 모양(사유를 버리는 조용한 except)이 여기 남아 있다.
    """
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

해당하는 제목의 **번호만** 오름차순 JSON 배열로 출력해라. 다른 텍스트·설명은
절대 금지고, 해당하는 게 없으면 빈 배열 [] 만 출력해라.
예: [0, 3, 12]

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


def _post(url: str, model: str, api_key: str, prompt: str,
          reasoning_effort: str | None = None) -> "requests.Response":
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        # 상한을 우리가 쥔다 — 제공자 기본값이 얼마인지 모르는 채로 두지 않는다.
        "max_tokens": MAX_COMPLETION_TOKENS,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=TIMEOUT,
    )


def _message_text(message: dict) -> str:
    """모델이 실제로 쓴 글을 꺼낸다.

    gpt-oss 같은 추론 모델은 `content` 가 비고 추론이 `reasoning` 으로 따로 오는
    경우가 있다. 예전엔 `content` 만 봐서 그 경우가 **`Expecting value: line 1
    column 1 (char 0)`** 한 줄로만 남았다 — 빈 문자열을 파싱한 것이다.
    """
    text = (message.get("content") or "").strip()
    if not text:
        text = (message.get("reasoning") or "").strip()
    # <think>…</think> 로 감싸 오는 제공자도 있다. 닫혔으면 뒤쪽만 쓴다.
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    return text.strip("`").strip()


def _scan_array(text: str, start: int) -> tuple[list, bool]:
    """`text[start] == '['` 로 보고 **완성된 원소만** 순서대로 꺼낸다.

    ★ 잘려도 건지는 게 요점이다 ★ 예전엔 `json.loads` 한 방이라, 60개 중 59개가
    멀쩡히 왔어도 마지막 하나가 잘리면 **전부 버리고 키워드로 떨어졌다.**
    40개라도 분류된 게 0개보다 낫다.

    반환: (원소들, 정상적으로 닫혔는가)
    """
    dec = json.JSONDecoder()
    out: list = []
    i, n = start + 1, len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n:
            return out, False
        if text[i] == "]":
            return out, True
        try:
            value, i = dec.raw_decode(text, i)
        except ValueError:
            return out, False       # 여기서부터 잘렸거나 형식이 깨졌다
        out.append(value)
    return out, False


def _usable(elements: list) -> int:
    """이 배열에서 답으로 쓸 수 있는 원소가 몇 개인가."""
    return sum(1 for e in elements
               if (isinstance(e, int) and not isinstance(e, bool))
               or (isinstance(e, dict) and isinstance(e.get("i"), int)))


def _extract_elements(text: str) -> tuple[list, bool]:
    """본문에서 답 배열을 꺼낸다 — **첫 대괄호를 무조건 믿지 않는다.**

    ⚠️ 새 형식(번호만)에서 생기는 함정이다. 모델이 설명을 곁들이면서 각주처럼
    `[1]` 을 쓰면 첫 대괄호가 그것이다. 예전 형식은 개체 배열이라 그런 걸
    파싱하다 시끄럽게 실패했지만, 번호 배열은 `[1]` 도 **말이 되게 파싱돼서
    조용히 틀린 답이 된다.** 조용히 틀리는 건 이 시스템에서 가장 나쁜 실패다.

    그래서 모든 `[` 를 후보로 훑고 **쓸 수 있는 원소가 가장 많은 것**을 고른다.
    같으면 뒤쪽을 고른다 — 모델은 최종 답을 마지막에 쓴다.
    """
    best: tuple[list, bool] | None = None
    best_score = -1
    i = text.find("[")
    while i != -1:
        elements, closed = _scan_array(text, i)
        score = _usable(elements)
        # 잘린 배열(닫히지 않음)은 그 자체가 '여기서 끝났다' 는 뜻이라 뒤에 더
        # 나은 후보가 없다. 동점이면 뒤쪽을 택한다(>= 가 그 뜻이다).
        if score >= best_score:
            best, best_score = (elements, closed), score
        i = text.find("[", i + 1)
    return best if best is not None else ([], False)


def _answered_flags(elements: list, closed: bool, n_entries: int) -> dict[int, bool]:
    """모델 응답을 `{제목 인덱스: 발병보도인가}` 로 바꾼다.

    ★ 답하지 않은 제목은 넣지 않는다 ★ 응답이 잘렸을 때 나머지를 `False` 로
    채우면 **실제 발병 보도를 '무관함' 으로 덮어써서 신호를 지운다.** 없는 답을
    지어내느니 그 제목은 키워드 값을 그대로 쓰게 둔다.

    두 형식을 모두 받는다:
      - 번호만       `[0, 3, 12]`                     (2026-08-30~ 요청 형식)
      - 개체         `[{"i": 0, "relevant": true}]`   (예전 형식 · 모델이 옛 습관대로 답할 때)
    """
    flags: dict[int, bool] = {}

    # 정상적으로 닫힌 빈 배열 = "해당하는 제목이 하나도 없다". 전부 아니오다.
    if not elements and closed:
        return {gi: False for gi in range(n_entries)}

    ints = [e for e in elements if isinstance(e, int) and not isinstance(e, bool)]
    if ints:
        # 번호만 온 형식: 목록에 없는 번호는 "아니오" 다. 다만 **모델이 실제로
        # 훑은 데까지만** 그렇게 볼 수 있다. 잘렸으면 마지막으로 답한 번호를
        # 수위선으로 삼는다(오름차순으로 달라고 했고, 아니어도 보수적이다).
        covered = n_entries - 1 if closed else max(ints)
        listed = set(ints)
        for gi in range(0, min(covered, n_entries - 1) + 1):
            flags[gi] = gi in listed
        return flags

    for item in elements:
        if not isinstance(item, dict):
            continue
        gi = item.get("i")
        if isinstance(gi, int) and not isinstance(gi, bool) and 0 <= gi < n_entries:
            flags[gi] = bool(item.get("relevant"))
    return flags


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
        attempts += [(f"Groq({m})", GROQ_URL, m, groq_key) for m in GROQ_MODELS]

    reasons: list[str] = []
    for name, url, model, key in attempts:
        if not key:
            reasons.append(f"{name}: 키 없음")
            continue
        reason = _try_classify(feeds, entries, url, model, key, prompt)
        if reason is None:
            # 어느 제공자·모델이 실제로 먹었는지 남긴다 — 다음엔 추측할 필요가 없다.
            feeds_marker = next((f for f in feeds if "llm_hit_ratio" in f), None)
            if feeds_marker is not None:
                feeds_marker["llm_provider"] = name
            return None
        reasons.append(f"{name}: {reason}")
        # 404 는 "그 모델이 없다" 는 뜻이라 다음 후보로 넘어갈 이유가 된다.
        # 402·429 는 모델 문제가 아니므로 같은 제공자의 남은 후보를 더 태우지 않는다.
        if name.startswith("Groq(") and "404" not in reason:
            break
    return " | ".join(reasons)


def _try_classify(feeds, entries, url: str, model: str, api_key: str,
                  prompt: str) -> str | None:
    """제공자 하나로 시도. 성공이면 None, 실패면 사유."""
    try:
        r = _post(url, model, api_key, prompt, REASONING_EFFORT)
        # reasoning_effort 를 이 제공자가 모르면 400 이다. 그건 "이 요청이
        # 틀렸다" 가 아니라 "이 파라미터가 없다" 는 뜻이므로, 빼고 한 번 더
        # 보낸다. 검증할 수 없는 것을 단정하지 않는 대신 프로덕션이 답하게 한다.
        if r.status_code == 400 and REASONING_EFFORT:
            r = _post(url, model, api_key, prompt, None)

        # ── 실패 종류를 갈라서 남긴다 ────────────────────────────────────
        # 402(결제)·429(한도)·5xx(장애)·형식 문제는 조치가 전혀 다르다.
        # 예전엔 넷이 전부 같은 침묵이었다.
        if r.status_code == 402:
            return f"결제 필요(402) — 무료 티어가 끝났을 수 있다: {r.text[:150]}"
        if r.status_code == 429:
            return f"분당 요청 한도(429): {r.text[:150]}"
        r.raise_for_status()

        choice = r.json()["choices"][0]
        # ★ finish_reason 을 반드시 들고 간다 ★ 이게 없어서 2026-08-29 하루치
        # 실패 14건이 전부 "JSONDecodeError" 한 덩어리로만 남았다. 'length' 면
        # 잘린 것이고 'stop' 이면 모델이 애초에 JSON 을 안 준 것이다 —
        # 조치가 서로 다른데 로그가 그 둘을 구분해주지 못했다.
        finish = choice.get("finish_reason")
        raw = _message_text(choice.get("message") or {})
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

        if "[" not in raw:
            return (f"응답에 JSON 배열이 없음 (finish_reason={finish}, "
                    f"본문 {len(raw)}자): {raw[:120]}")
        elements, closed = _extract_elements(raw)
        # 빈 배열 `[]` 은 실패가 아니라 **"해당하는 제목이 하나도 없다"** 는
        # 정당한 답이다. 이걸 실패로 치면 조용한 날마다 키워드로 떨어진다.
        if not elements and not closed:
            return (f"JSON 배열을 읽지 못함 (finish_reason={finish}, "
                    f"본문 {len(raw)}자): {raw[raw.find('['):][:120]}")
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:180]}"

    # 잘린 응답도 **답한 데까지는** 쓴다. 답하지 않은 제목은 건드리지 않는다.
    flags = _answered_flags(elements, closed, len(entries))
    if not flags:
        return (f"배열은 읽었지만 쓸 수 있는 항목이 없음 "
                f"(finish_reason={finish}, 원소 {len(elements)}개)")

    per_feed_titles: dict[int, list[str]] = {}
    per_feed_relevant: dict[int, list[str]] = {}
    for gi, (fi, t) in enumerate(entries):
        is_rel = flags.get(gi)
        if is_rel is None:
            continue                      # 모델이 답하지 않은 제목 — 키워드 값을 그대로 둔다
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

    # 몇 개를 보내 몇 개를 답받았는지 남긴다. 잘린 응답으로 절반만 분류된 채
    # 도는 걸 "성공" 으로만 적으면, 커버가 조용히 반토막 나도 아무도 모른다.
    marker = next((f for f in feeds if "llm_hit_ratio" in f), None)
    if marker is not None:
        marker["llm_answered_titles"] = len(flags)
        marker["llm_sent_titles"] = len(entries)
        marker["llm_finish_reason"] = finish
    return None

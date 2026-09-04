"""EU 조달 감시 (TED) — "국가 조달 감시" 를 한국 밖으로 넓힌다 (2026-09-04, C-2).

## 왜

지금 조달 층은 나라장터 하나뿐인데 이름은 "국가 조달 감시" 다. 범위를 넘어
읽히기 쉽고, 실제로 국제 바이오안보 조달 흐름은 안 보인다. HERA(EU 보건비상
대응청)·EU 공동조달이 무엇을 사는지는 TED(Tenders Electronic Daily)에 공고된다.

## ★ 이 파일이 검증되지 않았다는 사실을 값에 담는다 ★

개발 샌드박스의 외부 접속이 조직 정책으로 막혀 있어(403) **TED 엔드포인트를
한 번도 실제로 부르지 못했다.** 응답 형식은 공개 문서 기준으로 짰고, 파싱을
방어적으로 두고, 실패를 조용히 삼키지 않게 했다.

그래서 이 모듈은 스스로를 `verified=False` 로 보고한다. 운영에서 처음 성공하면
능력 장부(capability_ledger)에 `verified_run` 이 찍히고, 그전까지는
`configuration_only` 로 남는다 — **안 되면 조용하지 않다.**

이 표시를 지우지 마라. 첫 성공을 눈으로 확인하기 전까지 이 층의 숫자를 대외
자료에 쓰면 안 된다.

## ★ 국내 층에서 배운 것을 그대로 적용한다 ★

나라장터에서 `bidNtceNm=방역` 에 *"청소년 해외역사탐방 여행사 위탁 용역"* 이
딸려 왔다. 검색이 느슨하면 무관한 공고가 섞인다. 그래서 여기서도 **받아온 뒤
제목에 낱말이 실제로 들어 있는지 우리가 다시 확인하고, 못 짚으면 버린다.**

## ★ 말하지 않는 것 ★

- **"우리가 딸 수 있는 사업" 이 아니다.** 참가자격은 공고 문서 안에 있다.
- **금액은 추정가치지 낙찰가가 아니다.**
- **낱말로 찾는다** — 표에 없는 이름을 단 공고는 안 걸린다. 여기 없다고 공고가
  없었다는 뜻이 아니다.
- **EU 밖은 안 본다.** TED 는 EU 공고 등록부다.
"""
from __future__ import annotations

import datetime as dt

import requests

# TED Search API v3. 키가 필요 없는 공개 검색 엔드포인트다(문서 기준).
TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
TIMEOUT = 45
PAGE_SIZE = 50

# ★ 이 층은 아직 실측되지 않았다 ★ 값에 실어 보낸다.
IS_VERIFIED = False
UNVERIFIED_NOTE = (
    "개발 환경의 외부 접속이 막혀 TED 엔드포인트를 실제로 호출해보지 못했다. "
    "운영에서 첫 성공이 능력 장부에 남기 전까지 이 층의 숫자를 대외 자료에 "
    "쓰지 말 것."
)

# 영문 검색어 — 국내 표(BIOSECURITY_KEYWORDS)와 같은 갈래를 영어로 옮긴 것.
# ★ 너무 흔한 낱말은 뺐다 ★ 'health' 같은 걸 넣으면 하루치가 수천 건이 되고,
# 그러면 아무도 안 본다(국내 표와 같은 이유).
TED_KEYWORDS: dict[str, list[str]] = {
    "감염병 감시·대응": ["epidemic", "infectious disease", "epidemiological surveillance",
                        "outbreak response", "vaccination campaign"],
    "대응제·비축": ["vaccine", "antiviral", "medical countermeasure", "stockpile"],
    "진단·검사체계": ["diagnostic test", "PCR test", "genomic sequencing", "pathogen detection"],
    "생물안보": ["biosecurity", "biological threat", "biosafety", "CBRN"],
    "가축·조류": ["avian influenza", "foot-and-mouth", "african swine fever"],
}


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _confirm(notice: dict, keyword: str) -> str | None:
    """서버가 줬어도 우리가 낱말을 못 짚으면 버린다(국내 층과 같은 규칙).

    반환: 어디서 걸렸는지("title"/"description") 또는 None."""
    needle = _norm(keyword)
    for field in ("title", "description"):
        if needle and needle in _norm(notice.get(field)):
            return field
    return None


def _shape(notice: dict, keyword: str, category: str, matched_in: str) -> dict:
    value = notice.get("estimated_value")
    try:
        value = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        value = None
    return {
        "notice_no": notice.get("publication_number") or notice.get("id"),
        "title": notice.get("title"),
        "agency": notice.get("buyer_name"),
        "country": notice.get("buyer_country"),
        "posted_at": notice.get("publication_date"),
        "closes_at": notice.get("deadline"),
        # ★ 추정가치지 낙찰가가 아니다 ★ 이름에 담는다.
        "estimated_value": value,
        "currency": notice.get("currency"),
        "url": notice.get("links", {}).get("html") if isinstance(notice.get("links"), dict)
               else notice.get("url"),
        "category": category,
        "keyword": keyword,
        "matched_in": matched_in,
        "source": "TED (EU Tenders Electronic Daily)",
    }


def _search(keyword: str, begin: str, end: str) -> list[dict] | str:
    """한 낱말 조회. 실패하면 **사유 문자열**을 돌려준다(빈 목록과 구분)."""
    try:
        resp = requests.post(
            TED_SEARCH_URL,
            json={
                "query": f'FT~"{keyword}" AND publication-date>={begin} '
                         f'AND publication-date<={end}',
                "fields": ["publication-number", "notice-title", "buyer-name",
                           "buyer-country", "publication-date", "deadline-receipt-request",
                           "estimated-value", "links"],
                "limit": PAGE_SIZE,
            },
            timeout=TIMEOUT,
            headers={"User-Agent": "AEGIRON/1.0", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json() or {}
    except Exception as exc:                        # noqa: BLE001
        return f"{type(exc).__name__}"

    notices = body.get("notices")
    if notices is None:
        # 형식이 바뀌었을 수 있다. 빈 결과로 접지 않는다.
        return "응답에 notices 가 없음(형식 변경 의심)"
    return [_flatten(n) for n in notices]


def _flatten(notice: dict) -> dict:
    """TED 응답의 다국어 필드를 우리 모양으로. 값이 없으면 None(지어내지 않는다).

    TED 는 제목 등을 언어별 배열로 준다(예: {"eng": ["..."]}). 영어를 우선하되
    없으면 첫 언어를 쓴다."""
    def _text(value):
        if isinstance(value, dict):
            for lang in ("eng", "ENG", "en"):
                if value.get(lang):
                    value = value[lang]
                    break
            else:
                value = next(iter(value.values()), None)
        if isinstance(value, list):
            value = value[0] if value else None
        return value if isinstance(value, str) else None

    return {
        "publication_number": _text(notice.get("publication-number")),
        "title": _text(notice.get("notice-title")),
        "description": _text(notice.get("description")),
        "buyer_name": _text(notice.get("buyer-name")),
        "buyer_country": _text(notice.get("buyer-country")),
        "publication_date": _text(notice.get("publication-date")),
        "deadline": _text(notice.get("deadline-receipt-request")),
        "estimated_value": notice.get("estimated-value"),
        "currency": _text(notice.get("currency")),
        "links": notice.get("links"),
    }


def watch_ted(days: int = 7, today: dt.datetime | None = None) -> dict:
    """최근 며칠간의 EU 바이오안보 관련 공고. **검증 안 됨을 값에 담는다.**"""
    now = today or dt.datetime.now()
    begin = (now - dt.timedelta(days=max(1, days))).strftime("%Y%m%d")
    end = now.strftime("%Y%m%d")

    found: dict[str, dict] = {}
    dropped, failures = 0, []

    for category, words in TED_KEYWORDS.items():
        for word in words:
            result = _search(word, begin, end)
            if isinstance(result, str):
                failures.append(f"{word}: {result}")
                continue
            for notice in result:
                where = _confirm(notice, word)
                if not where:
                    # ★ 서버가 줬어도 근거를 못 짚으면 버린다 ★ 국내 층과 같은 규칙.
                    dropped += 1
                    continue
                key = notice.get("publication_number")
                if not key or key in found:
                    continue
                found[key] = _shape(notice, word, category, where)

    # 낱말을 하나도 못 물었으면 '0건'이 아니라 실패다. 그 둘을 섞으면 조회
    # 실패가 '공고 없음'이라는 발견으로 둔갑한다(A-2 에서 고친 것과 같은 구분).
    total_words = sum(len(w) for w in TED_KEYWORDS.values())
    if len(failures) == total_words:
        return {"available": False,
                "reason": f"모든 낱말 조회 실패({len(failures)}건) — "
                          f"예: {failures[0] if failures else '?'}",
                "is_verified": IS_VERIFIED, "unverified_note": UNVERIFIED_NOTE}

    bids = sorted(found.values(), key=lambda b: (b["closes_at"] or "~", b["title"] or ""))
    return {
        "available": True,
        "window_days": days,
        "bid_count": len(bids),
        "bids": bids,
        "dropped_unconfirmed": dropped,
        "lookup_failures": failures,
        "keyword_count": total_words,
        "source": "TED (EU Tenders Electronic Daily)",
        # ★ 지우지 마라 ★ 첫 실측 성공 전까지 이 층은 검증되지 않았다.
        "is_verified": IS_VERIFIED,
        "unverified_note": UNVERIFIED_NOTE,
        "limits": [
            "참가자격은 공고 문서 안에 있고 이 API 로는 안 보인다. "
            "'우리가 딸 수 있는 사업' 목록이 아니다.",
            "금액은 추정가치이며 낙찰가가 아니다.",
            "낱말로 찾는다 — 표에 없는 이름을 단 공고는 안 걸린다. "
            "여기 없다고 공고가 없었다는 뜻이 아니다.",
            "TED 는 EU 공고 등록부다. EU 밖 조달은 보지 않는다.",
        ],
    }

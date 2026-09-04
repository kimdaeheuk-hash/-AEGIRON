"""국가 조달 감시 — "정부가 지금 무엇을 사려고 하는가" (2026-09-02).

## 왜 만들었나

캡틴: *"국가 바이오 안보 분야로 진입을 해야 국가사업을 할 수 있어!"*

국가사업은 어느 날 갑자기 오지 않는다. **입찰공고로 먼저 나온다.** 그리고
공고는 보통 2~3주 뒤에 닫힌다. 늦게 알면 그걸로 끝이다.

캡틴이 받아둔 공공데이터포털 키에 **나라장터만 이미 열려 있었다**(2026-09-02
실측). 질병관리청·식약처는 활용신청을 안 해서 "등록되지 않은 서비스키" 였다.
그래서 열려 있는 것부터 붙인다.

## ★ 이 모듈이 가장 조심하는 것 — 나라장터 검색은 느슨하다 ★

`bidNtceNm=방역` 으로 물었더니 이런 게 딸려 왔다(실측):

    2026 남대문쪽방촌 감염병 방역 및 해충방역        ← 맞다
    2026년 청소년 해외역사탐방 여행사 위탁 용역      ← 왜 나왔는지 모른다

**서버가 준 것을 그대로 믿으면 안 된다.** 학교 수학여행 공고를 바이오안보
입찰로 보고하면, 그 보고서를 다시 볼 사람이 없어진다.

그래서 받아온 뒤 **공고명·분류명에 그 낱말이 실제로 들어 있는지 우리가 다시
확인한다.** 못 짚으면 버린다. `matched_in` 에 어디서 걸렸는지 남긴다.

## ★ 이 목록이 말하지 않는 것 ★

- **"우리가 딸 수 있는 사업" 이 아니다.** 참가자격·실적요건은 공고문(HWP) 안에
  있고 이 API 로는 안 보인다. 여기서 내는 건 "그런 공고가 났다" 까지다.
- **금액은 배정예산이지 낙찰가가 아니다.** 실제 계약금은 개찰 뒤에 정해진다.
- **순위를 매기지 않는다.** 어느 공고가 더 중요한지는 사람이 정한다.
- **놓친 공고가 없다는 뜻이 아니다.** 낱말로 찾는 방식이라, 우리 낱말 표에
  없는 이름을 단 공고는 안 걸린다.
"""
from __future__ import annotations

import datetime as dt
import os

import requests

BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
# 용역과 물품을 함께 본다. 감시장비·진단키트는 물품, 역학조사·연구는 용역이다.
OPERATIONS = {
    "용역": "getBidPblancListInfoServcPPSSrch",
    "물품": "getBidPblancListInfoThngPPSSrch",
}
TIMEOUT = 60
MAX_WINDOW_DAYS = 30          # 조회 기간 상한. 이보다 길게 물으면 API 가 거절한다.
PAGE_SIZE = 100

# ── 낱말 표 ────────────────────────────────────────────────────────────────
# ★ 이건 위험 순위가 아니다 ★ "이 낱말이 공고명에 있으면 사람이 봐야 한다" 는
# 목록이다. 너무 흔한 낱말(검사·조사·관리)은 일부러 뺐다 — 넣으면 하루치가
# 수백 건이 되고, 그러면 아무도 안 본다.
BIOSECURITY_KEYWORDS: dict[str, list[str]] = {
    "감염병 감시·대응": ["감염병", "역학조사", "방역", "검역", "예방접종",
                        "인수공통", "결핵", "말라리아", "뎅기"],
    "대응제·비축": ["백신", "항바이러스", "치료제", "비축", "의약품 비축"],
    "진단·검사체계": ["진단키트", "유전체", "병원체", "실험실 정도관리"],
    "생물안보": ["생물테러", "생물무기", "바이오안보", "생물안전", "고위험병원체"],
    "가축·조류": ["조류인플루엔자", "구제역", "아프리카돼지열병", "살처분"],
    "기후·매개체": ["기후보건", "매개체", "모기", "폭염 건강"],
}


# ★ 같은 키가 이름 두 개로 있다 ★ 운영에는 예전부터 `KDCA_API_KEY` 라는 이름으로
# 들어 있었는데, 실측해보니 캡틴이 새로 준 `DATA_GO_KR_KEY` 와 **같은 값**이었다
# (지문 대조 2026-09-02). 원래 공공데이터포털 키 하나가 질병관리청·나라장터를
# 함께 여는 구조인데, 이름이 질병관리청만 가리키고 있었다.
#
# 이름을 하나로 정리하되(DATA_GO_KR_KEY 가 맞는 이름), 예전 이름도 계속 받는다 —
# 운영 변수를 못 고치는 상황에서 조용히 "키 없음" 이 되면 안 된다.
_KEY_NAMES = ("DATA_GO_KR_KEY", "KDCA_API_KEY")


def _key() -> str | None:
    for name in _KEY_NAMES:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return None


def _search(keyword: str, operation: str, begin: str, end: str,
            key: str, rows: int = PAGE_SIZE) -> list[dict] | str:
    """한 낱말·한 종류를 조회. 실패하면 **사유 문자열**을 돌려준다."""
    try:
        resp = requests.get(
            f"{BASE}/{operation}",
            params={"serviceKey": key, "type": "json", "inqryDiv": 1,
                    "pageNo": 1, "numOfRows": rows, "bidNtceNm": keyword,
                    "inqryBgnDt": begin, "inqryEndDt": end},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        body = (resp.json().get("response") or {}).get("body") or {}
    except Exception as exc:                        # noqa: BLE001
        return f"조회 실패: {type(exc).__name__}"

    if "totalCount" not in body:
        return "응답에 totalCount 가 없음(형식 변경 의심)"
    return body.get("items") or []


# ── ★ 같은 낱말, 다른 세상 ★ ────────────────────────────────────────────────
# 낱말이 진짜로 공고명에 있는데도 바이오안보와 무관한 경우다. 전부 실측에서
# 실제로 걸려 나온 것들이다(2026-09-02, 7일치):
#
#     2026년산 공공비축미 매입용 포대 제작        ← '비축' 이 쌀이었다
#     제어감시시스템 백신 라이센스(V3) 구매        ← '백신' 이 안티바이러스였다
#     유전체물성연구소 헬륨3 가스 구매             ← '유전체' 가 연구소 이름이었다
#     국가 희귀·특산식물 참조 유전체 정보 구축      ← '유전체' 가 식물이었다
#
# 이걸 안 걸러내면 목록의 1/5 이 쌀·소프트웨어·헬륨가스가 된다. 그러면 아무도
# 목록을 다시 안 본다.
#
# ★ 조용히 버리지 않는다 ★ 제외한 것도 사유와 함께 돌려준다. 낱말 표가 언젠가
# 진짜 공고를 잘못 자를 수 있고, 그때 눈에 보여야 고칠 수 있다.
FALSE_FRIENDS: dict[str, str] = {
    "공공비축미": "쌀 비축 — 의약품·방역물자 비축이 아니다",
    "비축미": "쌀 비축 — 의약품·방역물자 비축이 아니다",
    "심야전력": "전력 비축 설비 — 의약품 비축이 아니다",
    "백신 라이센스": "컴퓨터 백신(안티바이러스) 소프트웨어",
    "백신 프로그램": "컴퓨터 백신 소프트웨어",
    "바이러스 백신 S": "컴퓨터 백신 소프트웨어",
    "유전체물성": "물성물리 연구소 이름",
    "특산식물": "식물 유전체",
    "해충방역": "해충 구제 — 감염병 방역과 함께 쓰이면 남는다",
}


def _false_friend(item: dict) -> str | None:
    """무관한 세상의 공고인가. 맞으면 **사유**를 돌려준다."""
    title = item.get("bidNtceNm") or ""
    for phrase, reason in FALSE_FRIENDS.items():
        if phrase in title:
            # '해충방역' 이라도 '감염병' 이 같이 있으면 진짜다.
            if phrase == "해충방역" and "감염병" in title:
                continue
            return f"{phrase} — {reason}"
    return None


# 공고명 말고 여기까지는 근거로 인정한다 — 조달분류명에 "방역" 이 들어간 건
# 공고명이 애매해도 진짜다.
_SEARCHABLE_FIELDS = ("bidNtceNm", "pubPrcrmntLrgClsfcNm",
                      "pubPrcrmntMidClsfcNm", "pubPrcrmntClsfcNm")


def _confirm(item: dict, keyword: str) -> str | None:
    """그 낱말이 **실제로** 어디에 있는지 짚는다. 못 짚으면 None → 버린다."""
    for field in _SEARCHABLE_FIELDS:
        if keyword in (item.get(field) or ""):
            return field
    return None


def _shape(item: dict, keyword: str, category: str, matched_in: str,
           kind: str) -> dict:
    budget = item.get("asignBdgtAmt")
    try:
        budget = int(float(budget)) if budget not in (None, "") else None
    except (TypeError, ValueError):
        budget = None
    return {
        "notice_no": item.get("bidNtceNo"),
        "notice_ord": item.get("bidNtceOrd"),
        "title": item.get("bidNtceNm"),
        "agency": item.get("ntceInsttNm"),
        "demand_agency": item.get("dminsttNm"),
        "kind": kind,
        "posted_at": item.get("bidNtceDt"),
        "closes_at": item.get("bidClseDt"),
        # ★ 배정예산이지 낙찰가가 아니다 ★ 이름에 그대로 담는다.
        "assigned_budget_krw": budget,
        "url": item.get("bidNtceDtlUrl") or item.get("bidNtceUrl"),
        "category": category,
        "keyword": keyword,
        # 어디서 걸렸는지 남긴다 — 못 짚는 건 애초에 여기 오지 않는다.
        "matched_in": matched_in,
        "classification": item.get("pubPrcrmntClsfcNm"),
    }


def watch_bids(days: int = 7, today: dt.datetime | None = None) -> dict:
    """최근 며칠간의 바이오안보 관련 입찰공고. **키가 없으면 없다고 말한다.**"""
    key = _key()
    if not key:
        return {"available": False,
                "reason": "공공데이터포털 키가 없다 "
                          f"({' 또는 '.join(_KEY_NAMES)})",
                "is_eligibility_check": False}

    days = max(1, min(days, MAX_WINDOW_DAYS))
    now = today or dt.datetime.now()
    begin = (now - dt.timedelta(days=days)).strftime("%Y%m%d%H%M")
    end = now.strftime("%Y%m%d%H%M")

    found: dict[tuple, dict] = {}
    excluded: dict[tuple, dict] = {}
    dropped, failures = 0, []

    for category, words in BIOSECURITY_KEYWORDS.items():
        for word in words:
            for kind, operation in OPERATIONS.items():
                result = _search(word, operation, begin, end, key)
                if isinstance(result, str):
                    failures.append(f"{word}/{kind}: {result}")
                    continue
                for item in result:
                    where = _confirm(item, word)
                    if not where:
                        # ★ 서버가 줬어도 근거를 못 짚으면 버린다 ★
                        dropped += 1
                        continue
                    dedupe = (item.get("bidNtceNo"), item.get("bidNtceOrd"))
                    if dedupe in found or dedupe in excluded:
                        continue
                    reason = _false_friend(item)
                    if reason:
                        # 조용히 버리지 않는다 — 사유와 함께 따로 센다.
                        excluded[dedupe] = {"title": item.get("bidNtceNm"),
                                            "keyword": word, "reason": reason}
                        continue
                    found[dedupe] = _shape(item, word, category, where, kind)

    bids = sorted(found.values(), key=lambda b: (b["closes_at"] or "", b["title"] or ""))
    return {
        "available": True,
        "window_days": days,
        "bid_count": len(bids),
        "bids": bids,
        # 서버 검색이 느슨해서 버린 건수. 0 이 아니어야 정상이다.
        "dropped_unconfirmed": dropped,
        # 낱말은 맞았지만 다른 세상이라 뺀 것. 사유가 붙어 있다.
        "excluded": sorted(excluded.values(), key=lambda e: e["title"] or ""),
        "excluded_count": len(excluded),
        "lookup_failures": failures,
        "keyword_count": sum(len(w) for w in BIOSECURITY_KEYWORDS.values()),
        "source": "조달청 나라장터 입찰공고정보 (공공데이터포털)",
        "is_eligibility_check": False,
        "limits": [
            "참가자격·실적요건은 공고문(HWP) 안에 있고 이 API 로는 보이지 않는다. "
            "'우리가 참여할 수 있는 사업' 목록이 아니다.",
            "금액은 배정예산이며 낙찰가가 아니다. 실제 계약금은 개찰 뒤에 정해진다.",
            "낱말로 찾는다 — 표에 없는 이름을 단 공고는 걸리지 않는다. "
            "여기 없다고 공고가 없었다는 뜻이 아니다.",
            "나라장터 검색은 느슨해서 무관한 공고가 섞여 나온다. "
            "공고명·분류명에서 낱말을 직접 짚은 것만 남겼다.",
            "낱말이 맞아도 다른 세상인 공고는 뺐다(쌀 비축·컴퓨터 백신 등). "
            "뺀 목록은 excluded 에 사유와 함께 남긴다 — 잘못 뺀 것을 찾을 수 있어야 한다.",
            "순위를 매기지 않는다. 어느 공고가 중요한지는 사람이 정한다.",
        ],
    }


# ── 마감 인식 (2026-09-04, C안) ────────────────────────────────────────────
# ★ 점검에서 나온 것 ★ closes_at 은 정렬에만 쓰이고 그 뒤 아무도 안 읽었다.
# 그래서 **이미 마감된 공고가 "조달 31건" 에 그대로 섞여 있었다.** 7일 창으로
# 조회하니 그 사이 닫힌 것도 같이 들어온다.
#
# 이 층의 존재 이유가 "공고는 보통 2~3주 뒤에 닫힌다. 늦게 알면 그걸로 끝이다"
# 인데, 정작 마감을 안 보고 있었다. 열린 것과 닫힌 것을 같은 숫자로 세면
# 그 숫자는 기회의 크기를 말하지 못한다.
CLOSING_SOON_DAYS = 3          # 이 안에 닫히면 '임박' — 사람이 지금 봐야 한다


def _parse_close(value: str | None) -> dt.datetime | None:
    """나라장터 마감일시("YYYY-MM-DD HH:MM:SS") 파싱. 못 읽으면 None."""
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d%H%M"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def deadline_status(bid: dict, now: dt.datetime | None = None) -> str:
    """open | closing_soon | closed | unknown.

    ★ 못 읽은 마감일을 '열림'으로 치지 않는다 ★ 모르는 것을 기회로 세면
    숫자가 부풀고, 그 숫자를 보고 준비하다 이미 닫힌 걸 알게 된다."""
    closes = _parse_close(bid.get("closes_at"))
    if closes is None:
        return "unknown"
    now = now or dt.datetime.now()
    if closes <= now:
        return "closed"
    if (closes - now).total_seconds() <= CLOSING_SOON_DAYS * 86400:
        return "closing_soon"
    return "open"


def summarize_bids(bids: list[dict], now: dt.datetime | None = None,
                   keep: int = 5) -> dict:
    """공고 목록 → 마감 기준 요약. **제목을 버리지 않는다.**

    예전엔 발할라가 건수와 공고번호만 보관해서, "정부가 지금 무엇을 사려는지"
    라는 이 층의 목적이 로그·스냅샷 어디에도 안 남았다(파이프라인 층과 같은
    '결과를 버린다' 문제)."""
    now = now or dt.datetime.now()
    buckets: dict[str, list[dict]] = {
        "open": [], "closing_soon": [], "closed": [], "unknown": []}
    for bid in bids:
        buckets[deadline_status(bid, now)].append(bid)

    def _trim(rows: list[dict]) -> list[dict]:
        # 마감이 가까운 순. 상태 파일이 커지지 않게 몇 건만 들고 간다.
        rows = sorted(rows, key=lambda b: (b.get("closes_at") or "~", b.get("title") or ""))
        return [{"title": b.get("title"), "agency": b.get("agency"),
                 "closes_at": b.get("closes_at"), "category": b.get("category"),
                 "assigned_budget_krw": b.get("assigned_budget_krw"),
                 "notice_no": b.get("notice_no")} for b in rows[:keep]]

    return {
        "counts": {k: len(v) for k, v in buckets.items()},
        # ★ 지금 행동할 수 있는 것만 따로 ★ 마감된 건 기회가 아니다.
        "actionable_count": len(buckets["open"]) + len(buckets["closing_soon"]),
        "closing_soon": _trim(buckets["closing_soon"]),
        "open_sample": _trim(buckets["open"]),
        "closing_soon_days": CLOSING_SOON_DAYS,
        "note": ("closed 는 이미 닫힌 공고다 — 조회 창(7일) 안에 마감된 것들이라 "
                 "목록에는 남지만 기회로 세지 않는다. unknown 은 마감일을 못 읽은 "
                 "것이며, 열림으로 치지 않는다."),
    }


def procurement_summary(value: dict | None) -> str | None:
    """조달 값 → 로그 한 줄. 값이 없으면 None(빈 줄을 흘리지 않는다).

    ★ 마감 임박 공고의 제목을 찍는다 ★ 건수만으로는 사람이 아무것도 못 한다.
    이 층의 목적이 "정부가 지금 무엇을 사려는지 본다" 인데, 공고번호만 남기던
    탓에 로그에 그 답이 한 줄도 없었다."""
    if not value:
        return None
    deadline = value.get("deadline") or {}
    counts = deadline.get("counts") or {}
    if not counts:
        # 옛 모양(마감 요약이 없는 값)이면 건수만이라도 정직하게 낸다 —
        # 파이프라인 층에서 옛 모양을 못 읽어 이틀 침묵한 전례가 있다.
        total = value.get("bid_count")
        return f"{total}건(마감 정보 없음 — 갱신 대기)" if total is not None else None

    parts = [f"열림 {counts.get('open', 0)}건",
             f"임박 {counts.get('closing_soon', 0)}건",
             f"마감 {counts.get('closed', 0)}건"]
    if counts.get("unknown"):
        parts.append(f"마감일미상 {counts['unknown']}건")
    line = " · ".join(parts)

    coverage = value.get("coverage") or []
    if coverage:
        line += f" (범위 {'·'.join(coverage)})"

    soon = deadline.get("closing_soon") or []
    if soon:
        titles = "·".join((b.get("title") or "?")[:24] for b in soon[:2])
        line += f" [임박: {titles}]"
    return line

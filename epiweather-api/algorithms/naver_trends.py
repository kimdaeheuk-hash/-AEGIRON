"""네이버 데이터랩 검색어 트렌드 — 배치 분리와 그룹 이름 대조 (2026-09-19).

## ★ 왜 요청을 나누는가 ★

네이버는 **한 HTTP 요청 안의 모든 키워드 그룹 중 최댓값을 100으로** 정규화한다.
같은 배치에 속한 그룹끼리만 같은 0~100 척도 위에 있다는 뜻이다.

그래서 기존 요청(독감·에볼라)에 코로나를 그냥 한 줄 더 넣으면, 코로나 검색량이
더 많은 순간 **독감·에볼라 값이 통째로 재척도된다.** 오늘 92.5 로 찍힌 독감비율이
내일 5 로 내려앉는데, 실제 독감 검색은 그대로다. 요청은 200 이고 숫자도 들어오고
로그도 조용하다 — 3개월치 기준선이 의미를 잃은 걸 아무도 모른다.

이 층은 anomaly_engine 이 z-score 로 급증을 판정하는 입력이다. 척도가 갈아엎히면
과거 평균·표준편차가 현재 값과 다른 단위가 되어, **급증이 없는데 급증으로 잡히거나
반대로 진짜 급증을 놓친다.** 값이 비는 고장보다 나쁘다.

→ 축마다 요청을 따로 보낸다. 주기당 호출이 1회에서 2회로 늘지만(네이버 일 한도
   1,000회, 우리는 하루 48회) 각 축이 자기 기준으로 정규화돼 시계열이 이어진다.

## ★ 배치가 다르면 값을 비교하지 마라 ★

독감비율 92.5 와 코로나비율 30 을 나란히 놓고 "독감이 3배"라고 읽으면 안 된다.
서로 다른 척도다. 각 축은 **자기 과거와만** 비교된다(z-score 가 하는 일이 정확히
그것이다). 이 사실을 값에 담을 수 없어서 — ratio 는 그냥 숫자다 — 여기 적는다.

## ★ 이름으로 찾는다 ★

예전엔 results[0]·results[1] 로 위치를 믿었다. 그룹이 둘일 땐 버텼지만, 순서가
바뀌면 독감 값이 에볼라 자리에 들어가도 아무도 모른다. 값이 비는 게 아니라
**틀린 값이 채워지는** 쪽이라 더 나쁘다. 응답이 돌려주는 title 로 대조한다.
"""
from __future__ import annotations

import datetime as dt

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
TIMEOUT = 15
WINDOW_DAYS = 90
TIME_UNIT = "week"

# ★ 이 배치 구성을 함부로 합치지 마라 ★ 위 주석의 재척도 문제가 그대로 돌아온다.
#
# baseline: 2026-06 부터 같은 요청으로 수집해 온 두 축이다. 갈라놓아도(따로 보내도)
#           척도가 바뀌므로, 붙여둔 채로 유지한다.
# covid:    2026-09-19 신설. 기존 축에 섞으면 저쪽이 재척도되므로 따로 보낸다.
NAVER_BATCHES: list[tuple[str, list[dict]]] = [
    ("baseline", [
        {"groupName": "독감", "keywords": ["독감", "인플루엔자", "해열제"]},
        {"groupName": "에볼라", "keywords": ["에볼라", "바이러스감염"]},
    ]),
    ("covid", [
        # '코로나' 단독은 코로나 맥주 등 동음 검색을 일부 포함한다 — 국내 검색에서는
        # 압도적으로 코로나19 를 뜻하지만 순수하지는 않다. 그래서 확실한 낱말
        # (코로나19·코로나증상)과 행동 프록시(자가검사키트)를 같이 묶는다.
        # 자가검사키트는 증상 의심 시점에 검색되므로 신고 통계보다 앞선다.
        {"groupName": "코로나", "keywords": ["코로나", "코로나19", "코로나증상", "자가검사키트"]},
    ]),
]

# 그룹 이름 → 수집 결과에 담기는 필드 이름.
GROUP_FIELDS = {
    "독감": "naver_flu_ratio",
    "에볼라": "naver_ebola_ratio",
    "코로나": "naver_covid_ratio",
}

# 로그 한 줄에 쓰는 표기.
GROUP_LABELS = {"독감": "독감비율", "에볼라": "에볼라비율", "코로나": "코로나비율"}


def request_body(groups: list[dict], today: dt.date | None = None) -> dict:
    """한 배치의 요청 본문. 창·단위를 배치마다 같게 둔다(시간 해상도까지 달라지면
    축끼리 비교가 더 어려워진다 — 척도는 이미 다르다)."""
    end = today or dt.date.today()
    return {
        "startDate": (end - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": TIME_UNIT,
        "keywordGroups": groups,
    }


def latest_ratios(payload: dict | None) -> dict[str, float | None]:
    """응답 → {그룹이름: 최근 ratio}. 못 찾으면 그 이름이 아예 안 담긴다.

    ★ 0 으로 채우지 않는다 ★ 그룹이 응답에 없는 것과 검색량이 0 인 것은 다르다.
    앞은 고장이고 뒤는 관측이다. 섞으면 '네이버가 죽었다'가 '아무도 안 찾는다'로
    둔갑한다 — 조기경보에서 정확히 반대 방향의 오독이다.
    """
    out: dict[str, float | None] = {}
    for row in ((payload or {}).get("results") or []):
        name = row.get("title")
        if not name:
            continue
        points = row.get("data") or []
        # 데이터 배열이 비면 '최근 값'이 없는 것이다. 마지막 원소를 억지로
        # 만들어내지 않는다.
        out[name] = points[-1].get("ratio") if points else None
    return out


def summary(ratios: dict[str, float | None], failures: dict[str, str] | None = None) -> str:
    """수집기 로그 한 줄. 수집기에서 즉석으로 조립하지 않는다 — 문자열도
    시험 가능한 자리에 둔다(extraction_summary·stale_lines 와 같은 이유).

    실패한 배치는 숨기지 않는다. 한 배치가 죽어도 다른 배치 값은 그대로 찍히므로,
    사유를 안 붙이면 '코로나비율이 원래 없는 것'처럼 읽힌다.
    """
    parts = []
    for name in GROUP_FIELDS:
        if name in ratios:
            parts.append(f"{GROUP_LABELS[name]}={ratios[name]}")
    line = " ".join(parts) if parts else "값 없음"
    for batch, reason in sorted((failures or {}).items()):
        line += f" · {batch} 실패({reason})"
    return line

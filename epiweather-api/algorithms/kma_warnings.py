"""기상청 특보(KMA API허브) → 한국 재난 감시창 입력 (2026-10-06).

## 왜 만드는가

`disaster_watch` 는 GDACS Orange/Red 만 입력으로 받는다. GDACS 는 전 지구 큰 재난 위주라
한국 안의 호우경보처럼 **국지적이지만 감시창을 열 만한 사건**은 등급에 못 미쳐 놓친다.
기상청 특보는 그 빈틈을 한국에 한해 메운다. 입력만 늘릴 뿐 규칙표(`WATCH_RULES`)는 그대로다 —
호우 → `FL`, 태풍 → `TC` 로 **기존 규칙에 매핑**하고, 새 질병 규칙을 지어내지 않는다.

## ★ 정직성 경계선 ★

- **라이브 검증 못 함.** 이 샌드박스는 apihub.kma.go.kr 에 못 나간다(프록시 403). 응답 형식은
  문서 기억에 기대 짰고, 그래서 **헤더 줄의 열 이름으로 읽고**, 못 읽으면 가짜를 만들지 않고
  사유와 응답 앞부분(키는 지워서)을 들고 올라온다. 프로덕션 첫 주기 로그가 이 파일의 검증이다.
- **주의보로는 창을 열지 않는다.** 경보(위험 단계 2)만 연다 — GDACS 의 Green 을 안 여는 것과
  같은 '노이즈 관리' 판단이고 역학 근거가 아니다.
- **모르는 코드는 건너뛰고 센다.** 특보 종류·수준·명령 코드를 모르면 그 행은 쓰지 않는다.
  '해제'를 '발효'로 잘못 읽어 없는 창을 여는 쪽이 반대보다 나쁘다.
- **키는 절대 새지 않는다.** `requests` 예외 문구에는 쿼리 문자열이 통째로 들어간다 — 그대로 로그와
  `signals.jsonl` 에 가면 키가 새므로 `scrub()` 로 지운다.
- 호우·태풍 말고는 매핑하지 않는다. 폭염·한파·대설은 이 시스템의 질병 규칙표에 대응이 없다.
"""
from __future__ import annotations

import os
import re

import requests

USER_AGENT = {"User-Agent": "EpiWeather-KmaWarnings/1.0 (epiweather.kr)"}
TIMEOUT = 20
KEY_ENV = "KMA_API_KEY"
# 현재 발효 중인 특보 현황. 시각을 안 주면 '지금'. (형식 미검증 — 위 경계선 참조)
KMA_WARNING_URL = "https://apihub.kma.go.kr/api/typ01/url/wrn_now_data.php"

ISO3 = "KOR"
COUNTRY = "대한민국"

# 특보 종류 → 우리 규칙표의 재난 코드. 여기 없는 종류는 쓰지 않는다.
KIND_TO_TYPE = {"R": "FL", "호우": "FL", "T": "TC", "태풍": "TC"}
KIND_NAME = {"FL": "호우", "TC": "태풍"}
# 특보 수준 — **경보만** 창을 연다. 주의보(1)는 연 적 없다.
WARNING_LEVELS = {"2", "경보"}
ADVISORY_LEVELS = {"1", "주의보"}
# 특보 명령 — 지금 발효 중인 것만. 해제(3)·대치해제(4)·변경해제(7)는 창을 열지 않는다.
ACTIVE_COMMANDS = {"1", "2", "5", "6", "발표", "대치", "연장", "변경"}
CANCEL_COMMANDS = {"3", "4", "7", "해제", "대치해제", "변경해제"}

REQUIRED_COLUMNS = ("WRN", "LVL", "CMD")
TIME_COLUMNS = ("TM_EF", "TM_FC", "TM_IN")      # 발효 → 발표 → 통보 순으로 쓴다


class KmaError(RuntimeError):
    """이 층의 실패. 종류를 반드시 들고 다닌다."""


def api_key() -> str | None:
    key = (os.environ.get(KEY_ENV) or "").strip()
    return key or None


def scrub(text: object, key: str | None = None) -> str:
    """오류 문구에서 키를 지운다. `authKey=…` 쿼리와 환경변수 값, 둘 다."""
    s = str(text)
    s = re.sub(r"(?i)(auth_?key|service_?key|apikey)=[^&\s'\"]+", r"\1=***", s)
    key = key if key is not None else api_key()
    if key:
        s = s.replace(key, "***")
    return s


# ── 파싱 ────────────────────────────────────────────────────────────────

def _split(line: str, comma: bool) -> list[str]:
    return [p.strip() for p in (line.split(",") if comma else line.split())]


def _header_columns(lines: list[str]) -> tuple[list[str], bool] | None:
    """주석(`#`) 줄 가운데 열 이름이 적힌 마지막 줄. (열 목록, 쉼표 구분 여부)."""
    found = None
    for ln in lines:
        if not ln.startswith("#"):
            continue
        body = ln.lstrip("#").strip()
        comma = "," in body
        cols = [c.upper() for c in _split(body, comma)]
        if all(c in cols for c in REQUIRED_COLUMNS):
            found = (cols, comma)
    return found


def _date_of(row: dict[str, str]) -> str | None:
    for col in TIME_COLUMNS:
        raw = row.get(col, "")
        m = re.match(r"(\d{4})(\d{2})(\d{2})", raw)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def parse_warnings(text: str) -> dict:
    """응답 본문 → {"events": [...], "rows": n, "skipped": {사유: n}}.

    사건은 (재난코드, 발효일) 하나로 묶고 구역 수를 센다 — 호우경보가 40개 구역에 동시에 나도
    '한국에 호우경보 한 건'이다. 형식이 예상 밖이면 `KmaError`.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header = _header_columns(lines)
    if header is None:
        raise KmaError("기상청 특보 응답에서 열 이름 줄(WRN·LVL·CMD)을 못 찾았다(형식 확인 필요): "
                       + scrub(text[:200]))
    cols, comma = header
    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    grouped: dict[tuple[str, str], int] = {}
    rows = 0
    for ln in lines:
        if ln.startswith("#"):
            continue
        parts = _split(ln, comma)
        rows += 1
        if len(parts) != len(cols):
            skip("열 수 불일치")
            continue
        row = dict(zip(cols, parts))
        etype = KIND_TO_TYPE.get(row["WRN"])
        if etype is None:
            skip("매핑 없는 특보 종류")
            continue
        level = row["LVL"]
        if level in ADVISORY_LEVELS:
            skip("주의보")
            continue
        if level not in WARNING_LEVELS:
            skip("모르는 수준 코드")
            continue
        cmd = row["CMD"]
        if cmd in CANCEL_COMMANDS:
            skip("해제")
            continue
        if cmd not in ACTIVE_COMMANDS:
            skip("모르는 명령 코드")
            continue
        date = _date_of(row)
        if not date:
            skip("날짜 못 읽음")
            continue
        grouped[(etype, date)] = grouped.get((etype, date), 0) + 1

    if rows and skipped.get("열 수 불일치", 0) == rows:
        # 한 행도 못 읽었다 — '특보가 없다'가 아니라 '파서가 못 읽었다'다.
        raise KmaError("기상청 특보 응답의 모든 행이 열 수와 안 맞았다(구분자·형식 확인 필요): "
                       f"헤더 {len(cols)}열 / 첫 행 {scrub(next(l for l in lines if not l.startswith('#'))[:160])}")

    events = [
        {"type": etype, "date": date, "iso3": ISO3, "country": COUNTRY, "alert": "경보",
         "source": "kma", "regions": n,
         "title": f"기상청 {KIND_NAME[etype]}경보 — {n}개 구역 발효"}
        for (etype, date), n in sorted(grouped.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    ]
    return {"events": events, "rows": rows, "skipped": skipped}


def fetch_warnings(key: str | None = None) -> dict:
    """KMA 특보 수집. 키가 없으면 호출하지 않는다(호출부가 '키 없음'으로 구분한다)."""
    key = key or api_key()
    if not key:
        raise KmaError(f"{KEY_ENV} 가 설정되지 않았다")
    try:
        resp = requests.get(KMA_WARNING_URL, headers=USER_AGENT, timeout=TIMEOUT,
                            params={"fe": "f", "disp": "0", "help": "0", "authKey": key})
        resp.raise_for_status()
    except requests.RequestException as e:
        # 예외 문구에 URL(= 키)이 들어 있다 — 지워서 올린다.
        raise KmaError(f"기상청 특보 수집 실패({type(e).__name__}): {scrub(e, key)[:160]}") from None
    return parse_warnings(resp.text)

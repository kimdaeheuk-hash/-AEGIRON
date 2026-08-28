"""재난 → 발병 감시창 (2026-08-28).

## 왜 만드는가

2026-08-28 네팔 홍수 보도를 계기로 이 시스템이 네팔을 어디까지 아는지 봤더니,
현지어 뉴스 피드(`gn_np`)는 있는데 **그 피드가 찾는 건 질병 단어뿐**이었다 —
`महामारी`(전염병)·`रोग`(질병)·`डेंगु`(뎅기). 홍수 기사는 안 걸린다.

    시스템은 '발병 보도가 시작될 때' 네팔을 발견한다.
    그런데 그때는 이미 발병한 뒤다.

★ 그런데 홍수 자체는 발병이 아니다. 발병은 **뒤에 온다.** ★
그 사이의 시간이 이 제품이 팔려고 하는 바로 그 시간이다. 이 모듈은 그 시간을
'감시창'으로 만든다 — 재난이 나면 그 나라에 창을 열고, 창이 열린 동안 해당
질병 보도를 **더 낮은 문턱으로** 본다.

## 입력: GDACS (무료, 키 불필요)

Global Disaster Alert and Coordination System — UN·EC 가 돌리는 전 지구 재난
경보다. RSS 한 줄이면 되고 API 키가 없다. 유료 전환이 선택지가 아닌 이
프로젝트에 맞다.

## ★ 정직성 경계선 ★

- **잠복 구간은 문헌값이고, 이 시스템 데이터로 보정한 값이 아니다.**
  `windows_calibrated=False` 로 응답에 항상 명시한다. 우리 자신의 과거
  데이터로 재보정하기 전까지 이 숫자는 '가설'이지 '측정'이 아니다.
- **감시창은 예측이 아니다.** 창이 열렸다는 건 "이 기간에 이 질병 보도가
  뜨면 우연으로 넘기지 말라" 는 뜻이지, "발병한다" 가 아니다.
- **Green 경보로는 창을 열지 않는다.** GDACS 는 매일 다수의 Green 을 낸다.
  전부 창을 열면 세계의 절반이 감시 대상이 되고 그 순간 신호가 의미를 잃는다.
  Orange·Red 만 연다 — 이 판단의 근거는 '노이즈 관리'이지 '역학'이 아니다.
- **라이브 검증 못 함.** 이 샌드박스는 외부 접속이 허용목록 방식이라 GDACS
  응답을 실제로 못 봤다. 그래서 파서를 방어적으로 짰고(형태가 예상 밖이면
  가짜를 만들지 않고 건너뛴다), 실패하면 **사유를 들고 올라온다.**
  프로덕션 첫 주기 로그로 확인할 것 — 그게 이 파일의 미검증 항목이다.

## ★ 왜 저장하는가 (안 하면 조용히 반쪽이 된다) ★

GDACS RSS 는 **최근 며칠치만** 실린다. 그런데 뎅기 감시창은 재난 42일 뒤까지
열려 있어야 한다. 저장하지 않으면 RSS 에서 항목이 빠지는 순간 창이 닫힌다 —
**가장 중요한 후반부가 통째로 사라진다.** 그래서 source_health.json 과 같은
Railway 볼륨(`data/`)에 이벤트를 쌓는다.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import requests

from .country_resolve import resolve_countries

USER_AGENT = {"User-Agent": "EpiWeather-DisasterWatch/1.0 (epiweather.kr)"}
TIMEOUT = 20
GDACS_RSS = "https://www.gdacs.org/xml/rss.xml"

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "disaster_watch.json"

# 창을 여는 경보 등급. Green 을 넣지 않는 이유는 위 '정직성 경계선' 참조.
OPENING_ALERT_LEVELS = {"orange", "red"}

# 이 일수를 넘긴 이벤트는 저장소에서 지운다(가장 긴 창 + 여유).
EVENT_RETENTION_DAYS = 150


class DisasterWatchError(RuntimeError):
    """이 층의 실패. 종류를 반드시 들고 다닌다(2026-08-25·08-28 교훈)."""


# ── 잠복 구간 표 ────────────────────────────────────────────────────────
# (질병, 매칭 키워드, 최소일, 최대일, 근거)
#
# 근거는 표준 잠복기 + 재난 역학에서 반복 관측된 발생 시점이다. 재난 당일을
# 0일로 본다. **문헌값이고 우리 데이터로 보정하지 않았다** — 위 경계선 참조.
_WATER_BORNE = ("콜레라·장티푸스", ["cholera", "typhoid", "콜레라", "장티푸스", "diarrhea", "설사"],
                3, 14,
                "상하수도 오염. 콜레라 잠복 2시간~5일·장티푸스 6~30일이고, "
                "침수 직후부터 오염수 노출이 시작돼 첫 집단발생 보고가 대개 1~2주 안에 나온다")
_LEPTO = ("렙토스피라증", ["leptospirosis", "렙토스피라"],
          2, 28,
          "잠복 2~30일. 침수된 물의 설치류 소변 접촉 — 홍수 뒤 가장 특징적인 질환이다")
_HEP_A = ("A형간염", ["hepatitis a", "hepatitis", "A형간염", "간염"],
          15, 50,
          "잠복 15~50일(평균 28). 오염된 물·식품 경로라 수인성보다 늦게 나타난다")
_MEASLES_SHELTER = ("홍역", ["measles", "홍역", "rubeola"],
                    7, 21,
                    "잠복 7~21일. 대피소 밀집 + 예방접종 중단이 겹친다")
_VECTOR = ("뎅기·말라리아", ["dengue", "malaria", "chikungunya", "뎅기", "말라리아", "치쿤구니야"],
           14, 42,
           "물이 빠진 뒤 고인물이 번식지가 된다 — 매개체 세대 형성 + 잠복기라 "
           "수인성 질환보다 뚜렷하게 늦다")
_TETANUS = ("파상풍", ["tetanus", "파상풍"],
            3, 21,
            "잠복 3~21일. 붕괴·잔해로 인한 외상 경로 — 지진에 특징적이다")
_ARI = ("급성호흡기감염", ["respiratory", "pneumonia", "폐렴", "호흡기"],
        1, 14,
        "화산재·분진 흡입에 따른 기도 손상 + 대피소 밀집")

WATCH_RULES: dict[str, list[tuple]] = {
    # 홍수 — 이 모듈을 만든 계기
    "FL": [_WATER_BORNE, _LEPTO, _HEP_A, _MEASLES_SHELTER, _VECTOR],
    # 열대저기압(폭풍해일·침수·대피) — 경로가 홍수와 사실상 같다
    "TC": [_WATER_BORNE, _LEPTO, _HEP_A, _MEASLES_SHELTER, _VECTOR],
    "TS": [_WATER_BORNE, _LEPTO, _MEASLES_SHELTER],          # 쓰나미
    # 지진 — 침수가 아니라 상하수도 파괴·외상·대피소
    "EQ": [_WATER_BORNE, _MEASLES_SHELTER, _TETANUS],
    "VO": [_MEASLES_SHELTER, _ARI],                          # 화산
    # 가뭄 — 다른 재난보다 훨씬 느리다. 안전한 물 부족 + 영양실조로 인한 면역저하.
    "DR": [("콜레라", ["cholera", "콜레라"], 14, 90,
            "안전한 식수 부족이 누적되며 나타난다 — 급성 재난과 시간축이 다르다"),
           ("홍역", ["measles", "홍역"], 30, 120,
            "영양실조로 인한 면역저하 경로라 가장 느리다")],
    # WF(산불)는 **일부러 뺐다.** 산불 → 발병으로 이어지는 경로가 뚜렷하지 않다.
    # 없는 규칙을 지어내면 그 순간 이 표 전체의 신뢰가 없어진다.
}

# 가장 긴 창(가뭄 → 홍역 120일). EVENT_RETENTION_DAYS 가 이보다 커야 한다.
MAX_WINDOW_DAYS = max(hi for rules in WATCH_RULES.values() for (_, _, _, hi, _) in rules)


# ── GDACS 파싱 ─────────────────────────────────────────────────────────

def _tag(block: str, name: str) -> str | None:
    """`<ns:name>값</ns:name>` 에서 값 하나. CDATA 도 벗긴다.

    XML 파서를 쓰지 않는 이유: GDACS 는 네임스페이스가 여럿이고 항목마다
    선택적 필드가 다르다. 엄격한 파서는 한 항목이 이상하면 피드 전체를
    버리는데, 여기선 **읽을 수 있는 항목만 살리는 쪽**이 맞다.
    """
    m = re.search(rf"<(?:\w+:)?{name}[^>]*>(.*?)</(?:\w+:)?{name}>", block, re.S | re.I)
    if not m:
        return None
    val = m.group(1).strip()
    cdata = re.match(r"^<!\[CDATA\[(.*?)\]\]>$", val, re.S)
    if cdata:
        val = cdata.group(1).strip()
    return val or None


def _parse_date(raw: str | None) -> str | None:
    """GDACS 날짜 → `YYYY-MM-DD`. 못 읽으면 **지어내지 않고 None**."""
    if not raw:
        return None
    raw = raw.strip()
    # RFC 822: "Thu, 21 Aug 2026 00:00:00 GMT"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", raw)
    if m:
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                  "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        month = months.get(m.group(2).lower())
        if month:
            try:
                return dt.date(int(m.group(3)), month, int(m.group(1))).isoformat()
            except ValueError:
                return None
    # ISO: "2026-08-21T00:00:00" / "2026-08-21"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    return None


def _iso3_list(block: str) -> list[str]:
    """이벤트가 가리키는 ISO3 목록.

    `gdacs:iso3` 를 먼저 믿는다. 다국가 이벤트라 쉼표로 여럿일 수 있다.
    비었으면 `gdacs:country` 이름을 country_resolve 로 넘긴다 — **추측은
    거기서도 안 한다.** 못 읽으면 빈 목록이고, 이벤트는 버려진다.
    """
    raw = _tag(block, "iso3")
    out: list[str] = []
    if raw:
        for part in re.split(r"[,;/]", raw):
            code = part.strip().upper()
            if len(code) == 3 and code.isalpha() and code not in out:
                out.append(code)
    if out:
        return out
    return resolve_countries(_tag(block, "country"))


def parse_gdacs(xml: str) -> list[dict]:
    """GDACS RSS 본문 → 이벤트 목록. 읽을 수 없는 항목은 조용히 버리지 않고
    `skipped` 사유로 세어 돌려준다 — 는 건 호출부의 몫이라 여기선 건너뛴다.

    형태가 예상 밖이면 **가짜를 만들지 않는다.** 국가나 종류를 못 읽은 항목은
    창을 열 수 없으므로 제외한다.
    """
    events: list[dict] = []
    for block in re.findall(r"<item[ >].*?</item>", xml, re.S | re.I):
        etype = (_tag(block, "eventtype") or "").strip().upper()
        alert = (_tag(block, "alertlevel") or "").strip().lower()
        if not etype or not alert:
            continue
        iso3s = _iso3_list(block)
        if not iso3s:
            continue
        date = _parse_date(_tag(block, "fromdate")) or _parse_date(_tag(block, "pubDate"))
        if not date:
            continue
        event_id = _tag(block, "eventid") or ""
        for iso3 in iso3s:
            events.append({
                # 같은 이벤트가 여러 나라를 덮으면 나라별로 하나씩 센다 —
                # 감시창은 나라 단위로 열리기 때문이다.
                "key": f"{etype}-{event_id or date}-{iso3}",
                "event_id": event_id,
                "type": etype,
                "alert": alert,
                "iso3": iso3,
                "country": _tag(block, "country"),
                "date": date,
                "title": (_tag(block, "title") or "")[:200],
            })
    return events


def fetch_gdacs_events() -> list[dict]:
    """GDACS RSS 수집. 실패는 **종류를 담아 올린다** — None 을 돌려주지 않는다."""
    try:
        resp = requests.get(GDACS_RSS, headers=USER_AGENT, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise DisasterWatchError(
            f"GDACS RSS 수집 실패({type(e).__name__}): {str(e)[:160]}"
        ) from e
    events = parse_gdacs(resp.text)
    if not events:
        # 0건은 '재난이 없다' 가 아니라 '파서가 못 읽었다' 일 수 있다. 이 둘이
        # 구분 안 되면 조용한 실패가 된다 — 응답 앞부분을 증거로 실어 올린다.
        raise DisasterWatchError(
            "GDACS 응답에서 이벤트를 하나도 못 읽었다(파서·형식 확인 필요): "
            f"{resp.text[:200]}"
        )
    return events


# ── 저장 ────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"events": {}}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # 파일이 깨졌다고 층 전체를 죽이지 않는다. 다음 주기에 다시 쌓인다.
        return {"events": {}}
    return data if isinstance(data.get("events"), dict) else {"events": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def record_events(events: list[dict], today: dt.date | None = None) -> dict:
    """새 이벤트를 저장소에 합치고 오래된 것을 지운다.

    ★ 창을 여는 등급만 저장한다 ★ Green 까지 쌓으면 파일이 계속 커지는데
    쓰이지도 않는다.

    반환: {"stored": 전체, "new": 새로 들어온 수, "pruned": 지운 수}
    """
    today = today or dt.date.today()
    state = _load_state()
    stored: dict = state["events"]

    new = 0
    for ev in events:
        if ev["alert"] not in OPENING_ALERT_LEVELS:
            continue
        if ev["key"] in stored:
            # 같은 이벤트가 등급이 올라올 수 있다(Orange → Red). 갱신은 하되
            # first_seen 은 유지한다 — 창의 기준일이 흔들리면 안 된다.
            stored[ev["key"]].update({"alert": ev["alert"], "title": ev["title"]})
            continue
        stored[ev["key"]] = {**ev, "first_seen": today.isoformat()}
        new += 1

    cutoff = today - dt.timedelta(days=EVENT_RETENTION_DAYS)
    stale = [k for k, v in stored.items()
             if (_as_date(v.get("date")) or today) < cutoff]
    for k in stale:
        del stored[k]

    _save_state(state)
    return {"stored": len(stored), "new": new, "pruned": len(stale)}


def _as_date(raw: str | None) -> dt.date | None:
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


# ── 감시창 ──────────────────────────────────────────────────────────────

def open_windows(today: dt.date | None = None) -> dict[str, list[dict]]:
    """지금 열려 있는 감시창을 국가(ISO3)별로.

    각 항목: 질병·키워드·재난종류·경보등급·재난 후 며칠·창 구간·근거.
    창은 나라별로 여러 재난에서 동시에 열릴 수 있다(홍수 뒤 지진 등).
    """
    today = today or dt.date.today()
    out: dict[str, list[dict]] = {}
    for ev in _load_state()["events"].values():
        date = _as_date(ev.get("date"))
        rules = WATCH_RULES.get(ev.get("type", ""))
        if not date or not rules:
            continue
        elapsed = (today - date).days
        if elapsed < 0:            # 미래 날짜(예보성 항목) — 아직 창이 아니다
            continue
        for disease, keywords, lo, hi, why in rules:
            if not lo <= elapsed <= hi:
                continue
            out.setdefault(ev["iso3"], []).append({
                "disease": disease,
                "keywords": keywords,
                "disaster_type": ev["type"],
                "alert_level": ev["alert"],
                "country": ev.get("country"),
                "disaster_date": ev["date"],
                "days_since_disaster": elapsed,
                "window_days": [lo, hi],
                "rationale": why,
                "title": ev.get("title"),
            })
    return out


def watched_countries(today: dt.date | None = None) -> set[str]:
    """지금 감시창이 하나라도 열려 있는 나라들. local_news 가 이걸 쓴다."""
    return set(open_windows(today))


def disaster_watch_report(today: dt.date | None = None) -> dict:
    """`/api/disaster-watch` 응답. 저장된 것만 읽는다(네트워크 없음)."""
    today = today or dt.date.today()
    windows = open_windows(today)
    state = _load_state()
    countries = [
        {
            "country_iso3": iso3,
            "country": items[0].get("country"),
            "open_windows": sorted(items, key=lambda w: w["days_since_disaster"]),
            "window_count": len(items),
            "diseases": sorted({w["disease"] for w in items}),
        }
        for iso3, items in windows.items()
    ]
    countries.sort(key=lambda c: (-c["window_count"], c["country_iso3"]))
    return {
        "countries": countries,
        "watched_country_count": len(countries),
        "stored_events": len(state["events"]),
        "updated_at": state.get("updated_at"),
        "data_source": "GDACS (Global Disaster Alert and Coordination System, 무료·키 불필요)",
        "opening_alert_levels": sorted(OPENING_ALERT_LEVELS),
        # ↓ 이 층이 무엇이 아닌지 — 항상 붙인다
        "is_prediction": False,
        "windows_calibrated": False,
        "note": "감시창은 '이 기간에 이 질병 보도가 뜨면 우연으로 넘기지 말라'는 뜻이지 "
                "발병 예측이 아니다. 잠복 구간은 문헌 기반 추정이며 이 시스템의 과거 "
                "데이터로 보정하지 않았다(windows_calibrated=False).",
        "disclaimer": "GDACS Green 경보로는 창을 열지 않는다 — 매일 다수가 발령돼 전부 열면 "
                      "세계의 절반이 감시 대상이 되고 신호가 의미를 잃기 때문이다. 이 판단의 "
                      "근거는 노이즈 관리이지 역학이 아니다.",
    }


def collect_disaster_watch() -> dict:
    """수집 주기 1회분: GDACS 를 받아 저장하고 현재 창을 돌려준다.

    ★ 반환값은 signals.jsonl 에 **매 주기** 통째로 쌓인다 ★ 그래서 규칙표에서
    오는 고정 텍스트(근거 문장·키워드 목록)는 빼고 압축해서 돌려준다. 안 그러면
    같은 문장이 매시간 다시 적혀 하루 1MB 가까이 불어난다. 전체 상세가 필요하면
    `/api/disaster-watch` 를 보면 된다 — 거기선 저장소를 그때그때 읽는다.
    """
    events = fetch_gdacs_events()
    counts = record_events(events)
    report = disaster_watch_report()
    return {
        **counts,
        "fetched": len(events),
        "watched_country_count": report["watched_country_count"],
        "countries": [
            {
                "country_iso3": c["country_iso3"],
                "country": c["country"],
                "diseases": c["diseases"],
                "open_windows": [
                    {"disease": w["disease"], "disaster_type": w["disaster_type"],
                     "alert_level": w["alert_level"],
                     "days_since_disaster": w["days_since_disaster"],
                     "window_days": w["window_days"]}
                    for w in c["open_windows"]
                ],
            }
            for c in report["countries"]
        ],
    }

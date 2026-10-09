"""WHO 질병발생소식(DON) → 정답 테이블(outbreak_timeline) 적재 (2026-10-07).

## 왜 만드는가

정답 경로(`declaration_ingest`)는 신뢰도 0.90 이상이면서 `신규발생` 인 신호를 요구하는데, 그런
신호를 만드는 생산자가 없어 한 건도 못 적재했다(자세한 진단은 `ground_truth_channel` 머리말).
DON 은 WHO 가 **사람이 쓴 공식 발표**라 AI 추출을 거치지 않는다 — 정답이 채점받는 쪽보다 믿을 만해야
한다는 원칙(자기 숙제를 자기가 매기지 않는다)을 지키면서 정답 경로를 열 수 있다.

## ★ 정직성 경계선 ★

- **라이브 검증 못 함.** 이 샌드박스는 who.int 에 못 나간다(프록시 403). 응답 형식(`value[]`, 제목·발행일
  필드명)은 기억에 기대 짰고, 그래서 **필드명을 여러 이름으로 읽고**, 한 건도 못 읽으면 가짜 대신 사유와
  응답 앞부분을 들고 올라온다. 프로덕션 첫 21:00 슬롯 로그가 이 파일의 검증이다.
- **DON 은 '선언'이 아니라 'WHO 가 알렸다'이다.** 같은 질병·국가·연도의 첫 DON 만 정답으로 올린다
  (`upsert` 가 첫 날짜를 지킨다) — 이후 갱신 보고가 선언일을 뒤로 밀지 못한다. 마일스톤은 `who_statement`
  (WHO 공개 성명)이고 이미 `DECLARATION_MILESTONES` 에 있다.
- **국가를 못 읽으면 건너뛴다.** `Mpox – African Region` 같은 지역·다국가 제목은 추측하지 않는다.
- **자가채점 위험은 낮지만 0이 아니다.** 우리 입력 신호는 WHO AFRO RSS 건수·뉴스·검색행태이고 DON 본문을
  신호로 쓰지 않는다. 그래도 뉴스가 DON 을 인용하는 경로는 있을 수 있다 — `source_type="who_don"` 으로 갈라
  두어 나중에 트랙레코드에서 따로 볼 수 있게 한다.
"""
from __future__ import annotations

import datetime as dt
import re

import requests

import db

from .country_resolve import resolve_countries
from .declaration_ingest import event_id_for, event_name_for
from .event_dedup import normalize_disease

USER_AGENT = {"User-Agent": "EpiWeather-DonIngest/1.0 (epiweather.kr)"}
TIMEOUT = 20
DON_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
PAGE_SIZE = 100
SAMPLES_PER_REASON = 3
SAMPLE_CHARS = 90

MILESTONE = "who_statement"
SOURCE_TYPE = "who_don"
# 이 일수보다 오래된 DON 은 올리지 않는다 — 아주 옛 발표를 한꺼번에 올려 타임라인을 부풀리지 않는다.
LOOKBACK_DAYS = 400

_TITLE_KEYS = ("Title", "title")
_DATE_KEYS = ("PublicationDate", "PublicationDateAndTime", "publicationDate", "DateCreated")
_ID_KEYS = ("DonId", "donId", "UrlName", "Id")
_SEPARATOR = re.compile(r"\s+[–—-]\s+")


class DonError(RuntimeError):
    """이 층의 실패. 종류를 반드시 들고 다닌다."""


def _first(item: dict, keys: tuple[str, ...]):
    for k in keys:
        if item.get(k):
            return item[k]
    return None


# 제목 앞의 군더더기("Disease Outbreak News: " 같은) — 질병 이름에 섞이지 않게 뗀다.
_PREFIX = re.compile(r"^\s*(?:disease outbreak news|don)\s*[:;\-–—]\s*", re.I)
# "Outbreak of cholera in Angola" 의 "Outbreak of" — 질병명 앞 일반어.
_LEAD = re.compile(r"^\s*(?:(?:an?\s+)?(?:outbreak|outbreaks|cases?|cluster|clusters|human cases?|confirmed cases?|"
                   r"detection|emergence|spread)\s+(?:of|in)\s+)+", re.I)


def split_title(title: str | None) -> tuple[str, str] | None:
    """`질병 – 국가` 제목을 (질병, 국가 문구)로. 구분자가 없으면 None — 추측하지 않는다."""
    parts = _SEPARATOR.split(_PREFIX.sub("", (title or "").strip()))
    if len(parts) < 2:
        return None
    disease = " ".join(parts[:-1]).strip()
    place = parts[-1].strip()
    return (disease, place) if disease and place else None


def title_options(title: str | None) -> list[tuple[str, str]]:
    """제목에서 (질병, 국가 문구) 후보를 **믿을 만한 순서**로. 여기선 추측만 늘어놓고,
    실제로 쓸지는 호출부가 국가 문구가 **사전에서 나라로 읽히는지**로 가린다(읽히지 않으면 버린다).

    형식: ① `질병 – 국가`(구분자) ② `… in 국가` ③ `질병, 국가`.
    """
    text = _PREFIX.sub("", (title or "").strip())
    out: list[tuple[str, str]] = []
    first = split_title(text)
    if first:
        out.append(first)
    head, sep, tail = text.rpartition(" in ")
    if sep and head.strip() and tail.strip():
        out.append((_LEAD.sub("", head).strip() or head.strip(), tail.strip()))
    head, sep, tail = text.rpartition(", ")
    if sep and head.strip() and tail.strip():
        out.append((head.strip(), tail.strip()))
    return out


def parse_items(payload: object, today: dt.date | None = None) -> dict:
    """응답 → {"declarations": [...], "read": n, "skipped": {사유: n}}.

    선언 하나 = (질병, 국가, 발행일). 한 제목이 여러 나라를 가리키면 나라별로 하나씩 낸다.
    """
    today = today or dt.date.today()
    items = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise DonError(f"DON 응답에서 목록(value[])을 못 찾았다(형식 확인 필요): {str(payload)[:200]}")

    skipped: dict[str, int] = {}
    samples: dict[str, list[str]] = {}

    def skip(reason: str, title: str | None = None) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1
        # 못 읽은 제목의 예 — 어떤 형식을 못 읽는지는 제목을 봐야 안다(2026-10-09: 기간 안 54건 중 40건이 그랬다).
        if title and len(samples.setdefault(reason, [])) < SAMPLES_PER_REASON:
            samples[reason].append(str(title)[:SAMPLE_CHARS])

    cutoff = today - dt.timedelta(days=LOOKBACK_DAYS)
    declarations: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            skip("항목 형식 아님")
            continue
        raw_title = _first(item, _TITLE_KEYS)
        options = title_options(raw_title)
        if not options:
            skip("제목 형식 모름", raw_title)
            continue
        when = _date(_first(item, _DATE_KEYS))
        if when is None:
            skip("날짜 못 읽음", raw_title)
            continue
        if when < cutoff or when > today:
            skip("기간 밖")
            continue
        # 후보 가운데 **국가 문구가 사전에서 나라로 읽히는 첫 번째**만 쓴다. 하나도 안 읽히면 추측하지 않는다.
        disease = place = None
        isos: list[str] = []
        for d, p in options:
            isos = resolve_countries(p)
            if isos:
                disease, place = d, p
                break
        if not isos:
            skip("국가 못 읽음", raw_title)
            continue
        for iso3 in isos:
            declarations.append({
                "disease": disease, "place": place, "iso3": iso3, "date": when,
                "source": f"WHO DON {_first(item, _ID_KEYS) or ''}".strip(),
            })

    if items and not declarations and not skipped.get("기간 밖") and \
            skipped.get("제목 형식 모름", 0) + skipped.get("날짜 못 읽음", 0) == len(items):
        raise DonError("DON 항목을 하나도 못 읽었다(제목·날짜 필드명 확인 필요): "
                       f"{str(items[0])[:200]}")
    return {"declarations": declarations, "read": len(items), "skipped": skipped, "samples": samples}


def _date(raw) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None


def fetch_items() -> object:
    try:
        resp = requests.get(DON_URL, headers=USER_AGENT, timeout=TIMEOUT,
                            params={"$orderby": "PublicationDate desc", "$top": PAGE_SIZE})
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as e:
        raise DonError(f"WHO DON 수집 실패({type(e).__name__}): {str(e)[:160]}") from e


def ingest_don(payload: object | None = None, today: dt.date | None = None) -> dict:
    """DON 을 받아 정답 테이블에 올린다. 실패는 호출부로 올린다(조용히 0건으로 만들지 않는다).

    반환: {"등재": 새로 올라간 수, "이미있음": n, "건너뜀": {사유: n}, "검토": n}
    """
    parsed = parse_items(fetch_items() if payload is None else payload, today)
    added = existing = 0
    for d in parsed["declarations"]:
        event_id = event_id_for(d["disease"], d["iso3"], d["date"])
        before = db.get_timeline(event_id)
        if any(m.get("milestone") == MILESTONE for m in before.get("milestones", [])):
            existing += 1          # 같은 질병·국가·연도의 첫 발표가 이미 정답이다 — 날짜를 뒤로 밀지 않는다
            continue
        canonical = normalize_disease(d["disease"])
        name_disease = d["disease"] if canonical in (None, d["disease"]) else f"{d['disease']} {canonical}"
        db.upsert_timeline_event(
            event_id,
            event_name_for(name_disease, d["place"], d["date"]),
            d["date"].isoformat(),
            MILESTONE,
            f"WHO 질병발생소식(DON) 발표 — {d['disease']} / {d['place']}",
            d["source"],
            SOURCE_TYPE,
        )
        added += 1
    return {"등재": added, "이미있음": existing, "건너뜀": parsed["skipped"], "검토": parsed["read"],
            "예시": parsed.get("samples") or {}}


def samples_line(result: dict) -> str | None:
    """못 읽은 제목의 예 한 줄. 없으면 None. 다음 파서 개선이 추측이 아니라 실제 제목을 보고 하게 한다."""
    ex = result.get("예시") or {}
    if not ex:
        return None
    return "WHO DON 못 읽은 제목 예: " + " · ".join(
        f"{reason}[{' / '.join(titles)}]" for reason, titles in sorted(ex.items()))


def summary(result: dict) -> str:
    parts = [f"WHO DON 정답 적재 {result.get('등재', 0)}건 / 검토 {result.get('검토', 0)}건"]
    if result.get("이미있음"):
        parts.append(f"이미 있음 {result['이미있음']}")
    skipped = result.get("건너뜀") or {}
    if skipped:
        parts.append(" · ".join(f"{k} {v}" for k, v in sorted(skipped.items())))
    return " · ".join(parts)

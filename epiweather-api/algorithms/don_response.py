"""발병국이 어떻게 대처하는가 — WHO DON '대응(Response)' 단락에서 대응 조치를 읽는다 (2026-11-16).

캡틴: "발병국가가 어떻게 대처를 하고 있는가" · "내가 얘기한 거 빠트리지 마라".
관측 데이터 활용 계획 ⑥. 유료 AI 추출을 새로 돌리지 않는다 — WHO 가 사람이 쓴 공식 발표(DON)의
`Response` 칸을 **정해진 낱말 규칙**으로 읽는다. 운영 로그(2026-11-15 21:19)가 DON 항목에
`Response`·`Advice` 칸이 있음을 보여 줬다.

## 무엇을 말하고 무엇을 말하지 않나

- 말함: "WHO 가 이 발표에서 이 나라(들)에 대해 이런 대응이 있었다고 적었다" + 근거 문장(영어 원문) + 발표일 + DON 번호.
- 말하지 않음: 실행 정도·범위·효과. 낱말이 맞았다는 것이지 조치가 충분했다는 판정이 아니다.
- 한 발표가 여러 나라를 말하면 나라마다 같은 조치를 붙인다 — 어느 나라가 했는지까지는 가르지 않는다(`shared_countries`).
- 나라를 못 읽은 발표(제목·본문 모두)는 저장하지 않고 센다. `Response` 칸이 빈 발표도 센다.

## 누가 부르나

main 의 21:00 슬롯 — WHO DON 정답 적재와 같은 응답(payload)을 쓴다(WHO 를 두 번 부르지 않음).
"""
from __future__ import annotations

import datetime as dt
import html
import re

from .country_resolve import resolve_countries
from .who_don_declarations import (
    _DATE_KEYS,
    _ID_KEYS,
    _TITLE_KEYS,
    BODY_MAX_COUNTRIES,
    _date,
    _first,
    body_countries,
    title_options,
)

LOOKBACK_DAYS = 400
EVIDENCE_CHARS = 240
RESPONSE_KEYS = ("Response", "PublicHealthResponse")
_TAG = re.compile(r"<[^>]+>")
_SENTENCE = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(•-])")

# 조치 → (한국어·영어·프랑스어 이름, 낱말 규칙). 넓게 잡지 않는다 — 'vaccine' 한 낱말만으로는 접종으로 세지 않는다.
MEASURES: dict[str, tuple[str, str, str, re.Pattern[str]]] = {
    "contact_tracing": ("접촉자 추적", "Contact tracing", "Recherche des contacts",
                        re.compile(r"contact[- ]tracing|contacts? (?:were|are|have been|being) (?:traced|identified|listed|followed|monitored)", re.IGNORECASE)),
    "isolation": ("환자 격리", "Isolation of cases", "Isolement des cas",
                  re.compile(r"\bisolat(?:ion|ed)\b", re.IGNORECASE)),
    "quarantine": ("검역·격리 관찰", "Quarantine", "Quarantaine",
                   re.compile(r"\bquarantin", re.IGNORECASE)),
    "vaccination": ("백신 접종", "Vaccination", "Vaccination",
                    re.compile(r"vaccinat(?:ion|ed)|immuni[sz]ation campaign|ring vaccination", re.IGNORECASE)),
    "surveillance": ("감시 강화", "Enhanced surveillance", "Surveillance renforcée",
                     re.compile(r"(?:enhanced|strengthened|intensified|heightened) (?:\w+ ){0,2}surveillance|surveillance (?:has been|was|were|is being) (?:enhanced|strengthened|intensified)|active case[- ]finding|active case search", re.IGNORECASE)),
    "entry_screening": ("입국·국경 검사", "Entry/border screening", "Contrôle aux frontières",
                        re.compile(r"(?:points? of entry|border|airports?|ports?|entry|exit)\b.{0,40}\bscreening|screening (?:at|of) (?:\w+ ){0,3}(?:points? of entry|borders?|airports?|travell?ers)", re.IGNORECASE)),
    "lab_testing": ("검사·실험실 확인", "Laboratory testing", "Tests de laboratoire",
                    re.compile(r"laborator(?:y|ies)\b.{0,40}\b(?:testing|confirm|capacity|analys)|samples? (?:were|was|have been) (?:collected|sent|shipped|tested)", re.IGNORECASE)),
    "case_management": ("환자 치료 체계", "Case management", "Prise en charge des cas",
                        re.compile(r"case management|treatment cent(?:re|er)s?|clinical management", re.IGNORECASE)),
    "ipc": ("감염 예방·관리", "Infection prevention and control", "Prévention et contrôle des infections",
            re.compile(r"infection prevention and control|\bIPC\b", re.IGNORECASE)),
    "risk_communication": ("위험 소통·주민 참여", "Risk communication", "Communication sur les risques",
                           re.compile(r"risk communication|community engagement|awareness campaigns?|health education", re.IGNORECASE)),
    "vector_control": ("매개체 방제", "Vector control", "Lutte antivectorielle",
                       re.compile(r"vector control|larvicid|insecticid|indoor residual spraying|fogging", re.IGNORECASE)),
    "emergency_declared": ("비상사태·발병 선포", "Outbreak/emergency declared", "Épidémie/urgence déclarée",
                           re.compile(r"declared (?:an? |the )?(?:outbreak|emergency|public health emergency|state of emergency)|state of (?:health )?emergency", re.IGNORECASE)),
    "rapid_response": ("신속대응팀 파견", "Rapid response team", "Équipe d’intervention rapide",
                       re.compile(r"rapid response teams?|deploy(?:ed|ment of) (?:\w+ ){0,3}(?:experts|teams?)", re.IGNORECASE)),
    "who_support": ("WHO 지원", "WHO support", "Soutien de l’OMS",
                    re.compile(r"WHO (?:(?:is|has|has been) )?(?:supporting|supported|provided|providing|deployed|delivered)", re.IGNORECASE)),
}


def response_text(item: dict) -> str:
    for key in RESPONSE_KEYS:
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", raw))).strip()
    return ""


def _evidence(text: str, m: re.Match[str]) -> str:
    """일치한 자리를 품은 문장 하나(최대 EVIDENCE_CHARS 자). 잘린 쪽은 `…`."""
    start = 0
    for s in _SENTENCE.finditer(text[: m.start() + 1]):  # 일치가 문장 첫 낱말이어도 그 앞 경계를 본다
        start = s.end()
    nxt = _SENTENCE.search(text, m.end())
    end = nxt.start() if nxt else len(text)
    sent = text[start:end].strip()
    if len(sent) <= EVIDENCE_CHARS:
        return sent
    at = m.start() - start
    lo = max(0, at - EVIDENCE_CHARS // 3)
    cut = sent[lo: lo + EVIDENCE_CHARS]
    return ("…" if lo > 0 else "") + cut.strip() + ("…" if lo + EVIDENCE_CHARS < len(sent) else "")


def measures_in(text: str) -> list[dict]:
    out = []
    for key, (_ko, _en, _fr, pat) in MEASURES.items():
        m = pat.search(text)
        if m:
            out.append({"measure": key, "evidence": _evidence(text, m)})
    return out


def item_countries(item: dict) -> tuple[str | None, list[str], str]:
    """(질병, 나라 ISO3 목록, 읽은 곳 'title'|'body'|''). 정답 적재와 같은 규칙 — 제목 먼저, 안 되면 본문 앞부분."""
    title = _first(item, _TITLE_KEYS)
    for disease, place in title_options(title):
        isos = resolve_countries(place)
        if isos:
            return disease, isos, "title"
    isos = body_countries(item)
    if isos and len(isos) <= BODY_MAX_COUNTRIES:
        opts = title_options(title)
        return (opts[0][0] if opts else str(title or "").strip()) or None, isos, "body"
    return None, [], ""


def don_url(item: dict) -> str | None:
    """DON 페이지 주소 — `UrlName`(예: 2026-DON624) 기준. 형식은 WHO 사이트 주소 규칙을 따른 것이고 라이브로 확인 못 함."""
    slug = item.get("UrlName") or item.get("DonId")
    return f"https://www.who.int/emergencies/disease-outbreak-news/item/{slug}" if slug else None


def parse_responses(payload: object, today: dt.date | None = None) -> dict:
    """응답 → {"rows": [...], "read", "with_response", "no_response", "no_country", "out_of_window"}."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    items = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise TypeError(f"DON 응답에서 목록(value[])을 못 찾음: {str(payload)[:160]}")
    cutoff = today - dt.timedelta(days=LOOKBACK_DAYS)
    rows: list[dict] = []
    counts = {"read": 0, "with_response": 0, "no_response": 0, "no_country": 0, "out_of_window": 0}
    for item in items:
        if not isinstance(item, dict):
            continue
        counts["read"] += 1
        when = _date(_first(item, _DATE_KEYS))
        if when is None or when < cutoff or when > today:
            counts["out_of_window"] += 1
            continue
        text = response_text(item)
        if not text:
            counts["no_response"] += 1
            continue
        counts["with_response"] += 1
        disease, isos, read_from = item_countries(item)
        if not isos:
            counts["no_country"] += 1
            continue
        don_id = str(_first(item, _ID_KEYS) or "")
        for found in measures_in(text):
            for iso3 in isos:
                rows.append({
                    "don_id": don_id, "iso3": iso3, "disease": disease, "published": when.isoformat(),
                    "measure": found["measure"], "evidence": found["evidence"], "url": don_url(item),
                    "title": str(_first(item, _TITLE_KEYS) or "")[:200], "country_from": read_from,
                    "shared_countries": len(isos),
                })
    return {"rows": rows, **counts}


def ingest_responses(payload: object, today: dt.date | None = None) -> dict:
    import db

    parsed = parse_responses(payload, today)
    new = sum(1 for r in parsed["rows"] if db.upsert_don_response(r))
    return {**{k: v for k, v in parsed.items() if k != "rows"}, "rows": len(parsed["rows"]), "new": new,
            "countries": len({r["iso3"] for r in parsed["rows"]})}


def summary(result: dict) -> str:
    return (f"🛡 WHO DON 대응 조치: 검토 {result['read']}건 · 대응 단락 있음 {result['with_response']} · "
            f"단락 없음 {result['no_response']} · 나라 못 읽음 {result['no_country']} · 기간 밖 {result['out_of_window']} → "
            f"조치 {result['rows']}건(새 {result['new']}) · {result['countries']}개국")

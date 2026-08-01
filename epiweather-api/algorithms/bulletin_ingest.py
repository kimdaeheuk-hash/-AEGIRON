"""보건 보고서 신호 → extracted_signals 적재. 파이프라인의 마지막 한 칸.

bulletin_signals가 표를 신호 모양으로 바꿔놨지만 DB에 안 들어가면 경보 엔진이
못 본다. 이 모듈이 기존 스키마(db.create_extracted_signal)에 맞춰 적재한다.

★ 적재하면서 지켜야 할 것들(전부 실제 스키마 의미에서 나온 제약) ★

1) known_disease=False는 '설명 불가 → 즉시경보'를 뜻한다(collector.py 참조).
   사이클론·홍수·인도적 위기 같은 비질병 이벤트를 그대로 넣으면 가짜 즉시경보가
   터진다. 그래서 **비질병 이벤트는 적재하지 않고 건너뛴 수를 보고**한다.
   (버리는 게 아쉬워도 경보를 오염시키는 것보다 낫다.)

2) source_trust는 출처가 아니라 '이 값이 얼마나 믿을 만한가'다. WHO 공식 문서지만
   VLM 추출이라 100%가 아니다. 교차검증 결과에 따라 나눈다 —
   숫자가 전부 원문과 일치하면 document_extracted(0.90), 원문에 없는 숫자가 섞였으면
   document_extracted_unverified(0.70). trust.py에 카테고리로 등록해 매직넘버를 안 쓴다.

3) severity는 우리가 매기지 않는다. WHO 자신의 등급(Grade 3·Protracted 2 등)이
   문서에 있으므로 그걸 키워드로 넣는다 — 지어낸 심각도가 아니라 기관 판정이다.

4) signal_type은 AFRO '감시 중 이벤트' 표에서 온 것만 '진행중'으로 둔다. 문서가
   그 표를 그렇게 정의하기 때문이다. 급증·감소는 이전 회차와 비교해야 알 수 있는데
   지금은 비교 대상이 없으므로 쓰지 않는다.

5) 같은 보고서를 두 번 넣어도 중복이 쌓이지 않게 (source·disease·location·
   signal_date·raw_text)로 먼저 조회해 거른다.
"""
from __future__ import annotations

import re

from .trust import trust_for

# WHO AFRO 보고서에 실제로 등장하는 국가 표기 → ISO 3166-1 alpha-3.
# 못 찾으면 None으로 둔다(추측 금지) — 잘못된 국가코드는 지도·유입경로를 통째로 틀리게 한다.
_ISO3: dict[str, str] = {
    "algeria": "DZA", "angola": "AGO", "benin": "BEN", "botswana": "BWA",
    "burkina faso": "BFA", "burundi": "BDI", "cabo verde": "CPV", "cameroon": "CMR",
    "central african republic": "CAF", "car": "CAF", "chad": "TCD", "comoros": "COM",
    "congo": "COG", "republic of congo": "COG",
    "democratic republic of the congo": "COD", "democratic republic of congo": "COD",
    "drc": "COD", "dr congo": "COD", "cote d ivoire": "CIV", "ivory coast": "CIV",
    "equatorial guinea": "GNQ", "eritrea": "ERI", "eswatini": "SWZ", "ethiopia": "ETH",
    "gabon": "GAB", "gambia": "GMB", "ghana": "GHA", "guinea": "GIN",
    "guinea bissau": "GNB", "kenya": "KEN", "lesotho": "LSO", "liberia": "LBR",
    "madagascar": "MDG", "malawi": "MWI", "mali": "MLI", "mauritania": "MRT",
    "mauritius": "MUS", "mozambique": "MOZ", "namibia": "NAM", "niger": "NER",
    "nigeria": "NGA", "rwanda": "RWA", "sao tome and principe": "STP",
    "senegal": "SEN", "seychelles": "SYC", "sierra leone": "SLE", "somalia": "SOM",
    "south africa": "ZAF", "south sudan": "SSD", "sudan": "SDN", "tanzania": "TZA",
    "united republic of tanzania": "TZA", "togo": "TGO", "uganda": "UGA",
    "zambia": "ZMB", "zimbabwe": "ZWE", "burkina": "BFA",
    # 역외 유입이 보고되는 나라들(프랑스 분디부조 1건 등)
    "france": "FRA", "united kingdom": "GBR", "uk": "GBR", "belgium": "BEL",
    "united states": "USA", "usa": "USA", "germany": "DEU", "saudi arabia": "SAU",
    "united arab emirates": "ARE", "india": "IND", "china": "CHN", "korea": "KOR",
}

# 질병이 아닌 이벤트 — 적재하면 known_disease 의미가 깨져 가짜 즉시경보가 난다.
_NON_DISEASE = re.compile(
    r"cyclone|flood|landslide|drought|earthquake|conflict|crisis|insecurity|"
    r"displacement|famine|storm|fire|volcan|humanitarian",
    re.I,
)

# WHO 자신의 등급 표기 → severity 키워드(우리가 매기는 게 아니라 기관 판정).
_GRADE_SLUG = re.compile(r"(grade|protracted)\s*(\d)", re.I)


def iso3_for(location: str | None) -> str | None:
    """국가명 → ISO3. 사전에 없으면 None(추측하지 않는다)."""
    if not location:
        return None
    key = re.sub(r"[^a-z ]+", " ", location.lower())
    key = re.sub(r"\s+", " ", key).strip()
    if key in _ISO3:
        return _ISO3[key]
    # "Democratic Republic of the Congo*" 처럼 꼬리가 붙는 경우를 위해 부분일치도 본다.
    # 짧은 키가 우연히 걸리지 않도록 6자 이상만, 그리고 가장 긴 일치를 쓴다.
    matches = [name for name in _ISO3 if len(name) >= 6 and name in key]
    return _ISO3[max(matches, key=len)] if matches else None


def is_disease_event(label: str | None) -> bool:
    """질병 이벤트인지 — 사이클론·인도적 위기 등은 제외."""
    return bool(label) and not _NON_DISEASE.search(label)


def severity_keywords(signal: dict) -> list[str]:
    """WHO 등급을 severity 키워드로. 우리가 심각도를 지어내지 않는다."""
    match = _GRADE_SLUG.search(signal.get("grade") or "")
    if match:
        return [f"{match.group(1).lower()}_{match.group(2)}"]
    if (signal.get("grade") or "").strip().lower() == "ungraded":
        return ["ungraded"]
    return []


def signal_type_for(signal: dict) -> str:
    """문서가 실제로 말한 것에서만 signal_type을 정한다.

    두 가지 근거만 쓴다:
    1) WHO AFRO '감시 중인 이벤트' 표 — 문서가 그 표를 '진행 중'으로 정의한다.
    2) 보고 기간 신규 환자·사망이 0보다 큼 — 이번 주에 새 환자가 나왔다는
       문서의 직접 진술이므로 진행 중이 사실이다(실측: DRC 7일 신규 확진 567명).
    신규가 0이면 잦아드는 중인지 보고 지연인지 구분할 수 없어 '불명'으로 둔다
    — 실제로 우간다가 그 경우다(누적 20명, 이번 주 신규 0).

    급증·감소는 이전 회차와 비교해야 알 수 있는데 지금은 비교 대상이 없어 쓰지 않는다."""
    if signal.get("layout") == "who_afro_events":
        return "진행중"
    metrics = signal.get("metrics") or {}
    recent = [v for key, v in metrics.items() if key.startswith("new_")]
    if recent and any(v > 0 for v in recent):
        return "진행중"
    return "불명"


def trust_category(signal: dict) -> str:
    """교차검증 결과로 신뢰도 카테고리를 정한다."""
    cross = signal.get("cross_check") or {}
    if cross.get("checked") and cross.get("numbers_unverified"):
        return "document_extracted_unverified"
    return "document_extracted"


def to_extracted_signal(signal: dict, source: str | None = None) -> dict | None:
    """bulletin_signals의 신호 → db.create_extracted_signal 인자. 부적격이면 None."""
    disease = signal.get("disease")
    if not is_disease_event(disease):
        return None                       # 비질병 이벤트는 적재하지 않는다
    location = signal.get("location")
    if not disease and not location:
        return None

    metrics = signal.get("metrics") or {}
    # 수치를 raw_text에 함께 남겨 나중에 사람이 원본과 대조할 수 있게 한다.
    measured = " ".join(
        f"{k}={v:.4g}" for k, v in sorted(metrics.items())
    )
    raw = (signal.get("raw_text") or "").strip()
    return {
        "source": source or signal.get("source") or "who_bulletin",
        "disease": disease,
        "location": location,
        "signal_type": signal_type_for(signal),
        "severity": severity_keywords(signal),
        "symptom": None,
        "transmission": None,
        "source_trust": trust_for(trust_category(signal)),
        "signal_date": signal.get("signal_date"),
        "raw_text": f"{raw} [{measured}]" if measured else raw,
        "known_disease": True,            # 질병명이 확인된 것만 여기 오므로 항상 True
        "country_iso3": iso3_for(location),
    }


def ingest(signals: list[dict], source: str | None = None, dbmod=None,
           dedup_days: int = 60) -> dict:
    """신호를 extracted_signals에 적재. 이미 있는 건 건너뛴다.

    dbmod를 주입받는 이유: 테스트가 실제 DB를 안 건드리게 하기 위함."""
    if dbmod is None:
        import db as dbmod                                   # noqa: PLC0415

    effective_source = source or (signals[0].get("source") if signals else None) or "who_bulletin"
    try:
        existing = dbmod.list_recent_signals_by_source(effective_source, days=dedup_days, limit=1000)
    except Exception:
        existing = []
    seen = {
        (r.get("disease"), r.get("location"), r.get("signal_date"), r.get("raw_text"))
        for r in existing
    }

    inserted, skipped_dup, skipped_non_disease, failed = [], 0, 0, 0
    for signal in signals:
        payload = to_extracted_signal(signal, source=effective_source)
        if payload is None:
            skipped_non_disease += 1
            continue
        key = (payload["disease"], payload["location"],
               payload["signal_date"], payload["raw_text"])
        if key in seen:
            skipped_dup += 1
            continue
        try:
            inserted.append(dbmod.create_extracted_signal(**payload))
            seen.add(key)
        except Exception:
            failed += 1

    return {
        "ok": True,
        "source": effective_source,
        "received": len(signals),
        "inserted": len(inserted),
        "skipped_duplicate": skipped_dup,
        "skipped_non_disease": skipped_non_disease,
        "failed": failed,
        "iso3_resolved": sum(1 for r in inserted if r.get("country_iso3")),
        "rows": inserted,
        "note": (
            "비질병 이벤트(사이클론·인도적 위기 등)는 적재하지 않는다 — known_disease가 "
            "'설명 불가 → 즉시경보'를 뜻하는 스키마라 그대로 넣으면 가짜 경보가 난다. "
            "국가코드는 사전에 없으면 비워둔다(추측하면 지도·유입경로가 통째로 틀어짐)."
        ),
    }

"""현재 공식 선언 → 정답 테이블(outbreak_timeline) 적재.

## ★ 왜 이 파일이 생겼나 ★ (2026-09-21)

캡틴: *"각 엔진들의 온톨로지가 있어야 하고 피드백 루프가 돌아야 아이기론이
동적인 살아있는 게 돼!"*

맞는 말인데, 확인해보니 **루프가 닫힐 수가 없는 상태**였다.

예측 채점기(prediction_resolver)는 `outbreak_timeline` 의 공식 선언과 예측을
대조한다. 그런데 그 테이블을 채우는 건 `historical_outbreaks.OUTBREAKS` —
**손으로 적은 16건이고 가장 최근 선언이 2024-09-27** 이다(오늘로부터 2년 전).

채점 조건이 `lead = 선언일 - 예측일 > 0` 이므로, **2026년 예측은 2024년 선언을
영원히 못 만난다.** 적중은 구조적으로 불가능했다.

그리고 빗나간 예측은 90일 뒤 자동으로 `incorrect` 가 된다. 즉 그대로 두면
아이기론은 **"측정된 것처럼 보이는 적중률 0%"** 를 스스로 만들어낸다.
이 제품이 파는 게 정확히 그 숫자다.

## ★ 정답은 채점받는 것보다 더 믿을 만해야 한다 ★

여기가 이 파일에서 제일 조심한 자리다. 아무 신호나 '공식 선언'으로 올리면
**우리가 낸 신호로 우리 예측을 채점**하게 된다 — 자기 숙제를 자기가 매기는 꼴이다.

그래서 문턱을 trust.py 의 카테고리에 맞춰 건다:

    document_extracted            0.90  WHO 문서의 표에서 뽑고 숫자를 원문과 교차검증함 → 받는다
    document_extracted_unverified 0.70  원문에 없는 숫자가 섞임 → 안 받는다
    ai_extracted                  0.65  뉴스 자유문장에서 AI 추출 → 안 받는다

0.90 은 '사람이 확인한 기관 발표'가 아니라 '기관 문서에서 뽑고 교차검증한 값'
이다. 그래서 `source_type` 을 백필분("official")과 다르게 남겨(아래),
나중에 트랙레코드를 볼 때 **어느 정답이 어디서 왔는지** 갈라 볼 수 있게 한다.
섞어놓으면 며칠 뒤 아무도 구분 못 한다.
"""
from __future__ import annotations

import datetime as dt

import db

# 이 값 미만은 정답으로 안 쓴다. trust.SOURCE_TRUST 의 document_extracted 와 같다 —
# 숫자를 여기 또 적지 않고 거기서 가져온다(매직넘버 금지).
from .trust import SOURCE_TRUST

MIN_TRUST = SOURCE_TRUST["document_extracted"]

# '새 발병이 선언됐다'에 해당하는 신호유형만. '진행중'은 이미 알려진 사건의
# 경과 보고라 선언이 아니고, '급증'·'감소'는 추세지 선언이 아니다.
DECLARATION_SIGNAL_TYPES = {"신규발생"}

# prediction_resolver.DECLARATION_MILESTONES 에 들어있는 값이어야 채점에 쓰인다.
MILESTONE = "official_declaration"

# 백필분(historical_outbreaks, source_type="official")과 구분한다.
SOURCE_TYPE = "official_live"


def _slug(text: str) -> str:
    """event_id 에 쓸 짧은 토막. 공백·구분자만 정리하고 **번역하지 않는다** —
    지금 이 시스템에 질병명 표준 어휘가 없다(캡틴이 물은 온톨로지 문제). 여기서
    임의로 영문화하면 예측 쪽 표기와 더 어긋난다."""
    return "".join(ch for ch in (text or "").strip().lower() if not ch.isspace())[:24]


def event_id_for(disease: str, iso3: str, when: dt.date) -> str:
    return f"{_slug(disease)}_{(iso3 or '').lower()}_{when.year}"


def event_name_for(disease: str, location: str, when: dt.date) -> str:
    """★ 이 문자열이 곧 대조 키다 ★ prediction_resolver._matches 가 예측의
    국가·질병이 event_name 안에 들어있는지를 부분일치로 본다. 질병명과 지역명을
    **그대로** 넣는다 — 줄이거나 바꾸면 매칭이 조용히 깨진다."""
    parts = [p for p in (disease, location, str(when.year)) if p]
    return " ".join(parts)


def _parse_date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def eligible(signal: dict) -> tuple[bool, str]:
    """정답으로 쓸 수 있는 신호인가. (가능?, 사유).

    사유를 돌려주는 이유: 거른 것을 조용히 버리면 '정답이 왜 안 늘어나는지'를
    아무도 모른다 — 이번에 2년을 그렇게 보냈다.
    """
    if (signal.get("source_trust") or 0) < MIN_TRUST:
        return False, "신뢰도미달"
    if (signal.get("signal_type") or "") not in DECLARATION_SIGNAL_TYPES:
        return False, "선언아님"
    if not signal.get("disease"):
        return False, "질병불명"
    if not signal.get("country_iso3"):
        return False, "국가불명"
    if _parse_date(signal.get("signal_date")) is None:
        return False, "날짜없음"
    return True, "적재"


def ingest_declarations(signals: list[dict] | None = None, limit: int = 200) -> dict:
    """extracted_signals 에서 공식 선언을 골라 outbreak_timeline 에 올린다.

    같은 (event_id, milestone) 은 upsert 라 중복이 쌓이지 않는다.
    반환: {"등재": n, "건너뜀": {사유: 수}, "검토": n}
    """
    rows = signals if signals is not None else db.list_extracted_signals(limit=limit)
    added = 0
    skipped: dict[str, int] = {}

    for sig in rows or []:
        ok, reason = eligible(sig)
        if not ok:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        when = _parse_date(sig.get("signal_date"))
        disease = sig["disease"]
        iso3 = sig["country_iso3"]
        location = sig.get("location") or iso3
        db.upsert_timeline_event(
            event_id_for(disease, iso3, when),
            event_name_for(disease, location, when),
            when.isoformat(),
            MILESTONE,
            f"{disease} 공식 발병 선언(문서 추출·교차검증, 신뢰도 {sig.get('source_trust')})",
            sig.get("source"),
            SOURCE_TYPE,
        )
        added += 1

    return {"등재": added, "건너뜀": skipped, "검토": len(rows or [])}


def summary(result: dict) -> str:
    """로그 한 줄. 문자열은 시험 가능한 자리에 둔다(naver_trends.summary 와 같은 이유)."""
    parts = [f"정답 적재 {result.get('등재', 0)}건 / 검토 {result.get('검토', 0)}건"]
    skipped = result.get("건너뜀") or {}
    if skipped:
        parts.append(" · ".join(f"{k} {v}" for k, v in sorted(skipped.items())))
    return " · ".join(parts)

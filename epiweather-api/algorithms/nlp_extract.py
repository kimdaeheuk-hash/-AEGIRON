"""NLP 신호 추출 — 인수인계서 Part5 ⑦.

global_watch.py가 Perplexity/Tavily로 모아온 자유문장은 그대로는 GAI 계산에
못 들어간다(숫자가 아니라 문장이라서). Claude로 구조화 JSON으로 강제 변환해
DB(extracted_signals)에 쌓아야 disease·location 단위로 집계·조회가 가능해진다.

신뢰도는 모델에게 묻지 않는다 — 텍스트 출처(global_watch.py의 수집 경로)로
이미 정해져 있으므로(trust.py의 ai_extracted=0.65) 그 값을 그대로 주입한다.
"""
from __future__ import annotations
import json
import re
import datetime as dt

# 사유 문자열을 만드는 자리는 한 곳이다(common.py). 여기에만 뒀더니 조달(TED)
# 층이 같은 실수를 되풀이했다 — 이름만 찍고 상태코드를 버렸다.
# 이름을 그대로 재노출해 기존 호출부(nx.brief_reason)를 깨지 않는다.
from .common import brief_reason, tally      # noqa: F401  (재노출)
from .trust import trust_for

_ISO3_RE = re.compile(r"^[A-Z]{3}$")

MODEL = "claude-haiku-4-5-20251001"

VALID_SIGNAL_TYPES = {"급증", "감소", "신규발생", "진행중", "종료", "불명"}

# 인수인계서 Part4 한계④: 텍스트에 연도가 없으면 모델이 학습시점 기준 연도로
# 잘못 추측하는 현상이 실측 확인됨(2026년 맥락 텍스트를 2024년으로 답함).
# → 오늘 날짜를 프롬프트에 명시하고, 연도 불명확하면 추측 대신 null을 강제.
EXTRACT_PROMPT = """다음 감염병 관련 텍스트에서 아래 항목을 추출해 JSON 객체만 출력해(다른 텍스트 절대 금지).
오늘 날짜는 {today}야. date는 텍스트에 연도가 명시돼 있을 때만 채우고, 연도 없이 "지난달"·"6월 20일"처럼만
나오면 절대 추측하지 말고 null로 둬(특히 네 학습 시점 연도로 채우지 마).
모르는 항목은 null. severity는 텍스트에서 드러나는 심각도를 나타내는 영어 소문자 키워드 배열(예: ["unusual","spike"]), 없으면 빈 배열.
signal_type은 다음 중 하나만 골라: 급증, 감소, 신규발생, 진행중, 종료, 불명.
known_disease는 텍스트가 설명하는 병이 의학적으로 이미 알려지고 연구된 질병(예: 에볼라, 인플루엔자, 한타바이러스처럼
이름·원인체·임상양상이 규명된 것)이면 true. 원인불명·미규명·기존 질병 패턴과 안 맞는 새로운 증후군이면 false.
질병명을 못 뽑아도(disease가 null이어도) 텍스트가 "독감 유사 증상"처럼 알려진 패턴을 가리키면 true로 둬도 됨 — disease 칸과
독립적으로 판단해.

country_iso3는 location이 가리키는 국가의 ISO 3166-1 alpha-3 코드(예: 한국→KOR, 미국→USA, 콩고민주공화국→COD)를
대문자 3글자로 채워. 텍스트가 국가 하나로 특정되지 않으면(여러 국가 언급, "아프리카 전역"처럼 지역 단위, 국가 불명)
절대 추측하지 말고 반드시 null.

형식:
{{"disease": "질병명 또는 null", "location": "지역/국가 또는 null", "country_iso3": "ISO 3166-1 alpha-3 3글자 또는 null", "signal_type": "위 6개 중 하나", "severity": ["키워드"], "symptom": "증상 요약 또는 null", "transmission": "전파경로 또는 null", "date": "YYYY-MM-DD 또는 null", "known_disease": true 또는 false}}

텍스트:
{text}"""


def build_prompt(raw_text: str) -> str:
    """추출 프롬프트를 완성해 반환. Claude·NIM 등 모든 백엔드가 동일 프롬프트를 쓴다."""
    return EXTRACT_PROMPT.format(today=dt.date.today().isoformat(), text=raw_text[:2000])


def parse_extraction_detailed(model_text: str, raw_text: str,
                              source: str) -> tuple[dict | None, dict]:
    """(구조화 dict | None, 형식 위반 기록).

    방어 로직은 모델의 오출력을 조용히 고쳐서 넘긴다 — 파이프라인엔 그게 맞지만,
    '몇 번이나 형식을 어겼나'가 그 과정에서 통째로 지워진다. 모델을 바꿔 달 때는
    바로 그 숫자가 판단 근거라서(작은 모델일수록 스키마를 못 지킨다) 교정 사실을
    따로 남긴다. notes는 비교·감사용이며 DB에는 안 들어간다."""
    notes = {
        "json_parse_failed": False,
        "not_an_object": False,
        "signal_type_coerced": False,
        "country_iso3_dropped": False,
        "severity_coerced": False,
    }
    try:
        raw = (model_text or "").strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
    except Exception:
        notes["json_parse_failed"] = True
        return None, notes
    if not isinstance(data, dict):
        notes["not_an_object"] = True   # 모델이 배열 등 객체가 아닌 형태로 응답
        return None, notes

    signal_type = data.get("signal_type")
    if signal_type not in VALID_SIGNAL_TYPES:
        notes["signal_type_coerced"] = True
        signal_type = "불명"
    severity = data.get("severity") or []
    if isinstance(severity, str):
        notes["severity_coerced"] = True
        severity = [severity]

    country_iso3 = data.get("country_iso3")
    if not isinstance(country_iso3, str) or not _ISO3_RE.match(country_iso3):
        # 모델 오출력(소문자·전체국명·다중언급 등) 방어. 애초에 null이면 위반이 아니다.
        notes["country_iso3_dropped"] = country_iso3 is not None
        country_iso3 = None

    record = {
        "source": source,
        "disease": data.get("disease"),
        "location": data.get("location"),
        "country_iso3": country_iso3,
        "signal_type": signal_type,
        "severity": severity,
        "symptom": data.get("symptom"),
        "transmission": data.get("transmission"),
        "source_trust": trust_for("ai_extracted"),
        "signal_date": data.get("date"),
        "known_disease": bool(data.get("known_disease", True)),
        "raw_text": raw_text,
    }
    return record, notes


def parse_extraction(model_text: str, raw_text: str, source: str) -> dict | None:
    """모델의 원시 응답 문자열 → 구조화 dict. 코드펜스·정규화·검증을 한 곳에서 처리.
    어떤 백엔드(Claude/NIM/로컬)가 만들었든 출력 스키마와 방어 로직이 동일하게 적용된다."""
    return parse_extraction_detailed(model_text, raw_text, source)[0]


# ── 실패가 사유를 달고 나오게 한다 (2026-09-04) ────────────────────
# 운영 로그에서 3일 연속 이렇게 찍혔다:
#
#     09-02  NLP 구조화 추출: 0건 저장
#     09-03  NLP 구조화 추출: 0건 저장
#     09-04  NLP 구조화 추출: 0건 저장 · 추출실패 5
#
# 마지막 줄의 '5'는 어제 붙인 계수기가 처음 드러낸 것이고, 앞의 두 줄은 실패였는지
# 중복건너뜀이었는지조차 구분이 안 됐다. **그런데 5를 보고도 할 수 있는 게 없었다** —
# 아래 except가 사유를 통째로 삼켰기 때문이다. 키가 죽었는지, 모델명이 틀렸는지,
# 크레딧이 떨어졌는지, 모델이 JSON을 못 지켰는지가 전부 같은 None으로 접혔다.
#
# 계수기만으로는 부족하다. **몇 번 실패했나** 다음에 반드시 **왜** 가 와야 한다.
PARSE_FAILED = "파싱실패"

# 외부 LLM 폴백도 능력 장부에 남긴다. NIM 층(nvidia_text)은 이미 남기는데 폴백은
# 안 남겨서, "NIM이 죽고 폴백도 죽었다"와 "NIM만 죽었다"를 /api/status에서 구분할
# 수 없었다. 폴백이 마지막 방어선이므로 그게 살아 있는지가 특히 중요하다.
EXTERNAL_LLM_CAPABILITY = "external_llm_extract"


def _record_external(ok: bool, detail: str | None = None) -> None:
    """장부 기록이 본 기능을 막으면 안 된다(nvidia.record_layer_call과 같은 규칙)."""
    try:
        from .capability_ledger import record
        record(EXTERNAL_LLM_CAPABILITY, ok=ok, detail=detail,
               endpoint="api.anthropic.com", sovereign=False)
    except Exception:                                     # noqa: BLE001
        pass


def llm_raw(raw_text: str, api_key: str) -> tuple[str | None, str | None]:
    """(원시 응답, 실패 사유). aegiron_model.nim_raw의 외부 LLM 짝.

    성공하면 (문자열, None), 실패하면 (None, 사유). **사유가 None이 아닌 채로
    조용히 넘어가는 경로를 두지 않는다.**"""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=250,
            messages=[{"role": "user", "content": build_prompt(raw_text)}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
    except Exception as exc:                              # noqa: BLE001
        _record_external(ok=False, detail=f"{type(exc).__name__}: {exc}")
        return None, brief_reason(exc)
    _record_external(ok=True)
    return raw, None


def extract_signal_detailed(raw_text: str, source: str,
                            api_key: str) -> tuple[dict | None, str | None]:
    """(구조화 dict | None, 실패 사유 | None).

    호출 실패와 파싱 실패를 가른다 — 전자는 키·엔드포인트 문제고 후자는 모델이
    스키마를 못 지킨 것이라, 손댈 곳이 완전히 다르다."""
    raw, reason = llm_raw(raw_text, api_key)
    if raw is None:
        return None, reason
    record = parse_extraction(raw, raw_text, source)
    return record, None if record is not None else PARSE_FAILED


def extract_signal(raw_text: str, source: str, api_key: str) -> dict | None:
    """자유문장 1건 → 구조화 dict. 모델 호출/파싱 실패 시 None.
    사유까지 필요하면 extract_signal_detailed를 쓸 것."""
    return extract_signal_detailed(raw_text, source, api_key)[0]


EXTRACTION_DEDUP_WINDOW_DAYS = 3  # 같은 source의 원문이 이 기간 내 그대로 재수집되면 재추출 안 함


def extract_from_global_watch_detailed(
    watch_result: dict, api_key: str | None = None,
    dedup_window_days: int = EXTRACTION_DEDUP_WINDOW_DAYS,
) -> dict:
    """run_global_watch() 결과의 signals 리스트 중 text가 있는 항목만 구조화.

    추출은 aegiron_model을 거친다 — NIM(자체/NVIDIA 호스팅) → 로컬 → 외부 LLM
    순으로 시도되고, 어느 경로가 처리했는지가 레코드의 ai_provider에 남는다.
    예전엔 여기서 Claude를 직접 불러서, NIM 키를 넣어도 운영에선 안 쓰였다.

    providers는 '어느 모델이 몇 건 뽑았나'다. NIM을 켰는데 여기가 계속
    external_llm_fallback이면 NIM이 실패해 폴백 중이라는 뜻 — 조용히 넘어가지
    않도록 수집기가 이 값을 로그로 찍는다.

    global_watch.py의 소스(WHO EMRO·Africa CDC 등)는 고정 피드라 매시간
    수집기가 돌아도 기사가 안 바뀌면 원문(raw_text)도 완전히 그대로다 —
    unexplained.py의 능동검색(Perplexity/Tavily, 매번 문구가 재구성됨)과
    다름. 같은 source에서 최근 며칠 내 이미 뽑아낸 원문과 완전히 같으면
    Claude를 다시 호출하지 않고 건너뛴다: (1) API 비용 낭비를 막고,
    (2) 같은 기사가 여러 번 저장돼 _nlp_raw_score의 신뢰도가중 평균이
    실제보다 부풀려지는 걸 막는다. 원문이 조금이라도 다르면(기사 갱신)
    새 신호로 취급 — 완전 일치만 건너뛰므로 실제 갱신을 놓치지 않는다."""
    import db

    from .aegiron_model import extract_record

    extracted: list[dict] = []
    providers: dict[str, int] = {}
    # ★ '몇 번' 다음엔 반드시 '왜' ★ 실패 수만 세면 손댈 곳을 못 찾는다.
    # {"nvidia_nim_hosted: HTTPError 404": 5, "external_llm_fallback: 파싱실패": 5}
    failure_reasons: dict[str, int] = {}
    # 폴백이 구해준 횟수 — 성공했어도 NIM이 죽고 있다는 사실은 봐야 한다.
    rescued_by_fallback = 0
    blocked = 0
    failed = 0
    skipped_duplicate = 0

    for s in watch_result.get("signals", []):
        text = s.get("text")
        if not text:
            continue
        try:
            recent = db.list_recent_signals_by_source(s["id"], days=dedup_window_days)
        except Exception:
            recent = []
        if any(r.get("raw_text") == text for r in recent):
            skipped_duplicate += 1
            continue

        record, prov = extract_record(text, source=s["id"], api_key=api_key)
        for attempt in prov.get("attempts") or []:
            failure_reasons[attempt] = failure_reasons.get(attempt, 0) + 1
        if record is None:
            if prov["blocked"]:
                blocked += 1
            else:
                failed += 1
            continue
        if prov.get("attempts"):
            rescued_by_fallback += 1
        providers[prov["ai_provider"]] = providers.get(prov["ai_provider"], 0) + 1
        extracted.append(record)

    return {
        "records": extracted,
        "providers": providers,
        "blocked": blocked,
        "failed": failed,
        "skipped_duplicate": skipped_duplicate,
        # 실패한 경로별 횟수. 성공분의 폴백 자취도 포함되므로 합계가 failed보다
        # 클 수 있다 — 그건 오류가 아니라 '한 건에 두 경로가 죽었다'는 뜻이다.
        "failure_reasons": failure_reasons,
        "rescued_by_fallback": rescued_by_fallback,
    }


def extract_from_global_watch(
    watch_result: dict, api_key: str | None = None,
    dedup_window_days: int = EXTRACTION_DEDUP_WINDOW_DAYS,
) -> list[dict]:
    """레코드만 필요할 때 쓰는 얇은 래퍼(기존 호출부 호환)."""
    return extract_from_global_watch_detailed(
        watch_result, api_key=api_key, dedup_window_days=dedup_window_days
    )["records"]


def extraction_summary(out: dict) -> str:
    """수집기 로그 한 줄. 수집기에서 즉석으로 조립하지 않고 여기서 만든다 —
    발할라 조각 판정을 수집기에 인라인으로 짰다가 첫 성공 주기에 터뜨린 전례가
    있어서(stale_parts), 로그 문자열도 시험 가능한 곳에 둔다.

    ★ 옛 모양을 견딘다 ★ 배포 직후엔 지난 주기가 만든 값에 새 키가 없을 수
    있다. .get 으로 읽고, 없으면 그 조각만 빠진다 — 줄이 통째로 안 나오면
    '조용해진 층'이 하나 더 생긴다."""
    detail = [f"{len(out.get('records') or [])}건 저장"]
    providers = out.get("providers") or {}
    if providers:
        detail.append(", ".join(f"{k}={v}" for k, v in sorted(providers.items())))
    if out.get("skipped_duplicate"):
        detail.append(f"중복건너뜀 {out['skipped_duplicate']}")
    if out.get("failed"):
        detail.append(f"추출실패 {out['failed']}")
    if out.get("blocked"):
        detail.append(f"주권차단 {out['blocked']}")
    # ★ '몇 번' 뒤에 반드시 '왜' ★ 09-04 운영에서 '추출실패 5'만 찍혀서, NIM이
    # 죽은 건지 폴백이 죽은 건지 판단할 수 없었고 잘못된 처방이 나올 뻔했다.
    why = out.get("failure_reasons") or {}
    if why:
        # 정렬하지 않는다 — 삽입 순서가 곧 시도 순서(NIM → 로컬 → 폴백)라,
        # 줄을 왼쪽부터 읽으면 어디까지 갔다가 무엇 때문에 멈췄는지가 그대로 나온다.
        detail.append("경로별: " + " · ".join(f"{k}×{v}" for k, v in why.items()))
    # 폴백이 매번 구해주고 있으면 NIM은 사실상 꺼져 있는 것이다.
    if out.get("rescued_by_fallback"):
        detail.append(f"폴백이 구제 {out['rescued_by_fallback']}")
    return " · ".join(detail)

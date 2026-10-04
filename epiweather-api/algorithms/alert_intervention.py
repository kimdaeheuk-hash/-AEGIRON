"""경보 → NPI 반사실 브리핑 (Stage 5 연결).

배경: 지금까지 경보는 "무엇이 온다"에서 끝났다(예측 도구). 받는 사람은 "그래서
뭘 하라고?"에 답을 못 받는다. 이 모듈은 critical/high 경보를 받아 Stage 5 SEIR
방어 시뮬레이션(defense.run_defense)을 자동으로 돌려 **"무대응 vs 개입"** 반사실을
붙인다 — 예측 도구를 의사결정 도구로 바꾼다. 그리고 그 예측+시나리오를
OpenTimestamps로 봉인해(prediction_timestamp), 운영할수록 '검증 가능한 트랙레코드'가
스스로 쌓이게 한다(복제 불가능한 자산).

★ 정직성 경계선 ★
- 반사실 숫자는 표준 SEIR '모델 시나리오'다 — R0·CFR·레버 효과는 예시 상수라
  실제 병원체·지역으로 캘리브레이션 전엔 '방향성 참고'다. "N명 구한다"가 아니라
  "모델 가정 하 N명"으로만 말한다(검증 불가능한 반사실 세일즈 금지).
- 질병→위협 매핑은 휴리스틱(추정)이다 — basis에 근거를 남기고 '추정'으로 표시.
- 봉인은 "예측이 맞았다"가 아니라 "이 시각에 이 내용을 갖고 있었다"만 증명한다
  (Proof of Existence). 네트워크 없으면 sealed=False로 정직 표시, 생성은 안 막는다.
"""
from __future__ import annotations
import datetime as dt

from .common import PRESETS, THREAT
from .defense import run_defense
from . import disease_params as dp

# 질병명 키워드 → 위협 시나리오(추정). 고치명 병원체는 severe, 신종/미상은 novel.
# 근거: 대략적 CFR 수준(에볼라·마르부르크 25~90%, 니파 40~75%, MERS ~35%).
_SEVERE_KWS = ("에볼라", "ebola", "마르부르크", "marburg", "니파", "nipah",
               "mers", "메르스", "h5n1", "조류", "avian", "라싸", "lassa",
               "두창", "천연두", "smallpox")
_NOVEL_KWS = ("신종", "미상", "불명", "원인불명", "novel", "unknown",
              "sars", "사스", "코로나", "corona", "엠폭스", "mpox", "monkeypox")


def assume_threat(disease: str | None, tier: str) -> tuple[str, str]:
    """질병·경보등급 → (위협 시나리오, 근거문). 휴리스틱임을 근거에 명시."""
    d = (disease or "").lower()
    if any(k in d for k in _SEVERE_KWS):
        return "severe", f"고치명 병원체 추정(‘{disease}’) → severe. 휴리스틱, 실제 CFR로 대체 가능."
    if any(k in d for k in _NOVEL_KWS):
        return "novel", f"신종/불확실 병원체 추정(‘{disease}’) → novel. 휴리스틱."
    if disease:
        return "flu", f"일반 감염병 추정(‘{disease}’) → flu 수준. 휴리스틱, 보수적 하한."
    # 질병 불명 → 경보등급으로 예방적 매핑
    return ("novel", "질병 불명 + critical → 예방적 novel 가정.") if tier == "critical" \
        else ("flu", "질병 불명 + high → flu 수준 가정.")


def _scenario_view(defense_out: dict) -> dict:
    """run_defense 출력에서 브리핑에 필요한 핵심만 추린다."""
    r = defense_out["result"]
    return {
        "peak_infected": r["peak_infected"],
        "peak_day": r["peak_day"],
        "total_deaths": r["total_deaths"],
        "hosp_overflow_days": r["hosp_overflow_days"],
        "saved_lives": defense_out["saved_lives"],
        "saved_pct": defense_out["saved_pct"],
        "effective_rt": defense_out["effective_rt"],
        "transmission_controlled": defense_out["transmission_controlled"],
    }


DISCLAIMER_MEASURED = ("SEIR를 질병별 문헌 실측 R0/CFR로 캘리브레이션함. 단 발병·지역·"
                       "시기별 편차가 크므로 절대값이 아닌 '방향성 참고'로 사용. "
                       "‘구할 생명’은 모델 추정이며 실측·보장이 아니다.")
DISCLAIMER_GENERIC = ("표준 SEIR 모델 시나리오 — R0·CFR·개입효과는 generic tier 예시 상수다. "
                      "이 질병은 실측 파라미터 미등재라 방향성만 참고. "
                      "‘구할 생명’은 모델 가정 하 추정이며 실측·보장이 아니다.")


def intervention_brief(disease: str | None, country: str | None,
                       tier: str, score: float, threat: str | None = None) -> dict:
    """경보 → 무대응/mild/strong 반사실 브리핑. threat 미지정이면 질병에서 추정.
    질병이 실측 파라미터 레지스트리에 있으면 그 R0/CFR로 SEIR를 캘리브레이션한다."""
    explicit_threat = threat in THREAT
    if explicit_threat:
        threat_basis = f"명시된 위협 시나리오 사용({threat}) — 질병 캘리브레이션 생략."
    else:
        threat, threat_basis = assume_threat(disease, tier)

    # 위협을 명시하지 않았고 질병별 실측 파라미터가 있으면 그걸로 캘리브레이션.
    # (명시했으면 그 generic tier를 존중해 캘리브레이션하지 않는다.)
    measured = None if explicit_threat else dp.lookup(disease)
    params = dp.as_threat_params(measured) if measured else None

    mild = run_defense(dict(PRESETS["mild"]), threat, params=params)
    strong = run_defense(dict(PRESETS["strong"]), threat, params=params)
    no_action = strong["baseline_no_intervention"]   # PRESETS["none"] 결과

    # 권장: 전파를 통제(rt<1)하는 최소 개입. mild로 되면 mild, 아니면 strong.
    recommended = "mild" if mild["transmission_controlled"] else "strong"
    rec_view = _scenario_view(mild if recommended == "mild" else strong)

    # 실측 캘리브레이션 여부 + 사용한 역학 파라미터를 정직하게 노출.
    if measured:
        epidemic_params = {
            "R0": measured["R0"], "R0_range": list(measured["R0_range"]),
            "cfr": measured["cfr"], "cfr_range": list(measured["cfr_range"]),
            "source": measured["source"],
        }
        calibration = "disease_measured"
        disclaimer = DISCLAIMER_MEASURED
    else:
        sp = THREAT[threat]
        epidemic_params = {"R0": sp["R0"], "cfr": sp["cfr"], "source": f"generic tier '{threat}' 예시 상수"}
        calibration = "generic_tier"
        disclaimer = DISCLAIMER_GENERIC

    # 사람간 지속전파가 없는 병원체(R0<1)는 대규모 확산이 안 나는 게 정직 — 명시.
    limited = epidemic_params["R0"] < 1.0
    transmission_mode = measured.get("transmission_mode") if measured else None
    if transmission_mode == "environmental":
        # 환경전파형(레지오넬라 등): 사람간 전파가 아예 없어 SEIR·NPI가 무의미하다.
        # 확산 서사 대신 '오염원 제거' 대응을 그대로 노출한다.
        spread_note = measured.get("intervention_note") or (
            "환경 노출형 — 사람간 전파 없음. 격리·거리두기는 무의미하고 오염원 조사·소독이 대응."
        )
    elif limited:
        spread_note = ("이 병원체는 사람간 지속전파가 제한적(R0<1)이라 대규모 유행 위험은 낮음 "
                       "— 개별 치명률은 높아도 SEIR상 확산은 작다(격리·접촉추적 위주).")
    else:
        spread_note = None
    if transmission_mode:
        epidemic_params["transmission_mode"] = transmission_mode

    headline = (
        f"무대응 시 사망 {no_action['total_deaths']:,}명·병상초과 "
        f"{no_action['hosp_overflow_days']}일 → 권장개입({'중' if recommended == 'mild' else '강'})으로 "
        f"사망 {rec_view['total_deaths']:,}명(구할 생명 {rec_view['saved_lives']:,}명, "
        f"병상초과 {rec_view['hosp_overflow_days']}일). "
        f"{'질병별 실측 캘리브레이션' if measured else '모델 추정(generic)'}."
    )
    # 모델값을 역사상 최대 발병과 자동 대조한다. 발병률 상한으로 1차 교정하지만
    # 상한 자체가 판단치라 놓치는 게 남는다 — 그걸 여기서 드러낸다.
    plaus = dp.plausibility(measured.get("key") if measured else None,
                            no_action["total_deaths"])
    return {
        "disease": disease,
        "country": country,
        "alert_tier": tier,
        "alert_score": score,
        "assumed_threat": threat,
        "threat_basis": threat_basis,
        "calibration": calibration,
        "epidemic_params": epidemic_params,
        "limited_human_transmission": limited,
        "spread_note": spread_note,
        "scenarios": {
            "no_action": {
                "peak_infected": no_action["peak_infected"],
                "peak_day": no_action["peak_day"],
                "total_deaths": no_action["total_deaths"],
                "hosp_overflow_days": no_action["hosp_overflow_days"],
            },
            "mild": _scenario_view(mild),
            "strong": _scenario_view(strong),
        },
        "recommended": recommended,
        "recommended_saved_lives": rec_view["saved_lives"],
        "headline": headline,
        "disclaimer": disclaimer,
        # 역사 대조 결과를 숫자와 같이 실어 보낸다 — 경고가 docstring에만 있으면
        # 숫자만 떨어져 나가 화면·자료에서 그대로 쓰인다.
        "plausibility": plaus,
        "is_modeled_scenario": True,
    }


def summary_line(brief: dict) -> str:
    """텔레그램용 요약. ★ headline 만 보내면 안 된다 ★ (2026-09-19)

    실측 사고다. 09-19 05:47, 아이기론이 처음으로 사람에게 보낸 경보에 이 줄이
    붙어서 나갔다:

        무대응 시 사망 69,092명 … 질병별 실측 캘리브레이션.

    브리핑 dict 에는 disclaimer 가 제대로 들어 있었다 — "절대값이 아닌 방향성
    참고", "구할 생명은 모델 추정이며 실측·보장이 아니다". 그런데 사람이 실제로
    읽는 한 줄에는 그게 **하나도 안 실렸다.** 게다가 headline 이 "질병별 실측
    캘리브레이션"으로 끝나서, 경고가 빠진 자리에 오히려 **더 믿음직한 말**이
    들어갔다. 모듈은 정직했는데 출구가 그걸 흘렸다.

    숫자 자체도 단서가 필요하다. 저 69,092명은 covid19 실측 파라미터로 나오는데
    그 출처 문자열이 "COVID-19 조상주 추정 … 초기 CFR ~1.5%(IFR 더 낮음)"이다.
    지금 도는 계통에 2020년 초기 치명률을 적용한 값이라는 뜻이고, 그 사실은
    파라미터 출처에 적혀 있으므로 같이 보낸다.

    사람간 전파가 제한적인 병원체(R0<1)·환경전파형이면 spread_note 도 같이
    간다 — 그게 빠지면 SEIR 숫자만 남아 대유행처럼 읽힌다.
    """
    if brief.get("calibration") == "generic_tier":
        # ★ 질병별 파라미터가 없으면 숫자를 만들지 않는다 ★ (2026-10-04, 텔레그램 본문 검토)
        # `행동신호 · social_dengue`(Mastodon 게시자 12명)의 경보에 이런 줄이 나갔다:
        #
        #     🧭 개입 브리핑: 무대응 시 사망 41,779명 … 구할 생명 41,774명 … 모델 추정(generic).
        #     ⚠️ 예보가 아니라 모델 시나리오다 · 파라미터: generic tier 'flu' 예시 상수
        #
        # 경보 이름이 질병명이 아니라서 실측 파라미터를 못 찾고 '독감' 일반 예시 상수로 돌렸고, 지역도
        # 인구도 없다. 고지문은 있었지만 폰에서는 첫 줄의 큰 숫자가 먼저 읽힌다 — 뎅기를 독감
        # 파라미터로 돌린 값이 '사망 4만 명'이 되어 나가는 건 없는 근거를 만든 것이다. 숫자 없이
        # 사유만 보낸다. 브리핑 본체(dict)는 그대로라 명시 요청하는 API 는 영향이 없다.
        return ("🧭 개입 브리핑: 만들지 않음 — 이 경보에서 질병을 특정할 수 없어 질병별 파라미터가 "
                "없다. 일반 예시 상수로 만든 사망·병상 숫자는 근거가 없어 싣지 않는다.")
    line = f"🧭 개입 브리핑: {brief['headline']}"
    if brief.get("spread_note"):
        line += f"\n   ↳ {brief['spread_note']}"
    source = (brief.get("epidemic_params") or {}).get("source")
    tail = "⚠️ 예보가 아니라 모델 시나리오다"
    if source:
        tail += f" · 파라미터: {source}"
    return f"{line}\n   {tail}"


def sealed_brief(disease: str | None, country: str | None,
                 tier: str, score: float, threat: str | None = None,
                 seal: bool = True) -> dict:
    """브리핑 + OpenTimestamps 봉인. 예측+시나리오를 이 시각에 가졌음을 증명.
    seal=False거나 네트워크 없으면 sealed=False로 정직 표시(생성은 안 막음)."""
    brief = intervention_brief(disease, country, tier, score, threat)
    record = {
        "id": f"{country or '?'}:{disease or '?'}:{dt.date.today().isoformat()}",
        "predicted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "country": country,
        "disease": disease,
        "risk_score": score,
        "basis": brief["headline"],
    }
    from .prediction_timestamp import canonical_hash
    digest = canonical_hash(record)
    proof = None
    if seal:
        try:
            from .prediction_timestamp import submit_timestamp
            proof = submit_timestamp(digest)
        except Exception:
            proof = None
    brief["timestamp"] = {
        "digest_sha256": digest,
        "sealed": bool(proof),
        "proof_hex": proof,
        "note": ("OpenTimestamps 제출됨(pending) — 몇 시간~하루 내 비트코인 체인에 확정. "
                 "이 시각에 이 내용을 가졌음만 증명(정확도 주장 아님)."
                 if proof else
                 "봉인 미완(네트워크 없음/미요청) — 다이제스트는 계산됨. 생성은 정상."),
    }
    return brief


def enrich_alerts_with_briefs(alerts: list[dict], seal: bool = False) -> list[dict]:
    """경보 목록 각각에 NPI 브리핑 요약을 붙인다(자동연결). 알림·대시보드용.
    기본 seal=False — 대량 알림에서 매건 네트워크 봉인은 피하고, 봉인은 단건 조회
    엔드포인트에서 수행한다."""
    out = []
    for a in alerts:
        try:
            brief = intervention_brief(
                a.get("disease") or a.get("label"), a.get("country") or a.get("country_iso3"),
                a.get("tier", "high"), a.get("score", 0),
            )
            a = {**a, "npi_summary": summary_line(brief), "npi_brief": brief}
        except Exception as e:
            # 처방이 빠진 채 경보만 나가는 건 "그래서 뭘 해야 하나"에 답하는 이
            # 제품의 핵심이 조용히 사라진 것이다. 경보 발송은 막지 않되(사람에게
            # 알리는 게 우선), 왜 빠졌는지는 반드시 남긴다 — 예전엔 흔적이 없어
            # 처방이 며칠째 안 붙고 있어도 알 방법이 없었다.
            print(f"  ⚠️ [NPI] 처방 생성 실패 — 경보는 그대로 발송: "
                  f"{a.get('label') or a.get('disease')} / {type(e).__name__}: {str(e)[:120]}",
                  flush=True)
            a = {**a, "npi_summary": None, "npi_unavailable_reason": f"{type(e).__name__}: {str(e)[:120]}"}
        out.append(a)
    return out

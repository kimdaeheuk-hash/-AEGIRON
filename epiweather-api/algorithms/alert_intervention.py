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


DISCLAIMER = ("표준 SEIR 모델 시나리오 — R0·CFR·개입효과는 예시 상수다. 실제 병원체·"
              "지역 데이터로 캘리브레이션 전엔 절대값이 아닌 '방향성 참고'로만 사용. "
              "‘구할 생명’은 모델 가정 하 추정이며 실측·보장이 아니다.")


def intervention_brief(disease: str | None, country: str | None,
                       tier: str, score: float, threat: str | None = None) -> dict:
    """경보 → 무대응/mild/strong 반사실 브리핑. threat 미지정이면 질병에서 추정."""
    if threat in THREAT:
        threat_basis = f"명시된 위협 시나리오 사용({threat})."
    else:
        threat, threat_basis = assume_threat(disease, tier)

    mild = run_defense(dict(PRESETS["mild"]), threat)
    strong = run_defense(dict(PRESETS["strong"]), threat)
    no_action = strong["baseline_no_intervention"]   # PRESETS["none"] 결과

    # 권장: 전파를 통제(rt<1)하는 최소 개입. mild로 되면 mild, 아니면 strong.
    recommended = "mild" if mild["transmission_controlled"] else "strong"
    rec_view = _scenario_view(mild if recommended == "mild" else strong)

    headline = (
        f"무대응 시 사망 {no_action['total_deaths']:,}명·병상초과 "
        f"{no_action['hosp_overflow_days']}일 → 권장개입({'중' if recommended == 'mild' else '강'})으로 "
        f"사망 {rec_view['total_deaths']:,}명(구할 생명 {rec_view['saved_lives']:,}명, "
        f"병상초과 {rec_view['hosp_overflow_days']}일). 모델 추정."
    )
    return {
        "disease": disease,
        "country": country,
        "alert_tier": tier,
        "alert_score": score,
        "assumed_threat": threat,
        "threat_basis": threat_basis,
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
        "disclaimer": DISCLAIMER,
        "is_modeled_scenario": True,
    }


def summary_line(brief: dict) -> str:
    """텔레그램/UI용 한 줄 요약."""
    return f"🧭 개입 브리핑: {brief['headline']}"


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
        except Exception:
            pass
        out.append(a)
    return out

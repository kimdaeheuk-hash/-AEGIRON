"""부정적 공간 감시 — 인수인계서 Part5 ⑤.

신호가 늘어나는 것만 위험한 게 아니다. 평소 활발하던 보고 채널이 갑자기
조용해지면 그 자체가 경보 대상 — 실제로 보고 체계가 무너졌을 수 있다.

  실제 사례:
  2014년 기니 에볼라 — 보건부 보고가 갑자기 감소
  → WHO가 "조용하다"고 판단 → 실제론 의료시스템 붕괴
  → 몇 주 후 폭발적 확산

판정 기준은 인수인계서 원문 그대로: 오늘 값이 과거 평균의 50% 미만이면 경보.
gai.py의 이상도 계산은 증가만 보므로(z<0은 0점), 이 모듈이 감소 쪽을 전담한다.
"""
from __future__ import annotations
import statistics

from .signal_metrics import LAYERS, MIN_HISTORY, load_records

DROP_RATIO = 0.5

# SNS 언급수(social_*)·AI 긴급도 점수(groq_pulse_urgency) 같은 지표는 원래
# 평균이 시간당 0~2건 수준으로 작아서, "0건"이 뜨는 게 극히 정상적인
# 상태인데도 50% 급감 규칙을 그대로 적용하면 거의 항상 오탐이 뜬다
# (2026-07-19, social_cholera·social_mpox·groq_pulse_urgency 확인).
# 평균이 이 값 미만인 지표는 비율 기반 판정이 통계적으로 무의미하므로
# 부정적 공간 스캔에서 제외한다.
MIN_MEANINGFUL_AVG = 2.0

# OpenSky는 익명/제한 쿼터 탓에 대부분의 시도가 None(수집 실패)으로 끝나고
# 어쩌다 성공한 값도 표본이 1~2건뿐이라 신뢰할 수 없다. None은 이미
# cleaned 단계에서 제거되지만, 그 결과 "latest"가 우연히 성공한 희소
# 표본(예: 0)이 되어 실제 감소가 아닌데도 50% 급감으로 오판하는 사례가
# 있었음(2026-07-19). OpenSky 연결 문제가 해결되기 전까지 이 지표는
# 부정적 공간 스캔에서 제외한다.
UNRELIABLE_METRICS = {"mobility_total_flights"}

# 뎅기열(infodengue_casos_total)은 브라질 여름(12~4월)에 집중되는 계절성
# 질병이라, 겨울철(지금, 7월) 실제 값을 계절 구분 없는 다년 평균과 비교하면
# 매년 저계절마다 "50% 급감"으로 오판한다(2026-07-19 확인: 평균 2871건/주 vs
# 현재 199건/주 — 실제 계절적 감소이지 보고 체계 붕괴가 아님). 계절성을
# 반영한 판정으로 바꾸기 전까지는 부정적 공간 스캔에서 제외한다.
SEASONAL_METRICS = {"infodengue_casos_total"}

# ★ 네이버 검색 비율은 '보고량'이 아니다 ★ (2026-09-22, 거짓 경보 ②)
#
# 09-22 00:01, 세 축이 **동시에** 무너져 critical + high 가 캡틴 폰으로 나갔다:
#
#     09-21 내내   독감=100       에볼라=5.23115  코로나=56.3341  ← 소수점 5자리까지 고정
#     09-22 00:00  독감=16.40322  에볼라=0.46997  코로나=7.7593   ← 셋이 한꺼번에
#
# 세 축은 **각각 다른 요청**이다(#34 에서 정규화 오염 때문에 일부러 나눴다). 다른
# 요청 셋이 같은 시각에 같은 배율로 무너지는 건 검색이 준 게 아니라 **새 날짜가
# 창에 들어오며 재척도된 것**이다. 네이버는 요청 창 안의 최댓값을 100 으로 놓으므로
# 값의 절대 크기에 의미가 없고, 우리가 시간당 샘플링하는 동안 원천은 하루 한 번만
# 갱신된다 — 그 경계에서 값이 기계적으로 갈아엎힌다.
#
# 이 모듈의 전제는 *"평소 활발하던 보고 채널이 조용해지면 보고 체계가 무너진 것"*
# 이다. 검색 관심도에는 그 전제가 성립하지 않는다 — 사람들이 덜 검색한 것은
# 기관이 보고를 멈춘 것이 아니다. **문턱을 조이는 문제가 아니라 대상이 아닌 것이다.**
#
# 증가 쪽은 그대로 둔다. 검색 급증은 신고보다 앞서는 실제 조기신호이고(이 축을
# 넣은 이유 자체가 그것이다), #37 의 '서로 다른 값 3개' 문턱이 거기서 재척도를 막는다.
RESCALED_METRICS = {"naver_flu_ratio", "naver_ebola_ratio", "naver_covid_ratio"}

# 부정적 공간 스캔에서 빼는 지표 전체. 이유가 서로 달라 집합을 따로 두고, 스캔은
# 이 하나만 본다 — 새 제외 사유가 생겨도 스캔 쪽 조건을 안 고치게 한다.
EXCLUDED_METRICS = UNRELIABLE_METRICS | SEASONAL_METRICS | RESCALED_METRICS


def check_negative_space(latest: float | None, history_avg: float | None) -> dict:
    """단건 판정 — 인수인계서 원문 함수와 동일한 기준."""
    if latest is None or history_avg is None or history_avg <= 0:
        return {"alert": False, "message": "판정 불가 (과거 기준선 없음)"}
    if history_avg < MIN_MEANINGFUL_AVG:
        return {"alert": False, "message": "판정 불가 (평균값이 너무 작아 비율 판정 무의미)"}
    if latest < history_avg * DROP_RATIO:
        return {"alert": True, "message": "⚠️ 신호 50% 감소 — 보고 체계 붕괴 가능성"}
    return {"alert": False, "message": "정상"}


def scan_negative_space() -> dict:
    """모든 신호원을 스캔해 보고량이 급감한 곳을 찾는다."""
    records = load_records()
    alerts = []
    checked = 0

    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, _trust_category in cfg["metrics"]:
            if metric_id in EXCLUDED_METRICS:
                continue
            series = [extractor(r) for r in records if r.get("type") == rtype]
            cleaned = [v for v in series if v is not None]
            if len(cleaned) < MIN_HISTORY + 1:
                continue
            checked += 1
            *history, latest = cleaned
            history_avg = statistics.mean(history)
            verdict = check_negative_space(latest, history_avg)
            if verdict["alert"]:
                alerts.append({
                    "layer": layer_key,
                    "label": cfg["label"],
                    "metric": metric_id,
                    "latest": latest,
                    "history_avg": round(history_avg, 2),
                    "drop_ratio": round(latest / history_avg, 2) if history_avg else None,
                    "message": verdict["message"],
                })

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "metrics_checked": checked,
    }

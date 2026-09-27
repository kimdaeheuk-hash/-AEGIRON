"""부정적 공간 감시 — 인수인계서 Part5 ⑤.

신호가 늘어나는 것만 위험한 게 아니다. 평소 활발하던 보고 채널이 갑자기
조용해지면 그 자체가 경보 대상 — 실제로 보고 체계가 무너졌을 수 있다.

  실제 사례:
  2014년 기니 에볼라 — 보건부 보고가 갑자기 감소
  → WHO가 "조용하다"고 판단 → 실제론 의료시스템 붕괴
  → 몇 주 후 폭발적 확산

판정 기준은 인수인계서 원문 그대로: 오늘 값이 과거 평균의 50% 미만이면 경보.
gai.py의 이상도 계산은 증가만 보므로(z<0은 0점), 이 모듈이 감소 쪽을 전담한다.

## ★ 왜 허용목록으로 바뀌었나 ★ (2026-09-27, 소킹 판정)

런칭 전 소킹 1주일(09-20~09-27)에서 **이 층이 거짓 critical 을 네 번 냈다.**
네 번 다 캡틴 폰까지 갔고, 네 번 다 같은 모양이었다:

    kdca_weekly_total    새 역학주간 집계가 아직 안 올라온 0
    naver_*_ratio x3     날짜 창이 밀려 기계적으로 재척도
    supply_alert_count   위 재척도의 파생(비율 30 이상 품목 수)
    social_mpox          평소가 시간당 2.6건이라 0이 정상

그때마다 제외 목록을 하나 붙였고 네 개가 됐다(UNRELIABLE·SEASONAL·RESCALED·
MIN_MEANINGFUL_AVG). 그리고 **네 번째가 증거다** — `social_mpox` 의 과거 평균이
2.59 인데 `MIN_MEANINGFUL_AVG` 가 2.0 이다. 주석에 `social_*` 이 이름으로 적혀
있는데도 통과했다. 문턱이 잘못 잡힌 게 아니라 **문턱으로는 못 막는 문제**다.

원인은 전제에 있다. 이 층의 추론은 *"평소 활발하던 보고 채널이 조용해지면 보고
체계가 무너진 것"* 이고, 그게 성립하려면 지표가 **보고 채널의 보고량**이어야
한다. 검색 관심도·SNS 언급수·우리가 만든 파생 카운트는 그게 아니다. 사람들이
덜 검색한 것은 기관이 보고를 멈춘 것이 아니다.

→ 그래서 **자격을 선언한 지표만 판정한다**(REPORTING_CHANNELS). 새 지표는
   기본적으로 이 층에서 조용하다.

★ 그리고 조용히 막지 않는다 ★ #36 이 정확히 반대 위험을 적어뒀다 — "새 지표가
표에 없다고 조용히 막히면 이번엔 반대로 진짜 신호를 죽인다". 그래서 거른 것을
사유별로 세어 돌려주고(`skipped`), 그 줄이 로그에 찍힌다(summary_line). 목록은
**관측을 근거로** 늘린다.

⚠️ 정직하게 적어둘 대가: 판정 대상이 ~30개에서 9개로 줄었다. 선언 안 된 지표에서
진짜 보고 붕괴가 나면 이 층은 못 잡는다. 지금까지 이 층의 실적이 거짓 4건·확인된
진짜 0건이라 이 교환을 택했고, 되돌릴 근거는 로그의 `미선언` 수가 준다.
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

# ★ 이 층이 판정할 자격이 있는 지표 ★ (metric_id → 무슨 채널인가)
#
# 기준 하나: **기관이나 언론 채널이 내놓는 '보고 건수'인가.**
# 지수·비율·관심도·우리 파이프라인의 파생 카운트는 해당하지 않는다 — 그것들이
# 줄어드는 건 보고 체계가 무너진 게 아니다.
#
# 여기 없는 지표는 이 층에서 판정하지 않는다. **지수에는 그대로 반영된다** —
# 막는 것은 '감소를 보고 붕괴로 읽는 판정'뿐이고, 측정은 건드리지 않는다(#36).
REPORTING_CHANNELS: dict[str, str] = {
    "kdca_weekly_total":      "질병관리청 법정감염병 주간 신고 건수",
    "who_afro_items":         "WHO 아프리카 지역 발병 공고 건수",
    "who_paho_items":         "WHO 미주 지역(PAHO) 발병 공고 건수",
    "hk_chp_total":           "홍콩 CHP 감염병 보고 건수",
    "japan_idwr_total":       "일본 IDWR 주간 감염병 보고 건수",
    "infodengue_casos_total": "브라질 InfoDengue 뎅기 보고 건수",
    "local_news_kw_hits":     "현지어 뉴스 179개 피드 키워드 히트(2014 기니 사례의 현대판)",
    "wahis_outbreaks_30d":    "WOAH 동물 발병 보고 건수(30일)",
    "wahis_watch_hits":       "WOAH 관심종 발병 보고 건수",
}

# 왜 안 넣었나 — 다음 사람이 되돌리려 할 때 읽을 자리다.
#
#   naver_*_ratio · social_* · wiki_* · pubmed_* · supply_* · mobility_* ·
#   groq_pulse_urgency · medrxiv_* · polymarket_*
#       관심도·언급수·가격이다. 줄어드는 게 '보고 중단'이 아니다.
#   kdca_disease_spike_max · cdc_nwss_concentration · genomic_new_clades_*
#       지수·농도·증가 카운트다. 감소가 오히려 좋은 소식인 자리도 있다.
#   local_news_llm_relevant · supply_alert_count
#       우리 파이프라인이 만든 파생값이다. 우리 분류기가 조용해진 것을 세상이
#       조용해진 것으로 읽으면 #36 과 같은 고장이다.
#   cidrap_* · cdc_eid_items
#       언론·학술 기사 수다. 한 주 기사가 없는 건 흔한 일이다.
#   africa_cdc_confirmed · africa_cdc_deaths
#       기관 보고 수라 후보는 되는데, 누적값인지 주간값인지 확인하지 않았다.
#       안 본 것을 근거로 넣지 않는다.

SKIP_UNDECLARED = "미선언"
SKIP_SEASONAL = "계절성"
SKIP_UNRELIABLE = "표본불안정"
SKIP_RESCALED = "재척도"
SKIP_SHORT_HISTORY = "관측부족"


def eligibility(metric_id: str) -> tuple[bool, str]:
    """이 지표를 부정적 공간으로 판정할 수 있는가. (가능?, 사유).

    ★ 기존 제외 집합을 안 지웠다 ★ 허용목록이 이미 그것들을 덮지만, 그 셋은
    **왜 뺐는지**를 들고 있다(2026-07-19 오탐 3건, 09-22 재척도). 사유를 지우면
    다음 사람이 목록을 늘릴 때 같은 함정을 다시 밟는다. 그래서 더 구체적인
    사유를 먼저 돌려준다.
    """
    if metric_id in UNRELIABLE_METRICS:
        return False, SKIP_UNRELIABLE
    if metric_id in SEASONAL_METRICS:
        return False, SKIP_SEASONAL
    if metric_id in RESCALED_METRICS:
        return False, SKIP_RESCALED
    if metric_id not in REPORTING_CHANNELS:
        return False, SKIP_UNDECLARED
    return True, "판정"


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
    skipped: dict[str, int] = {}

    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, _trust_category in cfg["metrics"]:
            ok, reason = eligibility(metric_id)
            if not ok:
                skipped[reason] = skipped.get(reason, 0) + 1
                continue
            series = [extractor(r) for r in records if r.get("type") == rtype]
            cleaned = [v for v in series if v is not None]
            if len(cleaned) < MIN_HISTORY + 1:
                skipped[SKIP_SHORT_HISTORY] = skipped.get(SKIP_SHORT_HISTORY, 0) + 1
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
        "skipped": skipped,
    }


def summary_line(result: dict) -> str:
    """로그 한 줄. 문자열은 시험 가능한 자리에 둔다(alerts.summary_line 과 같은 이유).
    **무엇이 감시 밖에 있는지가 이 줄에 남아야** 목록을 근거로 늘릴 수 있다."""
    parts = [f"판정 {result.get('metrics_checked', 0)}개 · 급감 {result.get('alert_count', 0)}건"]
    skipped = result.get("skipped") or {}
    if skipped:
        parts.append("제외 " + " · ".join(f"{k} {v}" for k, v in sorted(skipped.items())))
    return " / ".join(parts)

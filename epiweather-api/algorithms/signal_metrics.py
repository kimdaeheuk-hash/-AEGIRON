"""collector.py가 쌓은 signals_log.jsonl에서 신호원별 시계열을 뽑아내는 공통 정의.

gai.py(①GAI 점수)와 negative_space.py(⑤부정적 공간 감시)가 같은 신호원
목록·계층 배정을 공유해야 해서 분리함 — 신호원이 늘어나도 한 곳만 고치면 됨.

층 배정 근거는 gai.py 모듈 docstring 참고.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = DATA_DIR / "signals_log.jsonl"

MIN_HISTORY = 3  # 통계 계산에 필요한 최소 과거 관측치 수

# ── 표본이 아니라 '서로 다른 값'을 센다 ────────────────────────────
#
# ★ 실측 사고 (2026-09-20 01:02) ★
# naver_covid_ratio 를 09-19 03:26 에 붙였다. 도입 PR 에 이렇게 적었다 —
# "신규 지표는 관측 4개 미만이면 판정을 보류하므로 초기 지수 왜곡은 없다".
# **그 보호가 작동하지 않았다.** 22시간 뒤 이 축이 critical 경보를 냈다.
#
#     과거 = 44.89879 × 21개   (도입 후 매시간 같은 값)
#     최신 = 50.87138
#     → pstdev 1.24 → z ≈ 4.6 → 상한 3 → raw 100 → trusted 90 = critical
#
# MIN_HISTORY=3 은 **'한 주기에 한 관측'** 을 전제로 쓴 값이다. 그런데 네이버는
# 주 단위로 값이 바뀌는데 수집은 시간마다 한다 — 같은 주 값이 168번 복제된다.
# 그래서 "과거 관측 4개"가 실제로는 **"과거 관측 1개를 4번 본 것"** 이었다.
# 표본을 세는 것과 관측을 세는 것이 같다는 전제가 수집 주기 때문에 깨진 것이고,
# 깨진 자리에서 z-score 는 조용히 무의미해진다(분모가 '값이 얼마나 변하는가'가
# 아니라 '값이 언제 바뀌었나'를 재게 된다).
#
# 서로 다른 값이 이만큼 쌓이기 전에는 판정하지 않는다. 2개 값으로 낸 "3σ"는
# 숫자이지 근거가 아니다 — 그걸 90점으로 내보내는 건 이 리포가 반복해서
# 고쳐온 '상태 필드가 관측보다 많이 주장하는' 바로 그 짓이다.
#
# ★ 대가를 분명히 적는다 ★ 주 단위 지표는 서로 다른 값 3개가 모이는 데
# 3주가 걸린다. 조기경보에서 3주는 긴 시간이다. 그래도 '모르는 것을 모른다고
# 하는 쪽'을 택했다(캡틴 결정, 2026-09-20). 이걸 줄이려면 수집 주기를 낮추는
# 게 아니라 **원천이 실제로 갱신되는 주기에 맞춰 관측을 세는 것**이 답이다.
MIN_DISTINCT_HISTORY = 3


# ── 원천보다 자주 다시 기록되는 지표 — 기준선은 '관측 회차'로 센다 (2026-10-19, ④) ──
#
# ★ 운영 관측 ★ 10-19 하수 농도 경보의 '평소 값'이 10:01 137,336 → 12:03 141,075 로 매시간
# 올랐다. 주간 값이 매시간 다시 기록돼 기준선 평균이 그 값 쪽으로 끌려간 것이다(시간당 약 650).
# 같은 이유로 z-score 도 새 주 값이 들어온 순간이 가장 높고, 값은 그대로인데 그 주 안에서
# 시간마다 저절로 낮아진다 — 기준선이 '평소'가 아니라 '이번 주에 몇 시간 지났나'를 잰다.
#
# 이 지표들은 연속으로 같은 값을 **한 관측으로 접는다**(collapse_repeats). 점수·기준선·직전
# 값이 모두 '주(또는 일) 단위 관측'의 통계가 된다. 값이 실제로 그대로인 주가 이어지면 그것도
# 하나로 접힌다 — 대가: 과거 표본이 한 개 줄 수 있다(없는 값을 만들지는 않는다).
# 늘릴 때는 원천의 갱신 주기를 먼저 확인한다(RSS 항목 수처럼 매시 바뀔 수 있는 값은 넣지 않는다).
SLOW_CADENCE_METRICS: frozenset[str] = frozenset({
    "kdca_weekly_total", "kdca_disease_spike_max",     # 질병청 주간 신고
    "japan_idwr_total",                                # 일본 감염증 주보(주간)
    "infodengue_casos_total",                          # 브라질 InfoDengue(주간)
    "cdc_nwss_concentration",                          # 미국 하수 감시(주간 창)
    "naver_flu_ratio", "naver_ebola_ratio", "naver_covid_ratio",   # 네이버 데이터랩(주 단위로 바뀜)
    "wiki_ebola_daily",                                # 위키 일일 조회수(하루 한 번 바뀜)
})


def collapse_repeats(series: list) -> list:
    """None 을 빼고 연속으로 같은 값을 하나로 접는다. [1,1,None,1,2,2,1] → [1,2,1]."""
    out: list = []
    for v in series:
        if v is None:
            continue
        if not out or out[-1] != v:
            out.append(v)
    return out


def has_enough_distinct_history(history) -> bool:
    """z-score 를 낼 만큼 과거가 '변해왔는가'. 표본 수는 MIN_HISTORY 가 본다.

    두 문턱이 따로 있는 이유: 표본이 적은 것(아직 안 쌓임)과 표본은 많은데
    전부 같은 값인 것(수집 주기가 원천보다 빠름)은 다른 상태다. 둘 다 판정을
    막지만, 로그·코드에서 어느 쪽인지 구분할 수 있어야 한다.
    """
    return len(set(history)) >= MIN_DISTINCT_HISTORY


# ── 경보로 올리기 전에 요구하는 최소 절대값 ────────────────────────
#
# ★ 실측 사고 (2026-09-19 05:47) ★
# 아이기론이 처음으로 사람에게 보낸 경보가 이것이었다:
#
#     🟠 비공식신호 · genomic_new_clades_covid — 85.0점
#
# 그 85점을 만든 관측값은 **신규 계통 1건**이었다(로그: 우세계통 25C (XFG)
# (50%, n=559) 🆕신규계통1건). 85.0 ÷ 0.85(academic 신뢰도) = raw 100 =
# z-score 상한이다. 평소 0 인 카운트 지표는 **1 만 나와도 최대 이상도**가 나온다.
# 과거가 거의 다 0 이면 표준편차가 작아서, 0→1 이 곧 3σ 다.
#
# 산술은 맞다. 통계적으로 1 은 정말로 이상값이다. 틀린 건 그 다음 문장이다 —
# "그러므로 사람을 깨울 일이다". 전 세계 공개 시퀀스 빌드에서 새 계통 하나가
# 보이는 건 SARS-CoV-2 에서 늘 있는 일이고, 그걸 매번 high 경보로 올리면
# 경보 피로가 쌓여 **진짜를 놓치는 경로**가 된다(alerts.py 모듈 docstring 참고).
#
# ★ 그래서 지수(GAI)는 안 건드린다 ★
# 이상도는 측정값이다. 1 이 이상값인 건 사실이고, 그 사실을 0 으로 고쳐 쓰면
# 그게 바로 이 리포가 금지하는 "상태 필드가 관측보다 적게/많게 주장하는" 짓이다.
# 문턱은 **경보 승격 자리에만** 둔다 — 측정은 그대로, 판단만 명시적으로.
# 선례: kdca_anomaly.SPIKE_MIN_COUNT = 5 (비율만 보면 2건→4건도 2배다).
#
# ★ 여기 지표를 늘릴 땐 근거가 있어야 한다 ★
# 아래 셋은 같은 함수(genomic_variants.analyze_build)가 같은 모양으로 만드는
# 0 근처 카운트라 함께 넣었다. 다른 지표를 추가하려면 "그 지표가 평소 0 이고
# 1 에 최대 이상도가 났다"는 관측을 먼저 확인해라 — 짐작으로 문턱을 씌우면
# 진짜 신호를 조용히 죽이게 된다. 그건 지금 고치는 것보다 나쁜 고장이다.
ALERT_MIN_COUNT: dict[str, float] = {
    "genomic_new_clades_covid": 2,
    "genomic_new_clades_mpox": 2,
    "genomic_new_clades_rsv": 2,
}


def meets_alert_minimum(metric_id: str, latest: float | None) -> bool:
    """이 지표를 경보 후보로 올려도 되는 관측값인가.

    문턱이 없는 지표는 언제나 True — 이 표는 '막는 목록'이지 '허용 목록'이 아니다.
    새 지표가 추가될 때 여기 없다고 조용히 막히면 안 된다.

    latest 가 None 이면 False 다. 값을 못 본 상태에서 '문턱을 넘었다'고 할 수는
    없다 — 모르는 것을 통과로 세지 않는다(이 리포의 세 갈래 원칙과 같은 방향).
    """
    minimum = ALERT_MIN_COUNT.get(metric_id)
    if minimum is None:
        return True
    return latest is not None and latest >= minimum



# ── 소표본 카운트의 유의도 문턱 (2026-10-04, 캡틴 지시 1번) ───────────────────
#
# ★ 실측 사고 (2026-10-03) ★ 캡틴 폰이 닷새 만에 세 번 울렸다. 전부 Mastodon 7일 게시자
# 수(`social_*`)였다.
#
#     콜레라  3명 ·· 3명(사흘 넘게 평평) → 5명      → critical 90.0   (11:03 전송됨)
#     뎅기열  9명 → 12명                              → high     87.6   (13:02 전송됨)
#
# 90.0 = 100 × 0.90(behavioral_api 신뢰도) — 원시 이상도가 **상한(z ≥ 3)** 에 닿았다는
# 역산이다. 게시자 +2명이 최대 이상도를 만들었다. 같은 계열의 선례가 이미 있다:
# 09-19 신규 계통 1건 → 85.0점(ALERT_MIN_COUNT), 09-24~27 social_mpox.
#
# 왜 z-score 가 이걸 못 거르나: 경험적 표준편차는 '과거가 얼마나 평평했나'를 재지, 카운트
# 자체의 불확실성을 재지 않는다. 평소 3 이던 카운트가 5 가 되는 것은 포아송 잡음만으로도
# 흔하다(√3 ≈ 1.7). 그래서 승격 자리에서만 **카운트 기준 유의도**를 한 번 더 본다:
#
#     유의도 = (관측값 − 과거 평균) / √max(과거 평균, 1)
#
# ★ 지수(GAI)는 안 건드린다 ★ 이상도는 측정값이다 — 문턱은 **사람을 깨우는 자리에서만**.
# 막은 사실과 계산된 유의도는 로그에 남긴다(조용히 거르면 진짜를 놓쳐도 모른다).
# 막지 못한 쪽(통과)도 같은 줄로 찍는다 — 실제 평균이 얼마였는지가 내일 값으로 보이게.
#
# 적용 대상: `social_*` 전부. 같은 함수(`_social_count`)가 같은 모양(7일 게시자 수)으로
# 만드는 카운트라 함께 넣었다(ALERT_MIN_COUNT 의 genomic 셋과 같은 이유). 다른 지표를
# 늘릴 땐 '평소 N 인데 작은 변화에 최대 이상도가 났다'는 관측을 먼저 확인해라.
COUNT_NOISE_PREFIXES: tuple[str, ...] = ("social_", "medrxiv_")
COUNT_MIN_SIGMA = 2.0   # 2σ — anomaly_engine.ANOMALY_Z_THRESHOLD 와 같은 관례


# ★ 2σ 문턱만으로는 부족했다 — 프로덕션 관측 (2026-10-04 13:39 UTC, #51 배포 직후) ★
#
#     🧮 social_cholera: 관측값 5 · 과거 평균 1.7306 · 2.49σ (문턱 2.0σ) → 통과
#     🧮 social_dengue : 관측값 12 · 과거 평균 5.0578 · 3.09σ (문턱 2.0σ) → 통과
#
# 둘 다 포아송 기준으로는 '유의'하다. 그런데 이 값은 Mastodon **7일 게시자 수**다 — 매시간
# 겹치는 창으로 재서 서로 독립이 아니고, 게시자 몇 명이 늘어도 critical(90점)로 폰이 울린다.
# 문턱을 3σ 로 올리면 이 두 건에 맞춘 숫자가 된다(콜레라 2.49 만 막고 뎅기 3.09 는 통과).
# 그래서 문턱이 아니라 **등급의 상한**을 건다: 사회 카운트 신호는 단독으로 high(80) 에
# 닿지 못한다. 무역 신호와 같은 원칙이다(comtrade_signals: 상한 79 — "다른 층과 겹칠 때
# 비로소 등급이 올라가야 정직하다"). 지수는 그대로 두고 **경보 점수만** 깎으며, 깎은 사실은
# 로그와 근거에 남는다. 진짜 확산이면 다른 층(공식·뉴스)이 같이 올라 종합(gai:overall)이 말한다.
COUNT_NOISE_ALERT_CAP = 79.0


# 관측값이 **무엇의 값인지**. 경보 본문에 `관측값 12` 만 나가면 환자 12명으로 읽힌다 — 실제로는
# Mastodon 에서 최근 7일에 해당 해시태그로 글을 쓴 서로 다른 게시자 수다(collector 로그의
# `Mastodon #dengue(뎅기열): 최근7일 12명(원문 14건)`). 단위를 모르는 지표는 안 적는다(지어내지 않는다).
METRIC_UNITS: dict[str, str] = {
    "social_": "Mastodon 7일 게시자 수",
    # 환자 수가 아니라 논문(프리프린트) 편수다 — `관측값 6` 만 나가면 6명으로 읽힌다(2026-10-16).
    "medrxiv_": "medRxiv 감염병 프리프린트 편수",
}

# 점수를 깎았을 때 근거에 붙이는 이유 — 지표 계열마다 '왜 단독으로는 high 에 못 닿는가'가 다르다.
# 한 문장을 모두에게 쓰면 틀린 이유가 나간다(게시자 수의 '7일 겹치는 창'은 프리프린트와 무관하다).
COUNT_NOISE_REASONS: dict[str, str] = {
    "social_": "단독 사회 신호 — 게시자 수는 7일 겹치는 창이라 다른 층과 겹칠 때 등급이 올라감",
    "medrxiv_": "프리프린트 편수는 게재 주기·휴일에 따라 출렁이고 선행 효과가 측정된 적 없음 — "
                "다른 층과 겹칠 때 등급이 올라감",
}


def count_noise_reason(metric_id: str) -> str:
    for prefix, reason in COUNT_NOISE_REASONS.items():
        if metric_id.startswith(prefix):
            return reason
    return "단독 카운트 신호"


def approx_baseline(value: float) -> str:
    """평소 값을 사람이 읽는 만큼만 적는다 — `5.0612` 는 카운트 평균에 과한 정밀도다(`약 5.1`).
    크면 정수로(`약 64,253`). 정밀도를 줄이는 것이지 값을 바꾸는 게 아니다(로그에는 원값이 남는다)."""
    return f"약 {value:,.0f}" if abs(value) >= 100 else f"약 {value:,.1f}"


def metric_unit(metric_id: str) -> str | None:
    for prefix, unit in METRIC_UNITS.items():
        if metric_id.startswith(prefix):
            return unit
    return None


# ── 한 주 사이 비현실적 점프의 경보 상한 (2026-10-17, 소킹 일지 10-16) ────────────────
#
# ★ 실측 사고 (2026-10-16 16:01 UTC) ★ 폰에 critical 이 나갔다:
#
#     환경신호 · cdc_nwss_concentration 95.0점(관측값 1,680,229.8 · 평소 약 87,690)
#
# 수집 로그: 직전 윈도 `2026-09-30~2026-10-06 757개 · 평균 63,488.7` → 새 윈도 `2026-10-07~2026-10-13
# 656개 · 평균 1,680,229.8` — 26.5배, 그런데 행은 101개 **줄었다**. 이 값은 원시 표본 행의
# `pcr_target_avg_conc` **단순 평균**(이상치에 지배되는 통계)이고, 갓 닫힌 주라 부분 채움일 수 있다.
# 하수 농도의 주간 평균이 26배 뛰는 것은 역학적으로 흔치 않아 측정 구성 변화일 가능성이 크지만,
# **이 샌드박스는 data.cdc.gov 에 못 나가 분포를 못 봤다 — 인공물은 가설이다.**
#
# ★ 그래서 지우지도, 폰으로도 안 보낸다 ★ 이상도(지수)는 측정값이라 그대로 두고, **경보 점수만**
# 79(medium) 로 제한한다 — 무역·사회 카운트와 같은 원칙("다른 층과 겹칠 때 비로소 등급이 올라가야
# 정직하다"). 진짜 급증이면 공식·뉴스 층이 같이 올라 종합(gai:overall)이 말한다. 화면에는 남고, 왜 깎았는지
# 근거에 적힌다. 문턱 10배는 관측 한 건(26.5배)에서 나온 판단 상수다 — 되돌리려면 표에서 한 줄 뺀다.
IMPLAUSIBLE_JUMP_RATIO: dict[str, float] = {"cdc_nwss_concentration": 10.0}
IMPLAUSIBLE_JUMP_CAP = 79.0


def implausible_jump(metric_id: str, latest: float | None, baseline_mean: float | None,
                     previous: float | None = None, baseline_median: float | None = None) -> float | None:
    """관측값이 평소(또는 직전의 다른 값)의 몇 배인가 — 대상 지표에서 문턱을 넘었을 때만 배수를 돌려준다. 아니면 None.

    비교점은 둘이고 **더 큰 배수**를 쓴다(어느 쪽으로 봐도 비현실적이면 비현실적이다):
    - `baseline_mean`: 과거 평균. 값이 오래 높게 머무는 새 수준(단위 변경 등)에서도 한동안 문턱 위에 남는다.
    - `previous`: 최신값과 다른 가장 최근 값(지난 창). 같은 주간 값을 매시간 다시 기록해 평균이 끌려 올라가도
      흔들리지 않는다 — 평균만 보면 같은 주 안에서 배수가 저절로 줄어 상한이 풀리고 폰이 다시 울린다(10-18 자기검토).
    - `baseline_median`: 과거 중앙값. 이상치가 두 주 연달아 오면 앞의 둘이 다 오염된다(10-23: 평균 152,470 ·
      직전 1,680,230 → 1,404,069 가 9.2배로 상한 풀림). 중앙값은 그 정도로는 안 움직인다.

    관측값을 못 봤거나 쓸 비교점(양수)이 없으면 None — 이 함수는 점수를 *깎는* 쪽이라 모를 때는 깎지 않는다."""
    limit = IMPLAUSIBLE_JUMP_RATIO.get(metric_id)
    if limit is None or latest is None:
        return None
    refs = [r for r in (baseline_mean, previous, baseline_median) if r is not None and r > 0]
    if not refs:
        return None
    ratio = latest / min(refs)
    return ratio if ratio > limit else None


def cap_count_noise_score(metric_id: str, score: float) -> float:
    """대상 카운트 지표의 **경보 점수**를 상한으로 깎는다. 대상이 아니면 그대로."""
    if is_count_noise_metric(metric_id):
        return min(score, COUNT_NOISE_ALERT_CAP)
    return score


def is_count_noise_metric(metric_id: str) -> bool:
    return metric_id.startswith(COUNT_NOISE_PREFIXES)


def count_significance(latest: float | None, baseline_mean: float | None) -> float | None:
    """(관측값 − 과거 평균) / √max(과거 평균, 1). 값을 못 봤으면 None.

    분모의 하한 1 은 평균이 0 근처일 때 0 나누기·과민반응을 막는다(평균 0.1 에서 관측값 1
    이 9σ 가 되는 것을 피한다). 음수(평소보다 낮음)도 그대로 음수로 돌려준다 — 하향은
    승격 대상이 아니다.
    """
    if latest is None or baseline_mean is None:
        return None
    return (latest - baseline_mean) / (max(baseline_mean, 1.0) ** 0.5)


def meets_count_significance(metric_id: str, latest: float | None,
                             baseline_mean: float | None) -> bool:
    """이 카운트 지표의 변화가 포아송 잡음 이상인가. 대상 지표가 아니면 언제나 True.

    `meets_alert_minimum` 과 같은 방향 — **막는 목록**이지 허용 목록이 아니다. 단, 대상
    지표인데 관측값·평균을 못 봤으면 False 다(모르는 것을 통과로 세지 않는다).
    """
    if not is_count_noise_metric(metric_id):
        return True
    sig = count_significance(latest, baseline_mean)
    return sig is not None and sig >= COUNT_MIN_SIGMA


def sum_if_complete(values) -> float | None:
    """조각을 다 받았을 때만 합계를 낸다. 하나라도 못 받았으면 None.

    ★ 조각이 빠진 합계는 낮은 값이 아니라 **다른 값**이다 ★

    여러 곳에서 가져와 더하는 지표들이 전부 이렇게 돼 있었다 —

        vals = [v for v in totals.values() if v is not None]
        return sum(vals) if vals else None

    전부 실패해야 None 이고, **일부만 실패하면 조용히 낮은 숫자**가 된다.
    그 낮은 숫자는 negative_space 로 가서 "보고 체계 붕괴 가능성"이 된다.
    2026-09-19 에 LocalNews 가 정확히 그 경로로 critical 경보를 냈다 — 무너진
    건 세상의 보고가 아니라 우리 수집기였다.

    일본 IDWR 이 제일 위험했다. 11개 질병을 합치는데 독감 하나가 12,299건으로
    전체의 90% 가 넘는다. 그 한 줄만 파싱에 실패해도 합계가 700 대로 내려앉고
    severity 94.6 → critical 이 된다. 그리고 fetch_japan_idwr 의 docstring 이
    이미 적어뒀듯 **유행이 커질수록 파싱이 깨지는 방향**이라, 진짜 유행이 오는
    순간 "보고가 끊겼다"는 거짓 경보가 나간다.

    수집은 그대로 둔다("한 도시 실패해도 나머지는 계속 수집"은 의도된 설계다).
    바꾸는 건 **판정**뿐이다 — 못 본 조각이 있으면 판정하지 않는다.
    """
    vals = list(values)
    if not vals or any(v is None for v in vals):
        return None
    return sum(vals)


def _kdca_latest_total(rec: dict) -> float | None:
    # 이제 kdca_weekly엔 전 법정감염병이 들어온다. 총합에 상재성 질병(수두·결핵 등)을
    # 다 넣으면 신종 신호가 파묻히므로, 집계는 '위험군만' 합산한다(kdca_anomaly).
    from .kdca_anomaly import notable_latest_total
    # 기록 시각 기준으로 '새 주가 덜 찼나'를 본다(옛 기록을 지금 시각으로 재면 틀린다). 시각이 없으면 보지 않는다.
    as_of = None
    ts = rec.get("timestamp")
    if ts:
        try:
            as_of = dt.datetime.fromisoformat(str(ts)).date()
        except ValueError:
            as_of = None
    return notable_latest_total(rec.get("kdca_weekly"), as_of=as_of)


def _kdca_max_disease_spike(rec: dict) -> float | None:
    # 질병별 개별 급증 중 가장 강한 것. 전체 총합이 평온해도 단일 질병 급증(레지오넬라
    # 등)이 여기서 신호로 뜬다 — '전부 감시 + 개별 판단'의 핵심 지표.
    from .kdca_anomaly import max_spike_signal
    return max_spike_signal(rec.get("kdca_disease_spikes"))


def _japan_idwr_total(rec: dict) -> float | None:
    # 11개 질병 중 독감 하나가 전체의 90% 가 넘는다 — 그 한 줄이 빠진 합계는
    # '줄어든 값'이 아니라 '다른 값'이다. sum_if_complete docstring 참고.
    j = rec.get("japan_idwr")
    totals = (j or {}).get("national_totals") or {}
    return sum_if_complete(totals.values())


def _hk_chp_total(rec: dict) -> float | None:
    # 피드 2개짜리라 하나만 죽어도 합계가 절반이 된다 — 그건 홍콩이 보고를
    # 줄인 게 아니라 우리가 절반을 못 읽은 것이다.
    hk = rec.get("hk_chp")
    return sum_if_complete((hk or {}).values())


def _infodengue_total(rec: dict) -> float | None:
    # 도시 하나가 실패하면 그 항목이 None 으로 온다(fetch_infodengue). 예전엔
    # falsy 라 그냥 건너뛰어서, 09-20 01:00 '상파울루=실패' 같은 날 합계가 조용히
    # 내려앉았다. 지금은 계절성 제외 목록에 있어 경보로는 안 갔지만, 그 보호가
    # 사라지면 바로 같은 사고가 난다 — 지표 쪽에서 막는다.
    inf = rec.get("infodengue")
    return sum_if_complete(
        (city.get("casos") if city else None) for city in (inf or {}).values())


def _cidrap_field(slug: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("cidrap") or {}).get(slug)
    return fn


def _cdc_nwss_conc(rec: dict) -> float | None:
    return (rec.get("cdc_nwss") or {}).get("mean_concentration")


def _polymarket_prob(slug: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("polymarket") or {}).get(slug, {}).get("yes_probability")
    return fn


def _genomic_field(slug: str, field: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("genomic_variants") or {}).get(slug, {}).get(field)
    return fn


_GROQ_URGENCY_SCORE = {"low": 1, "medium": 2, "high": 3}


def _groq_pulse_score(rec: dict) -> float | None:
    g = rec.get("groq_pulse")
    if not g:
        return None
    if not g.get("has_new_signal"):
        return 0
    return _GROQ_URGENCY_SCORE.get(g.get("urgency"), 1)


def _local_news_kw_hits(rec: dict) -> float | None:
    """★ '한 곳도 못 읽음'과 '히트 0건'은 다른 사실이다 ★ (2026-09-19)

    실측 사고. 11:03 에 critical 경보가 캡틴 폰으로 나갔다. 같은 사이클 로그:

        [11:01:49] 현지어 뉴스: 0/179개 피드(고유 0묶음), 키워드 히트 0건
        [11:03:14] 📊 소스 건강: 정상 22/23 · 값없음 LocalNews

    179개 피드가 전멸했는데도 fetch_all_local_news 는 **정상 모양의 dict**를
    돌려준다 — total_kw_hits 가 0 으로. collector.py:798 은 이미 그걸 알고
    active_feeds 가 0 이면 mark_no_data 를 찍는다(그래서 소스 건강에 '값없음'이
    떴다). 그런데 **지표 추출기가 그 구분을 안 봤다.** 0 을 그대로 읽었다.

    그 0 이 negative_space 로 간다. 과거 평균 1,600건대 대비 latest=0 →
    drop_ratio 0.0 → severity (1-0)*100 = 100점 → critical. 부정적 공간 감시가
    "보고 체계가 무너졌다"고 판정한 것이다 — 무너진 건 우리 수집기인데.

    2014년 기니 에볼라를 잡으라고 만든 층이 **우리 스크레이퍼 장애**에 울렸다.
    그리고 그건 이 리포가 반복해서 고쳐온 바로 그 모양이다:

        naver_trends: "그룹 부재 ≠ 검색량 0 … '네이버가 죽었다'가
                       '아무도 안 찾는다'로 둔갑한다"
        mark_no_data: "실패로 세면 상시 degraded, 성공으로 세면 죽은 소스가
                       살아있다고 보고된다. 둘 다 거짓이다"

    한 곳도 못 읽었으면 판정하지 않는다(None). 0 은 '아무도 그 말을 안 했다'는
    관측일 때만 쓴다.
    """
    news = rec.get("local_news")
    if not news:
        return None
    if not news.get("active_feeds"):
        return None
    return news.get("total_kw_hits")


def _local_news_llm_relevant(rec: dict) -> float | None:
    """Cerebras 재분류가 켜져있을 때만 값이 나옴(꺼져있으면 None — 0과 구분)."""
    feeds = (rec.get("local_news") or {}).get("feeds") or []
    classified = [f for f in feeds if "llm_relevant_count" in f]
    if not classified:
        return None
    return sum(f["llm_relevant_count"] for f in classified)


def _social_count(tag: str):
    def fn(rec: dict) -> float | None:
        entry = (rec.get("social_signal") or {}).get(tag)
        if not entry or not entry.get("available"):
            return None
        return entry.get("count_recent")
    return fn


def _ai_anchor_field(field: str):
    def fn(rec: dict) -> float | None:
        return (rec.get("anchors") or {}).get("africa_cdc", {}).get(field)
    return fn


# (metric_id, collector.py record type, 레코드 → 값 추출 함수, 신뢰도 카테고리)
LAYERS = {
    "official": {
        "label": "공식신호", "weight": 0.15,
        "metrics": [
            ("kdca_weekly_total", "free_sources", _kdca_latest_total, "government"),
            ("kdca_disease_spike_max", "free_sources", _kdca_max_disease_spike, "government"),
            ("who_afro_items", "free_sources", lambda r: r.get("who_afro_items"), "who"),
            ("who_paho_items", "free_sources", lambda r: r.get("who_paho_items"), "who"),
            ("cdc_eid_items", "free_sources", lambda r: r.get("cdc_eid_items"), "cdc"),
            ("hk_chp_total", "free_sources", _hk_chp_total, "government"),
            ("japan_idwr_total", "free_sources", _japan_idwr_total, "government"),
            ("infodengue_casos_total", "free_sources", _infodengue_total, "academic"),
        ],
    },
    "informal": {
        "label": "비공식신호", "weight": 0.20,
        "metrics": [
            ("cidrap_ebola", "free_sources", _cidrap_field("ebola"), "academic"),
            ("cidrap_mers", "free_sources", _cidrap_field("mers"), "academic"),
            ("cidrap_cholera", "free_sources", _cidrap_field("cholera"), "academic"),
            ("africa_cdc_confirmed", "ai_sources", _ai_anchor_field("confirmed_cases"), "ai_extracted"),
            ("africa_cdc_deaths", "ai_sources", _ai_anchor_field("deaths"), "ai_extracted"),
            ("local_news_kw_hits", "free_sources", _local_news_kw_hits, "behavioral_api"),
            ("local_news_llm_relevant", "free_sources", _local_news_llm_relevant, "ai_extracted"),
            ("genomic_new_clades_covid", "free_sources", _genomic_field("ncov_open_global_6m", "new_clade_count"), "academic"),
            ("genomic_new_clades_mpox", "free_sources", _genomic_field("mpox", "new_clade_count"), "academic"),
            ("genomic_new_clades_rsv", "free_sources", _genomic_field("rsv_a_genome", "new_clade_count"), "academic"),
            ("groq_pulse_urgency", "free_sources", _groq_pulse_score, "ai_extracted"),
        ],
    },
    "behavioral": {
        "label": "행동신호", "weight": 0.25,
        "metrics": [
            ("naver_flu_ratio", "free_sources", lambda r: r.get("naver_flu_ratio"), "behavioral_api"),
            ("naver_ebola_ratio", "free_sources", lambda r: r.get("naver_ebola_ratio"), "behavioral_api"),
            # 2026-09-19 신설. 국내 코로나 축이 통째로 없어서 "국내 유행 중인가"에
            # 답할 소스가 하나도 없었다(KDCA 전수감시 API 는 표본감시 질병을 안 준다).
            # ★ 다른 네이버 축과 값을 비교하지 마라 ★ 별도 요청이라 척도가 다르다.
            # z-score 는 자기 과거와만 비교하므로 문제되지 않는다.
            ("naver_covid_ratio", "free_sources", lambda r: r.get("naver_covid_ratio"), "behavioral_api"),
            ("social_ebola", "free_sources", _social_count("ebola"), "behavioral_api"),
            ("social_mpox", "free_sources", _social_count("mpox"), "behavioral_api"),
            ("social_birdflu", "free_sources", _social_count("birdflu"), "behavioral_api"),
            ("social_h5n1", "free_sources", _social_count("h5n1"), "behavioral_api"),
            ("social_cholera", "free_sources", _social_count("cholera"), "behavioral_api"),
            ("social_measles", "free_sources", _social_count("measles"), "behavioral_api"),
            ("social_dengue", "free_sources", _social_count("dengue"), "behavioral_api"),
            ("social_marburg", "free_sources", _social_count("marburg"), "behavioral_api"),
            ("wiki_ebola_daily", "free_sources", lambda r: r.get("wiki_ebola_daily"), "behavioral_api"),
            ("pubmed_ebola_count", "free_sources", lambda r: r.get("pubmed_ebola_count"), "behavioral_api"),
            ("supply_total_ratio", "free_sources", lambda r: (r.get("supply_chain") or {}).get("total_supply_ratio"), "behavioral_api"),
            ("supply_alert_count", "free_sources", lambda r: (r.get("supply_chain") or {}).get("supply_alert_count"), "behavioral_api"),
            ("mobility_total_flights", "free_sources", lambda r: (r.get("mobility") or {}).get("mobility_total_flights"), "behavioral_api"),
            ("medrxiv_epi_papers", "free_sources", lambda r: (r.get("extra_sources") or {}).get("medrxiv", {}).get("medrxiv_epi_papers"), "academic"),
        ],
    },
    "environmental": {
        "label": "환경신호", "weight": 0.15,
        "metrics": [
            ("cdc_nwss_concentration", "free_sources", _cdc_nwss_conc, "cdc"),
        ],
    },
    "animal": {
        "label": "동물신호", "weight": 0.15,
        "metrics": [
            ("cidrap_avian_flu", "free_sources", _cidrap_field("avian_flu"), "academic"),
            ("wahis_outbreaks_30d", "free_sources", lambda r: (r.get("wahis") or {}).get("outbreaks_30d"), "government"),
            ("wahis_watch_hits", "free_sources", lambda r: (r.get("wahis") or {}).get("watch_hits"), "government"),
        ],
    },
    "unexplained": {
        "label": "설명불가", "weight": 0.10,
        "metrics": [
            ("polymarket_new_pandemic", "free_sources", _polymarket_prob("new-pandemic-in-2026"), "prediction_market"),
        ],
    },
}


def load_records() -> list[dict]:
    """
    기준선 파일(baseline_signals.jsonl) + 실시간 수집 파일(signals_log.jsonl)을
    시간순으로 합쳐서 반환. 기준선이 먼저, 실시간이 뒤에 오므로 z-score 계산 시
    역사적 컨텍스트를 확보할 수 있다.
    """
    baseline_file = DATA_DIR / "baseline_signals.jsonl"
    records = []
    for path in (baseline_file, LOG_FILE):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def iter_metric_series(records: list[dict]):
    """LAYERS에 정의된 모든 신호원을 순회하며 (layer_key, metric_id, trust_category, series)를 내놓는다."""
    for layer_key, cfg in LAYERS.items():
        for metric_id, rtype, extractor, trust_category in cfg["metrics"]:
            series = [extractor(r) for r in records if r.get("type") == rtype]
            if metric_id in SLOW_CADENCE_METRICS:
                series = collapse_repeats(series)      # gai 와 같은 관측 단위(SLOW_CADENCE_METRICS 주석)
            yield layer_key, metric_id, trust_category, series

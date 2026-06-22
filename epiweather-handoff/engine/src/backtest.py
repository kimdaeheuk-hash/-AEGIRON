"""
백테스트 하니스 (Backtest Harness)
===================================
- 여러 시즌의 다중 신호(공식 확진 / 검색어 / 하수)를 생성하거나 로드
- 선행 신호로 탐지 → 공식 onset과 비교해 리드타임 채점
- 방법(Farrington/z/EWMA)과 신호별 성능 비교 리포트 출력

핵심: '공식 확진'으로 탐지하면 onset보다 늦지만(임계 지연),
      '선행 신호'(검색어/하수)로 탐지하면 onset보다 앞선다(=리드타임 양수).
      이것이 조기경보의 가치다.
"""
from __future__ import annotations
import numpy as np
from scorer import RetrospectiveScorer, BacktestReport


# ----------------------------------------------------------------------
# 합성 시즌 생성 (정답 onset이 알려진 데이터)
# ----------------------------------------------------------------------

def make_season(name: str, seed: int, n: int = 150,
                onset: int = 100, lead_offsets=None, severity: float = 1.0):
    """
    한 시즌의 다중 신호 생성.
      - official : day=onset 부터 급증 (정답 기준)
      - search   : official보다 lead_offsets['search']일 먼저 상승
      - waste    : official보다 lead_offsets['waste']일 먼저 상승
    각 신호는 계절 베이스라인 + 추세 + 잡음 + 유행성장.
    """
    if lead_offsets is None:
        lead_offsets = {"official": 0, "search": 7, "waste": 10}
    rng = np.random.default_rng(seed)

    def build(lead, scale, base_level, noise_sd):
        s = (base_level
             + 11 * np.sin((np.arange(n) + 18) / n * np.pi * 1.5)
             + np.arange(n) * 0.05
             + rng.normal(0, noise_sd, n))
        # 유행 성장: 이 신호는 (onset - lead) 시점부터 상승
        start = onset - lead
        for i in range(n):
            e = i - start
            if e >= 0:
                s[i] += min(scale * severity * np.exp(0.17 * e),
                            scale * severity * 9.5)
        return np.maximum(0, s)

    return {
        "name": name,
        "onset": onset,
        "signals": {
            "official": build(lead_offsets["official"], 26, 45, 5),
            "search":   build(lead_offsets["search"],   30, 48, 8),
            "waste":    build(lead_offsets["waste"],     28, 38, 6),
        },
    }


def fuse_signals(season: dict, keys=("search", "waste")) -> np.ndarray:
    """선행 신호들을 표준화 후 평균하여 융합 신호 생성."""
    arrs = []
    for k in keys:
        s = season["signals"][k]
        train = s[8:72]
        m, sd = train.mean(), max(2.0, train.std())
        arrs.append((s - m) / sd)
    fused_z = np.mean(arrs, axis=0)
    # z를 양수 카운트 스케일로 환원 (탐지기가 count 가정하므로 100 기준 재구성)
    return 50 + fused_z * 12


# ----------------------------------------------------------------------
# 백테스트 실행
# ----------------------------------------------------------------------

def run_backtest(seasons, signal_choice="fused", methods=("farrington", "zscore", "ewma")):
    """
    signal_choice: 'official' | 'search' | 'waste' | 'fused'
    반환: {method: BacktestReport}
    """
    scorer = RetrospectiveScorer(train_a=8, train_b=72, consecutive=2, pre_buffer=5)
    prepared = []
    for s in seasons:
        if signal_choice == "fused":
            sig = fuse_signals(s)
        else:
            sig = s["signals"][signal_choice]
        prepared.append({"name": s["name"], "signal": sig, "onset": s["onset"]})

    return {m: scorer.backtest(prepared, m) for m in methods}


def print_report(reports: dict, title: str, unit: str = "일"):
    print(f"\n{'='*64}\n {title}\n{'='*64}")
    header = f"{'방법':<12}{'탐지율':>8}{'평균리드':>10}{'중앙리드':>10}{'헛경보':>8}"
    print(header)
    print("-" * 64)
    for method, rep in reports.items():
        ml = rep.mean_lead
        md = rep.median_lead
        ml_s = f"{ml:+.1f}{unit}" if ml is not None else "  —  "
        md_s = f"{md:+.1f}{unit}" if md is not None else "  —  "
        print(f"{method:<12}{rep.detection_rate*100:>6.0f}%{ml_s:>11}{md_s:>11}{rep.total_false_alarms:>7}")
    print("-" * 64)


def detail_table(reports: dict, method: str, unit: str = "일"):
    rep = reports[method]
    print(f"\n[{method}] 시즌별 상세")
    print(f"{'시즌':<14}{'공식onset':>10}{'탐지일':>9}{'리드타임':>10}{'헛경보':>8}")
    print("-" * 52)
    for s in rep.scores:
        det = f"day{s.detected_at}" if s.detected else "미탐지"
        lead = f"{s.lead_time_days:+d}{unit}" if s.lead_time_days is not None else " — "
        print(f"{s.season:<14}{'day'+str(s.official_onset):>10}{det:>9}{lead:>10}{s.false_alarms:>7}")

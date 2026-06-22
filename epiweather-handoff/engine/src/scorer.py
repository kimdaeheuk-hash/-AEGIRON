"""
역병예보 후향 검증 채점 모듈 (Retrospective Backtest Scorer)
==============================================================
정답(실제 유행 시작일)이 알려진 과거 데이터에서, 우리 추론 엔진이
공식 발표/실제 유행 시작보다 며칠 먼저 탐지했는지를 자동 채점한다.

핵심 지표:
  - lead_time_days : 엔진 탐지일 vs 기준일(공식/실제 onset) 차이 (양수 = 선행)
  - sensitivity    : 실제 유행을 놓치지 않았는가 (탐지율)
  - false_alarms   : 비유행기 헛경보 횟수
  - 방법 비교       : Farrington vs 단순 z vs EWMA

설계 원칙:
  - 미래 데이터 누수 금지: 각 시점 t의 판단은 t 이전 데이터만 사용
  - 학습/검증 분리: 베이스라인은 과거 참조창(reference window)에서만 학습
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ----------------------------------------------------------------------
# 1. 이상탐지기 (detectors) — 각 시점 t의 상한 임계선을 t 이전 데이터로 계산
# ----------------------------------------------------------------------

def _linreg(x: np.ndarray, y: np.ndarray):
    """단순 최소제곱 회귀. 반환 (기울기 b, 절편 a)."""
    if len(x) < 2:
        return 0.0, float(np.mean(y)) if len(y) else 0.0
    mx, my = x.mean(), y.mean()
    den = ((x - mx) ** 2).sum()
    if den == 0:
        return 0.0, my
    b = ((x - mx) * (y - my)).sum() / den
    return b, my - b * mx


def detect_farrington(series: np.ndarray, window: int = 45,
                      z: float = 2.58, min_ref: int = 10):
    """
    Farrington 계열 이상탐지 (Farrington et al. 1996 의 단순화 구현).
      - 참조창에서 로그선형 추세 적합 (quasi-Poisson 근사)
      - 추세 유의성 약식 검정 (|b| 임계)
      - Pearson 잔차로 과분산(phi) 추정
      - 2/3 거듭제곱 변환 상한선
    반환: (threshold[t], score_sigma[t])  — 미래 누수 없음 (t 이전만 사용)
    """
    n = len(series)
    thr = np.full(n, np.inf)
    sig = np.zeros(n)
    for t in range(n):
        lo = max(0, t - window)
        ref_idx = np.arange(lo, t)
        ref_val = series[lo:t]
        if len(ref_val) < min_ref:
            continue
        ly = np.log(np.maximum(1.0, ref_val))
        b, a = _linreg(ref_idx.astype(float), ly)
        use_trend = abs(b) > 0.004
        if use_trend:
            mu = np.exp(a + b * t)
        else:
            mu = np.exp(ly.mean())
        mu = max(1.0, float(mu))
        # 과분산 phi (Pearson)
        if use_trend:
            fit = np.exp(a + b * ref_idx)
        else:
            fit = np.full(len(ref_val), np.exp(ly.mean()))
        fit = np.maximum(1.0, fit)
        chi = (((ref_val - fit) ** 2) / fit).sum()
        phi = max(1.0, chi / max(1, len(ref_val) - 2))
        var = phi * mu
        # 2/3-power 상한 (Farrington upper bound)
        thr[t] = mu * (1 + (2.0 / 3.0) * z * np.sqrt(var) / mu) ** 1.5
        sig[t] = (series[t] - mu) / np.sqrt(var)
    return thr, sig


def detect_zscore(series: np.ndarray, train_a: int, train_b: int, z: float = 3.0):
    """단순 z-score: 고정 학습창의 평균/표준편차 기준."""
    train = series[train_a:train_b]
    m = float(train.mean())
    sd = max(2.0, float(train.std()))
    thr = np.full(len(series), m + z * sd)
    sig = (series - m) / sd
    return thr, sig


def detect_ewma(series: np.ndarray, train_a: int, train_b: int,
                lam: float = 0.2, z: float = 3.0):
    """EWMA 관리도: 점진적 변화에 민감."""
    train = series[train_a:train_b]
    m = float(train.mean())
    sd = max(2.0, float(train.std()))
    n = len(series)
    thr = np.zeros(n)
    sig = np.zeros(n)
    e = m
    for t in range(n):
        e = lam * series[t] + (1 - lam) * e
        sig_e = sd * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * (t + 1))))
        thr[t] = m + z * sig_e
        sig[t] = (e - m) / max(0.5, sig_e)
    return thr, sig


DETECTORS = {
    "farrington": lambda s, a, b: detect_farrington(s),
    "zscore":     lambda s, a, b: detect_zscore(s, a, b),
    "ewma":       lambda s, a, b: detect_ewma(s, a, b),
}


# ----------------------------------------------------------------------
# 2. 탐지 시점 계산
# ----------------------------------------------------------------------

def first_exceedance(series: np.ndarray, thr: np.ndarray,
                     start_from: int, consecutive: int = 1) -> int:
    """
    임계 초과가 처음 (연속 consecutive회) 발생한 인덱스. 없으면 -1.
    consecutive>1 이면 헛경보(단발성 잡음)를 줄인다.
    """
    n = len(series)
    run = 0
    for i in range(start_from, n):
        if np.isfinite(thr[i]) and series[i] > thr[i]:
            run += 1
            if run >= consecutive:
                return i - consecutive + 1
        else:
            run = 0
    return -1


# ----------------------------------------------------------------------
# 3. 채점 결과 구조
# ----------------------------------------------------------------------

@dataclass
class SeasonScore:
    season: str
    method: str
    official_onset: int            # 기준일 (공식/실제 유행 시작 인덱스)
    detected_at: Optional[int]     # 엔진 탐지 인덱스 (None = 미탐지)
    lead_time_days: Optional[int]  # 양수 = 공식보다 선행
    detected: bool
    false_alarms: int              # 유행 전 구간 헛경보 수


@dataclass
class BacktestReport:
    method: str
    scores: list = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.detected for s in self.scores) / len(self.scores)

    @property
    def mean_lead(self) -> Optional[float]:
        leads = [s.lead_time_days for s in self.scores if s.detected and s.lead_time_days is not None]
        return float(np.mean(leads)) if leads else None

    @property
    def median_lead(self) -> Optional[float]:
        leads = [s.lead_time_days for s in self.scores if s.detected and s.lead_time_days is not None]
        return float(np.median(leads)) if leads else None

    @property
    def total_false_alarms(self) -> int:
        return sum(s.false_alarms for s in self.scores)


# ----------------------------------------------------------------------
# 4. 채점기
# ----------------------------------------------------------------------

class RetrospectiveScorer:
    """
    여러 시즌의 (신호 시계열, 기준 onset)을 받아 방법별로 채점한다.

    signal_for_detection: 탐지에 쓸 신호 (예: 선행지표인 검색어/하수, 또는 공식 확진).
    onset: 정답 — 실제 유행이 시작된 인덱스 (공식 기준).
    pre_window: 헛경보를 세는 '유행 전 안정' 구간 (train_b ~ onset-buffer).
    """

    def __init__(self, train_a: int = 8, train_b: int = 72,
                 consecutive: int = 2, pre_buffer: int = 5):
        self.train_a = train_a
        self.train_b = train_b
        self.consecutive = consecutive
        self.pre_buffer = pre_buffer

    def score_season(self, season_name: str, signal: np.ndarray,
                     onset: int, method: str) -> SeasonScore:
        signal = np.asarray(signal, dtype=float)
        thr, _ = DETECTORS[method](signal, self.train_a, self.train_b)

        detected_at = first_exceedance(signal, thr, self.train_b, self.consecutive)
        detected = detected_at >= 0
        lead = (onset - detected_at) if detected else None

        # 헛경보: train_b ~ (onset - pre_buffer) 구간에서 '경보가 울린' 횟수.
        # 실제 탐지와 동일하게 연속 consecutive회 초과를 1건의 경보로 센다
        # (단발성 잡음 초과는 경보로 치지 않음).
        fa_end = max(self.train_b, onset - self.pre_buffer)
        false_alarms = 0
        run = 0
        for i in range(self.train_b, fa_end):
            if np.isfinite(thr[i]) and signal[i] > thr[i]:
                run += 1
                if run == self.consecutive:   # 경보 발생 시점에 1건 집계
                    false_alarms += 1
            else:
                run = 0

        return SeasonScore(
            season=season_name, method=method, official_onset=onset,
            detected_at=detected_at if detected else None,
            lead_time_days=lead, detected=detected, false_alarms=false_alarms,
        )

    def backtest(self, seasons: list, method: str) -> BacktestReport:
        """seasons: list of dict(name, signal, onset)."""
        rep = BacktestReport(method=method)
        for s in seasons:
            rep.scores.append(
                self.score_season(s["name"], s["signal"], s["onset"], method)
            )
        return rep

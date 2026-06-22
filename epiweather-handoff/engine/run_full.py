"""
통합 실행: 파이프라인 → 후향 검증 (End-to-End)
================================================
실행:  python3 run_full.py

1) 파이프라인으로 ILI+검색어 수집·정렬
2) 매 겨울 유행 시즌을 자동 분할하고 ILI 기준 onset 라벨링
3) 검색어 신호로 탐지 → ILI onset 대비 리드타임 채점
4) 종합 리포트
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import numpy as np
import pandas as pd
from pipeline import fetch_kdca_ili, fetch_search_trend, align
from backtest import run_backtest, print_report, detail_table


def segment_seasons(df: pd.DataFrame, target="ILI"):
    """
    주간 데이터를 'flu year'(8월 시작) 단위로 분할.
    각 시즌에서 ILI가 시즌 초 베이스라인을 유의하게 초과하는 첫 주를 onset으로 라벨.
    반환: list of dict(name, signals(dict), onset) — backtest 형식과 호환.
    """
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["flu_year"] = d["date"].apply(lambda x: x.year if x.month >= 8 else x.year - 1)

    seasons = []
    for fy, g in d.groupby("flu_year"):
        g = g.reset_index(drop=True)
        if len(g) < 30:           # 너무 짧은(잘린) 시즌 제외
            continue
        ili = g[target].to_numpy()
        search = g["SEARCH"].to_numpy()
        # onset을 탐지와 '동일한' 로직(zscore 탐지기)으로 라벨링하여
        # 민감도 비대칭을 제거 → 리드타임이 순수 신호 선행성만 반영
        from scorer import detect_zscore, first_exceedance
        thr_o, _ = detect_zscore(ili, 2, 8, z=2.58)
        onset = first_exceedance(ili, thr_o, 8, consecutive=1)
        if onset < 0:
            continue
        seasons.append({
            "name": f"{fy}-{fy+1}",
            "onset": onset,
            "signals": {"official": ili, "search": search,
                        "waste": search},   # 데모: waste 대용으로 search 재사용
        })
    return seasons


def main():
    print("=" * 64)
    print(" 통합 실행: 파이프라인 → 후향 검증")
    print("=" * 64)

    # 1) 수집·정렬
    df = align(fetch_kdca_ili(), fetch_search_trend())
    print(f" 정렬 데이터: {len(df)}주 ({df['date'].min().date()} ~ {df['date'].max().date()})")

    # 2) 시즌 분할 + onset 라벨
    seasons = segment_seasons(df)
    print(f" 분할된 겨울 시즌: {len(seasons)}개")
    for s in seasons:
        print(f"   - {s['name']}: onset = 주{s['onset']} ({len(s['signals']['official'])}주 시즌)")

    if not seasons:
        print(" 시즌이 분할되지 않음 — 데이터 기간/임계 재검토 필요")
        return

    # 3) 검색어 신호로 탐지 → ILI onset 대비 리드타임
    #    (train_b를 시즌 길이에 맞춰 동적으로: onset 직전까지 학습)
    from scorer import RetrospectiveScorer
    scorer = RetrospectiveScorer(train_a=2, train_b=8, consecutive=1, pre_buffer=2)
    methods = ("farrington", "zscore", "ewma")
    from backtest import BacktestReport
    reports = {m: BacktestReport(method=m) for m in methods}
    for s in seasons:
        for m in methods:
            sc = scorer.score_season(s["name"], s["signals"]["search"], s["onset"], m)
            reports[m].scores.append(sc)

    print_report(reports, "검색어로 탐지 → ILI 유행 onset 대비 리드타임", unit="주")
    detail_table(reports, "farrington", unit="주")
    detail_table(reports, "zscore", unit="주")
    detail_table(reports, "ewma", unit="주")

    far = reports["farrington"]
    print("\n" + "=" * 64)
    ml = far.mean_lead
    ok = far.detection_rate >= 0.75 and (ml is not None and ml > 0)
    print(f" 통합 검증: {'✅ 파이프라인→엔진 연결 정상, 선행 탐지 확인' if ok else '⚠ 신호/파라미터 재검토'}")
    if ml is not None:
        print(f"   평균 선행 리드타임: {ml:+.1f}주  (탐지율 {far.detection_rate*100:.0f}%)")
    print("=" * 64)
    print(" 주의: 방법별로 결과가 다름 — Farrington(보수적, 헛경보 적음)이 가장 신뢰도 높은")
    print(" 기준이며, EWMA가 보여주는 더 긴 리드타임은 헛경보가 그만큼 늘어난 트레이드오프임.")

    # 결과 저장 (covid/ebola 백테스트와 동일한 패턴)
    import json
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "flu_backtest_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "period": [str(df["date"].min().date()), str(df["date"].max().date())],
            "n_weeks_aligned": len(df),
            "seasons": [
                {"name": s["name"], "onset_week_index": s["onset"], "season_length_weeks": len(s["signals"]["official"])}
                for s in seasons
            ],
            "results": {
                m: {
                    "detection_rate": rep.detection_rate,
                    "mean_lead_weeks": rep.mean_lead,
                    "median_lead_weeks": rep.median_lead,
                    "total_false_alarms": rep.total_false_alarms,
                    "seasons": [
                        {"season": sc.season, "official_onset_week": sc.official_onset,
                         "detected_at_week": sc.detected_at, "lead_weeks": sc.lead_time_days,
                         "detected": sc.detected, "false_alarms": sc.false_alarms}
                        for sc in rep.scores
                    ],
                } for m, rep in reports.items()
            },
            "ili_data_source": "KDCA 공공데이터포털 인플루엔자 표본감시 Open API (apis.data.go.kr/1790387/flu/flu) — 실시간 호출",
            "search_data_source": "네이버 데이터랩 API 실시간 호출 (다년치, 2년 단위 분할 요청)",
            "caveat": "방법(Farrington/zscore/EWMA)에 따라 평균 리드타임이 크게 다름 — 헛경보가 적은"
                      " Farrington이 가장 보수적·신뢰도 높은 추정. EWMA의 긴 리드타임은 헛경보 증가와"
                      " 트레이드오프이므로 '선행 N주'를 단일 숫자로 단정하면 안 됨.",
        }, f, ensure_ascii=False, indent=2)
    print(f"\n 결과 저장: {out_path}")


if __name__ == "__main__":
    main()

"""
후향 검증 메인 실행 스크립트
============================
실행:  python3 run_backtest.py

합성 시즌(데모) 또는 실제 데이터(CSV)를 백테스트하고,
방법/신호별 성능 리포트를 출력하며 결과를 CSV로 저장한다.
"""
import sys, os, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import numpy as np
from backtest import make_season, run_backtest, print_report, detail_table


def build_demo_seasons():
    """데모용 4개 시즌 (실제 데이터 연결 전 검증용)."""
    return [
        make_season("2021-2022", seed=11, onset=98,  severity=1.0),
        make_season("2022-2023", seed=22, onset=105, severity=1.2),
        make_season("2023-2024", seed=33, onset=92,  severity=0.9),
        make_season("2024-2025", seed=44, onset=110, severity=1.1),
    ]


def save_csv(reports: dict, path: str):
    rows = []
    for method, rep in reports.items():
        for s in rep.scores:
            rows.append({
                "method": method, "season": s.season,
                "official_onset": s.official_onset,
                "detected_at": s.detected_at if s.detected else "",
                "lead_time_days": s.lead_time_days if s.lead_time_days is not None else "",
                "detected": int(s.detected), "false_alarms": s.false_alarms,
            })
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    print("="*64)
    print(" 역병예보 후향 검증 (Retrospective Backtest)")
    print("="*64)

    seasons = build_demo_seasons()
    print(f" 시즌 수: {len(seasons)}  |  신호: 공식확진 / 검색어 / 하수")

    # 비교군: 공식 확진으로 탐지 (선행 효과 없음)
    rep_off = run_backtest(seasons, signal_choice="official")
    print_report(rep_off, "[비교군] 공식 확진으로 탐지")

    # 본 실험: 선행 신호 융합으로 탐지
    rep_fused = run_backtest(seasons, signal_choice="fused")
    print_report(rep_fused, "[조기경보] 선행 신호 융합(검색어+하수)으로 탐지")
    detail_table(rep_fused, "farrington")

    # 결과 저장
    out = os.path.join(os.path.dirname(__file__), "output", "backtest_results.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = save_csv(rep_fused, out)

    # 합격 판정
    far = rep_fused["farrington"]
    print("\n" + "="*64)
    print(" PoC 합격 기준 판정")
    print("="*64)
    checks = [
        ("선행성 (평균 리드 ≥ 5일)", far.mean_lead is not None and far.mean_lead >= 5),
        ("재현성 (탐지율 = 100%)",   far.detection_rate == 1.0),
        ("헛경보 통제 (시즌당 ≤ 1건)", far.total_false_alarms <= len(seasons)),
    ]
    for label, ok in checks:
        print(f"  [{'✅ PASS' if ok else '❌ FAIL'}]  {label}")
    all_pass = all(ok for _, ok in checks)
    print(f"\n 종합: {'✅ PoC 합격 — 다음 단계 진입 가능' if all_pass else '⚠ 일부 미달 — 튜닝 필요'}")
    print(f" 결과 저장: {out}  ({n}행)")


if __name__ == "__main__":
    main()

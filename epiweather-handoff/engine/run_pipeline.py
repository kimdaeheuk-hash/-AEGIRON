"""
데이터 파이프라인 메인 실행 스크립트
====================================
실행:  python3 run_pipeline.py

Phase 0 '이번 주 할 일' 3단계를 한 번에 수행:
  1) ILI + 검색어 수집 (키 있으면 실데이터, 없으면 합성 폴백)
  2) 주간 정렬 + CSV 저장
  3) 교차상관으로 선행성 확인 + 콘솔 오버레이 그래프
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import numpy as np
import pandas as pd
from pipeline import (fetch_kdca_ili, fetch_search_trend, align,
                      cross_correlation_lead)

# 실제 API 키가 있으면 환경변수로 주입 (없으면 합성 폴백)
KDCA_KEY      = os.environ.get("KDCA_API_KEY")
NAVER_ID      = os.environ.get("NAVER_CLIENT_ID")
NAVER_SECRET  = os.environ.get("NAVER_CLIENT_SECRET")


def ascii_overlay(df, cols, height=12, width=80):
    """두 시계열을 콘솔에 정규화하여 겹쳐 그린다 (선행성 눈으로 확인)."""
    n = len(df)
    step = max(1, n // width)
    idx = list(range(0, n, step))
    norm = {}
    for c in cols:
        v = df[c].to_numpy()[idx]
        norm[c] = (v - v.min()) / (np.ptp(v) + 1e-9)
    chars = {cols[0]: "I", cols[1]: "S"}
    grid = [[" "] * len(idx) for _ in range(height)]
    for c in cols:
        for j, val in enumerate(norm[c]):
            row = height - 1 - int(val * (height - 1))
            grid[row][j] = chars[c] if grid[row][j] == " " else "*"
    print(f"\n  [{cols[0]}=I (ILI)]  [{cols[1]}=S (검색어)]  [*=겹침]  좌→우 = 시간")
    for r in grid:
        print("  |" + "".join(r))
    print("  +" + "-" * len(idx))


def main():
    print("=" * 64)
    print(" 역병예보 데이터 파이프라인")
    print("=" * 64)
    mode = "실데이터" if (KDCA_KEY and NAVER_ID and NAVER_SECRET) else "합성 폴백(키 없음)"
    print(f" 모드: {mode}")

    # 1) 수집
    ili = fetch_kdca_ili(api_key=KDCA_KEY)
    search = fetch_search_trend(client_id=NAVER_ID, client_secret=NAVER_SECRET)
    print(f" 수집: ILI {len(ili.df)}주 / 검색어 {len(search.df)}주")

    # 2) 정렬 + 저장
    df = align(ili, search)
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    aligned_path = os.path.join(out_dir, "aligned_weekly.csv")
    df.to_csv(aligned_path, index=False, encoding="utf-8-sig")
    print(f" 정렬: {len(df)}주, {len(df.columns)}열 → 저장 {aligned_path}")

    # 3) 교차상관 선행성
    best_lag, best_corr, allc = cross_correlation_lead(df, "SEARCH", "ILI", 6)
    print("\n 교차상관 (검색어 → ILI):")
    for lag in sorted(allc):
        bar = "#" * int(max(0, allc[lag]) * 30)
        mark = "  ← 최대" if lag == best_lag else ""
        print(f"  {lag:+d}주  r={allc[lag]:+.3f}  {bar}{mark}")

    verdict = (f"검색어가 ILI보다 약 {best_lag}주 선행 (r={best_corr:.3f})"
               if best_lag > 0 else "뚜렷한 선행성 미검출 — 키워드/기간 재검토 필요")
    print(f"\n 결론: {verdict}")

    # 오버레이 그래프
    ascii_overlay(df, ["ILI", "SEARCH"])

    # 합격 판정 (이번 주 가설: '선행 신호가 존재하는가')
    ok = best_lag > 0 and best_corr > 0.5
    print("\n" + "=" * 64)
    print(f" 1주차 가설 검증: {'✅ 선행 신호 존재 — PoC 진행 가치 확인' if ok else '⚠ 재검토 필요'}")
    print("=" * 64)
    print(" 다음: 이 aligned_weekly.csv를 후향 검증(run_backtest.py)에 연결")


if __name__ == "__main__":
    main()

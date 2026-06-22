#!/usr/bin/env bash
# 역병예보 인수인계 패키지 · 전체 검증 스크립트
# Claude Code가 가장 먼저 실행하여 패키지가 손상 없이 작동하는지 확인합니다.
#
# 사용법:  bash scripts/verify-all.sh
#
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PASS=0; FAIL=0

echo "════════════════════════════════════════════════════════════════"
echo " 역병예보 (EpiWeather) 인수인계 패키지 검증"
echo "════════════════════════════════════════════════════════════════"
echo ""

# ── 1. 파일 구조 검증 ─────────────────────────────────────────────
echo "▶ 1. 파일 구조 확인"
REQUIRED=(
  "CLAUDE.md" "README.md"
  "prototypes/01-unified-command.html"
  "prototypes/02-patient-zero.html"
  "prototypes/03-civic-first.html"
  "prototypes/04-global-inflow.html"
  "prototypes/05-domestic-spread.html"
  "prototypes/06-defense.html"
  "prototypes/07-inference-engine.html"
  "engine/src/scorer.py" "engine/src/backtest.py" "engine/src/pipeline.py"
  "engine/run_pipeline.py" "engine/run_backtest.py" "engine/run_full.py"
  "docs/strategy.md" "docs/phase0-poc-plan.md" "docs/architecture.md"
)
for f in "${REQUIRED[@]}"; do
  if [ -f "$f" ]; then
    echo "  ✅ $f"; PASS=$((PASS+1))
  else
    echo "  ❌ $f  (누락)"; FAIL=$((FAIL+1))
  fi
done
echo ""

# ── 2. HTML 프로토타입 문법 검증 (Node 가능 시) ─────────────────────
echo "▶ 2. HTML 프로토타입 JS 문법"
if command -v node >/dev/null 2>&1; then
  for html in prototypes/*.html; do
    result=$(node -e "
      const fs=require('fs');const html=fs.readFileSync('$html','utf8');
      const m=html.match(/<script>([\s\S]*?)<\/script>/);
      if(!m){console.log('NO_SCRIPT');process.exit(0);}
      try{new Function(m[1]);console.log('OK');}catch(e){console.log('ERR:'+e.message);}
    " 2>&1)
    if [[ "$result" == OK* ]]; then
      echo "  ✅ $(basename $html)"; PASS=$((PASS+1))
    else
      echo "  ❌ $(basename $html) — $result"; FAIL=$((FAIL+1))
    fi
  done
else
  echo "  ⚠ node 없음 — JS 문법 검증 건너뜀 (선택)"
fi
echo ""

# ── 3. Python 엔진 실행 검증 ──────────────────────────────────────
echo "▶ 3. Python 엔진 실행"
if command -v python3 >/dev/null 2>&1; then
  # 의존성 확인
  if ! python3 -c "import pandas, numpy, scipy" 2>/dev/null; then
    echo "  ⚠ pandas/numpy/scipy 미설치 — 다음 명령으로 설치:"
    echo "      pip install pandas numpy scipy --break-system-packages"
  else
    cd engine
    for s in run_pipeline.py run_backtest.py run_full.py; do
      if python3 $s > /dev/null 2>&1; then
        echo "  ✅ $s — exit 0"; PASS=$((PASS+1))
      else
        echo "  ❌ $s — 실패"; FAIL=$((FAIL+1))
      fi
    done
    cd "$ROOT"
  fi
else
  echo "  ⚠ python3 없음 — 엔진 검증 건너뜀"
fi
echo ""

# ── 4. 최종 요약 ─────────────────────────────────────────────────
echo "════════════════════════════════════════════════════════════════"
echo " 검증 결과: ✅ $PASS 통과 / ❌ $FAIL 실패"
echo "════════════════════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo " 🎉 모든 검증 통과 — 패키지 정상 작동"
  echo ""
  echo " 다음 단계:"
  echo "   1. CLAUDE.md를 읽고 프로젝트 맥락 파악"
  echo "   2. prototypes/01-unified-command.html 브라우저로 열기"
  echo "   3. docs/architecture.md 의 Phase 1~5 중 어디부터 시작할지 결정"
  echo ""
  exit 0
else
  echo ""
  echo " ⚠ 일부 검증 실패 — 위 항목 확인 필요"
  exit 1
fi

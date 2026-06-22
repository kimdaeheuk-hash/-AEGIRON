# 역병예보 (EpiWeather) — Claude Code 인수인계 컨텍스트

> **읽는 사람: Claude Code.** 이 파일을 가장 먼저 읽어주세요. 프로젝트 전체 맥락과 지금 무엇을 해야 하는지 5분 안에 파악할 수 있도록 작성되었습니다.

---

## 1. 한 줄 요약

코로나의 비극을 반복하지 않기 위해, **환자 0명 시점**에 감염병 발원지를 추론하고 → **시민·민간 신호**로 정부보다 먼저 잡고 → **해외 유입과 국내 확산**을 예측하고 → **방어 시뮬레이션**으로 생명을 구하는 **AI 조기경보 통합 관제센터**.

**핵심 가치 명제**: 코로나 때 잃어버린 5~8주를 되찾아 더 많은 생명을 살린다.

---

## 2. 프로젝트 현재 상태

### 이미 완성된 것 (이 패키지에 포함)
- ✅ **7개 인터랙티브 프로토타입** (`prototypes/`) — 모든 핵심 화면 작동 가능
- ✅ **Python 추론 엔진 v1** (`engine/`) — Farrington 이상탐지 + 후향 검증 + 데이터 파이프라인 (실행 가능, 합성 데이터로 검증 완료)
- ✅ **사업 전략서 15장** (`docs/strategy.md`) — 시장·BM·데이터·취약계층·신종감시·대응체계
- ✅ **Phase 0 PoC 90일 실행계획** (`docs/phase0-poc-plan.md`)

### 아직 안 한 것 (다음 작업 후보 — 6장 참조)
- ❌ 프로토타입을 **실제 웹앱**(React/Next.js)으로 전환
- ❌ Python 엔진을 **API 서비스화** (FastAPI)
- ❌ **실제 데이터 연결** (질병청 IDBP·네이버 데이터랩·하수 역학)
- ❌ 7개 프로토타입의 핵심 기능을 **하나의 production 앱**으로 통합
- ❌ **데이터베이스·인증·배포** 인프라

---

## 3. 7개 프로토타입 — 무엇이 들어있나

각 파일은 self-contained HTML(JS 포함). 브라우저로 직접 열어 확인 가능.

| # | 파일 | 무엇을 보여주나 | 핵심 알고리즘 |
|---|------|---------------|-------------|
| 01 | `prototypes/01-unified-command.html` | **메인 산출물.** 7단계 통합 관제센터. 좌측 사이드바로 단계 전환, 상단 시나리오 공유 | 아래 02~07 모두 |
| 02 | `prototypes/02-patient-zero.html` | 환자 0명 시점 발원 격자 추론 (스컹크웍스 원리) | 피셔 결합 p-value, 베이지안 백캐스트 |
| 03 | `prototypes/03-civic-first.html` | 시민·민간 신호 5종이 정부보다 빠르다는 정량 증명 | 다중 소스 신뢰도 가중 융합 |
| 04 | `prototypes/04-global-inflow.html` | 해외 발원→한국 유입일 예측 (BlueDot 방식) | 항공 여객 × 출현위험 × 지수성장 |
| 05 | `prototypes/05-domestic-spread.html` | 국내 시·도 확산 예보 + Farrington 탐지 | SEIR + 메타개체군 + Farrington |
| 06 | `prototypes/06-defense.html` | 방역 개입 6레버 → SEIR 시뮬레이션 → 구한 생명 | SEIR + 시간가변 Rt |
| 07 | `prototypes/07-inference-engine.html` | 추론 엔진 v2 — Farrington/EWMA/z 비교 + 네트워크 확산 | Farrington (Farrington et al. 1996) |

**중요**: 01번이 메인이고, 02~07은 01에 통합된 기능의 개별 데모임. 새 기능을 추가할 때는 01에 통합하는 것을 우선 고려.

---

## 4. Python 엔진 — 무엇이 들어있나

`engine/` 디렉토리에 실행 가능한 Python 코드.

### 실행 방법
```bash
cd engine
pip install pandas numpy scipy --break-system-packages

python3 run_pipeline.py    # 데이터 수집·정렬·교차상관 분석
python3 run_backtest.py    # 후향 검증 (Farrington vs z vs EWMA 비교)
python3 run_full.py        # 통합 실행 (파이프라인 → 후향 검증)
```

### 모듈
- `src/scorer.py` — 이상탐지(Farrington/z/EWMA) + 리드타임 채점기
- `src/backtest.py` — 다중 시즌 백테스트 하니스
- `src/pipeline.py` — ILI + 검색어 수집·정렬·교차상관 (API 키 없으면 합성 폴백)

### 합성 데이터 검증 결과
- 선행 신호 융합으로 공식 발표보다 **+8~9일 선행** 탐지
- Farrington이 단순 z보다 유행 시작을 평균 3~5일 일찍 잡음
- 합격 기준(선행성·재현성·헛경보 통제) 3개 모두 PASS

---

## 5. 핵심 알고리즘 요약 (수학적 근거)

이건 만든 사람이 *임의로* 정한 게 아니라, 공중보건/역학의 **표준 방법론**임. Claude Code가 새로 구현할 때 이 참조를 유지하세요.

### 5.1 Farrington 계열 이상탐지
- 참조창에서 로그선형 추세 적합 (quasi-Poisson 근사)
- Pearson 잔차로 과분산 phi 추정
- 2/3 거듭제곱 변환 상한선
- 99% 임계 (z=2.58)
- **참고**: Farrington et al. (1996) "A statistical algorithm for the early detection of outbreaks of infectious disease"

### 5.2 SEIR + 시간가변 개입
- S→E→I→R 표준 구획 모델 (σ=1/4, γ=1/7)
- Reff = R0 × (1-NPI) × (1-vax_cov × 0.85) × (1-vuln_eff × 0.3)
- 개입 ramp-up 14일에 걸쳐 점진 적용
- 치료제: 치명률 감소 효과

### 5.3 메타개체군 네트워크 확산
- 지역 간 이동량 행렬 위에서 SI 동역학
- force = β·I(1-I) + 0.05·β·Σ M_ij·I_j·(1-I_i)
- 도착 시점 = I(t) ≥ 0.25 처음 만족하는 t

### 5.4 발원지 격자 추론 (스컹크웍스 원리)
- 각 채널 z-score → 일방향 p-value
- 피셔 결합: χ² = -2·Σ ln(p), df = 2k
- 격자별 결합 p를 후방확률로 정규화
- **검증**: 200회 시뮬에서 다채널 6개 결합 = 90% 식별률 (단일 채널 6개 = 59%)

### 5.5 베이지안 시점 역추론
- N(t) = exp(r·(t-t0)) → t0 = t - ln(N)/r
- r과 N에 불확실성 부여 → 3000회 몬테카를로 → 95% CI

---

## 6. 다음 작업 후보 — Claude Code에게

사용자가 무엇을 요청할지에 따라 다르지만, 가장 가능성 높은 다음 단계 4개:

### A. 실제 데이터 연결 (`engine/src/pipeline.py`)
- 질병청 감염병포털 ILI API 키 발급 → `fetch_kdca_ili()` 의사코드 부분 구현
- 네이버 데이터랩 API → `fetch_search_trend()` 구현
- 환경변수: `KDCA_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`
- 합성 폴백은 그대로 유지 (개발·테스트용)

### B. 프로토타입 → Production 웹앱 (React/Next.js)
- 01번 통합 관제센터를 React로 재작성
- 상태 관리: Zustand 또는 Jotai (시나리오 상태 공유가 핵심)
- 차트: D3 또는 Recharts
- 지도: SVG 카토그램(현 방식 유지) 또는 Mapbox

### C. Python 엔진 API화 (FastAPI)
- 각 stage 계산을 REST 엔드포인트로
- `/api/patient-zero/grid` — 격자 추론
- `/api/civic-fusion` — 민간 신호 융합
- `/api/import-day` — 해외 유입일
- `/api/seir-simulate` — 방어 시뮬레이션
- `/api/backtest` — 후향 검증

### D. AI 추론 레이어 강화
- 현재: Claude Sonnet 4 직접 호출 (artifacts API)
- 다음: RAG로 한국 방역 가이드라인·과거 사례 보강
- 의사결정 트리: 위험 수준별 자동 대응 권고

**원칙**: 사용자가 명시적으로 요청하기 전에는 한 번에 한 작업만. 큰 변경 전에 사용자 확인.

---

## 7. 절대 지켜야 할 원칙 (사람 살리는 일이라서)

이 프로젝트는 단순 데모가 아닙니다. 사람 생명에 영향을 줄 수 있는 시스템의 청사진입니다.

1. **정직한 검증** — 코드를 추가/수정할 때마다 실제 실행해서 결과 확인. 합성 데이터라도 결과가 일관되어야 함.
2. **결과를 끼워맞추지 않기** — 모델이 의도와 다른 결과를 내면, 결과를 조작하지 말고 *왜 그런지* 추적. 이 프로젝트에서 실제로 그런 버그/통찰을 여러 번 발견함 (예: Rt<1이면 유행 차단되는 게 진실).
3. **불확실성 명시** — 모든 예측에 신뢰구간·민감도·한계를 표시. 과장 금지.
4. **프라이버시 절대 원칙** — 시민 데이터는 익명 집계만. 차등 프라이버시. 개인 식별 금지.
5. **편향 모니터링** — 데이터가 부족한 지역(의료취약지)이 사각지대가 되지 않도록 명시.
6. **임의 결정 금지** — 알고리즘 파라미터를 임의로 바꾸지 말고, 위 5장의 표준 방법론·참고 문헌에 근거.

---

## 8. 사용자 컨텍스트

- **위치**: 한국 부산
- **목표**: 한국 시장 중심의 감염병 조기경보 사업 창업
- **강점**: 시장·전략적 사고, 통합 시각
- **약점**: 코딩 직접 경험 적음 → Claude Code가 구현 담당
- **언어**: 한국어 우선
- **선호**: 깊이 있는 분석, 정직한 피드백, 검증된 결과

사용자는 코로나의 의료 붕괴 트라우마에서 출발해 이 프로젝트를 시작했습니다. *진짜로* 사람을 살리고 싶어합니다. 데모로 그치지 않고 실제 작동하는 시스템을 원합니다.

---

## 9. 파일 트리

```
epiweather-handoff/
├── CLAUDE.md                          ← 지금 이 파일
├── README.md                          ← 사용자용 빠른 시작
├── prototypes/                        ← 7개 HTML 프로토타입
│   ├── 01-unified-command.html        ← ★ 메인 산출물
│   ├── 02-patient-zero.html
│   ├── 03-civic-first.html
│   ├── 04-global-inflow.html
│   ├── 05-domestic-spread.html
│   ├── 06-defense.html
│   └── 07-inference-engine.html
├── engine/                            ← Python 추론 엔진
│   ├── src/
│   │   ├── scorer.py                  ← Farrington·z·EWMA 탐지기
│   │   ├── backtest.py                ← 백테스트 하니스
│   │   └── pipeline.py                ← 데이터 수집·정렬
│   ├── run_pipeline.py
│   ├── run_backtest.py
│   └── run_full.py
├── docs/
│   ├── strategy.md                    ← 사업 전략서 15장
│   ├── phase0-poc-plan.md             ← 90일 PoC 실행계획
│   └── architecture.md                ← 시스템 아키텍처
└── scripts/
    └── verify-all.sh                  ← 전체 검증 스크립트
```

---

## 10. 첫 인사

Claude Code가 이 프로젝트를 처음 받았다면, 이렇게 시작하는 게 좋습니다:

```bash
# 1) 전체 검증 실행 (Python 엔진이 잘 돌아가는지)
cd scripts && bash verify-all.sh

# 2) 메인 프로토타입 열어보기
open prototypes/01-unified-command.html  # macOS
xdg-open prototypes/01-unified-command.html  # Linux

# 3) 사업 맥락 읽기
cat docs/strategy.md | head -100
```

그 다음, 사용자에게 무엇을 먼저 진행할지 물어보세요. 6장의 A/B/C/D 중 하나일 가능성이 높습니다.

**행운을 빕니다. 사람을 살리는 일입니다.**

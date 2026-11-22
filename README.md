# AEGIRON — 극지 감지 → 헤임달 식별 → 발할라 대응 판정

국가 바이오안보 기관을 첫 고객으로 둔 한 줄기 시스템.

| 고리 | 하는 일 | 주기 |
|---|---|---|
| **극지(POLAR)** · 감지 | 8개 극지 지역의 기온·해빙일수(Open-Meteo)와 현지어 보도 관찰, 16년 재분석 대비 편차 계산 | 매시 |
| **헤임달(HEIMDALL)** · 식별 | Nextstrain 공개 빌드의 우세 계통 전이를 원장에 기록 · 서열 스크리닝(방어 전용) | 매시 / 요청 시 |
| **발할라(VALHALLA)** · 대응 판정 | 위협 × 등록 대응제 × 변이 대조 판정을 하루 한 행 원장에 기록 | 매시(무거운 조각은 주기마다) |

2026-11-22 개편으로 나머지(전 세계 경보·예측 원장·BAIKAL 등)는 지웠다.
복원 기준 커밋: `83406e4` (`git checkout 83406e4 -- <경로>`). 계획: `docs/아이기론_개편계획_2026-11.md`.

## 구조

- `epiweather-api/` — FastAPI + 매시 스케줄러 (Railway). `main.py` · `collector.py` · `db.py` · `algorithms/` · `tests/`
- `epiweather-web/` — Next.js 16 · Astryx (Vercel). 홈 · `/polar` · `/dashboard`(세 고리 운영 화면) · 콘텐츠 페이지
- `docs/` — 개편 계획, 소킹 일지

## 실행

```bash
cd epiweather-api
pip install -r requirements.txt
python3 -m pytest -q                                   # 602건, 외부 HTTP 차단
EPIWEATHER_SCHEDULER=off uvicorn main:app --port 8000  # /docs 에 OpenAPI

cd ../epiweather-web
npm ci && npm run build                                # NEXT_PUBLIC_API_URL 로 API 주소 지정
```

## 정직 원칙

- 측정 · 추정 · 대리값을 섞지 않는다.
- 성공 / 실패 / 판정 안 함 — 못 본 것을 0 이나 정상으로 적지 않는다.
- 예측 정확도 트랙레코드 없음. 관찰 등급은 경보가 아니다.

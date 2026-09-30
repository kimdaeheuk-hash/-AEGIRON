---
name: backend-conventions
description: epiweather-api 코드 규약 — 파일 구조, 스케줄러 시각, 라우트/DB 추가법, 로그 규칙, 신호 카테고리와 신뢰도. 백엔드 코드를 쓰거나 고칠 때 읽는다.
---

# backend-conventions

## 구조

- `main.py` — FastAPI 라우트(약 120개) + **스케줄러**(`asyncio` 루프). 라우트는 얇게, 계산은 `algorithms/` 로.
- `collector.py` — 소스 수집(`collect_free_sources`, `collect_ai_sources`)과 `log()`/`log_error()`.
- `algorithms/` — 순수에 가깝게 쓴다: 입력을 받아 dict 를 돌려준다. DB 는 `db` 모듈로만.
- `db.py` — SQLite(`data/epiweather.db`). 테스트는 `isolated_db` 픽스처로 임시 DB 를 쓴다.
- `data/` — 운영 상태 파일. **테스트가 여기에 쓰면 안 된다**(능력 장부가 가짜 성공을 적은 적이 있다 — `conftest.py` 참고).

## 스케줄 (UTC)

- 무료 소스: 매시간. 경보 주기(`_run_alert_cycle`): 매시간.
- AI 갭필링(유료): `_AI_HOUR_UTC = 21`. 이 슬롯에 `📌 정답 적재`, `📋 예측 기록` 이 찍힌다.
- 일일 브리핑: `_DAILY_BRIEF_HOUR_UTC = 22`.
- **배포는 컨테이너를 죽인다** — 틱 직전에 배포되면 그 슬롯이 통째로 빠진다(2026-08-22). 빠진 것과 못 본 것을 구분해 적는다.

## 신호와 신뢰도

`trusted_score = raw_score × trust` (`algorithms/trust.py` 의 `SOURCE_TRUST`).
who 1.00 · cdc 0.95 · government/behavioral_api/document_extracted 0.90 · academic 0.85 ·
document_extracted_unverified 0.70 · ai_extracted 0.65 · prediction_market 0.35 · unknown 0.10.
**새 카테고리를 만들기 전에 이 표에서 고른다.** 낮춘 이유·높인 이유가 코드 주석에 있다 — 지우지 않는다.

## 규칙

- **`log()` 만 쓴다.** `print` 를 직접 쓰지 않는다. 예외는 `log_error(context, e)` — 파일에만 남기지 않는다(2026-08-13).
- 문자열로 숫자를 읽을 때 쉼표를 처리한다(`int("1,296")` 가 나흘간 국내 데이터를 비웠다).
- 여러 조각을 더하는 지표는 `signal_metrics.sum_if_complete()` — 조각이 하나라도 빠지면 `None`(판정 안 함).
- 새 라우트: `main.py` 에 추가하고 시험은 `TestClient` 로. 인증이 필요한 라우트는 기존 `Depends` 를 따른다.
- 새 값을 화면·알림으로 내보낼 때는 **`honesty-review`** 를 먼저 거친다.
- 함수를 만들었으면 **누가 부르는지** 확인한다. 만들어만 두고 아무도 안 부르는 층이 이 저장소의 반복 결함이다.

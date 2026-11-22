---
name: backend-conventions
description: epiweather-api 코드 규약 — 파일 구조, 스케줄러, 라우트/DB 추가법, 로그 규칙. 백엔드 코드를 쓰거나 고칠 때 읽는다.
---

# backend-conventions

2026-11-22 개편 뒤 남은 층은 셋이다 — **극지(감지) → 헤임달(식별) → 발할라(대응 판정).** 나머지는 지웠다
(복원 기준 커밋 `83406e4`: `git checkout 83406e4 -- <경로>`). 범위를 넓히는 변경은 캡틴 지시가 있을 때만.

## 구조

- `main.py` — FastAPI 라우트(25개 · 인증 7개) + **스케줄러**(`asyncio` 루프). 라우트는 얇게, 계산은 `algorithms/` 로.
- `collector.py` — `collect_free_sources()` 가 극지 → 헤임달(변이·대조 원장) → 발할라 → 소스 건강 순으로 돈다. `log()`/`log_error()`.
- `algorithms/` — 입력을 받아 dict 를 돌려준다. DB 는 `db` 모듈로만.
- `db.py` — SQLite(`data/epiweather.db`). 남은 표: `variant_ledger` · `match_ledger` · `countermeasure_stockpile` · `observations` · `api_key_usage`.
  운영 DB 에는 옛 표가 남아 있지만 읽지도 쓰지도 않는다. 표를 바꾸면 `SCHEMA_VERSION` 을 올린다(안 올리면 운영 DB 에 안 생긴다).
- `data/` — 운영 상태 파일. **테스트가 여기에 쓰면 안 된다**(`conftest.py`).

## 스케줄 (UTC)

- 수집: 매시간(`_run_collection`) — 끝나면 극지 관측값을 `observations` 에 저장(`_store_observations`).
- 주간 작업: 기준 스냅샷 갱신(`reference_snapshots.refresh_due`), 7일마다.
- **배포는 컨테이너를 죽인다** — 틱 직전에 배포되면 그 슬롯이 빠진다. 빠진 것과 못 본 것을 구분해 적는다.

## 규칙

- **`log()` 만 쓴다.** 예외는 `log_error(context, e)`.
- 실패는 `None`(판정 안 함)이지 `0` 이 아니다. 여러 조각을 더하면 하나라도 빠졌을 때 `None`.
- 새 라우트: `main.py` 에 추가하고 시험은 `TestClient` 로. 인증이 필요한 라우트는 `dependencies=_auth`.
  라우트를 바꾸면 웹의 `epiweather-web/src/data/api-endpoints.json` 도 다시 뽑는다.
- 새 값을 화면으로 내보낼 때는 **`honesty-review`** 를 먼저 거친다.
- 함수를 만들었으면 **누가 부르는지** 확인한다. 만들어만 두고 아무도 안 부르는 층이 이 저장소의 반복 결함이다.

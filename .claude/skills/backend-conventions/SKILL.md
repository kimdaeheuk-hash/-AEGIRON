---
name: backend-conventions
description: epiweather-api 코드 규약 — 파일 구조, 스케줄러, 라우트/DB 추가법, 로그 규칙. 백엔드 코드를 쓰거나 고칠 때 읽는다.
---

# backend-conventions

2026-11-22 개편 뒤 남은 층은 셋이다 — **극지(감지) → 헤임달(식별) → 발할라(대응 판정).** 나머지는 지웠다
(복원 기준 커밋 `83406e4`: `git checkout 83406e4 -- <경로>`). 범위를 넓히는 변경은 캡틴 지시가 있을 때만.

## 구조

- `main.py` — FastAPI 라우트(17개 · 인증 5개) + **스케줄러**(`asyncio` 루프). 라우트는 얇게, 계산은 `algorithms/` 로.
- `collector.py` — `collect_free_sources()` 가 극지 → 헤임달(변이·대조 원장) → 발할라 → 소스 건강 → **BAIKAL MOB** 순으로 돈다. `log()`/`log_error()`.
- **헤임달 성장 신호**(`genomic_variants.growth_signal`, 2026-11-23) — 최근 4주 vs 직전 4주 계통 구성비 로그 변화/주(추정).
  두 구간 각 50건 미만이면 판정 안 함, 최근 10건 미만 계통은 안 올린다. 수집이 `response_cache.put("variant_growth")` →
  `/api/variant-growth` 가 `peek` 으로 읽는다(없으면 판정 안 함 — Nextstrain 을 대신 받지 않는다). 로그 `📈 성장 신호 …`.
- **발할라 공백 지도**(`algorithms/gap_map.py`, 2026-11-23) — WHO 2024 체계 기반 27개 병원체 × 백신·치료제·FDA 승인·진단·국산.
  등록부 `REGISTRY` 는 2차 문헌 기반(원문 표 미대조 — `basis` 로 근거 수준 표기). 백신 = WHO PQ → 없으면 CT.gov 백신 연구,
  치료제 = CT.gov 치료제 연구(4상=approved), FDA = openFDA 주간 스냅숏(검색어는 `FDA_TERMS` 를 approved_products 에 합침),
  진단 = 출처 있는 손 표 `DIAGNOSTICS` 만, 국산 = 판정 안 함. 임상은 발할라 무거운 조각 `gap_trials`(24h, 병렬 6).
  `/api/valhalla/gap-map`(10분 캐시)·로그 `🗺 공백 지도 …` 는 `gap_map.current()` 로 저장본만 읽는다.
  승인 제품 스냅숏이 새 위협을 안 물어봤으면 신선해도 다시 받는다(`reference_snapshots._missing_threats`).
- **BAIKAL MOB**(`algorithms/baikal.py`, 2026-11-22 재구현) — 상태변화 엔진. **온톨로지(`algorithms/ontology.py`) 위층.**
  수집 주기 끝에서 엔진 5개(수집 주기·헤임달 변이·헤임달 스크리너·발할라·극지)를 정상/저하/중단/판정 안 함으로 판정하고,
  바뀐 순간만 전이로 남긴다(`baikal_mob_*` 표). 상류가 중단·판정 안 함이면 온톨로지 간선을 따라 하류 입력이 낡았다고 **주석만** 단다(하류 상태는 안 바꾼다).
  로그 `🌊 BAIKAL: 정상 N/5 · …` · `🌊 BAIKAL 전이: …`. API `/api/baikal` · `/api/baikal/transitions`.
  수집 결과 dict 에 판정용 키(`polar_regions_*` · `*_error` · `variant_ledger_ok`)를 남기는 것은 이 엔진을 위해서다 — 지우면 판정이 '판정 안 함'으로 떨어진다.
  온톨로지에 간선을 더할 때는 `wired_at` 에 실제 코드 자리를 적는다(지어낸 간선 금지).
- `algorithms/` — 입력을 받아 dict 를 돌려준다. DB 는 `db` 모듈로만.
- `db.py` — SQLite(`data/epiweather.db`). 남은 표: `variant_ledger` · `match_ledger` · `countermeasure_stockpile` · `observations` · `api_key_usage` · `baikal_mob_snapshots` · `baikal_mob_transitions`(v7).
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

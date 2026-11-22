---
name: collector-source
description: 데이터 소스를 추가·수정할 때의 규칙 — 실패 사유 집계, 값 없음 표시, 소스 건강 반영, 원천 갱신 주기. collector.py 나 fetch_* 함수를 만질 때 읽는다.
---

# collector-source

## ⚠️ 먼저 — 범위

개편(2026-11-22) 뒤 소스는 셋뿐이다: `PolarWatch`(Open-Meteo + 현지어 뉴스) · `GenomicVariants`(Nextstrain) · `Valhalla`.
`collector.FREE_SOURCE_HEALTH_KEYS` 가 그 목록이다. **새 소스는 캡틴 지시가 있을 때만** 붙인다 — 넓히다가 전문성이 흐려진 것이 개편 이유였다.

## 소스 하나가 지켜야 할 것

1. **실패와 '값 없음'을 구분한다.**
   - 실패 → `log_error`, 결과 키를 `None` 으로 — 소스 건강이 실패로 센다.
   - 값 없음(수집은 정상이나 쓸 값이 없음) → `mark_no_data(result, key)` **그리고 사유를 로그에 남긴다.**
2. **실패 사유를 집계한다**(`_fmt_failure_reasons`, Open-Meteo 는 `failure_reasons_line`). `HTTP 429×2` 처럼.
3. **실패 시 0 을 돌려주지 않는다.**
4. **원천의 갱신 주기를 확인한다.** 매시 읽는 것과 원천이 바뀌는 속도는 다르다 — 발할라는 무거운 조각을 주기가 지났을 때만 다시 받고 `age_hours` 를 같이 낸다.
5. **외부 한도를 아낀다.** Open-Meteo 재분석은 일일 한도(429)에 걸린 적이 있다 — 과거 구간은 월 단위 캐시, 이번 달만 매일(`polar_baseline._fetch_daily_max`).
6. **소스 건강에 잡히는지 확인한다.** `📊 소스 건강: 정상 N/M` — 맵에 없는 옛 항목은 `record_cycle` 이 상태 파일에서 지운다.

## 끝내기 전

- 시험: 성공 / 부분 실패 / 전체 실패 / 값 없음 / 파싱 이상 — 다섯 경로.
- 배포 뒤: 이 소스가 정상으로 잡히는지 **로그로 관측**한다(`prod-observability`).

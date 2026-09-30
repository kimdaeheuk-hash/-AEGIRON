---
name: alert-pipeline
description: 경보가 만들어져 사람(폰·화면)에게 가는 전 과정 — GAI 점수·신뢰도, 등급과 캡, 부정적 공간 감시(허용목록), 에스컬레이션 통보, 내림. alerts.py·negative_space.py·gai.py 를 만지거나 "왜 이 경보가 울렸지/안 울렸지"를 추적할 때 읽는다.
---

# alert-pipeline

```
수집 → 지표 → 후보(collect_candidate_alerts) ─┐
                부정적 공간(scan_negative_space) ─┴→ refresh_alerts → 등급·캡 → 화면 / 텔레그램
```

## 점수와 등급 (`algorithms/alerts.py`)

- `trusted_score = raw_score × trust` (신뢰도는 `trust.SOURCE_TRUST`).
- 등급(`classify_tier`): critical ≥ 90 · high ≥ 80 · medium ≥ 70 · 그 아래 low. **`CANDIDATE_FLOOR = 50` 미만은 후보도 아니다.**
- 하루 캡: `DAILY_CAPS = {"critical": 3, "high": 5}`(medium·low 는 무제한). 대시보드 상단은 `DASHBOARD_TOP_N = 5`.
- `refresh_alerts(today)` 는 후보를 `db.upsert_alert` 로 올린 뒤 캡을 적용한다. **행을 지우지 않는다** — `suppressed` 로만 가린다(감사 기록).

## 부정적 공간 감시 (`negative_space.py`)

"평소 활발하던 **보고 채널**이 조용해지면 보고 체계가 무너진 것"이라는 추론이다. 전제가 성립하는 지표만 판정한다:

- **허용목록 `REPORTING_CHANNELS`(9개)** 만 본다. 나머지는 사유별로 세어 로그에 낸다(`계절성 · 미선언 · 재척도 · 표본불안정 · 관측부족`).
- `eligibility(metric_id)` 가 (판정 가능?, 사유)를 돌려준다. 옛 제외 집합 셋은 **왜 뺐는지를 들고 있어서** 지우지 않았다.
- 문턱(`DROP_RATIO=0.5`, `MIN_MEANINGFUL_AVG=2.0`)으로는 못 막는 문제가 있었다 — `social_mpox` 의 평균 2.59 가 2.0 을 넘었다.
  **그래서 제외 목록을 늘리지 않고 자격을 선언하게 했다.** 대가: 판정 대상 ~30개 → 9개.
- 늘릴 때는 `collector-source` 의 기준(기관·언론의 보고 건수인가, 누적/주간 확인했는가)을 따른다.

## 통보 (텔레그램)

- 신규 critical/high 만 보낸다. 상태: `전송됨 / 전송 실패 / 보낼 신규 경보 없음 / 채널 미설정 / 판정 안 함`.
- **에스컬레이션**(`escalated`): 처음 보는 source 는 보낸다 · low→critical 은 보낸다 · critical→critical 은 안 보낸다 ·
  critical→high 는 안 보낸다 · high→critical 은 보낸다. 낯선 등급 문자열은 0 으로 본다(모르는 값이 진짜 경보를 막으면 안 된다).
  (09-22 에 등급이 올라가도 통보가 안 나간 적이 있다 — `already_seen_today` 가 source 만 봤다.)
- `seen_rank` 는 **upsert 전에** 계산한다. 그래서 내려갔다 되살아난 행이 폰을 두 번 때리지 않는다.
- 근거 첫 두 줄이 텔레그램에 같이 간다. 데이터가 `<`·`&` 를 포함할 수 있으니(`parse_mode=HTML`) 값은 전부 이스케이프하고 우리 태그는 템플릿에서만 쓴다.

## 내림 (#46, #47)

후보에서 빠진 행은 `retired` 로 화면·등급 집계에서 내린다(행은 남는다, 되살아나면 upsert 가 다시 올린다).
등급 캡의 `suppressed`("한도에 밀림")와 **따로** 센다("판정에서 빠짐"). 로그 `🔽 내림:` 이 이름을 말한다.
⚠️ **열린 질문**: 내림은 "이번 사이클에 후보가 아니다" 하나로 결정된다. 값이 내려간 것과 *스캔이 못 낸 것*이 섞이면
수집 실패가 진짜 경보를 조용히 내릴 수 있다. 캡틴 결정 대기 중(스캔이 못 낸 경우를 '판정 안 함'으로 가르는 안).

## "왜 울렸나 / 왜 안 울렸나" 추적 순서

1. `🚨 경보 주기` 줄의 이름 목록과 근거 첫 줄 → 무엇이 몇 점이었나.
2. `🔇 부정적 공간` 줄의 `급감 N건` 이 0 인데 경보에 그 이름이 있으면 → **옛 행**이다(같은 사이클 대조가 증거).
3. `🔽 내림` → 어떤 행이 화면에서 내려갔나.
4. `📊 소스 건강` → 입력이 끊긴 게 아닌가.
5. 그래도 모르면 **'판정 못 함'** 으로 적는다.

---
name: prediction-loop
description: 피드백 루프(정답 적재 → 질병 지목 예측 → 채점) — 각 링크가 어디서 도는지, 왜 흐르는 양이 0 이어도 정직한지, 자가채점을 피하는 법. declaration_ingest·country_risk 예측·prediction_resolver 를 만질 때, 또는 '선행일수 실측'을 논할 때 읽는다.
---

# prediction-loop

"아이기론이 남보다 먼저 안다"는 제품의 논지를 **증명할 경로**다. 세 링크가 다 매일 돌아야 증거가 쌓인다.

```
① 신호 → 정답        who_don_declarations + declaration_ingest (21:00 UTC 슬롯)
                       📌 WHO DON 정답 적재 N건 / 검토 N건   ·   📌 정답 적재 N건 / 검토 N건
② 위험도 → 예측       country_risk._record_prediction            📋 예측 기록: …   (매 시간 수집 주기 · 새 기록이 있을 때만)
③ 예측 → 채점        prediction_resolver.resolve_due_predictions 해소할 예측 없음(미결 N건)
```

**순서가 중요하다 — 채점 전에 적재가 먼저 돈다.** 반대면 오늘 들어온 선언을 못 보고 채점한다.

## ① 정답 (`algorithms/declaration_ingest.py`)

- `extracted_signals` 의 **공식 선언**을 `outbreak_timeline` 에 올린다. `source_type="official_live"`(손으로 적은 16건 백필과 구분).
- 문턱은 `trust.SOURCE_TRUST["document_extracted"]` = **0.90**. `ai_extracted`(0.65)·`document_extracted_unverified`(0.70)는 안 받는다.
- **문턱을 낮추지 않는다.** 우리 신호로 우리 예측을 채점하는 자가채점이 되고, 이 제품이 파는 게 정확히 그 숫자(적중률)다.
- 걸러낸 사유를 집계해 로그에 낸다: `선언아님 22 · 신뢰도미달 178`. 조용히 버리면 정답이 왜 안 느는지 아무도 모른다 —
  2년을 그렇게 보냈다(가장 최근 정답이 2024-09-27 이었다).

### 왜 `declaration_ingest` 만으로는 0건이었나 (2026-10-07 진단)

`eligible()` 은 신뢰도 ≥0.90 **그리고** `신규발생` 을 요구하는데 그런 신호를 만드는 생산자가 없었다 — 뉴스 NLP 추출은
0.65(`신규발생` 가능), WHO 표 추출(`bulletin_ingest`)은 0.90 이지만 `진행중/불명` 만. `신뢰도미달 178 · 선언아님 22` 가
정확히 그 모양이다. 문턱을 낮추지 않고 **생산자를 추가**했다: `who_don_declarations`(WHO DON — 사람이 쓴 공식 발표,
AI 추출 없음). `source_type="who_don"`, 마일스톤 `who_statement`. 같은 질병·국가·연도의 **첫 DON** 만 정답이고
(날짜를 뒤로 밀지 않는다), 국가를 못 읽는 제목(`… – African Region`)은 건너뛴다. 영어 제목에 한글 표준명을 덧붙여
한글 예측과 완전일치가 되게 한다. ⚠️ 응답 형식은 샌드박스에서 못 봤다 — 프로덕션 첫 21:00 슬롯 로그가 검증이다.

### 눈이 먼 채 지난 침묵은 오답이 아니다 — `ground_truth_channel.blind_reason`

기한이 지나도 선언이 없을 때 `incorrect`(채점기)·`no_declaration`(원장)으로 닫는 것은 **정답 경로가 그 기간을 보고 있었을
때만**이다: ①첫 적재가 구간 시작 이전, ②구간 안 날짜의 선언이 하나라도 적재됨(손으로 적은 백필은 안 센다). 아니면 닫지
않고 열어 둔다(판정 안 함) — `⏸ 예측 판정 보류: … N건 — 사유`. 정답이 나중에 적재되면 ①이 다시 대조할 수 있다.

## ② 예측 (`country_risk.py`)

- 예측의 `disease` 는 **위험도를 실제로 끌어올린 질병**이다: `dominant_disease()` → `(이름|None, 비중)`.
  비중 < `DOMINANT_DISEASE_MIN_SHARE`(0.5)이거나 **동점**이면 이름을 안 붙인다(동점의 1등은 dict 순서가 정한 것이지 신호가 정한 게 아니다).
- 못 고른 경우 `UNNAMED_DISEASE`(`"종합 위험도(GAI 기반)"`)로 기록하고 로그에는 **`질병 미지목`** 으로 그대로 보인다 — 숨기면 '전부 지목되고 있다'로 읽힌다.
- 지목한 이름은 정답이 올라가는 필드(`extracted_signals.disease`)와 **같은 어휘**라 표기가 어긋날 자리가 없다.
  이름이 `종합 위험도(…)` 면 어떤 사건 이름에도 안 나오므로 **적중이 불가능**하다(#42 가 고친 것).
- 점수(`_nlp_raw_score`)와 이름 붙이기가 같은 식(`_signal_weight`)을 쓴다 — 식이 두 벌이면 '점수를 만든 질병'과 '이름 붙인 질병'이 말없이 갈라진다.
- 쿨다운 `PREDICTION_COOLDOWN_DAYS=14`, 판정 기한 `PREDICTION_HORIZON_DAYS=90`.

## ③ 채점 (`prediction_resolver.py`)

- 선언이 기한 내에 있으면 `correct=1`, `lead_days = 선언일 − 예측일`. 기한이 지나도 선언이 없으면 `correct=0`(**조용했다는 것도 채점 대상**).
  기한 전이고 선언도 없으면 미결 — 건드리지 않는다.
- `match_kind()` 는 `none/country/full`. **국가만 맞는 것을 correct 로 올리지 않는다**(그 나라에 아무 발병이나 나면 맞은 게 된다).
  incorrect 로 떨어뜨리지도 않는다(실제로 있었던 발병을 없었다고 하는 것).
- ⚠️ 정답이 안 쌓이면 빗나간 예측이 90일 뒤 `incorrect` 가 되며 **"측정된 것처럼 보이는 적중률 0%"** 를 스스로 만든다.
  그래서 ①이 열려 있어야 ③을 믿을 수 있다.

## 지금 상태를 읽는 법

`정답 적재 0건 / 검토 200건 · 선언아님 22 · 신뢰도미달 178` 이 며칠째 같은 자리 — 이건 **정답이 없는 게 아니라
정답으로 쓸 자격이 되는 신호가 0건**이라는 뜻이다. 루프는 돌고 있고 흐르는 양이 0이다. 실측 선행일수는 아직 0건이고
미결 예측이 쌓이는 중이다(21→23건). 이걸 "적중률 없음"이나 "적중률 0%"로 쓰지 않는다 — **'아직 측정 불가'** 다.

---
name: testing
description: 아이기론 시험 작성·실행 규칙 — 픽스처, 스텁 방식, 배선을 AST 로 고정하는 법, 옛 입력 재현, 단언을 약하게 만들지 않는 원칙. 시험을 쓰거나 시험이 깨졌을 때 읽는다.
---

# testing

## 실행

`cd epiweather-api && python3 -m pytest -q` — **push 전에 전체를 돌린다.**(마지막 기준 1,966건)
부분 실행은 개발 중에만. CI 는 `pytest tests/ -v`.

## 기본 도구

- `isolated_db` — 임시 SQLite. DB 를 건드리는 시험은 반드시 쓴다.
- 외부 HTTP 는 자동 차단(`conftest.py`). 호출부가 `requests.RequestException` 을 이미 다루므로 시험이 안 깨진다.
- 스텁은 `monkeypatch.setattr(모듈, "함수", lambda …)`. 좋은 예: `tests/test_retired_alerts.py` 의 `_stub`.

## 이 저장소 고유의 시험 세 가지

1. **배선 시험(AST)** — 함수를 만들었으면 *호출 경로*를 AST 로 고정한다. `ast.parse(파일)` 로 스케줄러
   함수 안에 `Call(Name=…)` 이 있는지, 그 결과가 `log` 로 나가는지 본다.
   (`tests/test_retired_alerts_named.py::test_scheduler_path_actually_logs_the_line`)
   문자열 grep 이 아니라 **AST 상수/호출**을 본다 — 주석에 남은 옛 문장이 시험을 깨면 다음 사람이 이유를 지운다.
2. **옛 입력 재현** — 거짓 경보를 고칠 때, *그 사고의 입력을 그대로* 넣고 **옛 동작이 경보였다는 사실까지** 고정한다.
   "판정은 옳았고 틀린 건 입력이었다"가 코드에 남아야 한다. (`test_period_boundary_false_alarms_0922.py`)
3. **경계 시험** — 같음(`>=`)·동점·0·`None`·키 없음(옛 형태 결과). 이번에 `50/50` 을 내 가정과 다르게 처리한
   시험 3건이 깨졌다 — **시험이 맞았고 내 가정이 틀렸다.**

## 원칙

- **단언을 약하게 만들거나 지우지 않는다.** 깨지면 먼저 내 가정을 의심한다. 시험을 고쳐야 한다면 더 *강하게* 고친다
  (#44 에서 AST 시험을 두 단계 경로를 다 고정하도록 다시 썼다 — 원래 계약보다 강하다).
- `skip`/`xfail` 로 초록을 만들지 않는다. "flake"는 원인이 아니다.
- 시험 이름은 무엇을 지키는지 말한다 (`test_returning_candidate_does_not_ring_the_phone_again`).
- 시험 docstring 에 **배경(어떤 사고인가)** 을 적는다 — 이 저장소 시험은 사고 기록을 겸한다.
- 운영 파일(`data/`)에 쓰는 시험을 만들지 않는다.

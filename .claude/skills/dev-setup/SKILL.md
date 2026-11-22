---
name: dev-setup
description: 아이기론 로컬 개발 환경 — 백엔드(FastAPI)·웹(Next.js) 실행, 시험, 린트, CI 가 도는 조건, 환경변수 이름. 코드를 처음 만지기 전이나 "어떻게 돌리지?" 할 때 읽는다.
---

# dev-setup

**일은 `epiweather-api/` 와 `epiweather-web/` 에서 한다.** 2026-11-22 개편으로 극지 → 헤임달 → 발할라만 남겼다(복원 기준 커밋 `83406e4`).

| 폴더 | 무엇 | 비고 |
|---|---|---|
| `epiweather-api/` | FastAPI + 스케줄러 + 수집기 + 알고리즘(`algorithms/`) | Python 3.11, 프로덕션은 Railway |
| `epiweather-web/` | Next.js 16.2 · React 19 · Astryx | Vercel(루트 디렉터리 `epiweather-web`) |
| `docs/` | 소킹 일지, 개편 계획 | `docs/아이기론_개편계획_2026-11.md` |

## 백엔드

```bash
cd epiweather-api
pip install -r requirements.txt            # pytest 포함
python3 -m pytest -q                        # 전체 — 마지막 기준 365건, 약 3초
python3 -m pytest tests/test_polar_signals.py -q   # 하나만
EPIWEATHER_SCHEDULER=off uvicorn main:app --port 8000   # 로컬 서버 (프로덕션: Procfile 참고)
```

- **테스트는 바깥 인터넷에 나가지 않는다** (`tests/conftest.py`). 모킹을 빠뜨린 호출은 `ConnectionError` 로 막힌다.
  실제 HTTP 가 필요하면 `@pytest.mark.allow_network` — 지금은 하나도 없다. 남의 API 가 죽어서 우리 CI 가
  빨개지는 일을 막으려는 것이다(CI 가 42분 걸리던 원인이 테스트의 실제 호출 814번이었다).
- **스케줄러는 기본이 켜짐**이다(`EPIWEATHER_SCHEDULER=off` 로 끈다). 로컬 서버를 띄우면 시작하자마자 실제 외부 소스를 두드리니,
  개발 중에는 `EPIWEATHER_SCHEDULER=off uvicorn main:app …` 로 띄운다.
- 로그는 `collector.log()` 로 남긴다 — `Dockerfile` 이 `PYTHONUNBUFFERED=1` 이라야 실시간으로 도착한다.

## CI

`.github/workflows/backend-tests.yml` — `epiweather-api/**` 가 바뀔 때만 `pytest tests/ -v`(py 3.11).
**문서만 바꾸면 백엔드 시험은 안 돈다.** 웹은 Vercel 이 배포 미리보기로 검증한다.

## 웹

```bash
cd epiweather-web
npm ci
npm run dev        # 개발 서버
npm run lint       # eslint
npm run build
npm run test:e2e   # playwright
```

⚠️ **이 Next.js 는 학습 데이터의 그것이 아니다.** `epiweather-web/AGENTS.md` 가 코드를 쓰기 전에
`node_modules/next/dist/docs/` 의 해당 가이드를 읽으라고 한다. 지키라.

## 환경변수 (이름만 — 값은 절대 커밋하지 않는다)

`EPIWEATHER_API_KEY(S)` `ALLOWED_ORIGINS` `ANTHROPIC_API_KEY` `NVIDIA_API_KEY` `AEGIRON_VARIANT_BUILDS`
`EPIWEATHER_SCHEDULER` `EPIWEATHER_OBSERVATION_STORE` · GitHub 시크릿 `TELEGRAM_BOT_TOKEN/OPS_CHAT_ID`(liveness 전용).
키가 없는 소스는 **'값 없음'으로 표시하고 사유를 로그에 남긴다** — 조용히 0 으로 읽지 않는다(`collector-source` 참고).

## 샌드박스 제약

Claude Code 원격 샌드박스는 외부 접속이 허용목록 방식이다. `railway.app` 은 프록시에서 403 이라
**curl 로 프로덕션을 못 부른다** — Railway MCP 로 로그를 읽는다(`prod-observability` 참고).
TLS 검증을 끄거나 `HTTPS_PROXY` 를 해제하지 않는다.

---
name: frontend-web
description: epiweather-web(Next.js 16 / React 19) 작업 규칙 — 이 Next.js 는 학습 데이터와 다르다, 정직 표시(근거·고지·caveat)를 화면에서 잃지 않는 법, Vercel 배포 특성. 웹 코드를 만지기 전에 읽는다.
---

# frontend-web

## 먼저

- **`epiweather-web/AGENTS.md` 를 읽는다.** 이 Next.js(16.2.6)는 API·규약·파일 구조가 다를 수 있으니
  코드를 쓰기 전에 `node_modules/next/dist/docs/` 의 해당 가이드를 읽고 deprecation 을 따르라고 한다.
  (`CLAUDE.md` 는 `@AGENTS.md` 한 줄이다.) 기억으로 쓰지 않는다.
- 스택: React 19 · zustand(상태) · leaflet/react-leaflet(지도). 새 의존성은 이유가 있을 때만.

## 명령

`npm run dev` · `npm run lint`(eslint) · `npm run build` · `npm run test:e2e`(playwright).
PR 전에 `lint` 와 `build` 를 돌린다 — Vercel 이 빌드하지만 실패를 PR 에서 처음 보고 싶지 않다.

## 정직 표시는 화면에서 끝난다

백엔드가 `evidence`·`honesty`·`caveat`·`disclaimer` 를 만들어 내려줘도 **화면이 안 그리면 사람은 못 본다.**
2026-09-20 감사에서 웹은 evidence 20곳·disclaimer 14곳·honesty 5곳·caveat 2곳을 그리는데 텔레그램은 셋 다 안 보냈었다 —
"먼저 도착하는 쪽, 묻지도 않았는데 도착하는 쪽, 스크린샷이 찍히는 쪽"이 폰이다.

- 새 숫자를 화면에 붙일 때 **측정/추정/대리(proxy)** 를 같은 모양으로 그리지 않는다. 사람 수처럼 보이는 외삽값에는
  "측정된 발병 수가 아니라 신호 시계열의 외삽" 고지를 같이 그린다.
- 상태 문구가 관측보다 많은 것을 주장하지 않는다("정상"은 "관측했고 정상"일 때만).
- 값이 없으면 `0` 이 아니라 **'값 없음'/'판정 안 함'** 으로 그린다.
- API 응답의 dict 는 통째로 넘어온다 — 필드가 늘면 화면이 그걸 그리는지 확인한다.

## 배포

Vercel 프로젝트 `epiweather-web`(루트 디렉터리 `epiweather-web`). PR 마다 미리보기가 생긴다.
- **백엔드만 바꾼 PR 의 Vercel 빨강은 그 PR 때문이라는 근거가 없다** — `git diff origin/master...HEAD -- epiweather-web` 로 먼저 본다.
  (#47 의 빨강은 9초 만에 났고 몇 분 뒤 #48 은 초록이었다. 원인은 못 읽었다 — 이 세션의 Vercel 권한으론 로그가 404/403.)
- 미리보기 URL 은 샌드박스에서 403 이라 **프론트 렌더링을 여기서 검증할 수 없다.** 캡틴 눈이 필요한 자리라고 적는다.

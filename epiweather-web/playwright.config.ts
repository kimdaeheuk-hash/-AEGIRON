import { defineConfig, devices } from '@playwright/test';

// 모바일 레이아웃 회귀 방지용 최소 설정.
// 백엔드 없이도 돌아가게 설계(에러 카드 상태도 오버플로우 없이 렌더되어야 함).
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  webServer: {
    command: 'npm run dev -- --port 3099',
    url: 'http://localhost:3099',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  use: {
    baseURL: 'http://localhost:3099',
    // 이 환경엔 핀 고정된 chromium-headless-shell 리비전이 아니라 풀 Chromium
    // 바이너리만 설치돼 있어서 실행 경로를 명시적으로 지정해야 함.
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
      : {},
  },
  projects: [
    {
      // iPhone SE 프리셋은 기본 브라우저가 WebKit인데 이 환경엔 Chromium만
      // 설치돼 있어서, 폭이 비슷한(320px) Android 프리셋으로 대체.
      name: 'mobile-iphone-se',
      use: { ...devices['Galaxy S9+'] }, // 320x658, Chromium 기반
    },
  ],
});

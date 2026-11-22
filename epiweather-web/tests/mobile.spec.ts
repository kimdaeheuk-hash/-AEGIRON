import { test, expect } from '@playwright/test';

// 좁은 화면에서 가로 스크롤이 생기지 않는지 — 개편(2026-11-22) 뒤 남은 화면만 본다.
// 백엔드 연결과 무관하게 통과해야 한다(못 읽은 상태 문구도 넘치지 않아야 하므로).

async function hasHorizontalOverflow(page: import('@playwright/test').Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
}

for (const path of ['/ko', '/ko/polar', '/dashboard']) {
  test(`${path} 는 좁은 뷰포트에서 가로 스크롤이 생기지 않는다`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByText('AEGIRON').first()).toBeVisible();
    expect(await hasHorizontalOverflow(page)).toBe(false);
  });
}

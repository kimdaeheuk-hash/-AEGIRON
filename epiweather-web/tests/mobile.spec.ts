import { test, expect } from '@playwright/test';

// 모바일 좁은 화면에서 레이아웃이 가로로 안 깨지는지(스크롤/카드 잘림 없는지)
// 회귀 방지용. 백엔드 연결 여부와 무관하게 통과해야 함 — 에러 상태 카드도
// 오버플로우 없이 렌더돼야 하므로 백엔드는 띄우지 않고 테스트한다.

async function hasHorizontalOverflow(page: import('@playwright/test').Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
}

test('메인 화면(0단계)은 좁은 뷰포트에서 가로 스크롤이 생기지 않는다', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('역병예보').first()).toBeVisible();
  expect(await hasHorizontalOverflow(page)).toBe(false);
});

test('실시간 대시보드(9단계)로 전환해도 가로 스크롤이 생기지 않는다', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /실시간 대시보드/ }).click();
  // 백엔드가 없으면 에러 카드가 뜨는데, 그 상태에서도 오버플로우가 없어야 함.
  await page.waitForTimeout(1000);
  expect(await hasHorizontalOverflow(page)).toBe(false);
});

test('사이드바 내비게이션이 세로로 쌓여서 전체 폭을 넘지 않는다', async ({ page }) => {
  await page.goto('/');
  const sidenav = page.locator('.sidenav');
  const box = await sidenav.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  if (box && viewport) {
    expect(box.width).toBeLessThanOrEqual(viewport.width);
  }
});

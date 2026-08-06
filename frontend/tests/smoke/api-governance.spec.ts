import { expect, test } from '@playwright/test';

test('api governance page renders and navigation link is present', async ({ page }) => {
  await page.goto('/');

  // Verify the top nav link exists
  const govLink = page.locator('a[href="/api-governance"]').first();
  await expect(govLink).toBeVisible();

  // Navigate to the page and check it loads without a crash
  await page.goto('/api-governance');
  await expect(page).toHaveURL(/api-governance/);

  // The page heading must be visible
  await expect(
    page
      .locator('h1, h2')
      .filter({ hasText: /api governance/i })
      .first()
  ).toBeVisible({
    timeout: 15_000,
  });
});

test('api governance page shows encryption posture section', async ({ page }) => {
  await page.goto('/api-governance');

  // Encryption posture panel must be present (even when backend data is empty)
  await expect(page.locator('text=/encryption posture/i').first()).toBeVisible({ timeout: 15_000 });
});

test('api governance page does not throw a runtime error', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto('/api-governance');

  // Wait for deterministic UI anchors instead of network idle, which can hang with live polling/SSE.
  await expect(
    page
      .locator('h1, h2')
      .filter({ hasText: /api governance/i })
      .first()
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('text=/encryption posture/i').first()).toBeVisible({ timeout: 15_000 });

  // No uncaught errors should have fired
  expect(errors.filter((e) => !/partytown/i.test(e))).toHaveLength(0);
});

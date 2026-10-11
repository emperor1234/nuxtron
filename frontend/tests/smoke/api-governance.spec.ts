import { expect, test } from '@playwright/test';

test('api governance page renders and navigation link is present', async ({ page }) => {
  await page.goto('/dashboard');
  await page.getByRole('button', { name: 'Operations', exact: true }).click();
  await expect(page).toHaveURL(/\/crm$/);
  const govLink = page.getByRole('link', { name: 'API Access', exact: true });
  await expect(govLink).toBeVisible();
  await expect(govLink).toHaveAttribute('href', '/api-governance');

  await govLink.click();
  await expect(page).toHaveURL(/\/api-governance$/);

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

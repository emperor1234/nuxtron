import { expect, test } from '@playwright/test';

const strictLive = process.env.STRICT_LIVE_SOCIAL === '1';

test.describe('Sprout Social strict-live verification', () => {
  test.skip(!strictLive, 'Set STRICT_LIVE_SOCIAL=1 to run strict-live social assertions.');

  test('all best-stack checks pass in strict-live mode', async ({ page }) => {
    test.slow();
    test.setTimeout(120000);

    await page.goto('/seo/sproutsocial-automation');

    await expect(page.getByRole('heading', { name: 'Best-of Stack Coverage Chart' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Sprout Social (ops)' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Lately (AI repurposing)' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Jasper (AI copy)' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Brandwatch (listening intelligence)' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Buffer/Later (visual scheduling)' })).toBeVisible();

    await page.getByRole('button', { name: 'Run Best-Stack Probe' }).click();
    await expect(page.getByRole('heading', { name: 'Best-of Stack Probe Results' })).toBeVisible();

    const failures = page.locator('section.card').filter({ hasText: 'Best-of Stack Probe Results' }).getByText('FAIL');
    await expect(failures).toHaveCount(0);
  });
});

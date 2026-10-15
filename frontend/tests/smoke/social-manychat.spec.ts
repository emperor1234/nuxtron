import { expect, test } from '@playwright/test';

test.describe('Social automation route compatibility', () => {
  test('redirects the retired provider-branded path to customer automation', async ({ page }) => {
    await page.goto('/studio/social-studio/manychat');

    await expect(page).toHaveURL(/\/studio\/social-studio\/automation\/?$/);
    await expect(page.getByRole('heading', { name: 'Automation Engine' })).toBeVisible();
    await expect(page.getByRole('heading', { name: /ManyChat integration/i })).toHaveCount(0);
  });
});

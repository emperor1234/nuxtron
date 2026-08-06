import { expect, test } from '@playwright/test';

test.describe('Social Manychat Workspace', () => {
  test('manychat workspace route renders core UI sections', async ({ page }) => {
    await page.goto('/studio/social-studio/manychat');

    await expect(page.getByRole('heading', { name: 'Manychat Automation Workspace' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Automation Simulation' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Vendor Map' })).toBeVisible();

    await expect(page.getByPlaceholder('Tag name')).toBeVisible();
    await expect(page.getByPlaceholder('@contact_handle')).toBeVisible();
    await expect(page.getByPlaceholder('Incoming message text')).toBeVisible();
  });
});

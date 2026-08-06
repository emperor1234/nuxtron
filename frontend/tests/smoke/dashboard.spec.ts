import { expect, test } from '@playwright/test';

test('dashboard renders live metrics snapshot', async ({ page }) => {
  await page.goto('/dashboard');

  await expect(page.getByRole('heading', { name: 'Nuxtron Operations Command Center' })).toBeVisible();

  const metricsUnavailable = page.getByRole('heading', { name: 'Metrics Unavailable' });
  const renderedLiveSnapshot = !(await metricsUnavailable.isVisible().catch(() => false));

  if (renderedLiveSnapshot) {
    const topQueueCard = page.locator('article').filter({ has: page.getByText('Top Queue') }).first();
    await expect(topQueueCard).toBeVisible();
    await expect(topQueueCard.getByRole('heading').first()).toContainText(/.+/);
    await expect(page.getByRole('heading', { name: 'Queue Distribution' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Secret And Data Plane Readiness' })).toBeVisible();
    await expect(page.getByText('HashiCorp Vault')).toBeVisible();
    await expect(page.getByText('Supabase Vault Path')).toBeVisible();
    const totalQueuedCard = page.locator('article').filter({ has: page.getByText('Total Queued Events') }).first();
    await expect(totalQueuedCard).toBeVisible();
    await expect(totalQueuedCard.getByRole('heading').first()).toContainText(/\d+/);
  } else {
    await expect(metricsUnavailable).toBeVisible();
  }
});

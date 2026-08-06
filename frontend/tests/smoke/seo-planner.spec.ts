import { expect, test, type Page } from '@playwright/test';

const MIN_EXPECTED_MODULE_COUNT = 51;

async function gotoWithRetry(page: Page, url: string): Promise<void> {
  try {
    await page.goto(url);
    return;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes('ERR_ABORTED')) {
      throw error;
    }
    await page.goto(url);
  }
}

test('seo hub and planner pages render', async ({ page }) => {
  test.slow();
  test.setTimeout(120000);
  await gotoWithRetry(page, '/seo');
  await expect(page.getByRole('heading', { name: 'SEO Platform' })).toBeVisible();
  await expect(page.getByTestId('seo-module-card').first()).toBeVisible();
  expect(await page.getByTestId('seo-module-card').count()).toBeGreaterThanOrEqual(MIN_EXPECTED_MODULE_COUNT);
  await expect(page.getByRole('link', { name: 'GTmetrix-Style Performance Audit' })).toBeVisible();

  await gotoWithRetry(page, '/seo/performance');
  await expect(page.getByRole('heading', { name: 'GTmetrix-Style Performance Audit' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run Audit' })).toBeVisible();

  await gotoWithRetry(page, '/seo/planner');
  await expect(page.getByRole('heading', { name: 'SEO Execution Planner' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create Execution Plan' })).toBeVisible();
  await page.getByRole('button', { name: 'All Modules Orchestration' }).click();
  await expect(page.getByRole('button', { name: 'Plan All Modules' })).toBeVisible();

  await gotoWithRetry(page, '/seo/modules/search-monitoring');
  await expect(page).toHaveURL(/\/seo\/modules\/search-monitoring$/);
  await expect(page.locator('h1')).toBeVisible();
});

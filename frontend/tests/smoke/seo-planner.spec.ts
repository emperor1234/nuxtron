import { expect, test, type Page } from '@playwright/test';

const MIN_EXPECTED_TOOL_LINK_COUNT = 38;

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
  await expect(page.getByRole('heading', { name: 'SEO', exact: true })).toBeVisible();
  const toolLinks = page.getByTestId('seo-tool-link');
  await expect(toolLinks.first()).toBeVisible();
  expect(await toolLinks.count()).toBeGreaterThanOrEqual(
    MIN_EXPECTED_TOOL_LINK_COUNT,
  );
  await expect(page.getByRole('link', { name: 'Top Pages', exact: true })).toHaveAttribute(
    'href',
    '/seo/performance',
  );

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

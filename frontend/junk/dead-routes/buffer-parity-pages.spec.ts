import { expect, test } from '@playwright/test';

async function gotoWithRetry(page: import('@playwright/test').Page, path: string): Promise<void> {
  try {
    await page.goto(path, { waitUntil: 'commit' });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes('net::ERR_CONNECTION_RESET') && !message.includes('net::ERR_ABORTED')) {
      throw error;
    }
    await page.goto(path, { waitUntil: 'commit' });
  }
}

test.describe('Buffer parity pages', () => {
  test('buffer create page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-create');
    await expect(page.getByRole('heading', { name: 'Create' })).toBeVisible();
    await expect(page.getByRole('button', { name: '+ New Idea' })).toBeVisible();
  });

  test('buffer publish page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-publish');
    await expect(page.getByRole('heading', { name: 'Publish' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Schedules' })).toBeVisible();
  });

  test('buffer community page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-community');
    await expect(page.getByRole('heading', { name: 'Community' })).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
  });

  test('buffer analyze page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-analyze');
    await expect(page.getByRole('heading', { name: 'Analyze' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate report' })).toBeVisible();
  });

  test('buffer collaborate page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-collaborate');
    await expect(page.getByRole('heading', { name: 'Collaborate' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'name@company.com' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Send invite' })).toBeVisible();
  });

  test('buffer startpage loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/buffer-startpage');
    await expect(page.getByRole('heading', { name: 'Start Page' })).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
  });
});

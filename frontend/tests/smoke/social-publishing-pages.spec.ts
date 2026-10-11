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

test.describe('Social publishing pages', () => {
  test('ideas and drafts page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/studio/social-studio/ideas');
    await expect(page.getByRole('heading', { name: 'Ideas & Drafts' })).toBeVisible();
    await expect(page.getByRole('button', { name: '+ New Idea' })).toBeVisible();
  });

  test('publishing queue page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/studio/social-studio/queue');
    await expect(page.getByRole('heading', { name: 'Publishing Queue' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Schedules' })).toBeVisible();
  });

  test('comment replies page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/studio/social-studio/community');
    await expect(page.getByRole('heading', { name: 'Comment Replies' })).toBeVisible();
  });

  test('audience insights page loads', async ({ page }) => {
    test.setTimeout(45000);
    await gotoWithRetry(page, '/studio/social-studio/audience');
    await expect(page.getByRole('heading', { name: 'Audience Insights' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate report' })).toBeVisible();
  });

  test('old vendor-named URLs redirect to the renamed pages', async ({ page }) => {
    test.setTimeout(60000);
    for (const [from, to] of [
      ['/buffer-create', '/studio/social-studio/ideas'],
      ['/buffer-publish', '/studio/social-studio/queue'],
      ['/buffer-collaborate', '/studio/team'],
      ['/buffer-startpage', '/studio/social-studio/link-in-bio'],
      ['/studio/lately/brand-voice', '/studio/content-hub/brand-voice'],
    ]) {
      await gotoWithRetry(page, from);
      await expect(page).toHaveURL(new RegExp(`${to}$`));
    }
  });
});

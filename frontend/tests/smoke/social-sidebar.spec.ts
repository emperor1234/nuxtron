import { expect, test, type Page } from '@playwright/test';

async function mockEmptySmartInboxApi(page: Page) {
  await page.route('**/api/fastapi/social/inbox**', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    });
  });
}

test.describe('Social Sidebar Navigation', () => {
  test('social command center links are visible from the sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('button', { name: 'Social' }).click();

    for (const label of [
      'Post Scheduler',
      'Content Calendar',
      'Publishing Queue',
      'Smart Inbox',
      'Review Management',
      'Analytics & KPIs',
      'Social Listening',
      'Paid Social Ads',
      'Employee Advocacy',
      'Comment Replies',
      'Audience Insights',
    ]) {
      await expect(page.getByRole('link', { name: label, exact: true })).toBeVisible();
    }
  });

  test('social sidebar content calendar link navigates to working studio route', async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto('/dashboard');
    await page.getByRole('button', { name: 'Social' }).click();
    await expect(page).toHaveURL(/\/studio\/social-studio$/, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: 'Social Studio', exact: true })).toBeVisible({ timeout: 60_000 });

    await page.getByRole('link', { name: 'Content Calendar' }).click();
    await expect(page).toHaveURL(/\/studio\/social-studio\/calendar$/, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: 'Content Calendar' })).toBeVisible({ timeout: 60_000 });
  });

  test('social sidebar smart inbox link navigates to working studio route', async ({ page }) => {
    test.setTimeout(120_000);
    await mockEmptySmartInboxApi(page);
    const inboxErrors: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error' && /Failed to load inbox/.test(message.text())) {
        inboxErrors.push(message.text());
      }
    });
    await page.goto('/dashboard');
    await page.getByRole('button', { name: 'Social' }).click();
    await expect(page).toHaveURL(/\/studio\/social-studio$/, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: 'Social Studio', exact: true })).toBeVisible({ timeout: 60_000 });

    const smartInboxLink = page.locator('a[href="/studio/social-studio/inbox"]').filter({ hasText: 'Smart Inbox' }).first();

    await expect(smartInboxLink).toBeVisible();
    await smartInboxLink.click();
    await expect(page).toHaveURL(/\/studio\/social-studio\/inbox$/, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: 'Smart Inbox' })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText('Loading inbox…')).toHaveCount(0);
    await expect(page.getByText(/Inbox backend unavailable/)).toHaveCount(0);
    expect(inboxErrors).toEqual([]);
  });

  test('A/B Testing sidebar link deep-links panel in social studio', async ({ page }) => {
    await page.goto('/studio/social-studio?panel=ab-testing');
    await expect(page).toHaveURL(/\/studio\/social-studio\?panel=ab-testing$/);
    await expect(page.getByRole('heading', { name: 'A/B Testing Lab' })).toBeVisible();
  });
});

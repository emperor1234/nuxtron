import { expect, test } from '@playwright/test';

test.describe('Social Sidebar Navigation', () => {
  test('social command center links are visible from the sidebar', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page.getByRole('link', { name: 'Reputation Management' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Brand Monitoring' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Crisis Management' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Review Management' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Market Research' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Audience Insights' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Product Research' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Trend Research' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Competitive Analysis' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Media Management' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Media Analytics' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Media Scheduling' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Media ROI Tracking' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Employee Advocacy' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Engagement and Inbox' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately AI Hub' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately Brand Voice DNA' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately Content Repurposer' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately Keyword Intelligence' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately A/B Testing' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately ROI Forecaster' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lately Brand Hierarchy' })).toBeVisible();

    await expect(page.getByRole('link', { name: 'Social Command Hub' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Connected Accounts' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Publishing Queue' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Content Calendar', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Smart Inbox' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Listening' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Social Analytics' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Reviews & Reputation' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Executive Reports' })).toBeVisible();

    await expect(page.getByRole('link', { name: 'Predis A/B Testing Lab' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Copy Generator' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Content Calendar' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Brand Kit Studio' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Voiceover Lab' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Performance AI' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Animation FX' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Competitor Intel' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Bulk Generator' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Meme Factory' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Quote Studio' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Holiday Posts' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Ecommerce Posts' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis Asset Library' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predis AI Ideation Chat' })).toBeVisible();
  });

  test('social sidebar content calendar link navigates to working studio route', async ({ page }) => {
    await page.goto('/dashboard');

    await page.getByRole('link', { name: 'Content Calendar', exact: true }).click();
    await expect(page).toHaveURL(/\/studio\/social-calendar$/);
    await expect(page.getByRole('link', { name: /back to hub/i })).toBeVisible();
  });

  test('social sidebar smart inbox link navigates to working studio route', async ({ page }) => {
    await page.goto('/dashboard');

    const smartInboxLink = page.locator('a[href="/studio/social-inbox"]').filter({ hasText: 'Smart Inbox' }).first();

    await expect(smartInboxLink).toBeVisible();
    await smartInboxLink.click();
    await expect(page).toHaveURL(/\/studio\/social-inbox$/);
    await expect(page.getByRole('heading', { name: 'Smart Inbox' })).toBeVisible();
  });

  test('Predis A/B Testing sidebar link deep-links panel in social studio', async ({ page }) => {
    await page.goto('/studio/social-studio?panel=ab-testing');
    await expect(page).toHaveURL(/\/studio\/social-studio\?panel=ab-testing$/);
    await expect(page.getByRole('heading', { name: 'Predis A/B Testing Lab' })).toBeVisible();
  });
});

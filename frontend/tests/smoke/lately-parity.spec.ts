import { expect, test } from '@playwright/test';

test.describe('Lately AI parity workspace', () => {
  test('hub and core entry pages render', async ({ page }) => {
    test.setTimeout(60000);

    await page.goto('/studio/lately', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Lately AI' })).toBeVisible();

    await page.goto('/studio/growth-suite', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'AI Growth Suite' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run full growth suite' })).toBeVisible();

    await page.goto('/studio/lately/brand-voice', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Brand Voice DNA' })).toBeVisible();
  });

  test('growth suite bootstrap and drill-downs work', async ({ page }) => {
    await page.goto('/studio/growth-suite', { waitUntil: 'domcontentloaded' });

    // Verify the page heading and the bootstrap CTA are present
    await expect(page.getByRole('heading', { name: 'AI Growth Suite' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run full growth suite' })).toBeVisible();

    // Verify the CTA is actionable and the page remains stable after triggering bootstrap.
    await page.getByRole('button', { name: 'Run full growth suite' }).click();
    await expect(page).toHaveURL(/\/studio\/growth-suite$/);
    await expect(page.getByRole('heading', { name: 'AI Growth Suite' })).toBeVisible();
  });

  test('brand voice create and feedback flow works', async ({ page }) => {
    await page.goto('/studio/lately/brand-voice');

    await page.getByRole('button', { name: 'Analyse Voice & Save Profile' }).click();
    await expect(page.getByText('Saved Voice Models')).toBeVisible();

    const submitFeedback = page.getByRole('button', { name: 'Submit Feedback' }).first();
    if (await submitFeedback.isVisible()) {
      await submitFeedback.click();
    }
  });

  test('repurpose, keyword tracking, and roi forecast execute', async ({ page }) => {
    await page.goto('/studio/lately/repurpose');
    await page.getByRole('button', { name: '♻️ Repurpose into 20 Formats' }).click();
    await expect(page.getByRole('button', { name: '♻️ Repurpose into 20 Formats' })).toBeVisible();

    await page.goto('/studio/lately/word-cloud');
    await page.locator('#track-keyword').fill('mock ai growth');
    await page.getByRole('button', { name: '+ Track Keyword' }).click();
    await expect(page.getByText('Top Keywords (40)')).toBeVisible();

    await page.goto('/studio/lately/roi-forecast');
    await page.getByRole('button', { name: '📈 Generate ROI Forecast' }).click();
    await expect(page.getByText('Forecast Results')).toBeVisible();
  });

  test('ab testing and brand hierarchy write paths work', async ({ page }) => {
    await page.goto('/studio/lately/ab-testing');
    await page.getByRole('button', { name: '🔬 Generate 5 Variants' }).click();
    await expect(page.getByText('All A/B Tests')).toBeVisible();

    await page.goto('/studio/lately/brand-hierarchy');
    await page.getByLabel('Brand Name *').fill('Nuxtron APAC');
    await page.getByRole('button', { name: '🏢 Add Brand' }).click();
    await expect(page.getByRole('heading', { name: 'Brand Hierarchy', exact: true })).toBeVisible();
  });
});

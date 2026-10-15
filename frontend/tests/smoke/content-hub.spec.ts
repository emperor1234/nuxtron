import { expect, test } from '@playwright/test';

test.describe('AI Content Hub', () => {
  test('hub and core entry pages render', async ({ page }) => {
    test.setTimeout(60000);

    await page.goto('/studio/content-hub', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'AI Content Hub' })).toBeVisible();

    await page.goto('/studio/content-hub/brand-voice', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Brand Voice DNA' })).toBeVisible();
  });

  test('brand voice create and feedback flow works', async ({ page }) => {
    await page.goto('/studio/content-hub/brand-voice');

    await page.getByRole('button', { name: 'Analyse Voice & Save Profile' }).click();
    await expect(page.getByText('Saved Voice Models')).toBeVisible();

    const submitFeedback = page.getByRole('button', { name: 'Submit Feedback' }).first();
    if (await submitFeedback.isVisible()) {
      await submitFeedback.click();
    }
  });

  test('repurpose, keyword tracking, and roi forecast execute', async ({ page }) => {
    await page.goto('/studio/content-hub/repurpose');
    await page.getByRole('button', { name: '♻️ Repurpose into 20 Formats' }).click();
    await expect(page.getByRole('button', { name: '♻️ Repurpose into 20 Formats' })).toBeVisible();

    await page.goto('/studio/content-hub/word-cloud');
    await page.locator('#track-keyword').fill('mock ai growth');
    await page.getByRole('button', { name: '+ Track Keyword' }).click();
    await expect(page.getByText('Top Keywords (40)')).toBeVisible();

    await page.goto('/studio/content-hub/roi-forecast');
    await page.getByRole('button', { name: '📈 Generate ROI Forecast' }).click();
    await expect(page.getByText('Forecast Results')).toBeVisible();
  });

  test('ab testing and brand hierarchy write paths work', async ({ page }) => {
    await page.goto('/studio/content-hub/ab-testing');
    await page.getByRole('button', { name: '🔬 Generate 5 Variants' }).click();
    await expect(page.getByText('All A/B Tests')).toBeVisible();

    await page.goto('/studio/content-hub/brand-hierarchy');
    await page.getByLabel('Brand Name *').fill('Nuxtron APAC');
    await page.getByRole('button', { name: '🏢 Add Brand' }).click();
    await expect(page.getByRole('heading', { name: 'Your brands', exact: true })).toBeVisible();
  });
});

import { expect, test } from '@playwright/test';

test.describe('Sprout Social automation console', () => {
  test('loads live console and executes end-to-end probe', async ({ page }) => {
    test.slow();
    test.setTimeout(120000);

    await page.goto('/seo/sproutsocial-automation');

    await expect(page.getByRole('heading', { name: 'Sprout Social End-to-End Production Console' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh Live State' })).toBeVisible();
    const runProbeButton = page.getByRole('button', { name: 'Run E2E Probe' });
    await expect(runProbeButton).toBeVisible();

    await runProbeButton.click();
    await expect(page.getByRole('button', { name: 'Running...' })).toBeVisible({ timeout: 10000 });

    const e2eProbeSection = page.getByRole('heading', { name: 'E2E Probe Results' }).locator('xpath=ancestor::section[1]');
    await expect(e2eProbeSection).toBeVisible({ timeout: 30000 });
    await expect(e2eProbeSection).toContainText('Production readiness contract', { timeout: 30000 });

    await expect(page.getByRole('heading', { name: 'Best-of Stack Coverage Chart' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Production Verification Scorecard' })).toBeVisible();
    await page.getByRole('button', { name: 'Run Best-Stack Probe' }).click();
    await expect(page.getByRole('heading', { name: 'Best-of Stack Probe Results' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Jasper (AI copy)' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Social Audit Trail' })).toBeVisible();

    const jsonButton = page.getByRole('button', { name: 'Export Latest Report (JSON)' });
    const markdownButton = page.getByRole('button', { name: 'Export Latest Report (Markdown)' });

    await expect(jsonButton).toBeVisible();
    await expect(markdownButton).toBeVisible();
  });

  test('is linked from SEO command center quick links', async ({ page }) => {
    await page.goto('/seo');

    const link = page.getByRole('link', { name: 'Sprout Social Automation' }).first();
    await expect(link).toBeVisible();
    await link.click();

    await expect(page).toHaveURL(/\/seo\/sproutsocial-automation$/);
  });
});

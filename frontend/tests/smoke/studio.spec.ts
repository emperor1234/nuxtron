import { expect, test } from '@playwright/test';

test('studio hub exposes curated creation workspaces', async ({ page }) => {
  await page.goto('/studio');

  const main = page.locator('main');
  await expect(main.getByRole('heading', { name: 'Studio', exact: true })).toBeVisible();
  await expect(main.getByRole('heading', { name: 'Create' })).toBeVisible();
  await expect(main.getByRole('link', { name: /Editor/ }).first()).toBeVisible();
  await expect(main.getByRole('link', { name: /Image Studio/ }).first()).toBeVisible();
  await expect(main.getByRole('link', { name: /Short Video Factory/ }).first()).toBeVisible();
});

test('studio editor library flow supports insert, layers, and history', async ({ page }) => {
  await page.goto('/studio/editor');
  await page.waitForLoadState('domcontentloaded');

  await expect(page.getByRole('heading', { name: 'Content Library' })).toBeVisible();
  await page.goto('/studio/editor?view=editor&template=blank');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('.editor-workspace-modern')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('button', { name: 'Back to Library' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.canvas-stage').getByRole('heading', { name: 'BLACK FRIDAY' })).toBeVisible();

  await page.getByRole('button', { name: 'Buttons' }).click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toBeVisible();

  await page.getByRole('button', { name: 'Layers' }).click();
  const ctaLayerRow = page.locator('.editor-stack-item:visible', {
    has: page.getByRole('button', { name: 'CTA button' }),
  });
  await expect(ctaLayerRow).toBeVisible();
  const visibilityToggle = ctaLayerRow.locator('.layer-visibility-pill');
  await visibilityToggle.click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toHaveCount(0);
  await visibilityToggle.click();
  await expect(page.locator('.canvas-stage').getByText('Shop Now')).toBeVisible();

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Added CTA button')).toBeVisible();
  await expect(page.getByText('Hidden CTA button')).toBeVisible();
  await expect(page.getByText('Showed CTA button')).toBeVisible();
});

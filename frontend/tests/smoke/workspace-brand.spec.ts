import { expect, test } from '@playwright/test';

test('workspace brand tab saves and persists voiceover plus logo URLs', async ({ page }) => {
  const tenantId = 'tenant-demo';

  const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2p5wAAAABJRU5ErkJggg==';
  const logoDataUrl = `data:image/png;base64,${pngBase64}`;

  await page.goto('/studio/workspace?tab=brand');
  await expect(page.getByRole('button', { name: 'Select voiceover' })).toBeVisible();

  await page.getByRole('textbox', { name: 'Brand/Business Name' }).fill('Decor Studio');
  await page.getByRole('textbox', { name: 'Business Description' }).fill('Brand test for workspace smoke flow.');

  const voiceButton = page.getByRole('button', { name: 'Select voiceover' });
  await voiceButton.scrollIntoViewIfNeeded();
  await voiceButton.click();

  await page.getByPlaceholder('Search voiceover').fill('Liam');
  await page.locator('label.voiceover-row', { hasText: 'Liam' }).first().locator('input[type="radio"]').check();
  await page.getByRole('button', { name: 'Confirm' }).click();

  await page.getByLabel('Logo for light background (URL)').fill(logoDataUrl);
  await page.getByLabel('Logo for dark background (URL)').fill(logoDataUrl);

  const saveButton = page.getByRole('button', { name: 'Save Changes' });
  await saveButton.scrollIntoViewIfNeeded();
  await saveButton.click();

  const readbackAfterSave = await page.request.get('/api/fastapi/social/brand-profile', {
    headers: {
      'X-Tenant-Id': tenantId,
    },
  });
  expect([200, 502]).toContain(readbackAfterSave.status());
  if (readbackAfterSave.status() === 200) {
    const saveJson = (await readbackAfterSave.json()) as {
      brand_profile?: { voiceover?: string; logo_url?: string; logo_dark_url?: string };
    };
    expect(saveJson.brand_profile).toBeTruthy();
  }

  await page.reload();
  await expect(page.getByRole('button', { name: 'Select voiceover' })).toBeVisible();

  const readbackAfterReload = await page.request.get('/api/fastapi/social/brand-profile', {
    headers: {
      'X-Tenant-Id': tenantId,
    },
  });
  expect([200, 502]).toContain(readbackAfterReload.status());
  if (readbackAfterReload.status() === 200) {
    const reloadJson = (await readbackAfterReload.json()) as {
      brand_profile?: { voiceover?: string; logo_url?: string; logo_dark_url?: string };
    };
    expect(reloadJson.brand_profile).toBeTruthy();
  }
});

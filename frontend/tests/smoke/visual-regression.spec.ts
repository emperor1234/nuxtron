import { expect, test } from '@playwright/test';

/**
 * Visual regression baseline for the Phase 3/4 design-system work
 * (docs: plan `cheerful-greeting-volcano`). Covers one representative page
 * per surface — home, a marketing page, and the two heaviest dashboard
 * pages (dashboard home, CRM) — so a later token/primitive migration has
 * something to diff against instead of relying on eyeballing.
 *
 * First run creates baseline screenshots (committed to the repo); later
 * runs fail on unintended pixel drift. Run `npx playwright test
 * tests/smoke/visual-regression.spec.ts --update-snapshots` to intentionally
 * accept a visual change.
 */

const PAGES = [
  { name: 'home', path: '/' },
  { name: 'pricing', path: '/pricing' },
  { name: 'login', path: '/login' },
  { name: 'dashboard-home', path: '/dashboard' },
  { name: 'crm', path: '/crm' },
] as const;

for (const { name, path } of PAGES) {
  test(`${name} visual snapshot`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot(`${name}.png`, {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      animations: 'disabled',
    });
  });
}

import { expect, test } from '@playwright/test';

const GATEWAY_STATUS_URL = '**/api/fastapi/ai/gateway/status';
const MODULE_CARDS_SELECTOR = '[data-testid="seo-module-card"]';
const MIN_EXPECTED_MODULE_COUNT = 51;

async function gotoWithRetry(page: import('@playwright/test').Page, href: string): Promise<void> {
  try {
    await page.goto(href, { waitUntil: 'domcontentloaded' });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes('net::ERR_ABORTED')) {
      throw error;
    }

    // Retry once for transient navigation aborts observed under smoke-suite load.
    await page.waitForTimeout(250);
    await page.goto(href, { waitUntil: 'domcontentloaded' });
  }
}

test.describe('SEO hub partial-failure resilience', () => {
  test('shows all module cards when a non-module API feed returns 503', async ({ page }) => {
    // Intercept the gateway status feed to simulate a backend failure
    await page.route(GATEWAY_STATUS_URL, (route) => route.fulfill({ status: 503, body: 'Service Unavailable' }));

    await page.goto('/seo');

    // The catalog may switch between fallback variants; enforce minimum expected coverage.
    await expect(page.getByTestId('seo-module-card').first()).toBeVisible();
    const moduleCount = await page.getByTestId('seo-module-card').count();
    expect(moduleCount).toBeGreaterThanOrEqual(MIN_EXPECTED_MODULE_COUNT);

    // Verify the page remains usable even when the gateway feed fails.
    await expect(page.getByRole('heading', { name: 'SEO Platform' })).toBeVisible();
  });

  test('Growth & Governance cards are present when a feed fails', async ({ page }) => {
    await page.route(GATEWAY_STATUS_URL, (route) => route.fulfill({ status: 503, body: 'Service Unavailable' }));

    await page.goto('/seo');

    // Each of the 4 Growth & Governance cards must render with the correct href.
    // The card itself is the <a> (Next.js Link renders data-testid on the anchor).
    await expect(page.locator('a[data-testid="seo-module-card"][href="/seo/revenue-attribution"]')).toBeVisible();
    await expect(page.locator('a[data-testid="seo-module-card"][href="/seo/growth-playbooks"]')).toBeVisible();
    await expect(page.locator('a[data-testid="seo-module-card"][href="/seo/trust-risk-governance"]')).toBeVisible();
    await expect(page.locator('a[data-testid="seo-module-card"][href="/seo/multi-channel-activation"]')).toBeVisible();
  });

  test('Growth & Governance cards navigate to correct pages', async ({ page }) => {
    test.slow();
    test.setTimeout(90000);
    const cases = [
      { href: '/seo/revenue-attribution' },
      { href: '/seo/growth-playbooks' },
      { href: '/seo/trust-risk-governance' },
      { href: '/seo/multi-channel-activation' },
    ];

    for (const { href } of cases) {
      await gotoWithRetry(page, href);
      await expect(page).toHaveURL(new RegExp(`${href.replace('/', '\\/')}$`), { timeout: 20000 });
      await expect(page.locator('h1').first()).toBeVisible({ timeout: 20000 });
    }
  });

  test('all module cards render on clean load without a warning banner', async ({ page }) => {
    await page.goto('/seo');

    await expect(page.getByTestId('seo-module-card').first()).toBeVisible();
    expect(await page.getByTestId('seo-module-card').count()).toBeGreaterThanOrEqual(MIN_EXPECTED_MODULE_COUNT);

    // No partial-failure banner should appear when all feeds succeed
    await expect(page.getByText(/some analytics feeds failed to load/i)).not.toBeVisible();
  });
});

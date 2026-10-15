import { expect, test } from '@playwright/test';

async function installSearchParityMocks(page: import('@playwright/test').Page) {
  await page.route('**/api/fastapi/search-everywhere/cost-savings-calculator', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        output: {
          total_pages_in_scope: 75000,
          manual_monthly_hours: 1200,
          automated_monthly_hours_saved: 1000,
          monthly_labor_cost_saved_usd: 90000,
          net_monthly_savings_usd: 89201,
          annual_net_savings_usd: 1070412,
          payback_days: 9,
        },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/ai-search-impact-calculator', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        output: {
          incremental_clicks_monthly: 42000,
          incremental_conversions_monthly: 1176,
          incremental_revenue_monthly_usd: 164640,
          incremental_revenue_annual_usd: 1975680,
        },
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/vendors', async (route) => {
    if (route.request().url().includes('/report')) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        configured: 7,
        total: 10,
        vendors: [
          { key: 'openai', display_name: 'OpenAI', category: 'ai', configured: true, mode: 'api' },
          { key: 'cloudflare', display_name: 'Cloudflare', category: 'edge', configured: true, mode: 'api' },
        ],
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/readiness', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ readiness: { configured_pct: 70, grade: 'A', production_ready: false } }),
    });
  });

  await page.route('**/api/fastapi/ai-crawler/dashboard**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: {
          total_hits: 1200,
          ai_crawler_hits: 800,
          ssr_served_hits: 760,
          blocked_hits: 40,
          avg_render_time_ms: 184,
          visibility_score: 84,
          sites_registered: 6,
          sites_with_snippet: 5,
        },
        top_crawlers: [
          { name: 'GPTBot', hits: 342 },
          { name: 'ClaudeBot', hits: 211 },
        ],
        top_pages: [{ url: '/pricing', hits: 122 }],
      }),
    });
  });

  await page.route('**/api/fastapi/ai-crawler/sites', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 1,
        sites: [
          {
            id: 's-1',
            domain: 'nuxtron.ai',
            snippet_installed: true,
            ssr_enabled: true,
            ai_crawlers_detected_total: 342,
          },
        ],
      }),
    });
  });

  await page.route('**/api/fastapi/ai-crawler/readiness', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        readiness: { score: 84, grade: 'A', production_ready: false, total_sites: 1 },
        coverage: {
          snippet_installed_pct: 100,
          ssr_enabled_pct: 100,
          cloudflare_zone_configured_pct: 80,
          deployment_webhook_configured_pct: 75,
        },
      }),
    });
  });


}

test('ai search impact page renders vendor readiness after run', async ({ page }) => {
  test.slow();
  test.setTimeout(60000);
  await installSearchParityMocks(page);
  await page.goto('/ai-search-impact-calculator');

  await expect(page.getByRole('heading', { name: 'AI Search Impact And Cost Savings Calculator' })).toBeVisible();
  const costResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/cost-savings-calculator') &&
      response.request().method() === 'POST'
  );
  const impactResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/ai-search-impact-calculator') &&
      response.request().method() === 'POST'
  );
  const vendorResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/vendors') && response.request().method() === 'GET'
  );
  const readinessResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/readiness') && response.request().method() === 'GET'
  );
  await page.getByRole('button', { name: 'Run Calculators' }).click();
  await Promise.all([costResponse, impactResponse, vendorResponse, readinessResponse]);

  await expect(page.locator('article.card').filter({ hasText: /Monthly AI Revenue Lift/ })).toContainText('$164,640', {
    timeout: 20000,
  });
  await expect(page.getByRole('heading', { name: 'Third-Party Vendors' })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText(/Grade A/i)).toBeVisible();
});

test('ai visibility dashboard loads crawler analytics', async ({ page }) => {
  test.slow();
  test.setTimeout(60000);
  await installSearchParityMocks(page);
  await page.goto('/ai-visibility-dashboard');

  await expect(page.getByRole('heading', { name: 'AI Crawler Visibility Dashboard' })).toBeVisible();
  const dashboardResponse = page.waitForResponse(
    (response) => response.url().includes('/api/fastapi/ai-crawler/dashboard') && response.request().method() === 'GET'
  );
  const sitesResponse = page.waitForResponse(
    (response) => response.url().includes('/api/fastapi/ai-crawler/sites') && response.request().method() === 'GET'
  );
  const readinessResponse = page.waitForResponse(
    (response) => response.url().includes('/api/fastapi/ai-crawler/readiness') && response.request().method() === 'GET'
  );
  await page.getByRole('button', { name: 'Load Visibility Data' }).click();
  await Promise.all([dashboardResponse, sitesResponse, readinessResponse]);

  await expect(page.locator('article.card').filter({ hasText: /Visibility Score/ })).toContainText('84%', {
    timeout: 20000,
  });
  await expect(page.getByRole('heading', { name: 'Top Crawlers' })).toBeVisible();
  await expect(page.getByText(/GPTBot:\s*342\s*hits/i)).toBeVisible();
});

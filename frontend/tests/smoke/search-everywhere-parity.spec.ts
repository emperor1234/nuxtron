import { expect, test } from '@playwright/test';

async function gotoSeoHub(page: import('@playwright/test').Page): Promise<void> {
  try {
    await page.goto('/seo', { waitUntil: 'domcontentloaded' });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes('net::ERR_ABORTED')) {
      throw error;
    }
    await page.goto('/seo', { waitUntil: 'domcontentloaded' });
  }
}

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

  await page.route('**/api/fastapi/search-everywhere/vendors/report/export?format=csv**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        format: 'csv',
        count: 2,
        filename: `vendor-inventory-report-${Date.now()}.csv`,
        csv: 'source,vendor,category,integration,configured_units,total_units,runtime_dependency\nsearch_everywhere,Cloudflare,edge,bot_allowlisting,1,1,true',
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/vendors/report/export?format=json**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        format: 'json',
        count: 2,
        filename: `vendor-inventory-report-${Date.now()}.json`,
        json: [
          {
            source: 'search_everywhere',
            vendor: 'Cloudflare',
            category: 'edge',
            integration: 'bot_allowlisting',
            configured_units: 1,
            total_units: 1,
            runtime_dependency: true,
          },
        ],
      }),
    });
  });

  await page.route('**/api/fastapi/search-everywhere/vendors/report', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        summary: { domains: 4, vendors: 6, categories: 3 },
        domain_chart: [{ domain: 'search_everywhere', configured_units: 6, total_units: 8, coverage_pct: 75 }],
        category_chart: [{ category: 'edge', vendors: 2, configured_units: 2, total_units: 2 }],
        vendor_chart: [
          {
            source: 'search_everywhere',
            vendor: 'Cloudflare',
            category: 'edge',
            integration: 'bot_allowlisting',
            configured_units: 1,
            total_units: 1,
            runtime_dependency: true,
          },
          {
            source: 'search_everywhere',
            vendor: 'OpenAI',
            category: 'ai',
            integration: 'llm_inference',
            configured_units: 1,
            total_units: 1,
            runtime_dependency: true,
          },
        ],
        export_rows: [
          {
            source: 'search_everywhere',
            vendor: 'Cloudflare',
            category: 'edge',
            integration: 'bot_allowlisting',
            configured_units: 1,
            total_units: 1,
            runtime_dependency: true,
          },
        ],
      }),
    });
  });
}

test('cost saving calculator page runs and renders savings KPIs', async ({ page }) => {
  test.slow();
  test.setTimeout(60000);
  await installSearchParityMocks(page);
  await page.goto('/cost-saving-calculator');

  await expect(page.getByRole('heading', { name: 'SEO Automation Cost Saving Calculator' })).toBeVisible();
  const runButton = page.getByRole('button', { name: 'Run Cost Saving Model' });
  const pagesInScopeHeading = page.getByRole('heading', { name: 'Pages In Scope' });
  const modelResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/fastapi/search-everywhere/cost-savings-calculator') &&
      response.request().method() === 'POST'
  );
  await runButton.click();
  await modelResponse;
  if (!(await pagesInScopeHeading.isVisible())) {
    await runButton.click();
  }

  await expect(pagesInScopeHeading).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('75,000')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Net Annual Savings' })).toBeVisible();
});

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

test('vendor inventory report renders unified vendor coverage', async ({ page }) => {
  await installSearchParityMocks(page);
  await page.goto('/vendor-inventory-report');

  await expect(page.getByRole('heading', { name: 'Unified Third-Party Vendor Report' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Domain Coverage' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Unified Vendor Chart' })).toBeVisible();
  await expect(page.getByText('Cloudflare').first()).toBeVisible();
  await expect(page.getByText('OpenAI').first()).toBeVisible();
  await expect(page.getByText('bot_allowlisting').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Refresh Report' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Copy JSON' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Download JSON' })).toBeVisible();
  const jsonDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download JSON' }).click();
  const jsonDownload = await jsonDownloadPromise;
  expect(jsonDownload.suggestedFilename()).toContain('vendor-inventory-report-');
  expect(jsonDownload.suggestedFilename()).toContain('.json');

  const csvDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download CSV' }).click();
  const csvDownload = await csvDownloadPromise;
  expect(csvDownload.suggestedFilename()).toContain('vendor-inventory-report-');
  expect(csvDownload.suggestedFilename()).toContain('.csv');
});

test('vendor inventory report is discoverable from features and footer navigation', async ({ page }) => {
  await installSearchParityMocks(page);
  await page.goto('/features');

  await expect(page.getByRole('heading', { name: 'Autonomous AI Features For Social, Ads, And SEO' })).toBeVisible();

  await page.locator('a.feature-card').filter({ hasText: 'Vendor Inventory Report' }).click();
  await expect(page).toHaveURL(/\/vendor-inventory-report$/);
  await expect(page.getByRole('heading', { name: 'Unified Third-Party Vendor Report' })).toBeVisible();

  await page.goto('/features');
  await page.locator('footer').getByRole('link', { name: 'Vendor Inventory Report' }).click();
  await expect(page).toHaveURL(/\/vendor-inventory-report$/);
  await expect(page.getByRole('heading', { name: 'Unified Third-Party Vendor Report' })).toBeVisible();
});

test('botify quick links are visible on seo hub and navigate to Botify pages', async ({ page }) => {
  test.slow();
  test.setTimeout(90000);
  await page.goto('/seo');

  await expect(page.getByRole('heading', { name: 'Botify Command Center' })).toBeVisible();

  const readinessLink = page.locator('a[href="/seo/botify-readiness"]').first();
  await expect(readinessLink).toBeVisible();
  await expect(readinessLink).toHaveAttribute('href', '/seo/botify-readiness');
  await page.goto('/seo/botify-readiness');
  await expect(page).toHaveURL(/\/seo\/botify-readiness$/);
  await expect(page.getByRole('heading', { name: 'Botify End-to-End Readiness Hub' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'Botify Command Center' })).toBeVisible();
  const automationLink = page.locator('a[href="/seo/botify-automation"]').first();
  await expect(automationLink).toBeVisible();
  await expect(automationLink).toHaveAttribute('href', '/seo/botify-automation');
  await page.goto('/seo/botify-automation');
  await expect(page).toHaveURL(/\/seo\/botify-automation$/);
  await expect(page.getByRole('heading', { name: 'Botify Run And Schedule Control' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'Botify Command Center' })).toBeVisible();
  const integrationsLink = page.locator('a[href="/seo/botify-integrations"]').first();
  await expect(integrationsLink).toBeVisible();
  await expect(integrationsLink).toHaveAttribute('href', '/seo/botify-integrations');
  await page.goto('/seo/botify-integrations');
  await expect(page).toHaveURL(/\/seo\/botify-integrations$/);
  await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'Botify Command Center' })).toBeVisible();
  const assistLink = page.locator('a[href="/seo/botify-assist"]').first();
  await expect(assistLink).toBeVisible();
  await expect(assistLink).toHaveAttribute('href', '/seo/botify-assist');
  await page.goto('/seo/botify-assist');
  await expect(page).toHaveURL(/\/seo\/botify-assist$/);
  await expect(page.getByRole('heading', { name: 'Assist Prompt Console' })).toBeVisible();
});

test('hootsuite quick links are visible on seo hub and navigate to Hootsuite pages', async ({ page }) => {
  test.slow();
  test.setTimeout(90000);
  await page.goto('/seo');

  await expect(page.getByRole('heading', { name: 'Hootsuite Command Center' })).toBeVisible();

  const readinessLink = page.locator('a[href="/seo/hootsuite-readiness"]').first();
  await expect(readinessLink).toBeVisible();
  await expect(readinessLink).toHaveAttribute('href', '/seo/hootsuite-readiness');
  await page.goto('/seo/hootsuite-readiness');
  await expect(page).toHaveURL(/\/seo\/hootsuite-readiness$/);
  await expect(page.getByRole('heading', { name: 'Hootsuite End-to-End Readiness Hub' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'Hootsuite Command Center' })).toBeVisible();
  const automationLink = page.locator('a[href="/seo/hootsuite-automation"]').first();
  await expect(automationLink).toBeVisible();
  await expect(automationLink).toHaveAttribute('href', '/seo/hootsuite-automation');
  await page.goto('/seo/hootsuite-automation');
  await expect(page).toHaveURL(/\/seo\/hootsuite-automation$/);
  await expect(page.getByRole('heading', { name: 'Hootsuite Run And Schedule Control' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'Hootsuite Command Center' })).toBeVisible();
  const integrationsLink = page.locator('a[href="/seo/hootsuite-integrations"]').first();
  await expect(integrationsLink).toBeVisible();
  await expect(integrationsLink).toHaveAttribute('href', '/seo/hootsuite-integrations');
  await page.goto('/seo/hootsuite-integrations');
  await expect(page).toHaveURL(/\/seo\/hootsuite-integrations$/);
  await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();
});

test('brightedge quick links are visible on seo hub and navigate to BrightEdge pages', async ({ page }) => {
  test.slow();
  test.setTimeout(90000);
  await page.goto('/seo');

  await expect(page.getByRole('heading', { name: 'BrightEdge Command Center' })).toBeVisible();

  const readinessLink = page.locator('a[href="/seo/brightedge-readiness"]').first();
  await expect(readinessLink).toBeVisible();
  await expect(readinessLink).toHaveAttribute('href', '/seo/brightedge-readiness');
  await page.goto('/seo/brightedge-readiness');
  await expect(page).toHaveURL(/\/seo\/brightedge-readiness$/);
  await expect(page.getByRole('heading', { name: 'BrightEdge End-to-End Readiness Hub' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'BrightEdge Command Center' })).toBeVisible();
  const automationLink = page.locator('a[href="/seo/brightedge-automation"]').first();
  await expect(automationLink).toBeVisible();
  await expect(automationLink).toHaveAttribute('href', '/seo/brightedge-automation');
  await page.goto('/seo/brightedge-automation');
  await expect(page).toHaveURL(/\/seo\/brightedge-automation$/);
  await expect(page.getByRole('heading', { name: 'BrightEdge Run And Product Control' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'BrightEdge Command Center' })).toBeVisible();
  const integrationsLink = page.locator('a[href="/seo/brightedge-integrations"]').first();
  await expect(integrationsLink).toBeVisible();
  await expect(integrationsLink).toHaveAttribute('href', '/seo/brightedge-integrations');
  await page.goto('/seo/brightedge-integrations');
  await expect(page).toHaveURL(/\/seo\/brightedge-integrations$/);
  await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'BrightEdge Command Center' })).toBeVisible();
  const assistLink = page.locator('a[href="/seo/brightedge-assist"]').first();
  await expect(assistLink).toBeVisible();
  await expect(assistLink).toHaveAttribute('href', '/seo/brightedge-assist');
  await page.goto('/seo/brightedge-assist');
  await expect(page).toHaveURL(/\/seo\/brightedge-assist$/);
  await expect(page.getByRole('heading', { name: 'Assist Prompt Console' })).toBeVisible();
});

test('seoai quick links are visible on seo hub and navigate to SEOAI pages', async ({ page }) => {
  test.slow();
  test.setTimeout(90000);
  await page.goto('/seo');

  await expect(page.getByRole('heading', { name: 'SEO.AI Command Center' })).toBeVisible();

  const readinessLink = page.locator('a[href="/seo/seo-ai-readiness"]').first();
  await expect(readinessLink).toBeVisible();
  await expect(readinessLink).toHaveAttribute('href', '/seo/seo-ai-readiness');
  await page.goto('/seo/seo-ai-readiness');
  await expect(page).toHaveURL(/\/seo\/seo-ai-readiness$/);
  await expect(page.getByRole('heading', { name: 'SEO.AI End-to-End Readiness Hub' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'SEO.AI Command Center' })).toBeVisible();
  const automationLink = page.locator('a[href="/seo/seo-ai-automation"]').first();
  await expect(automationLink).toBeVisible();
  await expect(automationLink).toHaveAttribute('href', '/seo/seo-ai-automation');
  await page.goto('/seo/seo-ai-automation');
  await expect(page).toHaveURL(/\/seo\/seo-ai-automation$/);
  await expect(page.getByRole('heading', { name: 'SEO.AI Run And Schedule Control' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'SEO.AI Command Center' })).toBeVisible();
  const integrationsLink = page.locator('a[href="/seo/seo-ai-integrations"]').first();
  await expect(integrationsLink).toBeVisible();
  await expect(integrationsLink).toHaveAttribute('href', '/seo/seo-ai-integrations');
  await page.goto('/seo/seo-ai-integrations');
  await expect(page).toHaveURL(/\/seo\/seo-ai-integrations$/);
  await expect(page.getByRole('heading', { name: 'Provider Wiring And Remediation' })).toBeVisible();

  await gotoSeoHub(page);
  await expect(page.getByRole('heading', { name: 'SEO.AI Command Center' })).toBeVisible();
  const assistLink = page.locator('a[href="/seo/seo-ai-assist"]').first();
  await expect(assistLink).toBeVisible();
  await expect(assistLink).toHaveAttribute('href', '/seo/seo-ai-assist');
  await page.goto('/seo/seo-ai-assist');
  await expect(page).toHaveURL(/\/seo\/seo-ai-assist$/);
  await expect(page.getByRole('heading', { name: 'Assist Prompt Console' })).toBeVisible();
});
